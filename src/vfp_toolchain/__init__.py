# -*- coding: utf-8 -*-
"""
vfp_toolchain - transport-neutral Python Core Service for the VFP9 SP2 toolchain.

This package is the single service layer shared by the CLI adapter
(vfp_driver.py), the OpenCode adapter (tools/vfp.ts) and, later, a future
MCP adapter. Transports stay thin; domain logic lives here.

Design rules (docs/MCP_TARGET_ARCHITECTURE.md):
  * import must be side-effect free (no VFP, no COM, no files, no network),
  * operations return OperationResult objects (JSON-serializable),
  * capability classes come from docs/mcp_capability_model.json (one truth),
  * source projects are immutable by default.
"""

from .service import VFPToolchainService  # noqa: F401
from .models import OperationResult  # noqa: F401
from .capabilities import Capability  # noqa: F401

__version__ = "0.3.0"

__all__ = ["VFPToolchainService", "OperationResult", "Capability", "__version__"]
