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


def repo_root():
    """Absolute path of the repository root (parent of src/)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def config_path():
    """Absolute path to config.json."""
    return os.path.join(repo_root(), "config.json")


def load_config():
    """Parse config.json. Returns {} on any error (read-only, fail-soft)."""
    path = config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def target_dialect():
    cfg = load_config()
    return (cfg.get("target") or {}).get("dialect", "microsoft.visual-foxpro.9.0.sp2")


def vfp_exe_candidate():
    """Resolve the configured VFP9 executable path (existence NOT checked).

    Precedence (mirrors vfp_driver._vfp9_exe):
      1. VFP9_EXE env var
      2. config.vfp.exeEnvironmentVariable -> value of that env var
      3. config.vfp.exeDefault
      4. documented default location
    """
    cfg = load_config()
    v = cfg.get("vfp") or {}
    env_name = v.get("exeEnvironmentVariable", "VFP9_EXE")
    exe = os.environ.get(env_name)
    if not exe:
        exe = v.get("exeDefault") or os.path.join(
            "C:\\Program Files (x86)", "Microsoft Visual FoxPro 9", "vfp9.exe")
    return exe


def foxbin2prg_program():
    """Resolve the configured foxbin2prg.prg path (existence NOT checked)."""
    cfg = load_config()
    fb = cfg.get("foxbin2prg") or {}
    program_file = fb.get("programFile") or "foxbin2prg.prg"
    d = os.environ.get(fb.get("directoryEnvironmentVariable", "VFP_FOXBIN2PRG_DIR"))
    if not d:
        d = fb.get("directoryDefault") or os.path.join("tools", "foxbin2prg")
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(repo_root(), d))
    return os.path.join(d, program_file)


def dbfbridge_vendored_dir():
    cfg = load_config()
    db = cfg.get("dbfbridge") or {}
    d = db.get("directory") or os.path.join("tools", "dbfbridge")
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(repo_root(), d))
    return d


def default_excludes():
    """Canonical directory exclusion list (lowercase names), from config.json."""
    cfg = load_config()
    raw = cfg.get("defaultExcludes") or []
    items = tuple((x or "").strip().lower() for x in raw if x and str(x).strip())
    return items or (
        ".git", ".vfp-ai", "backup", "backups", "archive", "tmp",
        "node_modules", "__pycache__",
    )


def detect_extensions():
    """Canonical VFP artifact detection extensions (config.artifacts.detect)."""
    cfg = load_config()
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
