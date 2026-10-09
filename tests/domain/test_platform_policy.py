# -*- coding: utf-8 -*-
"""REQ-P00-002: Windows-only production platform policy gate.

Deterministic evidence:
* canonical machine-readable platform policy covering packaging, path
  handling, process execution, COM integration, filesystem safety, and
  test/support declarations;
* package metadata conveys Windows support;
* operator-facing documentation states Windows-only product support;
* CI product acceptance has no Linux/macOS product jobs;
* negative fixtures: forbidden OS classifiers and non-Windows CI runners are
  detected as policy violations.
"""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-P00-002",
    "REQ-G00-005",
    "REQ-G00-016",
    "REQ-G00-017",
)

import vfp_toolchain  # noqa: E402
from vfp_toolchain import domain  # noqa: E402
from vfp_toolchain.verification import engine, support_claims  # noqa: E402


class WindowsPlatformPolicyTests(unittest.TestCase):
    def test_canonical_policy_machine_readable(self) -> None:
        policy = domain.platform_policy()
        self.assertEqual(policy["production_server_operating_systems"], ["Windows"])
        self.assertIs(policy["windows_only"], True)
        self.assertIs(policy["linux_product_support"], False)
        self.assertIs(policy["macos_product_support"], False)
        self.assertIs(policy["non_windows_product_support"], False)
        self.assertEqual(policy["non_windows_interpreter_execution"], "INCIDENTAL_BOOTSTRAP_ONLY_NOT_SUPPORTED")
        self.assertEqual(policy["target_dialect"], "microsoft.visual-foxpro.9.0.sp2")

    def test_policy_covers_all_semantic_boundaries(self) -> None:
        boundaries = domain.platform_policy()["boundaries"]
        for name in (
            "packaging",
            "path_handling",
            "process_execution",
            "com_integration",
            "filesystem_safety",
            "test_and_support_declarations",
        ):
            self.assertIn(name, boundaries)
            self.assertEqual(boundaries[name]["semantics"], "WINDOWS_ONLY", name)

    def test_policy_deterministic(self) -> None:
        self.assertEqual(domain.platform_policy(), domain.platform_policy())
        self.assertEqual(vfp_toolchain.domain.platform_policy(), domain.platform_policy())

    def test_package_metadata_conveys_windows_support(self) -> None:
        pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('  "Environment :: Win32 (MS Windows)"', pyproject_text)
        self.assertIn('  "Operating System :: Microsoft :: Windows"', pyproject_text)
        for forbidden in ("POSIX", "Linux", "MacOS", "OS Independent"):
            self.assertNotIn(f'Operating System :: {forbidden}', pyproject_text)

    def test_documentation_states_windows_only_product_support(self) -> None:
        readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(readme_text, r"(?i)windows[-\s]only")
        support_doc = REPO_ROOT / "docs" / "support.md"
        self.assertTrue(support_doc.is_file(), "docs/support.md (installation/support/troubleshooting) must exist")
        self.assertRegex(support_doc.read_text(encoding="utf-8"), r"(?i)windows[-\s]only")

    def test_report_passes_on_candidate_tree(self) -> None:
        report = engine.platform_policy_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        for check in report["checks"]:
            self.assertEqual(check["status"], "PASS", check)

    # -- negative fixtures -------------------------------------------------

    def test_negative_forbidden_os_classifier_detected(self) -> None:
        bad_pyproject = (
            '[project]\nname = "x"\nclassifiers = [\n  "Operating System :: Microsoft :: Windows",\n'
            '  "Operating System :: POSIX :: Linux",\n]\n'
        )
        findings = support_claims.pyproject_classifier_findings("pyproject.toml", bad_pyproject)
        self.assertTrue(any(f["check"] == "forbidden_os_classifier" for f in findings), findings)

    def test_negative_os_independent_classifier_detected(self) -> None:
        bad_pyproject = '[project]\nclassifiers = [\n  "Operating System :: OS Independent",\n]\n'
        findings = support_claims.pyproject_classifier_findings("pyproject.toml", bad_pyproject)
        self.assertTrue(any(f["check"] == "forbidden_os_classifier" for f in findings), findings)

    def test_negative_windows_classifier_missing_detected(self) -> None:
        bad_pyproject = '[project]\nclassifiers = [\n  "Programming Language :: Python :: 3",\n]\n'
        findings = support_claims.pyproject_classifier_findings("pyproject.toml", bad_pyproject)
        self.assertTrue(any(f["check"] == "windows_classifier_missing" for f in findings), findings)

    def test_negative_linux_ci_runner_detected(self) -> None:
        bad_ci = (
            "jobs:\n  contract:\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n"
            '        python: ["3.10", "3.11", "3.12", "3.13", "3.14"]\n'
        )
        findings = support_claims.ci_platform_findings("ci.yml", bad_ci)
        self.assertTrue(any(f["check"] == "forbidden_ci_runner" for f in findings), findings)

    def test_negative_macos_ci_runner_detected(self) -> None:
        bad_ci = "jobs:\n  contract:\n    runs-on: macos-latest\n"
        findings = support_claims.ci_platform_findings("ci.yml", bad_ci)
        self.assertTrue(any(f["check"] == "forbidden_ci_runner" for f in findings), findings)

    def test_negative_misleading_cross_platform_statement_detected(self) -> None:
        bad_readme = "Deployment\n==========\n\nThe toolchain is fully cross-platform.\n"
        findings = support_claims.text_surface_findings("README.md", bad_readme)
        self.assertTrue(any(f["check"] == "non_windows_support_claim" for f in findings), findings)

    def test_negative_linux_support_claim_detected(self) -> None:
        bad_readme = "Support\n-------\n\nThis product fully supports Linux servers.\n"
        findings = support_claims.text_surface_findings("README.md", bad_readme)
        self.assertTrue(any(f["check"] == "non_windows_support_claim" for f in findings), findings)

    def test_negative_macos_support_claim_detected(self) -> None:
        bad_readme = "Support\n-------\n\nmacOS is a supported production platform.\n"
        findings = support_claims.text_surface_findings("README.md", bad_readme)
        self.assertTrue(any(f["check"] == "non_windows_support_claim" for f in findings), findings)

    # -- allow/exclude semantics (no false positives) ----------------------

    def test_negated_linux_statement_is_not_a_finding(self) -> None:
        good_readme = "Support\n-------\n\nLinux is not supported. macOS is not supported as a product platform.\n"
        self.assertEqual(support_claims.text_surface_findings("README.md", good_readme), [])

    def test_negated_unsupported_statement_is_not_a_finding(self) -> None:
        good_readme = "The product targets Windows only; Linux/macOS are unsupported product platforms.\n"
        self.assertEqual(support_claims.text_surface_findings("README.md", good_readme), [])

    def test_structured_non_windows_os_scope_detected(self) -> None:
        bad = {"supported_operating_systems": ["Windows", "Linux"]}
        findings = support_claims.structured_os_scope_findings("manifest.json", bad)
        self.assertTrue(any(f["check"] == "forbidden_os_scope_value" for f in findings), findings)

    def test_structured_windows_only_os_scope_allowed(self) -> None:
        self.assertEqual(support_claims.structured_os_scope_findings("manifest.json", {"runs_on": "windows-latest"}), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
