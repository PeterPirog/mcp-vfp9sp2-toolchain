# -*- coding: utf-8 -*-
"""Deterministic GREENFIELD bootstrap dependency-lock builder (REQ-G00-018/022).

Consumes the canonical resolution receipt of the ONE authorized resolution
event and materializes the frozen canonical bootstrap dependency lock:

    spec/dependency-lock.json             canonical frozen lock (RESOLVED_FROZEN)
    spec/dependency-lock.wheelhouse.txt   require-hashes wheelhouse manifest

The builder performs NO dependency resolution and NO network access. It
fails closed when the receipt, the materialized pyproject declarations, or
the frozen wheelhouse disagree. The receipt carries the approved-origin
authorization; the lock binds SOT, invocation, resolver, origin, exact
versions, the complete transitive artifact inventory, and integrity hashes.

Usage:
    python tools/build_dependency_lock.py --receipt PATH --wheelhouse DIR
                                          [--check-only] [--repo-root DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT_CANDIDATE / "src"))

from vfp_toolchain.canonical import artifact_json_bytes, logical_sha256  # noqa: E402
from vfp_toolchain.verification import engine  # noqa: E402

RECEIPT_KIND = "GREENFIELD_DEPENDENCY_RESOLUTION_RECEIPT"
RECEIPT_SCHEMA_VERSION = 1
EXPECTED_WORK_PACKET = "WP-GREENFIELD-B0-001A"
GENERATOR_IDENTITY = "vfp-toolchain-dependency-lock-builder"
GENERATOR_VERSION = "1.0.0"
POST_SEAL_POLICY = "after candidate-tree sealing: no floating re-resolution (REQ-G00-022)"
PYTHON_RANGE = ">=3.10,<3.15"


class LockBuilderError(Exception):
    """Deterministic lock-builder failure (fail closed, never guess)."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_receipt(receipt_path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise LockBuilderError("RECEIPT_UNREADABLE", str(error)[:200]) from error
    if not isinstance(receipt, dict):
        raise LockBuilderError("RECEIPT_MALFORMED", "receipt is not a JSON object")
    if receipt.get("receipt_kind") != RECEIPT_KIND or receipt.get("receipt_schema_version") != RECEIPT_SCHEMA_VERSION:
        raise LockBuilderError("RECEIPT_KIND_MISMATCH", "unrecognized resolution receipt kind/schema version")
    if receipt.get("work_packet") != EXPECTED_WORK_PACKET:
        raise LockBuilderError("RECEIPT_WORK_PACKET_MISMATCH", str(receipt.get("work_packet")))
    return receipt


def _normalize_direct_pairs(
    constraints: dict[str, list[dict[str, str]]],
) -> dict[str, list[tuple[str, str]]]:
    return {
        role: sorted((engine._pep503_normalize(entry["distribution"]), entry["constraint"]) for entry in entries)
        for role, entries in constraints.items()
    }


def build(repo_root: Path, receipt_path: Path, wheelhouse: Path) -> tuple[dict[str, Any], str]:
    receipt = _load_receipt(receipt_path)

    authorization = receipt.get("authorization") or {}
    approved_index = str(authorization.get("approved_index", ""))
    approved_host = str(authorization.get("approved_artifact_host", ""))
    authorization_id = str(authorization.get("authorization_id", ""))
    if not approved_index or not approved_host or not authorization_id:
        raise LockBuilderError("RECEIPT_AUTHORIZATION_INCOMPLETE", "authorization_id/approved origins missing")

    # SOT identity must match the materialized frozen SOT in this tree.
    sot_sha256 = _sha256_file(repo_root / "spec" / "SOURCE_OF_TRUTH.md")
    if receipt.get("sot_sha256") != sot_sha256:
        raise LockBuilderError("RECEIPT_SOT_MISMATCH", "receipt SOT hash differs from the tree's frozen SOT")

    invocation_hash = str(receipt.get("bootstrap_invocation_logical_sha256", ""))
    if not engine._SHA256_RE.fullmatch(invocation_hash):
        raise LockBuilderError("RECEIPT_INVOCATION_MALFORMED", "missing/malformed bootstrap invocation hash")

    # Direct dependency inputs must equal the materialized declarations.
    pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    try:
        declared = engine.declared_direct_constraints(pyproject_text)
        declared_profiles = engine.declared_optional_profiles(pyproject_text)
    except engine.DependencyDeclarationClassificationError as error:
        raise LockBuilderError("DECLARATION_CLASSIFICATION_FAILED", str(error)) from error
    receipt_direct = receipt.get("direct_inputs") or {}
    receipt_pairs = _normalize_direct_pairs(
        {
            "runtime": [],
            "build": [e for e in receipt_direct.get("declared_constraints", []) if e.get("role") == "build"],
            "test": [e for e in receipt_direct.get("declared_constraints", []) if e.get("role") == "test"],
            "schema_validation": [e for e in receipt_direct.get("declared_constraints", []) if e.get("role") == "schema_validation"],
        }
    )
    receipt_pairs["runtime"] = sorted(
        (engine._pep503_normalize(e["distribution"]), e["constraint"])
        for e in receipt_direct.get("declared_constraints", [])
        if e.get("role") == "runtime"
    )
    if receipt_pairs != _normalize_direct_pairs(declared):
        raise LockBuilderError("RECEIPT_DECLARATION_MISMATCH", "receipt direct inputs differ from pyproject declarations")
    receipt_profiles = {k: sorted(engine._pep503_normalize(n) for n in v) for k, v in (receipt_direct.get("optional_profiles") or {}).items()}
    if receipt_profiles != declared_profiles:
        raise LockBuilderError("RECEIPT_PROFILE_MISMATCH", "receipt optional profiles differ from pyproject declarations")

    # Union of the resolved artifacts across the environment sub-runs.
    artifacts: dict[str, dict[str, str]] = {}
    versions_by_distribution: dict[str, set[str]] = {}
    origin_hosts: set[str] = set()
    for sub_run in receipt.get("sub_runs", []):
        for artifact in sub_run.get("resolved_artifacts", []):
            filename = str(artifact.get("filename", ""))
            sha256 = str(artifact.get("sha256", "")).upper()
            name = engine._pep503_normalize(str(artifact.get("name", "")))
            version = str(artifact.get("version", ""))
            url = str(artifact.get("url", ""))
            if not engine._SHA256_RE.fullmatch(sha256):
                raise LockBuilderError("ARTIFACT_HASH_MALFORMED", filename)
            parsed = engine._wheel_artifact_record(filename)
            if parsed is None:
                raise LockBuilderError("ARTIFACT_FILENAME_UNPARSABLE", filename)
            if parsed["distribution"] != name or parsed["version"] != version:
                raise LockBuilderError("ARTIFACT_FILENAME_MISMATCH", filename)
            if not url.startswith(approved_host.rstrip("/") + "/"):
                raise LockBuilderError(
                    "UNEXPECTED_PACKAGE_ARTIFACT_ORIGIN",
                    f"{filename} -> {url[:80]}",
                )
            origin_hosts.add(url.split("/")[2])
            if filename in artifacts and artifacts[filename]["sha256"] != sha256:
                raise LockBuilderError("ARTIFACT_CROSS_RUN_DISAGREEMENT", filename)
            artifacts[filename] = {"name": name, "version": version, "sha256": sha256, "url": url}
            versions_by_distribution.setdefault(name, set()).add(version)
    floating = {name: sorted(values) for name, values in versions_by_distribution.items() if len(values) != 1}
    if floating:
        raise LockBuilderError("MATRIX_VERSION_DIVERGENCE", json.dumps(floating, sort_keys=True))

    direct_names = {
        engine._pep503_normalize(entry["distribution"])
        for entries in declared.values()
        for entry in entries
    }
    resolved_names = {record["name"] for record in artifacts.values()}
    missing_direct = sorted(direct_names - resolved_names)
    if missing_direct:
        raise LockBuilderError("DIRECT_SET_INCOMPLETE", json.dumps(missing_direct))

    # The frozen wheelhouse is authoritative input for closure and integrity.
    if not wheelhouse.is_dir():
        raise LockBuilderError("WHEELHOUSE_REQUIRED", "frozen wheelhouse directory required")
    wheelhouse_files = {path.name for path in wheelhouse.iterdir() if path.is_file()}
    undeclared = sorted(wheelhouse_files - set(artifacts))
    missing = sorted(set(artifacts) - wheelhouse_files)
    hash_mismatches = sorted(
        filename
        for filename, record in artifacts.items()
        if filename in wheelhouse_files and _sha256_file(wheelhouse / filename) != record["sha256"]
    )
    if undeclared or missing or hash_mismatches:
        raise LockBuilderError(
            "WHEELHOUSE_NOT_EQUAL_TO_RESOLUTION",
            json.dumps(
                {"undeclared": undeclared[:10], "missing": missing[:10], "hash_mismatches": hash_mismatches[:10]},
                sort_keys=True,
            ),
        )

    closure = engine.compute_lock_closure(
        wheelhouse,
        declared,
        declared_profiles,
        {filename: {"distribution": record["name"], "version": record["version"]} for filename, record in sorted(artifacts.items())},
    )
    if closure["status"] == "BLOCKED":
        raise LockBuilderError(
            "CLOSURE_CAPABILITY_UNAVAILABLE",
            str(closure.get("reason", "")),
        )
    if closure["status"] != "PASS":
        raise LockBuilderError(
            "CLOSURE_INVALID",
            json.dumps(closure["errors"][:10], sort_keys=True),
        )
    if not origin_hosts <= {"files.pythonhosted.org"}:
        raise LockBuilderError("UNEXPECTED_ORIGIN_HOSTS", json.dumps(sorted(origin_hosts - {"files.pythonhosted.org"})))

    distributions: list[dict[str, Any]] = []
    for filename, record in sorted(artifacts.items()):
        distributions.append(
            {
                "distribution": record["name"],
                "version": record["version"],
                "artifact_filename": filename,
                "sha256": record["sha256"],
                "profile_membership": closure["profile_membership"].get(record["name"], []),
                "origin": record["url"],
            }
        )
    transitive_artifacts = [
        {
            "filename": filename,
            "distribution": record["name"],
            "version": record["version"],
            "sha256": record["sha256"],
        }
        for filename, record in sorted(artifacts.items())
    ]

    resolver_identity = receipt.get("resolver_identity") or {}
    pip_versions = resolver_identity.get("pip_versions_by_python") or {}
    resolver_version_string = ";".join(f"py{python}:{pip_versions[python]}" for python in sorted(pip_versions))
    if not resolver_version_string:
        raise LockBuilderError("RESOLVER_IDENTITY_MISSING", "receipt carries no per-environment resolver identity")

    lock: dict[str, Any] = {
        "schema_version": 1,
        "sot_revision": 35,
        "sot_sha256": sot_sha256,
        "generator": {
            "identity": GENERATOR_IDENTITY,
            "version": GENERATOR_VERSION,
            "source_sha256": _sha256_file(Path(__file__).resolve()),
        },
        "artifact_kind": "DEPENDENCY_LOCK",
        "lock_role": "GREENFIELD_BOOTSTRAP",
        "resolution_status": "RESOLVED_FROZEN",
        "blocker": None,
        "approved_origins": [
            {"origin": approved_index, "authorization_ref": authorization_id},
            {"origin": approved_host.rstrip("/"), "authorization_ref": authorization_id},
        ],
        "resolver_identity": {
            "tool": str(resolver_identity.get("resolver_tool", "pip")),
            "version": resolver_version_string,
        },
        "python_range": PYTHON_RANGE,
        "direct_constraints": declared,
        "optional_profiles": declared_profiles,
        "resolved": {
            "resolved_at_invocation_hash": invocation_hash,
            "distributions": distributions,
        },
        "transitive_artifacts": transitive_artifacts,
        "post_seal_policy": POST_SEAL_POLICY,
    }
    lock["content_sha256"] = logical_sha256(lock)

    wheelhouse_manifest = render_wheelhouse_manifest(artifacts, lock["content_sha256"])
    return lock, wheelhouse_manifest


def render_wheelhouse_manifest(artifacts: dict[str, dict[str, str]], lock_content_sha256: str) -> str:
    """Deterministic require-hashes manifest for the frozen wheelhouse.

    One block per distribution (sorted), every artifact hash of that
    distribution listed; pip then picks the wheel matching the installing
    environment while refusing anything whose hash is not in this manifest.
    """
    lines = [
        "# Canonical GREENFIELD bootstrap wheelhouse manifest (REQ-G00-018 / REQ-G00-022).",
        "# Generated by tools/build_dependency_lock.py — deterministic output; never hand-edited.",
        f"# Bound lock: spec/dependency-lock.json (content_sha256: {lock_content_sha256})",
        "# Offline install:",
        "#   python -m pip install --no-index --only-binary=:all: --find-links <WHEELHOUSE_DIR> --require-hashes -r spec/dependency-lock.wheelhouse.txt",
    ]
    by_distribution: dict[str, dict[str, str]] = {}
    for record in artifacts.values():
        existing = by_distribution.setdefault(record["name"], {"version": record["version"], "sha256": record["sha256"]})
        if existing["version"] != record["version"]:
            raise LockBuilderError("MANIFEST_VERSION_DIVERGENCE", record["name"])
    for name in sorted(by_distribution):
        record = by_distribution[name]
        hashes = sorted(
            artifact["sha256"]
            for artifact in artifacts.values()
            if artifact["name"] == name
        )
        requirement = f"{name}=={record['version']}"
        if len(hashes) == 1:
            lines.append(f"{requirement} --hash=sha256:{hashes[0].lower()}")
        else:
            lines.append(f"{requirement} \\")
            for index, digest in enumerate(hashes):
                tail = "" if index == len(hashes) - 1 else " \\"
                lines.append(f"    --hash=sha256:{digest.lower()}{tail}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT_CANDIDATE)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        lock, wheelhouse_manifest = build(args.repo_root, args.receipt, args.wheelhouse)
    except LockBuilderError as error:
        print(f"LOCK_BUILD_FAILED: {error.code}: {error.message}", file=sys.stderr)
        return 2
    if args.check_only:
        print("LOCK_BUILD_CHECK_ONLY_PASS")
        return 0
    (args.repo_root / "spec" / "dependency-lock.json").write_bytes(artifact_json_bytes(lock))
    (args.repo_root / "spec" / "dependency-lock.wheelhouse.txt").write_text(wheelhouse_manifest, encoding="utf-8", newline="\n")
    print(f"DEPENDENCY_LOCK_FROZEN content_sha256={lock['content_sha256']}")
    print(f"DEPENDENCY_LOCK_WHEELHOUSE_MANIFEST_WRITTEN artifacts={len(lock['transitive_artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())