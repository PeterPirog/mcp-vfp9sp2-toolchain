# -*- coding: utf-8 -*-
"""Verification manifest integrity tests (REQ-AUTO-002/003/004, REQ-PORT-004/007)."""

from __future__ import annotations

import unittest
from pathlib import Path

from vfp_toolchain.verification import engine

from tests.support import REPO_ROOT, load_repo_json

REQUIREMENT_IDS = (
    "REQ-AUTO-002",
    "REQ-AUTO-003",
    "REQ-AUTO-004",
    "REQ-AUTO-005",
    "REQ-G00-007",
    "REQ-PORT-004",
    "REQ-PORT-007",
)


class VerificationManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_repo_json("spec/verification.manifest.json")
        cls.graph = load_repo_json("spec/requirements.graph.json")

    def test_manifest_covers_all_484_requirements(self) -> None:
        self.assertEqual(len(self.manifest["requirements"]), 484)
        graph_ids = {r["id"] for r in self.graph["requirements"]}
        self.assertEqual(set(self.manifest["requirements"]), graph_ids)

    def test_every_requirement_has_a_verifier(self) -> None:
        empty = [rid for rid, record in self.manifest["requirements"].items() if not record["verifier_ids"]]
        self.assertEqual(empty, [])

    def test_no_false_pass(self) -> None:
        for rid, record in self.manifest["requirements"].items():
            if record["current_state"] == "PASS":
                self.fail(f"false PASS in manifest for {rid}")
        for verifier_id, verifier in self.manifest["verifiers"].items():
            if verifier["state"] == "PLANNED" and verifier["command"] is not None:
                self.fail(f"PLANNED verifier with command: {verifier_id}")

    def test_no_dangling_executable_references(self) -> None:
        dangling = engine._dangling_executable_references(self.manifest, REPO_ROOT)  # noqa: SLF001
        self.assertEqual(dangling, [])

    def test_planned_verifier_cannot_pass(self) -> None:
        # REQ-P00-014 (contract evolution) is IMPLEMENTATION with only a
        # PLANNED verifier: dispatch must return non-PASS.
        context = {
            "start_mode": "GREENFIELD",
            "operation_scope": "LOCAL_QUALIFICATION",
            "authoring_mode": "HYBRID",
            "release_profile": "NONE",
            "release_context": "NONE",
        }
        result = engine.dispatch_requirement("REQ-P00-014", context, None, graph=self.graph, manifest=self.manifest)
        self.assertEqual(result["status"], "PLANNED")
        self.assertNotEqual(result["status"], "PASS")

    def test_unknown_requirement_id_fails_closed(self) -> None:
        context = {
            "start_mode": "GREENFIELD",
            "operation_scope": "LOCAL_QUALIFICATION",
            "authoring_mode": "HYBRID",
            "release_profile": "NONE",
            "release_context": "NONE",
        }
        result = engine.dispatch_requirement("REQ-XXX-999", context, None, graph=self.graph, manifest=self.manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["error_code"], "VERIFIER_UNKNOWN")

    def test_executable_verifier_commands_are_repo_local(self) -> None:
        for verifier_id, verifier in self.manifest["verifiers"].items():
            if verifier["state"] == "EXECUTABLE":
                command = verifier["command"]
                self.assertTrue(command, verifier_id)
                for arg in command:
                    if isinstance(arg, str) and (arg.startswith("/") or arg.startswith("..")):
                        self.fail(f"non repo-local command element in {verifier_id}: {arg}")
                path_args = [
                    arg
                    for arg in command
                    if isinstance(arg, str) and not arg.startswith("-") and ("/" in arg or "\\" in arg)
                ]
                self.assertTrue(
                    path_args or command[:1] == ["python"],
                    f"{verifier_id}: no repo-local path argument",
                )
                for arg in path_args:
                    self.assertTrue((REPO_ROOT / arg).exists(), f"{verifier_id}: {arg}")

    def test_manifest_carries_state_vocabulary(self) -> None:
        self.assertEqual(
            self.manifest["state_vocabulary"],
            ["UNASSESSED", "PLANNED", "NOT_IMPLEMENTED", "PARTIAL", "BLOCKED", "PASS", "NOT_APPLICABLE"],
        )
        for record in self.manifest["requirements"].values():
            self.assertIn(record["current_state"], self.manifest["state_vocabulary"])

    def test_manifest_binds_graph_hash(self) -> None:
        self.assertEqual(self.manifest["graph_content_sha256"], self.graph["content_sha256"])
        self.assertEqual(self.manifest["sot_sha256"], self.graph["sot_sha256"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()