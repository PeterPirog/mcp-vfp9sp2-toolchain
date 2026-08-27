# -*- coding: utf-8 -*-
"""
tests/test_core_service.py — transport-neutral Core Service (Phase 1).

Key guarantees tested here:
  * `import vfp_toolchain` works with NO VFP9, NO FoxBin2Prg (env vars point
    at non-existent paths) — no exception, no side effects,
  * service.capabilities() and service.detect_project() work without VFP,
  * OperationResult is JSON-serializable and keeps the legacy protocol fields,
  * the Capability enum matches docs/mcp_capability_model.json (one truth),
  * PURE_READ detect is source-immutable (SHA256 before == after),
  * the Core Service is importable from a fresh interpreter with only the
    repo on sys.path.

Run: py -m pytest tests/test_core_service.py -v
"""

import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import pytest  # noqa: E402

import vfp_toolchain  # noqa: E402
from vfp_toolchain import Capability, OperationResult, VFPToolchainService  # noqa: E402
from vfp_toolchain import capabilities as cap_mod  # noqa: E402


def _broken_env():
    """Environment where VFP9 and FoxBin2Prg point at non-existent paths."""
    env = dict(os.environ)
    env["VFP9_EXE"] = os.path.join(ROOT, "definitely-not-installed", "vfp9.exe")
    env["VFP_FOXBIN2PRG_DIR"] = os.path.join(ROOT, "definitely-not-installed", "foxbin2prg")
    return env


def _subprocess(script, env):
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


def _tree_hashes(root_dir):
    """SHA256 map of every file under root_dir (immutability evidence)."""
    out = {}
    for dirpath, dirs, files in os.walk(root_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root_dir)] = hashlib.sha256(f.read()).hexdigest()
    return out


# -- import without VFP ------------------------------------------------------

def test_core_import_without_vfp(tmp_path):
    """import vfp_toolchain + capabilities() + detect_project() with no VFP."""
    script = (
        "import sys; sys.path.insert(0, r'%s')" % os.path.join(ROOT, "src").replace("\\", "/") +
        "; import vfp_toolchain" +
        "; s = vfp_toolchain.VFPToolchainService()" +
        "; c = s.capabilities().to_dict()" +
        "; assert c['ok'] is True, c" +
        "; assert c['data']['modes']['pureRead'] is True" +
        "; assert c['data']['modes']['vfpEnhancedRead'] is False" +
        "; assert c['data']['vfp9']['executableExists'] is False" +
        "; d = s.detect_project(r'%s').to_dict()" % str(tmp_path) +
        "; assert d['ok'] is True" +
        "; print('CORE_WITHOUT_VFP_OK')"
    )
    res = _subprocess(script, _broken_env())
    assert res.returncode == 0, res.stderr
    assert "CORE_WITHOUT_VFP_OK" in res.stdout


def test_detect_project_on_fixture(tmp_path):
    (tmp_path / "karta.dbf").write_bytes(b"\xc5\x00" + b"\x00" * 20)
    (tmp_path / "form.scx").write_bytes(b"fake")
    (tmp_path / "code.prg").write_text("?* hello")
    (tmp_path / "backup").mkdir(exist_ok=True)
    (tmp_path / "backup" / "hidden.dbf").write_bytes(b"\xc5")
    (tmp_path / ".vfp-ai").mkdir(exist_ok=True)

    res = VFPToolchainService().detect_project(str(tmp_path))
    assert res.ok is True
    data = res.data
    assert data["totalVfpFiles"] == 3
    assert data["byExtension"][".dbf"] == 1  # backup/ excluded
    assert data["byExtension"][".scx"] == 1
    assert data["byExtension"][".prg"] == 1
    assert data["cacheExists"] is True
    assert data["vfpDetected"] is True


def test_detect_project_missing_dir(tmp_path):
    res = VFPToolchainService().detect_project(str(tmp_path / "nope"))
    assert res.ok is False
    assert res.status == "FAIL"
    assert res.errorCode


# -- OperationResult contract ------------------------------------------------

def test_operation_result_json_serializable_and_legacy_fields():
    r = OperationResult.success(
        operation="vfp_capabilities", requires=["PURE_READ"],
        backend="PURE_PYTHON", data={"a": 1})
    d = r.to_dict()
    # legacy protocol fields must be present (backward compatibility)
    for field in ("ok", "status", "errorCode", "rc", "version",
                  "stdout", "stderr", "data"):
        assert field in d
    # new core fields
    for field in ("operation", "requires", "backend", "sourceModified",
                  "warnings", "errors", "metadata"):
        assert field in d
    parsed = json.loads(json.dumps(d))  # must round-trip
    assert parsed["status"] in ("PASS", "PARTIAL", "FAIL")


def test_operation_result_failure_defaults():
    r = OperationResult.failure("SOME_CODE", operation="op")
    assert r.ok is False
    assert r.status == "FAIL"
    assert r.errorCode == "SOME_CODE"


def test_operation_result_invalid_status_rejected():
    with pytest.raises(ValueError):
        OperationResult(ok=True, status="WONK")


# -- capability model: one truth ---------------------------------------------

def test_capability_enum_matches_json_model():
    problems = cap_mod.verify_model_consistency()
    assert problems == [], problems


def test_capability_enum_exact_set():
    assert {c.value for c in Capability} == {
        "PURE_READ", "PURE_WRITE_COPY", "VFP_READ_ENHANCED",
        "VFP_WRITE_WORKSPACE", "VFP_BUILD_VALIDATE", "PRIVACY_SENSITIVE"}


# -- source immutability (PURE_READ never writes) ----------------------------

def test_detect_is_source_immutable(tmp_path):
    (tmp_path / "x.dbf").write_bytes(os.urandom(64))
    (tmp_path / "x.fpt").write_bytes(os.urandom(32))
    (tmp_path / "a.prg").write_text("* nothing")

    before = _tree_hashes(str(tmp_path))
    VFPToolchainService().detect_project(str(tmp_path))
    after = _tree_hashes(str(tmp_path))
    assert before == after
