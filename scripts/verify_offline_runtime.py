#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_offline_runtime.py - verify the OFFLINE runtime (Phase 10).

Checks, WITHOUT any network and WITHOUT VFP9/FoxBin2Prg:
  * vfp_toolchain import
  * dbfread import (runtime-mandatory for PURE READ)
  * dbfbridge import + public API + module origin + pin
  * dbf_anonymizer import + public API + module origin + pin
    + dbfbridge compatibility
  * installed versions vs the lock manifest (informational for optional
    packages, mandatory for dbfread)
  * wheelhouse SHA256 (if a wheelhouse is present)
  * VFPToolchainService().capabilities() reports pureRead available
    and offlineRuntime.verified

Exit code: 0 on verified, 1 otherwise. Machine-readable JSON to stdout.

Usage:
    python verify_offline_runtime.py [--root PATH]
"""

import argparse
import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_CANDIDATES = [os.path.dirname(THIS_DIR), THIS_DIR, os.getcwd()]


def _find_root(explicit=None):
    if explicit:
        return os.path.abspath(explicit)
    for c in REPO_CANDIDATES:
        if os.path.isfile(os.path.join(c, "src", "vfp_toolchain", "__init__.py")):
            return c
    # inside a bundle: app/ contains src/
    for c in REPO_CANDIDATES:
        app = os.path.join(c, "app")
        if os.path.isdir(os.path.join(app, "src", "vfp_toolchain")):
            return app
    return REPO_CANDIDATES[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify the offline runtime")
    ap.add_argument("--root", default=None, help="repo or bundle app root")
    args = ap.parse_args(argv)

    root = _find_root(args.root)
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    if root not in sys.path:
        sys.path.insert(0, root)

    # Force "no VFP / no FoxBin2Prg" for the capabilities probe: point the
    # resolvers at guaranteed-nonexistent paths (read-only semantics).
    os.environ.setdefault("VFP9_EXE", os.path.join(root, "definitely-not-installed", "vfp9.exe"))
    if not os.environ.get("VFP_FOXBIN2PRG_DIR"):
        os.environ["VFP_FOXBIN2PRG_DIR"] = os.path.join(root, "definitely-not-installed", "foxbin2prg")

    report = {"root": root, "checks": []}  # type: dict

    def check(name, ok, detail=None):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    # 1. vfp_toolchain import
    try:
        import vfp_toolchain  # noqa: F401
        check("vfp_toolchain_import", True)
    except Exception as e:  # noqa: BLE001
        check("vfp_toolchain_import", False, str(e))
        report["verified"] = False
        report["errorCode"] = "OFFLINE_RUNTIME_INCOMPLETE"
        print(json.dumps(report, indent=1))
        return 1

    # 2. dbfread (runtime-mandatory for PURE READ)
    try:
        import dbfread  # noqa: F401
        check("dbfread_import", True, getattr(dbfread, "__version__", None))
    except Exception as e:  # noqa: BLE001
        check("dbfread_import", False, str(e))

    # 3. vendored backends (origin + pin + public API)
    from vfp_toolchain.runtime import (  # noqa: E402
        check_imports,
        expected_versions_from_manifest,
        load_manifest,
        offline_runtime_status,
    )

    for c in check_imports(root):
        check("import:" + c["name"], c["imported"], c.get("error"))
        if c["imported"]:
            check("origin:" + c["name"], c.get("originVerified", True),
                  c.get("moduleFile"))
            if "pinVerified" in c:
                check("pin:" + c["name"], c.get("pinVerified", False))

    # 4. versions vs lock manifest.
    # Only RUNTIME-MANDATORY packages gate the result (dbfread). Optional
    # lazy packages (dbf, orjson, openpyxl, xlsxwriter, polars) are reported
    # as informational mismatches — they are not required for PURE READ.
    manifest = load_manifest(os.path.join(root, "runtime", "runtime-dependencies.json"))
    version_problems = []  # type: list
    version_info = []  # type: list
    mandatory_names = set()
    if manifest:
        for dep in manifest.get("dependencies", []):
            if dep.get("runtimeMandatory"):
                mandatory_names.add(dep.get("name"))
        expected = expected_versions_from_manifest(manifest)
        import importlib.metadata as md  # noqa: E402
        for name, want in sorted(expected.items()):
            try:
                have = md.version(name)
            except Exception:  # noqa: BLE001
                have = None
            if have is None:
                continue
            if not have.startswith(str(want)):
                item = {"name": name, "expected": want, "actual": have}
                if name in mandatory_names:
                    version_problems.append(item)
                else:
                    version_info.append(item)
    check("versions_match_lock", not version_problems,
          version_problems or version_info or None)

    # 5. capabilities() without VFP
    from vfp_toolchain.service import VFPToolchainService  # noqa: E402
    cap = VFPToolchainService(root=root).capabilities().to_dict()
    check("capabilities_ok", cap["ok"] is True, cap.get("errorCode"))
    check("pureRead_available",
          cap["data"]["modes"].get("pureRead") is True)
    check("vfpEnhancedRead_false",
          cap["data"]["modes"].get("vfpEnhancedRead") is False)

    offline = cap["data"].get("offlineRuntime", {})
    check("offlineRuntime_verified", offline.get("verified") is True,
          {"missing": offline.get("missing"),
           "mismatched": offline.get("mismatched"),
           "hashMismatched": offline.get("hashMismatched"),
           "errorCodes": offline.get("errorCodes")})

    verified = all(c["ok"] for c in report["checks"])
    report["verified"] = verified
    report["networkRequired"] = False
    report["errorCode"] = None if verified else "OFFLINE_RUNTIME_INCOMPLETE"
    print(json.dumps(report, indent=1))
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
