# -*- coding: utf-8 -*-
"""
config.py - read-only access to the toolchain configuration (config.json).

The Core Service reads the same config.json used by the legacy CLI modules
(vfp_common.py). This module is a thin, side-effect-free reader that:
  * resolves the repository root (src/vfp_toolchain/config.py -> root),
  * parses config.json on demand (read-only usage),
  * provides typed getters with documented fallbacks.

No network, no VFP, no file creation. Import is side-effect free.
"""

import json
import os


def repo_root(override=None):
    """Absolute path of the repository root (parent of src/).

    ``override`` (optional) lets tests / future per-project sessions point the
    whole resolver at a different root. No side effects.
    """
    if override:
        return os.path.abspath(override)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def config_path(override_root=None):
    """Absolute path to config.json."""
    return os.path.join(repo_root(override_root), "config.json")


# Read-only, per-root record of the most recent config load problem (or None).
_last_error = {}


def load_config(override_root=None):
    """Parse config.json. Returns {} on any error (read-only, fail-soft).

    If the file is present but unparseable, the caller is told via
    ``config_error()`` so a corrupt config can be surfaced as PARTIAL instead
    of silently falling back.
    """
    key = override_root or "_default"
    path = config_path(override_root)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _last_error[key] = None
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        _last_error[key] = str(e)
        return {}


def config_error(override_root=None):
    """Last config load error for a root (None = no error / not loaded)."""
    return _last_error.get(override_root or "_default")


def target_dialect(override_root=None):
    cfg = load_config(override_root)
    return (cfg.get("target") or {}).get("dialect", "microsoft.visual-foxpro.9.0.sp2")


def vfp_exe_candidate(override_root=None):
    """Resolve the configured VFP9 executable path (existence NOT checked).

    Precedence (mirrors vfp_driver._vfp9_exe):
      1. VFP9_EXE env var
      2. config.vfp.exeEnvironmentVariable -> value of that env var
      3. config.vfp.exeDefault
      4. documented default location
    """
    cfg = load_config(override_root)
    v = cfg.get("vfp") or {}
    env_name = v.get("exeEnvironmentVariable", "VFP9_EXE")
    exe = os.environ.get(env_name)
    if not exe:
        exe = v.get("exeDefault") or os.path.join(
            "C:\\Program Files (x86)", "Microsoft Visual FoxPro 9", "vfp9.exe")
    return exe


def foxbin2prg_program(override_root=None):
    """Resolve the configured foxbin2prg.prg path (existence NOT checked)."""
    cfg = load_config(override_root)
    fb = cfg.get("foxbin2prg") or {}
    program_file = fb.get("programFile") or "foxbin2prg.prg"
    d = os.environ.get(fb.get("directoryEnvironmentVariable", "VFP_FOXBIN2PRG_DIR"))
    if not d:
        d = fb.get("directoryDefault") or os.path.join("tools", "foxbin2prg")
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(repo_root(override_root), d))
    return os.path.join(d, program_file)


def dbfbridge_vendored_dir(override_root=None):
    cfg = load_config(override_root)
    db = cfg.get("dbfbridge") or {}
    d = db.get("directory") or os.path.join("tools", "dbfbridge")
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(repo_root(override_root), d))
    return d


def default_excludes(override_root=None):
    """Canonical directory exclusion list (lowercase names), from config.json."""
    cfg = load_config(override_root)
    raw = cfg.get("defaultExcludes") or []
    items = tuple((x or "").strip().lower() for x in raw if x and str(x).strip())
    return items or (
        ".git", ".vfp-ai", "backup", "backups", "archive", "tmp",
        "node_modules", "__pycache__",
    )


def detect_extensions(override_root=None):
    """Canonical VFP artifact detection extensions (config.artifacts.detect)."""
    cfg = load_config(override_root)
    arts = cfg.get("artifacts") or {}
    raw = arts.get("detect") or []
    exts = []
    for item in raw:
        s = str(item).strip().lower()
        if not s:
            continue
        if not s.startswith("."):
            s = "." + s
        exts.append(s)
    return tuple(exts)


__all__ = [
    "repo_root", "config_path", "load_config", "target_dialect",
    "vfp_exe_candidate", "foxbin2prg_program", "dbfbridge_vendored_dir",
    "default_excludes", "detect_extensions",
]
