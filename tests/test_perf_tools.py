#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_perf_tools.py - unit tests for the performance-audit subcommands.

These tests exercise the pure-Python logic (form_perf, count_patterns,
find_duplicates) using synthetic .sc2 files and skip the VFP9-dependent
run_prg / benchmark paths when VFP9 is not installed.

Run:  py -m pytest tests/test_perf_tools.py -v
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_driver  # noqa: E402

# A minimal synthetic .sc2 form with two procedures. One contains a SCAN FOR
# and a SEEK, the other contains RLOCK / UNLOCK ALL. The two "Blokada"
# procedures are intentionally near-identical to test duplicate detection.
SAMPLE_SC2 = """\
DEFINE CLASS Form1 AS Form
PROCEDURE Init
    LOCAL x
    x = 1
    RETURN
ENDPROC
PROCEDURE BlokadaA
    * lock all three tables
    IF NOT RLOCK(kp, ks, kw)
        ? "nie zablokowano"
        UNLOCK ALL
        RETURN
    ENDIF
    SCAN
    DO WHILE .NOT. EOF()
        SKIP
    ENDDO
    USE kp
    USE
    RETURN
ENDPROC
PROCEDURE BlokadaB
    * lock all three tables
    IF NOT RLOCK(kp, ks, kw)
        ? "nie zablokowano"
        UNLOCK ALL
        RETURN
    ENDIF
    SCAN
    DO WHILE .NOT. EOF()
        SKIP
    ENDDO
    USE kp
    USE
    RETURN
ENDPROC
ENDDEFINE
"""


def _write_tmp(content, ext=".sc2"):
    fd, path = tempfile.mkstemp(suffix=ext, prefix="vfp_test_")
    os.close(fd)
    with open(path, "w", encoding="cp1252") as f:
        f.write(content)
    return path


def _call_capture(fn, *args, **kw):
    """Call a driver run_* function, capturing the emit() payload by
    intercepting sys.exit and sys.stdout."""
    import io
    buf = io.StringIO()
    rc_holder = {"rc": 0, "ok": None}

    class _Exit(Exception):
        def __init__(self, code):
            self.code = code

    real_stdout = sys.stdout
    real_exit = sys.exit
    sys.stdout = buf

    def _fake_exit(code=0):
        raise _Exit(code)

    sys.exit = _fake_exit
    try:
        try:
            fn(*args, **kw)
        except _Exit as e:
            rc_holder["rc"] = e.code
    finally:
        sys.stdout = real_stdout
        sys.exit = real_exit

    text = buf.getvalue().strip()
    payload = {}
    if text:
        try:
            payload = json.loads(text.splitlines()[-1])
        except ValueError:
            pass
    rc_holder["ok"] = payload.get("ok")
    rc_holder["payload"] = payload
    return rc_holder


def test_form_perf_finds_seek_and_scan(tmp_path):
    """form_perf must find SCAN and data-access operations in a form."""
    fp = str(tmp_path / "sample.sc2")
    with open(fp, "w", encoding="cp1252") as f:
        f.write(SAMPLE_SC2)
    tables = str(tmp_path)
    res = _call_capture(vfp_driver.run_form_perf, fp, tables)
    assert res["ok"] is True, res
    data = res["payload"]["data"]
    assert data["totalOperations"] >= 1
    ops = {op["operation"] for op in data["accessMap"]}
    # The synthetic form has a SCAN (and USE). Confirm at least one op captured.
    assert any(o in ops for o in ("SCAN", "SCAN_FOR", "LOCATE_FOR", "COUNT_FOR")), ops


def test_form_perf_missing_file():
    """form_perf with a non-existent form must return ok=False."""
    res = _call_capture(vfp_driver.run_form_perf,
                        os.path.join("no_such_dir", "x.sc2"), "no_such_dir")
    assert res["ok"] is False


def test_count_patterns_finds_rlock(tmp_path):
    """count_patterns must count RLOCK and UNLOCK ALL occurrences."""
    proj = str(tmp_path)
    cache = os.path.join(proj, ".vfp-ai", "source")
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(cache, "sample.sc2"), "w", encoding="cp1252") as f:
        f.write(SAMPLE_SC2)
    res = _call_capture(vfp_driver.run_count_patterns, proj, "RLOCK,UNLOCK ALL")
    assert res["ok"] is True, res
    patterns = res["payload"]["data"]["patterns"]
    assert patterns["RLOCK"]["total"] >= 2
    assert patterns["UNLOCK ALL"]["total"] >= 2
    assert res["payload"]["data"]["totalForms"] >= 1


def test_count_patterns_empty(tmp_path):
    """count_patterns with a pattern that never occurs reports total 0."""
    proj = str(tmp_path)
    res = _call_capture(vfp_driver.run_count_patterns, proj, "TOTALLY_MISSING_XYZ")
    assert res["ok"] is True
    assert res["payload"]["data"]["patterns"]["TOTALLY_MISSING_XYZ"]["total"] == 0


def test_find_duplicates_identical_blocks(tmp_path):
    """find_duplicates must detect the identical BlokadaA/BlokadaB blocks."""
    fp = str(tmp_path / "sample.sc2")
    with open(fp, "w", encoding="cp1252") as f:
        f.write(SAMPLE_SC2)
    res = _call_capture(vfp_driver.run_find_duplicates, fp, 5)
    assert res["ok"] is True, res
    data = res["payload"]["data"]
    assert data["duplicateCount"] >= 1
    # One pair should be identical (similarity 100).
    assert any(d["similarity"] == 100 and "Blokada" in d["block1"]
               and "Blokada" in d["block2"] for d in data["duplicates"])


def test_find_duplicates_min_lines_filters(tmp_path):
    """Raising min_lines filters out the small duplicate blocks."""
    fp = str(tmp_path / "sample.sc2")
    with open(fp, "w", encoding="cp1252") as f:
        f.write(SAMPLE_SC2)
    res = _call_capture(vfp_driver.run_find_duplicates, fp, 1000)
    assert res["ok"] is True
    assert res["payload"]["data"]["analyzedBlocks"] == 0


# ---------------------------------------------------------------------------
# VFP9-dependent subcommands — verify graceful behaviour when VFP9 is absent.
# ---------------------------------------------------------------------------

def _vfp9_available():
    exe = vfp_driver._vfp9_exe()
    return os.path.isfile(exe)


def test_run_prg_missing_file():
    """run_prg with a non-existent .prg must return ok=False (no crash)."""
    res = _call_capture(vfp_driver.run_run_prg,
                        os.path.join("no_such_dir", "nope.prg"))
    assert res["ok"] is False


def test_benchmark_missing_dane(tmp_path):
    """benchmark without a Dane/ directory must return ok=False (no crash)."""
    res = _call_capture(vfp_driver.run_benchmark, str(tmp_path), "t",
                        "count_for")
    assert res["ok"] is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
