# -*- coding: utf-8 -*-
"""Canonical product/platform domain identity (REQ-P00-001 / REQ-P00-002 /
REQ-P00-011).

This module is the ONE canonical product-level source of truth for:

* the supported Visual FoxPro dialect identity (``microsoft.visual-foxpro.9.0.sp2``);
* the Windows-only production platform policy;
* the supported Python runtime range (``>=3.10,<3.15``).

Every other product module that needs these values imports them from here.
Domain behavior (parsing, compiling, corpus semantics) is NOT implemented in
this module — this packet establishes the domain identity and its gate only
(REQ-P00-001 scope boundary).

Dialect policy (REQ-P00-001):
* Visual FoxPro 9.0 SP2 is the sole supported product dialect target;
* syntax, object models, file semantics, compiler behavior, and runtime
  behavior from older FoxPro / Visual FoxPro releases are NOT automatically
  supported;
* an older-compatible language element can become relevant only when it is
  documented inside the pinned VFP9 SP2 corpus (VFPX HelpFile 1.08; the corpus
  itself is acquired/validated by a later milestone — see REQ-P00-004).

Platform policy (REQ-P00-002):
* the production server supports Windows only;
* packaging, path handling, process execution, COM integration, filesystem
  safety, and test/support declarations are designed for Windows semantics;
* incidental import/bootstrap execution of pure logic on a non-Windows
  interpreter is possible but is never supported product behavior.
"""

from __future__ import annotations

import re
from typing import Any

POLICY_VERSION = 1

# ----------------------------------------------------------------------
# Canonical product identity (single source of truth; re-exported by the
# package ``__init__`` — never duplicate these literals elsewhere).
# ----------------------------------------------------------------------

PRODUCT_NAME = "mcp-vfp9sp2-toolchain"
CANONICAL_REPOSITORY_IDENTITY = "https://github.com/PeterPirog/mcp-vfp9sp2-toolchain"

# REQ-P00-001: exact canonical dialect identifier (must never be widened,
# aliased, or given a generic "FoxPro" fallback).
TARGET_DIALECT = "microsoft.visual-foxpro.9.0.sp2"

# REQ-P00-011: canonical supported Python runtime range.
SUPPORTED_PYTHON_RANGE = ">=3.10,<3.15"
SUPPORTED_PYTHON_MINORS = ("3.10", "3.11", "3.12", "3.13", "3.14")

# REQ-P00-002: canonical production platform policy.
PRODUCTION_PLATFORM = "Windows"
SUPPORTED_OPERATING_SYSTEMS = ("Windows",)
WINDOWS_ONLY = True

# Older-release policy (REQ-P00-001).
OLDER_RELEASE_SEMANTICS = "NOT_AUTOMATICALLY_SUPPORTED"
OLDER_ELEMENT_RELEVANCE_RULE = "RELEVANT_ONLY_WHEN_DOCUMENTED_IN_PINNED_VFP9SP2_CORPUS"
SUPPORT_CLASSIFICATION = "SOLE_SUPPORTED_DIALECT"

_NON_WINDOWS_INCIDENTAL_EXECUTION = "INCIDENTAL_BOOTSTRAP_ONLY_NOT_SUPPORTED"

# ----------------------------------------------------------------------
# Dialect identity reporting (deterministic, pure).
# ----------------------------------------------------------------------


def dialect_identity() -> dict[str, Any]:
    """Return the canonical dialect identity report (REQ-P00-001).

    Deterministic programmatic reporting of: dialect identifier, product
    family, major version, service-pack baseline, and support classification.
    """
    return {
        "policy_version": POLICY_VERSION,
        "dialect_identifier": TARGET_DIALECT,
        "product_family": "Microsoft Visual FoxPro",
        "major_version": 9,
        "service_pack_baseline": "SP2",
        "support_classification": SUPPORT_CLASSIFICATION,
        "sole_dialect_target": True,
        "older_release_semantics": OLDER_RELEASE_SEMANTICS,
        "older_element_relevance_rule": OLDER_ELEMENT_RELEVANCE_RULE,
        "older_release_scope_note": (
            "Syntax, object models, file semantics, compiler behavior, and "
            "runtime behavior from older FoxPro or Visual FoxPro releases are "
            "unsupported unless the same element is explicitly documented by "
            "the pinned VFP9 SP2 corpus (REQ-P00-001)."
        ),
    }


# Classification vocabulary for candidate dialect identifiers (closed).
CLASSIFICATION_SUPPORTED = "SUPPORTED_PRODUCT_DIALECT"
CLASSIFICATION_REJECTED_OTHER_VERSION = "REJECTED_NON_CANONICAL_DIALECT_VERSION"
CLASSIFICATION_REJECTED_GENERIC = "REJECTED_GENERIC_FOXPRO_IDENTITY"
CLASSIFICATION_REJECTED_UNRECOGNIZED = "REJECTED_UNRECOGNIZED_DIALECT_IDENTITY"

_DIALECT_STRUCTURE_RE = re.compile(
    r"^microsoft\.(?:visual-)?foxpro\.(?P<major>\d+)\.(?P<minor>\d+)(?:\.sp(?P<sp>\d+))?$"
)
_GENERIC_FOXPRO_IDENTIFIERS = frozenset(
    {
        "foxpro",
        "vfp",
        "visual-foxpro",
        "microsoft.foxpro",
        "microsoft.vfp",
        "microsoft.visual-foxpro",
        "xbase",
        "dbase",
    }
)


def classify_dialect_identity(identifier: str) -> str:
    """Classify a candidate dialect identifier (REQ-P00-001 negative gate).

    Only the exact canonical identifier classifies as supported. Structured
    ``microsoft.(visual-)foxpro.<major>.<minor>[.spN]`` identities with any
    other version/service-pack combination are rejected as non-canonical
    dialect versions (older releases are never automatically supported).
    Generic FoxPro-family identities are rejected — there is no generic
    "FoxPro" fallback identity.
    """
    if identifier == TARGET_DIALECT:
        return CLASSIFICATION_SUPPORTED
    if identifier.strip().lower() in _GENERIC_FOXPRO_IDENTIFIERS:
        return CLASSIFICATION_REJECTED_GENERIC
    match = _DIALECT_STRUCTURE_RE.match(identifier.strip().lower())
    if match:
        return CLASSIFICATION_REJECTED_OTHER_VERSION
    return CLASSIFICATION_REJECTED_UNRECOGNIZED


def is_supported_product_dialect(identifier: str) -> bool:
    """True only for the exact canonical dialect identifier (no fallback)."""
    return classify_dialect_identity(identifier) == CLASSIFICATION_SUPPORTED


# Deterministic negative probe set used by the dialect gate: identifiers that
# must NEVER classify as the supported product dialect.
DIALECT_NEGATIVE_PROBES: tuple[str, ...] = (
    "microsoft.visual-foxpro.9.0",        # VFP9 without the SP2 baseline
    "microsoft.visual-foxpro.9.0.sp1",    # earlier service pack
    "microsoft.visual-foxpro.8.0.sp1",    # Visual FoxPro 8
    "microsoft.visual-foxpro.7.0",        # Visual FoxPro 7
    "microsoft.visual-foxpro.6.0",        # Visual FoxPro 6
    "microsoft.visual-foxpro.5.0",        # Visual FoxPro 5
    "microsoft.visual-foxpro.3.0",        # Visual FoxPro 3
    "microsoft.foxpro.2.6",               # FoxPro 2.x
    "microsoft.foxpro.2.6.sp1",           # FoxPro 2.x service pack
    "microsoft.visual-foxpro.10.0.sp1",   # future/unreleased dialect
    "vfp",                                # generic identity
    "foxpro",                             # generic identity
    "visual-foxpro",                      # generic identity
    "microsoft.visual-foxpro",            # generic identity
    "xbase",                              # non-FoxPro xBase family
    "dbase",                              # non-FoxPro xBase family
    "microsoft.visual-foxpro.9.0.sp2-x",  # malformed variant
    "Microsoft.Visual-FoxPro.9.0.SP2",    # case-mangled variant
    "",                                   # empty identity
)


# ----------------------------------------------------------------------
# Windows-only platform policy (REQ-P00-002) — machine-readable.
# ----------------------------------------------------------------------


def platform_policy() -> dict[str, Any]:
    """Return the canonical machine-readable Windows-only platform policy.

    The policy covers the semantic boundary used by packaging, path handling,
    process execution, COM integration, filesystem safety, and test/support
    declarations (REQ-P00-002).  Implementation bodies of those boundaries
    arrive with their owning milestones; this policy is the product-level
    declaration they must conform to.
    """
    return {
        "policy_version": POLICY_VERSION,
        "production_server_operating_systems": [PRODUCTION_PLATFORM],
        "windows_only": WINDOWS_ONLY,
        "linux_product_support": False,
        "macos_product_support": False,
        "non_windows_product_support": False,
        "non_windows_interpreter_execution": _NON_WINDOWS_INCIDENTAL_EXECUTION,
        "supported_python_range": SUPPORTED_PYTHON_RANGE,
        "target_dialect": TARGET_DIALECT,
        "boundaries": {
            "packaging": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "Package metadata, classifiers, and distribution targets "
                    "declare Windows; no POSIX/macOS distribution claims."
                ),
            },
            "path_handling": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "Windows path semantics (drive letters, backslashes, case-"
                    "insensitivity, junction/reparse awareness) govern path "
                    "handling; no cross-platform path abstraction layer."
                ),
            },
            "process_execution": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "Process control targets Windows process semantics "
                    "(VFP9 SP2 executables, FoxBin2Prg helpers); no POSIX "
                    "process model claims."
                ),
            },
            "com_integration": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "COM automation assumes Windows COM registration and "
                    "apartment semantics; COM is unavailable elsewhere."
                ),
            },
            "filesystem_safety": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "Filesystem safety policy (immutable zones, reparse-point "
                    "handling) is defined for Windows filesystems only."
                ),
            },
            "test_and_support_declarations": {
                "semantics": "WINDOWS_ONLY",
                "note": (
                    "Product test matrices, CI acceptance, release "
                    "qualification, and operator documentation declare "
                    "Windows-only support (REQ-P00-002/REQ-P00-018)."
                ),
            },
        },
    }


# ----------------------------------------------------------------------
# Python support contract (REQ-P00-011) — deterministic reporting.
# ----------------------------------------------------------------------


def python_support() -> dict[str, Any]:
    """Return the canonical supported-Python contract report (REQ-P00-011)."""
    return {
        "policy_version": POLICY_VERSION,
        "supported_python_range": SUPPORTED_PYTHON_RANGE,
        "supported_python_minors": list(SUPPORTED_PYTHON_MINORS),
        "python_315_supported": False,
        "python_below_310_supported": False,
        "source": "vfp_toolchain.domain (canonical product constant)",
    }
