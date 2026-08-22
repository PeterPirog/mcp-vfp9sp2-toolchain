#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_driver.py - single Python entrypoint for the OpenCode VFP toolchain.

Subcommands:
  verno      --prg <foxbin2prg.prg>
  convert    --input <file-or-lib::class> --type T --out <folder> --cfg <cfg> --prg <prg>
  convert_dir --project <root> --out <folder> --cfg <cfg> --prg <prg> [--timeout N]
  index      --project <root> --cache <.vfp-ai> [--full]

Output protocol: exactly one JSON object on stdout:
  {"ok": bool, "rc": int|null, "version": str|null, "stdout": str, "stderr": str, "data": {...}}
Exit code: 0 when ok, 2 when not ok.
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VBS = os.path.join(HERE, "vfp_convert.vbs")
VBS_VERNO = os.path.join(HERE, "vfp_verno.vbs")
VFP9_DEFAULT = r"C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe"

BIN_EXTS = [".prg", ".h", ".pjx", ".pjt", ".pj2",
            ".scx", ".sct", ".sc2",
            ".vcx", ".vct", ".vc2",
            ".frx", ".frt", ".fr2",
            ".mnx", ".mnt", ".mn2",
            ".dbc", ".dct", ".dcx", ".dc2",
            ".dbf", ".fpt", ".cdx", ".lb2"]

BIN_WRITEABLE = [".pjx", ".scx", ".vcx", ".frx", ".mnx", ".dbc", ".dbf"]


def emit(ok, **kw):
    payload = {"ok": bool(ok), "rc": None, "version": None,
               "stdout": "", "stderr": "", "data": {}}
    payload.update(kw)
    out = json.dumps(payload, ensure_ascii=True)
    sys.stdout.write(out + "\n")
    sys.exit(0 if ok else 2)


def cscript_path():
    from shutil import which
    return which("cscript.exe") or which("cscript") or "cscript"


def vfp9_path():
    p = os.environ.get("VFP9_EXE")
    if p and os.path.isfile(p):
        return p
    return VFP9_DEFAULT


def _write_default(path, text):
    try:
        data = text.encode("cp1252")
    except Exception:
        data = text.encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)


def _run_process(cmd, timeout, cwd=None):
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
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("RC="):
            try:
                return int(line[3:])
            except ValueError:
                return None
    return None


def run_verno(prg, timeout=120):
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
    result = _convert_one(inp, ctype, out, cfg, prg, timeout)
    emit(result["ok"], rc=result["rc"], stdout=result["stdout"],
         stderr=result["stderr"], data=result["data"])


def run_convert_dir(project, out, cfg, prg, timeout=600):
    """Scan a project directory for VFP binary files and convert each to text."""
    results = []
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d.lower() not in ("backup", "backups", "archive")]
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
    sys.path.insert(0, HERE)
    try:
        import vfp_indexer
    except Exception as e:
        emit(False, stderr="cannot import vfp_indexer: %s" % e)
    try:
        data = vfp_indexer.run(project, cache, full=full)
        emit(True, rc=0, data=data)
    except Exception as e:
        emit(False, stderr="indexer failed: %s" % e, data={"error": str(e)})


def main():
    ap = argparse.ArgumentParser(prog="vfp_driver")
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

    a = ap.parse_args()
    if a.cmd == "verno":
        run_verno(a.prg)
    elif a.cmd == "convert":
        run_convert(a.input, a.type, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "convert_dir":
        run_convert_dir(a.project, a.out, a.cfg, a.prg, a.timeout)
    elif a.cmd == "index":
        run_index(a.project, a.cache, a.full)


if __name__ == "__main__":
    main()
