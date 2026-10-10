# -*- coding: utf-8 -*-
"""Threat-model tests (REQ-P02-017)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT, load_repo_json

REQUIREMENT_IDS = (
    "REQ-P02-017",
    "REQ-PORT-032",
    "REQ-AUTO-046",
)

EXPECTED_BOUNDARIES = (
    "REPOSITORY_MUTATION",
    "FILESYSTEM_PATHS_REPARSE",
    "EXTERNAL_PROCESS_EXECUTION",
    "DEPENDENCY_ORIGINS",
    "VFP_INTEGRATION",
    "DBF_BINARY_DATA_HANDLING",
    "POSTGRESQL_BOUNDARY",
    "MCP_TRANSPORT",
    "EVIDENCE_PROVENANCE",
    "AGENT_CONTROLLER_TRUST",
    "REMOTE_INTEGRATION_PUBLICATION",
)


class ThreatModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load_repo_json("spec/threat-model.json")

    def test_boundaries_present(self) -> None:
        ids = [b["boundary_id"] for b in self.model["boundaries"]]
        for expected in EXPECTED_BOUNDARIES:
            self.assertIn(expected, ids)

    def test_no_control_marked_pass(self) -> None:
        for boundary in self.model["boundaries"]:
            for control in boundary["controls"]:
                self.assertNotEqual(control["status"], "PASS", control["id"])

    def test_controls_reference_requirements(self) -> None:
        for boundary in self.model["boundaries"]:
            for control in boundary["controls"]:
                self.assertTrue(control["requirements"], control["id"])

    def test_threat_ids_unique(self) -> None:
        seen = set()
        for boundary in self.model["boundaries"]:
            for threat in boundary["threats"]:
                self.assertNotIn(threat["id"], seen)
                seen.add(threat["id"])

    def test_schema_validation_when_capability_available(self) -> None:
        try:
            import jsonschema  # type: ignore  # noqa: F401
        except ImportError:
            self.fail(
                "BLOCKED: SCHEMA_CAPABILITY_UNAVAILABLE — jsonschema is not importable; "
                "dependency resolution is pending an approved origin."
            )
        import json

        document = json.loads((REPO_ROOT / "spec" / "schemas" / "threat-model.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(document)
        validator = jsonschema.Draft202012Validator(document)
        errors = list(validator.iter_errors(self.model))
        self.assertEqual([f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()