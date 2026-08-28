# -*- coding: utf-8 -*-
"""
tests/test_offline_install.py - Phase 15: offline install integration test.

Guarantee: a CLEAN virtual environment, with pip pointed at a LOCAL
wheelhouse ONLY (`--no-index`, no PyPI, no network fallback), yields a
working offline PURE READ runtime:
  1. clean temporary venv,
  2. NO INDEX,
  3. install exclusively from the local wheelhouse,
  4. Core Service import + capabilities() (pureRead available),
  5. dbfbridge import + origin + pin,
  6. DBF_Anonymizer import + status,
  7. DBF pure-read fixture (schema + data),
  8. no VFP9, no FoxBin2Prg (env vars pointed at non-existent paths).

If pip would need the network the install fails (pip --no-index has no
fallback). If no local wheelhouse is available, the test is SKIPPED
(explicitly, never masked) — CI provides the wheelhouse artifact.

Run: py -3 -m pytest tests/test_offline_install.py -v
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# Wheelhouse sources, in priority order:
WHEELHOUSE_CANDIDATES = [
    os.environ.get("VFP_OFFLINE_WHEELHOUSE"),
    os.path.join(ROOT, "dist", "mcp-vfp9sp2-toolchain-offline", "wheels"),
]


def _find_wheelhouse():
    """Return the wheelhouse matching the CURRENT interpreter (native wheels
    like orjson are per-ABI). Returns None when no matching wheelhouse exists
    (e.g. a py3.10 dev box that only has a py3.14 bundle) — the caller skips.
    """
    current = "%d%d" % (sys.version_info[0], sys.version_info[1])
    for c in WHEELHOUSE_CANDIDATES:
        if not c:
            continue
        if os.path.basename(c) in ("310", "312", "314"):
            if os.path.basename(c) == current and os.path.isdir(c) \
                    and any(f.endswith(".whl") for f in os.listdir(c)):
                return c
        else:
            sub = os.path.join(c, current)
            if os.path.isdir(sub) and any(f.endswith(".whl") for f in os.listdir(sub)):
                return sub
    return None


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(scope="module")
def wheelhouse():
    wh = _find_wheelhouse()
    if wh is None:
        pytest.skip("no local offline wheelhouse available (CI provides the "
                    "artifact; dev machines run scripts/build_offline_bundle.ps1)")
    return wh


@pytest.fixture(scope="module")
def offline_venv(wheelhouse, tmp_path_factory):
    venv = tmp_path_factory.mktemp("offline_venv")
    # NOTE: no `--system-site-packages` — this must be a CLEAN environment.
    subprocess.run([sys.executable, "-m", "venv", str(venv)],
                   check=True, capture_output=True, timeout=300)
    py = os.path.join(venv, "Scripts" + os.sep + "python.exe"
                      if os.name == "nt" else "bin" + os.sep + "python")
    # Install EXCLUSIVELY from the local wheelhouse. --no-index => no PyPI,
    # no network fallback: a missing wheel is a hard failure.
    pip_args = [py, "-m", "pip", "install",
                "--no-index",
                "--find-links", wheelhouse,
                "dbfread==2.0.7", "dbf==0.99.11", "aenum==3.1.17",
                "openpyxl==3.1.5", "et_xmlfile==2.0.0", "xlsxwriter==3.2.9",
                "orjson==3.12.0", "polars==1.44.1", "polars_runtime_32==1.44.1"]
    res = subprocess.run(pip_args, capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, (
        "offline pip install failed — pip must NEVER need the network:\n"
        + res.stdout[-2000:] + res.stderr[-2000:])
    return py


def test_offline_core_service_in_clean_venv(offline_venv, wheelhouse, tmp_path_factory):
    """Core Service + dbfbridge + anonymizer + DBF pure read, no VFP."""
    outdir = tmp_path_factory.mktemp("offline_out")
    fixture = os.path.join(ROOT, "tests", "fixtures", "offline_fixture.dbf")
    before = _sha256(fixture)

    script = r"""
import sys, json, os, datetime
sys.path.insert(0, r'%s')
sys.path.insert(0, r'%s')

# 8. no VFP9 / no FoxBin2Prg — guaranteed non-existent paths
os.environ['VFP9_EXE'] = r'%s'
os.environ['VFP_FOXBIN2PRG_DIR'] = r'%s'

import vfp_toolchain
from vfp_toolchain.service import VFPToolchainService
from vfp_toolchain.backends import DBFBridgeBackend, DBFAnonymizerBackend

cap = VFPToolchainService().capabilities().to_dict()
assert cap['ok'] is True, cap
assert cap['data']['modes']['pureRead'] is True
assert cap['data']['modes']['vfpEnhancedRead'] is False
assert cap['data']['offlineRuntime']['verified'] is True

db = DBFBridgeBackend().status()
assert db['available'] is True and db['pinVerified'] is True
assert db['moduleOriginVerified'] is True

an = DBFAnonymizerBackend().status()
assert an['available'] is True, an
assert an['pinVerified'] and an['moduleOriginVerified'] and an['dbfbridgeCompatible']

# 7. DBF pure-read fixture (schema + data), source immutable
import dbfread
d = dbfread.dbf.DBF(r'%s', ignore_missing_memofile=True)
names = sorted(f.name.strip() for f in d.fields)
assert names == ['DATA', 'KWOTA', 'NAZWA', 'UWAGI'], names
rows = [dict(r) for r in d]
assert len(rows) == 3
assert rows[0]['NAZWA'.ljust(11)] == 'Jan Kowalski'
assert rows[0]['KWOTA'.ljust(11)] == 1234.56

# dbfbridge export (JSONL) on the fixture, output to a scratch dir
from pathlib import Path
from dbfbridge import export_dbf
export_dbf(Path(r'%s'), Path(r'%s'), formats='jsonl',
           missing_memo='null-with-warning', deleted='skip')
jsonl = Path(r'%s') / 'offline_fixture.jsonl'
assert jsonl.is_file()
lines = [l for l in jsonl.read_text(encoding='utf-8').splitlines() if l.strip()]
assert len(lines) == 3

print('OFFLINE_VENV_OK')
""" % (
        os.path.join(ROOT, "src").replace("\\", "/"),
        os.path.join(ROOT, "tools", "dbfbridge").replace("\\", "/"),
        os.path.join(ROOT, "definitely-not-installed", "vfp9.exe"),
        os.path.join(ROOT, "definitely-not-installed", "foxbin2prg"),
        fixture.replace("\\", "/"),
        fixture.replace("\\", "/"),
        str(outdir).replace("\\", "/"),
        str(outdir).replace("\\", "/"),
    )

    env = dict(os.environ)
    env.pop("VFP9_EXE", None)
    env.pop("VFP_FOXBIN2PRG_DIR", None)
    res = subprocess.run([offline_venv, "-c", script],
                         capture_output=True, text=True, timeout=300, env=env,
                         cwd=str(outdir))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "OFFLINE_VENV_OK" in res.stdout

    after = _sha256(fixture)
    assert before == after, "PURE READ must not modify the source fixture"


def test_no_runtime_network_imports_in_clean_venv(offline_venv):
    """Installed runtime must not pull in any network-capable import paths."""
    script = (
        "import sys\n"
        "blocked = [m for m in sys.modules if m.split('.')[0] in ('requests','urllib3','httpx','aiohttp')]\n"
        "assert not blocked, blocked\n"
        "import dbfread, dbf\n"
        "blocked = [m for m in sys.modules if m.split('.')[0] in ('requests','urllib3','httpx','aiohttp')]\n"
        "assert not blocked, blocked\n"
        "print('NO_NETWORK_MODULES_OK')\n"
    )
    res = subprocess.run([offline_venv, "-c", script],
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "NO_NETWORK_MODULES_OK" in res.stdout
