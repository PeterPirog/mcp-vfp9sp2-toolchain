# -*- coding: utf-8 -*-
"""Start-state classification tests (REQ-G00-001/002/033/034/036)."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from vfp_toolchain.bootstrap.classify import (
    CLASSIFICATION_SCHEMA_VERSION,
    classify_start_state,
)

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-G00-001",
    "REQ-G00-002",
    "REQ-G00-003",
    "REQ-G00-033",
    "REQ-G00-034",
    "REQ-G00-036",
)


class StartStateClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="vfp-startstate-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write_resume_provenance(self, root: Path, sot_sha256: str, tree: str) -> None:
        evidence_dir = root / "evidence" / "bootstrap"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": CLASSIFICATION_SCHEMA_VERSION,
            "provenance_kind": "GREENFIELD_BOOTSTRAP_RESUME",
            "sot_sha256": sot_sha256,
            "candidate_tree_sha256": tree,
        }
        (evidence_dir / "candidate-provenance.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_absent_root_is_greenfield(self) -> None:
        result = classify_start_state(self.tmp / "does-not-exist")
        self.assertEqual(result["occupancy"], "ABSENT")
        self.assertEqual(result["start_mode"], "GREENFIELD")

    def test_empty_directory_is_greenfield(self) -> None:
        (self.tmp / "empty").mkdir()
        result = classify_start_state(self.tmp / "empty")
        self.assertEqual(result["occupancy"], "EMPTY")
        self.assertEqual(result["start_mode"], "GREENFIELD")

    def test_empty_git_repository_is_greenfield(self) -> None:
        root = self.tmp / "emptygit"
        root.mkdir()
        (root / ".git").mkdir()
        result = classify_start_state(root)
        self.assertEqual(result["occupancy"], "EMPTY")
        self.assertEqual(result["start_mode"], "GREENFIELD")

    def test_unknown_nonempty_is_ambiguous(self) -> None:
        root = self.tmp / "unknown"
        root.mkdir()
        (root / "mystery.bin").write_bytes(b"\x00\x01")
        result = classify_start_state(root)
        self.assertEqual(result["occupancy"], "UNKNOWN_NONEMPTY")
        self.assertEqual(result["start_mode"], "AMBIGUOUS")

    def test_matching_resume_with_provenance_is_greenfield(self) -> None:
        root = self.tmp / "resume"
        root.mkdir()
        (root / "partial.txt").write_text("x", encoding="utf-8")
        self._write_resume_provenance(root, "A" * 64, "b" * 40)
        result = classify_start_state(root, expected_sot_sha256="A" * 64)
        self.assertEqual(result["occupancy"], "MATCHING_BOOTSTRAP_RESUME")
        self.assertEqual(result["start_mode"], "GREENFIELD")

    def test_wrong_sot_provenance_stays_unknown(self) -> None:
        root = self.tmp / "resumewrong"
        root.mkdir()
        (root / "partial.txt").write_text("x", encoding="utf-8")
        self._write_resume_provenance(root, "B" * 64, "b" * 40)
        result = classify_start_state(root, expected_sot_sha256="A" * 64)
        self.assertEqual(result["occupancy"], "UNKNOWN_NONEMPTY")

    def test_classifier_never_mutates(self) -> None:
        root = self.tmp / "sentinel"
        root.mkdir()
        (root / "keep.txt").write_text("keep", encoding="utf-8")
        before = sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob("*"))
        classify_start_state(root)
        after = sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse((root / "evidence").exists())

    def test_classification_is_deterministic(self) -> None:
        root = self.tmp / "determinism"
        root.mkdir()
        (root / "a.txt").write_text("x", encoding="utf-8")
        first = classify_start_state(root)
        second = classify_start_state(root)
        self.assertEqual(first, second)

    def test_project_home_siblings_do_not_affect_classification(self) -> None:
        # REQ-G00-027: classification is scoped to REPO_ROOT only.
        home = self.tmp / "home"
        (home / "TEMP").mkdir(parents=True)
        (home / "cache").mkdir()
        (home / "unrelated-repo").mkdir()
        repo = home / "mcp-vfp9sp2-toolchain"
        repo.mkdir()
        result = classify_start_state(repo)
        self.assertEqual(result["occupancy"], "EMPTY")
        self.assertEqual(result["start_mode"], "GREENFIELD")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()