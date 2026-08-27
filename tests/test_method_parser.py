"""Tests for the v0.3 method parser (PROCEDURE/FUNCTION, line ranges, robustness)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_method_parser as mp


SAMPLE = """DEFINE CLASS form1 AS Form
    *< CLASSDATA: Baseclass="Form" />
    PROCEDURE Init
        LOCAL x
        x = 'has ENDIF in a string'
        IF x = 'a'
            ? 1
        ENDIF
        ? 'done'
    ENDPROC

    FUNCTION ComputeValue
        LOCAL n
        n = 1
        FOR i = 1 TO 3
            n = n + i
        ENDFOR
        RETURN n
    ENDFUNC

    PROCEDURE WeirdComments
        (* comment with ENDFUNC inside *)
        // another ENDFUNC
        ? 'ENDPROC'
    ENDPROC
"""


def test_procedure_parsed():
    methods = mp.parse_methods(SAMPLE)
    names = [m["name"] for m in methods]
    assert "Init" in names
    init = [m for m in methods if m["name"] == "Init"][0]
    assert init["kind"] == "procedure"
    assert init["lineStart"] == 3  # 1-based
    assert init["lineEnd"] >= 8
    assert "ENDIF" in init["code"]


def test_function_parsed():
    methods = mp.parse_methods(SAMPLE)
    cv = [m for m in methods if m["name"] == "ComputeValue"][0]
    assert cv["kind"] == "function"
    assert cv["lineStart"] < cv["lineEnd"]
    assert "ENDFOR" in cv["code"]


def test_line_ranges_real():
    methods = mp.parse_methods(SAMPLE)
    for m in methods:
        assert m["lineStart"] >= 1
        assert m["lineEnd"] >= m["lineStart"]
        assert m["lineCount"] == m["lineEnd"] - m["lineStart"] + 1


def test_sha_present():
    methods = mp.parse_methods(SAMPLE)
    for m in methods:
        assert m["sourceSha256"] and len(m["sourceSha256"]) == 64


def test_endfunc_in_comment_ignored():
    methods = mp.parse_methods(SAMPLE)
    weird = [m for m in methods if m["name"] == "WeirdComments"][0]
    # must close at the real ENDPROC, not the comment
    assert "ENDPROC" in weird["code"].splitlines()[-1].upper()


def test_find_method_deterministic():
    methods = mp.parse_methods(SAMPLE)
    assert mp.find_method(methods, "init") is not None
    assert mp.find_method(methods, "nope") is None
    # ambiguous: duplicate names → None (no guessing)
    dup = [
        {"name": "A", "kind": "procedure"},
        {"name": "A", "kind": "function"},
    ]
    assert mp.find_method(dup, "A") is None


def test_line_continuation_merged():
    text = (
        "PROCEDURE Long\n"
        "   ? 1 ;\n"
        "     ? 2\n"
        "ENDPROC\n"
    )
    methods = mp.parse_methods(text)
    assert len(methods) == 1
    assert "? 1" in methods[0]["code"]
    assert "? 2" in methods[0]["code"]


def test_nested_blocks_counted():
    text = (
        "PROCEDURE N\n"
        "   DO Something\n"
        "      ENDDO\n"
        "   SCAN tbl\n"
        "      ENDSCAN\n"
        "   WHILE .T.\n"
        "      ENDWHILE\n"
        "   FOR i = 1 TO 2\n"
        "      ENDFOR\n"
        "ENDPROC\n"
    )
    methods = mp.parse_methods(text)
    assert methods[0]["name"] == "N"
    assert methods[0]["lineEnd"] >= methods[0]["lineStart"] + 6
