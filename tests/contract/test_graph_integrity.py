# -*- coding: utf-8 -*-
"""Requirement-graph integrity tests against the INDEPENDENT parser."""

from __future__ import annotations

import re
import unittest
from collections import Counter

from tests.support import (
    REPO_ROOT,
    canonical_requirement_edges,
    independent_lifecycle,
    independent_parse,
    independent_sot_text,
    load_repo_json,
    tarjan_scc,
    topo_ancestors,
)

REQUIREMENT_IDS = (
    "REQ-PORT-009",
    "REQ-PORT-010",
    "REQ-PORT-014",
    "REQ-PORT-015",
    "REQ-PORT-021",
    "REQ-PORT-024",
    "REQ-PORT-025",
    "REQ-PORT-026",
    "REQ-P00-013",
    "REQ-B00-004",
)


class RequirementGraphIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = load_repo_json("spec/requirements.graph.json")
        cls.by_id = {r["id"]: r for r in cls.graph["requirements"]}
        cls.model = independent_parse(independent_sot_text())
        cls.topo, cls.ancestors = topo_ancestors(cls.model["milestones"])
        cls.edges, cls.memberships = canonical_requirement_edges(cls.model, cls.topo, cls.ancestors)

    def test_requirement_count_484(self) -> None:
        self.assertEqual(self.graph["requirement_count"], 484)
        self.assertEqual(len(self.model["order"]), 484)

    def test_first_last_ids(self) -> None:
        self.assertEqual(self.graph["first_id"], "REQ-G00-001")
        self.assertEqual(self.graph["last_id"], "REQ-P18-030")
        self.assertEqual(self.model["order"][0], "REQ-G00-001")
        self.assertEqual(self.model["order"][-1], "REQ-P18-030")

    def test_no_duplicate_ids(self) -> None:
        ids = [r["id"] for r in self.graph["requirements"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_exact_text_equality_with_sot(self) -> None:
        mismatches = [rid for rid, text in self.model["defs"].items() if self.by_id[rid]["text"] != text]
        self.assertEqual(mismatches, [])

    def test_document_order_equality(self) -> None:
        self.assertEqual([r["id"] for r in self.graph["requirements"]], self.model["order"])

    def test_lifecycle_counts_match_canonical_map(self) -> None:
        counts = Counter(r["lifecycle"] for r in self.graph["requirements"])
        self.assertEqual(
            dict(counts),
            {
                "IMPLEMENTATION": 268,
                "BOOTSTRAP": 125,
                "RELEASE_GUARD": 44,
                "MERGE_GUARD": 33,
                "FINAL_ACCEPTANCE": 11,
                "DEPLOYMENT_GUARD": 3,
            },
        )

    def test_lifecycle_assignment_independent_equality(self) -> None:
        independent = independent_lifecycle(self.model)
        recorded = {rid: self.by_id[rid]["lifecycle"] for rid in self.model["order"]}
        self.assertEqual(independent, recorded)

    def test_requirement_graph_acyclic_independent_scc(self) -> None:
        big = [c for c in tarjan_scc({rid: sorted(deps) for rid, deps in self.edges.items()}) if len(c) > 1]
        self.assertEqual(big, [])

    def test_graph_prerequisites_match_independent_canonical_edges(self) -> None:
        mismatches = []
        for rid in self.model["order"]:
            recorded = set(self.by_id[rid]["prerequisite_ids"])
            independent = self.edges[rid]
            if recorded != independent:
                mismatches.append((rid, len(recorded), len(independent)))
        self.assertEqual(mismatches, [])

    def test_regression_exec_milestones(self) -> None:
        expected = {
            "REQ-P00-005": "P11_REFACTOR",
            "REQ-P00-006": "P06_FOXBIN_ANALYSIS",
            "REQ-P03-001": "P03_KNOWLEDGE",
            "REQ-P17-001": "P01_MCP_MIN",
        }
        for rid, milestone in expected.items():
            self.assertEqual(self.by_id[rid]["execution_milestone"], milestone, rid)

    def test_split_scope_no_later_ancestor_import(self) -> None:
        deps = self.by_id["REQ-P17-001"]["prerequisite_ids"]
        # earliest-activation basis P01_MCP_MIN: P00/P01/P02 members only
        self.assertTrue(deps)
        for dep in deps:
            self.assertIn(self.by_id[dep]["execution_milestone"], ("P00_DOMAIN", "P01_CORE", "P02_SECURITY"))
        self.assertNotIn("REQ-P00-005", deps)  # P11 member — old back-edge target
        self.assertNotIn("REQ-P11-001", deps)
        # later re-selection (P17_MCP_STABILIZATION) must not import its ancestors
        self.assertNotIn("P11_REFACTOR", self.by_id["REQ-P17-001"]["prerequisite_milestones"])

    def test_future_phase_exclusion_p03_007(self) -> None:
        self.assertEqual(self.by_id["REQ-P03-007"]["execution_milestone"], "P05_SEMANTIC_GRAPH")
        p03_members = self.by_id["REQ-P03-007"]["milestones"]
        self.assertEqual(p03_members, ["P05_SEMANTIC_GRAPH"])

    def test_no_backwards_dependency_p11_to_p01_mcp_min(self) -> None:
        # P01_MCP_MIN is an ancestor of P11_REFACTOR, never a successor.
        successors: dict[str, set[str]] = {}
        for name, spec in self.model["milestones"].items():
            for parent in [a for a in spec.get("after", []) if a != "START_READY"]:
                successors.setdefault(parent, set()).add(name)
        reached: set[str] = set()
        frontier = ["P11_REFACTOR"]
        while frontier:
            current = frontier.pop()
            for nxt in successors.get(current, ()):  # type: ignore[arg-type]
                if nxt not in reached:
                    reached.add(nxt)
                    frontier.append(nxt)
        self.assertNotIn("P01_MCP_MIN", reached)

    def test_milestone_member_counts(self) -> None:
        counts = {m["name"]: m["member_count"] for m in self.graph["milestones"]}
        self.assertEqual(counts["P00_DOMAIN"], 16)
        self.assertEqual(counts["P01_MCP_MIN"], 14)
        self.assertEqual(counts["P03_KNOWLEDGE"], 8)
        self.assertEqual(counts["P06_FOXBIN_ANALYSIS"], 4)
        self.assertEqual(counts["P11_REFACTOR"], 18)
        self.assertEqual(counts["P17_MCP_STABILIZATION"], 23)

    def test_requirement_record_format_one_line_with_evidence(self) -> None:
        bad_format = []
        bad_evidence = []
        for record in self.graph["requirements"]:
            text = record["text"]
            if "\n" in text:
                bad_format.append(record["id"])
            if not ("acceptance evidence is" in text or "acceptance evidence covers" in text):
                bad_evidence.append(record["id"])
        self.assertEqual(bad_format, [])
        self.assertEqual(bad_evidence, [])

    def test_sot_sha256_binding(self) -> None:
        import hashlib

        sot_bytes = (REPO_ROOT / "spec" / "SOURCE_OF_TRUTH.md").read_bytes()
        digest = hashlib.sha256(sot_bytes).hexdigest().upper()
        self.assertEqual(self.graph["sot_sha256"], digest)

    def test_milestone_topological_order_linear_chain(self) -> None:
        self.assertEqual(
            self.graph["milestone_topological_order"],
            [
                "P00_DOMAIN",
                "P01_CORE",
                "P02_SECURITY",
                "P01_MCP_MIN",
                "P03_KNOWLEDGE",
                "P04_DATA",
                "P05_SEMANTIC_GRAPH",
                "P06_FOXBIN_ANALYSIS",
                "P07_FORMS_CLASSES",
                "P08_DBC_MODEL",
                "P09_REASONING",
                "P10_OPTIMIZATION",
                "P11_REFACTOR",
                "P12_PRIVACY",
                "P13_RELATIONAL_MODEL",
                "P14_TRANSLATION",
                "P15_SHADOW_MIGRATION",
                "P16_TRANSITION",
                "P17_MCP_STABILIZATION",
                "P18_FINAL",
            ],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()