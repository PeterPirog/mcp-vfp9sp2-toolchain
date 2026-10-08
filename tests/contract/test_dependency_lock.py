# -*- coding: utf-8 -*-
"""Frozen dependency-lock verification tests (REQ-G00-018/022, REQ-P00-024,
REQ-AUTO-045).

Positive lock-internal checks run against the real candidate tree. The four
required negative-control mutations (exact version, artifact hash, origin,
direct dependency declaration) run the verifier against isolated temp copies
of the canonical artifacts and must each fail deterministically. All checks
are stdlib-only and offline; no wheelhouse is required for the negative
controls.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterator

from vfp_toolchain.verification import engine

from tests.support import REPO_ROOT, load_repo_json

REQUIREMENT_IDS = (
    "REQ-G00-018",
    "REQ-G00-022",
    "REQ-P00-024",
    "REQ-AUTO-045",
)

MUTATED_LOCK_FILES = (
    "spec/dependency-lock.json",
    "spec/requirements.graph.json",
    "spec/SOURCE_OF_TRUTH.md",
    "spec/schemas/dependency-lock.schema.json",
    "pyproject.toml",
)


@contextlib.contextmanager
def _temp_repo_with_lock(lock: dict[str, Any]) -> Iterator[Path]:
    """Materialize a minimal verifier-visible repo copy with a mutated lock."""
    tmp = tempfile.TemporaryDirectory(prefix="vfp-lock-negative-")
    try:
        tmp_root = Path(tmp.name)
        spec = tmp_root / "spec"
        (spec / "schemas").mkdir(parents=True)
        for relative in MUTATED_LOCK_FILES:
            source = REPO_ROOT / relative
            destination = tmp_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        (tmp_root / "spec" / "dependency-lock.json").write_text(
            json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        yield tmp_root
    finally:
        tmp.cleanup()


def _mutated_lock(mutator) -> dict[str, Any]:
    lock = load_repo_json("spec/dependency-lock.json")
    mutator(lock)
    return lock


class FrozenLockPositiveTests(unittest.TestCase):
    def test_lock_internal_checks_have_no_failures(self) -> None:
        report = engine.dependency_lock_report(REPO_ROOT)
        failures = [c for c in report["checks"] if c["status"] == "FAIL"]
        self.assertEqual(failures, [], report)
        self.assertIn(report["status"], ("PASS", "BLOCKED"))
        wheelhouse_value = __import__("os").environ.get(engine.DEPENDENCY_LOCK_WHEELHOUSE_ENV_VAR)
        if wheelhouse_value:
            self.assertEqual(report["status"], "PASS", report)

    def test_lock_is_frozen_single_version_per_distribution(self) -> None:
        lock = load_repo_json("spec/dependency-lock.json")
        self.assertEqual(lock["resolution_status"], "RESOLVED_FROZEN")
        self.assertEqual(lock["lock_role"], "GREENFIELD_BOOTSTRAP")
        versions: dict[str, set] = {}
        for entry in lock["resolved"]["distributions"]:
            versions.setdefault(entry["distribution"], set()).add(entry["version"])
        self.assertEqual({name: sorted(v) for name, v in versions.items() if len(v) != 1}, {})

    def test_runtime_profile_is_truthfully_empty(self) -> None:
        lock = load_repo_json("spec/dependency-lock.json")
        self.assertEqual(lock["direct_constraints"]["runtime"], [])
        runtime_members = [
            entry["distribution"]
            for entry in lock["resolved"]["distributions"]
            if "runtime" in entry["profile_membership"]
        ]
        self.assertEqual(runtime_members, [])


class FrozenLockNegativeControls(unittest.TestCase):
    """Each mutation of the frozen lock must fail the verifier deterministically."""

    def _assert_verifier_fails(self, lock: dict[str, Any], expected_check: str) -> None:
        with _temp_repo_with_lock(lock) as tmp_root:
            report = engine.dependency_lock_report(tmp_root)
            self.assertEqual(
                report["status"],
                "FAIL",
                f"mutation was not detected: {json.dumps(report['checks'], indent=2)[:800]}",
            )
            failed = [c["check"] for c in report["checks"] if c["status"] == "FAIL"]
            self.assertIn(expected_check, failed, failed)

    def test_exact_version_mutation_is_rejected(self) -> None:
        # REQ-AUTO-045 / REQ-G00-018: a changed exact version must not pass.
        def mutate(lock: dict[str, Any]) -> None:
            entry = lock["resolved"]["distributions"][0]
            entry["version"] = "9.9.9"

        self._assert_verifier_fails(_mutated_lock(mutate), "no_floating_versions")

    def test_artifact_hash_mutation_is_rejected(self) -> None:
        # REQ-AUTO-045 (same-version-different-hash) / REQ-P00-024.
        def mutate(lock: dict[str, Any]) -> None:
            lock["transitive_artifacts"][0]["sha256"] = "0" * 64

        self._assert_verifier_fails(_mutated_lock(mutate), "artifact_inventory_internal_consistency")

    def test_origin_mutation_is_rejected(self) -> None:
        # REQ-AUTO-045 (wrong-origin) / REQ-G00-022 approved-origin binding.
        def mutate(lock: dict[str, Any]) -> None:
            entry = lock["resolved"]["distributions"][0]
            entry["origin"] = "https://unapproved-index.example/simple/attrs-9.9.9-py3-none-any.whl"

        self._assert_verifier_fails(_mutated_lock(mutate), "artifact_inventory_internal_consistency")

    def test_direct_dependency_declaration_mutation_is_rejected(self) -> None:
        # REQ-G00-018/022: the lock's direct set must equal the materialized
        # pyproject declarations; dropping a direct constraint must fail.
        def mutate(lock: dict[str, Any]) -> None:
            lock["direct_constraints"]["test"] = []

        self._assert_verifier_fails(_mutated_lock(mutate), "direct_dependency_declaration_equality")

    def test_tampered_wheelhouse_is_rejected(self) -> None:
        # REQ-G00-018 (tampered-artifact rejection): an empty wheelhouse
        # cannot satisfy the locked artifact inventory.
        with tempfile.TemporaryDirectory(prefix="vfp-empty-wheelhouse-") as tmp:
            report = engine.dependency_lock_report(REPO_ROOT, wheelhouse=Path(tmp))
            self.assertEqual(report["status"], "FAIL", report)
            failed = [c["check"] for c in report["checks"] if c["status"] == "FAIL"]
            self.assertIn("wheelhouse_lock_equality", failed, failed)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()