#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_dbf_export.py - Export VFP DBF/FPT schema and data without VFP9.

Uses the `dbfread` library (same core dependency as dbfbridge) when available,
falling back to a built-in minimal DBF reader so there is no hard dependency.

Inspiration: dbfbridge (https://github.com/PeterPirog/dbfbridge) by Peter Pirog.
This module re-implements the schema + data export portion only, using dbfread
directly instead of requiring the dbfbridge package.

Usage:
    py vfp_dbf_export.py schema  --input table.dbf --out .vfp-ai/dbf
    py vfp_dbf_export.py data    --input table.dbf --out .vfp-ai/dbf --format jsonl --deleted skip

Output protocol: one JSON object on stdout:
    {"ok": bool, "rc": int|null, "table": str, "schemaFile": str|null, "dataFile": str|null,
     "recordCount": int, "fieldCount": int, "warnings": [...], "stderr": str}
"""

import argparse
import json
import os
import struct
import sys
import time


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
    "0": "Picture",
    "S": "Stripped",
    "V": "Variant",
    "X": "Currency",
    "B": "Double",
    "+": "Autoincrement",
    "0": "Binary",
    "_": "Autoincrement",
}

DBF_DELETED_FLAG = 0x2A  # ord('*')


def _emit(ok, **kw):
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


# ---------------------------------------------------------------------------
# dbfread backend
# ---------------------------------------------------------------------------

def _dbfread_schema(dbf_path):
    """Read DBF using dbfread library. Returns (schema_dict, dbf_read_table_or_rows)."""
    from dbfread import DBF

    table = DBF(dbf_path, load=False, ignore_missing_memo=True,
                encoding="cp1252")  # We'll handle encoding manually
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
        })

    schema = {
        "table": os.path.splitext(os.path.basename(dbf_path))[0].upper(),
        "sourceFile": os.path.basename(dbf_path),
        "recordCount": len(table),
        "fieldCount": len(fields),
        "fields": fields,
        "codePage": codepage,
        "hasMemo": any(f["type"] in ("M", "G", "P") for f in fields),
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return schema, table, codepage


def _dbfread_data(table, out_path, fmt, deleted, codepage, schema=None):
    """Export records using dbfread."""
    if schema is None:
        schema = {"fields": []}
    if table is None:
        return 0, ["table is None"]
    count = 0
    warnings = []

    # Resolve encoding
    if deleted == "include":
        deleted_set = table.records
    else:
        deleted_set = [r for r in table.records if not r.deleted]

    try:
        with open(out_path, "w", encoding="utf-8") as out:
            if fmt == "jsonl":
                for rec in deleted_set:
                    row = {}
                    for k in rec.keys():
                        val = rec[k]
                        if isinstance(val, bytes):
                            val = val.decode(codepage or "cp1252", "replace")
                        row[k] = val
                    row["__deleted__"] = rec.deleted
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
            elif fmt == "csv":
                import csv
                writer = csv.writer(out)
                header = [f["name"] for f in schema["fields"]] + ["__deleted__"]
                writer.writerow(header)
                for rec in deleted_set:
                    row = []
                    for f in schema["fields"]:
                        val = rec[f["name"]] if f["name"] in rec else ""
                        if isinstance(val, bytes):
                            val = val.decode(codepage or "cp1252", "replace")
                        row.append(val)
                    row.append(rec.deleted)
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
            # Last update date (unused for schema)
            record_count = struct.unpack("<I", header[4:8])[0]
            header_len = struct.unpack("<H", header[8:10])[0]
            record_len = struct.unpack("<H", header[10:12])[0]
            # Reserved bytes 12-27

            # Determine if memo (version byte)
            # VFP (8) and dBASE IV (13) use FPT
            memo_versions = {0x30, 0x31, 0x83, 0x87, 0xCB}
            has_memo = version_byte in memo_versions

            # Table name from filename
            basename = os.path.splitext(os.path.basename(dbf_path))[0].upper()

            # Check for codepage byte at offset 29-30 (DBT/FPT block size)
            fpt_block_size = struct.unpack("<H", header[29:30] + b"\x00")[0]
            code_page_id = header[29] if len(header) >= 30 else 0
            if code_page_id == 0:
                code_page_id = header[30] if len(header) >= 31 else 0

            # VFP codepage detection from byte 29+? Actually VFP stores it elsewhere
            # For VFP, the codepage is in the database header differently
            # Let's try a different approach

            codepage = "cp1252"  # default
            # Common DBF codepage IDs (dBASE)
            cp_map = {
                0x01: "cp1252", 0x02: "cp1252", 0x03: "cp1252", 0x7F: "cp437",
                0x96: "cp1250", 0x97: "cp1251", 0x98: "cp1251", 0x99: "cp1252",
                0x9A: "cp1253", 0x9B: "cp1253", 0x9C: "cp1254", 0x9D: "cp1254",
                0x9E: "cp1255", 0x9F: "cp1255", 0xA0: "cp1257", 0xA1: "cp1256",
                0xA2: "cp1257", 0xA3: "cp1250", 0xA4: "cp1251", 0xA5: "cp1251",
                0xA6: "cp1252", 0x01: "cp1252", 0xC8: "cp1252", 0xC9: "cp1252",
                0xCA: "cp1252", 0xCB: "cp1252", 0xE8: "cp1250", 0xE9: "cp1251",
            }
            if code_page_id in cp_map:
                codepage = cp_map[code_page_id]

            # Read field descriptors
            fields = []
            offset = 32
            while True:
                field_header = f.read(32)
                if len(field_header) < 32:
                    break
                if field_header[0:1] == b"\x0D":  # End-of-field marker (0x0D)
                    break

                name_bytes = field_header[0:11]
                name = name_bytes.split(b"\x00")[0].decode(codepage, "replace").strip().upper()

                field_type = chr(field_header[11])
                field_length = field_header[16]
                # For VFP, field length can be in bytes 16-18 as a 32-bit value
                actual_length = struct.unpack("<I", field_header[16:20])[0] if field_type in ("C", "M") else field_header[16]
                decimal_count = field_header[17] if field_type in ("N", "F") else 0

                fields.append({
                    "name": name,
                    "type": field_type,
                    "typeName": DBF_TYPE_NAMES.get(field_type, field_type),
                    "length": actual_length,
                    "decimal": decimal_count,
                    "position": len(fields) + 1,
                })

            schema = {
                "table": basename,
                "sourceFile": os.path.basename(dbf_path),
                "recordCount": record_count,
                "fieldCount": len(fields),
                "fields": fields,
                "codePage": codepage,
                "hasMemo": has_memo,
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
                            elif ftype == "N" or ftype == "F":
                                val = val.decode("ascii", "replace").strip()
                            elif ftype == "D":
                                val = val.decode("ascii", "replace").strip()
                            elif ftype == "L":
                                val = "T" if val == b"T" else ("F" if val == b"F" else "?")
                            elif ftype == "M":
                                val = "(memo)"  # We can't read FPT without more work
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
    basename = os.path.splitext(os.path.basename(dbf_path))[0].upper()

    try:
        from dbfread import DBF
        USE_DBFREAD = True
    except ImportError:
        USE_DBFREAD = False

    if USE_DBFREAD:
        schema, table_obj, codepage = _dbfread_schema(dbf_path)
    else:
        schema, warnings, err = _fallback_schema(dbf_path)
        if err:
            return None, None, [err]
        if schema is None:
            return None, None, ["schema is None but no error reported"]
        codepage = schema["codePage"]
        table_obj = None
        warnings = []

    schema_file = os.path.join(out_dir, "%s_schema.json" % basename)
    with open(schema_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    return schema, schema_file, []


def export_data(dbf_path, out_dir, fmt="jsonl", deleted="skip"):
    """Export DBF records to <table>.<fmt> in out_dir. Returns (count, data_file, warnings)."""
    os.makedirs(out_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(dbf_path))[0].upper()

    try:
        from dbfread import DBF
        USE_DBFREAD = True
    except ImportError:
        USE_DBFREAD = False

    if USE_DBFREAD:
        schema, table_obj, codepage = _dbfread_schema(dbf_path)
    else:
        schema, _, err = _fallback_schema(dbf_path)
        if err:
            return 0, None, [err]
        if schema is None:
            return 0, None, ["schema is None but no error reported"]
        codepage = schema["codePage"]
        table_obj = None

    ext = "jsonl" if fmt == "jsonl" else "csv"
    data_file = os.path.join(out_dir, "%s.%s" % (basename, ext))

    if USE_DBFREAD:
        count, warnings = _dbfread_data(table_obj, data_file, fmt, deleted, codepage, schema)
    else:
        schema2, _, err2 = _fallback_schema(dbf_path)
        if err2:
            return 0, None, [err2]
        count, warnings = _fallback_data(dbf_path, data_file, fmt, deleted, schema2)

    return count, data_file, warnings


def scan_dbf(dbf_path):
    """Read a single DBF file. Returns a compact dict with schema info. No data export."""
    try:
        from dbfread import DBF
        schema, _, codepage = _dbfread_schema(dbf_path)
        return schema if schema is not None else {"error": "dbfread returned None"}
    except ImportError:
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
                }
                if "error" in schema:
                    entry["error"] = schema["error"]
                results.append(entry)
    return results


def main():
    ap = argparse.ArgumentParser(prog="vfp_dbf_export")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("schema", help="Export DBF schema to JSON")
    ps.add_argument("--input", required=True, help="Path to .dbf file")
    ps.add_argument("--out", required=True, help="Output directory for _schema.json")

    pd = sub.add_parser("data", help="Export DBF records to JSONL or CSV")
    pd.add_argument("--input", required=True, help="Path to .dbf file")
    pd.add_argument("--out", required=True, help="Output directory")
    pd.add_argument("--format", default="jsonl", choices=["jsonl", "csv"], help="Output format")
    pd.add_argument("--deleted", default="skip", choices=["skip", "separate", "include"],
                    help="Deleted record handling")

    pl = sub.add_parser("list", help="List all DBF files in a directory")
    pl.add_argument("--dir", required=True, help="Directory to scan")

    a = ap.parse_args()

    if a.cmd == "schema":
        schema, schema_file, warnings = export_schema(a.input, a.out)
        if schema:
            _emit(True,
                  table=schema["table"],
                  schemaFile=schema_file,
                  recordCount=schema["recordCount"],
                  fieldCount=schema["fieldCount"],
                  warnings=warnings)
        else:
            _emit(False, stderr="; ".join(warnings))

    elif a.cmd == "data":
        count, data_file, warnings = export_data(a.input, a.out, a.format, a.deleted)
        if data_file:
            _emit(True,
                  table=os.path.splitext(os.path.basename(a.input))[0].upper(),
                  dataFile=data_file,
                  recordCount=count,
                  warnings=warnings)
        else:
            _emit(False, stderr="; ".join(warnings))

    elif a.cmd == "list":
        results = list_dbf(a.dir)
        _emit(True, data={"tables": results, "count": len(results)})


if __name__ == "__main__":
    main()
