# -*- coding: utf-8 -*-
"""
tests/test_offline_dbf_read.py - offline PURE READ of a DBF fixture (Phase 16).

Guarantees (no VFP, no network, no PyPI):
  * the synthetic DBF fixture is committed and self-contained,
  * dbfread (vendored-free, wheelhouse-backed) reads schema + data,
  * dbfbridge export_dbf (JSONL) works on the fixture,
  * dbfbridge verify_conversion / check_conversion_quality primitives import
    and are callable,
  * the SOURCE fixture is byte-identical before and after (PURE READ).

The memo (.dbt) file is intentionally ABSENT: this exercises the
missing-memo graceful path (null-with-warning), which is the offline
PURE_READ contract. A memo-bearing variant is covered by the anonymizer
upstream suite.

Run: py -3 -m pytest tests/test_offline_dbf_read.py -v
"""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools", "dbfbridge"))

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "offline_fixture.dbf")


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_fixture_present_and_stable():
    assert os.path.isfile(FIXTURE), "synthetic fixture must be committed"
    size = os.path.getsize(FIXTURE)
    assert size > 0
    assert _sha256(FIXTURE) == _sha256(FIXTURE)  # sanity: deterministic


def test_dbfread_schema_and_data():
    import dbfread
    db = dbfread.dbf.DBF(FIXTURE, ignore_missing_memofile=True)
    names = sorted(f.name.strip() for f in db.fields)
    assert names == sorted(["NAZWA", "KWOTA", "DATA", "UWAGI"]), names
    types = {f.name.strip(): f.type for f in db.fields}
    assert types["NAZWA"] == "C"
    assert types["KWOTA"] == "N"
    assert types["DATA"] == "D"
    assert types["UWAGI"] == "M"
    rows = [dict(r) for r in db]
    assert len(rows) == 3
    first = rows[0]
    # dbfread keeps the 11-char padded field names in record dicts
    assert first["NAZWA".ljust(11)] == "Jan Kowalski"
    assert first["KWOTA".ljust(11)] == 1234.56
    import datetime
    assert first["DATA".ljust(11)] == datetime.date(2026, 1, 1)


def test_dbfbridge_export_jsonl(tmp_path):
    import sys as _s
    from pathlib import Path
    from dbfbridge import export_dbf
    before = _sha256(FIXTURE)
    outdir = tmp_path / "out"
    res = export_dbf(Path(FIXTURE), outdir, formats="jsonl",
                     missing_memo="null-with-warning", deleted="skip")
    after = _sha256(FIXTURE)
    assert before == after, "PURE READ must not modify the source fixture"
    jsonl = outdir / "offline_fixture.jsonl"
    assert jsonl.is_file(), "JSONL output must be produced"
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    import json
    first = json.loads(lines[0])
    # dbfbridge preserves the padded DBF field names
    assert first["NAZWA".ljust(11)] == "Jan Kowalski"
    assert first["KWOTA".ljust(11)] == 1234.56


def test_dbfbridge_verification_primitives_importable():
    import dbfbridge
    for fn in ("export_dbf", "reconstruct_dbf", "verify_conversion",
               "check_conversion_quality"):
        assert callable(getattr(dbfbridge, fn)), fn


def test_anonymizer_status_available_offline():
    """DBFAnonymizerBackend.status() must report available in this closure."""
    from vfp_toolchain.backends import DBFAnonymizerBackend
    meta = DBFAnonymizerBackend().status()
    assert meta["available"] is True, meta
    assert meta["pinVerified"] is True
    assert meta["moduleOriginVerified"] is True
    assert meta["dbfbridgeCompatible"] is True
    assert meta["recoveryCapabilityPresent"] is True
