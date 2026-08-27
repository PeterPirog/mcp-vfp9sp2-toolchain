"""Tests for form inventory + comparison (EXPECTED vs UNEXPECTED changes)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_form_inventory as fi

SC2 = """*< FOXBIN2PRG: Version="5.0" SourceFile="X.SCX" CPID="1250" />
DEFINE CLASS form1 AS Form
    Top = 10
    Left = 20
    Width = 300
    Height = 200
    Caption = "Main"
    ADD OBJECT 'form1.cmdSave' AS cmdSave OF CommandButton
    PROCEDURE cmdSave_Click
        THIS.Command1.Click()
    ENDPROC
    FUNCTION DoIt
        RETURN 1
    ENDFUNC
ENDDEFINE
"""


def _write_sc2(tmp_path, name, text=SC2):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_inventory_objects_and_methods(tmp_path):
    p = _write_sc2(tmp_path, "form.sc2")
    inv = fi.build_inventory(p)
    assert inv["suspiciousEncoding"] is False
    assert inv["codec"] == "cp1250"
    names = [o["name"] for o in inv["objects"]]
    assert "form1" in names
    methods = {m["methodName"] for m in inv["methods"]}
    assert "cmdSave_Click" in methods
    assert "DoIt" in methods
    for m in inv["methods"]:
        assert m["lineStart"] >= 1
        assert m["lineEnd"] >= m["lineStart"]
        assert m["sourceSha256"]


def test_properties_captured(tmp_path):
    p = _write_sc2(tmp_path, "form.sc2")
    inv = fi.build_inventory(p)
    f1 = [o for o in inv["objects"] if o["name"] == "form1"][0]
    props = f1["properties"]
    assert props.get("Top") == 10
    assert props.get("Width") == 300
    assert props.get("Caption") == "Main"


def test_compare_identical_passes(tmp_path):
    a = fi.build_inventory(_write_sc2(tmp_path, "a.sc2"))
    b = fi.build_inventory(_write_sc2(tmp_path, "b.sc2"))
    res = fi.compare_inventories(a, b)
    assert res["ok"] is True
    assert res["status"] == "PASS"


def test_unexpected_property_change_fails(tmp_path):
    a = fi.build_inventory(_write_sc2(tmp_path, "a.sc2"))
    changed = SC2.replace("Width = 300", "Width = 999")
    b = fi.build_inventory(_write_sc2(tmp_path, "b.sc2", changed))
    res = fi.compare_inventories(a, b)
    assert res["ok"] is False
    assert res["errorCode"] == "FORM_STRUCTURE_CHANGED"
    assert any(p["property"] == "WIDTH" for p in res["unexpectedPropertyChanges"])


def test_unexpected_object_removed_fails(tmp_path):
    a = fi.build_inventory(_write_sc2(tmp_path, "a.sc2"))
    noobj = SC2.replace("    ADD OBJECT 'form1.cmdSave' AS cmdSave OF CommandButton\n", "")
    b = fi.build_inventory(_write_sc2(tmp_path, "b.sc2", noobj))
    res = fi.compare_inventories(a, b)
    assert res["ok"] is False


def test_method_change_expected_when_planned(tmp_path):
    a = fi.build_inventory(_write_sc2(tmp_path, "a.sc2"))
    patched = SC2.replace(
        "        THIS.Command1.Click()",
        "        THIS.cmdSave.Click()")
    b = fi.build_inventory(_write_sc2(tmp_path, "b.sc2", patched))
    plan = {"schemaVersion": 1, "patches": [
        {"objectPath": "form1", "method": "cmdSave_Click",
         "oldMethodSha256": "x" * 64, "newCode": "..."}]}
    res = fi.compare_inventories(a, b, plan=plan)
    changed = [m for m in res["methodChanges"] if m["method"] == "cmdsave_click"]
    assert changed, "expected the method change to be detected"
    assert changed[0]["verdict"] == "EXPECTED"
    # property/object structure unchanged → overall pass
    assert res["ok"] is True


def test_method_change_unexpected_when_not_planned(tmp_path):
    a = fi.build_inventory(_write_sc2(tmp_path, "a.sc2"))
    patched = SC2.replace(
        "        THIS.Command1.Click()",
        "        THIS.cmdSave.Click()")
    b = fi.build_inventory(_write_sc2(tmp_path, "b.sc2", patched))
    res = fi.compare_inventories(a, b)  # no plan
    assert res["ok"] is False
