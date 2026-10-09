# -*- coding: utf-8 -*-
"""Deterministic P00_DOMAIN report builders (REQ-P00-001/002/011/018).

Each builder returns a machine-readable report consumed by ``tools/verify.py``
and the portable verification manifest.  All builders fail closed:

* missing required surfaces/fixtures are findings, never silent PASS;
* the structured scanners reject promotion-shaped non-Windows support claims
  with explicit allow/exclude (negation) semantics;
* a requirement's ``current_state`` stays PLANNED in the verification manifest
  until formal deterministic verification plus independent review succeeds
  (REQ-AUTO-002/004/048) — these builders never emit requirement PASS.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from .. import domain as domain_module
from . import python_support as python_support_module
from . import support_claims as support_claims_module

_DIALECT = domain_module.TARGET_DIALECT

# Fixed negative probe evaluation embedded in the dialect report so the gate
# carries its own deterministic negative evidence.
_DIALECT_NEGATIVE_PROBE_EXPECTATION = "ALL_REJECTED_AS_NON_PRODUCT_DIALECT"


def dialect_identity_report(repo_root: Path) -> dict[str, Any]:
    """REQ-P00-001 gate: canonical dialect identity + negative rejection."""
    identity = domain_module.dialect_identity()
    checks: list[dict[str, Any]] = []
    exact_identifier = identity["dialect_identifier"] == _DIALECT
    checks.append({"id": "canonical_dialect_identifier", "status": "PASS" if exact_identifier else "FAIL", "value": identity["dialect_identifier"]})
    required_fields = {
        "product_family": "Microsoft Visual FoxPro",
        "major_version": 9,
        "service_pack_baseline": "SP2",
        "support_classification": domain_module.SUPPORT_CLASSIFICATION,
    }
    for field, expected in required_fields.items():
        checks.append({"id": f"identity_field_{field}", "status": "PASS" if identity.get(field) == expected else "FAIL", "value": identity.get(field)})
    checks.append({"id": "sole_dialect_target_declared", "status": "PASS" if identity["sole_dialect_target"] is True else "FAIL", "value": identity["sole_dialect_target"]})
    checks.append({"id": "older_release_semantics_declared", "status": "PASS" if identity["older_release_semantics"] == domain_module.OLDER_RELEASE_SEMANTICS else "FAIL", "value": identity["older_release_semantics"]})
    checks.append({"id": "older_element_relevance_rule_declared", "status": "PASS" if identity["older_element_relevance_rule"] == domain_module.OLDER_ELEMENT_RELEVANCE_RULE else "FAIL", "value": identity["older_element_relevance_rule"]})

    # Package-level single-source consistency: the package re-exports the
    # canonical constants; no duplicate literal may exist in product modules.
    sys.path.insert(0, str(repo_root / "src"))
    import vfp_toolchain

    checks.append({"id": "package_reexports_canonical_dialect", "status": "PASS" if vfp_toolchain.TARGET_DIALECT == _DIALECT else "FAIL", "value": vfp_toolchain.TARGET_DIALECT})
    duplicate_literals = _scan_duplicate_dialect_literals(repo_root)
    checks.append({"id": "no_duplicate_dialect_literals_in_product_modules", "status": "PASS" if not duplicate_literals else "FAIL", "duplicates": duplicate_literals})

    # Negative gate: every probe must classify as non-product dialect.
    rejected: list[str] = []
    wrongly_supported: list[str] = []
    for probe in domain_module.DIALECT_NEGATIVE_PROBES:
        classification = domain_module.classify_dialect_identity(probe)
        if domain_module.is_supported_product_dialect(probe):
            wrongly_supported.append(probe)
        else:
            rejected.append(classification)
    checks.append(
        {
            "id": "negative_probes_all_rejected",
            "status": "PASS" if not wrongly_supported else "FAIL",
            "probe_count": len(domain_module.DIALECT_NEGATIVE_PROBES),
            "wrongly_supported": wrongly_supported,
        }
    )
    checks.append({"id": "negative_probes_classification_set", "status": "PASS", "classifications_observed": sorted(set(rejected))})

    # Cross-surface identity consistency (compatibility manifest + README).
    compat = _load_json(repo_root / "spec" / "compatibility.manifest.json")
    checks.append(
        {
            "id": "compatibility_manifest_target_dialect",
            "status": "PASS" if isinstance(compat, dict) and compat.get("target_dialect") == _DIALECT else "FAIL",
        }
    )
    readme_path = repo_root / "README.md"
    readme_ok = readme_path.is_file() and _DIALECT in readme_path.read_text(encoding="utf-8")
    checks.append({"id": "readme_states_canonical_dialect", "status": "PASS" if readme_ok else "FAIL"})

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "report": "DIALECT_IDENTITY",
        "status": "FAIL" if failed else "PASS",
        "requirement_ids": ["REQ-P00-001"],
        "identity": identity,
        "checks": checks,
        "negative_gate": {
            "expectation": _DIALECT_NEGATIVE_PROBE_EXPECTATION,
            "rejected_probe_count": len(rejected),
        },
    }


_PRODUCT_SOURCE_SUFFIXES = (".py",)
_ALLOWED_DIALECT_LITERAL_FILES = frozenset({"src/vfp_toolchain/domain.py", "src/vfp_toolchain/__init__.py"})


def _scan_duplicate_dialect_literals(repo_root: Path) -> list[str]:
    """Any product module hardcoding the dialect literal outside the canonical
    module (and the re-export shim) is a single-source violation."""
    duplicates: list[str] = []
    src_root = repo_root / "src" / "vfp_toolchain"
    for path in sorted(src_root.rglob("*.py")):
        relative = path.relative_to(repo_root).as_posix().replace("\\", "/")
        if relative in _ALLOWED_DIALECT_LITERAL_FILES or relative.startswith("src/vfp_toolchain/verification/"):
            continue
        text = path.read_text(encoding="utf-8")
        if _DIALECT in text or re.search(r"[\"']microsoft\.visual-foxpro\.", text):
            duplicates.append(relative)
    return duplicates


def platform_policy_report(repo_root: Path) -> dict[str, Any]:
    """REQ-P00-002 gate: Windows-only production platform policy."""
    policy = domain_module.platform_policy()
    checks: list[dict[str, Any]] = []
    checks.append({"id": "production_server_windows_only", "status": "PASS" if policy["production_server_operating_systems"] == ["Windows"] and policy["windows_only"] is True else "FAIL"})
    checks.append({"id": "linux_product_support_false", "status": "PASS" if policy["linux_product_support"] is False else "FAIL"})
    checks.append({"id": "macos_product_support_false", "status": "PASS" if policy["macos_product_support"] is False else "FAIL"})
    checks.append({"id": "non_windows_execution_incidental_only", "status": "PASS" if policy["non_windows_interpreter_execution"] == "INCIDENTAL_BOOTSTRAP_ONLY_NOT_SUPPORTED" else "FAIL"})
    required_boundaries = ("packaging", "path_handling", "process_execution", "com_integration", "filesystem_safety", "test_and_support_declarations")
    boundaries = policy["boundaries"]
    checks.append(
        {
            "id": "policy_covers_all_semantic_boundaries",
            "status": "PASS" if all(name in boundaries and boundaries[name]["semantics"] == "WINDOWS_ONLY" for name in required_boundaries) else "FAIL",
            "boundaries_declared": sorted(boundaries),
        }
    )

    # CI product acceptance is Windows-only (machine-validated, no remote run).
    ci_path = repo_root / ".github" / "workflows" / "ci.yml"
    if ci_path.is_file():
        ci_text = ci_path.read_text(encoding="utf-8")
        ci_findings = support_claims_module.ci_platform_findings(".github/workflows/ci.yml", ci_text)
        checks.append({"id": "ci_runs_windows_only", "status": "PASS" if not ci_findings else "FAIL", "findings": ci_findings})
        python_matrix = support_claims_module.ci_python_matrix(".github/workflows/ci.yml", ci_text)
        expected = list(domain_module.SUPPORTED_PYTHON_MINORS)
        checks.append(
            {
                "id": "ci_python_matrix_is_canonical",
                "status": "PASS" if python_matrix is not None and sorted(python_matrix) == sorted(expected) else "FAIL",
                "matrix": python_matrix,
                "expected": expected,
            }
        )
    else:
        checks.append({"id": "ci_runs_windows_only", "status": "FAIL", "findings": ["ci.yml missing"]})

    # Compatibility manifest is the canonical platform/support manifest.
    compat = _load_json(repo_root / "spec" / "compatibility.manifest.json")
    if isinstance(compat, dict):
        findings = support_claims_module.compatibility_manifest_findings("spec/compatibility.manifest.json", compat)
        checks.append({"id": "compatibility_manifest_windows_only", "status": "PASS" if not findings else "FAIL", "findings": findings})
    else:
        checks.append({"id": "compatibility_manifest_windows_only", "status": "FAIL", "findings": ["manifest missing or malformed"]})

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "report": "WINDOWS_PLATFORM_POLICY",
        "status": "FAIL" if failed else "PASS",
        "requirement_ids": ["REQ-P00-002"],
        "policy": policy,
        "checks": checks,
    }


def python_support_report(repo_root: Path) -> dict[str, Any]:
    """REQ-P00-011 gate: supported-Python range consistency across surfaces."""
    surfaces = python_support_module.collect_surface_texts(repo_root)
    findings = python_support_module.check_python_support(**surfaces)
    report: dict[str, Any] = {
        "report": "PYTHON_SUPPORT_CONTRACT",
        "status": "FAIL" if findings else "PASS",
        "requirement_ids": ["REQ-P00-011"],
        "canonical_range": python_support_module.CANONICAL_PYTHON_RANGE,
        "canonical_minors": list(python_support_module.CANONICAL_PYTHON_MINORS),
        "findings": findings,
        "clean_environment_acceptance": {
            "note": (
                "REQ-P00-011 PASS additionally requires executed clean-environment "
                "acceptance evidence for Python 3.10, 3.11, 3.12, 3.13 and 3.14 "
                "(tools/clean_env_smoke.py); a missing interpreter is a typed "
                "host-prerequisite blocker, never a skipped check."
            ),
            "tool": "tools/clean_env_smoke.py",
            "required_minors": list(python_support_module.CANONICAL_PYTHON_MINORS),
        },
    }
    return report


def support_claims_report(repo_root: Path) -> dict[str, Any]:
    """REQ-P00-018 gate: Windows-only support-claims enforcement."""
    scan = support_claims_module.scan_support_claims(repo_root)
    scan["report"] = "SUPPORT_CLAIMS_VERIFIER"
    scan["requirement_ids"] = ["REQ-P00-018"]
    return scan


def _load_json(path: Path) -> Any:
    import json

    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
