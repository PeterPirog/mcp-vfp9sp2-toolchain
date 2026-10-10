# -*- coding: utf-8 -*-
"""Canonical layout and required file-set tests (REQ-G00-004/005/024)."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.support import REPO_ROOT, load_repo_json

REQUIREMENT_IDS = (
    "REQ-G00-004",
    "REQ-G00-005",
    "REQ-G00-006",
    "REQ-G00-016",
    "REQ-G00-017",
    "REQ-G00-023",
    "REQ-G00-024",
)

CANONICAL_PATHS = (
    "spec/SOURCE_OF_TRUTH.md",
    "spec/requirements.graph.json",
    "spec/verification.manifest.json",
    "spec/compatibility.manifest.json",
    "spec/acquisition.manifest.json",
    "spec/dependency-lock.json",
    "spec/threat-model.json",
    "spec/schemas/",
    "execution-profiles/converge.yaml",
    "execution-profiles/generic.json",
    "release-gates/",
    "evidence/",
    "third_party/",
    "src/vfp_toolchain/",
    "tests/",
    "docs/",
    "tools/",
    ".github/workflows/",
)

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".gitignore",
    ".gitattributes",
    "pyproject.toml",
)

VFP_BINARY_SUFFIXES = (
    ".dbf", ".fpt", ".cdx", ".idx", ".scx", ".sct", ".vcx", ".vct", ".frx", ".frt",
    ".lbx", ".lbt", ".mnx", ".mnt", ".pjx", ".pjt", ".dbc", ".dct", ".dcx",
)


class CanonicalLayoutTests(unittest.TestCase):
    def test_canonical_layout_paths(self) -> None:
        missing = [p for p in CANONICAL_PATHS if not (REPO_ROOT / p).exists()]
        self.assertEqual(missing, [])

    def test_required_file_set(self) -> None:
        missing = [p for p in REQUIRED_FILES if not (REPO_ROOT / p).is_file()]
        self.assertEqual(missing, [])

    def test_sot_byte_identity_in_repository(self) -> None:
        import hashlib

        digest = hashlib.sha256((REPO_ROOT / "spec" / "SOURCE_OF_TRUTH.md").read_bytes()).hexdigest().upper()
        graph = load_repo_json("spec/requirements.graph.json")
        self.assertEqual(digest, graph["sot_sha256"])

    def test_typed_package_marker(self) -> None:
        self.assertTrue((REPO_ROOT / "src" / "vfp_toolchain" / "py.typed").is_file())

    def test_mit_license(self) -> None:
        text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)

    def test_gitattributes_protects_sot_and_binary_families(self) -> None:
        text = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertRegex(text, r"spec/SOURCE_OF_TRUTH\.md\s+-text")
        for suffix in VFP_BINARY_SUFFIXES:
            self.assertRegex(text, rf"\*{re.escape(suffix)}\s+-text", suffix)

    def test_gitignore_excludes_build_and_venv(self) -> None:
        text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("__pycache__/", ".venv/", "dist/", "build/"):
            self.assertIn(pattern, text)

    def test_layout_verifier_report_passes(self) -> None:
        from vfp_toolchain.verification import engine

        report = engine.layout_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)

    def test_docs_are_truthful_about_empty_state(self) -> None:
        capability_doc = (REPO_ROOT / "docs" / "capability-state.md").read_text(encoding="utf-8")
        self.assertIn("NOT_IMPLEMENTED", capability_doc)


import re  # noqa: E402  (used by gitattributes test above)

if __name__ == "__main__":  # pragma: no cover
    unittest.main()