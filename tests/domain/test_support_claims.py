# -*- coding: utf-8 -*-
"""REQ-P00-018: deterministic support-claims verifier + negative fixtures.

Full-scan evidence over a version-controlled fixture tree:
* positive control: a Windows-only tree passes the default scan;
* negative fixtures: deliberate Linux/macOS support claims, a Linux CI
  matrix, a misleading cross-platform production statement, an OS-Independent
  classifier, and a non-Windows OS-scope value in a release-gate manifest are
  all rejected;
* allow/exclude semantics: explicit unsupported statements are never findings;
* fail closed: a missing required surface is a finding, never a silent PASS.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-P00-018",
    "REQ-P00-002",
    "REQ-AUTO-004",
    "REQ-AUTO-009",
)

from vfp_toolchain.verification import engine, support_claims  # noqa: E402

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "support_claims" / "good_tree"


class SupportClaimsVerifierTests(unittest.TestCase):
    def test_positive_control_fixture_tree_passes(self) -> None:
        report = support_claims.scan_support_claims(FIXTURE_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["checks"]["readme_windows_only_statement"])
        self.assertTrue(report["checks"]["docs_windows_only_statement"])

    def test_real_repository_passes(self) -> None:
        report = engine.support_claims_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["requirement_ids"], ["REQ-P00-018"])

    def _variant(self, mutation) -> Path:
        temp_root = Path(tempfile.mkdtemp(prefix="vfp-support-claims-fixture-"))
        self.addCleanup(shutil.rmtree, temp_root, ignore_errors=True)
        shutil.copytree(FIXTURE_ROOT, temp_root / "tree")
        tree = temp_root / "tree"
        mutation(tree)
        return tree

    def _scan_variant(self, mutation) -> dict:
        return support_claims.scan_support_claims(self._variant(mutation))

    def _assert_single_finding(self, report: dict, check: str) -> None:
        self.assertEqual(report["status"], "FAIL", report)
        self.assertTrue(any(f["check"] == check for f in report["findings"]), report)

    # -- negative fixtures -------------------------------------------------

    def test_negative_linux_support_claim_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            readme = tree / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nThis product fully supports Linux servers.\n", encoding="utf-8")

        self._assert_single_finding(self._scan_variant(mutate), "non_windows_support_claim")

    def test_negative_macos_support_claim_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            readme = tree / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nmacOS is a supported production platform.\n", encoding="utf-8")

        self._assert_single_finding(self._scan_variant(mutate), "non_windows_support_claim")

    def test_negative_linux_ci_matrix_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            workflow = tree / ".github" / "workflows" / "ci.yml"
            workflow.write_text(
                "name: ci\non: [push]\njobs:\n  lint:\n    runs-on: ubuntu-latest\n", encoding="utf-8"
            )

        report = self._scan_variant(mutate)
        self.assertEqual(report["status"], "FAIL", report)
        self.assertTrue(any(f["check"] in ("forbidden_ci_runner", "non_windows_ci_runner") for f in report["findings"]), report)

    def test_negative_misleading_cross_platform_statement_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            readme = tree / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nDeployment is fully cross-platform in production.\n", encoding="utf-8")

        self._assert_single_finding(self._scan_variant(mutate), "non_windows_support_claim")

    def test_negative_os_independent_classifier_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            pyproject = tree / "pyproject.toml"
            text = pyproject.read_text(encoding="utf-8").replace(
                '"Operating System :: Microsoft :: Windows",',
                '"Operating System :: Microsoft :: Windows",\n  "Operating System :: OS Independent",',
            )
            pyproject.write_text(text, encoding="utf-8")

        self._assert_single_finding(self._scan_variant(mutate), "forbidden_os_classifier")

    def test_negative_release_gate_non_windows_os_scope_rejected(self) -> None:
        def mutate(tree: Path) -> None:
            gate = tree / "release-gates" / "sample-gate.json"
            gate.write_text(json.dumps({"runs_on": "ubuntu-latest", "gate": "fixture"}), encoding="utf-8")

        self._assert_single_finding(self._scan_variant(mutate), "forbidden_os_scope_value")

    def test_negative_missing_required_surface_fails_closed(self) -> None:
        def mutate(tree: Path) -> None:
            (tree / "README.md").unlink()

        report = self._scan_variant(mutate)
        self.assertEqual(report["status"], "FAIL", report)
        self.assertTrue(any(f["check"] == "required_surface_missing" for f in report["findings"]), report)

    def test_negative_windows_only_statement_removed_fails_closed(self) -> None:
        def mutate(tree: Path) -> None:
            readme = tree / "README.md"
            readme.write_text(
                "This product runs on Linux, Windows, and macOS.\n", encoding="utf-8"
            )

        report = self._scan_variant(mutate)
        self.assertEqual(report["status"], "FAIL", report)
        self.assertTrue(any(f["check"] == "windows_only_statement_missing" for f in report["findings"]), report)
        self.assertTrue(any(f["check"] == "non_windows_support_claim" for f in report["findings"]), report)

    # -- allow/exclude semantics -------------------------------------------

    def test_negated_platform_statements_are_never_findings(self) -> None:
        self.assertEqual(
            support_claims.text_surface_findings(
                "README.md",
                "Linux is unsupported.\nmacOS is not a supported product platform.\n"
                "We do not support Linux. There is no macOS support.\n",
            ),
            [],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
