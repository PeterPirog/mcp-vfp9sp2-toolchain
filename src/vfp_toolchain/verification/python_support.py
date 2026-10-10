# -*- coding: utf-8 -*-
"""Deterministic supported-Python contract verifier (REQ-P00-011).

Proves consistency of the canonical supported Python range ``>=3.10,<3.15``
across every product surface that declares it:

* ``pyproject.toml`` (``requires-python`` + per-minor classifiers);
* the canonical compatibility manifest (``supported_python_range``);
* the canonical dependency lock (``python_range``);
* CI configuration (the product Python matrix);
* operator-facing documentation (README);
* package runtime reporting (``vfp_toolchain.SUPPORTED_PYTHON_RANGE`` and
  ``vfp_toolchain.domain.python_support()``).

The range is never broadened to 3.15 and never narrowed below 3.10; any
surface disagreement is a finding (fail closed).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .. import SUPPORTED_PYTHON_MINORS, SUPPORTED_PYTHON_RANGE

CANONICAL_PYTHON_RANGE = ">=3.10,<3.15"
CANONICAL_PYTHON_MINORS: tuple[str, ...] = ("3.10", "3.11", "3.12", "3.13", "3.14")

_RANGE_RE = re.compile(r">=\s*3\.10\s*,\s*<\s*3\.15")
_CLASSIFIER_RE = re.compile(r"^Programming Language :: Python :: (\d+\.\d+)$")


def _finding(check: str, detail: str) -> dict[str, Any]:
    return {"check": check, "detail": detail}


def pyproject_range_findings(pyproject_text: str) -> list[dict[str, Any]]:
    """pyproject.toml must pin exactly the canonical range and minors."""
    findings: list[dict[str, Any]] = []
    match = re.search(r'(?m)^requires-python\s*=\s*"([^"]+)"\s*$', pyproject_text)
    declared = match.group(1) if match else None
    if declared is None:
        findings.append(_finding("pyproject_requires_python_missing", "requires-python declaration not found"))
    elif declared.strip() != CANONICAL_PYTHON_RANGE:
        findings.append(_finding("pyproject_requires_python_mismatch", f"requires-python={declared!r} != canonical {CANONICAL_PYTHON_RANGE!r}"))
    classifier_match = re.search(r"^classifiers\s*=\s*\[(.*?)\]", pyproject_text, re.MULTILINE | re.DOTALL)
    if classifier_match is None:
        findings.append(_finding("pyproject_classifiers_missing", "classifiers declaration not found"))
        return findings
    minors: list[str] = []
    for classifier in re.findall(r'"([^"]+)"', classifier_match.group(1)):
        match = _CLASSIFIER_RE.match(classifier.strip().strip('"'))
        if match:
            minors.append(match.group(1))
    minors.sort()
    if tuple(minors) != CANONICAL_PYTHON_MINORS:
        findings.append(
            _finding(
                "pyproject_python_classifiers_mismatch",
                f"classifier minors={minors!r} != canonical {list(CANONICAL_PYTHON_MINORS)!r}",
            )
        )
    return findings


def ci_python_matrix_findings(ci_text: str) -> list[dict[str, Any]]:
    """The CI product matrix must be exactly the five canonical minors."""
    findings: list[dict[str, Any]] = []
    match = re.search(r"(?ms)^\s*python:\s*\[([^\]]*)\]", ci_text)
    if match is None:
        findings.append(_finding("ci_python_matrix_missing", "no python matrix declared in CI workflow"))
        return findings
    versions = re.findall(r'"([^"]+)"', match.group(1))
    if sorted(versions) != sorted(CANONICAL_PYTHON_MINORS):
        findings.append(_finding("ci_python_matrix_mismatch", f"CI python matrix={versions!r} != canonical {list(CANONICAL_PYTHON_MINORS)!r}"))
    return findings


def compat_manifest_range_findings(compat_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    declared = compat_manifest.get("supported_python_range")
    if declared != CANONICAL_PYTHON_RANGE:
        return [_finding("compatibility_manifest_range_mismatch", f"supported_python_range={declared!r} != canonical {CANONICAL_PYTHON_RANGE!r}")]
    return []


def dependency_lock_range_findings(lock: dict[str, Any]) -> list[dict[str, Any]]:
    declared = lock.get("python_range")
    if declared != CANONICAL_PYTHON_RANGE:
        return [_finding("dependency_lock_range_mismatch", f"python_range={declared!r} != canonical {CANONICAL_PYTHON_RANGE!r}")]
    return []


def runtime_range_findings(runtime_range: str | None, runtime_minors: list[str] | None) -> list[dict[str, Any]]:
    """Package runtime reporting must expose the canonical contract."""
    findings: list[dict[str, Any]] = []
    if runtime_range != CANONICAL_PYTHON_RANGE:
        findings.append(_finding("runtime_python_range_mismatch", f"vfp_toolchain.SUPPORTED_PYTHON_RANGE={runtime_range!r} != canonical {CANONICAL_PYTHON_RANGE!r}"))
    if tuple(runtime_minors or ()) != CANONICAL_PYTHON_MINORS:
        findings.append(_finding("runtime_python_minors_mismatch", f"runtime minors={runtime_minors!r} != canonical {list(CANONICAL_PYTHON_MINORS)!r}"))
    return findings


def readme_range_findings(readme_text: str) -> list[dict[str, Any]]:
    """Operator-facing documentation must state the canonical range."""
    if _RANGE_RE.search(readme_text):
        return []
    return [_finding("readme_python_range_missing", f"README does not state the canonical range {CANONICAL_PYTHON_RANGE!r}")]


def check_python_support(
    *,
    pyproject_text: str | None,
    ci_text: str | None,
    compat_manifest: dict[str, Any] | None,
    dependency_lock: dict[str, Any] | None,
    readme_text: str | None,
    runtime_range: str | None,
    runtime_minors: list[str] | None,
) -> list[dict[str, Any]]:
    """Aggregate consistency findings; a missing surface is a finding (fail closed)."""
    findings: list[dict[str, Any]] = []
    if pyproject_text is None:
        findings.append(_finding("surface_missing", "pyproject.toml not found"))
    else:
        findings.extend(pyproject_range_findings(pyproject_text))
    if ci_text is None:
        findings.append(_finding("surface_missing", "CI workflow .github/workflows/ci.yml not found"))
    else:
        findings.extend(ci_python_matrix_findings(ci_text))
    if compat_manifest is None:
        findings.append(_finding("surface_missing", "spec/compatibility.manifest.json not found"))
    else:
        findings.extend(compat_manifest_range_findings(compat_manifest))
    if dependency_lock is None:
        findings.append(_finding("surface_missing", "spec/dependency-lock.json not found"))
    else:
        findings.extend(dependency_lock_range_findings(dependency_lock))
    if readme_text is None:
        findings.append(_finding("surface_missing", "README.md not found"))
    else:
        findings.extend(readme_range_findings(readme_text))
    findings.extend(runtime_range_findings(runtime_range, runtime_minors))
    return findings


def collect_surface_texts(repo_root: Path) -> dict[str, Any]:
    """Load the real repository surfaces for the aggregated check."""
    def _read(relative: str) -> str | None:
        path = repo_root / relative
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def _load_json(relative: str) -> dict[str, Any] | None:
        import json

        path = repo_root / relative
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    return {
        "pyproject_text": _read("pyproject.toml"),
        "ci_text": _read(".github/workflows/ci.yml"),
        "compat_manifest": _load_json("spec/compatibility.manifest.json"),
        "dependency_lock": _load_json("spec/dependency-lock.json"),
        "readme_text": _read("README.md"),
        "runtime_range": SUPPORTED_PYTHON_RANGE,
        "runtime_minors": list(SUPPORTED_PYTHON_MINORS),
    }
