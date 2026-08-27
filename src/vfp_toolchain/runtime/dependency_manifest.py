# -*- coding: utf-8 -*-
"""
runtime/dependency_manifest.py - machine-readable runtime dependency lock.

Loads runtime/runtime-dependencies.json (the pinned, reproducible dependency
set) and verifies a local wheelhouse against it:
  * every locked wheel file is present,
  * its SHA256 matches the locked hash.

This module is PURE_READ: it only reads the manifest and the wheelhouse
directory. It never installs, never touches the network.

Wheel selection for the current interpreter:
  * pure-Python wheels (`py3-none-any` / `py2.py3-none-any`) match every
    supported Python,
  * a native wheel matches when its platform tag is `win_amd64` (or `any`)
    AND its CPython tag equals the current one (cp310/cp312/cp314) or is
    abi3 (cp310-abi3 covers 3.10/3.12/3.14).
"""

import json
import os
import sys


def _sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _current_cptag():
    v = sys.version_info
    return "cp%d%d" % (v.major, v.minor)


def _wheel_matches_python(filename, supported_python=None):
    """True if the wheel filename is usable on the given CPython/Windows.

    filename like 'orjson-3.12.0-cp310-cp310-win_amd64.whl' or
    'polars_runtime_32-1.44.1-cp310-abi3-win_amd64.whl' or
    'dbfread-2.0.7-py2.py3-none-any.whl'.

    ``supported_python`` is (major, minor) or None (current interpreter).
    """
    base = filename[:-4] if filename.endswith(".whl") else filename
    parts = base.split("-")
    if len(parts) < 5:
        return False
    py_tags = parts[-3].split(".")
    abi_tags = parts[-2].split(".")
    plat_tags = parts[-1].split(".")
    # platform must allow Windows
    if not ("any" in plat_tags or "win_amd64" in plat_tags):
        return False
    cp = _current_cptag() if supported_python is None else "cp%d%d" % supported_python
    # python tag: py3/py2/any covers all supported interpreters
    if "py3" in py_tags or "py2" in py_tags or "any" in py_tags:
        return True
    if cp in py_tags:
        return True
    # cpXXX-abi3: the ABI floor in the python tag must be <= current
    if "abi3" in abi_tags:
        floor = [t for t in py_tags if t.startswith("cp")]
        if floor:
            f, c = floor[0][2:], cp[2:]
            return f.isdigit() and c.isdigit() and int(f) <= int(c)
        return True
    return False


def load_manifest(manifest_path):
    """Parse the lock manifest (read-only). Returns dict or None on error."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def locked_wheels_for_python(manifest, supported_python=None):
    """Flatten the manifest into the set of wheel files needed on this host.

    Returns a dict filename -> expected_sha256 (lowercase) for wheels that
    match the requested/supported Python (None = current interpreter).
    """
    out = {}  # type: dict
    if not manifest:
        return out
    for dep in manifest.get("dependencies", []):
        for fname, expected in (dep.get("hashes") or {}).items():
            if not _wheel_matches_python(fname, supported_python):
                continue
            out[fname] = str(expected).strip().lower()
    return out


def verify_wheelhouse(manifest, wheelhouse_dir, supported_python=None):
    """Verify a wheelhouse directory against the locked manifest.

    Returns:
        verified  bool  — every locked wheel present with a matching SHA256
        missing   [str] — locked wheel files not present
        mismatched[dict] — {filename, expectedSha256, actualSha256}
        files     int   — number of locked wheels checked
        ok        [str] — verified files

    Fail-closed: a missing or corrupt wheelhouse reports verified=False.
    """
    locked = locked_wheels_for_python(manifest, supported_python)
    missing, mismatched, ok = [], [], []
    if not wheelhouse_dir or not os.path.isdir(wheelhouse_dir):
        return {
            "verified": False,
            "missing": sorted(locked.keys()),
            "mismatched": [],
            "files": len(locked),
            "ok": [],
        }
    for fname, expected in sorted(locked.items()):
        path = os.path.join(wheelhouse_dir, fname)
        if not os.path.isfile(path):
            missing.append(fname)
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatched.append({"filename": fname,
                               "expectedSha256": expected,
                               "actualSha256": actual})
        else:
            ok.append(fname)
    return {
        "verified": not missing and not mismatched,
        "missing": missing,
        "mismatched": mismatched,
        "files": len(locked),
        "ok": ok,
    }


__all__ = [
    "load_manifest",
    "locked_wheels_for_python",
    "verify_wheelhouse",
    "_sha256_file",
]
