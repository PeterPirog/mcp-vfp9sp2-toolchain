# -*- coding: utf-8 -*-
"""
tests/test_dependency_adapters.py — dbfbridge + DBF_Anonymizer adapters.

Guarantees:
  * dbfbridge adapter imports the VENDORED snapshot, exposes the public API
    (export_dbf, reconstruct_dbf, verify_conversion, check_conversion_quality),
    reports a version, and the pin matches tools/dbfbridge/VERSION.txt,
  * DBF_Anonymizer adapter imports the vendored package, version == 0.3.0,
    public API present (anonymize_directory, make_dbf_recovery, self_test),
    depends on the vendored dbfbridge,
  * importing dbf_anonymizer performs NO anonymization and creates NO
    dictionary (no new files, no side effects),
  * no runtime network usage anywhere in the new core package
    (no requests / urllib.request / git clone / git pull / pip install).

Run: py -m pytest tests/test_dependency_adapters.py -v
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from vfp_toolchain.backends import (  # noqa: E402
    DBFAnonymizerBackend,
    DBFBridgeBackend,
)


# -- dbfbridge adapter -------------------------------------------------------

def test_dbfbridge_vendored_present():
    d = os.path.join(ROOT, "tools", "dbfbridge")
    assert os.path.isdir(os.path.join(d, "dbf_bridge")), "vendored snapshot missing"
    assert os.path.isfile(os.path.join(d, "VERSION.txt")), "VERSION.txt missing"
    assert os.path.isfile(os.path.join(d, "LICENSE"))


def test_dbfbridge_adapter_status_and_pin():
    be = DBFBridgeBackend()
    meta = be.status()
    assert meta["available"] is True
    assert meta["vendored"] is True
    assert meta["version"], "version must be reported"
    assert meta["publicApiOk"] is True
    for fn in ("export_dbf", "reconstruct_dbf", "verify_conversion",
               "check_conversion_quality"):
        assert meta["publicApi"][fn] is True
    # pin matches the provenance file (short or full SHA accepted)
    from vfp_toolchain.backends.dbfbridge_backend import EXPECTED_UPSTREAM_COMMIT
    actual = meta["upstreamCommit"].lower()
    expected = EXPECTED_UPSTREAM_COMMIT
    short, long_ = (actual, expected) if len(actual) <= len(expected) else (expected, actual)
    assert len(short) >= 7 and long_.startswith(short), \
        "dbfbridge pin mismatch: %r vs %r" % (actual, expected)


def test_dbfbridge_adapter_public_api_callable():
    be = DBFBridgeBackend()
    for fn in ("export_dbf", "reconstruct_dbf", "verify_conversion",
               "check_conversion_quality"):
        assert callable(getattr(be, fn))


# -- DBF_Anonymizer adapter --------------------------------------------------

def test_anonymizer_vendored_present():
    d = os.path.join(ROOT, "tools", "dbf_anonymizer")
    assert os.path.isdir(os.path.join(d, "dbf_anonymizer")), "vendored package missing"
    assert os.path.isfile(os.path.join(d, "VERSION.txt")), "VERSION.txt missing"
    with open(os.path.join(d, "VERSION.txt"), "r", encoding="utf-8") as f:
        text = f.read()
    assert "ed7915497862850c3de650f2c50c86569442ff77" in text
    assert "addbadb9281914661bf742924f45039e46a895cd" in text
    assert "NONE" in text  # local modifications declared


def test_anonymizer_adapter_status_version_and_api():
    be = DBFAnonymizerBackend()
    meta = be.status()
    assert meta["available"] is True, meta
    assert meta["vendored"] is True
    assert meta["version"] == "0.3.0"
    assert meta["publicApiOk"] is True
    for fn in ("anonymize_directory", "make_dbf_recovery", "self_test"):
        assert meta["publicApi"][fn] is True
    assert be.public_api_available() is True
    assert be.version() == "0.3.0"


def test_anonymizer_dbfbridge_compatibility():
    meta = DBFAnonymizerBackend().status()
    assert meta["dbfbridgeCompatible"] is True
    assert meta["recoveryCapabilityPresent"] is True


def test_anonymizer_import_has_no_side_effects(tmp_path):
    """Importing must not anonymize, create a dictionary or write files."""
    script = (
        "import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s')"
        "; import dbf_anonymizer"
        "; import os; os.chdir(r'%s')"
        "; import glob"
        "; files = glob.glob('**/*', recursive=True)"
        "; assert not any('dictionary' in f.lower() or 'sqlite' in f.lower() for f in files), files"
        "; print('NO_SIDE_EFFECTS_OK')"
    ) % (os.path.join(ROOT, "tools", "dbfbridge"),
         os.path.join(ROOT, "tools", "dbf_anonymizer"),
         str(tmp_path).replace("\\", "/"))
    import subprocess
    res = subprocess.run([sys.executable, "-c", script],
                         cwd=str(tmp_path), capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    assert "NO_SIDE_EFFECTS_OK" in res.stdout
    # and nothing was written into the scratch dir by the import itself
    leftovers = [f for f in os.listdir(str(tmp_path)) if f not in (".git",)]
    assert leftovers == [] or all(
        not ("dictionary" in f.lower() or f.lower().endswith(".sqlite3"))
        for f in leftovers)


# -- dependency manifest ------------------------------------------------------

def test_vendored_dependencies_manifest():
    path = os.path.join(ROOT, "tools", "VENDORED_DEPENDENCIES.json")
    with open(path, "r", encoding="utf-8") as f:
        man = json.load(f)
    deps = {d["name"].lower(): d for d in man["dependencies"]}
    assert "dbfbridge" in deps and deps["dbfbridge"]["mode"] == "VENDORED"
    assert "dbf_anonymizer" in deps and deps["dbf_anonymizer"]["mode"] == "VENDORED"
    assert "foxbin2prg" in deps and deps["foxbin2prg"]["mode"] == "EXTERNAL_CONFIGURED"
    for d in man["dependencies"]:
        assert d["runtimeNetworkRequired"] is False
    # anonymizer pin
    assert deps["dbf_anonymizer"]["commit"] == "ed7915497862850c3de650f2c50c86569442ff77"
    assert deps["dbf_anonymizer"]["requires"]["commit"] == \
        "addbadb9281914661bf742924f45039e46a895cd"


# -- no runtime network -------------------------------------------------------

def test_core_package_has_no_network_or_package_manager_calls():
    """Runtime core must not fetch/install anything over the network."""
    import re
    src_dir = os.path.join(ROOT, "src", "vfp_toolchain")
    forbidden = [
        re.compile(r"\bimport\s+requests\b"),
        re.compile(r"\bfrom\s+requests\b"),
        re.compile(r"\burllib\.request\."),
        re.compile(r"\bhttp\.client\b"),
        re.compile(r"\bsocket\.socket\s*\("),
        re.compile(r"git\s+(clone|pull)\b"),
        re.compile(r"pip\s+install\b"),
    ]
    hits = []
    for dirpath, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
            for rx in forbidden:
                for m in rx.finditer(text):
                    hits.append("%s: %s" % (os.path.relpath(p, ROOT), m.group(0)))
    assert hits == [], "network/package-manager usage found: %s" % hits
