# -*- coding: utf-8 -*-
"""mcp-vfp9sp2-toolchain — Windows-local MCP platform for Visual FoxPro 9.0 SP2.

Bootstrap foundation build (version 0.0.0.dev0): repository/control-plane
infrastructure only.  Every domain capability (DBF/FPT, VFP knowledge,
semantic analysis, forms/classes, optimization, refactoring, privacy,
relational design, PostgreSQL migration, MCP serving) is truthfully
NOT_IMPLEMENTED in this build; no placeholder success is exposed.
"""

from __future__ import annotations

__version__ = "0.0.0.dev0"
__all__ = [
    "__version__",
    "canonical",
    "capabilities",
    "core",
    "errors",
]

PRODUCT_NAME = "mcp-vfp9sp2-toolchain"
CANONICAL_REPOSITORY_IDENTITY = "https://github.com/PeterPirog/mcp-vfp9sp2-toolchain"
TARGET_DIALECT = "microsoft.visual-foxpro.9.0.sp2"
SUPPORTED_PYTHON_RANGE = ">=3.10,<3.15"