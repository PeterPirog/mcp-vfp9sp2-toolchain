# -*- coding: utf-8 -*-
"""Release-gate manifest tests (REQ-AUTO-025/026/036, REQ-PORT-015)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT, load_repo_json

REQUIREMENT_IDS = (
    "REQ-AUTO-025",
    "REQ-AUTO-026",
    "REQ-AUTO-036",
    "REQ-PORT-015",
    "REQ-G00-015",
)

RELEASES = ("0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "1.0.0")
RELEASE_ORDER = {v: i for i, v in enumerate(RELEASES)}


class ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = load_repo_json("spec/requirements.graph.json")
        cls.gates = {
            f"release-{version}.json": load_repo_json(f"release-gates/release-{version}.json")
            for version in RELEASES
        }
        cls.b0 = load_repo_json("release-gates/readiness-b0.json")
        cls.br0 = load_repo_json("release-gates/readiness-br0.json")
        cls.scenario = load_repo_json("release-gates/greenfield-scenario.json")
        cls.index = load_repo_json("release-gates/index.json")

    def test_release_gate_files_exist_for_all_releases(self) -> None:
        self.assertEqual(sorted(self.gates), sorted(f"release-{v}.json" for v in RELEASES))

    def test_no_release_is_qualified(self) -> None:
        for name, gate in self.gates.items():
            self.assertFalse(gate["qualified"], name)
            self.assertIsNone(gate["qualified_release_record"], name)
        self.assertFalse(self.b0["qualified"])
        self.assertEqual(self.b0["gate_result"], "PLANNED")

    def test_closures_are_cumulative(self) -> None:
        # Milestone-member IDs accumulate; earlier release-family gate
        # definitions (REQ-R0x-*) belong to their own release closure while a
        # later gate reruns the earlier releases' smoke/compatibility suites
        # (REQ-AUTO-026), recorded as cumulative_regression_releases.
        ordered = list(RELEASES)
        member_ids = {
            gate["release"]: set(gate["requirement_ids"]) - set(gate["governance_requirement_ids"])
            for gate in self.gates.values()
        }
        for previous, later in zip(ordered, ordered[1:]):
            self.assertTrue(
                member_ids[previous] <= member_ids[later],
                f"{later} milestone members must accumulate {previous}",
            )
            self.assertEqual(
                self.gates[f"release-{later}.json"]["cumulative_regression_releases"],
                ordered[: ordered.index(later)],
                later,
            )

    def test_release_closures_match_graph(self) -> None:
        for version in RELEASES:
            gate = self.gates[f"release-{version}.json"]
            graph_closure = self.graph["release_closures"][version]
            self.assertEqual(gate["requirement_ids"], graph_closure["requirement_ids"], version)
            self.assertEqual(gate["requirement_id_digest"], graph_closure["requirement_id_digest"], version)

    def test_readiness_gates_match_graph(self) -> None:
        self.assertEqual(self.b0["requirement_ids"], self.graph["readiness_closures"]["B0"]["requirement_ids"])
        self.assertEqual(self.br0["requirement_ids"], self.graph["readiness_closures"]["BR0"]["requirement_ids"])
        self.assertEqual(self.b0["gate"], "B0")
        self.assertEqual(self.br0["gate"], "BR0")

    def test_scenario_definitions_parameterized_by_authoring_mode(self) -> None:
        self.assertEqual(set(self.scenario["variants"]), {"MANUAL", "AUTONOMOUS", "HYBRID"})
        for variant, definition in self.scenario["variants"].items():
            self.assertTrue(definition["phases"], variant)
        self.assertTrue(self.scenario["all_scenario_inputs_declared"])

    def test_gate_index_lists_all_gates(self) -> None:
        self.assertEqual(len(self.index["gates"]), len(RELEASES) + 3)

    def test_first_release_includes_0_4_0_milestones(self) -> None:
        gate = self.gates["release-0.4.0.json"]
        self.assertEqual(
            gate["cumulative_milestones"],
            ["P00_DOMAIN", "P01_CORE", "P02_SECURITY", "P01_MCP_MIN", "P03_KNOWLEDGE", "P04_DATA"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()