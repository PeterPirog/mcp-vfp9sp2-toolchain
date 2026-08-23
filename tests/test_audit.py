#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_audit.py - unit tests for VFPProjectAuditor helpers (pure logic only,
no VFP9, no DBF files required).

Run:  py -m pytest tests/ -v   (or:  py tests/test_audit.py)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_audit


def _auditor(tmpdir):
    return vfp_audit.VFPProjectAuditor(
        source_dir=tmpdir, out_dir=os.path.join(tmpdir, "out"),
        skip_sync=True, include_forms=False)


def test_path_is_archive_like(tmp_path):
    a = _auditor(str(tmp_path))
    assert a._path_is_archive_like("Arch\\Ar_20211221\\x.dbf")
    assert a._path_is_archive_like("BAZA_TMP\\x.dbf")
    assert not a._path_is_archive_like("DANE\\x.dbf")
    assert not a._path_is_archive_like("src\\x.dbf")


def _schema(rel, records=0):
    return {"sourceFile": rel.replace("\\", os.sep), "recordCount": records}


def test_detect_duplicate_copies_single(tmp_path):
    a = _auditor(str(tmp_path))
    res = a._detect_duplicate_copies([_schema("DANE\\a.dbf")])
    assert res["duplicateNameCount"] == 0
    assert res["redundantCopies"] == 0
    assert res["uniqueNames"] == 1


def test_detect_duplicate_copies_multiple(tmp_path):
    a = _auditor(str(tmp_path))
    res = a._detect_duplicate_copies([
        _schema("DANE\\FOXUSER.dbf", 10),
        _schema("DANE_SIM\\FOXUSER.dbf", 1),
        _schema("BAZA_TMP\\FOXUSER.dbf", 0),
        _schema("DANE\\other.dbf", 5),
    ])
    assert res["uniqueNames"] == 2
    assert res["duplicateNameCount"] == 1
    assert res["redundantCopies"] == 2  # 3 FOXUSER copies -> 2 redundant
    fox = [d for d in res["duplicates"] if d["table"] == "FOXUSER"][0]
    # primary must be the non-archive copy with the most records
    assert "DANE" in fox["primary"]
    assert len(fox["suspectedBackups"]) == 2


def test_cache_is_usable_index(tmp_path):
    a = _auditor(str(tmp_path))
    assert not a._cache_is_usable()
    os.makedirs(a.cache_dir, exist_ok=True)
    with open(os.path.join(a.cache_dir, "index.json"), "w") as f:
        f.write("{}")
    assert a._cache_is_usable()


def test_cache_is_usable_source(tmp_path):
    a = _auditor(str(tmp_path))
    src = os.path.join(a.cache_dir, "source")
    os.makedirs(src, exist_ok=True)
    with open(os.path.join(src, "x.form.sc2"), "w") as f:
        f.write("DEFINE CLASS")
    assert a._cache_is_usable()


if __name__ == "__main__":
    import tempfile

    def _run(fn, *args):
        with tempfile.TemporaryDirectory() as d:
            fn(d, *args)
        print("  PASS  %s" % fn.__name__)

    fns = [v for k, v in list(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        _run(fn)
    print("\n%d/%d passed" % (len(fns), len(fns)))
