#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_common.py - shared constants and helpers for the VFP toolchain.

Canonical exclusion list (single source of truth). The list lives in
config.json under "defaultExcludes"; this module reads it and falls back
to a hard-coded default if the config is missing. TypeScript tooling in
tools/vfp.ts must keep the same list in sync (see the comment there).
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_HERE, "config.json")

# Hard-coded fallback (used when config.json is unavailable or malformed).
_DEFAULT_EXCLUDES = (
    ".git",
    ".vfp-ai",
    "backup",
    "backups",
    "archive",
    "tmp",
    "node_modules",
    "__pycache__",
)


def _load_config():
    """Load config.json from this package dir, or None on any error."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def default_excludes():
    """Return the canonical exclusion list as a tuple of lowercase names."""
    cfg = _load_config()
    raw = (cfg or {}).get("defaultExcludes") or []
    items = tuple((x or "").strip().lower() for x in raw if x and x.strip())
    return items or _DEFAULT_EXCLUDES


def should_skip_dir(name):
    """True if a directory name should be skipped during a project walk."""
    if not name:
        return True
    # Never descend into dot-directories (covers .git, .vfp-ai, .opencode …)
    if name.startswith("."):
        return True
    return name.lower() in default_excludes()


def foxbin2prg_program():
    """Resolve the full path to foxbin2prg.prg from config.json.

    Precedence:
      1. Environment variable VFP_FOXBIN2PRG_DIR
      2. config.foxbin2prg.directoryEnvironmentVariable (value of that env var)
      3. config.foxbin2prg.directoryDefault (relative to this package's dir)
      4. Fallback: tools/foxbin2prg

    Returns the full path to <dir>/<programFile> even if it does not exist —
    callers should check with os.path.isfile before use.
    """
    cfg = _load_config() or {}
    fb = cfg.get("foxbin2prg") or {}
    program_file = fb.get("programFile") or "foxbin2prg.prg"

    d = os.environ.get("VFP_FOXBIN2PRG_DIR")
    if not d:
        env_name = fb.get("directoryEnvironmentVariable")
        if env_name:
            d = os.environ.get(env_name)
    if not d:
        d = fb.get("directoryDefault") or os.path.join("tools", "foxbin2prg")
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(_HERE, d))
    return os.path.join(d, program_file)


# Binary companion/memo files that belong next to the primary VFP artifact.
# IMPORTANT: .lb2 is FoxBin2Prg's text representation of a label; the binary
# Label Designer companion of .lbx is .lbt.
COMPANIONS = {
    ".scx": (".sct",),
    ".vcx": (".vct",),
    ".frx": (".frt",),
    ".mnx": (".mnt",),
    ".pjx": (".pjt",),
    ".dbf": (".fpt",),
    ".lbx": (".lbt",),
    ".dbc": (".dcx", ".dct"),
}


def required_companions(binary_path):
    """Return the list of companion file paths required for a binary.

    A .dbf only *requires* its .fpt if the table declares memo fields; we cannot
    know that cheaply here, so callers should treat a missing .fpt as a
    *warning* (export may still work) rather than a hard failure.
    """
    ext = os.path.splitext(binary_path)[1].lower()
    base = os.path.splitext(binary_path)[0]
    return [base + c for c in COMPANIONS.get(ext, ())]


def missing_companions(binary_path):
    """Return companion files (per required_companions) that do not exist."""
    return [p for p in required_companions(binary_path) if not os.path.isfile(p)]
