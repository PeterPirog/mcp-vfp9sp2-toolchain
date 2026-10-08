# -*- coding: utf-8 -*-
"""Cycle-regression negative fixture (WP-SOT-REV35-SEMANTIC-AUDIT-001 Part E).

Recreates the removed brownfield generator defect (union of ancestor chains
over EVERY milestone membership) and proves:
  1. the failed rule DOES produce the reported four-node cycle
     (REQ-P00-005 -> REQ-P00-006 -> REQ-P03-001 -> REQ-P17-001 -> REQ-P00-005)
     inside an SCC;
  2. the canonical (corrected) rule produces NO such edge;
  3. the contract self-consistency engine REJECTS a graph built with the
     failed rule (fail-closed, machine-readable cycle evidence).
"""

from __future__ import annotations

import unittest

from vfp_toolchain.verification import engine
from vfp_toolchain.verification.sotparse import CycleError, RequirementGraphBuilder

from tests.support import (
    failed_requirement_edges,
    independent_sot_text,
    load_repo_json,
    tarjan_scc,
    topo_ancestors,
    canonical_requirement_edges,
    independent_parse,
)

REQUIREMENT_IDS = (
    "REQ-B00-004",
    "REQ-PORT-010",
    "REQ-AUTO-011",
)

REPORTED_CYCLE = ["REQ-P00-005", "REQ-P00-006", "REQ-P03-001", "REQ-P17-001"]


class CycleRegressionFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sot_text = independent_sot_text()
        cls.model = independent_parse(cls.sot_text)
        cls.topo, cls.ancestors = topo_ancestors(cls.model["milestones"])

    def test_failed_rule_reproduces_reported_cycle(self) -> None:
        edges = failed_requirement_edges(self.model, self.topo, self.ancestors)
        sccs = [c for c in tarjan_scc({rid: sorted(deps) for rid, deps in edges.items()}) if len(c) > 1]
        self.assertTrue(sccs, "the union-over-memberships rule must produce at least one SCC")
        containing = [c for c in sccs if set(REPORTED_CYCLE) <= set(c)]
        self.assertTrue(containing, "the reported four-node cycle must be inside a failed-rule SCC")
        # the concrete back edge that closed the reported cycle
        self.assertIn("REQ-P00-005", edges["REQ-P17-001"])

    def test_canonical_rule_has_no_back_edge(self) -> None:
        edges, _memberships = canonical_requirement_edges(self.model, self.topo, self.ancestors)
        self.assertNotIn("REQ-P00-005", edges["REQ-P17-001"])
        self.assertNotIn("REQ-P11-001", edges["REQ-P17-001"])
        sccs = [c for c in tarjan_scc({rid: sorted(deps) for rid, deps in edges.items()}) if len(c) > 1]
        self.assertEqual(sccs, [])

    def test_self_consistency_rejects_failed_rule_graph(self) -> None:
        graph = load_repo_json("spec/requirements.graph.json")
        manifest = load_repo_json("spec/verification.manifest.json")

        # Build the graph the way the removed brownfield generator did, then
        # force its prerequisite_ids into a tampered copy of the artifacts.
        failed_edges = failed_requirement_edges(self.model, self.topo, self.ancestors)
        tampered = dict(graph)
        tampered_requirements = []
        for record in graph["requirements"]:
            record = dict(record)
            record["prerequisite_ids"] = sorted(failed_edges[record["id"]])
            tampered_requirements.append(record)
        tampered["requirements"] = tampered_requirements

        report = engine.self_consistency_report(
            None, graph=tampered, manifest=manifest, sot_text=self.sot_text
        )
        self.assertEqual(report["status"], "FAIL")
        cycle_checks = [c for c in report["checks"] if c["check"] == "requirement_graph_acyclic_independent_scc"]
        self.assertTrue(cycle_checks and cycle_checks[0]["status"] == "FAIL")
        back_edge_check = [c for c in report["checks"] if c["check"] == "old_four_node_cycle_absent"]
        self.assertTrue(back_edge_check and back_edge_check[0]["status"] == "FAIL")

    def test_production_builder_fails_closed_on_injected_cycle(self) -> None:
        # Rule 6 (explicit prerequisite IDs remain authoritative) + rule 8
        # (mandatory cycle detection): inject an explicit prerequisite that
        # makes an early P00_DOMAIN member depend on a P18_FINAL member; the
        # canonical builder must raise CycleError, never emit a cyclic graph.
        marker = "`REQ-P00-001` — The product MUST target"
        injected = self.sot_text.replace(
            "The product MUST target Microsoft Visual FoxPro 9.0 Service Pack 2 exclusively",
            "The product MUST target (prerequisite REQ-P18-001 for the injected-cycle negative control) "
            "Microsoft Visual FoxPro 9.0 Service Pack 2 exclusively",
            1,
        )
        self.assertNotEqual(injected, self.sot_text)
        self.assertIn(marker, injected)  # record format preserved
        builder = RequirementGraphBuilder(injected)
        with self.assertRaises(CycleError) as caught:
            builder.build()
        cycle = caught.exception.cycle
        self.assertIn("REQ-P00-001", cycle)
        self.assertIn("REQ-P18-001", cycle)

    def test_malformed_record_fails_closed(self) -> None:
        from vfp_toolchain.verification.sotparse import SotParseError

        marker = "`REQ-P00-001` — The product MUST target"
        injected = self.sot_text.replace(
            marker,
            "`REQ-P00-001` The product MUST target (separator removed)",
            1,
        )
        self.assertNotEqual(injected, self.sot_text)
        with self.assertRaises(SotParseError):
            RequirementGraphBuilder(injected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()