# -*- coding: utf-8 -*-
"""Package foundation tests (REQ-G00-004/008/009/020, truthful state)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT  # noqa: F401  (ensures src path bootstrap)

REQUIREMENT_IDS = (
    "REQ-G00-004",
    "REQ-G00-009",
    "REQ-G00-020",
    "REQ-P01-005",
)

import vfp_toolchain  # noqa: E402
from vfp_toolchain import capabilities as caps  # noqa: E402
from vfp_toolchain.core import CoreService  # noqa: E402
from vfp_toolchain.errors import CapabilityNotImplementedError, OperationUnknownError  # noqa: E402


class PackageFoundationTests(unittest.TestCase):
    def test_import_and_version(self) -> None:
        self.assertEqual(vfp_toolchain.__version__, "0.0.0.dev0")
        self.assertIn(".dev", vfp_toolchain.__version__)

    def test_canonical_entry_point_targets(self) -> None:
        import re
        from pathlib import Path

        text = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^vfp-toolchain\s*=\s*"vfp_toolchain\.cli:main"$')
        self.assertRegex(text, r'(?m)^mcp-vfp9sp2\s*=\s*"vfp_toolchain\.mcp:main"$')

    def test_truthful_capability_state(self) -> None:
        discovery = caps.discover()
        self.assertEqual(discovery["implemented_count"], 0)
        self.assertGreater(discovery["declared_count"], 20)
        for entry in discovery["capabilities"]:
            self.assertFalse(entry["available"])
            self.assertEqual(entry["state"], "NOT_IMPLEMENTED")

    def test_capability_discovery_side_effect_free_and_deterministic(self) -> None:
        first = caps.discover()
        second = caps.discover()
        self.assertEqual(first, second)

    def test_core_describe(self) -> None:
        core = CoreService()
        envelope = core.describe()
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(envelope["schema_version"], 1)

    def test_core_refuses_unimplemented_domain_operation(self) -> None:
        core = CoreService()
        with self.assertRaises(CapabilityNotImplementedError) as caught:
            core.execute("data.rows_read", {"dataset_id": "x"})
        self.assertEqual(caught.exception.code, "CAPABILITY_NOT_IMPLEMENTED")

    def test_core_refuses_unknown_operation(self) -> None:
        core = CoreService()
        with self.assertRaises(OperationUnknownError):
            core.execute("no.such.operation")

    def test_both_adapters_share_same_core(self) -> None:
        from vfp_toolchain import cli, mcp

        self.assertIs(cli.CoreService, mcp.CoreService)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()