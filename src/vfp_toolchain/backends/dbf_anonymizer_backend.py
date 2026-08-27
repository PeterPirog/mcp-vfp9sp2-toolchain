# -*- coding: utf-8 -*-
"""
backends/dbf_anonymizer_backend.py - adapter for the vendored DBF_Anonymizer.

Loads the vendored snapshot under tools/dbf_anonymizer/ (pinned — see
tools/dbf_anonymizer/VERSION.txt) WITHOUT installing anything and WITHOUT
network access. The package imports `dbfbridge`; the toolchain guarantees
the vendored tools/dbfbridge snapshot is on sys.path first (single shared
dbfbridge, per docs/ANONYMIZATION_INTEGRATION.md §18).

This PR exposes READ-ONLY status only. The mutating wrappers
(anonymize_directory / make_dbf_recovery / self_test) are present as
prepared adapters but are NOT published as OpenCode/CLI tools yet —
production anonymization is the next phase.
"""

import os
import sys

from .. import config
from .dbfbridge_backend import DBFBridgeBackend, _ensure_vendored_on_path

_VENDORED_DIRNAME = "tools" + os.sep + "dbf_anonymizer"

EXPECTED_UPSTREAM_COMMIT = "ed7915497862850c3de650f2c50c86569442ff77"
EXPECTED_VERSION = "0.3.0"
REQUIRED_DBFBRIDGE_COMMIT = "addbadb9281914661bf742924f45039e46a895cd"
PUBLIC_API = ("anonymize_directory", "make_dbf_recovery", "self_test")


def _vendored_dir():
    d = os.path.join(config.repo_root(), _VENDORED_DIRNAME.replace("/", os.sep))
    return os.path.normpath(d)


def _ensure_on_path():
    """Put the vendored dbf_anonymizer on sys.path (idempotent).

    Order matters: the vendored dbfbridge must be first so the anonymizer's
    `import dbfbridge` resolves to the same pinned snapshot.
    """
    _ensure_vendored_on_path()
    vendored = _vendored_dir()
    pkg_dir = os.path.join(vendored, "dbf_anonymizer")
    if not os.path.isdir(pkg_dir):
        return False
    path = os.path.abspath(vendored)
    if path not in sys.path:
        sys.path.insert(0, path)
    return True


def _normalize_commit(raw):
    """Normalize a commit reference (strip URL/env decorations, lowercase)."""
    s = str(raw or "").strip().lower()
    if "@" in s:
        s = s.rsplit("@", 1)[-1]
    return s


def _commits_compatible(actual, expected):
    """Prefix-based commit compatibility (short SHAs are allowed).

    The vendored dbfbridge VERSION.txt records a short SHA ("addbadb") while
    the anonymizer pin is the full SHA. Compatible when the shorter of the
    two is a prefix of the longer (minimum 7 chars, git convention).
    """
    a = _normalize_commit(actual)
    e = _normalize_commit(expected)
    if not a or not e:
        return False
    short, long = (a, e) if len(a) <= len(e) else (e, a)
    return len(short) >= 7 and long.startswith(short)


class DBFAnonymizerBackend(object):
    """Read-only adapter over the vendored DBF_Anonymizer 0.3.0."""

    name = "dbf_anonymizer"
    backend = "DBF_ANONYMIZER"

    def _module(self):
        """Import the vendored dbf_anonymizer package (lazy; no side effects).

        Importing dbf_anonymizer must NOT anonymize anything or create a
        dictionary — all mutations happen only when a pipeline call runs.
        """
        if not _ensure_on_path():
            raise ImportError("vendored DBF_Anonymizer snapshot not found at %s"
                              % _vendored_dir())
        import dbf_anonymizer  # public package
        return dbf_anonymizer

    def _read_version_txt(self):
        path = os.path.join(_vendored_dir(), "VERSION.txt")
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
        """Read-only status report (PURE_READ, no VFP, no anonymization)."""
        meta = dict(self._read_version_txt())
        meta["expectedVersion"] = EXPECTED_VERSION
        meta["expectedUpstreamCommit"] = EXPECTED_UPSTREAM_COMMIT
        meta["dbfbridgeRequiredCommit"] = REQUIRED_DBFBRIDGE_COMMIT

        dbfbridge_meta = DBFBridgeBackend().status()
        meta["dbfbridgeCompatible"] = _commits_compatible(
            str(dbfbridge_meta.get("upstreamCommit", "")),
            REQUIRED_DBFBRIDGE_COMMIT)

        try:
            mod = self._module()
        except Exception as e:
            meta.update({"available": False, "vendored": False, "version": None,
                         "publicApiOk": False, "recoveryCapabilityPresent": False,
                         "error": str(e)})
            return meta

        version = getattr(mod, "__version__", None)
        api_ok = all(hasattr(mod, n) for n in PUBLIC_API)
        meta.update({
            "available": api_ok and version == EXPECTED_VERSION,
            "vendored": True,
            "version": version,
            "publicApi": {n: hasattr(mod, n) for n in PUBLIC_API},
            "publicApiOk": api_ok,
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
