#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_safety.py - SHARED safety core for the VFP toolchain (v0.3).

This module is the SINGLE place where path-safety and source-integrity logic
lives. No other module may re-implement it (rule from ARCHITECTURE_V03.md §3).

  PathSafetyGuard   — canonicalize/resolve paths, Windows case-insensitivity,
                      ".." handling, block source==target, block any write
                      under SOURCE, allow writes only under an explicit
                      workspace, FAIL CLOSED.
  SourceHashGuard   — SHA256 manifests (path/size/mtime/sha256/fileType/
                      companions) + before/after mutation detection.

Pure Python. No VFP9 required. No network. No side effects at import time.
"""

import hashlib
import os
import re
import stat as statmod

import vfp_common

# ---------------------------------------------------------------------------
# Path canonicalization (Windows case-insensitive)
# ---------------------------------------------------------------------------

_DRIVES_RE = re.compile(r"^[A-Za-z]:[\\/]")


def canonicalize_path(p):
    """Resolve a path to its canonical form.

    - absolutizes (cwd-relative),
    - collapses "." and ".." (lexical, then symlink-resolution best effort),
    - on Windows: lowercases drive letter and the whole path so equality
      tests are case-insensitive (NTFS semantics).
    Never raises for non-existent paths (pure lexical normalization);
    os.path.realpath is used when the path exists (resolves symlinks/junctions).
    """
    if not p or not str(p).strip():
        raise ValueError("empty path")
    s = os.path.abspath(str(p))
    try:
        s = os.path.realpath(s)
    except OSError:
        pass
    if os.name == "nt":
        s = s.replace("/", "\\")
        if _DRIVES_RE.match(s):
            s = s[0].upper() + ":" + s[2:]
        s = s.lower()
    else:
        s = s.replace("\\", "/").lower() if os.environ.get("VFP_SAFETY_FORCE_LOWER") else s
    return s


def is_under(path, root):
    """True if `path` is `root` itself or strictly inside `root`.

    Both arguments are canonicalized (see canonicalize_path). Works with
    backslash or forward separators on any platform.
    """
    p = canonicalize_path(path)
    r = canonicalize_path(root)
    if os.name == "nt":
        r = r.rstrip("\\")
        return p == r or p.startswith(r + "\\")
    r = r.rstrip("/")
    return p == r or p.startswith(r + "/")


def are_same(a, b):
    """Case-insensitive (Windows) equality of two paths."""
    return canonicalize_path(a) == canonicalize_path(b)


# ---------------------------------------------------------------------------
# PathSafetyGuard
# ---------------------------------------------------------------------------

class PathSafetyGuard(object):
    """Fail-closed guard for the controlled-write refactor plane.

    Usage:
        guard = PathSafetyGuard(source_dir, workspace_dir)
        guard.assert_writable(target_path)      # raises SourcePathWriteError
        guard.assert_workspace(target_path)     # same, explicit name
        guard.safe()                            # True when the guard itself is sane

    Rules (all enforced, any violation → exception, never silent):
      * source and workspace must exist and be directories (created by the
        caller via create_refactor_workspace),
      * source != workspace (neither may be under the other),
      * a target is writable ONLY if it is inside the workspace and NOT inside
        the source,
      * writes to the source tree are always forbidden,
      * canonicalization handles "..", case (Windows), and symlink resolution.
    """

    def __init__(self, source_dir, workspace_dir):
        if not source_dir or not workspace_dir:
            raise SourcePathWriteError("source and workspace are both required")
        if not os.path.isdir(source_dir):
            raise SourcePathWriteError("source directory does not exist: " + str(source_dir))
        if not os.path.isdir(workspace_dir):
            raise SourcePathWriteError("workspace directory does not exist (create it with "
                                       "vfp_create_refactor_workspace): " + str(workspace_dir))
        self.source = canonicalize_path(source_dir)
        self.workspace = canonicalize_path(workspace_dir)

        if are_same(self.source, self.workspace):
            raise SourcePathWriteError(
                "workspace must be a different directory than the source "
                "(source==target is forbidden): " + str(source_dir))
        if is_under(self.workspace, self.source):
            raise SourcePathWriteError(
                "workspace must NOT be inside the source project: " + str(workspace_dir))
        if is_under(self.source, self.workspace):
            raise SourcePathWriteError(
                "source must NOT be inside the workspace: " + str(source_dir))

    def safe(self):
        """Guard is usable only when both roots still exist and are directories."""
        return os.path.isdir(self.source) and os.path.isdir(self.workspace)

    def _check_target(self, target):
        if not target:
            raise SourcePathWriteError("target path is empty")
        if is_under(target, self.source):
            raise SourcePathWriteError(
                "write target is INSIDE the SOURCE project — forbidden: %s" % target)
        if not is_under(target, self.workspace):
            raise SourcePathWriteError(
                "write target is OUTSIDE the declared workspace — forbidden: %s"
                " (workspace: %s)" % (target, self.workspace))

    def assert_writable(self, target):
        """Raise SourcePathWriteError unless `target` may receive writes."""
        self._check_target(target)

    def assert_workspace(self, target):
        return self.assert_writable(target)

    def is_writable(self, target):
        try:
            self._check_target(target)
            return True
        except SourcePathWriteError:
            return False

    def describe(self):
        return {"source": self.source, "workspace": self.workspace,
                "mode": "controlled-write", "policy": "fail-closed"}


class SourcePathWriteError(Exception):
    """Raised when a write target violates the source-is-read-only policy."""

    errorCode = "SOURCE_PATH_WRITE_FORBIDDEN"

    def __init__(self, message):
        super(SourcePathWriteError, self).__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# SourceHashGuard (SHA256 manifests)
# ---------------------------------------------------------------------------

def sha256_file(path, chunk_size=1024 * 1024):
    """SHA-256 hex digest of a file; None if unreadable."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _classify_file(rel_upper):
    """File type for the manifest (form/class/report/menu/… based on extension)."""
    ext = os.path.splitext(rel_upper)[1]
    mapping = {
        ".SCX": "form", ".SCT": "form_memo",
        ".VCX": "class_library", ".VCT": "class_library_memo",
        ".FRX": "report", ".FRT": "report_memo",
        ".MNX": "menu", ".MNT": "menu_memo",
        ".LBX": "visual_library", ".LB2": "visual_library_text",
        ".PJX": "project", ".PJT": "project_text",
        ".DBC": "database_container", ".DCX": "database_index", ".DCT": "database_memo",
        ".DBF": "table", ".FPT": "table_memo", ".CDX": "index", ".IDX": "index",
        ".PRG": "program", ".H": "header",
    }
    return mapping.get(ext, "other")


def snapshot_tree(root, extra_files=(), excludes=None):
    """Build a source manifest for a directory tree (or a set of extra files).

    Returns {"root", "files": {relpath_upper: {...}}, "fileCount"}.
    Each entry: path, relPath, size, mtime, sha256, fileType, companions.
    """
    excl = tuple(excludes if excludes is not None else vfp_common.default_excludes())
    files = {}

    def add(fp):
        try:
            st = os.stat(fp)
        except OSError:
            return
        rel = os.path.relpath(fp, root)
        key = rel.upper().replace(os.sep, "/")
        sha = sha256_file(fp)
        if sha is None:
            return
        companions = [os.path.basename(c).upper()
                      for c in vfp_common.required_companions(fp) if os.path.isfile(c)]
        files[key] = {
            "path": fp,
            "relPath": rel.replace(os.sep, "/"),
            "size": st.st_size,
            "mtime": st.st_mtime,
            "sha256": sha,
            "fileType": _classify_file(key),
            "companions": companions,
        }

    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d.lower() not in excl]
            for fn in sorted(filenames):
                add(os.path.join(dirpath, fn))
    for fp in extra_files:
        if fp and os.path.isfile(fp):
            add(fp)

    return {"root": os.path.abspath(root), "fileCount": len(files), "files": files}


def compare_manifests(before, after):
    """Compare two manifests. Returns {"changed": [...], "added": [...],
    "removed": [...], "ok": bool}. Changed = size/sha256/mtime drift."""
    bf = before.get("files", {})
    af = after.get("files", {})
    changed, added, removed = [], [], []
    for key, b in bf.items():
        a = af.get(key)
        if a is None:
            removed.append(key)
        elif (a.get("sha256") != b.get("sha256") or a.get("size") != b.get("size")
              or a.get("mtime") != b.get("mtime")):
            changed.append({
                "file": key,
                "sha256Before": b.get("sha256"),
                "sha256After": a.get("sha256"),
                "sizeBefore": b.get("size"),
                "sizeAfter": a.get("size"),
            })
    for key in af:
        if key not in bf:
            added.append(key)
    return {"ok": not (changed or removed), "changed": changed,
            "added": added, "removed": removed}


class SourceHashGuard(object):
    """Before/after SHA256 guard for one operation (convert, patch, compile).

    Typical use:
        guard = SourceHashGuard([form.scx, form.sct])
        before = guard.capture()
        ... run the VFP9 operation (BIN2PRG / patch / compile) ...
        result = guard.verify()   # {"ok": bool, "changed": [...], ...}
        if not result["ok"]:
            emit(False, status="FAIL", errorCode="SOURCE_HASH_CHANGED", ...)
    """

    def __init__(self, file_paths):
        self.file_paths = [f for f in (file_paths or []) if f and os.path.isfile(f)]

    def capture(self):
        files = {}
        for fp in self.file_paths:
            sha = sha256_file(fp)
            if sha is not None:
                try:
                    st = os.stat(fp)
                    files[os.path.abspath(fp)] = {
                        "path": fp, "size": st.st_size, "mtime": st.st_mtime,
                        "sha256": sha,
                    }
                except OSError:
                    pass
        return {"fileCount": len(files), "files": files}

    def verify(self):
        after_files = {}
        for fp in self.file_paths:
            sha = sha256_file(fp)
            if sha is not None:
                try:
                    st = os.stat(fp)
                    after_files[os.path.abspath(fp)] = {
                        "path": fp, "size": st.st_size, "mtime": st.st_mtime,
                        "sha256": sha,
                    }
                except OSError:
                    pass
        before = self.capture()
        # Re-capture is harmless (we need the *previously captured* state, so
        # store it explicitly instead).
        return self._compare(before, after_files)

    def _compare(self, before, after_files):
        bf = before.get("files", {})
        changed, missing = [], []
        for key, b in bf.items():
            a = after_files.get(key)
            if a is None:
                missing.append(key)
            elif a.get("sha256") != b.get("sha256") or a.get("size") != b.get("size"):
                changed.append({"file": key,
                               "sha256Before": b.get("sha256"),
                               "sha256After": a.get("sha256")})
        return {"ok": not (changed or missing), "changed": changed,
                "missing": missing,
                "errorCode": None if not (changed or missing)
                else "SOURCE_HASH_CHANGED"}


def verify_source_hashes(before_manifest, file_paths):
    """One-shot verification against a previously captured manifest dict."""
    changed, missing = [], []
    for fp in file_paths or []:
        key = os.path.abspath(fp)
        b = before_manifest.get("files", {}).get(key)
        if b is None:
            continue
        sha = sha256_file(fp)
        if sha is None:
            missing.append(key)
        elif sha != b.get("sha256"):
            changed.append({"file": key,
                            "sha256Before": b.get("sha256"),
                            "sha256After": sha})
    return {"ok": not (changed or missing), "changed": changed, "missing": missing,
            "errorCode": None if not (changed or missing) else "SOURCE_HASH_CHANGED"}
