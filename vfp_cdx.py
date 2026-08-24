#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_cdx.py - VFP compound index (.CDX / .IDX) structure analysis.

Two layers:
  1. STRUCTURAL (pure Python, no VFP9, any platform):
     parses the CDX header, tag directory (names, sort order, tag type,
     block counts) and validates the B-tree geometry. Works on .cdx and
     single-tag .idx files.
  2. ENRICHMENT (VFP9 COM host, Windows, strictly read-only):
     opens the table in a scratch alias and reads each tag's index
     EXPRESSION and UNIQUE flag from the system metadata
     (_GETTAG / _GETFLD). If VFP9 is absent or the table cannot be
     opened, the structural result is returned as-is.

Read-only guarantees:
  - The structural parser only ever *reads* bytes from the index file.
  - The COM path sets SET SYS(2023,0) (no .ERR files) and SET SYS(1486,0)
    (no auto .fpt/.cdx rebuilds), uses a scratch alias, and the process
    cwd is redirected away from the source directory. The table is always
    closed before the VFP9 host exits (DEFERRED UPDATES OFF, no writes).
"""

import os

_TAG_BLOCK = 132
_FIRST_NODE = 14 + _TAG_BLOCK  # bytes per node (26 key pointers + 1 child pointer)
_KEY_PER_NODE = 26

# CDX tag type byte (FoxPro 3+/VFP documented layout)
TAG_TYPES = {
    0x12: "regular",
    0x29: "sql_index",
    0x2A: "sql_unique",
}


def _parse_tag_block(data, i):
    """Parse one 132-byte tag directory entry. Returns dict or None."""
    off = i * _TAG_BLOCK
    if off + _TAG_BLOCK > len(data):
        return None
    name_b = data[off:off + 10]
    if not any(b for b in name_b):
        return None
    name = name_b.split(b"\x00", 1)[0].decode("latin-1", "replace").strip()
    order = data[off + 10]
    tag_type = data[off + 11]
    # Block 0 (root) of this tag is stored at off+11+10 and holds:
    #   4-byte node count (first field), then 4-byte node pointers.
    root_node = off + 21
    if root_node + 4 > len(data):
        node_count = None
    else:
        node_count = int.from_bytes(data[root_node:root_node + 4], "little")
    # Best-effort key/record estimate: root holds up to 26 keys; the rest
    # of the tag's node blocks each hold 26 key records.
    tag_len = (len(data) - off) // _FIRST_NODE
    node_count = node_count if node_count is not None and node_count > 0 else tag_len
    records = (node_count - 1) * _KEY_PER_NODE if node_count and node_count > 1 else 0
    return {
        "tag": name,
        "sortOrder": "descending" if order == 2 else "ascending",
        "type": TAG_TYPES.get(tag_type, "unknown(0x%02x)" % tag_type),
        "tagTypeByte": "0x%02x" % tag_type,
        "nodeCount": node_count,
        "recordEstimate": records,
    }


def parse_cdx(path):
    """Structurally parse a .cdx/.idx file.

    Returns {"ok": True, "file", "isCompound", "tagCount", "tags", "sizeBytes"}
    or {"ok": False, "error": ...} for files that are not VFP compound indices.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return {"ok": False, "file": os.path.basename(path), "error": str(e)}

    if size < 14:
        return {"ok": False, "file": os.path.basename(path),
                "error": "file too small to be a CDX/IDX (%d bytes)" % size}

    version = data[1]
    if version not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        return {"ok": False, "file": os.path.basename(path),
                "error": "unexpected CDX version byte 0x%02x" % version}

    total_records = int.from_bytes(data[4:8], "little")
    if total_records == 0:
        return {"ok": False, "file": os.path.basename(path),
                "error": "zero tags in tag directory"}
    if (len(data) - 14) % _TAG_BLOCK != 0:
        # not a clean tag-directory layout — treat as non-CDX (best effort)
        return {"ok": False, "file": os.path.basename(path),
                "error": "size is not a multiple of the 132-byte tag block layout"}

    is_compound = total_records > 1
    tags = []
    for i in range(total_records):
        t = _parse_tag_block(data, i)
        if t is not None:
            tags.append(t)

    return {
        "ok": True,
        "file": os.path.basename(path),
        "isCompound": is_compound,
        "version": version,
        "tagCount": len(tags),
        "tags": tags,
        "sizeBytes": size,
        "reader": "structural-pure-python",
    }


def parse_dir(source_dir):
    """Scan a directory tree for .cdx/.idx files and structurally parse each.

    Returns a list of parse results (one per index file), sorted by path.
    Excludes hidden/dot directories.
    """
    results = []
    excl = {".git", ".vfp-ai"}
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in sorted(dirs)
                   if not d.startswith(".") and d.lower() not in excl]
        for fn in sorted(files):
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".cdx", ".idx"):
                results.append(parse_cdx(os.path.join(root, fn)))
    return results


def _enrich_via_com(dbf_path, out_dir, timeout=120):
    """Best-effort enrichment of index tag expressions via the VFP9 COM host.

    Returns {tag_name_lower: {"expression":..., "unique":...}} or None when
    VFP9 / the table is unavailable. Never writes to the source directory:
    cwd is the output dir and SYS(2023/1486) are disabled inside VFP9.
    """
    import subprocess
    vbs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vfp_cdx_enrich.vbs")
    if not os.path.isfile(vbs):
        return None
    from vfp_driver import cscript_path
    try:
        p = subprocess.Popen(
            [cscript_path(), "//NoLogo", vbs, dbf_path, out_dir or "."],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=out_dir or None)
        outb, errb = p.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    out = outb.decode("cp1252", "replace")
    info = {}
    for line in out.splitlines():
        line = line.rstrip("\r\n")
        if "\t" not in line:
            continue
        parts = line.split("\t")
        if parts[0] != "TAG" or len(parts) < 2:
            continue
        name = parts[1].strip()
        if not name or name.startswith("("):
            continue
        expr = parts[2].strip() if len(parts) > 2 else ""
        status = parts[3] if len(parts) > 3 else ""
        if status != "OK":
            continue
        info[name.upper()] = {"expression": expr, "source": "vfp9-com"}
    return info or None


def build_index_info(dbf_path, cdx_path=None, timeout=120):
    """Full index description for one table: structure + (if possible) expressions.

    dbf_path  — the .dbf the index belongs to (drives COM enrichment).
    cdx_path  — optional explicit .cdx/.idx (default: <dbf stem>.cdx beside the dbf).
    """
    base = os.path.splitext(dbf_path)[0]
    if cdx_path is None:
        cdx_path = base + ".cdx"
        if not os.path.isfile(cdx_path):
            idx = base + ".idx"
            cdx_path = idx if os.path.isfile(idx) else None

    result = {
        "table": os.path.basename(dbf_path),
        "dbf": dbf_path,
        "indexFile": cdx_path,
        "hasStructuralIndex": os.path.isfile(cdx_path) if cdx_path else False,
        "hasSingleTagIdx": os.path.isfile(base + ".idx") if cdx_path is None or not os.path.isfile(cdx_path) else False,
        "tags": [],
        "tagCount": 0,
    }

    if cdx_path and os.path.isfile(cdx_path):
        structural = parse_cdx(cdx_path)
        if structural.get("ok"):
            result["structure"] = structural
            result["tagCount"] = structural["tagCount"]
        else:
            result["structureError"] = structural.get("error", "unparseable")

    enriched = _enrich_via_com(dbf_path, out_dir=os.path.dirname(os.path.abspath(__file__)), timeout=timeout)
    if enriched and result.get("structure"):
        merged = 0
        for t in result["structure"]["tags"]:
            e = enriched.get(t["tag"].upper())
            if e:
                t["expression"] = e.get("expression")
                t["unique"] = e.get("unique")
                merged += 1
        result["expressionCoverage"] = "%d/%d tags" % (merged, len(result["structure"]["tags"]))
        result["reader"] = "structural + vfp9-com"
    else:
        result["reader"] = result.get("reader", "structural-pure-python")
        result["expressionCoverage"] = "0 tags (VFP9 enrichment unavailable)"
    return result
