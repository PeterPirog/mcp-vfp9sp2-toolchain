#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_form_inventory.py - structural form inventory (SC2) + comparison.

Builds a deterministic structural snapshot of a form from its FoxBin2Prg SC2
text:

  * object tree — every DEFINE CLASS and ADD OBJECT, with:
      objectPath, name, baseClass, classLib, parent
  * stable UI properties — Top, Left, Width, Height, Caption, ControlSource,
      RowSource, RecordSource, Enabled, Visible, ReadOnly, TabIndex (and
      whatever else is present in the *<PropValue> block)
  * methods — via vfp_method_parser (name, kind, lineStart, lineEnd,
      lineCount, sourceSha256)

Comparison (compare_inventories):
  For a METHOD-ONLY refactor the object count and structure must be identical.
  Each object/property delta is marked EXPECTED (listed in the RefactorPlan)
  or UNEXPECTED. Any UNEXPECTED delta → FAIL (FORM_STRUCTURE_CHANGED).

Pure Python. Read-only over the .sc2 file (it is workspace text anyway).
"""

import json
import os
import re

import vfp_encoding
import vfp_method_parser

RE_DEFINE_CLASS = re.compile(
    r'^\s*DEFINE\s+CLASS\s+(\w+)\s+AS\s+(\w+)(?:\s+OF\s+"([^"]*)")?', re.IGNORECASE | re.MULTILINE)
RE_ADD_OBJECT = re.compile(
    r'^\s*ADD\s+OBJECT\s+\'([^\']+)\'\s+AS\s+(\w+)(?:\s+OF\s+"([^"]*)")?',
    re.IGNORECASE | re.MULTILINE)
RE_ENDDEFINE = re.compile(r'^\s*ENDDEFINE\s*$', re.IGNORECASE | re.MULTILINE)
RE_PROP_BLOCK = re.compile(
    r'^\s*([\w.]+)\s*=\s*(.+?)\s*$', re.MULTILINE)

STABLE_PROPS = (
    "Top", "Left", "Width", "Height", "Caption", "ControlSource",
    "RowSource", "RecordSource", "Enabled", "Visible", "ReadOnly",
    "TabIndex", "Style", "FontName", "FontSize", "Name", "RecordSourceType",
    "RowSourceType", "ControlSourceType",
)


def _norm(value):
    """Normalize a property value for comparison (bools/numbers/strings)."""
    if value is None:
        return None
    s = str(value).strip()
    # Strip one layer of VFP string quoting ("..." or '...')
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    up = s.upper()
    if up == ".T.":
        return True
    if up == ".F.":
        return False
    if up in (".C.", ".N.", ".D.", ".L.", ".M.", ".T"):
        return up
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def _split_class_bodies(lines):
    """Yield (class_header_line_idx, body_lines) for each DEFINE CLASS ... ENDDEFINE."""
    bodies = []
    current = None
    for idx, line in enumerate(lines):
        m = RE_DEFINE_CLASS.match(line)
        if m:
            if current:
                bodies.append(current)
            current = {"line": idx, "name": m.group(1),
                       "baseClass": m.group(2), "classLib": m.group(3) or ""}
            continue
        if current is not None:
            if RE_ENDDEFINE.match(line):
                current["endLine"] = idx
                bodies.append(current)
                current = None
            else:
                current.setdefault("body", []).append((idx, line))
    if current:
        current.setdefault("endLine", len(lines) - 1)
        bodies.append(current)
    return bodies


def build_inventory(sc2_path):
    """Build the structural inventory for one .sc2 file.

    Returns dict with: file, cpid, codec, suspiciousEncoding, objectCount,
    objects[...], methods[...], objectTree, encoding info.
    """
    text, enc = vfp_encoding.read_sc2_text(sc2_path)
    lines = text.splitlines()

    objects = []
    methods_all = []
    for body in _split_class_bodies(lines):
        obj = {
            "objectPath": body["name"],
            "name": body["name"],
            "baseClass": body["baseClass"],
            "classLib": body["classLib"],
            "parent": None,
            "properties": {},
            "lineStart": body["line"] + 1,
            "lineEnd": body.get("endLine", len(lines)) + 1,
        }
        # Properties: first *<PropValue> style assignments before the first
        # PROCEDURE/FUNCTION in this body.
        body_lines = body.get("body", [])
        for _, line in body_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            if re.match(r'^(PROTECTED\s+)?(PROCEDURE|FUNCTION)\b', stripped, re.IGNORECASE):
                break
            m = RE_PROP_BLOCK.match(line)
            if m:
                key = m.group(1)
                top = key.split(".")[0]
                if top in STABLE_PROPS or top.lower() in STABLE_PROPS:
                    obj["properties"][top] = _norm(m.group(2))
        objects.append(obj)

        # Methods in this class body (method parser over the whole body text).
        body_text = "\n".join(l for _, l in body_lines)
        for mm in vfp_method_parser.parse_methods(body_text):
            rec = {
                "objectPath": body["name"],
                "objectName": body["name"],
                "methodName": mm["name"],
                "kind": mm["kind"],
                "lineStart": mm["lineStart"],
                "lineEnd": mm["lineEnd"],
                "lineCount": mm["lineCount"],
                "sourceSha256": mm["sourceSha256"],
            }
            methods_all.append(rec)

    # ADD OBJECT children (nested controls)
    for m in RE_ADD_OBJECT.finditer(text):
        objects.append({
            "objectPath": m.group(1),
            "name": m.group(1).split(".")[-1] if "." in m.group(1) else m.group(1),
            "baseClass": m.group(2),
            "classLib": m.group(3) or "",
            "parent": m.group(1).rsplit(".", 1)[0] if "." in m.group(1) else None,
            "properties": {},
        })

    return {
        "file": os.path.abspath(sc2_path),
        "cpid": enc.get("cpid"),
        "codec": enc.get("codec"),
        "suspiciousEncoding": vfp_encoding.is_suspicious(enc),
        "objectCount": len(objects),
        "objects": objects,
        "methodCount": len(methods_all),
        "methods": methods_all,
        "rawLineCount": len(lines),
    }


def _expected_method_names(plan):
    """Method names the RefactorPlan is allowed to change (by object)."""
    out = {}
    for p in (plan or {}).get("patches", []):
        out.setdefault((p.get("objectPath") or "").upper(), set()).add(
            (p.get("method") or "").lower())
    return out


def compare_inventories(source_inv, final_inv, plan=None):
    """Compare source vs final inventories.

    Method-ONLY policy: object count + object structure + property values must
    be identical. Method SHAs may differ ONLY for (objectPath, method) pairs
    listed in the RefactorPlan (EXPECTED). Anything else → UNEXPECTED → FAIL.
    """
    findings = []
    expected = _expected_method_names(plan)

    # Object-level structure
    src_objs = {o["objectPath"].upper(): o for o in source_inv.get("objects", [])}
    fin_objs = {o["objectPath"].upper(): o for o in final_inv.get("objects", [])}

    added = sorted(set(fin_objs) - set(src_objs))
    removed = sorted(set(src_objs) - set(fin_objs))
    for name in added:
        findings.append({"objectPath": name, "change": "object_added",
                         "verdict": "UNEXPECTED",
                         "message": "object appears in final but not in source"})
    for name in removed:
        findings.append({"objectPath": name, "change": "object_removed",
                         "verdict": "UNEXPECTED",
                         "message": "object missing in final (present in source)"})

    property_changes = []
    for name in sorted(set(src_objs) & set(fin_objs)):
        s, f = src_objs[name], fin_objs[name]
        if s.get("baseClass", "").upper() != f.get("baseClass", "").upper():
            findings.append({"objectPath": name, "change": "baseClass",
                             "verdict": "UNEXPECTED",
                             "message": "baseClass %s -> %s" % (s.get("baseClass"), f.get("baseClass"))})
        props_s = {k.upper(): v for k, v in (s.get("properties") or {}).items()}
        props_f = {k.upper(): v for k, v in (f.get("properties") or {}).items()}
        keys = set(props_s) | set(props_f)
        for k in sorted(keys):
            if props_s.get(k) != props_f.get(k):
                property_changes.append({
                    "objectPath": name, "property": k,
                    "source": props_s.get(k), "final": props_f.get(k),
                    "verdict": "UNEXPECTED",
                })
    findings += property_changes

    # Method-level
    src_m = {(m["objectPath"].upper(), m["methodName"].lower()): m
            for m in source_inv.get("methods", [])}
    fin_m = {(m["objectPath"].upper(), m["methodName"].lower()): m
             for m in final_inv.get("methods", [])}

    method_changes = []
    for key in sorted(set(src_m) & set(fin_m)):
        s, f = src_m[key], fin_m[key]
        if s.get("sourceSha256") != f.get("sourceSha256"):
            verdict = "EXPECTED" if key[0] in expected and key[1] in expected[key[0]] else "UNEXPECTED"
            method_changes.append({
                "objectPath": key[0], "method": key[1],
                "sourceSha256": s.get("sourceSha256"),
                "finalSha256": f.get("sourceSha256"),
                "verdict": verdict,
            })
    for key in sorted(set(src_m) - set(fin_m)):
        method_changes.append({"objectPath": key[0], "method": key[1],
                               "change": "method_removed", "verdict": "UNEXPECTED"})
    for key in sorted(set(fin_m) - set(src_m)):
        method_changes.append({"objectPath": key[0], "method": key[1],
                               "change": "method_added", "verdict": "UNEXPECTED"})
    findings += method_changes

    unexpected = [f for f in findings if f.get("verdict") == "UNEXPECTED"]
    ok = not unexpected
    return {
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "errorCode": None if ok else "FORM_STRUCTURE_CHANGED",
        "sourceObjectCount": source_inv.get("objectCount", 0),
        "finalObjectCount": final_inv.get("objectCount", 0),
        "sourceMethodCount": source_inv.get("methodCount", 0),
        "finalMethodCount": final_inv.get("methodCount", 0),
        "unexpectedObjectChanges": [f for f in findings if f.get("change", "").startswith("object") or "baseClass" in f.get("change", "") or f.get("property")],
        "unexpectedPropertyChanges": property_changes,
        "methodChanges": method_changes,
        "expectedMethodChanges": [m for m in method_changes if m.get("verdict") == "EXPECTED"],
        "findings": findings,
    }
