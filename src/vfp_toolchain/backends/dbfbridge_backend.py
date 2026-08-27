# -*- coding: utf-8 -*-
"""
backends/dbfbridge_backend.py - adapter for the vendored dbfbridge snapshot.

Uses the vendored copy under tools/dbfbridge/ (pinned snapshot — see
tools/dbfbridge/VERSION.txt) through its PUBLIC API only:
    export_dbf(), reconstruct_dbf(), verify_conversion(), check_conversion_quality()

Fail-closed verification (backends/verify.py):
  * pinVerified        — VERSION.txt commit must agree with the pinned commit,
  * moduleOriginVerified — the imported module must come from the vendored root.
If either fails, available == False (never assumed true from a file existing).

No private module imports, no algorithm re-implementation, no network.
Importing this module does not import dbfbridge; the package is loaded
lazily so that the Core Service stays importable anywhere.
"""

import os
import sys

from .. import config
from ..capabilities import BACKEND_DBFBRIDGE
from . import verify

# Vendored snapshot pin (architecturally pinned; must match VERSION.txt).
EXPECTED_UPSTREAM_COMMIT = "addbadb9281914661bf742924f45039e46a895cd"
PUBLIC_API = ("export_dbf", "reconstruct_dbf", "verify_conversion",
              "check_conversion_quality")


def _ensure_vendored_on_path(override_root=None):
    """Prepend the vendored tools/dbfbridge dir to sys.path (idempotent)."""
    vendored = config.dbfbridge_vendored_dir(override_root)
    if not os.path.isdir(os.path.join(vendored, "dbf_bridge")):
        return vendored, False
    path = os.path.abspath(vendored)
    if path not in sys.path:
        sys.path.insert(0, path)
    return vendored, True


class DBFBridgeBackend(object):
    """Stable adapter over the vendored dbfbridge public API."""

    name = "dbfbridge"
    backend = BACKEND_DBFBRIDGE

    def __init__(self, root=None):
        # root: optional repository-root override (tests / per-project later).
        self._root = root

    def _module(self):
        """Import the vendored dbfbridge package (lazy; no side effects)."""
        _vendored, ok = _ensure_vendored_on_path(self._root)
        if not ok:
            raise ImportError("vendored dbfbridge snapshot not found at %s"
                              % config.dbfbridge_vendored_dir(self._root))
        import dbfbridge  # public package
        return dbfbridge

    def status(self):
        """Availability + provenance report (PURE_READ, no VFP, no DBF open).

        Fail-closed: available requires BOTH a working public API AND a
        verified pin AND a verified module origin.
        """
        vendored_root = config.dbfbridge_vendored_dir(self._root)
        prov = verify.verify_provenance(vendored_root, EXPECTED_UPSTREAM_COMMIT)
        meta = dict(prov)
        meta["expectedUpstreamCommit"] = EXPECTED_UPSTREAM_COMMIT
        meta["upstreamCommit"] = prov.get("recordedCommit")

        mod_origin_ok = False
        try:
            mod = self._module()
        except Exception as e:
            meta.update({"available": False, "vendored": prov["vendoredDirPresent"],
                         "version": None, "publicApiOk": False,
                         "moduleOriginVerified": False, "error": str(e)})
            return meta

        ok_api = all(hasattr(mod, n) for n in PUBLIC_API)
        mod_origin_ok = verify.module_origin_verified(mod, vendored_root)
        pin_ok = prov["pinVerified"]
        available = bool(ok_api and pin_ok and mod_origin_ok)

        meta.update({
            "available": available,
            "vendored": bool(prov["vendoredDirPresent"]) and mod_origin_ok,
            "version": getattr(mod, "__version__", None),
            "publicApi": {n: hasattr(mod, n) for n in PUBLIC_API},
            "publicApiOk": ok_api,
            "pinVerified": pin_ok,
            "moduleOriginVerified": mod_origin_ok,
            "moduleFile": getattr(mod, "__file__", None),
            "vendoredRoot": os.path.abspath(vendored_root),
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
