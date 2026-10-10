# -*- coding: utf-8 -*-
"""Operator CLI adapter over the transport-neutral Core Service.

The canonical console entry point ``vfp-toolchain`` (REQ-G00-020) delegates to
:vclass:`vfp_toolchain.core.CoreService`; this adapter adds no domain logic.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import CoreService
from .errors import ToolchainError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vfp-toolchain",
        description="Windows-local MCP platform for Visual FoxPro 9.0 SP2 work (bootstrap foundation build).",
    )
    parser.add_argument("--version", action="store_true", help="print the package version and exit")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("capabilities", help="print the truthful capability state")
    subparsers.add_parser("describe", help="print the Core Service description envelope")

    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0

    core = CoreService()
    try:
        if args.command == "capabilities":
            envelope = core.execute("core.capabilities")
        elif args.command == "describe":
            envelope = core.execute("core.describe")
        else:
            parser.print_help()
            print(
                "\nNote: this is the bootstrap foundation build. All domain capabilities "
                "(DBF/FPT, knowledge, semantic analysis, refactoring, privacy, PostgreSQL, "
                "MCP serving) are truthfully NOT_IMPLEMENTED.",
                file=sys.stderr,
            )
            return 0
    except ToolchainError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())