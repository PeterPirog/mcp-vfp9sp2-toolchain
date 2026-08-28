# -*- coding: utf-8 -*-
"""
tests/test_offline_bundle.py - bundle integration tests (Phase 2 hardening).

Guarantees, against a BUILT bundle (dist/mcp-vfp9sp2-toolchain-offline or
$VFP_OFFLINE_BUNDLE):

  * app/ is the SINGLE canonical toolchain root — no sibling knowledge/
    duplicate, config.json + language/ + docs/ live INSIDE app/,
  * VFPToolchainService(root=<bundle>/app) loads the REAL shipped
    config.json (dialect + mandatory knowledge), not a checkout fallback,
  * detect_project() from the bundle works (root-bound config resolution),
  * a SUBPROCESS with cwd=<bundle>/app and sys.path pointed only at app/
    imports vfp_toolchain from under app/ (module.__file__ evidence) and
    reports pureRead available + offlineRuntime verified,
  * the bundle manifest lists wheels + test wheels with SHA256 for every
    supported Python, and its hashes match the files on disk,
  * licenses/ + THIRD_PARTY_NOTICES.md exist in the bundle.

The test is SKIPPED (explicitly, never masked) when no bundle has been
built yet: CI builds one per run; dev machines run
``scripts\\build_offline_bundle.ps1`` first.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BUNDLE_CANDIDATES = [
    os.environ.get("VFP_OFFLINE_BUNDLE"),
    os.path.join(ROOT, "dist", "mcp-vfp9sp2-toolchain-offline"),
]


def _find_bundle():
    for c in BUNDLE_CANDIDATES:
        if c and os.path.isdir(os.path.join(c, "app")) and \
                os.path.isdir(os.path.join(c, "wheels")):
            return c
    return None


BUNDLE = _find_bundle() or ""  # type: str
pytestmark = pytest.mark.skipif(
    not BUNDLE,
    reason="no built offline bundle (CI builds one per run; locally run "
           "scripts\\build_offline_bundle.ps1 first)",
)

APP = os.path.join(BUNDLE, "app")
PY_TAG = "%d%d" % (sys.version_info[0], sys.version_info[1])


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _manifest():
    p = os.path.join(BUNDLE, "manifests", "bundle-manifest.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def test_bundle_has_single_canonical_app_root():
    assert os.path.isfile(os.path.join(APP, "config.json"))
    assert os.path.isdir(os.path.join(APP, "src", "vfp_toolchain"))
    assert os.path.isdir(os.path.join(APP, "tools", "dbfbridge"))
    assert os.path.isdir(os.path.join(APP, "tools", "dbf_anonymizer"))
    assert os.path.isdir(os.path.join(APP, "runtime"))
    assert os.path.isfile(os.path.join(APP, "runtime", "runtime-dependencies.json"))
    assert os.path.isfile(os.path.join(APP, "runtime", "test-dependencies.json"))
    # canonical knowledge inside app/ — no ambiguous sibling duplicate
    assert not os.path.isdir(os.path.join(BUNDLE, "knowledge")), \
        "ambiguous knowledge/ sibling must not exist"
    # runtime lock inside app/ (self-contained)
    lock = os.path.join(APP, "runtime", "runtime-dependencies.json")
    with open(lock, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("dependencies", [])) >= 9


def test_config_json_is_real_and_mandatory_files_present():
    cfg_path = os.path.join(APP, "config.json")
    assert os.path.isfile(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert cfg.get("target", {}).get("dialect") == "microsoft.visual-foxpro.9.0.sp2"
    mand = (cfg.get("knowledge") or {}).get("mandatory") or []
    assert mand, "config.json must declare mandatory knowledge files"
    missing = [rel for rel in mand
               if not os.path.isfile(os.path.join(APP, *rel.split("/")))]
    assert not missing, "mandatory knowledge files missing from app/: %s" % missing


def _wheel_tag(version):
    """'3.10' (manifest form) or '310' (dir form) -> '310' (dir form)."""
    return version.replace(".", "")


def test_bundle_manifest_wheels_are_sha256_verified():
    m = _manifest()
    assert m.get("canonicalRoot") == "app"
    assert m["pythonVersions"] == ["3.10", "3.12", "3.14"]
    for ver in m["pythonVersions"]:
        tag = _wheel_tag(ver)
        assert m["wheels"][tag], "no wheels recorded for python tag %s" % tag
        assert m["testWheels"][tag], "no test wheels recorded for tag %s" % tag
        for name, sha in m["wheels"][tag].items():
            p = os.path.join(BUNDLE, "wheels", tag, name)
            assert os.path.isfile(p), "wheel missing from bundle: %s" % p
            assert _sha256(p).lower() == sha.lower(), "hash mismatch: %s" % name
        for name, sha in m["testWheels"][tag].items():
            p = os.path.join(BUNDLE, "test-wheels", tag, name)
            assert os.path.isfile(p), "test wheel missing: %s" % p
            assert _sha256(p).lower() == sha.lower(), "hash mismatch: %s" % name


def test_bundle_has_notices_and_licenses():
    assert os.path.isfile(os.path.join(BUNDLE, "licenses", "THIRD_PARTY_NOTICES.md"))
    assert os.path.isfile(os.path.join(APP, "THIRD_PARTY_NOTICES.md"))
    # at least one extracted wheel license per supported tag (py310/312/314)
    m = _manifest()
    for ver in m["pythonVersions"]:
        per = os.path.join(BUNDLE, "licenses", "py" + _wheel_tag(ver))
        assert os.path.isdir(per), "no extracted licenses for py%s" % ver
        assert any(f.endswith(".license.txt") for f in os.listdir(per))


def test_subprocess_imports_from_bundle_app_only():
    """A fresh interpreter with cwd=app/ and sys.path limited to app/ must
    resolve vfp_toolchain from UNDER app/ and report pureRead + verified."""
    # -I mode ignores PYTHONPATH; we must set sys.path inside the script.
    app_src = os.path.join(APP, "src")
    script = (
        "import os, sys\n"
        "sys.path.insert(0, r'%s')\n"
        "sys.path.insert(0, r'%s')\n"
        "import vfp_toolchain\n"
        "from vfp_toolchain.service import VFPToolchainService\n"
        "root = r'%s'\n"
        "assert os.path.normcase(os.path.abspath(vfp_toolchain.__file__))"
        ".startswith(os.path.normcase(root)), vfp_toolchain.__file__\n"
        "cap = VFPToolchainService(root=root).capabilities().to_dict()\n"
        "assert cap['ok'] is True, cap\n"
        "assert cap['data']['modes']['pureRead'] is True\n"
        "assert cap['data']['offlineRuntime']['verified'] is True\n"
        "det = VFPToolchainService(root=root).detect_project(root).to_dict()\n"
        "assert det['ok'] is True, det\n"
        "print('BUNDLE_APP_ONLY_OK')\n"
    ) % (app_src, APP, APP)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    res = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=APP, env=env, capture_output=True, text=True, timeout=300,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "BUNDLE_APP_ONLY_OK" in res.stdout


def test_detect_project_from_bundle_root():
    """detect_project(root=app) must be config-bound to the bundle's own
    config.json (extensions + excludes come from app/config.json).

    Runs in a SUBPROCESS so the bundle's vfp_toolchain import does not
    pollute the parent test process sys.path (it would shadow the repo's
    first-party modules for every test collected afterwards).
    """
    script = (
        "import os, sys, json\n"
        "sys.path.insert(0, r'%s')\n"
        "sys.path.insert(0, r'%s')\n"
        "from vfp_toolchain.service import VFPToolchainService\n"
        "root = r'%s'\n"
        "res = VFPToolchainService(root=root).detect_project(root).to_dict()\n"
        "assert res['ok'] is True, res\n"
        "assert 'totalVfpFiles' in res['data'], res['data']\n"
        "assert res['data']['directory'] == os.path.abspath(root), res['data']\n"
        "print('BUNDLE_DETECT_OK')\n"
    ) % (os.path.join(APP, "src"), APP, APP)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    res = subprocess.run([sys.executable, "-I", "-c", script],
                         cwd=APP, env=env, capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "BUNDLE_DETECT_OK" in res.stdout


def test_offline_verifier_passes_on_bundle_app():
    """The shipped verifier must pass against bundle/app as --root."""
    verifier = os.path.join(BUNDLE, "scripts", "verify_offline_runtime.py")
    assert os.path.isfile(verifier)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(APP, "src") + os.pathsep + APP
    res = subprocess.run(
        [sys.executable, "-I", verifier, "--root", APP],
        cwd=APP, env=env, capture_output=True, text=True, timeout=300,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(res.stdout)
    assert report["verified"] is True
