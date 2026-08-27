# -*- coding: utf-8 -*-
"""
errors.py - central machine-readable error-code catalog for the Core Service.

Re-exports the stable catalog from vfp_protocol.py (single source of truth
for the CLI protocol) and extends it with dependency/capability codes used
by the capability discovery and backend adapters. Do NOT invent new names
for the same condition in different adapters — this list is the only place.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Stable legacy catalog (do not rename — agents and CI rely on these).
from vfp_protocol import (  # noqa: E402
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_PARTIAL,
    EC_SOURCE_PATH_WRITE_FORBIDDEN,
    EC_SOURCE_HASH_CHANGED,
    EC_CRITICAL_SOURCE_MUTATION,
    EC_MISSING_COMPANION,
    EC_PATCH_PRECONDITION_FAILED,
    EC_VFP9_NOT_AVAILABLE,
    EC_VFP9_TIMEOUT,
    EC_COMPILE_ERROR,
    EC_ROUNDTRIP_FAILED,
    EC_FORM_STRUCTURE_CHANGED,
    EC_ENCODING_CORRUPTION,
    EC_STATIC_VALIDATION_FAILED,
    EC_PLAN_SCHEMA_INVALID,
    EC_WORKSPACE_NOT_FOUND,
    EC_OBJECT_NOT_FOUND,
    EC_METHOD_NOT_FOUND,
    EC_WORKSPACE_WRITE_FORBIDDEN,
    ALL_ERROR_CODES,
)

# Dependency / capability discovery codes (Core Service extension).
EC_DEPENDENCY_NOT_AVAILABLE = "DEPENDENCY_NOT_AVAILABLE"
EC_DEPENDENCY_VERSION_MISMATCH = "DEPENDENCY_VERSION_MISMATCH"
EC_VFP9_NOT_INSTALLED = "VFP9_NOT_INSTALLED"
EC_FOXBIN2PRG_NOT_AVAILABLE = "FOXBIN2PRG_NOT_AVAILABLE"
EC_ANONYMIZER_NOT_AVAILABLE = "ANONYMIZER_NOT_AVAILABLE"
EC_ANON_DICTIONARY_SENSITIVE = "ANON_DICTIONARY_SENSITIVE"
EC_CDX_REBUILD_REQUIRES_VFP9 = "CDX_REBUILD_REQUIRES_VFP9"
EC_KNOWLEDGE_INCOMPLETE = "KNOWLEDGE_INCOMPLETE"
EC_DEPENDENCY_PARTIAL = "DEPENDENCY_PARTIAL"
EC_CONFIG_ERROR = "CONFIG_ERROR"

CORE_EXTENSION_ERROR_CODES = (
    EC_DEPENDENCY_NOT_AVAILABLE,
    EC_DEPENDENCY_VERSION_MISMATCH,
    EC_VFP9_NOT_INSTALLED,
    EC_FOXBIN2PRG_NOT_AVAILABLE,
    EC_ANONYMIZER_NOT_AVAILABLE,
    EC_ANON_DICTIONARY_SENSITIVE,
    EC_CDX_REBUILD_REQUIRES_VFP9,
    EC_KNOWLEDGE_INCOMPLETE,
    EC_DEPENDENCY_PARTIAL,
    EC_CONFIG_ERROR,
)

ALL_CORE_ERROR_CODES = tuple(ALL_ERROR_CODES) + CORE_EXTENSION_ERROR_CODES

__all__ = [n for n in list(globals()) if n.startswith(("EC_", "STATUS_", "ALL_"))]
