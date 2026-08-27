"""Tests for the RefactorPlan schema, preconditions and the patch PRG generator."""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_refactor as ref


def _plan(patches=None):
    return {
        "schemaVersion": 1,
        "sourceForm": r"C:\proj\form.scx",
        "workspace": r"D:\ws",
        "patches": patches if patches is not None else [
            {"objectPath": "form1", "method": "Init",
             "oldMethodSha256": "a" * 64,
             "newCode": "? 'hi'\n"},
        ],
    }


def test_load_plan_ok(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(_plan()), encoding="utf-8")
    plan, errors = ref.load_plan(str(p))
    assert plan is not None
    assert errors == []


def test_load_plan_missing_file():
    plan, errors = ref.load_plan(r"C:\nope\plan.json")
    assert plan is None
    assert errors


def test_load_plan_bad_schema(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"schemaVersion": 99}), encoding="utf-8")
    plan, errors = ref.load_plan(str(p))
    assert any("schemaVersion" in e for e in errors)


def test_load_plan_requires_preconditions(tmp_path):
    p = tmp_path / "plan.json"
    good = _plan()
    del good["patches"][0]["oldMethodSha256"]
    p.write_text(json.dumps(good), encoding="utf-8")
    plan, errors = ref.load_plan(str(p))
    assert any("oldMethodSha256" in e for e in errors)


def test_load_plan_bad_sha(tmp_path):
    p = tmp_path / "plan.json"
    good = _plan()
    good["patches"][0]["oldMethodSha256"] = "zzz"
    p.write_text(json.dumps(good), encoding="utf-8")
    plan, errors = ref.load_plan(str(p))
    assert any("SHA256" in e for e in errors)


def test_check_preconditions_mismatch():
    text = (
        "DEFINE CLASS form1 AS Form\r\n"
        "PROCEDURE Init\r\n"
        "? 'original code'\r\n"
        "ENDPROC\r\n"
        "ENDDEFINE\r\n"
    )
    import vfp_method_parser as mp
    methods = mp.parse_methods(text)
    actual = methods[0]["sourceSha256"]
    wrong = "f" * 64
    res = ref.check_preconditions(text, [
        {"objectPath": "form1", "method": "Init", "oldMethodSha256": wrong,
         "newCode": "? 'x'"},
    ], None)
    assert res["ok"] is False
    assert res["patches"][0]["errorCode"] == "PATCH_PRECONDITION_FAILED"


def test_check_preconditions_match():
    text = (
        "DEFINE CLASS form1 AS Form\r\n"
        "PROCEDURE Init\r\n"
        "? 'original code'\r\n"
        "ENDPROC\r\n"
        "ENDDEFINE\r\n"
    )
    import vfp_method_parser as mp
    actual = mp.parse_methods(text)[0]["sourceSha256"]
    res = ref.check_preconditions(text, [
        {"objectPath": "form1", "method": "Init", "oldMethodSha256": actual,
         "newCode": "? 'x'"},
    ], None)
    assert res["ok"] is True


def test_check_preconditions_missing_method():
    res = ref.check_preconditions("PROCEDURE A\n?1\nENDPROC\n", [
        {"objectPath": "form1", "method": "Nope", "oldMethodSha256": "a" * 64,
         "newCode": "? 'x'"},
    ], None)
    assert res["ok"] is False
    assert res["patches"][0]["errorCode"] == "METHOD_NOT_FOUND"


def test_patch_prg_no_dangerous_commands(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    code, meta = ref.build_patch_prg(str(ws), "form1", [
        {"objectPath": "form1", "method": "Init",
         "oldMethodSha256": "a" * 64, "newCode": "? 'hi'"},
    ], form_class="form1")
    up = code.upper()
    for bad in ("REINDEX", "PACK", "ZAP", "ALTER TABLE", "UPDATE ",
                "PRG2BIN", "DELETE FROM"):
        assert bad not in up, "forbidden command in patch PRG: " + bad
    assert "SET PROCEDURE TO" in up
    assert "SAVE TO" in up
    assert "TYPE FORMCLASS" in up


def test_patch_prg_escapes_quotes(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    # raw VFP code with a single quote inside a string literal
    code, _ = ref.build_patch_prg(str(ws), "form1", [
        {"objectPath": "form1", "method": "M",
         "oldMethodSha256": "a" * 64, "newCode": "c = 'it's'"},
    ], form_class="form1")
    # the literal must be escaped to VFP '' form
    assert "'it''s'" in code


def test_find_form_class():
    text = "DEFINE CLASS form_arch AS Form\n"
    assert ref._find_form_class(text) == "form_arch"
    assert ref._find_form_class("nothing") is None


def test_workspace_creation(tmp_path):
    """create workspace: copy SCX+SCT, hash-verify, manifest written; source
    never modified; source-inside-workspace is rejected."""
    src = tmp_path / "source"
    src.mkdir()
    scx = src / "form1.scx"
    sct = src / "form1.sct"
    scx.write_bytes(b"SCX-BINARY-DATA")
    sct.write_bytes(b"SCT-MEMO-DATA")

    ws = tmp_path / "ws"
    ws.mkdir()

    import argparse
    args = argparse.Namespace(source_form=str(scx), workspace=str(ws))

    captured = {}

    def fake_emit(ok, **kw):
        captured["ok"] = ok
        captured.update(kw)
        raise SystemExit(0 if ok else 2)

    try:
        ref.cmd_workspace(args, emit=fake_emit)
    except SystemExit:
        pass
    assert captured["ok"] is True
    assert captured["status"] == "PASS"

    man = json.loads((ws / "workspace_manifest.json").read_text(encoding="utf-8"))
    assert man["sourceScxSha256"] == man["workingScxSha256"]
    assert man["sourceSctSha256"] == man["workingSctSha256"]
    assert (ws / "working" / "form1.scx").read_bytes() == b"SCX-BINARY-DATA"
    assert (ws / "working" / "form1.sct").read_bytes() == b"SCT-MEMO-DATA"
    # source untouched
    assert scx.read_bytes() == b"SCX-BINARY-DATA"


def test_workspace_inside_source_rejected(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "form1.scx").write_bytes(b"x")
    (src / "form1.sct").write_bytes(b"y")
    ws = src / "inner_ws"
    ws.mkdir()
    import argparse
    args = argparse.Namespace(source_form=str(src / "form1.scx"), workspace=str(ws))
    captured = {}

    def fake_emit(ok, **kw):
        captured.update(kw)
        raise SystemExit(0 if ok else 2)

    try:
        ref.cmd_workspace(args, emit=fake_emit)
    except SystemExit:
        pass
    assert captured.get("errorCode") == "SOURCE_PATH_WRITE_FORBIDDEN"
