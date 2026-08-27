#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_method_parser.py - state-machine method parser for FoxBin2Prg SC2/VC2 text.

v0.2 indexed methods with line=0 and used a single regex for PROCEDURE. v0.3
parses method blocks with a lightweight lexer/state-machine that is robust to:

  * comments               (* ... *)  and  // ...
  * string literals         '...' (with '' escape)  and  "..."
  * line continuation       ;  at end of (logical) line
  * nested blocks           IF/ENDIF, DO/ENDDO, FOR/ENDFOR, CASE/ENDCASE,
                            WHILE/ENDWHILE, SCAN/ENDSCAN, WITH/ENDWITH,
                            TRY/ENDTRY — only to skip over keywords that
                            appear inside method bodies (they are ignored;
                            the top-level delimiters are PROCEDURE/ENDPROC and
                            FUNCTION/ENDFUNC)
  * both forms              PROCEDURE name ... ENDPROC   and
                            [PROTECTED] FUNCTION name ... ENDFUNC

The parser works on already-decoded text (use vfp_encoding.read_sc2_text to
decode with the CPID from the FoxBin2Prg header). It never touches the file
system and never modifies source.

Each method record:
    {"name", "kind": "procedure"|"function", "lineStart", "lineEnd",
     "code": str, "lineCount", "sourceSha256"}
"""

import hashlib

# Top-level delimiters (case-insensitive, word-bounded).
_PROC_RE = None  # compiled lazily to keep imports fast


def _words(line):
    """Split a line into VFP tokens (crude but sufficient for keyword matching)."""
    out = []
    cur = []
    in_s = None
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if in_s:
            cur.append(c)
            if c == in_s:
                if i + 1 < n and line[i + 1] == in_s:
                    cur.append(line[i + 1])
                    i += 2
                    continue
                in_s = None
            i += 1
            continue
        if c in ("'", '"'):
            in_s = c
            cur.append(c)
            i += 1
            continue
        if c == "*" and line.startswith("(*", i):
            j = line.find("*)", i + 2)
            j = n if j < 0 else j + 2
            cur.append(line[i:j].replace("\n", " "))
            i = j
            continue
        if c == "/" and line.startswith("//", i):
            break  # rest is a comment
        if c.isspace():
            if cur:
                out.append("".join(cur))
                cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur))
    return out


def _line_continues(line):
    """True if the logical line continues (trailing ';' outside strings/comments)."""
    in_s = None
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if in_s:
            if c == in_s:
                if i + 1 < n and line[i + 1] == in_s:
                    i += 2
                    continue
                in_s = None
            i += 1
            continue
        if c in ("'", '"'):
            in_s = c
            i += 1
            continue
        if c == "*" and line.startswith("(*", i):
            j = line.find("*)", i + 2)
            if j < 0:
                return True  # unterminated block comment -> continues
            i = j + 2
            continue
        if c == "/" and line.startswith("//", i):
            return False
        i += 1
    return line.rstrip().endswith(";")


def _strip_continuations(lines):
    """Merge physical lines joined by ';' into logical lines.

    Returns list of (logical_text, lineStart, lineEnd) 1-based inclusive.
    """
    logical = []
    buf = []
    start = None
    last = None
    for idx, line in enumerate(lines, start=1):
        if start is None:
            start = idx
        buf.append(line)
        last = idx
        if not _line_continues(line):
            logical.append((" ".join(b.strip() for b in buf), start, last))
            buf = []
            start = None
    if buf:
        logical.append((" ".join(b.strip() for b in buf), start or 1, last or 1))
    return logical


def _match_delimiter(logical, kind_start, kind_end):
    """Match a top-level delimiter line, returning the name or None.

    Handles:  [PROTECTED] PROCEDURE name
              [PROTECTED] FUNCTION name
              ENDPROC / ENDFUNC  (bare)
    """
    text = logical[0].strip()
    if not text:
        return None
    tokens = _words(text)
    if not tokens:
        return None
    first = tokens[0].upper()
    if first == "PROTECTED" and len(tokens) > 1:
        first = tokens[1].upper()
        tokens = tokens[1:]
    if first == kind_start:
        if len(tokens) >= 2:
            return tokens[1]
        return None
    if first == kind_end and len(tokens) == 1:
        return ""  # bare ENDPROC/ENDFUNC
    return None


def parse_methods(text):
    """Parse method blocks from SC2/VC2 text.

    Returns a list of method records (see module docstring). Order is source
    order. Methods inside DEFINE CLASS bodies are included; the owning class
    is resolved separately by the inventory builder (which walks the same text
    and tracks the current class).

    Unknown/unterminated blocks: an unterminated PROCEDURE at EOF is reported
    with "unterminated": True (validators can FAIL on it).
    """
    lines = text.splitlines()
    logical = _strip_continuations(lines)

    methods = []
    i = 0
    n = len(logical)
    while i < n:
        name = _match_delimiter(logical[i], "PROCEDURE", "ENDPROC")
        fname = _match_delimiter(logical[i], "FUNCTION", "ENDFUNC")
        if name is None and fname is None:
            i += 1
            continue
        if fname is not None and name is None:
            kind, mname = "function", fname
        else:
            kind, mname = "procedure", name
        if mname is None:
            i += 1
            continue
        line_start = logical[i][1]
        j = i + 1
        closed = False
        while j < n:
            if _match_delimiter(logical[j], "PROCEDURE", "ENDPROC") == "" and kind == "procedure":
                closed = True
                break
            if _match_delimiter(logical[j], "FUNCTION", "ENDFUNC") == "" and kind == "function":
                closed = True
                break
            # Nested same-kind declaration would indicate malformed text; we
            # still close on the FIRST matching END to keep the parse stable.
            j += 1
        line_end = logical[j][2] if closed else len(lines)
        code_lines = lines[line_start - 1:line_end]
        code = "\n".join(code_lines)
        methods.append({
            "name": mname,
            "kind": kind,
            "lineStart": line_start,
            "lineEnd": line_end,
            "lineCount": line_end - line_start + 1,
            "code": code,
            "sourceSha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
            "unterminated": not closed,
        })
        i = (j + 1) if closed else (i + 1)
    return methods


def methods_by_name(methods):
    """Index methods by lowercased name → list of records (duplicates kept)."""
    out = {}
    for m in methods:
        out.setdefault(m["name"].lower(), []).append(m)
    return out


def find_method(methods, name, kind=None):
    """Deterministically find a method by (case-insensitive) name.

    If multiple overloads exist (rare in VFP forms), the caller must disambiguate;
    this returns None for ambiguous matches instead of guessing.
    """
    cands = [m for m in methods
             if m["name"].lower() == (name or "").lower()
             and (kind is None or m["kind"] == kind)]
    if len(cands) == 1:
        return cands[0]
    return None


def method_code_sha256(code):
    """SHA256 of normalized method code (used for patch preconditions)."""
    return hashlib.sha256((code or "").encode("utf-8")).hexdigest()
