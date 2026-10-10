# -*- coding: utf-8 -*-
"""Deterministic support-claims verifier (REQ-P00-002 / REQ-P00-018).

Scans version-controlled product surfaces and proves that:

* product runtime support is Windows-only;
* product CI acceptance is Windows-only (no Linux/macOS product jobs);
* release qualification support scope is Windows-only;
* documentation does not claim Linux/macOS product support;
* incidental non-Windows bootstrap/tool behavior is never promoted to
  supported product behavior.

Explicit allow/exclude semantics: text that merely states a platform is
UNSUPPORTED (e.g. "Linux is unsupported", "macOS is not a supported product
platform") is never a finding.  Only promotion-shaped statements are findings.

The scanner is fail closed: a missing required surface file is a finding
(never a silent PASS), and the default surface specification covers the
complete product surface set.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Promotion-shaped patterns: a match is a suspected non-Windows support
# claim.  Evaluated line by line; a line containing any NEGATION pattern is
# treated as an explicit unsupported statement (allowed, excluded from
# findings) rather than a promotion.
# ----------------------------------------------------------------------

_PROMOTION_OS_VERB = re.compile(
    r"(?i)\b(?:"
    r"support(?:s|ed|ing)?|"
    r"tested\s+on|"
    r"works?\s+on|"
    r"runs?\s+on|"
    r"install(?:s|ed)?\s+on|"
    r"available\s+on|"
    r"compatible\s+with|"
    r"targets?|"
    r"deploy(?:s|ed)?\s+to|"
    r"validated\s+on"
    r")\b[^\n]{0,64}?\b(?:linux|macos|mac\s+os\s+x|os\s+x|unix|posix|darwin)\b"
)
_PROMOTION_OS_SUBJECT = re.compile(
    r"(?i)\b(?:linux|macos|mac\s+os\s+x|os\s+x|unix|posix|darwin)\b[^\n]{0,64}?"
    r"\b(?:support(?:s|ed|ing)?|platform|target|release|build|production|deployment|server)\b"
)
_PROMOTION_CROSS_PLATFORM = re.compile(r"(?i)\bcross[-\s]?platform\b")
_PROMOTION_OS_INDEPENDENT = re.compile(r"(?i)\bOS\s+Independent\b")
_PROMOTION_MULTI_OS_LIST = re.compile(
    r"(?i)\b(?:windows|win32|win64)\b[^\n]{0,48}\b(?:and|or|/|,)\s*(?:linux|macos|mac\s+os\s+x|unix|posix)\b"
)

PROMOTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    _PROMOTION_OS_VERB,
    _PROMOTION_OS_SUBJECT,
    _PROMOTION_CROSS_PLATFORM,
    _PROMOTION_OS_INDEPENDENT,
    _PROMOTION_MULTI_OS_LIST,
)

# Explicit negation/unsupported-statement cues: any match in the same scanned
# line excludes that line from findings (allow semantics, REQ-P00-018).
NEGATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(?:not|no|never|non-?|without|neither|nor|cannot|can(?:'t|not)|refus\w+|excluded)\b"),
    re.compile(r"(?i)\bunsupported\b"),
    re.compile(r"(?i)\b(?:isn't|aren't|won't|doesn't|don't)\b"),
    re.compile(r"(?i)\b(?:only|solely|exclusively)\s+(?:on\s+)?windows\b"),
    re.compile(r"(?i)\bwindows[-\s]only\b"),
)

# Forbidden packaging classifiers (any occurrence is a promotion claim).
FORBIDDEN_CLASSIFIER_SUBSTRINGS: tuple[str, ...] = (
    "POSIX",
    "Linux",
    "MacOS",
    "OS Independent",
    "OS/2",
    "Solaris",
)
REQUIRED_WINDOWS_CLASSIFIER = "Operating System :: Microsoft :: Windows"

# CI runner tokens that constitute non-Windows product CI acceptance.
FORBIDDEN_CI_RUNNER_TOKENS: tuple[str, ...] = (
    "ubuntu",
    "macos",
    "macos-latest",
    "linux",
    "self-hosted",
    "debian",
    "fedora",
)

# Structured-JSON keys whose values declare operating-system scope.
OS_SCOPE_KEYS = frozenset(
    {
        "runs_on",
        "runs-on",
        "operating_systems",
        "supported_operating_systems",
        "os",
        "platform",
        "platforms",
        "supported_platforms",
    }
)

# ----------------------------------------------------------------------
# Default product surface specification (the real repository).  Every
# surface is REQUIRED; a missing required surface is a finding (fail closed,
# REQ-AUTO-004 missing-fixture semantics).
# ----------------------------------------------------------------------

DEFAULT_SURFACE_SPEC: tuple[dict[str, Any], ...] = (
    {"kind": "file_text", "path": "README.md", "required": True},
    {"kind": "file_text", "path": "pyproject.toml", "required": True},
    {"kind": "glob_text", "path": "docs/*.md", "required": True, "min_count": 1},
    {"kind": "glob_text", "path": ".github/workflows/*.yml", "required": True, "min_count": 1},
    {"kind": "glob_json", "path": "release-gates/*.json", "required": True, "min_count": 1},
    {"kind": "json_surface", "path": "spec/compatibility.manifest.json", "required": True},
)

# Required affirmative Windows-only statements.  The README must state the
# Windows-only product support explicitly; at least one documentation file
# must carry the installation/support Windows statement.
REQUIRED_README_STATEMENT = re.compile(r"(?i)\bwindows[-\s]only\b")
REQUIRED_DOC_STATEMENT = re.compile(r"(?i)\bwindows[-\s]only\b")

_TEXT_EXTENSIONS = {".md", ".toml", ".yml", ".yaml", ".txt"}


def _finding(surface: str, check: str, detail: str, line_no: int | None = None, text: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"surface": surface, "check": check, "detail": detail}
    if line_no is not None:
        entry["line"] = line_no
    if text is not None:
        entry["text"] = text
    return entry


def _line_is_negated(line: str) -> bool:
    return any(pattern.search(line) for pattern in NEGATION_PATTERNS)


# ----------------------------------------------------------------------
# Pure text/structure checks (unit-testable without a repository tree).
# ----------------------------------------------------------------------


def text_surface_findings(surface: str, text: str) -> list[dict[str, Any]]:
    """Find promotion-shaped non-Windows support claims in a text surface."""
    findings: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _line_is_negated(line):
            continue
        for pattern in PROMOTION_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(
                    _finding(surface, "non_windows_support_claim", "promotion-shaped non-Windows support statement", line_no, line.strip())
                )
                break
    return findings


def pyproject_classifier_findings(surface: str, pyproject_text: str) -> list[dict[str, Any]]:
    """Packaging metadata must declare Windows and never POSIX/macOS/OS-independent."""
    findings: list[dict[str, Any]] = []
    classifier_match = re.search(r"^classifiers\s*=\s*\[(.*?)\]", pyproject_text, re.MULTILINE | re.DOTALL)
    if classifier_match is None:
        findings.append(_finding(surface, "classifiers_block_missing", "no classifiers declaration found"))
        return findings
    classifiers = re.findall(r'"([^"]+)"', classifier_match.group(1))
    for classifier in classifiers:
        for forbidden in FORBIDDEN_CLASSIFIER_SUBSTRINGS:
            if forbidden.lower() in classifier.lower():
                findings.append(_finding(surface, "forbidden_os_classifier", f"forbidden classifier: {classifier}"))
    if not any(classifier == REQUIRED_WINDOWS_CLASSIFIER for classifier in classifiers):
        findings.append(_finding(surface, "windows_classifier_missing", f"required classifier absent: {REQUIRED_WINDOWS_CLASSIFIER}"))
    return findings


def required_statement_findings(surface: str, text: str, statement: re.Pattern[str], check: str) -> list[dict[str, Any]]:
    if statement.search(text):
        return []
    return [_finding(surface, check, "required Windows-only support statement absent")]


def ci_platform_findings(surface: str, ci_text: str) -> list[dict[str, Any]]:
    """CI acceptance must be Windows-only: every runs-on must be a Windows runner."""
    findings: list[dict[str, Any]] = []
    runs_on = re.findall(r"(?m)^\s*runs-on:\s*(.+?)\s*$", ci_text)
    if not runs_on:
        findings.append(_finding(surface, "ci_runs_on_missing", "no runs-on declaration found in CI workflow"))
    for entry in runs_on:
        lowered = entry.lower()
        for token in FORBIDDEN_CI_RUNNER_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                findings.append(_finding(surface, "forbidden_ci_runner", f"non-Windows CI runner declared: {entry}"))
        if not re.search(r"\bwindows[\w.-]*", lowered):
            findings.append(_finding(surface, "non_windows_ci_runner", f"runs-on does not declare a Windows runner: {entry}"))
    # Matrix-level OS declarations (e.g. os: [ubuntu-latest]).
    for match in re.finditer(r"(?im)^\s*os:\s*\[([^\]]*)\]", ci_text):
        for token in re.findall(r"[^\s,\"']+", match.group(1)):
            lowered = token.lower()
            for forbidden in FORBIDDEN_CI_RUNNER_TOKENS:
                if forbidden in lowered:
                    findings.append(_finding(surface, "forbidden_ci_os_matrix", f"non-Windows OS in CI matrix: {token}"))
            if not lowered.startswith("windows"):
                findings.append(_finding(surface, "non_windows_ci_os_matrix", f"CI OS matrix entry is not Windows: {token}"))
    return findings


def ci_python_matrix(surface: str, ci_text: str) -> list[str] | None:
    """Extract the product CI Python matrix versions, or None when absent."""
    match = re.search(r"(?ms)^\s*python:\s*\[([^\]]*)\]", ci_text)
    if match is None:
        return None
    return re.findall(r'"([^"]+)"', match.group(1))


def structured_os_scope_findings(surface: str, payload: Any, path: str = "$") -> list[dict[str, Any]]:
    """Recursive structured scan: OS-scope keys must declare Windows only."""
    findings: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key.lower().replace("-", "_") in OS_SCOPE_KEYS:
                findings.extend(_os_scope_value_findings(surface, child_path, value))
            else:
                findings.extend(structured_os_scope_findings(surface, value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(structured_os_scope_findings(surface, value, f"{path}[{index}]"))
    return findings


def _os_scope_value_findings(surface: str, path: str, value: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    values = value if isinstance(value, list) else [value]
    for entry in values:
        if not isinstance(entry, str):
            findings.append(_finding(surface, "os_scope_malformed", f"OS-scope value at {path} is not a string: {entry!r}"))
            continue
        lowered = entry.lower().strip()
        if lowered in ("none", "windows", ""):
            continue
        if re.search(r"\bwindows\b", lowered):
            # A Windows declaration that also names other platforms is still a claim.
            for token in ("linux", "macos", "mac os x", "os x", "unix", "posix", "darwin"):
                if token in lowered:
                    findings.append(_finding(surface, "forbidden_os_scope_value", f"{path}: mixed-platform OS scope value: {entry}"))
                    break
            continue
        findings.append(_finding(surface, "forbidden_os_scope_value", f"{path}: non-Windows OS scope value: {entry}"))
    return findings


def compatibility_manifest_findings(surface: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """The support manifest must declare Windows-only scope explicitly."""
    findings: list[dict[str, Any]] = []
    if manifest.get("supported_operating_systems") != ["Windows"]:
        findings.append(_finding(surface, "supported_operating_systems_not_windows_only", f"supported_operating_systems={manifest.get('supported_operating_systems')!r}"))
    if manifest.get("windows_only") is not True:
        findings.append(_finding(surface, "windows_only_flag_not_true", f"windows_only={manifest.get('windows_only')!r}"))
    if manifest.get("target_dialect") != "microsoft.visual-foxpro.9.0.sp2":
        findings.append(_finding(surface, "target_dialect_not_canonical", f"target_dialect={manifest.get('target_dialect')!r}"))
    matrix = manifest.get("windows_support_matrix")
    if not isinstance(matrix, dict) or not any(
        isinstance(entry, str) and re.search(r"(?i)non-?windows", entry) for entry in matrix.get("UNSUPPORTED", [])
    ):
        findings.append(_finding(surface, "windows_support_matrix_unsupported_scope_missing", "windows_support_matrix must list non-Windows platforms as UNSUPPORTED"))
    return findings


# ----------------------------------------------------------------------
# Surface collection + aggregate scan.
# ----------------------------------------------------------------------


def _collect_text_surfaces(root: Path, spec: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    texts: list[str] = []
    findings: list[dict[str, Any]] = []
    scanned: list[str] = []
    base = root / spec["path"]
    names: list[Path]
    if spec["kind"] == "file_text":
        names = [base] if base.is_file() else []
    elif spec["kind"] == "glob_text":
        parent = base.parent
        names = sorted(parent.glob(base.name)) if parent.is_dir() else []
    else:  # pragma: no cover - spec construction error
        raise ValueError(f"unsupported surface kind: {spec['kind']}")
    if not names:
        if spec.get("required"):
            findings.append(_finding(spec["path"], "required_surface_missing", f"required surface not found: {spec['path']}"))
        return texts, findings, scanned
    if spec["kind"] == "glob_text" and len(names) < spec.get("min_count", 1):
        findings.append(_finding(spec["path"], "required_surface_underpopulated", f"surface {spec['path']} has {len(names)} files"))
    for path in names:
        if not path.is_file() or path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        scanned.append(relative)
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError) as error:
            findings.append(_finding(relative, "surface_unreadable", f"surface could not be read: {error}"))
    return texts, findings, scanned


def _collect_json_surfaces(root: Path, spec: dict[str, Any]) -> tuple[list[tuple[str, Any]], list[dict[str, Any]]]:
    payloads: list[tuple[str, Any]] = []
    findings: list[dict[str, Any]] = []
    base = root / spec["path"]
    names: list[Path]
    if spec["kind"] == "json_surface":
        names = [base] if base.is_file() else []
    elif spec["kind"] == "glob_json":
        parent = base.parent
        names = sorted(parent.glob(base.name)) if parent.is_dir() else []
    else:  # pragma: no cover
        raise ValueError(f"unsupported surface kind: {spec['kind']}")
    if not names:
        if spec.get("required"):
            findings.append(_finding(spec["path"], "required_surface_missing", f"required surface not found: {spec['path']}"))
        return payloads, findings
    if spec["kind"] == "glob_json" and len(names) < spec.get("min_count", 1):
        findings.append(_finding(spec["path"], "required_surface_underpopulated", f"surface {spec['path']} has {len(names)} files"))
    for path in names:
        relative = path.relative_to(root).as_posix()
        try:
            payloads.append((relative, json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError) as error:
            findings.append(_finding(relative, "surface_unreadable", f"surface could not be parsed: {error}"))
    return payloads, findings


def scan_support_claims(root: Path, *, surfaces: tuple[dict[str, Any], ...] | None = None) -> dict[str, Any]:
    """Full deterministic support-claims scan of a repository/fixture root.

    Returns a machine-readable report: ``status`` is PASS only when every
    required surface is present and zero findings exist (fail closed).
    """
    surface_spec = DEFAULT_SURFACE_SPEC if surfaces is None else surfaces
    findings: list[dict[str, Any]] = []
    surfaces_scanned: list[str] = []
    checks: dict[str, bool] = {}

    readme_text: str | None = None
    pyproject_text: str | None = None
    docs_texts: list[str] = []
    ci_texts: list[str] = []

    for spec in surface_spec:
        kind = spec["kind"]
        if kind in ("file_text", "glob_text"):
            texts, surface_findings, scanned = _collect_text_surfaces(root, spec)
            findings.extend(surface_findings)
            surfaces_scanned.extend(scanned)
            rel = spec["path"]
            if rel == "README.md":
                readme_text = texts[0] if texts else None
            elif rel == "pyproject.toml":
                pyproject_text = texts[0] if texts else None
                if pyproject_text is not None:
                    surface_findings = pyproject_classifier_findings(rel, pyproject_text)
                    findings.extend(surface_findings)
            elif rel.startswith("docs/"):
                docs_texts.extend(texts)
            elif rel.startswith(".github/workflows/"):
                ci_texts.extend(texts)
                for text, name in zip(texts, scanned, strict=False):
                    findings.extend(ci_platform_findings(name, text))
            for text, name in zip(texts, scanned, strict=False):
                if not name.startswith(".github/workflows/"):
                    findings.extend(text_surface_findings(name, text))
        elif kind in ("json_surface", "glob_json"):
            payloads, surface_findings = _collect_json_surfaces(root, spec)
            findings.extend(surface_findings)
            surfaces_scanned.extend(name for name, _payload in payloads)
            for name, payload in payloads:
                if spec["path"] == "spec/compatibility.manifest.json":
                    if isinstance(payload, dict):
                        findings.extend(compatibility_manifest_findings(name, payload))
                    else:
                        findings.append(_finding(name, "surface_malformed", "compatibility manifest is not an object"))
                else:
                    findings.extend(structured_os_scope_findings(name, payload))
        else:  # pragma: no cover
            raise ValueError(f"unsupported surface kind: {kind}")

    # Affirmative Windows-only statements (REQ-P00-002 documentation duty).
    if readme_text is not None:
        statement_ok = bool(REQUIRED_README_STATEMENT.search(readme_text))
        checks["readme_windows_only_statement"] = statement_ok
        if not statement_ok:
            findings.extend(required_statement_findings("README.md", readme_text, REQUIRED_README_STATEMENT, "windows_only_statement_missing"))
    else:
        checks["readme_windows_only_statement"] = False
    if docs_texts:
        checks["docs_windows_only_statement"] = any(REQUIRED_DOC_STATEMENT.search(text) for text in docs_texts)
        if not checks["docs_windows_only_statement"]:
            findings.append(
                _finding("docs/*.md", "windows_only_support_statement_missing", "no Windows-only installation/support statement found in docs/")
            )
    else:
        checks["docs_windows_only_statement"] = False

    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in findings:
        key = (entry["surface"], entry["check"], entry["detail"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(entry)

    return {
        "report": "SUPPORT_CLAIMS_SCAN",
        "status": "FAIL" if deduplicated else "PASS",
        "finding_count": len(deduplicated),
        "findings": deduplicated,
        "surfaces_scanned": surfaces_scanned,
        "checks": checks,
    }
