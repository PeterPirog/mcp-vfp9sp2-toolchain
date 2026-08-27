# -*- coding: utf-8 -*-
"""
tests/test_capability_semantics.py — PR8 capability/pin/origin semantics.

Guarantees verified:
  A. VFP9 absent + FoxBin2Prg absent -> capabilities() PASS with warnings
     (VFP9_NOT_INSTALLED, FOXBIN2PRG_NOT_AVAILABLE), vfpEnhancedRead False.
  B. VFP9 present + FoxBin2Prg absent -> vfpEnhancedRead True (VFP runtime
     does NOT require FoxBin2Prg; conversion-only needs both).
  C. dbfbridge pin mismatch -> available False, pinVerified False,
     capabilities() PARTIAL with an explicit domain errorCode.
  D. DBF_Anonymizer pin mismatch / dbfbridge incompat -> available False.
  E. Wrong module origin (shadow package wins the import) ->
     moduleOriginVerified False -> available False.
  F. OperationResult PARTIAL contract: partial() requires an explicit
     errorCode; FAIL without a code is UNEXPECTED_ERROR; PARTIAL is never
     auto-labelled UNEXPECTED_ERROR.
  G. Corrupt config.json -> PARTIAL + CONFIG_ERROR (not silent fallback).
  H. Root override: per-root config resolution is testable/isolated.
  I. verify.commits_compatible edge cases (empty, short prefixes, case).

Run: py -m pytest tests/test_capability_semantics.py -v
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import vfp_toolchain  # noqa: E402
from vfp_toolchain import OperationResult  # noqa: E402


def _subprocess(script, env=None, cwd=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd or ROOT, env=e, capture_output=True, text=True, timeout=120)


# -- A. no VFP, no FoxBin2Prg -> PASS + warnings ------------------------------

def test_a_capabilities_without_vfp_or_foxbin_pass_with_warnings():
    fake = os.path.join(ROOT, "definitely-not-installed")
    env = {
        "VFP9_EXE": os.path.join(fake, "vfp9.exe"),
        "VFP_FOXBIN2PRG_DIR": os.path.join(fake, "foxbin2prg"),
    }
    script = (
        "import sys, json; sys.path.insert(0, r'%s')" % os.path.join(ROOT, "src").replace("\\", "/") +
        "; import vfp_toolchain"
        "; c = vfp_toolchain.VFPToolchainService().capabilities().to_dict()"
        "; assert c['ok'] is True, c"
        "; assert c['status'] == 'PASS', c"
        "; assert c['data']['modes']['vfpEnhancedRead'] is False"
        "; assert any(w.startswith('VFP9_NOT_INSTALLED') for w in c['warnings']), c['warnings']"
        "; assert any(w.startswith('FOXBIN2PRG_NOT_AVAILABLE') for w in c['warnings']), c['warnings']"
        "; assert c['errors'] == [], c['errors']"
        "; print('A_OK')"
    )
    res = _subprocess(script, env)
    assert res.returncode == 0, res.stderr
    assert "A_OK" in res.stdout


# -- B. VFP present, FoxBin absent -> vfpEnhancedRead True -------------------

def test_b_vfp_present_without_foxbin_enhanced_read_true(tmp_path):
    vfp_dir = tmp_path / "fake_vfp"
    vfp_dir.mkdir()
    (vfp_dir / "vfp9.exe").write_bytes(b"fake")  # existence probe only
    env = {
        "VFP9_EXE": str(vfp_dir / "vfp9.exe"),
        "VFP_FOXBIN2PRG_DIR": str(tmp_path / "no-foxbin-here"),
    }
    script = (
        "import sys; sys.path.insert(0, r'%s')" % os.path.join(ROOT, "src").replace("\\", "/") +
        "; import vfp_toolchain"
        "; c = vfp_toolchain.VFPToolchainService().capabilities().to_dict()"
        "; assert c['ok'] is True, c"
        "; assert c['data']['vfp9']['executableExists'] is True"
        "; assert c['data']['foxbin2prg']['programExists'] is False"
        "; assert c['data']['modes']['vfpEnhancedRead'] is True, c['data']['modes']"
        "; assert c['data']['modes']['pureRead'] is True"
        "; assert any(w.startswith('FOXBIN2PRG_NOT_AVAILABLE') for w in c['warnings'])"
        "; assert not any(w.startswith('VFP9_NOT_INSTALLED') for w in c['warnings'])"
        "; print('B_OK')"
    )
    res = _subprocess(script, env)
    assert res.returncode == 0, res.stderr
    assert "B_OK" in res.stdout


# -- C. dbfbridge pin mismatch -> fail-closed PARTIAL -------------------------

def _make_fake_root(tmp_path, corrupt_dbfbridge_pin=True,
                    corrupt_anonymizer_pin=False):
    """Copy the vendored trees into a fake repo root, optionally corrupting pins."""
    tools = tmp_path / "tools"
    for name in ("dbfbridge", "dbf_anonymizer"):
        src = os.path.join(ROOT, "tools", name)
        shutil.copytree(src, str(tools / name), dirs_exist_ok=True)
    if corrupt_dbfbridge_pin:
        vf = tools / "dbfbridge" / "VERSION.txt"
        text = vf.read_text(encoding="utf-8", errors="replace")
        text = text.replace("addbadb9281914661bf742924f45039e46a895cd",
                            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        text = text.replace("addbadb", "deadbeef")
        vf.write_text(text, encoding="utf-8")
    if corrupt_anonymizer_pin:
        vf = tools / "dbf_anonymizer" / "VERSION.txt"
        text = vf.read_text(encoding="utf-8", errors="replace")
        text = text.replace("ed7915497862850c3de650f2c50c86569442ff77",
                            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        vf.write_text(text, encoding="utf-8")
    return str(tmp_path)


def test_c_dbfbridge_pin_mismatch_fails_closed(tmp_path):
    """A corrupted VERSION.txt pin must fail closed: available=False + PARTIAL.

    Note: sys.modules is per-process, so the *module origin* check still sees
    the real repo snapshot (which is correct behaviour); the pin check reads
    the fake root's VERSION.txt and MUST reject it.
    """
    fake_root = _make_fake_root(tmp_path, corrupt_dbfbridge_pin=True)
    script = (
        "import sys, json; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s')"
        % (os.path.join(ROOT, "src").replace("\\", "/"), ROOT) +
        "; from vfp_toolchain.backends import DBFBridgeBackend"
        "; m = DBFBridgeBackend(root=r'%s').status()" % fake_root.replace("\\", "/") +
        "; assert m['available'] is False, m"
        "; assert m['pinVerified'] is False, m"
        "; import vfp_toolchain"
        "; c = vfp_toolchain.VFPToolchainService(root=r'%s').capabilities().to_dict()" % fake_root.replace("\\", "/") +
        "; assert c['status'] == 'PARTIAL', c"
        "; assert c['errorCode'], c"
        "; assert any('DEPENDENCY_VERSION_MISMATCH' in e for e in c['errors']), c['errors']"
        "; print('C_OK')"
    )
    res = _subprocess(script)
    assert res.returncode == 0, res.stderr
    assert "C_OK" in res.stdout


def test_c2_module_origin_verified_true_for_real_vendored():
    """Sanity: the shipped snapshot passes BOTH pin and origin checks."""
    from vfp_toolchain.backends import DBFBridgeBackend
    m = DBFBridgeBackend().status()
    assert m["available"] is True
    assert m["pinVerified"] is True
    assert m["moduleOriginVerified"] is True
    assert m["moduleFile"], "module origin must report the resolved path"


# -- D. anonymizer pin / dbfbridge compatibility mismatch ---------------------

def test_d_anonymizer_pin_mismatch_fails_closed(tmp_path):
    fake_root = _make_fake_root(tmp_path, corrupt_dbfbridge_pin=False,
                                corrupt_anonymizer_pin=True)
    script = (
        "import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s')"
        % (os.path.join(ROOT, "src").replace("\\", "/"), ROOT) +
        "; from vfp_toolchain.backends import DBFAnonymizerBackend"
        "; m = DBFAnonymizerBackend(root=r'%s').status()" % fake_root.replace("\\", "/") +
        "; assert m['available'] is False, m"
        "; assert m['pinVerified'] is False, m"
        "; print('D_OK')"
    )
    res = _subprocess(script)
    assert res.returncode == 0, res.stderr
    assert "D_OK" in res.stdout


def test_d2_anonymizer_dbfbridge_incompatible_fails_closed(tmp_path):
    """Corrupt the SHARED dbfbridge pin -> anonymizer must report incompatible."""
    fake_root = _make_fake_root(tmp_path, corrupt_dbfbridge_pin=True,
                                corrupt_anonymizer_pin=False)
    script = (
        "import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s')"
        % (os.path.join(ROOT, "src").replace("\\", "/"), ROOT) +
        "; from vfp_toolchain.backends import DBFAnonymizerBackend"
        "; m = DBFAnonymizerBackend(root=r'%s').status()" % fake_root.replace("\\", "/") +
        "; assert m['available'] is False, m"
        "; assert m['dbfbridgeCompatible'] is False, m"
        "; print('D2_OK')"
    )
    res = _subprocess(script)
    assert res.returncode == 0, res.stderr
    assert "D2_OK" in res.stdout


# -- E. wrong module origin (shadow package) -> fail-closed -------------------

def test_e_shadow_module_origin_rejected(tmp_path):
    """A globally-imported 'dbfbridge' must be detected as wrong origin."""
    shadow = tmp_path / "shadow"
    pkg = shadow / "dbfbridge"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "__version__ = '9.9.9-shadow'\n"
        "def export_dbf(*a, **k): pass\n"
        "def reconstruct_dbf(*a, **k): pass\n"
        "def verify_conversion(*a, **k): pass\n"
        "def check_conversion_quality(*a, **k): pass\n",
        encoding="utf-8")
    script = (
        "import sys; sys.path.insert(0, r'%s')" % str(shadow).replace("\\", "/") +
        "; import dbfbridge"
        "; sys.path.insert(0, r'%s')" % os.path.join(ROOT, "src").replace("\\", "/") +
        "; sys.path.insert(0, r'%s')" % ROOT +
        "; from vfp_toolchain.backends import DBFBridgeBackend"
        "; m = DBFBridgeBackend().status()"
        "; assert m['moduleOriginVerified'] is False, m"
        "; assert m['available'] is False, m"
        "; print('E_OK')"
    )
    res = _subprocess(script)
    assert res.returncode == 0, res.stderr
    assert "E_OK" in res.stdout


# -- F. OperationResult PARTIAL contract --------------------------------------

def test_f_partial_requires_explicit_error_code():
    with pytest.raises(ValueError):
        OperationResult.partial("", operation="op")
    with pytest.raises(ValueError):
        OperationResult.partial(None, operation="op")
    with pytest.raises(ValueError):
        OperationResult.partial("  ", operation="op")


def test_f2_partial_carries_code_never_unexpected():
    r = OperationResult.partial("DEPENDENCY_PARTIAL", operation="op")
    assert r.ok is False
    assert r.status == "PARTIAL"
    assert r.errorCode == "DEPENDENCY_PARTIAL"
    assert r.errorCode != "UNEXPECTED_ERROR"


def test_f3_fail_without_code_defaults_unexpected():
    r = OperationResult(ok=False, status="FAIL")
    assert r.errorCode == "UNEXPECTED_ERROR"


def test_f4_success_has_no_error_code():
    r = OperationResult.success(operation="op")
    assert r.ok is True
    assert r.status == "PASS"
    assert r.errorCode is None


# -- G. corrupt config.json -> PARTIAL + CONFIG_ERROR --------------------------

def test_g_corrupt_config_is_partial_with_config_error(tmp_path):
    (tmp_path / "config.json").write_text("{ not valid json !!", encoding="utf-8")
    script = (
        "import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s')"
        % (os.path.join(ROOT, "src").replace("\\", "/"), ROOT) +
        "; import vfp_toolchain"
        "; c = vfp_toolchain.VFPToolchainService(root=r'%s').capabilities().to_dict()" % str(tmp_path).replace("\\", "/") +
        "; assert c['status'] == 'PARTIAL', c"
        "; assert any('CONFIG_ERROR' in e for e in c['errors']), c['errors']"
        "; print('G_OK')"
    )
    res = _subprocess(script)
    assert res.returncode == 0, res.stderr
    assert "G_OK" in res.stdout


# -- H. root override isolation ------------------------------------------------

def test_h_root_override_changes_config_resolution(tmp_path):
    from vfp_toolchain import config
    (tmp_path / "config.json").write_text(
        json.dumps({"target": {"dialect": "custom.dialect.9.0"}}),
        encoding="utf-8")
    assert config.config_path(str(tmp_path)) == os.path.join(str(tmp_path), "config.json")
    assert config.repo_root(str(tmp_path)) == os.path.abspath(str(tmp_path))
    cfg = config.load_config(str(tmp_path))
    assert cfg["target"]["dialect"] == "custom.dialect.9.0"
    assert config.config_error(str(tmp_path)) is None


# -- I. commit compatibility edge cases ----------------------------------------

def test_i_commits_compatible_edge_cases():
    from vfp_toolchain.backends import verify
    full = "addbadb9281914661bf742924f45039e46a895cd"
    assert verify.commits_compatible(full, full)
    assert verify.commits_compatible("addbadb", full)      # short prefix ok
    assert verify.commits_compatible(full.upper(), full)   # case-insensitive
    assert verify.commits_compatible("addbadb9", full)
    assert not verify.commits_compatible("", full)          # empty fails closed
    assert not verify.commits_compatible(None, full)
    assert not verify.commits_compatible("add", full)       # <7 chars
    assert not verify.commits_compatible("beefbeef", full)  # wrong sha
    assert verify.normalize_commit("https://github.com/x/y@abc12345") == "abc12345"
    assert not verify.module_origin_verified(None, ROOT)
    assert verify.module_under_root(os.path.join(ROOT, "a", "b.py"), ROOT)
    assert not verify.module_under_root(os.path.join(tmp_path if False else ROOT, "x", "y.py"),
                                        os.path.join(ROOT, "tools"))


def test_i2_verify_provenance_missing_file(tmp_path):
    from vfp_toolchain.backends import verify
    out = verify.verify_provenance(str(tmp_path), "abc1234567890abcdef")
    assert out["pinVerified"] is False
    assert out["recordedCommit"] is None
    (tmp_path / "VERSION.txt").write_text("commit: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n",
                                          encoding="utf-8")
    out = verify.verify_provenance(str(tmp_path), "abc1234567890abcdef")
    assert out["recordedCommit"].startswith("deadbeef")
    assert out["pinVerified"] is False
    out = verify.verify_provenance(str(tmp_path), "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    assert out["pinVerified"] is True
