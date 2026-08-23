#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_driver.py - single Python entrypoint for the OpenCode VFP toolchain.

Subcommands:
  verno          --prg <foxbin2prg.prg>
  convert        --input <file-or-lib::class> --type T --out <folder> --cfg <cfg> --prg <prg>
  convert_dir    --project <root> --out <folder> --cfg <cfg> --prg <prg> [--timeout N]
  index          --project <root> --cache <.vfp-ai> [--full]
  dbf_schema     --input <table.dbf> --out <folder>
  dbf_data       --input <table.dbf> --out <folder> --format <jsonl|csv> [--deleted skip|separate|include]
  dbf_list       --dir <folder>

Output protocol: exactly one JSON object on stdout:
  {"ok": bool, "rc": int|null, "version": str|null, "stdout": str, "stderr": str, "data": {...}}
Exit code: 0 when ok, 2 when not ok.

Note on dbfread: DBF schema/data export uses the optional `dbfread` library
(same dependency as the dbfbridge project). If not installed, a built-in
minimal DBF reader is used as fallback. No hard dependency required.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfp_common

__version__ = "0.2.0"

HERE = os.path.dirname(os.path.abspath(__file__))
VBS = os.path.join(HERE, "vfp_convert.vbs")
VBS_VERNO = os.path.join(HERE, "vfp_verno.vbs")

# Extensions that can be converted to text via FoxBin2Prg (BIN2PRG).
# Matches config.json -> artifacts.bin2prg (single source of truth).
BIN_WRITEABLE = [".pjx", ".scx", ".vcx", ".frx", ".lbx", ".mnx", ".dbc", ".dbf"]


def emit(ok, **kw):
    """Emit a single JSON object on stdout and exit (0 ok / 2 not ok).

    Protocol: {"ok", "rc", "version", "stdout", "stderr", "data"} merged with kw.
    This function ALWAYS exits the process — callers must not return after it.
    """
    payload = {"ok": bool(ok), "rc": None, "version": None,
               "stdout": "", "stderr": "", "data": {}}
    payload.update(kw)
    out = json.dumps(payload, ensure_ascii=True)
    sys.stdout.write(out + "\n")
    sys.exit(0 if ok else 2)


def cscript_path():
    """Return the cscript executable path (Windows)."""
    from shutil import which
    return which("cscript.exe") or which("cscript") or "cscript"


def _run_process(cmd, timeout, cwd=None):
    """Run a command, capture stdout/stderr, return {stdout,stderr,code}. Handles timeouts by killing the process tree."""
    try:
        p = subprocess.Popen(cmd, cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        return {"stdout": "", "stderr": "exec not found: %s" % e, "code": -1}
    try:
        outb, errb = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        return {"stdout": "", "stderr": "TIMEOUT after %ss" % timeout, "code": -1}
    return {"stdout": outb.decode("cp1252", "replace"),
            "stderr": errb.decode("cp1252", "replace"),
            "code": p.returncode}


def _kill_tree(p):
    """Best-effort kill of a process plus any lingering vfp9.exe COM host."""
    try:
        p.kill()
    except Exception:
        pass
    try:
        subprocess.run(["taskkill", "/F", "/IM", "vfp9.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=15)
    except Exception:
        pass


def _parse_rc(stdout):
    """Extract the last RC=<int> line from FoxBin2Prg stdout, or None."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("RC="):
            try:
                return int(line[3:])
            except ValueError:
                return None
    return None


def run_verno(prg, timeout=120):
    """Check FoxBin2Prg version via vfp_verno.vbs."""
    vbs = os.path.join(HERE, "vfp_verno.vbs")
    if not os.path.isfile(vbs):
        emit(False, stderr="vfp_verno.vbs not found at " + vbs)
    res = _run_process([cscript_path(), "//NoLogo", vbs, prg],
                       timeout, cwd=os.path.dirname(os.path.abspath(prg)))
    ver = None
    for line in res["stdout"].splitlines():
        line = line.strip()
        if line.startswith("VERNO="):
            ver = line[6:].strip() or None
            break
    emit(ver is not None and ver != "unknown", version=ver,
         stdout=res["stdout"], stderr=res["stderr"], data={"prg": prg})


def _convert_one(inp, ctype, out, cfg, prg, timeout=600):
    """Run a single conversion. Returns result dict (does NOT emit/exit)."""
    if not os.path.isfile(VBS):
        return {"ok": False, "rc": -1, "stderr": "vfp_convert.vbs not found at " + VBS, "stdout": ""}
    args = [cscript_path(), "//NoLogo", VBS, inp, ctype, out, cfg, prg]
    cwd = os.path.dirname(os.path.abspath(inp)) or None
    res = _run_process(args, timeout, cwd=cwd)
    rc = _parse_rc(res["stdout"])
    return {"ok": rc == 0, "rc": rc, "stdout": res["stdout"], "stderr": res["stderr"],
            "data": {"input": inp, "type": ctype, "out": out}}


def run_convert(inp, ctype, out, cfg, prg, timeout=600):
    """Convert a single VFP binary file (BIN2PRG) to text."""
    result = _convert_one(inp, ctype, out, cfg, prg, timeout)
    emit(result["ok"], rc=result["rc"], stdout=result["stdout"],
         stderr=result["stderr"], data=result["data"])


def run_convert_dir(project, out, cfg, prg, timeout=600):
    """Scan a project directory for VFP binary files and convert each to text."""
    results = []
    excl = vfp_common.default_excludes()
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d.lower() not in excl]
        for fn in sorted(files):
            ext = os.path.splitext(fn)[1].lower()
            if ext in BIN_WRITEABLE:
                fp = os.path.join(root, fn)
                res = _convert_one(fp, "BIN2PRG", out, cfg, prg, timeout)
                results.append({
                    "file": os.path.relpath(fp, project),
                    "ok": res["ok"],
                    "rc": res["rc"],
                    "stderr": res["stderr"][:500],
                })
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    emit(ok_count > 0 if results else True,
         rc=0 if fail_count == 0 else 1,
         data={"total": len(results), "ok": ok_count, "failed": fail_count, "results": results},
         stdout="", stderr="")


def run_index(project, cache, full=False):
    """Build/refresh the symbol index from converted .sc2/.vc2 text."""
    sys.path.insert(0, HERE)
    try:
        import vfp_indexer
    except Exception as e:
        emit(False, stderr="cannot import vfp_indexer: %s" % e)
    # If we reach here, emit() exited on failure
    data = vfp_indexer.run(project, cache, full=full)
    emit(True, rc=0, data=data)


# ---------------------------------------------------------------------------
# DBF schema/data export (pure Python, no VFP9 required)
# Uses optional dbfread library with built-in fallback reader.
# ---------------------------------------------------------------------------

def run_dbf_schema(input_path, out_dir):
    """Export one DBF table schema to JSON (no VFP9 needed)."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        schema, schema_file, warnings = vfp_dbf_export.export_schema(input_path, out_dir)
        if schema:
            emit(True, rc=0,
                 table=schema.get("table"),
                 schemaFile=schema_file,
                 recordCount=schema.get("recordCount", 0),
                 fieldCount=schema.get("fieldCount", 0),
                 hasMemo=schema.get("hasMemo", False),
                 codePage=schema.get("codePage"),
                  reader=schema.get("reader", "dbfbridge"),
                 warnings=warnings,
                 data={"schemaFile": schema_file, "fields": schema.get("fields", [])})
        else:
            emit(False, stderr="; ".join(warnings))
    except Exception as e:
        emit(False, stderr="dbf_schema failed: %s" % e)


def run_dbf_data(input_path, out_dir, fmt, deleted):
    """Export one DBF table record data to JSONL/CSV (no VFP9 needed)."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        count, data_file, warnings = vfp_dbf_export.export_data(input_path, out_dir, fmt, deleted)
        if data_file:
            emit(True, rc=0,
                 table=os.path.splitext(os.path.basename(input_path))[0].upper(),
                 dataFile=data_file,
                 recordCount=count,
                 format=fmt,
                 warnings=warnings)
        else:
            emit(False, stderr="; ".join(warnings))
    except Exception as e:
        emit(False, stderr="dbf_data failed: %s" % e)


def run_dbf_list(dbf_dir):
    """List all DBF files in a directory tree."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        results = vfp_dbf_export.list_dbf(dbf_dir)
        emit(True, rc=0, data={"tables": results, "count": len(results)})
    except Exception as e:
        emit(False, stderr="dbf_list failed: %s" % e)


def run_dbf_dir(source, out, formats, deleted):
    """Batch-export a whole directory tree of DBF files (dbfbridge)."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        run, warnings = vfp_dbf_export._dbfbridge_export_dir(source, out, tuple(formats), deleted)
        emit(run.failed == 0,
             rc=run.exit_code,
             warnings=warnings,
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
                         "encoding": t.encoding,
                     }
                     for t in run.results
                 ],
             })
    except Exception as e:
        emit(False, stderr="dbf_dir batch export failed: %s" % e)


def run_audit(source, out, skip_sync, include_data, data_formats,
             max_tables=0, dbf_exclude="", no_cache_scan=False,
             include_forms=True):
    """Run the comprehensive VFP project audit."""
    sys.path.insert(0, HERE)
    try:
        import vfp_audit
    except Exception as e:
        emit(False, stderr="cannot import vfp_audit: %s" % e)
    try:
        auditor = vfp_audit.VFPProjectAuditor(
            source_dir=source, out_dir=out,
            skip_sync=skip_sync,
            include_data=include_data,
            data_formats=tuple(f.strip() for f in data_formats.split(",") if f.strip()),
            max_tables=max_tables,
            dbf_exclude=tuple(x for x in dbf_exclude.split(",") if x),
            scan_cache=not no_cache_scan,
            include_forms=include_forms,
        )
        result = auditor.run()
        emit(True, rc=0, auditDir=result["auditDir"],
             dataExport=result.get("dataExport"),
             formsExport=result.get("formsExport"), summary=result["summary"])
    except Exception as e:
        emit(False, stderr="audit failed: %s" % e)


def main():
    """argparse entrypoint dispatching subcommands."""
    ap = argparse.ArgumentParser(prog="vfp_driver")
    ap.add_argument("--version", action="version", version="vfp_driver " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("verno")
    pv.add_argument("--prg", required=True)

    pc = sub.add_parser("convert")
    pc.add_argument("--input", required=True)
    pc.add_argument("--type", required=True)
    pc.add_argument("--out", required=True)
    pc.add_argument("--cfg", required=True)
    pc.add_argument("--prg", required=True)
    pc.add_argument("--timeout", type=int, default=600)

    pcd = sub.add_parser("convert_dir")
    pcd.add_argument("--project", required=True)
    pcd.add_argument("--out", required=True)
    pcd.add_argument("--cfg", required=True)
    pcd.add_argument("--prg", required=True)
    pcd.add_argument("--timeout", type=int, default=600)

    pi = sub.add_parser("index")
    pi.add_argument("--project", required=True)
    pi.add_argument("--cache", required=True)
    pi.add_argument("--full", action="store_true")

    ps = sub.add_parser("dbf_schema", help="Export DBF file schema to JSON (no VFP9 needed)")
    ps.add_argument("--input", required=True, help="Path to .dbf file")
    ps.add_argument("--out", required=True, help="Output directory for _schema.json")

    pd = sub.add_parser("dbf_data", help="Export DBF record data to JSONL/CSV (no VFP9 needed)")
    pd.add_argument("--input", required=True, help="Path to .dbf file")
    pd.add_argument("--out", required=True, help="Output directory")
    pd.add_argument("--format", default="jsonl",
                    choices=["jsonl", "csv", "json", "xlsx"], help="Output format")
    pd.add_argument("--deleted", default="skip", choices=["skip", "separate", "include"],
                    help="Deleted record handling")

    pl = sub.add_parser("dbf_list", help="List all DBF files in a directory tree (no VFP9 needed)")
    pl.add_argument("--dir", required=True, help="Directory to scan")

    pdt = sub.add_parser("dbf_dir", help="Batch-export a whole directory tree of DBF files (no VFP9 needed)")
    pdt.add_argument("--source", required=True, help="Directory containing .dbf files")
    pdt.add_argument("--out", required=True, help="Output directory (mirrors the source tree)")
    pdt.add_argument("--formats", default="jsonl", help="Comma-separated formats: jsonl,csv,json,xlsx")
    pdt.add_argument("--deleted", default="include", choices=["skip", "separate", "include"],
                     help="Deleted record handling")

    pa = sub.add_parser("audit", help="Run comprehensive audit: sync + DBF schema + table relationships + class analysis")
    pa.add_argument("--source", required=True, help="VFP project root directory")
    pa.add_argument("--out", required=True, help="Output directory for audit report")
    pa.add_argument("--skip-sync", action="store_true", help="Skip BIN2PRG conversion (use existing cache)")
    pa.add_argument("--include-data", action="store_true",
                    help="OPTIONAL / SLOW: export ALL DBF record data (incl. memo/FPT) to "
                          "<audit>/dbf, mirroring the project folder structure")
    pa.add_argument("--data-formats", default="jsonl", help="Comma-separated data export formats: jsonl,csv,json,xlsx")
    pa.add_argument("--max-tables", type=int, default=0, help="With --include-data: limit to N largest tables (0=all)")
    pa.add_argument("--dbf-exclude", default="", help="Comma-separated uppercase substrings to exclude from DBF scan")
    pa.add_argument("--no-cache-scan", action="store_true", help="Do not scan .vfp-ai/source for table usage")
    pa.add_argument("--no-include-forms", dest="include_forms", action="store_false", default=True,
                    help="Skip exporting full form/class code (on by default)")

    a = ap.parse_args()
    if a.cmd == "verno":
        run_verno(a.prg)
    elif a.cmd == "convert":
        run_convert(a.input, a.type, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "convert_dir":
        run_convert_dir(a.project, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "index":
        run_index(a.project, a.cache, a.full)
    elif a.cmd == "dbf_schema":
        run_dbf_schema(a.input, a.out)
    elif a.cmd == "dbf_data":
        run_dbf_data(a.input, a.out, a.format, a.deleted)
    elif a.cmd == "dbf_list":
        run_dbf_list(a.dir)
    elif a.cmd == "dbf_dir":
        run_dbf_dir(a.source, a.out, a.formats, a.deleted)
    elif a.cmd == "audit":
        run_audit(a.source, a.out, a.skip_sync, a.include_data, a.data_formats,
                  a.max_tables, a.dbf_exclude, a.no_cache_scan,
                  include_forms=a.include_forms)


if __name__ == "__main__":
    main()
