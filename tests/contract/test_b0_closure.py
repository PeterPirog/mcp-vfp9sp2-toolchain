# -*- coding: utf-8 -*-
"""B0 closure derivation tests (REQ-B00-002): graph-derived, no manual list."""

from __future__ import annotations

import unittest

from vfp_toolchain.verification import engine
from vfp_toolchain.verification.sotparse import readiness_closure

from tests.support import (
    independent_b0_closure,
    independent_parse,
    independent_sot_text,
    load_repo_json,
)

REQUIREMENT_IDS = (
    "REQ-B00-002",
    "REQ-B00-004",
    "REQ-G00-013",
    "REQ-G00-052",
    "REQ-AUTO-040",
    "REQ-AUTO-041",
    "REQ-PORT-030",
)

BROWNFIELD_ONLY_EXPECTED = {
    "REQ-G00-042",
    "REQ-G00-044",
    "REQ-G00-045",
    "REQ-G00-047",
    "REQ-G00-048",
    "REQ-G00-049",
    "REQ-G00-050",
    "REQ-G00-051",
    "REQ-B00-003",
    "REQ-P00-020",
    "REQ-P00-021",
    "REQ-P00-022",
}


class B0ClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = load_repo_json("spec/requirements.graph.json")
        cls.manifest = load_repo_json("spec/verification.manifest.json")
        cls.b0 = cls.graph["readiness_closures"]["B0"]
        cls.context = {
            "start_mode": "GREENFIELD",
            "operation_scope": "LOCAL_QUALIFICATION",
            "authoring_mode": "HYBRID",
            "release_profile": "NONE",
            "release_context": "NONE",
        }

    def test_closure_is_derived_not_manual(self) -> None:
        self.assertEqual(
            self.b0["derivation"],
            "lifecycle=BOOTSTRAP AND applicability(ctx) = true, plus transitive prerequisites",
        )
        # The graph must not carry a hand-maintained list source.
        self.assertNotIn("manual_list", self.b0)
        recomputed = readiness_closure(
            {k: v for k, v in self.graph.items() if k != "readiness_closures"} | {"requirements": self.graph["requirements"]},
            "B0",
            self.context,
        )
        self.assertEqual(recomputed["requirement_ids"], self.b0["requirement_ids"])
        self.assertEqual(recomputed["requirement_count"], self.b0["requirement_count"])

    def test_closure_matches_independent_derivation(self) -> None:
        model = independent_parse(independent_sot_text())
        independent = independent_b0_closure(model, self.context)
        self.assertEqual(independent, set(self.b0["requirement_ids"]))

    def test_b0_count_and_digest(self) -> None:
        self.assertEqual(self.b0["requirement_count"], 112)
        digest = self.b0["requirement_id_digest"]
        self.assertEqual(len(digest), 64)
        # digest stability: recomputed digest must equal the recorded one
        from vfp_toolchain.canonical import canonical_sha256

        self.assertEqual(canonical_sha256(sorted(self.b0["requirement_ids"])), digest)

    def test_brownfield_only_excluded_and_not_applicable(self) -> None:
        for rid in BROWNFIELD_ONLY_EXPECTED:
            self.assertNotIn(rid, self.b0["requirement_ids"], rid)
        excluded_rules = {e["id"]: e["rule"] for e in self.b0["excluded_by_applicability"]}
        for rid in BROWNFIELD_ONLY_EXPECTED:
            self.assertEqual(excluded_rules[rid], "BROWNFIELD_ONLY", rid)
        # dispatcher surfaces NOT_APPLICABLE with the deterministic rule
        result = engine.dispatch_requirement("REQ-G00-042", self.context, None, graph=self.graph, manifest=self.manifest)
        self.assertEqual(result["status"], "NOT_APPLICABLE")
        self.assertEqual(result["applicability_rule"], "BROWNFIELD_ONLY")

    def test_ambiguous_only_requirement_excluded(self) -> None:
        self.assertNotIn("REQ-G00-002", self.b0["requirement_ids"])
        rules = {e["id"]: e["rule"] for e in self.b0["excluded_by_applicability"]}
        self.assertEqual(rules["REQ-G00-002"], "START_AMBIGUOUS")

    def test_transitive_prerequisites_included(self) -> None:
        # Rev.35 declares no explicit prerequisites and no BOOTSTRAP
        # requirement is milestone-selected, so transitive additions are
        # empty — this assertion pins that derivation property explicitly.
        self.assertEqual(self.b0["transitive_prerequisites_added"], [])

    def test_autonomous_authoring_requirement_applies_to_hybrid(self) -> None:
        self.assertIn("REQ-AUTO-042", self.b0["requirement_ids"])
        # and is excluded under MANUAL context
        manual_context = dict(self.context, authoring_mode="MANUAL")
        recomputed = readiness_closure(
            {"requirements": self.graph["requirements"]},
            "B0",
            manual_context,
        )
        self.assertNotIn("REQ-AUTO-042", recomputed["requirement_ids"])

    def test_manifest_reflects_closure_membership(self) -> None:
        for rid in self.b0["requirement_ids"]:
            membership = self.manifest["requirements"][rid]["closure_membership"]
            self.assertIn("B0", membership, rid)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()