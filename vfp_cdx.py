#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_cdx.py - VFP compound index (.CDX / .IDX) structure analysis.

Two layers:
  1. STRUCTURAL (pure Python, no VFP9, any platform):
     Scans 512-byte blocks to find tag descriptors. Each tag descriptor
     contains the tag name (10 bytes, null-padded ASCII), sort order, type
     flags, and root B-tree block pointer. Works on .cdx and .idx files.
  2. ENRICHMENT (VFP9 COM host, Windows, strictly read-only):
     Opens the table in a scratch alias and reads each tag's index
     EXPRESSION via SYST(325). If VFP9 is absent, the structural result
     is returned as-is.

CDX file format (FoxPro 2.x / VFP 9):
  - File is organized in fixed 512-byte blocks.
  - Block 0: file header (signature, pointers — format varies by VFP version).
  - Tag descriptors are 512-byte blocks scattered through the file. Each has:
      Bytes 0x00-0x09: tag name (10 bytes, null-padded, ASCII)
      Byte  0x0A:      sort order (0=ascending, 1=descending, 2=descending)
      Byte  0x0B:      type/flags (bit 0x02=unique, bit 0x20=descending)
      Bytes 0x0C-0x0F: root B-tree node block number (int32 LE)
  - B-tree nodes and expression text blocks are interleaved.
  - The header does NOT reliably store a tag count (it varies by VFP version),
    so we scan all blocks and identify tag descriptors by signature.

Read-only guarantees:
  - The structural parser only ever *reads* bytes from the index file.
  - The COM path sets SET SYS(2023,0) (no .ERR files) and SET SYS(1486,0)
    (no auto .fpt/.cdx rebuilds), uses a scratch alias, and the process
    cwd is redirected away from the source directory.
"""

import os
import struct

BLOCK_SIZE = 512

# Valid sort order byte values
_VALID_SORT = {0, 1, 2}

# Valid type/flag byte values (combinations seen in real CDX files)
_VALID_TYPE = {0x00, 0x01, 0x02, 0x10, 0x20, 0x12, 0x29, 0x2A, 0x30}


def _safe_name(data, offset, maxlen=10):
    """Extract a null-padded ASCII name from data at the given offset."""
    raw = data[offset:offset + maxlen]
    # Cut at first null
    for i in range(len(raw)):
        if raw[i] == 0:
            raw = raw[:i]
            break
    name = raw.decode("latin-1", "replace").strip()
    return name


def _is_valid_tag_name(name):
    """Check if a string looks like a valid VFP tag name.

    VFP tag names are 1-10 characters, alphanumeric + underscore.
    This filters out FOR-expression text blocks that happen to start with
    a readable string (e.g. '.NOT.DELETED()').
    """
    if not name or len(name) > 10:
        return False
    return all(c.isalnum() or c == "_" for c in name)


def _parse_tag_descriptor(data, block_index, total_blocks):
    """Parse one 512-byte block as a tag descriptor. Returns dict or None.

    A real tag descriptor has:
      - Valid ASCII tag name in bytes 0-9 (alphanumeric + underscore)
      - Sort order byte (0x0A) in {0, 1, 2}
      - Type/flags byte (0x0B) in the known set
      - Root block (0x0C-0x0F) either 0 or a valid block number
      - No readable text right after the name (bytes 10-19 are 0x00) — this
        distinguishes tag descriptors from FOR-expression text blocks which
        have the tag name followed by expression text.
    """
    off = block_index * BLOCK_SIZE
    if off + BLOCK_SIZE > len(data):
        return None

    name = _safe_name(data, off, 10)
    if not _is_valid_tag_name(name):
        return None

    # Check bytes 10-19: if there's readable text, this is a FOR-expression
    # block (tag name + expression text), not a tag descriptor.
    after_name = data[off + 10:off + 20]
    if any(32 <= b < 127 for b in after_name):
        return None

    sort_byte = data[off + 0x0A]
    type_byte = data[off + 0x0B]
    root_block = struct.unpack_from("<I", data, off + 0x0C)[0]

    if sort_byte not in _VALID_SORT:
        return None
    if type_byte not in _VALID_TYPE:
        return None
    if root_block != 0 and root_block >= total_blocks:
        return None

    sort_order = "ascending"
    if sort_byte in (1, 2) or (type_byte & 0x20):
        sort_order = "descending"

    tag_type = "regular"
    if type_byte & 0x02:
        tag_type = "unique"
    if type_byte in (0x29, 0x2A):
        tag_type = "sql_" + ("unique" if type_byte == 0x2A else "index")

    return {
        "tag": name,
        "sortOrder": sort_order,
        "type": tag_type,
        "tagTypeByte": "0x%02x" % type_byte,
        "rootBlock": root_block,
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

    if size < BLOCK_SIZE:
        return {"ok": False, "file": os.path.basename(path),
                "error": "file too small to be a CDX/IDX (%d bytes, need >= %d)" % (size, BLOCK_SIZE)}

    total_blocks = size // BLOCK_SIZE

    # Scan all blocks for tag descriptors
    tags = []
    for block in range(1, total_blocks):
        t = _parse_tag_descriptor(data, block, total_blocks)
        if t is not None:
            tags.append(t)

    ext = os.path.splitext(path)[1].lower()

    if tags:
        return {
            "ok": True,
            "file": os.path.basename(path),
            "isCompound": len(tags) > 1,
            "version": data[0],
            "tagCount": len(tags),
            "tags": tags,
            "sizeBytes": size,
            "blockSize": BLOCK_SIZE,
            "totalBlocks": total_blocks,
            "reader": "structural-pure-python",
        }

    # .idx single-tag: no tag descriptor found, report implicit tag
    if ext == ".idx":
        tag_name = os.path.splitext(os.path.basename(path))[0]
        return {
            "ok": True,
            "file": os.path.basename(path),
            "isCompound": False,
            "version": data[0],
            "tagCount": 1,
            "tags": [{
                "tag": tag_name,
                "sortOrder": "ascending",
                "type": "regular",
                "tagTypeByte": "0x00",
                "rootBlock": None,
            }],
            "sizeBytes": size,
            "blockSize": BLOCK_SIZE,
            "totalBlocks": total_blocks,
            "reader": "structural-pure-python-idx",
        }

    return {"ok": False, "file": os.path.basename(path),
            "error": "no tag descriptors found (size=%d, blocks=%d)" % (size, total_blocks)}


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

    Returns {tag_name_upper: {"expression":...}} or None when
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
            result["tags"] = structural.get("tags", [])
        else:
            result["structureError"] = structural.get("error", "unparseable")

    enriched = _enrich_via_com(dbf_path, out_dir=os.path.dirname(os.path.abspath(__file__)), timeout=timeout)
    if enriched and result.get("tags"):
        merged = 0
        for t in result["tags"]:
            e = enriched.get(t["tag"].upper())
            if e:
                t["expression"] = e.get("expression")
                merged += 1
        result["expressionCoverage"] = "%d/%d tags" % (merged, len(result["tags"]))
        result["reader"] = "structural + vfp9-com"
    else:
        result["reader"] = result.get("reader", "structural-pure-python")
        result["expressionCoverage"] = "0 tags (VFP9 enrichment unavailable)"
    return result