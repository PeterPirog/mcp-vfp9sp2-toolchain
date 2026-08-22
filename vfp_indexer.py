#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_indexer.py - Parse FoxBin2Prg SC2/VC2 text output into a symbol index.

Used by vfp_driver.py "index" subcommand and by the @vfp-analyst agent tooling.
Read-only: never modifies source files.

Usage:
    py vfp_indexer.py --project <root_dir> --cache <.vfp-ai> [--full]
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time


# ---------------------------------------------------------------------------
# SC2/VC2 parser
# ---------------------------------------------------------------------------

RE_FOXBIN2PRG_HEADER = re.compile(
    r'\*< FOXBIN2PRG:\s*Version="([^"]*)"\s+SourceFile="([^"]*)"\s+CPID="([^"]*)"', re.IGNORECASE)

RE_DEFINE_CLASS = re.compile(
    r'DEFINE\s+CLASS\s+(\w+)\s+AS\s+(\w+)(?:\s+OF\s+"([^"]+)")?', re.IGNORECASE)

RE_CLASSDATA = re.compile(r'\*< CLASSDATA:\s*(.+?)\s*/>', re.DOTALL)

RE_DEFINED_PROP_ARRAY = re.compile(
    r'\*<DefinedPropArrayMethod>\s*(.*?)\*</?DefinedPropArrayMethod\s*>', re.IGNORECASE | re.DOTALL)

RE_EXTERNAL_CLASS = re.compile(
    r'\*< EXTERNAL_CLASS:\s*Name="([^"]+)"\s+Baseclass="([^"]+)(?:".*)?"', re.IGNORECASE)

RE_OBJECTDATA = re.compile(
    r'\*< OBJECTDATA:\s*ObjPath="([^"]+)"', re.IGNORECASE)

RE_ADD_OBJECT = re.compile(
    r"ADD\s+OBJECT\s+'([^']+)'\s+AS\s+(\w+)(?:\s+OF\s+\"([^\"]+)\")?", re.IGNORECASE)

RE_PROP_VALUE = re.compile(
    r'\*<PropValue>\s*(.*?)\s*\*</?PropValue\s*>', re.DOTALL | re.IGNORECASE)

RE_PROCEDURE = re.compile(r'^\s*(?:PROTECTED\s+)?Procedure\s+(.+)$', re.IGNORECASE)

RE_ENDDEFINE = re.compile(r'^\s*ENDDEFINE\s*$', re.IGNORECASE)

RE_PROP_ASSIGN = re.compile(r'^\s*(\w+(?:\.\w+)?)\s*=\s*(.+?)\s*$')


def parse_sc2(filepath):
    """Parse a single .sc2/.vc2 file and return a dict of extracted symbols."""
    try:
        with open(filepath, "r", encoding="cp1252", errors="replace") as f:
            content = f.read()
    except OSError:
        return None

    result = {
        "file": filepath,
        "sourceFile": None,
        "foxbinVersion": None,
        "classes": [],
        "methods": [],
        "properties": [],
        "objects": [],
        "externalClasses": [],
        "rawLines": 0,
    }
    result["rawLines"] = content.count("\n") + 1

    # FoxBin2Prg header
    m = RE_FOXBIN2PRG_HEADER.search(content)
    if m:
        result["foxbinVersion"] = m.group(1)
        result["sourceFile"] = m.group(2).lower()

    # DEFINE CLASS ... ENDDEFINE blocks
    define_re = re.compile(
        r'DEFINE\s+CLASS\s+(\w+)\s+AS\s+(\w+)(?:\s+OF\s+"([^"]+)")?(.*?)(?=ENDDEFINE|\Z)',
        re.IGNORECASE | re.DOTALL)
    for dm in define_re.finditer(content):
        cls_name = dm.group(1)
        base_class = dm.group(2)
        class_lib = dm.group(3) or ""
        body = dm.group(4)

        # CLASSDATA
        classdata = {}
        cd = RE_CLASSDATA.search(body)
        if cd:
            for pair in re.findall(r'(\w+)="([^"]*)"', cd.group(1)):
                classdata[pair[0]] = pair[1]

        cls = {
            "name": cls_name,
            "baseClass": base_class,
            "classLib": class_lib,
            "classData": classdata,
            "methods": [],
            "properties": [],
            "objects": [],
        }

        # Properties within *<PropValue> block
        pv = RE_PROP_VALUE.search(body)
        if pv:
            for line in pv.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("*"):
                    continue
                pm = RE_PROP_ASSIGN.match(line)
                if pm:
                    cls["properties"].append({"name": pm.group(1), "value": pm.group(2)})

        # Methods declared in *<DefinedPropArrayMethod> block
        dp = RE_DEFINED_PROP_ARRAY.search(body)
        if dp:
            for line in dp.group(1).splitlines():
                stripped = line.strip()
                if stripped.startswith("*p:") or stripped.startswith("*m:"):
                    parts = stripped.split(None, 1)
                    if len(parts) >= 2:
                        method_name = parts[1].split("&&")[0].strip().split("\t")[0].strip()
                        cls["methods"].append({"name": method_name, "line": 0})
                elif stripped.startswith("*a:"):
                    parts = stripped.split(None, 1)
                    if len(parts) >= 2:
                        cls["properties"].append({"name": parts[1].split("&&")[0].strip().split("\t")[0].strip(), "value": "array"})

        # Methods via PROCEDURE ... ENDPROC
        for pline in body.splitlines():
            pm = RE_PROCEDURE.match(pline)
            if pm:
                cls["methods"].append({"name": pm.group(1).strip(), "line": 0})

        # ADD OBJECT within class body
        for am in RE_ADD_OBJECT.finditer(body):
            cls["objects"].append({
                "name": am.group(1),
                "baseClass": am.group(2),
                "classLib": am.group(3) or "",
            })

        result["classes"].append(cls)
        result["methods"].extend(cls["methods"])
        result["properties"].extend(cls["properties"])
        result["objects"].extend(cls["objects"])

    # External classes (top-level marker)
    for em in RE_EXTERNAL_CLASS.finditer(content):
        result["externalClasses"].append({
            "name": em.group(1),
            "baseClass": em.group(2),
        })

    # Top-level object data
    for om in RE_OBJECTDATA.finditer(content):
        result["objects"].append({"name": om.group(1), "baseClass": ""})

    return result


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Project-level scanning
# ---------------------------------------------------------------------------

VFP_EXTENSIONS = (".prg", ".h", ".sct", ".sc2", ".vc2", ".fr2", ".mn2",
                   ".dc2", ".lb2", ".db2", ".pjx", ".pjt", ".pj2")

VFP_BINARY_EXTS = (".prg", ".h", ".sc2", ".vc2", ".fr2", ".mn2",
                   ".dc2", ".lb2", ".pjx", ".pjt", ".pj2", ".dbc")


def scan_project(project, cache_dir, full=False):
    """Scan a project directory and build/update the index."""
    project = os.path.abspath(project)
    cache_dir = os.path.abspath(cache_dir)

    index = {
        "project": project,
        "cacheDir": cache_dir,
        "scannedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files": {},
        "classes": [],
        "methods": [],
        "symbols": {},
    }

    # Phase 1: Scan for VFP source files
    for root, dirs, files in os.walk(project):
        # Skip cache and hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__MACOSX"]
        for fn in sorted(files):
            ext = os.path.splitext(fn)[1].lower()
            if ext not in VFP_EXTENSIONS:
                continue
            fp = os.path.join(root, fn)
            try:
                st = os.stat(fp)
                rel = os.path.relpath(fp, project)
            except OSError:
                continue

            entry = {
                "path": rel,
                "size": st.st_size,
                "modified": st.st_mtime,
                "sha256": sha256_file(fp),
                "type": ext,
            }

            # If we have an SC2/VC2/PJ2 file, parse it for symbols
            if ext in (".sc2", ".vc2", ".pjx", ".pjt", ".pj2") and full:
                parsed = parse_sc2(fp)
                if parsed:
                    entry["symbols"] = {
                        "classes": parsed["classes"],
                        "methods": parsed["methods"],
                        "properties": parsed["properties"],
                        "objects": parsed["objects"],
                        "externalClasses": parsed["externalClasses"],
                    }
                    for cls in parsed["classes"]:
                        index["classes"].append({
                            "name": cls["name"],
                            "baseClass": cls["baseClass"],
                            "file": rel,
                        })
                    for meth in parsed["methods"]:
                        index["methods"].append({
                            "name": meth["name"],
                            "class": "",
                            "file": rel,
                        })

            index["files"][rel] = entry

    # Phase 2: Build flat symbol index for lookup
    for cls in index["classes"]:
        index["symbols"].setdefault(cls["name"], []).append(cls)
    for meth in index["methods"]:
        index["symbols"].setdefault(meth["name"], []).append(meth)

    return index


def run(project, cache, full=False):
    """Main entry point: scan project and write index.json to cache dir."""
    if not os.path.isdir(project):
        return {"error": "project directory not found: %s" % project}

    os.makedirs(cache, exist_ok=True)

    index = scan_project(project, cache, full=full)

    index_path = os.path.join(cache, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    return {
        "ok": True,
        "indexFile": index_path,
        "fileCount": len(index["files"]),
        "classCount": len(index["classes"]),
        "methodCount": len(index["methods"]),
    }


def main():
    ap = argparse.ArgumentParser(prog="vfp_indexer")
    ap.add_argument("--project", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()

    result = run(a.project, a.cache, full=a.full)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
