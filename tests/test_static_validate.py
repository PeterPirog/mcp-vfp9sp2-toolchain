"""Tests for static SC2 validation (artifacts, duplicates, END balance, growth)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_static_validate as sv


def test_clean_method_passes():
    code = (
        "PROCEDURE Clean\n"
        "   IF Empty(c) = .T.\n"
        "      RETURN\n"
        "   ENDIF\n"
        "   ? 'ok'\n"
        "ENDPROC\n"
    )
    methods = [{"name": "Clean", "kind": "procedure", "code": code,
                "lineStart": 1, "lineEnd": 5, "lineCount": 5}]
    res = sv.validate_sc2(code, methods)
    assert res["ok"] is True


def test_control_char_detected():
    res = sv.check_controls("bad\x01char")
    assert res and res["severity"] == "error"
    assert sv.check_controls("fine") is None


def test_fffd_detected():
    res = sv.check_fffd("x\ufffdy")
    assert res and res["check"] == "replacement_char_u_fffd"
    assert sv.check_fffd("ok") is None


def test_mojibake_detected():
    res = sv.check_mojibake("napis: \u00c2\u2019" )
    assert res is not None
    assert sv.check_mojibake("cz\u0119\u015bcie") is None  # correct cp1250 text


def test_markdown_fence_detected():
    assert sv.check_markdown_fences("```python\nx=1\n```") is not None
    assert sv.check_markdown_fences("normal VFP code") is None


def test_ai_prompt_fragment_detected():
    res = sv.check_ai_prompt_fragments("Here is the refactored code:\n? 1")
    assert res is not None
    assert sv.check_ai_prompt_fragments("? 1 + 2") is None


def test_literal_escape_warning():
    res = sv.check_literal_escapes("x = 'a\\nb'")  # literal backslash-n outside strings
    assert res is not None
    assert res["severity"] == "warning"


def test_duplicate_procedure_detected():
    methods = [
        {"name": "Dup", "kind": "procedure", "code": "PROCEDURE Dup\n? 1\nENDPROC"},
        {"name": "Dup", "kind": "procedure", "code": "PROCEDURE Dup\n? 2\nENDPROC"},
    ]
    findings = sv.check_duplicates(methods)
    assert any(f["check"] == "duplicate_procedure" for f in findings)


def test_duplicated_large_block_detected():
    body = "\n".join("? line %d" % i for i in range(30))
    methods = [
        {"name": "A", "kind": "procedure", "code": body},
        {"name": "B", "kind": "procedure", "code": body},
    ]
    findings = sv.check_duplicates(methods)
    assert any(f["check"] == "duplicated_code_block" for f in findings)


def test_end_balance_if_endif():
    method = {
        "name": "Bad",
        "code": (
            "PROCEDURE Bad\n"
            "   IF x = 1\n"
            "      ? 1\n"
            "ENDPROC\n"
        ),
    }
    findings = sv.check_end_balance(method)
    assert any(f["check"] == "end_balance" and "ENDIF" in f["message"]
               for f in findings)


def test_end_balance_endif_in_string_ignored():
    method = {
        "name": "Ok",
        "code": (
            "PROCEDURE Ok\n"
            "   ? 'ENDIF'\n"
            "   IF x = 1\n"
            "      ? 1\n"
            "   ENDIF\n"
            "ENDPROC\n"
        ),
    }
    findings = sv.check_end_balance(method)
    assert findings == []


def test_growth_suspicious():
    m = {"name": "G", "lineCount": 500, "code": "x"}
    base = {"name": "G", "lineCount": 20, "code": "y"}
    assert sv.check_growth(m, base) is not None
    assert sv.check_growth({"name": "G", "lineCount": 30}, {"name": "G", "lineCount": 20}) is None


def test_full_validate_fail_sets_errorcode():
    code = "PROCEDURE X\n? 1\nPROCEDURE X\n? 2\nENDPROC\nENDPROC\n"
    methods = [
        {"name": "X", "kind": "procedure", "code": code, "lineStart": 1, "lineEnd": 5, "lineCount": 5},
    ]
    res = sv.validate_sc2(code, methods)
    if not res["ok"]:
        assert res["errorCode"] == "STATIC_VALIDATION_FAILED"
