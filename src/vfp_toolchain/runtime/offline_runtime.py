# -*- coding: utf-8 -*-
"""
runtime/offline_runtime.py - offline runtime verification (transport-neutral).

Checks that the Python runtime closure is complete and self-consistent,
WITHOUT any network access:

  * dbfread (runtime-mandatory for PURE READ) is importable,
  * dbfbridge imports from the vendored root (module origin),
  * DBF_Anonymizer imports from the vendored root and matches its pins,
  * the offline wheelhouse (if present) verifies against the lock manifest
    (SHA256 per wheel),
  * installed versions match the locked versions where a lock is provided.

Stable diagnostic codes (errors.py):
  OFFLINE_DEPENDENCY_MISSING
  OFFLINE_DEPENDENCY_VERSION_MISMATCH
  OFFLINE_DEPENDENCY_HASH_MISMATCH
  OFFLINE_DEPENDENCY_ORIGIN_MISMATCH
  OFFLINE_RUNTIME_INCOMPLETE

Everything here is PURE_READ: imports, file reads, SHA256. No install,
no network, no writes.
"""

import importlib
import os
import sys
from typing import Optional

from .. import config
from ..errors import (
    EC_OFFLINE_DEPENDENCY_HASH_MISMATCH,
    EC_OFFLINE_DEPENDENCY_MISSING,
    EC_OFFLINE_DEPENDENCY_ORIGIN_MISMATCH,
    EC_OFFLINE_DEPENDENCY_VERSION_MISMATCH,
    EC_OFFLINE_RUNTIME_INCOMPLETE,
)
from . import dependency_manifest

LOCK_MANIFEST_NAME = "runtime-dependencies.json"
LOCK_MANIFEST_REL = os.path.join("runtime", LOCK_MANIFEST_NAME)
WHEELHOUSE_REL = os.path.join("runtime", "wheels")


def lock_manifest_path(root=None):
    return os.path.join(config.repo_root(root), LOCK_MANIFEST_REL)


def wheelhouse_path(root=None):
    return os.path.join(config.repo_root(root), WHEELHOUSE_REL)


def _import_fresh(name, on_path_dirs):
    """Import ``name`` after placing the given dirs first on sys.path.

    Returns (module, error). Never installs anything; if the package is not
    importable the error is surfaced (OFFLINE_DEPENDENCY_MISSING upstream).
    """
    for d in reversed(on_path_dirs):
        if os.path.isdir(d) and d not in sys.path:
            sys.path.insert(0, d)
    try:
        return importlib.import_module(name), None
    except Exception as e:  # noqa: BLE001 - report, do not mask
        return None, str(e)


def check_imports(root=None):
    """Verify the runtime closure imports (dbfread + vendored packages).

    Returns dict with per-package import status + origin verification.
    """
    vendored_dbfbridge = config.dbfbridge_vendored_dir(root)
    vendored_anon = os.path.join(config.repo_root(root),
                                 "tools" + os.sep + "dbf_anonymizer")
    checks = []  # type: list

    # dbfread — runtime-mandatory for PURE READ (no vendored fallback exists;
    # it must come from the installed environment / offline wheelhouse).
    dbfread_ok, dbfread_err = _import_fresh("dbfread", [])
    checks.append({
        "name": "dbfread",
        "runtimeMandatory": True,
        "imported": dbfread_ok is not None,
        "version": getattr(dbfread_ok, "__version__", None)
                   if dbfread_ok else None,
        "moduleFile": getattr(dbfread_ok, "__file__", None) if dbfread_ok else None,
        "vendoredRoot": None,
        "originVerified": True,  # pip-installed; origin = site-packages is legal
        "error": dbfread_err,
    })

    # dbfbridge (vendored) — origin must be the vendored root.
    from ..backends.dbfbridge_backend import DBFBridgeBackend
    be = DBFBridgeBackend(root=root)
    meta = be.status()
    checks.append({
        "name": "dbfbridge",
        "runtimeMandatory": True,
        "imported": meta.get("publicApiOk", False),
        "version": meta.get("version"),
        "moduleFile": meta.get("moduleFile"),
        "vendoredRoot": meta.get("vendoredRoot"),
        "originVerified": bool(meta.get("moduleOriginVerified", False)),
        "pinVerified": bool(meta.get("pinVerified", False)),
        "error": meta.get("error"),
    })

    # dbf_anonymizer (vendored) — origin + pin + shared dbfbridge.
    from ..backends.dbf_anonymizer_backend import DBFAnonymizerBackend
    be2 = DBFAnonymizerBackend(root=root)
    meta2 = be2.status()
    checks.append({
        "name": "dbf_anonymizer",
        "runtimeMandatory": False,  # present, but only status-exposed in Phase 1/2
        "imported": meta2.get("publicApiOk", False),
        "version": meta2.get("version"),
        "moduleFile": meta2.get("moduleFile"),
        "vendoredRoot": meta2.get("vendoredRoot"),
        "originVerified": bool(meta2.get("moduleOriginVerified", False)),
        "pinVerified": bool(meta2.get("pinVerified", False)),
        "dbfbridgeCompatible": bool(meta2.get("dbfbridgeCompatible", False)),
        "error": meta2.get("error"),
    })

    return checks


def _codes_for(checks):
    """Map failed checks onto stable offline diagnostic codes (fail-closed)."""
    codes = set()
    for c in checks:
        if not c["imported"]:
            codes.add(EC_OFFLINE_DEPENDENCY_MISSING)
            continue
        if c["runtimeMandatory"] is False and not c.get("imported", False):
            continue
        if not c.get("originVerified", True):
            codes.add(EC_OFFLINE_DEPENDENCY_ORIGIN_MISMATCH)
    return codes


def verify_offline_runtime(root=None, expected_versions=None):
    """Full offline runtime verification. Returns a report dict.

    ``expected_versions``: optional {name: version} (from the lock manifest)
    to also verify installed versions against the lock.
    """
    checks = check_imports(root)
    codes = _codes_for(checks)

    # version verification against the lock (when provided).
    # Only RUNTIME-MANDATORY packages (dbfread) gate `verified`; optional
    # lazy packages (dbf, orjson, openpyxl, xlsxwriter, polars) are reported
    # as informational version problems, not hard failures.
    version_problems = []  # type: list
    if expected_versions:
        for c in checks:
            want = expected_versions.get(c["name"])
            if not want or c["version"] is None:
                continue
            have = str(c["version"])
            if not have.startswith(str(want)):
                version_problems.append({"name": c["name"],
                                         "expected": str(want),
                                         "actual": have,
                                         "mandatory": bool(c["runtimeMandatory"])})
                if c["runtimeMandatory"]:
                    codes.add(EC_OFFLINE_DEPENDENCY_VERSION_MISMATCH)

    # wheelhouse verification. The wheelhouse ships inside the BUILT bundle
    # (dist/.../wheels), not in the source repo. If the directory is absent
    # we report "not present" (a dev checkout) rather than failing; a
    # PRESENT but incomplete/corrupt wheelhouse is a hard failure.
    wh_result = None  # type: Optional[dict]
    manifest = dependency_manifest.load_manifest(lock_manifest_path(root))
    wh_dir = wheelhouse_path(root)
    if manifest is not None:
        if not os.path.isdir(wh_dir):
            wh_result = {"present": False, "verified": None,
                         "missing": [], "mismatched": [], "files": 0, "ok": []}
        else:
            wh_result = dependency_manifest.verify_wheelhouse(manifest, wh_dir)
            wh_result["present"] = True
            if wh_result["missing"]:
                codes.add(EC_OFFLINE_DEPENDENCY_MISSING)
            if wh_result["mismatched"]:
                codes.add(EC_OFFLINE_DEPENDENCY_HASH_MISMATCH)

    required_ok = all(c["imported"] for c in checks if c["runtimeMandatory"])
    mandatory_version_bad = any(v["mandatory"] for v in version_problems)
    # A wheelhouse that is NOT PRESENT (dev checkout) does not fail the
    # runtime; a PRESENT but failing wheelhouse does.
    wh_ok = (wh_result is None or not wh_result.get("present", True)
             or bool(wh_result.get("verified", False)))
    verified = (required_ok and not codes and not mandatory_version_bad
                and wh_ok)
    if not verified and not codes:
        codes.add(EC_OFFLINE_RUNTIME_INCOMPLETE)

    return {
        "verified": verified,
        "networkRequired": False,
        "requiredImportsOk": required_ok,
        "checks": checks,
        "versionProblems": version_problems,
        "wheelhouse": wh_result,
        "errorCodes": sorted(codes),
    }


def expected_versions_from_manifest(manifest):
    """{package: locked version} from the lock manifest."""
    out = {}  # type: dict
    for dep in (manifest or {}).get("dependencies", []):
        name = dep.get("name")
        version = dep.get("version")
        if name and version:
            out[name] = version
    return out


def offline_runtime_status(root=None):
    """Convenience for capability discovery: offlineRuntime block (Phase 11).

    Shape (documented in docs/OFFLINE_RUNTIME.md):
      {
        "dependencyClosure": bool,
        "verified": bool,
        "missing": [name...],
        "mismatched": [name...],
        "hashMismatched": [filename...],
        "networkRequired": false
      }
    """
    report = verify_offline_runtime(root)
    missing = [c["name"] for c in report["checks"] if not c["imported"]]
    mismatched = [v["name"] for v in report["versionProblems"]]
    wh = report.get("wheelhouse") or {}
    hash_bad = [m["filename"] for m in wh.get("mismatched", [])]
    origin_bad = [c["name"] for c in report["checks"]
                  if not c.get("originVerified", True) and c["imported"]]
    wh_present = bool(wh.get("present", False))
    # A dev checkout without a wheelhouse bundle is NOT an incomplete
    # runtime: the packages themselves are importable and verified. The
    # wheelhouse is a packaging artifact (dist bundle), not a runtime
    # requirement. A PRESENT but failing wheelhouse is a hard failure.
    wh_ok = (not wh_present) or bool(wh.get("verified", False))
    verified = bool(report["verified"]) and wh_ok
    return {
        "dependencyClosure": verified,
        "verified": verified,
        "missing": sorted(set(missing)),
        "mismatched": sorted(set(mismatched + origin_bad)),
        "hashMismatched": hash_bad,
        "wheelhousePresent": wh_present,
        "wheelhouseMissing": wh.get("missing", []),
        "wheelhouseVerified": bool(wh.get("verified", False)) if wh_present else None,
        "errorCodes": report["errorCodes"],
        "networkRequired": False,
    }


__all__ = [
    "lock_manifest_path",
    "wheelhouse_path",
    "check_imports",
    "verify_offline_runtime",
    "expected_versions_from_manifest",
    "offline_runtime_status",
]
