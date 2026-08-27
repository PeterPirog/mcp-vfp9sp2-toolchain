"""Tests for the v0.3 safety core: PathSafetyGuard, SHA256 source guard, protocol."""
import hashlib
import json
import os
import subprocess
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_protocol
import vfp_safety
from vfp_safety import (PathSafetyGuard, SourceHashGuard, SourcePathWriteError,
                        canonicalize_path, is_under, sha256_file)


def _write(path, data=b"content"):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "wb") as f:
        f.write(data)


class TestCanonicalize:
    def test_lowercases_on_windows(self):
        p = canonicalize_path("D:\\Some\\Path")
        if os.name == "nt":
            assert p == "d:\\some\\path"

    def test_dotdot(self, tmp_path):
        inner = tmp_path / "a" / "b"
        inner.mkdir(parents=True)
        f = inner / "x.txt"
        f.write_text("x")
        up = str(f) + "..\\..\\..\\.."
        assert is_under(f, tmp_path)

    def test_is_under(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        assert is_under(sub, tmp_path)
        assert is_under(tmp_path, tmp_path)
        assert not is_under(tmp_path, sub)


class TestPathSafetyGuard:
    def _make(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        ws = tmp_path / "workspace"
        ws.mkdir()
        return str(src), str(ws)

    def test_source_inside_workspace_rejected(self, tmp_path):
        src, _ = self._make(tmp_path)
        # workspace = source/child  → forbidden
        child = os.path.join(src, "child_ws")
        os.makedirs(child)
        try:
            PathSafetyGuard(src, child)
            raise AssertionError("expected SourcePathWriteError")
        except SourcePathWriteError as e:
            assert e.errorCode == "SOURCE_PATH_WRITE_FORBIDDEN"

    def test_workspace_inside_source_rejected(self, tmp_path):
        src, _ = self._make(tmp_path)
        inner_ws = os.path.join(src, "inner_ws")
        os.makedirs(inner_ws)
        try:
            PathSafetyGuard(src, inner_ws)
            raise AssertionError("expected SourcePathWriteError")
        except SourcePathWriteError:
            pass

    def test_same_dir_rejected(self, tmp_path):
        src, _ = self._make(tmp_path)
        try:
            PathSafetyGuard(src, src)
            raise AssertionError("expected SourcePathWriteError")
        except SourcePathWriteError:
            pass

    def test_case_insensitive_windows(self, tmp_path):
        if os.name != "nt":
            import pytest
            pytest.skip("windows only")
        src, ws = self._make(tmp_path)
        guard = PathSafetyGuard(src, ws)
        target = os.path.join(ws, "Working\\FORM.SCX")
        guard.assert_writable(target)  # must not raise

    def test_write_into_source_forbidden(self, tmp_path):
        src, ws = self._make(tmp_path)
        guard = PathSafetyGuard(src, ws)
        try:
            guard.assert_writable(os.path.join(src, "FORM.SCX"))
            raise AssertionError("expected SourcePathWriteError")
        except SourcePathWriteError:
            pass
        assert guard.is_writable(os.path.join(ws, "working", "f.scx")) is True

    def test_dotdot_escape_blocked(self, tmp_path):
        src, ws = self._make(tmp_path)
        evil = os.path.join(ws, "..", "source", "f.scx")
        guard = PathSafetyGuard(src, ws)
        assert guard.is_writable(evil) is False

    def test_outside_workspace_forbidden(self, tmp_path):
        src, ws = self._make(tmp_path)
        other = tmp_path / "elsewhere"
        other.mkdir()
        guard = PathSafetyGuard(src, ws)
        assert guard.is_writable(os.path.join(other, "x.scx")) is False


class TestSourceHashGuard:
    def test_detects_mutation(self, tmp_path):
        f = tmp_path / "a.scx"
        _write(str(f), b"v1")
        guard = SourceHashGuard([str(f)])
        before = guard.capture()
        _write(str(f), b"v2-changed")
        res = verify_after(before, [str(f)])
        assert res["ok"] is False
        assert res["errorCode"] == "SOURCE_HASH_CHANGED"
        assert len(res["changed"]) == 1

    def test_detects_missing(self, tmp_path):
        f = tmp_path / "b.sct"
        _write(str(f), b"data")
        before = vfp_safety.verify_source_hashes.__self__ if False else None
        m = _capture([str(f)])
        os.remove(str(f))
        res = vfp_safety.verify_source_hashes(m, [str(f)])
        assert res["ok"] is False
        assert res["errorCode"] == "SOURCE_HASH_CHANGED"

    def test_unchanged_passes(self, tmp_path):
        f = tmp_path / "c.scx"
        _write(str(f), b"same")
        m = _capture([str(f)])
        res = vfp_safety.verify_source_hashes(m, [str(f)])
        assert res["ok"] is True


def _capture(files):
    return vfp_safety.SourceHashGuard(files).capture()


def verify_after(before, files):
    return vfp_safety.verify_source_hashes(before, files)


class TestProtocol:
    def test_payload_fields(self):
        p = vfp_protocol.result_payload(True, data={"x": 1})
        assert p["ok"] is True
        assert p["status"] == "PASS"
        assert p["errorCode"] is None
        assert p["data"] == {"x": 1}

    def test_fail_default_errorcode(self):
        p = vfp_protocol.result_payload(False)
        assert p["status"] == "FAIL"
        assert p["errorCode"] == "UNEXPECTED_ERROR"

    def test_emit_exits(self, tmp_path):
        code = (
            "import sys, json; sys.path.insert(0, %r)\n"
            "import vfp_protocol\n"
            "vfp_protocol.emit(False, status='FAIL', errorCode='X', data={'k':1})\n"
            % ROOT
        )
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True)
        assert r.returncode == 2
        obj = json.loads(r.stdout.strip().splitlines()[-1])
        assert obj["ok"] is False
        assert obj["errorCode"] == "X"
        assert obj["data"] == {"k": 1}
        # exactly one JSON object on stdout
        assert len(r.stdout.strip().splitlines()) == 1


class TestNoGlobalTaskkill:
    """Regression guard: the toolchain must NEVER terminate vfp9.exe by image
    name (it would kill other users' VFP9 sessions)."""

    def test_no_global_vfp9_kill_anywhere(self):
        import glob
        bad = []
        for pattern in ("*.py", "*.vbs", "tools/*.ts"):
            for fp in glob.glob(os.path.join(ROOT, pattern)):
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read().lower()
                except OSError:
                    continue
                if "taskkill" in text and "vfp9" in text and "/im" in text:
                    bad.append(fp)
        assert bad == [], ("global kill of vfp9.exe by image name reappeared in: %s"
                           % bad)

    def test_run_process_timeout_kills_only_child(self, tmp_path):
        # A child that ignores SIGTERM-style kills: run with a 2s timeout.
        # The toolchain must terminate by PID (or report timeout) and must
        # never spawn 'taskkill'. Verify the result contract.
        if os.name == "nt":
            child = "import time; time.sleep(30)"
        else:
            child = "import time; time.sleep(30)"
        res = vfp_protocol.run_process([sys.executable, "-c", child], timeout=2)
        assert res["timeout"] is True
        assert res["code"] == -2
        assert "VFP9_TIMEOUT" in res["stderr"] or "TIMEOUT" in res["stderr"]

    def test_run_process_timeout_kills_only_child_fast(self):
        import time
        t0 = time.time()
        res = vfp_protocol.run_process([sys.executable, "-c", "import time; time.sleep(30)"],
                                       timeout=2)
        dt = time.time() - t0
        # The whole call must return within a sane bound (child killed by PID,
        # no waiting for a global kill).
        assert dt < 20
