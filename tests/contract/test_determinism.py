# -*- coding: utf-8 -*-
"""Control-plane determinism tests (REQ-PORT-017/018, REQ-AUTO-038)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-PORT-017",
    "REQ-PORT-018",
    "REQ-AUTO-038",
)


class DeterminismTests(unittest.TestCase):
    def test_double_generation_logical_identity(self) -> None:
        from vfp_toolchain.verification import engine

        report = engine.determinism_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)

    def test_generated_artifacts_carry_non_authoritative_timestamp(self) -> None:
        import json

        graph = json.loads((REPO_ROOT / "spec" / "requirements.graph.json").read_text(encoding="utf-8"))
        self.assertIn("generated_at_utc", graph)
        # the timestamp must be excluded from the logical hash
        content_without_ts = {k: v for k, v in graph.items() if k != "generated_at_utc" and k != "content_sha256"}
        from vfp_toolchain.canonical import canonical_sha256, strip_logical_metadata

        self.assertEqual(canonical_sha256(strip_logical_metadata(content_without_ts)), graph["content_sha256"])

    def test_logical_hash_ignores_key_order(self) -> None:
        import json

        from vfp_toolchain.canonical import canonical_sha256

        graph = json.loads((REPO_ROOT / "spec" / "requirements.graph.json").read_text(encoding="utf-8"))
        reordered = dict(reversed(list(graph.items())))
        stripped_a = {k: v for k, v in graph.items() if k not in ("generated_at_utc", "content_sha256")}
        stripped_b = {k: v for k, v in reordered.items() if k not in ("generated_at_utc", "content_sha256")}
        self.assertEqual(canonical_sha256(stripped_a), canonical_sha256(stripped_b))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()