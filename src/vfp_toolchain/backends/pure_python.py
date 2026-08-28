# -*- coding: utf-8 -*-
"""
backends/pure_python.py - PURE_READ backend (no VFP, no network).

Wraps the existing first-party logic (vfp_common, vfp_safety, vfp_dbf_export)
instead of copying it. All operations here are read-only and must work on a
machine without Visual FoxPro, FoxBin2Prg, COM or Bun.
"""

import os
import sys

from .. import config
from ..capabilities import BACKEND_PURE_PYTHON, Capability

_HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(_HERE)


def _ensure_repo_on_path():
    """Make the legacy first-party modules importable without side effects."""
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)


class PurePythonBackend(object):
    """PURE_READ operations that require neither VFP nor third-party code."""

    name = "pure_python"
    backend = BACKEND_PURE_PYTHON

    def __init__(self, root=None):
        # root: canonical toolchain root (repo or bundle app/) — overrides the
        # module-relative resolution so a bundle app/ is self-contained.
        self._root = root

    def status(self):
        """Availability report (always available — pure Python stdlib)."""
        return {"available": True, "vendored": False, "backend": self.backend}

    # -- project detection (single source of truth, replaces tools/vfp.ts walk)

    def detect_project(self, directory, root=None):
        """Detect VFP project artifacts under `directory` (PURE_READ).

        Uses config.artifacts.detect (config.json) as the single source of
        truth for extensions and config.defaultExcludes for the walk.
        ``root`` (or the instance root) selects which config.json is read,
        so a canonical bundle app/ root is self-contained.
        Never writes to the source tree.

        Returns (data, warnings) for the service layer to envelope.
        """
        _ensure_repo_on_path()
        import vfp_common  # legacy helper: should_skip_dir (canonical excludes)

        effective_root = root or self._root
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            return None, ["directory not found: %s" % directory]

        exts = config.detect_extensions(effective_root)
        counts = {}
        total = 0
        cache_exists = False
        file_count = 0

        for root, dirs, files in os.walk(directory):
            if ".vfp-ai" in dirs:
                cache_exists = True
            dirs[:] = [d for d in dirs if not vfp_common.should_skip_dir(d)]
            for fn in files:
                file_count += 1
                low = fn.lower()
                ext = os.path.splitext(low)[1]
                if ext in exts:
                    counts[ext] = counts.get(ext, 0) + 1
                    total += 1

        data = {
            "directory": directory,
            "totalVfpFiles": total,
            "fileCount": file_count,
            "byExtension": {k: counts[k] for k in sorted(counts)},
            "cacheExists": cache_exists,
            "vfpDetected": total > 0 or cache_exists,
        }
        return data, []

    # -- artifact inventory (counts of detected families, no VFP)

    def artifact_inventory(self, directory):
        """Group detected artifact counts by family (PURE_READ, read-only)."""
        data, warnings = self.detect_project(directory)
        if data is None:
            return None, warnings
        families = {
            "dbf": [".dbf", ".fpt", ".cdx", ".idx"],
            "forms": [".scx", ".sct", ".sc2"],
            "classes": [".vcx", ".vct", ".vc2"],
            "reports": [".frx", ".frt", ".fr2"],
            "labels": [".lbx", ".lbt", ".lb2"],
            "menus": [".mnx", ".mnt", ".mn2", ".mpr", ".mpx"],
            "projects": [".pjx", ".pjt", ".pj2"],
            "databases": [".dbc", ".dct", ".dcx", ".dc2"],
            "code": [".prg", ".h", ".mpr"],
            "other": [],
        }
        by_ext = data["byExtension"]
        inventory = {}
        seen = set()
        for family, members in families.items():
            vals = [m for m in members if m in by_ext]
            if vals:
                inventory[family] = {m: by_ext[m] for m in vals}
                seen.update(vals)
        other = {k: v for k, v in by_ext.items() if k not in seen}
        if other:
            inventory["other"] = other
        data["families"] = inventory
        return data, warnings

    # -- config reading

    def read_config(self):
        """Return the parsed toolchain config.json (PURE_READ)."""
        return config.load_config(), []

    # -- hash/snapshot primitives (delegated to vfp_safety, no VFP)

    def snapshot_files(self, paths):
        """SHA256 manifest of the given files via vfp_safety (PURE_READ)."""
        _ensure_repo_on_path()
        import vfp_safety

        existing = [p for p in paths if os.path.isfile(p)]
        if not existing:
            return None, ["no existing files given to snapshot"]
        guard = vfp_safety.SourceHashGuard(existing)
        manifest = guard.capture()
        return manifest, []

    # -- dbfbridge capability (delegated to the dbfbridge backend)

    def dbfbridge_capability(self):
        from .dbfbridge_backend import DBFBridgeBackend
        return DBFBridgeBackend().status(), []


__all__ = ["PurePythonBackend"]
