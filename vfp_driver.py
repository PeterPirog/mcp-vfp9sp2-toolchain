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
import re
import subprocess
import sys
import time

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
    # Run with a scratch cwd so any VFP9 side-effect (e.g. .ERR / .fpt) is
    # written next to the OUTPUT dir, never into the source project.
    run_cwd = out or os.path.dirname(os.path.abspath(inp)) or None
    res = _run_process(args, timeout, cwd=run_cwd)
    rc = _parse_rc(res["stdout"])
    # Surface a missing companion file (e.g. .sct/.fpt) as an explicit reason —
    # FoxBin2Prg returns rc=41 "missing companion" with an empty stderr, which
    # used to be confusing (real-run report #1/#6).
    missing = vfp_common.missing_companions(inp)
    if rc == 41 and missing:
        res["stderr"] = ("missing companion file(s) required by FoxBin2Prg: "
                         + ", ".join(os.path.basename(m) for m in missing))
    return {"ok": rc == 0, "rc": rc, "stdout": res["stdout"], "stderr": res["stderr"],
            "data": {"input": inp, "type": ctype, "out": out,
                     "missingCompanions": [os.path.relpath(m, os.path.dirname(inp)) for m in missing]}}


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
    # Exit code reflects the outcome: 0 only when nothing failed. A partial
    # batch (some ok, some failed) previously exited 0 (ok=True) while the JSON
    # said rc=1 — hard to distinguish from a shell. Now any failure -> exit 2.
    emit(fail_count == 0,
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


def run_cdx_info(dbf, cdx=None, timeout=120):
    """Describe one table's index structure (.cdx/.idx) + index expressions.

    Structural parsing is pure Python (no VFP9). When VFP9 is available,
    tag expressions are read via the read-only COM host.
    """
    sys.path.insert(0, HERE)
    try:
        import vfp_cdx
    except Exception as e:
        emit(False, stderr="cannot import vfp_cdx: %s" % e)
    if not os.path.isfile(dbf):
        emit(False, stderr="dbf not found: " + dbf)
    try:
        info = vfp_cdx.build_index_info(dbf, cdx_path=cdx, timeout=timeout)
        emit(True, rc=0, data=info, stdout="", stderr="")
    except Exception as e:
        emit(False, stderr="cdx_info failed: %s" % e)


def run_cdx_scan(source_dir, timeout=120):
    """Scan a project tree for .cdx/.idx files and structurally parse each."""
    sys.path.insert(0, HERE)
    try:
        import vfp_cdx
    except Exception as e:
        emit(False, stderr="cannot import vfp_cdx: %s" % e)
    try:
        results = vfp_cdx.parse_dir(source_dir)
        ok_count = sum(1 for r in results if r.get("ok"))
        emit(ok_count > 0, rc=0 if ok_count else 1,
             data={"total": len(results), "parsed": ok_count, "results": results},
             stdout="", stderr="")
    except Exception as e:
        emit(False, stderr="cdx_scan failed: %s" % e)


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


# ---------------------------------------------------------------------------
# run_prg — execute a .prg file in VFP9
# ---------------------------------------------------------------------------

def _vfp9_exe():
    """Resolve the VFP9 executable path from config.json or env.

    Precedence:
      1. VFP9_EXE environment variable
      2. config.json -> vfp.exeEnvironmentVariable (value of that env var)
      3. config.json -> vfp.exeDefault
    Returns the path string (even if not found — caller must check with os.path.isfile).
    """
    cfg = vfp_common._load_config() or {}
    v = cfg.get("vfp") or {}
    env_name = v.get("exeEnvironmentVariable", "VFP9_EXE")
    exe = os.environ.get(env_name)
    if not exe:
        exe = v.get("exeDefault") or os.path.join(
            "C:\\Program Files (x86)", "Microsoft Visual FoxPro 9", "vfp9.exe")
    return exe


def run_run_prg(prg_path, workdir=None, timeout=120):
    """Run a .prg file in VFP9 via command line.

    Uses: vfp9.exe /C <prg_path> with cwd=workdir.
    Captures stdout/stderr and any .ERR file content.
    Returns JSON: {ok, rc, stdout, stderr, errFile, durationMs}
    """
    prg_path = os.path.abspath(prg_path)
    if not os.path.isfile(prg_path):
        emit(False, stderr="prg file not found: " + prg_path)

    vfp9 = _vfp9_exe()
    if not os.path.isfile(vfp9):
        emit(False, stderr="vfp9.exe not found at: " + vfp9 +
               " (set VFP9_EXE environment variable)")

    if workdir is None:
        workdir = os.path.dirname(prg_path)

    prg_name = os.path.basename(prg_path)
    stem = os.path.splitext(prg_name)[0]
    cmd = [vfp9, "/C", prg_path]

    # Remove a stale .ERR from a previous run so the report reflects THIS run.
    for base_dir in (os.path.dirname(prg_path), workdir):
        if not base_dir:
            continue
        stale = os.path.join(base_dir, stem + ".ERR")
        if os.path.isfile(stale):
            try:
                os.remove(stale)
            except OSError:
                pass

    t0 = time.time()
    res = _run_process(cmd, timeout, cwd=workdir)
    duration_ms = int((time.time() - t0) * 1000)
    hung = res["code"] == -1  # timeout / killed

    # VFP9 /C writes <prg stem>.ERR into its working directory on any compile
    # or run error. In the hang case stdout is empty, so .ERR is the ONLY place
    # the real error lives — surface it into stderr and data.errContent.
    err_file = None
    err_content = ""
    for base_dir in (os.path.dirname(prg_path), workdir):
        if not base_dir:
            continue
        candidate = os.path.join(base_dir, stem + ".ERR")
        if os.path.isfile(candidate):
            err_file = candidate
            try:
                with open(candidate, "r", encoding="cp1252", errors="replace") as f:
                    err_content = f.read().strip()
            except OSError:
                err_content = ""
            break
    if err_content:
        res["stderr"] = (res["stderr"] + "\n" + err_content).strip()

    emit(res["code"] == 0 and not err_content, rc=res["code"],
         stdout=res["stdout"], stderr=res["stderr"],
         data={"prg": prg_path, "workdir": workdir,
               "errFile": err_file, "errContent": err_content,
               "vfpError": bool(err_content),
               "hung": hung, "durationMs": duration_ms})


def run_benchmark(project, table, operation, expression="", field="",
                  tag="", iterations=10, out_file=None, timeout=300):
    """Benchmark a DBF operation in VFP9.

    Generates a temporary .prg that:
    1. Opens the table from <project>/Dane/
    2. Runs the operation N times with SECONDS() timing
    3. Checks SYS(3054) for Rushmore status
    4. Writes results to a text file

    Operations: calculate_max, calculate_for, seek, scan, count_for, sum, set_filter_goto
    """
    project = os.path.abspath(project)
    dane_dir = os.path.join(project, "Dane")
    if not os.path.isdir(dane_dir):
        emit(False, stderr="Dane directory not found: " + dane_dir)

    # Generate benchmark PRG
    bench_dir = os.path.join(project, ".vfp-ai", "benchmarks") if os.path.isdir(
        os.path.join(project, ".vfp-ai")) else os.path.join(project, "benchmarks")
    os.makedirs(bench_dir, exist_ok=True)

    prg_path = os.path.join(bench_dir, "benchmark_temp.prg")
    results_path = os.path.join(bench_dir, "benchmark_results.txt")

    # Build the operation body
    ops = {
        "calculate_max": 'CALCULATE MAX({field}) TO lnResult FOR ({expr})',
        "calculate_for": 'CALCULATE MAX({field}) TO lnResult FOR ({expr})',
        "seek": 'SEEK {expr} TAG {tag}',
        "scan": 'DO WHILE .F.\n  SCAN FOR ({expr})\n  DO WHILE .NOT. EOF()\n    SKIP\n  ENDDO\n  SEEK -9E999\nENDDO',
        "count_for": 'COUNT TO lnCount FOR ({expr})',
        "sum": 'SUM {field} TO lnResult FOR ({expr})',
        "set_filter_goto": 'SET FILTER TO ({expr})\nGO TOP\nSET FILTER TO',
    }

    op_template = ops.get(operation, '')
    if not op_template:
        emit(False, stderr="unknown operation: " + operation)

    field_val = field or "1"
    expr_val = expression or ".T."
    tag_val = tag or "TAG1"

    # For simpler operations, build a clean loop
    op_lines = []
    if operation in ("calculate_max", "calculate_for", "sum"):
        if operation == "calculate_for" and expr_val:
            op_lines.append('   CALCULATE MAX({f}) TO lnVal FOR ({e})'.format(f=field_val, e=expr_val))
        else:
            op_lines.append('   CALCULATE MAX({f}) TO lnVal'.format(f=field_val))
    elif operation == "seek":
        op_lines.append('   SEEK {e} TAG {t}'.format(e=expr_val, t=tag_val))
    elif operation == "scan":
        if expr_val:
            op_lines.append('   SCAN FOR ({e})'.format(e=expr_val))
        else:
            op_lines.append('   SCAN')
        op_lines.append('   DO WHILE .NOT. EOF()')
        op_lines.append('     SKIP')
        op_lines.append('   ENDDO')
    elif operation == "count_for":
        if expr_val:
            op_lines.append('   COUNT TO lnCt FOR ({e})'.format(e=expr_val))
        else:
            op_lines.append('   COUNT TO lnCt')
    elif operation == "set_filter_goto":
        if expr_val:
            op_lines.append('   SET FILTER TO ({e})'.format(e=expr_val))
        else:
            op_lines.append('   SET FILTER TO .T.')
        op_lines.append('   GO TOP')
        op_lines.append('   SET FILTER TO')

    # Rushmore check: only when an expression is provided
    if expr_val:
        rushmore_line = (
            'lnRushmore = SYS(3054, 1, "{expr}")'.format(expr=expr_val)
        )
    else:
        rushmore_line = '* no expression provided - Rushmore check skipped'

    prg_body = """\
SET DEFAULT TO '{dane}'
SET TALK OFF

LOCAL lnStart, lnEnd, lnCt, lnResult, lnRushmore
lnRushmore = 0
USE {table} IN 0 SHARED
IF _VFP.Error <> 0
  STRTOFILE("OPEN_ERR " + ALLTRIM(TRANSFORM(_VFP.Errno)) + " " + ALLTRIM(_VFP.Message), '{results}')
  QUIT
ENDIF
{rushmore_line}

LOCAL aTimes[100]
LOCAL nIter
nIter = {iter}

* Warmup
lnStart = SECONDS()
{op_body_warmup}
lnEnd = SECONDS()
aTimes[1] = (lnEnd - lnStart) * 1000

LOCAL i, lnMin, lnMax, lnSum
lnMin = 999999
lnMax = 0
lnSum = 0
FOR i = 2 TO nIter
  lnStart = SECONDS()
  {op_body}
  lnEnd = SECONDS()
  aTimes[i] = (lnEnd - lnStart) * 1000
  IF aTimes[i] < lnMin
    lnMin = aTimes[i]
  ENDIF
  IF aTimes[i] > lnMax
    lnMax = aTimes[i]
  ENDIF
  lnSum = lnSum + aTimes[i]
ENDFOR

* Write results (line by line, top-level STRTOFILE)
STRTOFILE("COLD_MS=" + TRANSFORM(aTimes[1], "1:4"), '{results}')
STRTOFILE("WARM_MS=" + TRANSFORM(aTimes[nIter], "1:4"), '{results}', 'C')
STRTOFILE("AVG_MS=" + TRANSFORM(lnSum / (nIter - 1), "1:4"), '{results}', 'C')
STRTOFILE("MIN_MS=" + TRANSFORM(lnMin, "1:4"), '{results}', 'C')
STRTOFILE("MAX_MS=" + TRANSFORM(lnMax, "1:4"), '{results}', 'C')
STRTOFILE("RUSHMORE=" + TRANSFORM(lnRushmore), '{results}', 'C')
STRTOFILE("ITERATIONS=" + TRANSFORM(nIter), '{results}', 'C')
    STRTOFILE("BENCH_DONE", '{results}', 'C')
    
    USE
    QUIT
    """.format(
    dane=dane_dir.replace("\\", "\\\\"),
    table=table,
    rushmore_line=rushmore_line,
    iter=iterations,
    op_body_warmup="\n".join("  " + l for l in op_lines) or "  * warmup",
    op_body="\n".join("  " + l for l in op_lines) or "  * noop",
    results=results_path.replace("\\", "\\\\"),
)

    with open(prg_path, "w", encoding="cp1252") as f:
        f.write(prg_body)

    # Start clean: remove stale results/.ERR from a previous run
    for stale in (results_path, os.path.join(bench_dir, "benchmark_temp.ERR"),
                  os.path.join(dane_dir, "benchmark_temp.ERR")):
        try:
            if os.path.isfile(stale):
                os.remove(stale)
        except OSError:
            pass

    vfp9 = _vfp9_exe()
    if not os.path.isfile(vfp9):
        emit(False, stderr="vfp9.exe not found at: " + vfp9 +
               " (set VFP9_EXE environment variable)")

    cmd = [vfp9, "/C", prg_path]
    t0 = time.time()
    res = _run_process(cmd, timeout, cwd=dane_dir)
    duration_ms = int((time.time() - t0) * 1000)

    # .ERR (if any) is written to the working dir — read the real error
    bench_err_content = ""
    for base_dir in (dane_dir, bench_dir, os.path.dirname(prg_path)):
        candidate = os.path.join(base_dir, "benchmark_temp.ERR")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="cp1252", errors="replace") as f:
                    bench_err_content = f.read().strip()
            except OSError:
                bench_err_content = ""
            break

    # Parse results
    data = {
        "operation": operation,
        "table": table,
        "iterations": iterations,
        "coldMs": None,
        "warmMs": None,
        "avgMs": None,
        "minMs": None,
        "maxMs": None,
        "rushmore": None,
        "sys3054": None,
        "durationMs": duration_ms,
        "prg": prg_path,
    }
    if bench_err_content:
        data["vfpError"] = bench_err_content

    if os.path.isfile(results_path):
        with open(results_path, "r", encoding="cp1252", errors="replace") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    try:
                        if key == "COLD_MS":
                            data["coldMs"] = float(val)
                        elif key == "WARM_MS":
                            data["warmMs"] = float(val)
                        elif key == "AVG_MS":
                            data["avgMs"] = float(val)
                        elif key == "MIN_MS":
                            data["minMs"] = float(val)
                        elif key == "MAX_MS":
                            data["maxMs"] = float(val)
                        elif key == "RUSHMORE":
                            r = int(val)
                            data["rushmore"] = {1: "FULL", 0: "PARTIAL", -1: "NONE"}.get(r, str(r))
                            data["sys3054"] = str(r)
                    except ValueError:
                        pass
        os.remove(results_path)

    emit(res["code"] == 0 and data.get("coldMs") is not None,
         rc=res["code"],
         stdout=res["stdout"][:500], stderr=res["stderr"][:500],
         data=data)


def run_form_perf(form_sc2, tables_dir, out_file=None):
    """Build a performance access map for a form.

    Parses the .sc2 file and for each PROCEDURE finds:
    - SEEK, SCAN FOR, CALCULATE FOR, COUNT FOR, SUM FOR, LOCATE FOR
    - SET FILTER TO, DELETE ALL FOR, REPLACE FOR
    - Identifies the table from context (SELECT alias)
    - Cross-references with CDX tags
    - Marks Rushmore status: FULL/PARTIAL/NONE
    - Suggests missing indexes
    """
    form_sc2 = os.path.abspath(form_sc2)
    if not os.path.isfile(form_sc2):
        emit(False, stderr="form file not found: " + form_sc2)

    tables_dir = os.path.abspath(tables_dir)
    if not os.path.isdir(tables_dir):
        emit(False, stderr="tables dir not found: " + tables_dir)

    with open(form_sc2, "r", encoding="cp1252", errors="replace") as f:
        content = f.read()

    # Functions that block Rushmore optimization
    BLOCKING_FUNCS = ("LEFT", "RIGHT", "ALLTRIM", "UPPER", "LOWER",
                      "SUBSTR", "TRANSFORM", "STR", "DTOC", "DTOF", "VAL")

    # Regex patterns for data access operations
    op_patterns = [
        (r'\bSEEK\s+(.+?)\s+TAG\s+(\w+)', "SEEK"),
        (r'\bSCAN\s+FOR\s+(.+)', "SCAN_FOR"),
        (r'^\s*SCAN\s*$', "SCAN"),
        (r'\bCALCULATE\s+[\w\s]+\s+(?:TO\s+\w+\s+)?FOR\s+(.+)', "CALCULATE_FOR"),
        (r'\bCOUNT\s+TO\s+\w+\s+FOR\s+(.+)', "COUNT_FOR"),
        (r'\bSUM\s+(\w+)\s+(?:TO\s+\w+\s+)?FOR\s+(.+)', "SUM_FOR"),
        (r'\bLOCATE\s+FOR\s+(.+)', "LOCATE_FOR"),
        (r'\bSET\s+FILTER\s+TO\s+(.+)', "SET_FILTER"),
        (r'\bDELETE\s+ALL\s+FOR\s+(.+)', "DELETE_ALL_FOR"),
        (r'\bREPLACE\s+(?:\*|[\w\s]+)\s+FOR\s+(.+)', "REPLACE_FOR"),
    ]

    # Find PROCEDURE blocks
    proc_re = re.compile(r'\bPROCEDURE\s+(\w+)', re.IGNORECASE)
    endproc_re = re.compile(r'\bENDPROC', re.IGNORECASE)

    procedures = []
    lines = content.splitlines()
    i = 0
    current_proc = None
    proc_start = 0
    while i < len(lines):
        m = proc_re.match(lines[i].strip())
        if m:
            if current_proc:
                procedures.append((current_proc, proc_start, i))
            current_proc = m.group(1)
            proc_start = i
        elif endproc_re.match(lines[i].strip()) and current_proc:
            procedures.append((current_proc, proc_start, i))
            current_proc = None
        i += 1
    if current_proc:
        procedures.append((current_proc, proc_start, len(lines)))

    # Find all SELECT alias statements for context
    select_re = re.compile(r'\bSELECT\s+(\w+)\s+INTO\s+CURSOR|\bSELECT\s+.*?\s+FROM\s+(\w+)', re.IGNORECASE)
    select_alias_re = re.compile(r'\bSELECT\s+(\w+)\s+', re.IGNORECASE)

    # Build access map
    access_map = []
    for proc_name, start_line, end_line in procedures:
        proc_text = "\n".join(lines[start_line:end_line])

        # Track SELECT context
        current_table = None
        for pattern, op_name in op_patterns:
            for m in re.finditer(pattern, proc_text, re.IGNORECASE | re.MULTILINE):
                # Extract the FOR expression (last group that is an expression)
                groups = [g for g in m.groups() if g and not g.startswith("TAG")]
                for_expr = ""
                tag_name = None

                if op_name == "SEEK":
                    tag_name = m.group(2) if len(m.groups()) >= 2 else None
                    for_expr = m.group(1) if m.group(1) else ""
                elif op_name == "SUM_FOR":
                    for_expr = (m.group(2) or "")
                elif m.groups():
                    for_expr = m.group(1) or ""
                else:
                    for_expr = ""

                # Try to identify table
                table_name = current_table
                # Check if there's a SELECT before this in the procedure
                for sm in re.finditer(r'\bSELECT\s+(\w+)', proc_text[:m.start()], re.IGNORECASE):
                    table_name = sm.group(1)

                # Analyze Rushmore
                rushmore = "NONE"
                reason = "no matching tag found"
                suggested = None

                if for_expr and table_name:
                    # Extract field names from the FOR expression
                    fields = re.findall(r'\b([a-z_]\w{1,30})\b', for_expr.lower())
                    fields = [f for f in fields if f not in
                              ("and", "or", "not", "in", "is", "null", "between",
                               "like", "the", "to", "for", "all", "true", "false")]

                    # Check if expression uses blocking functions
                    upper_expr = for_expr.upper()
                    has_blocking = any(" ".join(f + "(") in upper_expr or
                                      f + "(" in upper_expr.replace(" ", "")
                                      for f in BLOCKING_FUNCS)

                    # Try to load CDX for this table
                    cdx_file = os.path.join(tables_dir, table_name + ".CDX")
                    if os.path.isfile(cdx_file):
                        try:
                            import vfp_cdx
                            cdx_info = vfp_cdx.parse_cdx(cdx_file)
                            if cdx_info.get("ok"):
                                tags = cdx_info.get("tags", [])
                                tag_names = [t["tag"].upper() for t in tags]
                                if tag_names:
                                    if not has_blocking:
                                        rushmore = "FULL"
                                        reason = "exact field match with tag"
                                    else:
                                        rushmore = "PARTIAL"
                                        reason = "expression uses function that blocks Rushmore"
                                        suggested = "INDEX ON %s TAG %s" % (
                                            for_expr, table_name + "_" + op_name.lower())
                                else:
                                    rushmore = "NONE"
                                    reason = "no tags found in CDX"
                                    suggested = "INDEX ON %s TAG %s" % (
                                        fields[0] if fields else for_expr, table_name + "_idx")
                            else:
                                rushmore = "NONE"
                                reason = "CDX parse failed"
                        except Exception:
                            pass

                entry = {
                    "procedure": proc_name,
                    "operation": op_name,
                    "expression": for_expr[:200],
                    "table": table_name,
                    "tag": tag_name,
                    "rushmore": rushmore,
                    "reason": reason,
                    "line": start_line + 1,
                }
                if suggested:
                    entry["suggestedIndex"] = suggested
                access_map.append(entry)

    result = {
        "form": os.path.splitext(os.path.basename(form_sc2))[0],
        "totalOperations": len(access_map),
        "accessMap": access_map,
    }

    if out_file:
        out_file = os.path.abspath(out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["outputFile"] = out_file

    emit(True, rc=0, data=result)


def run_count_patterns(project, patterns_str, out_file=None):
    """Count pattern occurrences across all .sc2 files in project cache.

    Patterns: comma-separated regex patterns.
    Scans .vfp-ai cache or Audit_output/forms for .sc2 files.
    Returns per-form counts + totals + top forms.
    """
    project = os.path.abspath(project)
    patterns = [p.strip() for p in patterns_str.split(",") if p.strip()]
    if not patterns:
        emit(False, stderr="no patterns specified")

    # Find .sc2 files
    sc2_files = []
    cache_dirs = [
        os.path.join(project, ".vfp-ai"),
        os.path.join(project, ".vfp-ai", "source"),
        os.path.join(project, "Audit_output", "forms"),
        os.path.join(project, "audit_report", "forms"),
    ]

    for cdir in cache_dirs:
        if not os.path.isdir(cdir):
            continue
        for root, dirs, files in os.walk(cdir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if fn.lower().endswith((".sc2", ".vc2", ".fr2")):
                    sc2_files.append(os.path.join(root, fn))

    if not sc2_files:
        # Fallback: scan project for .sc2 directly
        excl = vfp_common.default_excludes()
        for root, dirs, files in os.walk(project):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in excl]
            for fn in files:
                if fn.lower().endswith((".sc2", ".vc2", ".fr2")):
                    sc2_files.append(os.path.join(root, fn))

    # Compile patterns
    compiled = []
    for pat in patterns:
        try:
            compiled.append((pat, re.compile(pat, re.IGNORECASE)))
        except re.error:
            compiled.append((pat, re.compile(re.escape(pat), re.IGNORECASE)))

    # Count per file
    per_form = {}
    for fp in sc2_files:
        form_name = os.path.splitext(os.path.basename(fp))[0]
        try:
            with open(fp, "r", encoding="cp1252", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        counts = {}
        for pat, rx in compiled:
            n = len(rx.findall(text))
            if n > 0:
                counts[pat] = n
        if counts:
            per_form[form_name] = counts

    # Aggregate
    pattern_results = {}
    for pat, _ in compiled:
        total = sum(fc.get(pat, 0) for fc in per_form.values())
        top_forms = sorted(
            [(fn, fc[pat]) for fn, fc in per_form.items() if pat in fc],
            key=lambda x: -x[1])[:5]
        pattern_results[pat] = {
            "total": total,
            "topForms": [{"form": fn, "count": cnt} for fn, cnt in top_forms],
        }

    result = {
        "project": project,
        "totalForms": len(sc2_files),
        "formsWithMatches": len(per_form),
        "patterns": pattern_results,
    }

    if out_file:
        out_file = os.path.abspath(out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["outputFile"] = out_file

    emit(True, rc=0, data=result)


def run_find_duplicates(form_sc2, min_lines=10, out_file=None):
    """Find duplicate code blocks in a form.

    Parses PROCEDURE...ENDPROC blocks, normalizes (removes comments/whitespace),
    hashes them, and finds blocks with identical or similar content.
    """
    import hashlib
    import difflib

    form_sc2 = os.path.abspath(form_sc2)
    if not os.path.isfile(form_sc2):
        emit(False, stderr="form file not found: " + form_sc2)

    with open(form_sc2, "r", encoding="cp1252", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()

    # Find PROCEDURE blocks
    proc_re = re.compile(r'\bPROCEDURE\s+(\w+)', re.IGNORECASE)
    endproc_re = re.compile(r'\bENDPROC', re.IGNORECASE)

    blocks = []
    i = 0
    current_name = None
    current_start = 0
    while i < len(lines):
        m = proc_re.match(lines[i].strip())
        if m:
            current_name = m.group(1)
            current_start = i
        elif endproc_re.match(lines[i].strip()) and current_name:
            blocks.append({
                "name": current_name,
                "start": current_start + 1,
                "end": i + 1,
                "lines": lines[current_start:i],
            })
            current_name = None
        i += 1

    # Normalize and hash blocks
    def normalize(text):
        """Remove comments, normalize whitespace, replace identifiers with VAR."""
        # Remove VFP comments (*, //, &&, NOTE, REM)
        text = re.sub(r'^\s*\*.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'&&.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\bNOTE\b.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\bREM\b.*$', '', text, flags=re.MULTILINE)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Replace identifiers (keep keywords)
        _keywords = (
            "PROCEDURE|ENDPROC|LOCAL|DIMENSION|IF|ENDIF|FOR|ENDDO|WHILE|DO|RETURN|"
            "ELSE|ELSEIF|CASE|ENDCASE|PUBLIC|PROTECTED|PRIVATE|PARAMETERS|STORE|SET|"
            "USE|SEEK|SCAN|COUNT|SUM|CALCULATE|LOCATE|REPLACE|DELETE|APPEND|BROWSE|"
            "GO|TOP|BOTTOM|SKIP|EOF|BOF|FOUND|RECALL|PACK|ZAP|INDEX|TAG|EXCLUSIVE|"
            "SHARED|IN|TO|ALL|REST|NEXT|PREV|FIRST|LAST|BLANK|WITH|FROM|WHERE|AND|"
            "OR|NOT|IS|NULL|BETWEEN|LIKE|ON|BY|ASC|DESC|INTO|CURSOR|ARRAY|MEMO|"
            "CHAR|TEXT|INT|FLOAT|LOGICAL|DATE|STRING|TRUE|FALSE|QUIT|FUNCTION|ENDFUNC"
        )
        text = re.sub(r'\b(?!(?:' + _keywords + r')[\b(])\w+', 'VAR', text)
        return text

    # Filter blocks by min_lines
    valid_blocks = [b for b in blocks if (b["end"] - b["start"] + 1) >= min_lines]

    # Hash
    for b in valid_blocks:
        norm = normalize("\n".join(b["lines"]))
        b["hash"] = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        b["normalized"] = norm

    # Find duplicates by hash (100% similarity)
    hash_groups = {}
    for b in valid_blocks:
        hash_groups.setdefault(b["hash"], []).append(b)

    duplicates = []
    for h, group in hash_groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                duplicates.append({
                    "block1": "%s (lines %d-%d)" % (group[i]["name"], group[i]["start"], group[i]["end"]),
                    "block2": "%s (lines %d-%d)" % (group[j]["name"], group[j]["start"], group[j]["end"]),
                    "similarity": 100,
                    "lines": group[i]["end"] - group[i]["start"] + 1,
                    "type": "identical",
                })

    # Find similar blocks (80%+)
    if len(valid_blocks) > 1:
        checked = set()
        for i in range(len(valid_blocks)):
            for j in range(i + 1, len(valid_blocks)):
                if valid_blocks[i]["hash"] == valid_blocks[j]["hash"]:
                    continue
                pair_key = (i, j)
                if pair_key in checked:
                    continue
                checked.add(pair_key)
                a = valid_blocks[i]["normalized"]
                b_norm = valid_blocks[j]["normalized"]
                if len(a) < 50 or len(b_norm) < 50:
                    continue
                ratio = difflib.SequenceMatcher(None, a, b_norm).ratio()
                if ratio >= 0.80:
                    duplicates.append({
                        "block1": "%s (lines %d-%d)" % (valid_blocks[i]["name"],
                                                         valid_blocks[i]["start"],
                                                         valid_blocks[i]["end"]),
                        "block2": "%s (lines %d-%d)" % (valid_blocks[j]["name"],
                                                         valid_blocks[j]["start"],
                                                         valid_blocks[j]["end"]),
                        "similarity": round(ratio * 100, 1),
                        "lines": valid_blocks[i]["end"] - valid_blocks[i]["start"] + 1,
                        "type": "similar",
                    })

    result = {
        "form": os.path.splitext(os.path.basename(form_sc2))[0],
        "totalProcedures": len(blocks),
        "analyzedBlocks": len(valid_blocks),
        "duplicates": duplicates,
        "duplicateCount": len(duplicates),
    }

    if out_file:
        out_file = os.path.abspath(out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["outputFile"] = out_file

    emit(True, rc=0, data=result)


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

    prp = sub.add_parser("run_prg", help="Run a .prg script in VFP9")
    prp.add_argument("--prg", required=True, help="Path to .prg file")
    prp.add_argument("--workdir", default=None, help="Working directory (default: prg dir)")
    prp.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")

    pb = sub.add_parser("benchmark", help="Benchmark DBF operations in VFP9")
    pb.add_argument("--project", required=True, help="VFP project root (contains Dane/)")
    pb.add_argument("--table", required=True, help="Table alias to benchmark")
    pb.add_argument("--operation", required=True,
                    choices=["calculate_max", "calculate_for", "seek", "scan",
                             "count_for", "sum", "set_filter_goto"])
    pb.add_argument("--expression", default="", help="FOR expression or SEEK key")
    pb.add_argument("--field", default="", help="Field name for CALCULATE/SUM")
    pb.add_argument("--tag", default="", help="TAG name for SEEK")
    pb.add_argument("--iterations", type=int, default=10)
    pb.add_argument("--out", default=None, help="Output file for results")
    pb.add_argument("--timeout", type=int, default=300)

    pfp = sub.add_parser("form_perf", help="Build performance access map for a form")
    pfp.add_argument("--form", required=True, help="Path to .sc2 file")
    pfp.add_argument("--tables-dir", required=True, help="Directory with .dbf/.cdx files")
    pfp.add_argument("--out", default=None, help="Output JSON file")

    pcp = sub.add_parser("count_patterns", help="Count pattern occurrences across forms")
    pcp.add_argument("--project", required=True, help="Project root (with .vfp-ai cache)")
    pcp.add_argument("--patterns", required=True,
                     help="Comma-separated patterns: RLOCK,UNLOCK ALL,SET OPTIMIZE,...")
    pcp.add_argument("--out", default=None, help="Output JSON file")

    pfd = sub.add_parser("find_duplicates", help="Find duplicate code blocks in a form")
    pfd.add_argument("--form", required=True, help="Path to .sc2 file")
    pfd.add_argument("--min-lines", type=int, default=10, help="Minimum block size")
    pfd.add_argument("--out", default=None, help="Output JSON file")

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
    elif a.cmd == "cdx_info":
        run_cdx_info(a.dbf, a.cdx, a.timeout)
    elif a.cmd == "cdx_scan":
        run_cdx_scan(a.dir)
    elif a.cmd == "dbf_dir":
        run_dbf_dir(a.source, a.out, a.formats, a.deleted)
    elif a.cmd == "audit":
        run_audit(a.source, a.out, a.skip_sync, a.include_data, a.data_formats,
                  a.max_tables, a.dbf_exclude, a.no_cache_scan,
                  include_forms=a.include_forms)
    elif a.cmd == "run_prg":
        run_run_prg(a.prg, a.workdir, a.timeout)
    elif a.cmd == "benchmark":
        run_benchmark(a.project, a.table, a.operation,
                      expression=a.expression, field=a.field, tag=a.tag,
                      iterations=a.iterations, out_file=a.out, timeout=a.timeout)
    elif a.cmd == "form_perf":
        run_form_perf(a.form, a.tables_dir, a.out)
    elif a.cmd == "count_patterns":
        run_count_patterns(a.project, a.patterns, a.out)
    elif a.cmd == "find_duplicates":
        run_find_duplicates(a.form, a.min_lines, a.out)


if __name__ == "__main__":
    main()
