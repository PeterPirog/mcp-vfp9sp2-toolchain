#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_dbf_export.py - Export VFP DBF/FPT schema and data without VFP9.

Primary backend: dbfbridge (https://github.com/PeterPirog/dbfbridge)
  - streaming DBF/FPT reading with inline memo (FPT) support
  - automatic codepage detection with cp1250/cp852/Mazovia fallback
  - jsonl / csv / json / xlsx output formats
  - per-table *_schema.json with exact descriptors, encoding, memo metadata
  - migration_report.jsonl run summary

Fallback backends (when dbfbridge is not installed):
  - dbfread library (schema + non-memo data)
  - built-in minimal DBF reader (schema + non-memo data, no FPT)

Usage:
    py vfp_dbf_export.py schema --input table.dbf --out .vfp-ai/dbf
    py vfp_dbf_export.py data   --input table.dbf --out .vfp-ai/dbf --format jsonl --deleted include
    py vfp_dbf_export.py dir    --source <dbf_dir> --out <out_dir> --formats jsonl,csv
    py vfp_dbf_export.py list   --dir <dbf_dir>

Output protocol: one JSON object on stdout:
    {"ok": bool, "rc": int|null, "table": str, "schemaFile": str|null, "dataFile": str|null,
     "recordCount": int, "fieldCount": int, "warnings": [...], "stderr": str, "data": {...}}
"""

import argparse
import json
import os
import struct
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _ensure_vendored_dbfbridge_on_path():
    """Insert tools/dbfbridge into sys.path[0] so the vendored copy wins.

    This makes the VFP toolchain self-contained: it works even when the
    externally-installed ``dbfbridge`` distribution is absent, different, or
    incompatible (e.g. after the upstream repo evolved).
    """
    vendored = os.path.join(_HERE, "tools", "dbfbridge")
    if not os.path.isdir(os.path.join(vendored, "dbf_bridge")):
        return
    if not os.path.isfile(os.path.join(vendored, "VERSION.txt")):
        return
    path = os.path.abspath(vendored)
    if path not in sys.path:
        sys.path.insert(0, path)


_ensure_vendored_dbfbridge_on_path()


DBF_TYPE_NAMES = {
    "C": "Character",
    "N": "Numeric",
    "F": "Float",
    "D": "Date",
    "T": "@DT",
    "@": "DateTime",
    "L": "Logical",
    "M": "Memo",
    "G": "Memo (OLE)",
    "P": "Picture",
    "I": "Integer",
    "Y": "Currency",
    "S": "Stripped",
    "V": "Variant",
    "X": "Currency",
    "B": "Double",
    "0": "Binary",
    "+": "Autoincrement",
    "_": "Autoincrement",
}

DBF_DELETED_FLAG = 0x2A  # ord('*')


def _emit(ok, **kw):
    """Emit a single JSON object on stdout and exit (0 ok / 2 not ok)."""
    payload = {
        "ok": bool(ok),
        "rc": None,
        "table": None,
        "schemaFile": None,
        "dataFile": None,
        "recordCount": 0,
        "fieldCount": 0,
        "warnings": [],
        "stderr": "",
    }
    payload.update(kw)
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(0 if ok else 2)


def _find_outfile(out_dir, wanted):
    """Find a file in out_dir by name, case-insensitively. Returns full path or None."""
    direct = os.path.join(out_dir, wanted)
    if os.path.isfile(direct):
        return direct
    target = wanted.lower()
    for fn in os.listdir(out_dir):
        if fn.lower() == target:
            return os.path.join(out_dir, fn)
    return None


def _has_dbfbridge():
    """True if the vendored dbfbridge backend is importable."""
    try:
        import dbfbridge  # noqa: F401
        return True
    except ImportError:
        return False


def _has_dbfread():
    """True if the dbfread library is importable."""
    try:
        from dbfread import DBF  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# dbfbridge backend (preferred)
# ---------------------------------------------------------------------------

def _dbfbridge_export_table(dbf_path, out_dir, fmt, deleted):
    """Export a single table (schema + data) using dbfbridge.

    Returns (table_info_dict, warnings). table_info mirrors the legacy schema dict
    and points at the dbfbridge schema/data files.
    """
    from dbfbridge import export_dbf as _export

    dbf_path = os.path.abspath(dbf_path)
    parent = os.path.dirname(dbf_path)

    # dbfbridge refuses output inside the source tree; single-file export uses the
    # file's parent dir as the tree root, so run into a temp dir beside the table
    # and move the produced files back into the requested out dir.
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    run_out_dir = out_dir
    moved_back = False
    try:
        if os.path.commonpath([dbf_path, out_dir]) == parent:
            run_out_dir = os.path.join(parent, ".dbfbridge_tmp_out")
            os.makedirs(run_out_dir, exist_ok=True)
    except ValueError:
        pass

    try:
        run = _export(
            dbf_path, run_out_dir,
            formats=(fmt,),
            memo="inline",
            deleted=deleted,
            missing_memo="null-with-warning",
            overwrite=True,
            validate=True,
        )
    finally:
        if run_out_dir != out_dir and os.path.isdir(run_out_dir):
            for fn in os.listdir(run_out_dir):
                os.replace(os.path.join(run_out_dir, fn), os.path.join(out_dir, fn))
            os.rmdir(run_out_dir)
            moved_back = True

    warnings = []
    failed = [t for t in run.results if getattr(t, "status", "") == "FAILED"]
    for t in failed:
        for e in (t.errors or []):
            warnings.append("dbfbridge: %s" % e)

    # Locate produced files (dbfbridge preserves original filename casing)
    basename = os.path.splitext(os.path.basename(dbf_path))[0]
    schema_file = _find_outfile(out_dir, "%s_schema.json" % basename)
    data_file = _find_outfile(out_dir, "%s.%s" % (basename, fmt))

    if not schema_file:
        return None, ["dbfbridge schema file not found for %s" % basename]

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_raw = json.load(f)

    info = _normalize_dbfbridge_schema(schema_raw, dbf_path, schema_file, run)
    info["dataFile"] = data_file if (data_file and os.path.isfile(data_file)) else None
    if run.ok is False or failed:
        if warnings:
            info["warnings"] = warnings
    return info, warnings


def _normalize_dbfbridge_schema(schema_raw, dbf_path, schema_file, run):
    """Convert dbfbridge schema JSON into the legacy schema dict shape."""
    fields = []
    for i, f in enumerate(schema_raw.get("fields", [])):
        fields.append({
            "name": f.get("name"),
            "type": f.get("dbf_type"),
            "typeName": f.get("dbf_type_name") or DBF_TYPE_NAMES.get(f.get("dbf_type"), f.get("dbf_type")),
            "length": f.get("length"),
            "decimal": f.get("decimal_count", 0) or 0,
            "position": f.get("ordinal", i + 1),
            "isMemo": bool(f.get("is_memo")),
            "binary": bool(f.get("is_binary")),
        })

    enc = schema_raw.get("text_encoding", {}) or {}
    memo = schema_raw.get("memo", {}) or {}
    has_memo = bool(fields) and any(f.get("isMemo") for f in fields)

    table_info = getattr(run, "results", (None,))
    active = deleted_n = 0
    for t in table_info:
        if getattr(t, "status", "") in ("OK", "WARNING") or getattr(t, "status", "") not in ("FAILED",):
            active = getattr(t, "active_records", 0) or active
            deleted_n = getattr(t, "deleted_records", 0) or deleted_n

    return {
        "table": schema_raw.get("table") or os.path.splitext(os.path.basename(dbf_path))[0].upper(),
        "sourceFile": os.path.basename(dbf_path),
        "recordCount": active,
        "deletedCount": deleted_n,
        "fieldCount": len(fields),
        "fields": fields,
        "codePage": enc.get("declared_or_detected_encoding"),
        "encodingFallbacks": enc.get("fallback_order"),
        "hasMemo": has_memo,
        "memoFields": [f["name"] for f in fields if f.get("isMemo")],
        "memoFile": memo.get("path"),
        "schemaFile": schema_file,
        "reader": "dbfbridge",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "schemaSource": schema_raw,
    }


def _dbfbridge_export_dir(source_dir, out_dir, formats, deleted):
    """Export a whole directory tree of DBF files with a single dbfbridge run."""
    from dbfbridge import export_dbf as _export

    os.makedirs(out_dir, exist_ok=True)
    source_dir = os.path.abspath(source_dir)
    out_dir = os.path.abspath(out_dir)

    run = _export(
        source_dir, out_dir,
        formats=tuple(formats),
        memo="inline",
        deleted=deleted,
        missing_memo="null-with-warning",
        overwrite=True,
        validate=True,
    )

    warnings = []
    for t in run.results:
        if getattr(t, "status", "") == "FAILED":
            for e in (t.errors or []):
                warnings.append("dbfbridge: %s" % e)
    return run, warnings


# ---------------------------------------------------------------------------
# dbfread backend (fallback 1)
# ---------------------------------------------------------------------------

def _resolve_codepage(table_obj):
    """Best-effort codepage detection from a dbfread Table or our fallback reader."""
    cp = getattr(table_obj, "codepage", None)
    if cp and hasattr(cp, "name"):
        return cp.name
    if isinstance(cp, int):
        cp_map = {
            1: "cp1252", 2: "cp1252", 3: "cp1252", 4: "cp437",
            120: "cp1252", 121: "cp1250", 122: "cp1251", 123: "cp1253",
            124: "cp1254", 125: "cp1255", 126: "cp1256", 127: "cp1257",
            128: "cp1250", 129: "cp1252", 130: "cp1252", 131: "cp1252",
            132: "cp1252", 133: "cp1250", 134: "cp1251", 135: "cp1253",
            136: "cp1254", 137: "cp1255", 138: "cp1256", 139: "cp1257",
            209: "cp1252", 208: "cp1251",
            210: "cp866", 211: "cp866", 212: "cp866", 213: "cp866",
        }
        return cp_map.get(cp, "cp1252")
    return "cp1252"


def _dbfread_schema(dbf_path):
    """Read DBF using dbfread library. Returns (schema_dict, dbf_read_table_or_rows)."""
    from dbfread import DBF

    try:
        table = DBF(dbf_path, load=False, ignore_missing_memofile=True,
                    encoding="cp1252")
    except TypeError:
        table = DBF(dbf_path, load=False, encoding="cp1252")
    codepage = _resolve_codepage(table)

    fields = []
    for i, f in enumerate(table.fields):
        fields.append({
            "name": f.name,
            "type": f.type,
            "typeName": DBF_TYPE_NAMES.get(f.type, f.type),
            "length": f.length,
            "decimal": getattr(f, "decimal_count", 0) or 0,
            "position": i + 1,
            "isMemo": f.type in ("M", "G", "P"),
            "binary": f.type == "0",
        })

    schema = {
        "table": os.path.splitext(os.path.basename(dbf_path))[0].upper(),
        "sourceFile": os.path.basename(dbf_path),
        "recordCount": len(table),
        "fieldCount": len(fields),
        "fields": fields,
        "codePage": codepage,
        "hasMemo": any(f["type"] in ("M", "G", "P") for f in fields),
        "memoFields": [f["name"] for f in fields if f["type"] in ("M", "G", "P")],
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "reader": "dbfread",
    }
    return schema, table, codepage


def _rec_deleted(rec):
    """Deleted flag across dbfread versions (attribute or key)."""
    d = getattr(rec, "deleted", None)
    if d is not None:
        return bool(d)
    return bool(rec.get("__deleted__", False))


def _jsonable(val):
    """Convert dbfread values into JSON-serializable primitives."""
    import datetime as _dt
    if isinstance(val, bytes):
        return val.decode("utf-8", "replace")
    if isinstance(val, (_dt.datetime, _dt.date, _dt.time)):
        return val.isoformat()
    if isinstance(val, (list, tuple)):
        return [_jsonable(v) for v in val]
    if isinstance(val, dict):
        return {str(k): _jsonable(v) for k, v in val.items()}
    return val


def _dbfread_data(table, out_path, fmt, deleted, codepage, schema=None):
    """Export records using dbfread."""
    if schema is None:
        schema = {"fields": []}
    if table is None:
        return 0, ["table is None"]
    count = 0
    warnings = []

    if deleted == "include":
        record_set = table.records
    else:
        record_set = [r for r in table.records if not _rec_deleted(r)]

    try:
        with open(out_path, "w", encoding="utf-8") as out:
            if fmt == "jsonl":
                for rec in record_set:
                    row = {}
                    for k in rec.keys():
                        val = rec[k]
                        if isinstance(val, bytes):
                            val = val.decode(codepage or "cp1252", "replace")
                        row[k] = val
                    row["__deleted__"] = _rec_deleted(rec)
                    out.write(json.dumps(row, ensure_ascii=False, default=_jsonable) + "\n")
                    count += 1
            elif fmt == "csv":
                import csv
                writer = csv.writer(out)
                header = [f["name"] for f in schema["fields"]] + ["__deleted__"]
                writer.writerow(header)
                for rec in record_set:
                    row = []
                    for f in schema["fields"]:
                        val = rec[f["name"]] if f["name"] in rec else ""
                        if isinstance(val, bytes):
                            val = val.decode(codepage or "cp1252", "replace")
                        row.append(val)
                    row.append(_rec_deleted(rec))
                    writer.writerow(row)
                    count += 1
        return count, warnings
    except Exception as e:
        warnings.append("data_export_failed: %s" % e)
        return count, warnings


# ---------------------------------------------------------------------------
# Fallback reader (minimal DBF parser, no external deps)
# ---------------------------------------------------------------------------

def _fallback_schema(dbf_path):
    """
    Minimal built-in DBF reader.
    Supports DBF (dBASE IV/VFP) header + field descriptors + record data.
    Does NOT handle memo/FPT content (only flags presence).
    """
    warnings = []

    try:
        with open(dbf_path, "rb") as f:
            header = f.read(32)
            if len(header) < 32:
                return None, warnings, "file too small to be a DBF"

            version_byte = header[0]
            record_count = struct.unpack("<I", header[4:8])[0]
            header_len = struct.unpack("<H", header[8:10])[0]
            record_len = struct.unpack("<H", header[10:12])[0]

            memo_versions = {0x30, 0x31, 0x83, 0x87, 0xCB}
            has_memo = version_byte in memo_versions

            basename = os.path.splitext(os.path.basename(dbf_path))[0].upper()

            fpt_block_size = struct.unpack("<H", header[29:30] + b"\x00")[0]
            code_page_id = header[29] if len(header) >= 30 else 0
            if code_page_id == 0:
                code_page_id = header[30] if len(header) >= 31 else 0

            codepage = "cp1252"  # default
            cp_map = {
                0x01: "cp1252", 0x02: "cp1252", 0x03: "cp1252", 0x7F: "cp437",
                0x96: "cp1250", 0x97: "cp1251", 0x98: "cp1251", 0x99: "cp1252",
                0x9A: "cp1253", 0x9B: "cp1253", 0x9C: "cp1254", 0x9D: "cp1254",
                0x9E: "cp1255", 0x9F: "cp1255", 0xA0: "cp1257", 0xA1: "cp1256",
                0xA2: "cp1257", 0xA3: "cp1250", 0xA4: "cp1251", 0xA5: "cp1251",
                0xA6: "cp1252", 0xC8: "cp1252", 0xC9: "cp1252",
                0xCA: "cp1252", 0xCB: "cp1252", 0xE8: "cp1250", 0xE9: "cp1251",
            }
            if code_page_id in cp_map:
                codepage = cp_map[code_page_id]

            fields = []
            offset = 32
            while True:
                field_header = f.read(32)
                if len(field_header) < 32:
                    break
                if field_header[0:1] == b"\x0D":
                    break

                name_bytes = field_header[0:11]
                name = name_bytes.split(b"\x00")[0].decode(codepage, "replace").strip().upper()

                field_type = chr(field_header[11])
                field_length = field_header[16]
                actual_length = struct.unpack("<I", field_header[16:20])[0] if field_type in ("C", "M") else field_header[16]
                decimal_count = field_header[17] if field_type in ("N", "F") else 0

                fields.append({
                    "name": name,
                    "type": field_type,
                    "typeName": DBF_TYPE_NAMES.get(field_type, field_type),
                    "length": actual_length,
                    "decimal": decimal_count,
                    "position": len(fields) + 1,
                    "isMemo": field_type in ("M", "G", "P"),
                    "binary": field_type == "0",
                })

            schema = {
                "table": basename,
                "sourceFile": os.path.basename(dbf_path),
                "recordCount": record_count,
                "fieldCount": len(fields),
                "fields": fields,
                "codePage": codepage,
                "hasMemo": has_memo,
                "memoFields": [f["name"] for f in fields if f["type"] in ("M", "G", "P")],
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "reader": "fallback",
            }
            return schema, warnings, None
    except Exception as e:
        return None, warnings, str(e)

    return None, warnings, "unknown error"


def _fallback_data(dbf_path, out_path, fmt, deleted, schema):
    """Minimal record reader (no dbfread). Reads raw field values."""
    warnings = []
    count = 0
    codepage = schema["codePage"]

    try:
        with open(dbf_path, "rb") as f:
            header = f.read(32)
            record_count = struct.unpack("<I", header[4:8])[0]
            header_len = struct.unpack("<H", header[8:10])[0]
            record_len = struct.unpack("<H", header[10:12])[0]

            f.seek(header_len)

            fields = schema["fields"]
            field_offsets = []
            offset = 0
            for fld in fields:
                field_offsets.append((offset, fld["length"], fld["type"], fld["name"]))
                offset += fld["length"]

            with open(out_path, "w", encoding="utf-8") as out:
                if fmt == "jsonl":
                    for _ in range(record_count):
                        rec_bytes = f.read(record_len)
                        if len(rec_bytes) < record_len:
                            break
                        is_deleted = rec_bytes[0:1] == b"*"
                        if is_deleted and deleted != "include":
                            continue

                        row = {}
                        pos = 1
                        for foff, flen, ftype, fname in field_offsets:
                            raw = rec_bytes[pos:pos + flen]
                            val = raw.strip(b"\x00 ")
                            if ftype == "C":
                                val = val.decode(codepage, "replace").strip()
                            elif ftype in ("N", "F"):
                                val = val.decode("ascii", "replace").strip()
                            elif ftype == "D":
                                val = val.decode("ascii", "replace").strip()
                            elif ftype == "L":
                                val = "T" if val == b"T" else ("F" if val == b"F" else "?")
                            elif ftype == "M":
                                val = "(memo)"
                            else:
                                val = val.decode(codepage, "replace").strip()
                            pos += flen
                            row[fname] = val
                        row["__deleted__"] = is_deleted
                        out.write(json.dumps(row, ensure_ascii=False) + "\n")
                        count += 1
    except Exception as e:
        warnings.append("data_export_failed: %s" % e)

    return count, warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_schema(dbf_path, out_dir):
    """Export DBF schema to <table>_schema.json in out_dir. Returns (schema, schema_file, warnings)."""
    os.makedirs(out_dir, exist_ok=True)

    if _has_dbfbridge():
        try:
            info, warnings = _dbfbridge_export_table(dbf_path, out_dir, "jsonl", "skip")
            if info is not None:
                # dbfbridge schema file already written in out_dir
                return info, info.get("schemaFile"), warnings
        except Exception as e:
            if not _has_dbfread():
                return None, None, ["dbfbridge failed: %s" % e]

    if _has_dbfread():
        schema, table_obj, codepage = _dbfread_schema(dbf_path)
    else:
        schema, warnings, err = _fallback_schema(dbf_path)
        if err:
            return None, None, [err]
        if schema is None:
            return None, None, ["schema is None but no error reported"]

    schema_file = os.path.join(out_dir, "%s_schema.json" % schema["table"])
    with open(schema_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    return schema, schema_file, []


def export_data(dbf_path, out_dir, fmt="jsonl", deleted="skip"):
    """Export DBF records to <table>.<fmt> in out_dir. Returns (count, data_file, warnings)."""
    os.makedirs(out_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(dbf_path))[0]

    if fmt in ("jsonl", "csv", "json", "xlsx") and _has_dbfbridge():
        try:
            info, warnings = _dbfbridge_export_table(dbf_path, out_dir, fmt, deleted)
            if info and info.get("dataFile"):
                return info.get("recordCount", 0), info["dataFile"], warnings
        except Exception as e:
            if not _has_dbfread():
                return 0, None, ["dbfbridge failed: %s" % e]

    if fmt not in ("jsonl", "csv"):
        return 0, None, ["format %s requires dbfbridge" % fmt]

    if _has_dbfread():
        schema, table_obj, codepage = _dbfread_schema(dbf_path)
    else:
        schema, _, err = _fallback_schema(dbf_path)
        if err:
            return 0, None, [err]
        if schema is None:
            return 0, None, ["schema is None but no error reported"]
        codepage = schema["codePage"]
        table_obj = None

    data_file = os.path.join(out_dir, "%s.%s" % (basename, fmt))

    if _has_dbfread() and table_obj is not None:
        count, warnings = _dbfread_data(table_obj, data_file, fmt, deleted, codepage, schema)
    else:
        schema2, _, err2 = _fallback_schema(dbf_path)
        if err2:
            return 0, None, [err2]
        count, warnings = _fallback_data(dbf_path, data_file, fmt, deleted, schema2)

    return count, data_file, warnings


def scan_dbf(dbf_path):
    """Read a single DBF file. Returns a compact dict with schema info. No data export."""
    if _has_dbfbridge():
        try:
            from pathlib import Path as _Path
            from dbf_bridge.exporter.discovery import DiscoveredTable, find_related_file
            from dbf_bridge.exporter.models import ExportConfig
            from dbf_bridge.exporter.reader import read_table_metadata

            dbf_abs = _Path(os.path.abspath(dbf_path))
            memo_path = find_related_file(dbf_abs, ".fpt")
            discovered = DiscoveredTable(
                source_path=dbf_abs,
                relative_path=_Path(dbf_abs.name),
                memo_path=memo_path,
                memo_present=bool(memo_path and memo_path.is_file()),
            )
            config = ExportConfig(
                source=_Path(str(dbf_abs.parent)),
                output=_Path(tempfile.gettempdir()),
                missing_memo="null-with-warning",
            )
            meta = read_table_metadata(discovered, config)
            return {
                "table": meta.table_name.upper(),
                "sourceFile": dbf_abs.name,
                "recordCount": meta.record_count,
                "fieldCount": len(meta.fields),
                "fields": [
                    {
                        "name": f.name,
                        "type": f.dbf_type,
                        "typeName": DBF_TYPE_NAMES.get(f.dbf_type, f.dbf_type),
                        "length": f.length,
                        "decimal": f.decimal_count,
                        "position": f.ordinal,
                        "isMemo": f.is_memo,
                        "binary": f.is_binary,
                    }
                    for f in meta.fields
                ],
                "codePage": meta.encoding,
                "hasMemo": any(f.is_memo for f in meta.fields),
                "memoFields": [f.name for f in meta.fields if f.is_memo],
                "reader": "dbfbridge",
            }
        except Exception as e:
            return {"error": str(e), "file": dbf_path, "reader": "dbfbridge"}
    if _has_dbfread():
        try:
            schema, _, _ = _dbfread_schema(dbf_path)
            return schema if schema is not None else {"error": "dbfread returned None"}
        except Exception as e:
            return {"error": str(e), "file": dbf_path}
    schema, warnings, err = _fallback_schema(dbf_path)
    if err:
        return {"error": err, "file": dbf_path}
    return schema if schema is not None else {"error": "fallback reader returned None"}


def list_dbf(dbf_path):
    """List all DBF files in a directory tree. Returns list of dicts."""
    results = []
    for root, dirs, files in os.walk(dbf_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() == ".dbf":
                fp = os.path.join(root, fn)
                schema = scan_dbf(fp)
                entry = {
                    "path": os.path.relpath(fp, dbf_path),
                    "file": os.path.basename(fp),
                    "table": schema.get("table", os.path.splitext(fn)[0].upper()),
                    "recordCount": schema.get("recordCount", 0),
                    "fieldCount": schema.get("fieldCount", 0),
                    "hasMemo": schema.get("hasMemo", False),
                    "codePage": schema.get("codePage", "unknown"),
                    "reader": schema.get("reader", "unknown"),
                }
                if "error" in schema:
                    entry["error"] = schema["error"]
                results.append(entry)
    return results


def backend_info():
    """Report which DBF backend is active and where it comes from."""
    dbfbridge_active = _has_dbfbridge()
    dbfread_active = _has_dbfread()
    source = None
    if dbfbridge_active:
        try:
            import dbfbridge
            path = getattr(dbfbridge, "__file__", "") or ""
            if os.path.abspath(path).startswith(os.path.join(_HERE, "tools", "dbfbridge")):
                source = "vendored (tools/dbfbridge)"
            else:
                source = "site-packages"
        except Exception:
            source = "unknown"
    return {
        "dbfbridge": dbfbridge_active,
        "dbfbridgeSource": source,
        "dbfread": dbfread_active,
        "active": "dbfbridge" if dbfbridge_active
                  else ("dbfread" if dbfread_active else "fallback"),
    }


def main():
    """argparse entrypoint for the DBF export CLI."""
    ap = argparse.ArgumentParser(prog="vfp_dbf_export")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("schema", help="Export DBF schema to JSON")
    ps.add_argument("--input", required=True, help="Path to .dbf file")
    ps.add_argument("--out", required=True, help="Output directory for _schema.json")

    pd = sub.add_parser("data", help="Export DBF records to JSONL/CSV/JSON/XLSX")
    pd.add_argument("--input", required=True, help="Path to .dbf file")
    pd.add_argument("--out", required=True, help="Output directory")
    pd.add_argument("--format", default="jsonl",
                    choices=["jsonl", "csv", "json", "xlsx"], help="Output format")
    pd.add_argument("--deleted", default="skip", choices=["skip", "separate", "include"],
                    help="Deleted record handling")

    pb = sub.add_parser("dir", help="Export a directory tree of DBF files (dbfbridge batch)")
    pb.add_argument("--source", required=True, help="Directory containing .dbf files")
    pb.add_argument("--out", required=True, help="Output directory")
    pb.add_argument("--formats", default="jsonl",
                    help="Comma-separated formats: jsonl,csv,json,xlsx")
    pb.add_argument("--deleted", default="include",
                    choices=["skip", "separate", "include"],
                    help="Deleted record handling (default include for archival)")

    pl = sub.add_parser("list", help="List all DBF files in a directory")
    pl.add_argument("--dir", required=True, help="Directory to scan")

    a = ap.parse_args()

    if a.cmd == "schema":
        schema, schema_file, warnings = export_schema(a.input, a.out)
        if schema:
            _emit(True,
                  table=schema["table"],
                  schemaFile=schema_file,
                  recordCount=schema.get("recordCount", 0),
                  fieldCount=schema.get("fieldCount", 0),
                  reader=schema.get("reader"),
                  warnings=warnings,
                  data={"fields": schema.get("fields", [])})
        else:
            _emit(False, stderr="; ".join(warnings))

    elif a.cmd == "data":
        count, data_file, warnings = export_data(a.input, a.out, a.format, a.deleted)
        if data_file:
            _emit(True,
                  table=os.path.splitext(os.path.basename(a.input))[0].upper(),
                  dataFile=data_file,
                  recordCount=count,
                  format=a.format,
                  warnings=warnings)
        else:
            _emit(False, stderr="; ".join(warnings))

    elif a.cmd == "dir":
        if not _has_dbfbridge():
            _emit(False, stderr="dbfbridge is required for 'dir' batch export. "
                                "It is vendored in this repo at tools/dbfbridge — "
                                "ensure tools/dbfbridge is present and dbfread is installed "
                                "(py -m pip install dbfread orjson xlsxwriter openpyxl dbf).")
        formats = tuple(f.strip() for f in a.formats.split(",") if f.strip())
        try:
            run, warnings = _dbfbridge_export_dir(a.source, a.out, formats, a.deleted)
            _emit(run.failed == 0,
                  rc=run.exit_code,
                  data={
                      "successful": run.successful,
                      "failed": run.failed,
                      "tables": [
                          {
                              "table": t.table,
                              "status": t.status,
                              "format": t.format,
                              "activeRecords": t.active_records,
                              "deletedRecords": t.deleted_records,
                              "memoFields": list(t.memo_fields or []),
                              "encoding": t.encoding,
                          }
                          for t in run.results
                      ],
                      "migrationReport": str(run.migration_report_jsonl)
                      if run.migration_report_jsonl else None,
                  },
                  warnings=warnings)
        except Exception as e:
            _emit(False, stderr="dbfbridge dir export failed: %s" % e)

    elif a.cmd == "list":
        results = list_dbf(a.dir)
        _emit(True, data={"tables": results, "count": len(results),
                          "backend": backend_info()})


if __name__ == "__main__":
    main()
