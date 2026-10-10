# -*- coding: utf-8 -*-
"""Execution-profile tests (REQ-PORT-008/027/034, REQ-G00-026/028)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-G00-026",
    "REQ-G00-028",
    "REQ-PORT-008",
    "REQ-PORT-027",
    "REQ-PORT-034",
)

DRIVE_LETTER_PATTERN = re.compile(r"^[A-Za-z]:")


class ExecutionProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generic = load_profile("execution-profiles/generic.json")
        cls.converge_text = (REPO_ROOT / "execution-profiles" / "converge.yaml").read_text(encoding="utf-8")

    def test_generic_profile_structure(self) -> None:
        profile = self.generic
        self.assertEqual(profile["profile_id"], "generic")
        self.assertEqual(profile["controller_class"], "HUMAN_OPERATED_OR_HYBRID")
        self.assertFalse(profile["converge_required"])
        self.assertIn("MANUAL", profile["supported_authoring_modes"])
        self.assertIn("HYBRID", profile["supported_authoring_modes"])
        self.assertNotIn("AUTONOMOUS", profile["supported_authoring_modes"])
        self.assertEqual(profile["operation_scope_default"], "LOCAL_QUALIFICATION")

    def test_role_bindings_are_logical_not_machine(self) -> None:
        blob = (REPO_ROOT / "execution-profiles" / "generic.json").read_text(encoding="utf-8")
        for line in blob.splitlines():
            self.assertNotRegex(line, DRIVE_LETTER_PATTERN, "hard-coded drive letter in profile")
        bindings = self.generic["role_bindings"]
        for role in ("project_home", "repo_root", "temp_root", "venv_root", "cache_roots", "tool_roots", "bootstrap_sot_path"):
            self.assertIn(role, bindings)
        self.assertEqual(bindings["repo_root"]["rule"], "project_home\\mcp-vfp9sp2-toolchain")
        self.assertEqual(bindings["project_home"]["source"], "OPERATOR")
        self.assertEqual(bindings["bootstrap_sot_path"]["source"], "OPERATOR")

    def test_converge_profile_pins_controller_baseline(self) -> None:
        self.assertIn("https://github.com/PeterPirog/converge-orchestrator", self.converge_text)
        self.assertIn("1be97b75cf3b51f5ad0c2f212288f0a9edb3899b", self.converge_text)
        self.assertIn("d47b3c74b7b597dec503b4d3dca9db60e5488c93", self.converge_text)
        self.assertIn("AUTONOMOUS_MODEL_ROLE_CONTRACT_V1", self.converge_text)
        self.assertIn("require_spec_read_only: true", self.converge_text)
        self.assertIn("DISABLED", self.converge_text)

    def test_profiles_share_logical_bindings(self) -> None:
        # equivalent post-bootstrap logical bindings (REQ-PORT-034)
        self.assertIn("mcp-vfp9sp2-toolchain", self.converge_text)
        self.assertIn("refs/heads/main", self.converge_text)
        self.assertIn("LOCAL_QUALIFICATION", self.converge_text)
        self.assertIn("MANUAL_BOOTSTRAP_V1", self.converge_text)
        self.assertIn("AUTONOMOUS_BOOTSTRAP_V1", self.converge_text)

    def test_no_drive_letter_in_converge_profile(self) -> None:
        for line in self.converge_text.splitlines():
            self.assertNotRegex(line.strip(), DRIVE_LETTER_PATTERN, line)


def load_profile(relative: str) -> dict:
    import json

    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()