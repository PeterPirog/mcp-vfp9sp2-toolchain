# -*- coding: utf-8 -*-
"""MCP transport adapter entry point (``mcp-vfp9sp2`` console command).

The canonical MCP console entry point (REQ-G00-020) delegates to the same
transport-neutral Core Service.  At the bootstrap foundation the MCP server
transport is truthfully NOT_IMPLEMENTED: this entry point prints the truthful
capability state and refuses to fake a serving session
(REQ-P01-011/REQ-P01-012 are later-phase deliverables).
"""

from __future__ import annotations

import json
import sys

from .core import CoreService
from .errors import CapabilityNotImplementedError, ToolchainError

MCP_TRANSPORT_STATE = "NOT_IMPLEMENTED"


def main(argv: list[str] | None = None) -> int:
    core = CoreService()
    envelope = core.execute("core.capabilities")
    payload = {
        "entry_point": "mcp-vfp9sp2",
        "transport": "MCP",
        "transport_state": MCP_TRANSPORT_STATE,
        "message": (
            "The MCP server transport is not implemented in this bootstrap "
            "foundation build; the minimal official-SDK MCP shell arrives with "
            "milestone P01_MCP_MIN. No placeholder server session is started."
        ),
        "core_capabilities": envelope["data"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def serve() -> int:
    """Refuse to fake a serving session (typed, truthful)."""
    raise CapabilityNotImplementedError(
        "CAPABILITY_NOT_IMPLEMENTED",
        "MCP transport serving is not implemented in the bootstrap foundation build.",
        {"transport_state": MCP_TRANSPORT_STATE},
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ToolchainError as error:  # pragma: no cover - defensive
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)