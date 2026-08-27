# -*- coding: utf-8 -*-
"""
backends/dbfbridge_backend.py - adapter for the vendored dbfbridge snapshot.

Uses the vendored copy under tools/dbfbridge/ (pinned snapshot — see
tools/dbfbridge/VERSION.txt) through its PUBLIC API only:
    export_dbf(), reconstruct_dbf(), verify_conversion(), check_conversion_quality()

No private module imports, no algorithm re-implementation, no network.
Importing this module does not import dbfbridge; the package is loaded
lazily so that the Core Service stays importable anywhere.
"""

import os
import sys

from .. import config
from ..capabilities import BACKEND_DBFBRIDGE

# Vendored snapshot pin (tools/dbfbridge/VERSION.txt, upstream dbfbridge).
EXPECTED_UPSTREAM_COMMIT = "addbadb9281914661bf742924f45039e46a895cd"
PUBLIC_API = ("export_dbf", "reconstruct_dbf", "verify_conversion",
              "check_conversion_quality")


def _ensure_vendored_on_path():
    """Prepend the vendored tools/dbfbridge dir to sys.path (idempotent).

    Mirrors vfp_dbf_export._ensure_vendored_dbfbridge_on_path so the vendored
    snapshot wins over any externally installed dbfbridge.
    """
    vendored = config.dbfbridge_vendored_dir()
    if not os.path.isdir(os.path.join(vendored, "dbf_bridge")):
        return False
    path = os.path.abspath(vendored)
    if path not in sys.path:
        sys.path.insert(0, path)
    return True


def _vendored_meta():
    """Read provenance facts from tools/dbfbridge/VERSION.txt (read-only)."""
    meta = {"upstreamCommit": EXPECTED_UPSTREAM_COMMIT}  # type: dict
    path = os.path.join(config.dbfbridge_vendored_dir(), "VERSION.txt")
    if not os.path.isfile(path):
        meta["versionFile"] = None
        return meta
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        meta["versionFile"] = path
        return meta
    meta["versionFile"] = path
    for line in text.splitlines():
        line = line.strip().lstrip("# ").strip()
        low = line.lower()
        if low.startswith("commit"):
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                meta["upstreamCommit"] = parts[1].strip()
        elif low.startswith("vendored"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                meta["vendoredDate"] = parts[1].strip()
    return meta


class DBFBridgeBackend(object):
    """Stable adapter over the vendored dbfbridge public API."""

    name = "dbfbridge"
    backend = BACKEND_DBFBRIDGE

    def _module(self):
        """Import the vendored dbfbridge package (lazy; no side effects)."""
        if not _ensure_vendored_on_path():
            raise ImportError("vendored dbfbridge snapshot not found at %s"
                              % config.dbfbridge_vendored_dir())
        import dbfbridge  # public package
        return dbfbridge

    def status(self):
        """Availability + provenance report (PURE_READ, no VFP, no DBF open)."""
        meta = _vendored_meta()
        try:
            mod = self._module()
        except Exception as e:
            meta.update({"available": False, "vendored": False,
                         "version": None, "publicApiOk": False,
                         "error": str(e)})
            return meta
        ok_api = all(hasattr(mod, n) for n in PUBLIC_API)
        meta.update({
            "available": ok_api,
            "vendored": True,
            "version": getattr(mod, "__version__", None),
            "publicApi": {n: hasattr(mod, n) for n in PUBLIC_API},
            "publicApiOk": ok_api,
            "vfpRequired": False,
        })
        return meta

    def version(self):
        return getattr(self._module(), "__version__", None)

    # -- public API passthrough (thin wrappers, no re-implementation) -------

    def export_dbf(self, source, output, **kwargs):
        return self._module().export_dbf(source, output, **kwargs)

    def reconstruct_dbf(self, source, output, **kwargs):
        return self._module().reconstruct_dbf(source, output, **kwargs)

    def verify_conversion(self, *args, **kwargs):
        return self._module().verify_conversion(*args, **kwargs)

    def check_conversion_quality(self, *args, **kwargs):
        return self._module().check_conversion_quality(*args, **kwargs)


__all__ = ["DBFBridgeBackend", "PUBLIC_API", "EXPECTED_UPSTREAM_COMMIT"]
