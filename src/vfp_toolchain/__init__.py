# -*- coding: utf-8 -*-
"""mcp-vfp9sp2-toolchain — Windows-local MCP platform for Visual FoxPro 9.0 SP2.

Bootstrap foundation build (version 0.0.0.dev0): repository/control-plane
infrastructure only.  Every domain capability (DBF/FPT, VFP knowledge,
semantic analysis, forms/classes, optimization, refactoring, privacy,
relational design, PostgreSQL migration, MCP serving) is truthfully
NOT_IMPLEMENTED in this build; no placeholder success is exposed.

Canonical product/platform identity constants live in ``vfp_toolchain.domain``
(REQ-P00-001/002/011) and are re-exported here for stable public access; the
``domain`` module is the single source of truth — never duplicate those
literals in other product modules.
"""

from __future__ import annotations

from .domain import (
    CANONICAL_REPOSITORY_IDENTITY,
    PRODUCT_NAME,
    SUPPORTED_PYTHON_RANGE,
    SUPPORTED_PYTHON_MINORS,
    TARGET_DIALECT,
    WINDOWS_ONLY,
)

__version__ = "0.0.0.dev0"
__all__ = [
    "__version__",
    "canonical",
    "capabilities",
    "core",
    "domain",
    "errors",
    "PRODUCT_NAME",
    "CANONICAL_REPOSITORY_IDENTITY",
    "TARGET_DIALECT",
    "SUPPORTED_PYTHON_RANGE",
    "SUPPORTED_PYTHON_MINORS",
    "WINDOWS_ONLY",
]