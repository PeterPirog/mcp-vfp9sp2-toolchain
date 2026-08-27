#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_static_validate.py - static validation of FoxBin2Prg SC2/method code.

Validates TEXT methods (SC2 / method code). It never treats OBJCODE or SCT
binary bytes as text (those are never passed in; callers decode SC2 with
vfp_encoding and pass the method *code* strings).

Checks (each produces a finding with severity):
  * control characters (except tab/newline),
  * U+FFFD replacement character,
  * common bad-encoding artifacts (mojibake sequences, e.g. 'Ä'/'â€'),
  * suspicious literal escape artifacts  \\n  \\r  \\"  \\\\  outside strings,
  * Markdown fences (```),
  * accidental AI prompt fragments ("As an AI", "Here is the refactored", ...),
  * duplicated PROCEDURE names,
  * duplicated FUNCTION names,
  * duplicated large code blocks (same body in >1 method),
  * missing/extra ENDPROC / ENDFUNC / ENDIF / ENDCASE / ENDDO / ENDFOR /
    ENDSCAN / ENDWITH / ENDTRY (per-method balance),
  * suspicious code growth vs a baseline (optional).

Result:
    {"ok": bool, "status": "PASS"|"FAIL", "findings": [
        {"check", "severity": "error"|"warning", "message", "method"?}],
     "methodCount", "checksRun"}
"""

import re

CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
U_FFFD = "\ufffd"
MOJIBAKE_RE = re.compile(r"[\u00c2\u00e2\u00c3][\u2018\u2019\u201c\u201d\u2026\u0093\u0094]|â€|Ã.")
LITERAL_ESCAPE_RE = re.compile(r'\\[nrt"]|\\\\')
MD_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*")
AI_PROMPT_RE = re.compile(
    r"(?im)^\s*(as an ai|here is (the|a) |certainly!|i (hope|am happy|would be happy)|"
    r"i'?m (an )?ai|let me (help|explain)|refactored (code|version) below)",
)

# Keyword pairs for per-method balance checking.
PAIRS = [
    ("IF", "ENDIF"),
    ("DO", "ENDDO"),
    ("FOR", "ENDFOR"),
    ("CASE", "ENDCASE"),
    ("WHILE", "ENDWHILE"),
    ("SCAN", "ENDSCAN"),
    ("WITH", "ENDWITH"),
    ("TRY", "ENDTRY"),
    ("PROCEDURE", "ENDPROC"),
    ("FUNCTION", "ENDFUNC"),
]

_OPEN_RES = {}
_CLOSE_RES = {}
for _o, _c in PAIRS:
    _OPEN_RES[_o] = re.compile(r"^\s*" + _o + r"\b", re.IGNORECASE)
    _CLOSE_RES[_c] = re.compile(r"^\s*" + _c + r"\b", re.IGNORECASE)

GROWTH_SUSPICIOUS_FACTOR = 5.0


def _strip_strings_and_comments(code):
    """Return code with string literals and comments blanked out (lengths kept,
    line structure preserved) — so keyword counting is not fooled by e.g. a
    word ENDIF inside a string or comment."""
    out = []
    in_s = None
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if in_s:
            if c == "\n":
                out.append(c)
                in_s = None
                i += 1
                continue
            if c == in_s:
                if i + 1 < n and code[i + 1] == in_s:
                    out.append("  ")
                    i += 2
                    continue
                in_s = None
                out.append(" ")
                i += 1
                continue
            out.append(" ")
            i += 1
            continue
        if c in ("'", '"'):
            in_s = c
            out.append(" ")
            i += 1
            continue
        if code.startswith("(*", i):
            j = code.find("*)", i + 2)
            j = n if j < 0 else j + 2
            out.append(" " * (j - i))
            i = j
            continue
        if code.startswith("//", i):
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_controls(code, method=None):
    m = CTRL_RE.search(code)
    if m:
        return {"check": "control_characters", "severity": "error",
                "message": "unexpected control character U+%04X" % ord(m.group(0)),
                "method": method}
    return None


def check_fffd(code, method=None):
    if U_FFFD in code:
        return {"check": "replacement_char_u_fffd", "severity": "error",
                "message": "U+FFFD replacement character present (encoding corruption)",
                "method": method}
    return None


def check_mojibake(code, method=None):
    if MOJIBAKE_RE.search(code):
        return {"check": "mojibake_encoding_artifact", "severity": "error",
                "message": "common bad-encoding artifact sequence found",
                "method": method}
    return None


def check_literal_escapes(code, method=None):
    if LITERAL_ESCAPE_RE.search(code):
        return {"check": "literal_escape_artifact", "severity": "warning",
                "message": "literal backslash-escape artifact (\\n/\\r/\\\"/\\\\) in code",
                "method": method}
    return None


def check_markdown_fences(code, method=None):
    for line in code.splitlines():
        if MD_FENCE_RE.match(line):
            return {"check": "markdown_fence", "severity": "error",
                    "message": "Markdown code fence in method code", "method": method}
    return None


def check_ai_prompt_fragments(code, method=None):
    if AI_PROMPT_RE.search(code):
        return {"check": "ai_prompt_fragment", "severity": "warning",
                "message": "text resembling an AI prompt/answer fragment found in code",
                "method": method}
    return None


def check_duplicates(methods):
    """Duplicated PROCEDURE / FUNCTION names and duplicated large bodies."""
    findings = []
    by_kind = {"procedure": {}, "function": {}}
    for m in methods:
        by_kind[m["kind"]].setdefault(m["name"].lower(), []).append(m["name"])
    for kind, names in by_kind.items():
        for nm, occ in names.items():
            if len(occ) > 1:
                findings.append({
                    "check": "duplicate_%s" % kind, "severity": "error",
                    "message": "duplicated %s '%s' (%d occurrences)" % (kind, occ[0], len(occ)),
                })
    body_seen = {}
    for m in methods:
        body = m.get("code", "")
        if len(body) < 200:
            continue  # small bodies legitimately repeat
        key = body.strip()[:400]
        if key in body_seen:
            findings.append({
                "check": "duplicated_code_block", "severity": "error",
                "message": "method '%s' duplicates a large code block of '%s'"
                           % (m["name"], body_seen[key]),
                "method": m["name"],
            })
        else:
            body_seen[key] = m["name"]
    return findings


def check_end_balance(method, min_lines=3):
    """Per-method keyword balance on string/comment-stripped logical lines."""
    findings = []
    code = _strip_strings_and_comments(method.get("code", ""))
    lines = [l for l in code.splitlines() if l.strip()]
    if len(lines) < min_lines:
        return findings
    counts = {c: 0 for _o, c in PAIRS}
    expected_close = {}
    for line in lines:
        for o, c in PAIRS:
            if _OPEN_RES[o].match(line):
                if o in ("PROCEDURE", "FUNCTION"):
                    continue
                expected_close[c] = expected_close.get(c, 0) + 1
        for _o, c in PAIRS:
            if _CLOSE_RES[c].match(line):
                counts[c] += 1
    # IF ... ENDIF etc. must balance within the method body.
    for o, c in PAIRS:
        if o in ("PROCEDURE", "FUNCTION"):
            continue
        if expected_close.get(c, 0) != counts.get(c, 0):
            findings.append({
                "check": "end_balance", "severity": "error",
                "message": "%s (%d) vs %s (%d) imbalanced" %
                           (o, expected_close.get(c, 0), c, counts.get(c, 0)),
                "method": method["name"],
            })
    return findings


def check_growth(method, baseline_method):
    """Suspicious code growth vs the baseline (pre-patch) method."""
    if not baseline_method:
        return None
    a = baseline_method.get("lineCount") or 0
    b = method.get("lineCount") or 0
    if a and b > max(a * GROWTH_SUSPICIOUS_FACTOR, a + 50):
        return {"check": "suspicious_code_growth", "severity": "warning",
                "message": "method grew from %d to %d lines (factor > %.0f)"
                           % (a, b, GROWTH_SUSPICIOUS_FACTOR),
                "method": method["name"]}
    if b and not a:
        return {"check": "suspicious_code_growth", "severity": "warning",
                "message": "method appeared with %d lines (baseline had 0)" % b,
                "method": method["name"]}
    return None


def validate_sc2(text, methods=None, baseline_methods=None):
    """Run all static checks over SC2 text + its parsed methods.

    `methods` (list, see vfp_method_parser) is required for the method-level
    checks; when omitted, only the whole-text checks run (degraded mode).
    """
    findings = []
    whole = [
        check_controls(text),
        check_fffd(text),
        check_mojibake(text),
        check_markdown_fences(text),
    ]
    findings += [f for f in whole if f]

    methods = methods or []
    baseline_methods = baseline_methods or []
    base_by_name = {m["name"].lower(): m for m in baseline_methods}

    if methods:
        findings += check_duplicates(methods)
        for m in methods:
            findings += [f for f in [
                check_controls(m.get("code", ""), m["name"]),
                check_fffd(m.get("code", ""), m["name"]),
                check_mojibake(m.get("code", ""), m["name"]),
                check_literal_escapes(m.get("code", ""), m["name"]),
                check_markdown_fences(m.get("code", ""), m["name"]),
                check_ai_prompt_fragments(m.get("code", ""), m["name"]),
            ] if f]
            findings += check_end_balance(m)
            g = check_growth(m, base_by_name.get(m["name"].lower()))
            if g:
                findings.append(g)

    errors = [f for f in findings if f["severity"] == "error"]
    ok = not errors
    return {
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "errorCode": None if ok else "STATIC_VALIDATION_FAILED",
        "findings": findings,
        "methodCount": len(methods),
        "checksRun": 8 + (5 * len(methods) if methods else 0),
    }
