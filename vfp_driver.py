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
from typing import NoReturn

import vfp_common
import vfp_protocol

__version__ = "0.3.0"

HERE = os.path.dirname(os.path.abspath(__file__))
VBS = os.path.join(HERE, "vfp_convert.vbs")
VBS_VERNO = os.path.join(HERE, "vfp_verno.vbs")

# Extensions that can be converted to text via FoxBin2Prg (BIN2PRG).
# Matches config.json -> artifacts.bin2prg (single source of truth).
BIN_WRITEABLE = [".pjx", ".scx", ".vcx", ".frx", ".lbx", ".mnx", ".dbc", ".dbf"]


def emit(ok, **kw) -> NoReturn:
    """Emit a single JSON object on stdout and exit (0 ok / 2 not ok).

    Protocol: {"ok", "status", "errorCode", "rc", "version", "stdout",
    "stderr", "data"} — see vfp_protocol.result_payload.
    This function ALWAYS exits the process — callers must not return after it.
    """
    kw.setdefault("version", __version__)
    vfp_protocol.emit(ok, **kw)


def cscript_path():
    """Return the cscript executable path (Windows)."""
    from shutil import which
    return which("cscript.exe") or which("cscript") or "cscript"


def _run_process(cmd, timeout, cwd=None):
    """Run a command with a timeout.

    Timeout policy (v0.3): ONLY the child PID spawned by the toolchain may be
    terminated (vfp_protocol.run_process → TerminateProcess(pid)). The
    toolchain must not terminate vfp9.exe instances by image name — those may
    belong to other users/sessions. A timed-out VFP9 COM host that cannot be
    attributed to this operation is reported as VFP9_TIMEOUT with a
    manual-diagnostics instruction instead.
    """
    res = vfp_protocol.run_process(cmd, timeout, cwd=cwd)
    return {"stdout": res["stdout"], "stderr": res["stderr"],
            "code": res["code"], "timeout": res["timeout"]}


def _timeout_error(res, data=None):
    """Emit a clean VFP9_TIMEOUT failure for a timed-out child process."""
    emit(False, status=vfp_protocol.STATUS_FAIL,
         errorCode=vfp_protocol.EC_VFP9_TIMEOUT,
         rc=-2, stdout=res.get("stdout", ""), stderr=res.get("stderr", ""),
         data=data or {})


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
        emit(False, status=vfp_protocol.STATUS_FAIL,
             errorCode="MISSING_TOOLING", stderr="vfp_verno.vbs not found at " + vbs)
    res = _run_process([cscript_path(), "//NoLogo", vbs, prg],
                       timeout, cwd=os.path.dirname(os.path.abspath(prg)))
    if res["timeout"]:
        _timeout_error(res, data={"prg": prg})
    ver = None
    for line in res["stdout"].splitlines():
        line = line.strip()
        if line.startswith("VERNO="):
            ver = line[6:].strip() or None
            break
    ok = ver is not None and ver != "unknown"
    emit(ok, status=vfp_protocol.STATUS_PASS if ok else vfp_protocol.STATUS_FAIL,
         errorCode=None if ok else vfp_protocol.EC_VFP9_NOT_AVAILABLE,
         version=ver,
         stdout=res["stdout"], stderr=res["stderr"], data={"prg": prg})


def _convert_one(inp, ctype, out, cfg, prg, timeout=600):
    """Run a single conversion. Returns result dict (does NOT emit/exit).

    v0.3: SHA256 of the input + its companions is captured BEFORE and AFTER
    the BIN2PRG conversion. Any mutation of the source is a CRITICAL failure
    (enforced in code, not by agent instructions).
    """
    import vfp_safety
    if not os.path.isfile(VBS):
        return {"ok": False, "rc": -1, "status": "FAIL", "errorCode": "MISSING_TOOLING",
                "stderr": "vfp_convert.vbs not found at " + VBS, "stdout": ""}
    hash_guard = vfp_safety.SourceHashGuard(
        [inp] + [c for c in vfp_common.required_companions(inp) if os.path.isfile(c)])
    before = hash_guard.capture()

    args = [cscript_path(), "//NoLogo", VBS, inp, ctype, out, cfg, prg]
    # Run with a scratch cwd so any VFP9 side-effect (e.g. .ERR / .fpt) is
    # written next to the OUTPUT dir, never into the source project.
    run_cwd = out or os.path.dirname(os.path.abspath(inp)) or None
    res = _run_process(args, timeout, cwd=run_cwd)
    if res["timeout"]:
        return {"ok": False, "rc": -2, "status": "FAIL",
                "errorCode": vfp_protocol.EC_VFP9_TIMEOUT,
                "stdout": res["stdout"], "stderr": res["stderr"],
                "data": {"input": inp, "type": ctype, "out": out}}
    rc = _parse_rc(res["stdout"])
    # Surface a missing companion file (e.g. .sct/.fpt) as an explicit reason —
    # FoxBin2Prg returns rc=41 "missing companion" with an empty stderr, which
    # used to be confusing (real-run report #1/#6).
    missing = vfp_common.missing_companions(inp)
    if rc == 41 and missing:
        res["stderr"] = ("missing companion file(s) required by FoxBin2Prg: "
                         + ", ".join(os.path.basename(m) for m in missing))

    # SOURCE MUTATION GUARD (v0.3): BIN2PRG must be read-only. If anything
    # changed in the source files, this is CRITICAL even if rc==0.
    after = verify_capture(before, hash_guard.file_paths)
    source_intact = after["ok"]
    data = {"input": inp, "type": ctype, "out": out,
            "missingCompanions": [os.path.relpath(m, os.path.dirname(inp)) for m in missing]}
    if not source_intact:
        data["sourceHashGuard"] = after
        return {"ok": False, "rc": rc, "status": "FAIL",
                "errorCode": vfp_protocol.EC_CRITICAL_SOURCE_MUTATION,
                "stdout": res["stdout"], "stderr": res["stderr"],
                "data": data}
    if source_intact:
        data["sourceHashGuard"] = {"ok": True, "checked": len(before.get("files", {}))}
    return {"ok": rc == 0, "rc": rc,
            "status": vfp_protocol.STATUS_PASS if rc == 0 else vfp_protocol.STATUS_FAIL,
            "errorCode": None if rc == 0 else ("MISSING_COMPANION" if missing and rc == 41 else "CONVERSION_FAILED"),
            "stdout": res["stdout"], "stderr": res["stderr"],
            "data": data}


def verify_capture(before_manifest, file_paths):
    """Re-hash files and compare against a previously captured manifest."""
    import vfp_safety
    return vfp_safety.verify_source_hashes(before_manifest, file_paths)


def run_convert(inp, ctype, out, cfg, prg, timeout=600):
    """Convert a single VFP binary file (BIN2PRG) to text."""
    result = _convert_one(inp, ctype, out, cfg, prg, timeout)
    emit(result["ok"], rc=result["rc"], stdout=result["stdout"],
         stderr=result["stderr"], data=result["data"])


def run_convert_dir(project, out, cfg, prg, timeout=600):
    """Scan a project directory for VFP binary files and convert each to text.

    v0.3 pipeline model: CONVERT → VERIFY CONVERSION MANIFEST → (caller indexes).
    The emitted JSON carries an explicit status:
      COMPLETE  — every file converted,
      PARTIAL   — some converted, some failed (callers MUST NOT treat this as a
                  complete audit; index is a PARTIAL index),
      FAILED    — nothing converted.
    """
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
                    "errorCode": res.get("errorCode"),
                    "stderr": res["stderr"][:500],
                })
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    failed_files = [r["file"] for r in results if not r["ok"]]
    converted_files = [r["file"] for r in results if r["ok"]]
    missing_companions = [r["file"] for r in results
                          if r.get("errorCode") == vfp_protocol.EC_MISSING_COMPANION]
    if fail_count == 0:
        status = vfp_protocol.STATUS_PASS  # COMPLETE
    elif ok_count == 0 and len(results) > 0:
        status = vfp_protocol.STATUS_FAIL  # FAILED
    else:
        status = vfp_protocol.STATUS_PARTIAL
    emit(fail_count == 0,
         status=status,
         errorCode=None if fail_count == 0 else "CONVERSION_PARTIAL",
         rc=0 if fail_count == 0 else 1,
         data={
             "status": status,
             "total": len(results),
             "ok": ok_count,
             "failed": fail_count,
             "convertedFiles": converted_files,
             "failedFiles": failed_files,
             "missingCompanions": missing_companions,
             "indexCompleteness": ("COMPLETE" if fail_count == 0 else
                                   ("NONE" if ok_count == 0 else "PARTIAL")),
             "results": results,
         },
         stdout="", stderr="")


def run_index(project, cache, full=False):
    """Build/refresh the symbol index from converted .sc2/.vc2 text."""
    sys.path.insert(0, HERE)
    try:
        import vfp_indexer
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_indexer: %s" % e)
    # If we reach here, emit() exited on failure
    data = vfp_indexer.run(project, cache, full=full)
    emit(True, status=vfp_protocol.STATUS_PASS, rc=0, data=data)


def run_sync(project, cache, full=False, timeout=600):
    """v0.3 sync pipeline: CONVERT → VERIFY CONVERSION MANIFEST → INDEX.

    The index is only built after the conversion manifest has been verified.
    If conversion has errors, the result is PARTIAL (or FAILED) and the index —
    when built — is explicitly a PARTIAL index (indexCompleteness=PARTIAL).
    Agents MUST NOT treat PARTIAL as a complete audit.
    """
    cfg_path = os.path.join(HERE, "FoxBin2Prg-AI.cfg")
    prg = vfp_common.foxbin2prg_program()
    if not os.path.isfile(prg):
        emit(False, status=vfp_protocol.STATUS_FAIL,
             errorCode="MISSING_TOOLING",
             stderr="foxbin2prg.prg not found at %s (set VFP_FOXBIN2PRG_DIR)" % prg)
    out_dir = os.path.join(cache, "source")

    # Phase 1: CONVERT (in-process; single JSON source of truth)
    conv = {"results": []}
    excl = vfp_common.default_excludes()
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d.lower() not in excl]
        for fn in sorted(files):
            ext = os.path.splitext(fn)[1].lower()
            if ext in BIN_WRITEABLE:
                fp = os.path.join(root, fn)
                res = _convert_one(fp, "BIN2PRG", out_dir, cfg_path, prg, timeout)
                conv["results"].append({
                    "file": os.path.relpath(fp, project),
                    "ok": res["ok"],
                    "rc": res["rc"],
                    "errorCode": res.get("errorCode"),
                    "stderr": res["stderr"][:500],
                })

    ok_count = sum(1 for r in conv["results"] if r["ok"])
    fail_count = len(conv["results"]) - ok_count
    converted_files = [r["file"] for r in conv["results"] if r["ok"]]
    failed_files = [r["file"] for r in conv["results"] if not r["ok"]]
    missing_companions = [r["file"] for r in conv["results"]
                          if r.get("errorCode") == vfp_protocol.EC_MISSING_COMPANION]

    # Phase 2: VERIFY CONVERSION MANIFEST
    if len(conv["results"]) > 0 and ok_count == 0:
        status = vfp_protocol.STATUS_FAIL
        index_completeness = "NONE"
    elif fail_count > 0:
        status = vfp_protocol.STATUS_PARTIAL
        index_completeness = "PARTIAL"
    else:
        status = vfp_protocol.STATUS_PASS
        index_completeness = "COMPLETE"

    # Phase 3: INDEX (only when there is at least one converted file).
    # A PARTIAL index is built explicitly as such — never presented as complete.
    index_result = None
    if ok_count > 0:
        index_result = run_index_internal(project, cache, full=full)

    payload = {
        "status": status,
        "convertedFiles": converted_files,
        "failedFiles": failed_files,
        "missingCompanions": missing_companions,
        "indexCompleteness": index_completeness,
        "total": len(conv["results"]),
        "ok": ok_count,
        "failed": fail_count,
        "results": conv["results"],
        "index": index_result,
    }
    ok = (status == vfp_protocol.STATUS_PASS)
    emit(ok, status=status,
         errorCode=None if ok else "CONVERSION_PARTIAL" if fail_count else "CONVERSION_FAILED",
         rc=0 if ok else 1, data=payload, stdout="", stderr="")


def run_index_internal(project, cache, full=False):
    """In-process index build (no emit). Returns dict or None."""
    sys.path.insert(0, HERE)
    try:
        import vfp_indexer
        return vfp_indexer.run(project, cache, full=full)
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        schema, schema_file, warnings = vfp_dbf_export.export_schema(input_path, out_dir)
        if schema:
            emit(True, status=vfp_protocol.STATUS_PASS, rc=0,
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
            emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
                 stderr="; ".join(warnings))
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
             stderr="dbf_schema failed: %s" % e)


def run_dbf_data(input_path, out_dir, fmt, deleted):
    """Export one DBF table record data to JSONL/CSV (no VFP9 needed)."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        count, data_file, warnings = vfp_dbf_export.export_data(input_path, out_dir, fmt, deleted)
        if data_file:
            emit(True, status=vfp_protocol.STATUS_PASS, rc=0,
                 table=os.path.splitext(os.path.basename(input_path))[0].upper(),
                 dataFile=data_file,
                 recordCount=count,
                 format=fmt,
                 warnings=warnings)
        else:
            emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
                 stderr="; ".join(warnings))
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
             stderr="dbf_data failed: %s" % e)


def run_dbf_list(dbf_dir):
    """List all DBF files in a directory tree."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        results = vfp_dbf_export.list_dbf(dbf_dir)
        emit(True, status=vfp_protocol.STATUS_PASS, rc=0,
             data={"tables": results, "count": len(results)})
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
             stderr="dbf_list failed: %s" % e)


def run_dbf_dir(source, out, formats, deleted):
    """Batch-export a whole directory tree of DBF files (dbfbridge)."""
    sys.path.insert(0, HERE)
    try:
        import vfp_dbf_export
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_dbf_export: %s" % e)
    try:
        run, warnings = vfp_dbf_export._dbfbridge_export_dir(source, out, tuple(formats), deleted)
        emit(run.failed == 0,
             status=vfp_protocol.STATUS_PASS if run.failed == 0 else vfp_protocol.STATUS_PARTIAL,
             errorCode=None if run.failed == 0 else "EXPORT_FAILED",
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
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="EXPORT_FAILED",
             stderr="dbf_dir batch export failed: %s" % e)


def run_cdx_info(dbf, cdx=None, timeout=120):
    """Describe one table's index structure (.cdx/.idx) + index expressions.

    Structural parsing is pure Python (no VFP9). When VFP9 is available,
    tag expressions are read via the read-only COM host.
    """
    sys.path.insert(0, HERE)
    try:
        import vfp_cdx
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_cdx: %s" % e)
    if not os.path.isfile(dbf):
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="MISSING_FILE",
             stderr="dbf not found: " + dbf)
    try:
        info = vfp_cdx.build_index_info(dbf, cdx_path=cdx, timeout=timeout)
        emit(True, status=vfp_protocol.STATUS_PASS, rc=0, data=info, stdout="", stderr="")
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="CDX_ANALYSIS_FAILED",
             stderr="cdx_info failed: %s" % e)


def run_cdx_scan(source_dir, timeout=120):
    """Scan a project tree for .cdx/.idx files and structurally parse each."""
    sys.path.insert(0, HERE)
    try:
        import vfp_cdx
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_cdx: %s" % e)
    try:
        results = vfp_cdx.parse_dir(source_dir)
        ok_count = sum(1 for r in results if r.get("ok"))
        emit(ok_count > 0,
             status=vfp_protocol.STATUS_PASS if ok_count > 0 else vfp_protocol.STATUS_PARTIAL,
             errorCode=None if ok_count > 0 else "NO_INDEXES_PARSED",
             rc=0 if ok_count else 1,
             data={"total": len(results), "parsed": ok_count, "results": results},
             stdout="", stderr="")
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="CDX_ANALYSIS_FAILED",
             stderr="cdx_scan failed: %s" % e)


def run_audit(source, out, skip_sync, include_data, data_formats,
              max_tables=0, dbf_exclude="", no_cache_scan=False,
              include_forms=True, no_validate=False, only_tables=""):
    """Run the comprehensive VFP project audit.

    include_data defaults to True (ON BY DEFAULT — same as vfp_audit.py,
    tools/vfp.ts, README, docs/USAGE.md). Opt out with --no-include-data.
    """
    sys.path.insert(0, HERE)
    try:
        import vfp_audit
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="INTERNAL_ERROR",
             stderr="cannot import vfp_audit: %s" % e)
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
            no_validate=no_validate,
            only_tables=tuple(x for x in only_tables.split(",") if x),
        )
        result = auditor.run()
        emit(True, status=vfp_protocol.STATUS_PASS, rc=0, auditDir=result["auditDir"],
             dataExport=result.get("dataExport"),
             formsExport=result.get("formsExport"), summary=result["summary"])
    except Exception as e:
        emit(False, status=vfp_protocol.STATUS_FAIL, errorCode="AUDIT_FAILED",
             stderr="audit failed: %s" % e)


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

    pcdi = sub.add_parser("cdx_info", help="Describe one table's index structure (.cdx/.idx) + tag expressions")
    pcdi.add_argument("--dbf", required=True, help="Path to the .dbf file")
    pcdi.add_argument("--cdx", default=None, help="Explicit .cdx/.idx (default: <dbf stem>.cdx)")
    pcdi.add_argument("--timeout", type=int, default=120, help="COM enrichment timeout (s)")

    pcds = sub.add_parser("cdx_scan", help="Scan a directory tree for .cdx/.idx files and parse each (no VFP9 needed)")
    pcds.add_argument("--dir", required=True, help="Directory to scan")

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
    pa.add_argument("--no-include-data", dest="include_data", action="store_false", default=True,
                    help="Skip the full DBF record data export (ON BY DEFAULT; "
                         "set this flag for a fast schema-only audit)")
    pa.add_argument("--data-formats", default="jsonl", help="Comma-separated data export formats: jsonl,csv,json,xlsx")
    pa.add_argument("--max-tables", type=int, default=0, help="With include-data: limit to N largest tables (0=all)")
    pa.add_argument("--dbf-exclude", default="", help="Comma-separated uppercase substrings to exclude from DBF scan")
    pa.add_argument("--only-tables", default="", help="Only process DBF tables whose path contains one of these uppercase substrings (comma-separated, e.g. 'ARCH,TMP')")
    pa.add_argument("--no-cache-scan", action="store_true", help="Do not scan .vfp-ai/source for table usage")
    pa.add_argument("--no-include-forms", dest="include_forms", action="store_false", default=True,
                    help="Skip exporting full form/class code (on by default)")
    pa.add_argument("--no-validate", action="store_true",
                    help="Export DBF data with validate=False (use when validate=True fails)")

    ps = sub.add_parser("snapshot",
                        help="Source manifest: path/size/mtime/sha256/fileType/companions for all VFP files (READ-ONLY)")
    ps.add_argument("--source", required=True, help="VFP project root directory")
    ps.add_argument("--out", required=True,
                    help="Directory to receive source_manifest.json (MUST be outside the source; never the source itself)")

    psyn = sub.add_parser("sync",
                          help="v0.3 pipeline: CONVERT -> VERIFY CONVERSION MANIFEST -> INDEX (status COMPLETE|PARTIAL|FAILED)")
    psyn.add_argument("--project", required=True, help="VFP project root")
    psyn.add_argument("--cache", required=True, help="Cache directory (.vfp-ai)")
    psyn.add_argument("--full", action="store_true", help="Re-parse all .sc2/.vc2 files for symbols")
    psyn.add_argument("--timeout", type=int, default=600)

    penv = sub.add_parser("env",
                          help="VFP9 environment/language inventory (VERSION, SYS(3099), CPCURRENT, ALANGUAGE) via COM")
    penv.add_argument("--out", required=True,
                      help="Directory to receive vfp_environment.json (workspace or audit dir — never the source)")

    pws = sub.add_parser("refactor_workspace",
                         help="Create an isolated refactor workspace: verify source, SHA256 SCX/SCT, copy to workspace, workspace_manifest.json (WRITES ONLY TO WORKSPACE)")
    pws.add_argument("--source-form", required=True, help="Full path to the source .scx")
    pws.add_argument("--workspace", required=True,
                     help="Workspace directory (MUST differ from the source project)")

    ppatch = sub.add_parser("apply_form_patch",
                            help="Apply a RefactorPlan (method-only) to the WORKSPACE COPY via VFP9 COM (WRITES ONLY TO REFACTOR WORKSPACE — NEVER SOURCE)")
    ppatch.add_argument("--plan", required=True, help="Path to refactor_plan.json")
    ppatch.add_argument("--workspace", required=True, help="Workspace root (contains working/ and final/)")
    ppatch.add_argument("--timeout", type=int, default=300)

    pcomp = sub.add_parser("compile_form",
                           help="COMPILE FORM of the workspace copy via VFP9; .ERR only in the workspace (WRITES ONLY TO REFACTOR WORKSPACE — NEVER SOURCE)")
    pcomp.add_argument("--workspace", required=True, help="Workspace root (contains working/)")
    pcomp.add_argument("--form", required=True, help="Base name (no ext) of the form in working/")
    pcomp.add_argument("--timeout", type=int, default=300)

    ptrip = sub.add_parser("roundtrip_form",
                           help="FINAL SCX/SCT -> BIN2PRG -> FINAL SC2 into workspace/validation/")
    ptrip.add_argument("--workspace", required=True, help="Workspace root")
    ptrip.add_argument("--form", required=True, help="Base name (no ext) of the form")
    ptrip.add_argument("--stage", default="working", choices=["working", "final"],
                       help="Which stage to roundtrip (default: working)")
    ptrip.add_argument("--timeout", type=int, default=600)

    pfinv = sub.add_parser("form_inventory",
                           help="Structural snapshot of a form (objects, geometry, stable properties) from its SC2")
    pfinv.add_argument("--sc2", required=True, help="Path to the .sc2 file")
    pfinv.add_argument("--out", default=None, help="Optional path to write <name>_form_inventory.json")

    pcmpf = sub.add_parser("compare_forms",
                           help="Compare source vs final form inventories; UNEXPECTED change = FAIL (method-only refactor)")
    pcmpf.add_argument("--source-inventory", required=True, help="Path to source_form_inventory.json")
    pcmpf.add_argument("--final-inventory", required=True, help="Path to final_form_inventory.json")
    pcmpf.add_argument("--plan", default=None, help="Optional refactor_plan.json (expected method changes)")

    pstv = sub.add_parser("static_validate",
                          help="Static validation of SC2/method code (artifacts, duplicates, END* balance, growth)")
    pstv.add_argument("--sc2", required=True, help="Path to the .sc2 file to validate")
    pstv.add_argument("--baseline-sc2", default=None,
                      help="Optional baseline .sc2 for suspicious code-growth comparison")

    pval = sub.add_parser("validate_form",
                          help="One-command validation state machine -> PASS_VERIFIED or FAIL (+ validation_report.json/.md)")
    pval.add_argument("--workspace", required=True, help="Workspace root")
    pval.add_argument("--form", required=True, help="Base name (no ext) of the form")
    pval.add_argument("--source-form", required=True, help="Source .scx path (for SHA verification)")
    pval.add_argument("--timeout", type=int, default=300)

    a = ap.parse_args()
    if a.cmd == "verno":
        run_verno(a.prg)
    elif a.cmd == "convert":
        run_convert(a.input, a.type, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "convert_dir":
        run_convert_dir(a.project, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "index":
        run_index(a.project, a.cache, a.full)
    elif a.cmd == "sync":
        run_sync(a.project, a.cache, a.full, a.timeout)
    elif a.cmd == "dbf_schema":
        run_dbf_schema(a.input, a.out)
    elif a.cmd == "dbf_data":
        run_dbf_data(a.input, a.out, a.format, a.deleted)
    elif a.cmd == "dbf_list":
        run_dbf_list(a.dir)
    elif a.cmd == "cdx_info":
        run_cdx_info(a.dbf, a.cdx, a.timeout)
    elif a.cmd == "cdx_scan":
        run_cdx_scan(a.dir)
    elif a.cmd == "dbf_dir":
        run_dbf_dir(a.source, a.out, a.formats, a.deleted)
    elif a.cmd == "audit":
        run_audit(a.source, a.out, a.skip_sync, a.include_data, a.data_formats,
                  a.max_tables, a.dbf_exclude, a.no_cache_scan,
                  include_forms=a.include_forms, no_validate=a.no_validate,
                  only_tables=a.only_tables)
    elif a.cmd == "snapshot":
        _dispatch_snapshot(a)
    elif a.cmd == "env":
        _dispatch_env(a)
    elif a.cmd == "refactor_workspace":
        _dispatch_refactor(a, "workspace")
    elif a.cmd == "apply_form_patch":
        _dispatch_refactor(a, "patch")
    elif a.cmd == "compile_form":
        _dispatch_refactor(a, "compile")
    elif a.cmd == "roundtrip_form":
        _dispatch_refactor(a, "roundtrip")
    elif a.cmd == "form_inventory":
        _dispatch_refactor(a, "inventory")
    elif a.cmd == "compare_forms":
        _dispatch_refactor(a, "compare")
    elif a.cmd == "static_validate":
        _dispatch_refactor(a, "static")
    elif a.cmd == "validate_form":
        _dispatch_refactor(a, "validate")


def _dispatch_snapshot(args):
    import vfp_refactor
    vfp_refactor.cmd_snapshot(args, emit=emit, vfp_protocol=vfp_protocol)


def _dispatch_env(args):
    import vfp_refactor
    vfp_refactor.cmd_env(args, emit=emit, cscript_path=cscript_path,
                         run_process=_run_process, vfp_protocol=vfp_protocol,
                         here=HERE, timeout=120)


def _dispatch_refactor(args, which):
    import vfp_refactor
    if which == "workspace":
        vfp_refactor.cmd_workspace(args, emit=emit)
    elif which == "patch":
        vfp_refactor.cmd_patch(args, emit=emit, cscript_path=cscript_path,
                               run_process=_run_process, here=HERE,
                               timeout=args.timeout)
    elif which == "compile":
        vfp_refactor.cmd_compile(args, emit=emit, cscript_path=cscript_path,
                                 run_process=_run_process, here=HERE,
                                 timeout=args.timeout)
    elif which == "roundtrip":
        vfp_refactor.cmd_roundtrip(args, emit=emit, cscript_path=cscript_path,
                                   run_process=_run_process, here=HERE,
                                   timeout=args.timeout)
    elif which == "inventory":
        vfp_refactor.cmd_inventory(args, emit=emit)
    elif which == "compare":
        vfp_refactor.cmd_compare(args, emit=emit)
    elif which == "static":
        vfp_refactor.cmd_static(args, emit=emit)
    elif which == "validate":
        vfp_refactor.cmd_validate(args, emit=emit, cscript_path=cscript_path,
                                  run_process=_run_process, here=HERE,
                                  timeout=args.timeout)


if __name__ == "__main__":
    main()
