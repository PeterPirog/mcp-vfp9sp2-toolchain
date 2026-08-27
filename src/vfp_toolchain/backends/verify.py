# -*- coding: utf-8 -*-
"""
backends/verify.py - shared, fail-closed provenance verification for vendored
dependencies (dbfbridge and DBF_Anonymizer).

Two independent checks, both fail-closed:

1. PIN VERIFICATION
   The expected upstream commit (a hard constant in each backend, the
   architecturally pinned value) must match the commit recorded in the
   dependency's VERSION.txt provenance file. The mere existence of a
   VERSION.txt file is NOT evidence of compatibility — the recorded value must
   actually agree with the expected pin (short-SHA prefixes allowed, git
   convention). If they disagree -> pinVerified == False -> available == False.

2. MODULE ORIGIN VERIFICATION
   After importing a vendored package, ``module.__file__`` must resolve to a
   path that lies under the expected vendored root (tools/dbfbridge/ or
   tools/dbf_anonymizer/). This catches the case where a global/installed
   copy of the package is already present in ``sys.modules`` and ``sys.path
   .insert`` silently loses to it. The status probe DETECTS the conflict and
   reports moduleOriginVerified == False; it does not mutate sys.modules.

This module performs NO imports of the vendored packages and NO network.
"""

import os


def normalize_commit(raw):
    """Lowercase a commit reference and strip URL/@ decorations."""
    s = str(raw or "").strip().lower()
    if "@" in s:
        s = s.rsplit("@", 1)[-1]
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    return s


def commits_compatible(actual, expected):
    """True when the two commit references are the same SHA.

    Short-SHA prefixes (>= 7 chars, git convention) are accepted. Both must be
    non-empty. Comparing an empty value against anything is a mismatch
    (fail-closed).
    """
    a = normalize_commit(actual)
    e = normalize_commit(expected)
    if not a or not e:
        return False
    short, long_ = (a, e) if len(a) <= len(e) else (e, a)
    return len(short) >= 7 and long_.startswith(short)


def module_under_root(module_file, vendored_root):
    """True if ``module_file`` (a path) lies under ``vendored_root``.

    Canonicalizes both (case-insensitive on Windows) so symlink/junction and
    case differences do not produce false positives or negatives.
    """
    if not module_file or not vendored_root:
        return False
    try:
        m = os.path.realpath(os.path.abspath(str(module_file)))
        r = os.path.realpath(os.path.abspath(str(vendored_root)))
    except (OSError, ValueError):
        return False
    if os.name == "nt":
        m, r = m.lower().replace("/", "\\"), r.lower().replace("/", "\\")
        r = r.rstrip("\\")
        return m == r or m.startswith(r + "\\")
    m, r = m.lower().replace("\\", "/"), r.lower().replace("\\", "/")
    r = r.rstrip("/")
    return m == r or m.startswith(r + "/")


def module_origin_verified(module, vendored_root):
    """Fail-closed check that an imported module comes from the vendored root."""
    if module is None:
        return False
    module_file = getattr(module, "__file__", None)
    return module_under_root(module_file, vendored_root)


def verify_provenance(vendored_root, expected_commit, version_file_name="VERSION.txt"):
    """Check that the vendored dir exists and its provenance file pins the SHA.

    Returns a dict:
        vendoredDirPresent  bool
        versionFile         str|None
        recordedCommit      str|None
        expectedCommit      str
        pinVerified         bool   (fail-closed)
    """
    out = {
        "vendoredDirPresent": bool(vendored_root) and os.path.isdir(vendored_root),
        "versionFile": None,
        "recordedCommit": None,
        "expectedCommit": expected_commit,
        "pinVerified": False,
    }
    if not out["vendoredDirPresent"]:
        return out
    vfile = os.path.join(vendored_root, version_file_name)
    if not os.path.isfile(vfile):
        return out
    out["versionFile"] = vfile
    try:
        with open(vfile, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return out
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            stripped = stripped.lstrip("# ").strip()
        low = stripped.lower()
        if low.startswith("commit"):
            parts = stripped.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                out["recordedCommit"] = parts[1].strip()
    out["pinVerified"] = commits_compatible(out["recordedCommit"], expected_commit)
    return out


__all__ = [
    "normalize_commit",
    "commits_compatible",
    "module_under_root",
    "module_origin_verified",
    "verify_provenance",
]
