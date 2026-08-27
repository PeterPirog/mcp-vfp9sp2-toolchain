# -*- coding: utf-8 -*-
"""
backends/dbf_anonymizer_backend.py - adapter for the vendored DBF_Anonymizer.

Loads the vendored snapshot under tools/dbf_anonymizer/ (pinned — see
tools/dbf_anonymizer/VERSION.txt) WITHOUT installing anything and WITHOUT
network access. The package imports `dbfbridge`; the toolchain guarantees
the vendored tools/dbfbridge snapshot is on sys.path first (single shared
dbfbridge, per docs/ANONYMIZATION_INTEGRATION.md §18).

Fail-closed verification (backends/verify.py):
  available == True ONLY when ALL of:
    publicApiOk            (anonymize_directory, make_dbf_recovery, self_test)
    version == 0.3.0
    pinVerified            (VERSION.txt upstream commit == pinned commit)
    dbfbridgeCompatible    (shared vendored dbfbridge pins the required commit)
    moduleOriginVerified   (imported module comes from the vendored root)
  If any fails -> available == False. status() NEVER runs the mutating
  pipeline functions; it stays PURE_READ.

This PR exposes READ-ONLY status only. The mutating wrappers
(anonymize_directory / make_dbf_recovery / self_test) are present as
prepared adapters but are NOT published as OpenCode/CLI tools yet —
production anonymization is the next phase.
"""

import os
import sys

from .. import config
from . import verify
from .dbfbridge_backend import DBFBridgeBackend, _ensure_vendored_on_path

_VENDORED_DIRNAME = "tools" + os.sep + "dbf_anonymizer"

EXPECTED_UPSTREAM_COMMIT = "ed7915497862850c3de650f2c50c86569442ff77"
EXPECTED_VERSION = "0.3.0"
REQUIRED_DBFBRIDGE_COMMIT = "addbadb9281914661bf742924f45039e46a895cd"
PUBLIC_API = ("anonymize_directory", "make_dbf_recovery", "self_test")


def _vendored_dir(override_root=None):
    d = os.path.join(config.repo_root(override_root),
                     _VENDORED_DIRNAME.replace("/", os.sep))
    return os.path.normpath(d)


def _ensure_on_path(override_root=None):
    """Put the vendored dbf_anonymizer on sys.path (idempotent).

    Order matters: the vendored dbfbridge must be first so the anonymizer's
    `import dbfbridge` resolves to the same pinned snapshot.
    """
    _ensure_vendored_on_path(override_root)
    vendored = _vendored_dir(override_root)
    pkg_dir = os.path.join(vendored, "dbf_anonymizer")
    if not os.path.isdir(pkg_dir):
        return vendored, False
    path = os.path.abspath(vendored)
    if path not in sys.path:
        sys.path.insert(0, path)
    return vendored, True


class DBFAnonymizerBackend(object):
    """Read-only adapter over the vendored DBF_Anonymizer 0.3.0."""

    name = "dbf_anonymizer"
    backend = "DBF_ANONYMIZER"

    def __init__(self, root=None):
        # root: optional repository-root override (tests / per-project later).
        self._root = root

    def _module(self):
        """Import the vendored dbf_anonymizer package (lazy; no side effects).

        Importing dbf_anonymizer must NOT anonymize anything or create a
        dictionary — all mutations happen only when a pipeline call runs.
        """
        _vendored, ok = _ensure_on_path(self._root)
        if not ok:
            raise ImportError("vendored DBF_Anonymizer snapshot not found at %s"
                              % _vendored_dir(self._root))
        import dbf_anonymizer  # public package
        return dbf_anonymizer

    def _read_version_txt(self):
        path = os.path.join(_vendored_dir(self._root), "VERSION.txt")
        info = {"versionFile": path if os.path.isfile(path) else None}  # type: dict
        if not os.path.isfile(path):
            return info
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return info
        for line in text.splitlines():
            low = line.strip().lstrip("# ").strip().lower()
            if low.startswith("upstream commit"):
                info["upstreamCommit"] = line.split(":", 1)[1].strip()
            elif low.startswith("upstream version"):
                info["upstreamVersion"] = line.split(":", 1)[1].strip()
            elif low.startswith("vendored date"):
                info["vendoredDate"] = line.split(":", 1)[1].strip()
            elif low.startswith("dbfbridge required"):
                info["dbfbridgeRequired"] = line.split(":", 1)[1].strip()
        return info

    def status(self):
        """Read-only status report (PURE_READ, no VFP, no anonymization).

        Fail-closed: `available` is True only when the public API, the
        pinned version, the pinned upstream commit, dbfbridge compatibility
        AND the module origin all verify.
        """
        vendored_root = _vendored_dir(self._root)
        meta = dict(self._read_version_txt())
        meta["expectedVersion"] = EXPECTED_VERSION
        meta["expectedUpstreamCommit"] = EXPECTED_UPSTREAM_COMMIT
        meta["dbfbridgeRequiredCommit"] = REQUIRED_DBFBRIDGE_COMMIT
        meta["vendoredRoot"] = os.path.abspath(vendored_root)

        # Pin verification against the recorded upstream commit (fail-closed).
        pin_ok = verify.commits_compatible(
            meta.get("upstreamCommit"), EXPECTED_UPSTREAM_COMMIT)
        meta["pinVerified"] = pin_ok

        # Shared dbfbridge compatibility (single vendored snapshot).
        dbfbridge_meta = DBFBridgeBackend(root=self._root).status()
        dbfbridge_ok = (
            bool(dbfbridge_meta.get("available", False))
            and verify.commits_compatible(
                str(dbfbridge_meta.get("recordedCommit")
                   or dbfbridge_meta.get("upstreamCommit", "")),
                REQUIRED_DBFBRIDGE_COMMIT))
        meta["dbfbridgeCompatible"] = dbfbridge_ok

        try:
            mod = self._module()
        except Exception as e:
            meta.update({"available": False, "vendored": False, "version": None,
                         "publicApiOk": False, "moduleOriginVerified": False,
                         "recoveryCapabilityPresent": False,
                         "error": str(e)})
            return meta

        version = getattr(mod, "__version__", None)
        api_ok = all(hasattr(mod, n) for n in PUBLIC_API)
        origin_ok = verify.module_origin_verified(mod, vendored_root)
        version_ok = (version == EXPECTED_VERSION)
        available = bool(api_ok and version_ok and pin_ok and dbfbridge_ok
                         and origin_ok)

        meta.update({
            "available": available,
            "vendored": bool(meta.get("versionFile") and origin_ok),
            "version": version,
            "versionVerified": version_ok,
            "publicApi": {n: hasattr(mod, n) for n in PUBLIC_API},
            "publicApiOk": api_ok,
            "moduleOriginVerified": origin_ok,
            "moduleFile": getattr(mod, "__file__", None),
            "recoveryCapabilityPresent": hasattr(mod, "make_dbf_recovery"),
            "vfpRequired": False,
        })
        return meta

    def version(self):
        return getattr(self._module(), "__version__", None)

    def public_api_available(self):
        try:
            mod = self._module()
        except Exception:
            return False
        return all(hasattr(mod, n) for n in PUBLIC_API)

    # -- prepared (NOT yet published as mutating tools in this PR) ----------

    def anonymize_directory(self, *args, **kwargs):
        """PREPARED wrapper — not exposed as a tool in Phase 1."""
        return self._module().anonymize_directory(*args, **kwargs)

    def make_dbf_recovery(self, *args, **kwargs):
        """PREPARED wrapper — restricted/high-risk, not exposed in Phase 1."""
        return self._module().make_dbf_recovery(*args, **kwargs)

    def self_test(self, *args, **kwargs):
        """PREPARED wrapper — diagnostic, not exposed in Phase 1."""
        return self._module().self_test(*args, **kwargs)


__all__ = [
    "DBFAnonymizerBackend",
    "PUBLIC_API",
    "EXPECTED_UPSTREAM_COMMIT",
    "EXPECTED_VERSION",
    "REQUIRED_DBFBRIDGE_COMMIT",
]
