# -*- coding: utf-8 -*-
"""REQ-P00-011: supported-Python range contract gate + negative fixtures.

Deterministic evidence:
* the canonical range ``>=3.10,<3.15`` is consistent across pyproject.toml,
  compatibility manifest, dependency lock, CI configuration, documentation,
  and package runtime reporting;
* negative fixtures: ranges below 3.10 or including 3.15, manifest range
  mismatches, CI matrix omissions, and unsupported-version inclusions are
  rejected.
"""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-P00-011",
    "REQ-G00-025",
    "REQ-P00-016",
)

import vfp_toolchain  # noqa: E402
from vfp_toolchain import domain  # noqa: E402
from vfp_toolchain.verification import engine, python_support  # noqa: E402

CANONICAL_RANGE = ">=3.10,<3.15"
CANONICAL_MINORS = ["3.10", "3.11", "3.12", "3.13", "3.14"]


class PythonSupportContractTests(unittest.TestCase):
    def test_canonical_runtime_contract(self) -> None:
        self.assertEqual(vfp_toolchain.SUPPORTED_PYTHON_RANGE, CANONICAL_RANGE)
        self.assertEqual(domain.SUPPORTED_PYTHON_RANGE, CANONICAL_RANGE)
        contract = domain.python_support()
        self.assertEqual(contract["supported_python_range"], CANONICAL_RANGE)
        self.assertEqual(contract["supported_python_minors"], CANONICAL_MINORS)
        self.assertIs(contract["python_315_supported"], False)
        self.assertIs(contract["python_below_310_supported"], False)

    def test_pyproject_pins_canonical_range(self) -> None:
        pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(python_support.pyproject_range_findings(pyproject_text), [])

    def test_ci_matrix_is_canonical(self) -> None:
        ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertEqual(python_support.ci_python_matrix_findings(ci_text), [])

    def test_manifests_and_lock_pin_canonical_range(self) -> None:
        import json

        compat = json.loads((REPO_ROOT / "spec" / "compatibility.manifest.json").read_text(encoding="utf-8"))
        lock = json.loads((REPO_ROOT / "spec" / "dependency-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(python_support.compat_manifest_range_findings(compat), [])
        self.assertEqual(python_support.dependency_lock_range_findings(lock), [])

    def test_readme_states_canonical_range(self) -> None:
        readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(python_support.readme_range_findings(readme_text), [])

    def test_report_passes_on_candidate_tree(self) -> None:
        report = engine.python_support_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["clean_environment_acceptance"]["required_minors"], CANONICAL_MINORS)

    # -- negative fixtures -------------------------------------------------

    def test_negative_requires_python_below_310_rejected(self) -> None:
        bad = 'requires-python = ">=3.9,<3.15"'
        findings = python_support.pyproject_range_findings(bad)
        self.assertTrue(any(f["check"] == "pyproject_requires_python_mismatch" for f in findings), findings)

    def test_negative_requires_python_including_315_rejected(self) -> None:
        bad = 'requires-python = ">=3.10,<3.16"'
        findings = python_support.pyproject_range_findings(bad)
        self.assertTrue(any(f["check"] == "pyproject_requires_python_mismatch" for f in findings), findings)

    def test_negative_requires_python_missing_rejected(self) -> None:
        findings = python_support.pyproject_range_findings('[project]\nname = "x"\n')
        self.assertTrue(any(f["check"] == "pyproject_requires_python_missing" for f in findings), findings)

    def test_negative_compat_manifest_range_mismatch_rejected(self) -> None:
        findings = python_support.compat_manifest_range_findings({"supported_python_range": ">=3.10,<3.14"})
        self.assertTrue(any(f["check"] == "compatibility_manifest_range_mismatch" for f in findings), findings)

    def test_negative_dependency_lock_range_mismatch_rejected(self) -> None:
        findings = python_support.dependency_lock_range_findings({"python_range": ">=3.11,<3.15"})
        self.assertTrue(any(f["check"] == "dependency_lock_range_mismatch" for f in findings), findings)

    def test_negative_ci_matrix_omission_rejected(self) -> None:
        bad_ci = 'matrix:\n  python: ["3.10", "3.12", "3.13", "3.14"]\n'
        findings = python_support.ci_python_matrix_findings(bad_ci)
        self.assertTrue(any(f["check"] == "ci_python_matrix_mismatch" for f in findings), findings)

    def test_negative_ci_matrix_unsupported_version_inclusion_rejected(self) -> None:
        bad_ci = 'matrix:\n  python: ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]\n'
        findings = python_support.ci_python_matrix_findings(bad_ci)
        self.assertTrue(any(f["check"] == "ci_python_matrix_mismatch" for f in findings), findings)

    def test_negative_ci_matrix_315_inclusion_rejected(self) -> None:
        bad_ci = 'matrix:\n  python: ["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"]\n'
        findings = python_support.ci_python_matrix_findings(bad_ci)
        self.assertTrue(any(f["check"] == "ci_python_matrix_mismatch" for f in findings), findings)

    def test_negative_runtime_range_mismatch_rejected(self) -> None:
        findings = python_support.runtime_range_findings(">=3.10,<3.16", CANONICAL_MINORS)
        self.assertTrue(any(f["check"] == "runtime_python_range_mismatch" for f in findings), findings)

    def test_negative_missing_surface_fails_closed(self) -> None:
        findings = python_support.check_python_support(
            pyproject_text=None,
            ci_text=None,
            compat_manifest=None,
            dependency_lock=None,
            readme_text=None,
            runtime_range=CANONICAL_RANGE,
            runtime_minors=CANONICAL_MINORS,
        )
        missing = [f for f in findings if f["check"] == "surface_missing"]
        self.assertEqual(len(missing), 5, findings)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
