# -*- coding: utf-8 -*-
"""Canonical verifier dispatcher CLI (repo-local, deterministic, offline).

Subcommands produce machine-readable JSON reports on stdout and exit 0 on
PASS, 1 on FAIL, 2 on BLOCKED:

    self-consistency           contract self-consistency (REQ-B00-004)
    schemas                    schema document + artifact conformance
    layout                     canonical control-plane layout
    package                    package foundation checks
    determinism                double-generation logical identity
    no-download                runtime network/package-install sentinel
    test-map                   test-module -> requirement-ID evidence map
    dialect-identity           VFP9 SP2 dialect identity gate (REQ-P00-001)
    platform-policy            Windows-only platform policy gate (REQ-P00-002)
    python-support             supported-Python range gate (REQ-P00-011)
    support-claims             Windows-only support-claims gate (REQ-P00-018)
    invocation --evidence PATH validate retained invocation evidence
    dependency-lock [--wheelhouse PATH] [--invocation-evidence PATH]
                               verify the frozen canonical dependency lock;
                               lock-internal checks are stdlib-only, the
                               wheelhouse checks need the frozen wheelhouse
    dispatch --requirement REQ-... [--start-mode ...] [--authoring-mode ...]
                               [--operation-scope ...]  dispatch one
                                requirement against an explicit context
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from vfp_toolchain.verification import engine  # noqa: E402

EXIT_CODES = {"PASS": 0, "FAIL": 1, "BLOCKED": 2}


def _emit(report: dict) -> int:
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return EXIT_CODES.get(report.get("status", "FAIL"), 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify.py", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("self-consistency")
    subparsers.add_parser("schemas")
    subparsers.add_parser("layout")
    subparsers.add_parser("package")
    subparsers.add_parser("determinism")
    subparsers.add_parser("no-download")
    subparsers.add_parser("test-map")
    subparsers.add_parser("dialect-identity")
    subparsers.add_parser("platform-policy")
    subparsers.add_parser("python-support")
    subparsers.add_parser("support-claims")

    invocation_parser = subparsers.add_parser("invocation")
    invocation_parser.add_argument("--evidence", type=Path, required=True)

    dependency_lock_parser = subparsers.add_parser("dependency-lock")
    dependency_lock_parser.add_argument("--wheelhouse", type=Path, default=None)
    dependency_lock_parser.add_argument("--invocation-evidence", type=Path, default=None)

    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_parser.add_argument("--requirement", required=True)
    dispatch_parser.add_argument("--start-mode", default="GREENFIELD")
    dispatch_parser.add_argument("--authoring-mode", default="HYBRID")
    dispatch_parser.add_argument("--operation-scope", default="LOCAL_QUALIFICATION")

    args = parser.parse_args(argv)

    if args.command == "self-consistency":
        return _emit(engine.self_consistency_report(_REPO_ROOT))
    if args.command == "schemas":
        return _emit(engine.schema_validation_report(_REPO_ROOT))
    if args.command == "layout":
        return _emit(engine.layout_report(_REPO_ROOT))
    if args.command == "package":
        return _emit(engine.package_report(_REPO_ROOT))
    if args.command == "determinism":
        return _emit(engine.determinism_report(_REPO_ROOT))
    if args.command == "no-download":
        return _emit(engine.no_download_report(_REPO_ROOT))
    if args.command == "test-map":
        return _emit(engine.test_map_report(_REPO_ROOT))
    if args.command == "dialect-identity":
        return _emit(engine.dialect_identity_report(_REPO_ROOT))
    if args.command == "platform-policy":
        return _emit(engine.platform_policy_report(_REPO_ROOT))
    if args.command == "python-support":
        return _emit(engine.python_support_report(_REPO_ROOT))
    if args.command == "support-claims":
        return _emit(engine.support_claims_report(_REPO_ROOT))
    if args.command == "invocation":
        return _emit(engine.invocation_report(args.evidence))
    if args.command == "dependency-lock":
        return _emit(
            engine.dependency_lock_report(_REPO_ROOT, wheelhouse=args.wheelhouse, invocation_evidence=args.invocation_evidence)
        )
    if args.command == "dispatch":
        report = engine.dispatch_requirement(
            args.requirement,
            {
                "start_mode": args.start_mode,
                "authoring_mode": args.authoring_mode,
                "operation_scope": args.operation_scope,
                "release_profile": "NONE",
                "release_context": "NONE",
            },
            _REPO_ROOT,
        )
        return _emit(report)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())