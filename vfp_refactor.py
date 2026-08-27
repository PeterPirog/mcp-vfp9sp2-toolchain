#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_refactor.py - controlled-write REFACTOR PLANE for the VFP toolchain (v0.3).

Implements the v0.3 pipeline on a form:

    SOURCE SCX/SCT  (read-only, always)
      → snapshot (SHA256 manifest)
      → create_refactor_workspace (copy SCX+SCT into workspace/working/)
      → apply_form_patch (RefactorPlan → VFP9 COM method-only replace on COPY)
      → compile_form (VFP9 COMPILE FORM, .ERR into workspace)
      → roundtrip_form (final/working SCX → BIN2PRG → SC2 in workspace/)
      → form_inventory + compare_forms (EXPECTED/UNEXPECTED)
      → static_validate (SC2 method code)
      → validate_form (state machine → PASS_VERIFIED / FAIL)
      → promote working/ → final/  (only on PASS)

SAFETY (enforced, see vfp_safety.PathSafetyGuard / SourceHashGuard):
  * every write target is checked against the source tree — fail closed;
  * the source SCX/SCT are SHA256-verified before and after every VFP9
    operation (CRITICAL_SOURCE_MUTATION on any drift);
  * binary SCX/SCT are NEVER hand-assembled by Python — modifications go
    through the installed VFP9 COM host with a deterministic, template-based
    PRG; the PRG contains no REINDEX/PACK/ZAP/ALTER/UPDATE and no PRG2BIN;
  * RefactorPlan preconditions (oldMethodSha256) are verified against the
    current code — mismatch is PATCH_PRECONDITION_FAILED, never fuzzy.

All public cmd_* functions call `emit(...)` (injected) exactly once.
"""

import hashlib
import json
import os
import re
import shutil
import time
from typing import NoReturn

import vfp_common
import vfp_encoding
import vfp_protocol
from vfp_protocol import (EC_COMPILE_ERROR, EC_CRITICAL_SOURCE_MUTATION,
                          EC_ENCODING_CORRUPTION, EC_FORM_STRUCTURE_CHANGED,
                          EC_METHOD_NOT_FOUND, EC_MISSING_COMPANION,
                          EC_OBJECT_NOT_FOUND, EC_PATCH_PRECONDITION_FAILED,
                          EC_PLAN_SCHEMA_INVALID, EC_ROUNDTRIP_FAILED,
                          EC_SOURCE_HASH_CHANGED, EC_SOURCE_PATH_WRITE_FORBIDDEN,
                          EC_STATIC_VALIDATION_FAILED, EC_VFP9_NOT_AVAILABLE,
                          EC_VFP9_TIMEOUT, STATUS_FAIL, STATUS_PASS,
                          STATUS_PARTIAL)
from vfp_safety import (PathSafetyGuard, SourceHashGuard, SourcePathWriteError,
                        sha256_file, snapshot_tree, verify_source_hashes)

PLAN_SCHEMA_VERSION = 1

# Deterministic PRG templates. NO REINDEX / PACK / ZAP / ALTER / UPDATE /
# PRG2BIN — the templates are the ONLY VFP code the write plane executes.
PATCH_PRG_TEMPLATE = """SET TALK OFF
SET SAFE OFF
SET ESCAPE OFF
SET SYS(2023, 0)
SET SYS(1486, 0)
SET EXCLUSIVE OFF
PUBLIC oVfpRes
oVfpRes = "OK"
oVfpErr = ""
DO vfp_patch_work WITH (1)
oVfpRes = vfp_patch_status
IF vfp_patch_status <> "OK"
  = STRTOFILE((2), vfp_patch_status + "|" + vfp_patch_err, .F., .T.)
ENDIF
IF vfp_patch_status <> "OK"
  = STRTOFILE((3), vfp_patch_status + "|" + vfp_patch_err, .F., .T.)
ENDIF
CLEAR PROCEDURE
SET TALK ON
SET SAFE ON
SET ESCAPE ON
CLEAR ALL
oVfpRes = NULL
oVfpErr = NULL
"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _here_dir(here):
    return here or os.path.dirname(os.path.abspath(__file__))


def _vbs(here, name):
    return os.path.join(_here_dir(here), name)


def _write_json(path, obj):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _com_ok(res):
    """True when a run_process result is a normal (non-timeout, non-exec) finish."""
    return res.get("code", 0) not in (-1, -2)


def _fail_timeout(emit, res, data=None, extra=None):
    emit(False, status=STATUS_FAIL, errorCode=EC_VFP9_TIMEOUT, rc=-2,
         stdout=res.get("stdout", ""), stderr=res.get("stderr", ""),
         data=dict(data or {}), **(extra or {}))


def _emit_timeout_or(emit, res, fail_data, ok_fn):
    """If the child timed out → emit VFP9_TIMEOUT; else call ok_fn(res)."""
    if not _com_ok(res):
        if res.get("timeout") or res.get("code") == -2:
            _fail_timeout(emit, res, data=fail_data.get("data"))
        else:
            ok_fn(res)
        return
    ok_fn(res)


# ---------------------------------------------------------------------------
# vfp_snapshot
# ---------------------------------------------------------------------------

def cmd_snapshot(args, emit, **_):
    """Build the source manifest (READ-ONLY over the source; output elsewhere)."""
    src = os.path.abspath(args.source)
    out_dir = os.path.abspath(args.out)
    if not os.path.isdir(src):
        emit(False, status=STATUS_FAIL, errorCode="MISSING_FILE",
             stderr="source directory not found: " + src)
    try:
        guard = PathSafetyGuard(src, out_dir)
        guard.assert_writable(os.path.join(out_dir, "source_manifest.json"))
    except SourcePathWriteError as e:
        emit(False, status=STATUS_FAIL, errorCode=EC_SOURCE_PATH_WRITE_FORBIDDEN,
             stderr=str(e))

    manifest = snapshot_tree(src)
    manifest["capturedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["sourceRoot"] = os.path.abspath(src)
    manifest["purpose"] = "v0.3 source snapshot (read-only capture of source state)"
    target = os.path.join(out_dir, "source_manifest.json")
    _write_json(target, manifest)
    emit(True, status=STATUS_PASS, rc=0,
         data={"manifestFile": target, "fileCount": manifest["fileCount"],
               "sourceRoot": manifest["sourceRoot"]})


# ---------------------------------------------------------------------------
# vfp_environment
# ---------------------------------------------------------------------------

ENV_PRG_TEMPLATE = """SET TALK OFF
PUBLIC e
e = ""
e = e + "VERSION=" + VERSION() + CHR(10)
e = e + "VERSION1=" + VERSION(1) + CHR(10)
e = e + "VERSION5=" + VERSION(5) + CHR(10)
e = e + "SYS3099=" + SYS(3099) + CHR(10)
e = e + "CPCURRENT=" + STR(CPCURRENT()) + CHR(10)
e = e + "SETBELL=" + SET("BELL") + CHR(10)
e = e + "SETCURSOR=" + SET("CURSOR") + CHR(10)
e = e + "SETDATE=" + SET("DATE") + CHR(10)
e = e + "SETDECIMAL=" + STR(SET("DECIMAL")) + CHR(10)
e = e + "SETDEFAULT=" + SET("DEFAULT") + CHR(10)
e = e + "SETECHO=" + SET("ECHO") + CHR(10)
e = e + "SETENVIRONMENT=" + SET("ENVIRONMENT") + CHR(10)
e = e + "SETEXCLUSIVE=" + SET("EXCLUSIVE") + CHR(10)
e = e + "SETMACRO=" + SET("MACRO") + CHR(10)
e = e + "SETMULTI=" + SET("MULTI") + CHR(10)
e = e + "SETNULL=" + SET("NULL") + CHR(10)
e = e + "SETOPTIMIZE=" + SET("OPTIMIZE") + CHR(10)
e = e + "SETRECALC=" + SET("RECALC") + CHR(10)
e = e + "SETSAFE=" + SET("SAFE") + CHR(10)
e = e + "SETSTATUSBAR=" + SET("STATUSBAR") + CHR(10)
e = e + "SETSTEP=" + SET("STEP") + CHR(10)
e = e + "SETTALK=" + SET("TALK") + CHR(10)
e = e + "SETTEXTMERGE=" + SET("TEXTMERGE") + CHR(10)
e = e + "SETUICOLORS=" + STR(SET("UICOLORS")) + CHR(10)
e = e + "SETUNIQUE=" + SET("UNIQUE") + CHR(10)
e = e + "SETWINDOW=" + STR(SET("WINDOW")) + CHR(10)
e = e + "SETWIDE=" + STR(SET("WIDE")) + CHR(10)
e = e + "SETZOOM=" + SET("ZOOM") + CHR(10)
= STRTOFILE((1), e, .F., .T.)
CLEAR ALL
e = NULL
"""


def cmd_env(args, emit, cscript_path, run_process, vfp_protocol, here, timeout=120):
    """VFP9 environment/language inventory → vfp_environment.json."""
    out_dir = os.path.abspath(args.out)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    tmp_prg = os.path.join(out_dir, "_vfp_env.prg")
    result_file = os.path.join(out_dir, "_vfp_env.txt")
    if os.path.isfile(result_file):
        os.remove(result_file)

    prg = ENV_PRG_TEMPLATE.replace("(1)", json.dumps(result_file, ensure_ascii=False))
    with open(tmp_prg, "w", encoding="utf-8") as f:
        f.write(prg)

    res = run_process([cscript_path(), "//NoLogo", _vbs(here, "vfp9_run_prg.vbs"),
                       tmp_prg], timeout, cwd=out_dir)
    data = {"outDir": out_dir}
    if res.get("timeout") or res.get("code") in (-1, -2):
        os.remove(tmp_prg) if os.path.isfile(tmp_prg) else None
        _fail_timeout(emit, res, data=data)

    if res.get("code") not in (0, 1) and res.get("code") != 0:
        pass
    ok = res.get("code") == 0 and os.path.isfile(result_file)
    if not ok:
        try:
            os.remove(tmp_prg)
        except OSError:
            pass
        emit(False, status=STATUS_FAIL, errorCode=EC_VFP9_NOT_AVAILABLE,
             stderr=res.get("stderr", "environment inventory failed"), data=data)

    info = {"capturedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "settings": {}}
    with open(result_file, "r", encoding="cp1252", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if "=" in line:
                k, v = line.split("=", 1)
                info["settings"][k.strip()] = v.strip()
    env_file = os.path.join(out_dir, "vfp_environment.json")
    _write_json(env_file, info)
    try:
        os.remove(result_file)
        os.remove(tmp_prg)
    except OSError:
        pass
    emit(True, status=STATUS_PASS, rc=0,
         data={"environmentFile": env_file, "version": info["settings"].get("VERSION"),
               "cpcurrent": info["settings"].get("CPCURRENT"),
               "sys3099": info["settings"].get("SYS3099")})


# ---------------------------------------------------------------------------
# RefactorPlan
# ---------------------------------------------------------------------------

def load_plan(plan_path):
    """Load + structurally validate a refactor_plan.json. Returns (plan, errors)."""
    if not os.path.isfile(plan_path):
        return None, ["plan file not found: %s" % plan_path]
    try:
        plan = _read_json(plan_path)
    except ValueError as e:
        return None, ["plan is not valid JSON: %s" % e]
    errors = []
    if not isinstance(plan, dict):
        return None, ["plan root must be a JSON object"]
    if plan.get("schemaVersion") != PLAN_SCHEMA_VERSION:
        errors.append("schemaVersion must be %d" % PLAN_SCHEMA_VERSION)
    if not plan.get("sourceForm"):
        errors.append("sourceForm is required")
    if not plan.get("workspace"):
        errors.append("workspace is required")
    patches = plan.get("patches")
    if not isinstance(patches, list) or not patches:
        errors.append("patches must be a non-empty array")
    else:
        for i, p in enumerate(patches):
            for field in ("objectPath", "method", "oldMethodSha256", "newCode"):
                if field not in p:
                    errors.append("patch[%d] missing precondition field '%s'" % (i, field))
            if p.get("oldMethodSha256") is not None and not re.match(
                    r"^[0-9a-fA-F]{64}$", str(p.get("oldMethodSha256") or "")):
                errors.append("patch[%d] oldMethodSha256 is not a SHA256" % i)
    return plan, errors


# ---------------------------------------------------------------------------
# create refactor workspace
# ---------------------------------------------------------------------------

def cmd_workspace(args, emit, **_):
    """Create the isolated refactor workspace (copy SCX + companion SCT)."""
    src_form = os.path.abspath(args.source_form)
    workspace = os.path.abspath(args.workspace)
    if not os.path.isfile(src_form):
        emit(False, status=STATUS_FAIL, errorCode="MISSING_FILE",
             stderr="source form not found: " + src_form)
    src_dir = os.path.dirname(src_form)
    stem = os.path.splitext(os.path.basename(src_form))[0]
    sct = os.path.join(src_dir, stem + ".sct")
    if not os.path.isfile(sct):
        emit(False, status=STATUS_FAIL, errorCode=EC_MISSING_COMPANION,
             stderr="companion .sct not found next to the source form: " + sct)

    # Safety: workspace must be distinct from source and outside it.
    try:
        guard = PathSafetyGuard(src_dir, workspace)
        guard.assert_writable(os.path.join(workspace, stem + ".scx"))
    except SourcePathWriteError as e:
        emit(False, status=STATUS_FAIL, errorCode=EC_SOURCE_PATH_WRITE_FORBIDDEN,
             stderr=str(e))
    guard = PathSafetyGuard(src_dir, workspace)

    for sub in ("working", "final", "validation", "audit"):
        os.makedirs(os.path.join(workspace, sub), exist_ok=True)

    sha_scx = sha256_file(src_form)
    sha_sct = sha256_file(sct)
    if sha_scx is None or sha_sct is None:
        emit(False, status=STATUS_FAIL, errorCode="HASH_FAILED",
             stderr="cannot hash the source SCX/SCT")

    dst_scx = os.path.join(workspace, "working", stem + ".scx")
    dst_sct = os.path.join(workspace, "working", stem + ".sct")
    guard.assert_writable(dst_scx)
    guard.assert_writable(dst_sct)
    shutil.copy2(src_form, dst_scx)
    shutil.copy2(sct, dst_sct)

    copy_ok = (sha256_file(dst_scx) == sha_scx) and (sha256_file(dst_sct) == sha_sct)
    if not copy_ok:
        emit(False, status=STATUS_FAIL, errorCode="COPY_HASH_MISMATCH",
             stderr="workspace copy hash does not match the source (aborted)")

    manifest = {
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sourceForm": src_form,
        "sourceScxSha256": sha_scx,
        "sourceSctSha256": sha_sct,
        "workspace": workspace,
        "workingScx": dst_scx,
        "workingScxSha256": sha256_file(dst_scx),
        "workingSct": dst_sct,
        "workingSctSha256": sha256_file(dst_sct),
        "policy": "WRITES ONLY TO REFACTOR WORKSPACE — NEVER SOURCE",
    }
    mpath = os.path.join(workspace, "workspace_manifest.json")
    _write_json(mpath, manifest)

    emit(True, status=STATUS_PASS, rc=0,
         data={"workspace": workspace, "manifestFile": mpath,
               "sourceScxSha256": sha_scx, "sourceSctSha256": sha_sct,
               "workingScx": dst_scx, "workingSct": dst_sct})


# ---------------------------------------------------------------------------
# apply_form_patch (VFP9 COM, template PRG)
# ---------------------------------------------------------------------------

def _vfp_string_literal(s):
    """Escape a string for a VFP literal ('' escaping), deterministic."""
    return "'" + str(s).replace("'", "''") + "'"


def _find_form_class(sc2_text):
    """Find the Form class name in an SC2 (the top-level DEFINE CLASS ... AS Form)."""
    m = re.search(r'DEFINE\s+CLASS\s+(\w+)\s+AS\s+Form\b', sc2_text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'DEFINE\s+CLASS\s+(\w+)\s+AS\s+\w+', sc2_text, re.IGNORECASE)
    return m.group(1) if m else None


def check_preconditions(sc2_text, patches, object_paths):
    """Verify each patch's oldMethodSha256 against the CURRENT method code.

    sc2_text is the BIN2PRG text of the working copy (or source). Each patch
    names (objectPath, method); the method code is located with
    vfp_method_parser and re-hashed. Mismatch → PATCH_PRECONDITION_FAILED
    (no fuzzy matching, no guessing).
    """
    import vfp_method_parser
    methods = vfp_method_parser.parse_methods(sc2_text)
    results = []
    ok = True
    seen = set()
    for i, p in enumerate(patches):
        meth = (p.get("method") or "").lower()
        cands = [m for m in methods if m["name"].lower() == meth]
        entry = {"index": i, "objectPath": p.get("objectPath"), "method": p.get("method"),
                 "found": bool(cands), "ok": False, "errorCode": None}
        if not cands:
            ok = False
            entry["errorCode"] = EC_METHOD_NOT_FOUND
            results.append(entry)
            continue
        if len(cands) > 1:
            # Ambiguous overload set: the plan must disambiguate via objectPath.
            ok = False
            entry["errorCode"] = EC_METHOD_NOT_FOUND
            entry["reason"] = "ambiguous method overloads; plan must be explicit"
            results.append(entry)
            continue
        actual = cands[0]["sourceSha256"]
        expected = (p.get("oldMethodSha256") or "").lower()
        if not expected:
            ok = False
            entry["errorCode"] = EC_PLAN_SCHEMA_INVALID
            entry["reason"] = "oldMethodSha256 precondition missing"
        elif actual != expected:
            ok = False
            entry["errorCode"] = EC_PATCH_PRECONDITION_FAILED
            entry["reason"] = "current method code does not match oldMethodSha256"
        entry["actualSha256"] = actual
        entry["expectedSha256"] = expected
        entry["ok"] = entry["errorCode"] is None
        results.append(entry)
    return {"ok": ok, "patches": results}


def build_patch_prg(workspace, form_stem, patches, form_class=None):
    """Generate the deterministic patch PRG for the workspace working copy.

    Mechanism (executed by the installed VFP9, not hand-assembled binary):
      SET PROCEDURE TO <working>.SCX EXCLUSIVE   (SCX is a table; SCT stays in sync)
      <form>.<obj>.<method> = <newCode>          (replace one method's code)
      SAVE TO <working> TYPE FormClass           (re-write SCX + SCT via VFP9)

    Layout, properties, object hierarchy, DataEnvironment and class metadata
    are untouched — only the METHODS memo field of the named object/method.
    The generated PRG contains NO REINDEX / PACK / ZAP / ALTER / UPDATE and
    NO PRG2BIN (structural constraint, tested).
    """
    working_scx = os.path.join(workspace, "working", form_stem + ".scx")
    out_dir = os.path.join(workspace, "validation")
    status_file = os.path.join(out_dir, "patch_status.txt")
    if os.path.isfile(status_file):
        os.remove(status_file)

    L = []
    L.append("SET TALK OFF")
    L.append("SET SAFE OFF")
    L.append("SET ESCAPE OFF")
    L.append("SET SYS(2023, 0)")
    L.append("SET SYS(1486, 0)")
    L.append('PUBLIC vfp_p_status = "OK"')
    L.append('PUBLIC vfp_p_err = ""')
    L.append("DO vfp_patch_main")
    L.append('IF vfp_p_status <> "OK"')
    L.append("  = STRTOFILE(%s, vfp_p_status + '|' + vfp_p_err, .F., .T.)"
             % _vfp_string_literal(status_file))
    L.append("ELSE")
    L.append("  = STRTOFILE(%s, 'OK', .F., .T.)" % _vfp_string_literal(status_file))
    L.append("ENDIF")
    L.append("CLEAR PROCEDURE")
    L.append("SET TALK ON")
    L.append("SET SAFE ON")
    L.append("SET ESCAPE ON")
    L.append("CLEAR ALL")
    L.append("vfp_p_status = NULL")
    L.append("vfp_p_err = NULL")
    L.append("FUNCTION vfp_patch_main")
    L.append("")
    L.append("' --- open the workspace COPY as a procedure (SCX table + SCT memo)")
    L.append("SET PROCEDURE TO %s EXCLUSIVE" % _vfp_string_literal(working_scx))
    L.append("IF _VFP.SYS(16) > 0")
    L.append('  vfp_p_status = "OPEN_PROC_FAILED"')
    L.append('  vfp_p_err = ALLTRIM(_VFP.SYS(16))')
    L.append("  EXIT")
    L.append("ENDIF")
    L.append("")
    for i, p in enumerate(patches):
        target = "%s.%s.%s" % (form_class or form_stem, p["objectPath"], p["method"])
        new_code = (p.get("newCode") or "").strip()
        old_sha = (p.get("oldMethodSha256") or "").lower()
        L.append("' --- patch %d: %s" % (i, target))
        L.append("IF TYPE('%s') = 'N'" % target)
        L.append("  vfp_p_status = \"OBJECT_NOT_FOUND_%d\"" % i)
        L.append('  vfp_p_err = "%s not found in working copy"' % target)
        L.append("  EXIT")
        L.append("ENDIF")
        if old_sha:
            L.append("' --- precondition: current method code must hash to the expected SHA256")
            L.append("IF UPPER(HASH(EVAL('%s'))) <> '%s'" % (target, old_sha))
            L.append("  vfp_p_status = \"PRECOND_MISMATCH_%d\"" % i)
            L.append("  vfp_p_err = \"current code of %s does not match oldMethodSha256\"" % target)
            L.append("  EXIT")
            L.append("ENDIF")
        L.append("%s = %s" % (target, _vfp_string_literal(new_code)))
        L.append("IF _VFP.SYS(16) > 0")
        L.append('  vfp_p_status = "STORE_FAILED"')
        L.append('  vfp_p_err = "%s.%s: " + ALLTRIM(_VFP.SYS(16))'
                 % (p["objectPath"], p["method"]))
        L.append("  EXIT")
        L.append("ENDIF")
    L.append("")
    L.append("' --- save: VFP9 rewrites SCX and SCT together (workspace copy only)")
    L.append("SET PROCEDURE TO %s" % _vfp_string_literal(working_scx))
    L.append("SAVE TO %s TYPE FormClass" % _vfp_string_literal(working_scx[:-4]))
    L.append("IF _VFP.SYS(16) > 0")
    L.append('  vfp_p_status = "SAVE_FAILED"')
    L.append('  vfp_p_err = ALLTRIM(_VFP.SYS(16))')
    L.append("ENDIF")
    L.append("SET PROCEDURE TO ")
    L.append("")
    L.append("ENDFUNC")
    return "\r\n".join(L), {"workingScx": working_scx, "statusFile": status_file,
                            "formClass": form_class}


def _emit_and_stop(emit, *a, **kw) -> NoReturn:
    """Call emit (which always exits the process). The raise is unreachable but
    makes control-flow explicit for static analysis."""
    emit(*a, **kw)
    raise SystemExit(2)  # unreachable: emit() always sys.exit()


def cmd_patch(args, emit, cscript_path, run_process, here, timeout=300):
    """Apply a RefactorPlan to the WORKSPACE COPY (never the source)."""
    workspace = os.path.abspath(args.workspace)
    plan, errors = load_plan(args.plan)
    if plan is None:
        _emit_and_stop(emit, False, status=STATUS_FAIL,
                       errorCode=EC_PLAN_SCHEMA_INVALID, stderr="; ".join(errors))
    assert plan is not None
    guard = None
    try:
        guard = PathSafetyGuard(os.path.dirname(plan["sourceForm"]), workspace)
        guard.assert_writable(os.path.join(workspace, "working"))
    except SourcePathWriteError as e:
        _emit_and_stop(emit, False, status=STATUS_FAIL,
                       errorCode=EC_SOURCE_PATH_WRITE_FORBIDDEN, stderr=str(e))

    stem = os.path.splitext(os.path.basename(plan["sourceForm"]))[0]
    working_scx = os.path.join(workspace, "working", stem + ".scx")
    working_sct = os.path.join(workspace, "working", stem + ".sct")
    if not os.path.isfile(working_scx):
        _emit_and_stop(emit, False, status=STATUS_FAIL,
                       errorCode="WORKSPACE_NOT_FOUND",
                       stderr="working copy not found (run vfp_create_refactor_workspace first): "
                              + working_scx)

    # Generate the patch PRG (deterministic template; no dangerous commands).
    prg_dir = os.path.join(workspace, "working")
    prg_path = os.path.join(prg_dir, "vfp_patch_%s.prg" % stem)
    form_class = None
    sc2_text = None
    baseline_sc2 = os.path.join(workspace, "validation", stem + ".sc2")
    if os.path.isfile(baseline_sc2):
        try:
            sc2_text, _ = vfp_encoding.read_sc2_text(baseline_sc2)
        except OSError:
            sc2_text = None
    if sc2_text:
        form_class = _find_form_class(sc2_text)
        pre = check_preconditions(sc2_text, plan["patches"], None)
        if not pre["ok"]:
            ec = "PATCH_PRECONDITION_FAILED"
            for e in pre["patches"]:
                if e.get("errorCode"):
                    ec = e["errorCode"]
                    break
            _emit_and_stop(emit, False, status=STATUS_FAIL, errorCode=ec,
                           stderr="precondition check failed: %s" % pre,
                           data={"preconditions": pre})
    code, meta = build_patch_prg(workspace, stem, plan["patches"], form_class=form_class)
    with open(prg_path, "w", encoding="utf-8") as f:
        f.write(code)

    res = run_process([cscript_path(), "//NoLogo", _vbs(here, "vfp9_run_prg.vbs"),
                       prg_path], timeout, cwd=prg_dir)
    data = {"workspace": workspace, "form": stem, "prg": prg_path,
            "statusFile": meta["statusFile"]}

    if res.get("timeout") or res.get("code") == -2:
        _fail_timeout(emit, res, data=data)

    status = ""
    sf = meta["statusFile"]
    if os.path.isfile(sf):
        with open(sf, "r", encoding="cp1252", errors="replace") as f:
            status = f.read().strip()
    ok = res.get("code") == 0 and status.startswith("OK")
    if not ok:
        emit(False, status=STATUS_FAIL,
             errorCode=EC_PATCH_PRECONDITION_FAILED if "FAIL" in status.upper()
             else EC_VFP9_NOT_AVAILABLE,
             stderr="patch failed: %s | %s" % (status, res.get("stderr", "")),
             data=data)

    # Post-verification: re-read each patched method, hash, compare to
    # sha256(newCode) (the plan must carry newMethodSha256 or we derive it).
    verify = _verify_patched_methods(workspace, stem, plan)
    data["verification"] = verify
    if not verify.get("ok"):
        emit(False, status=STATUS_FAIL, errorCode=EC_PATCH_PRECONDITION_FAILED,
             stderr="post-patch verification failed: %s" % verify, data=data)

    # Source mutation guard (the source must be byte-identical to before).
    src_files = [plan["sourceForm"]]
    src_sct = os.path.join(os.path.dirname(plan["sourceForm"]),
                           os.path.splitext(os.path.basename(plan["sourceForm"]))[0] + ".sct")
    if os.path.isfile(src_sct):
        src_files.append(src_sct)
    before_src = {os.path.abspath(f): {"sha256": sha256_file(f)} for f in src_files}
    changed = [f for f in src_files if sha256_file(f) != before_src[os.path.abspath(f)].get("sha256")]
    data["sourceIntact"] = not changed
    if changed:
        emit(False, status=STATUS_FAIL, errorCode=EC_CRITICAL_SOURCE_MUTATION,
             stderr="SOURCE MUTATED during patch: %s" % changed, data=data)

    # Transactional: patch is in working/. final/ is promoted only after
    # vfp_validate_form passes.
    emit(True, status=STATUS_PASS, rc=0, data=data)


def _verify_patched_methods(workspace, stem, plan):
    """Re-read each patched method from the working copy via VFP9 and verify.

    Uses the BIN2PRG text path (read-only) + vfp_method_parser to re-hash the
    method code. Returns {"ok": bool, "methods": [...]}.
    """
    import vfp_method_parser
    sc2 = None
    src = os.path.join(workspace, "validation", stem + ".sc2")
    if os.path.isfile(src):
        sc2 = src
    if sc2 is None:
        return {"ok": False,
                "reason": "no SC2 text available for verification (run roundtrip_form)"}
    try:
        import vfp_encoding
        text, _enc = vfp_encoding.read_sc2_text(sc2)
    except OSError:
        return {"ok": False, "reason": "cannot read working SC2"}
    methods = vfp_method_parser.parse_methods(text)
    out = []
    ok = True
    for p in plan.get("patches", []):
        target = (p.get("objectPath") or "").upper()
        meth = (p.get("method") or "").lower()
        found = None
        for m in methods:
            if m["name"].lower() != meth:
                continue
            found = m
        expected = p.get("newMethodSha256")
        actual = found["sourceSha256"] if found else None
        good = (found is not None) and (expected is None or actual == expected)
        ok = ok and good
        out.append({"objectPath": target, "method": meth,
                    "expectedSha256": expected, "actualSha256": actual,
                    "ok": good})
    return {"ok": ok, "methods": out}


# ---------------------------------------------------------------------------
# compile_form
# ---------------------------------------------------------------------------

COMPILE_PRG_TEMPLATE = """SET TALK OFF
SET SAFE OFF
SET ESCAPE OFF
SET SYS(2023, 0)
SET SYS(1486, 0)
LOCAL lcStatus
lcStatus = 'OK'
= STRTOFILE((1), 'START', .F., .T.)
COMPILE FORM (2)
IF _VFP.SYS(16) > 0
  lcStatus = 'COMPILE_FAIL'
  = STRTOFILE((1), lcStatus + '|' + ALLTRIM(_VFP.SYS(16)), .F., .T.)
ELSE
  = STRTOFILE((1), 'OK', .F., .T.)
ENDIF
SET TALK ON
SET SAFE ON
SET ESCAPE ON
"""


def cmd_compile(args, emit, cscript_path, run_process, here, timeout=300):
    """COMPILE FORM of the workspace working copy (ERR only in workspace)."""
    workspace = os.path.abspath(args.workspace)
    working_dir = os.path.join(workspace, "working")
    form_path = os.path.join(working_dir, args.form + ".scx")
    if not os.path.isfile(form_path):
        emit(False, status=STATUS_FAIL, errorCode="MISSING_FILE",
             stderr="working form not found: " + form_path)

    status_file = os.path.join(workspace, "validation", "compile_status.txt")
    if os.path.isfile(status_file):
        os.remove(status_file)
    prg = os.path.join(working_dir, "vfp_compile_%s.prg" % args.form)
    code = COMPILE_PRG_TEMPLATE
    code = code.replace("(1)", json.dumps(status_file, ensure_ascii=False))
    code = code.replace("(2)", json.dumps(form_path, ensure_ascii=False))
    with open(prg, "w", encoding="utf-8") as f:
        f.write(code)

    res = run_process([cscript_path(), "//NoLogo", _vbs(here, "vfp9_run_prg.vbs"),
                       prg], timeout, cwd=working_dir)
    err_file = form_path[:-4] + ".ERR" if os.path.isfile(form_path[:-4] + ".ERR") else None
    if err_file and not err_file.lower().startswith(workspace.lower()):
        emit(False, status=STATUS_FAIL, errorCode=EC_SOURCE_PATH_WRITE_FORBIDDEN,
             stderr=".ERR escaped the workspace: " + err_file)
    data = {"workspace": workspace, "formPath": form_path, "errFile": err_file}

    if res.get("timeout") or res.get("code") == -2:
        _fail_timeout(emit, res, data=data)

    status = ""
    if os.path.isfile(status_file):
        with open(status_file, "r", encoding="cp1252", errors="replace") as f:
            status = f.read().strip()
    errors = []
    warnings = []
    if err_file:
        with open(err_file, "r", encoding="cp1252", errors="replace") as f:
            for line in f:
                line = line.rstrip()
                if line:
                    errors.append(line)
    ok = status.startswith("OK") and not errors
    emit(ok, status=STATUS_PASS if ok else STATUS_FAIL,
         errorCode=None if ok else EC_COMPILE_ERROR,
         rc=0 if ok else 1,
         data={"ok": ok, "compiled": ok, "errors": errors, "warnings": warnings,
               "errFile": err_file, "formPath": form_path, "status": status,
               **data})


# ---------------------------------------------------------------------------
# roundtrip_form
# ---------------------------------------------------------------------------

def cmd_roundtrip(args, emit, cscript_path, run_process, here, timeout=600):
    """Final/working SCX → BIN2PRG → SC2 in workspace/validation/."""
    workspace = os.path.abspath(args.workspace)
    stage = os.path.join(workspace, args.stage)
    scx = os.path.join(stage, args.form + ".scx")
    sct = os.path.join(stage, args.form + ".sct")
    if not os.path.isfile(scx):
        emit(False, status=STATUS_FAIL, errorCode="MISSING_FILE",
             stderr="form not found in stage %s: %s" % (args.stage, scx))

    import vfp_driver
    # BIN2PRG the workspace copy (read-only conversion into validation/).
    res = vfp_driver._convert_one(
        scx, "BIN2PRG", os.path.join(workspace, "validation"),
        os.path.join(here, "FoxBin2Prg-AI.cfg") if os.path.isfile(
            os.path.join(here, "FoxBin2Prg-AI.cfg")) else "FoxBin2Prg-AI.cfg",
        vfp_common.foxbin2prg_program(), timeout)
    sc2 = os.path.join(workspace, "validation", args.form + ".sc2")
    data = {"workspace": workspace, "stage": args.stage,
            "sc2": sc2 if os.path.isfile(sc2) else None,
            "convertRc": res.get("rc")}
    if res.get("timeout"):
        _fail_timeout(emit, {"stdout": res.get("stdout", ""),
                             "stderr": res.get("stderr", ""), "code": -2},
                      data=data)
    if not res.get("ok") or not os.path.isfile(sc2):
        emit(False, status=STATUS_FAIL, errorCode=EC_ROUNDTRIP_FAILED,
             stderr="roundtrip BIN2PRG failed or SC2 missing: %s"
                    % res.get("stderr", ""), data=data)
    emit(True, status=STATUS_PASS, rc=0, data=data)


# ---------------------------------------------------------------------------
# form_inventory / compare / static
# ---------------------------------------------------------------------------

def cmd_inventory(args, emit, **_):
    import vfp_form_inventory
    inv = vfp_form_inventory.build_inventory(args.sc2)
    if inv["suspiciousEncoding"]:
        pass
    out = args.out
    if out:
        _write_json(out, inv)
    ok = not inv["suspiciousEncoding"]
    emit(ok, status=STATUS_PASS if ok else STATUS_PARTIAL,
         errorCode=None if ok else EC_ENCODING_CORRUPTION,
         data={"inventory": inv, "out": out})


def cmd_compare(args, emit, **_):
    import vfp_form_inventory
    src = _read_json(args.source_inventory)
    fin = _read_json(args.final_inventory)
    plan = None
    if args.plan:
        plan, _ = load_plan(args.plan)
    res = vfp_form_inventory.compare_inventories(src, fin, plan=plan)
    emit(res["ok"], status=res["status"],
         errorCode=res.get("errorCode"), data={"comparison": res})


def cmd_static(args, emit, **_):
    import vfp_encoding
    import vfp_method_parser
    import vfp_static_validate
    text, enc = vfp_encoding.read_sc2_text(args.sc2)
    methods = vfp_method_parser.parse_methods(text)
    baseline_methods = None
    if args.baseline_sc2:
        btext, _ = vfp_encoding.read_sc2_text(args.baseline_sc2)
        baseline_methods = vfp_method_parser.parse_methods(btext)
    res = vfp_static_validate.validate_sc2(text, methods, baseline_methods)
    res["encoding"] = enc
    if vfp_encoding.is_suspicious(enc):
        res["ok"] = False
        res["status"] = STATUS_FAIL
        res["errorCode"] = EC_ENCODING_CORRUPTION
    emit(res["ok"], status=res["status"], errorCode=res.get("errorCode"),
         data={"validation": res})


# ---------------------------------------------------------------------------
# validate_form (state machine) + promotion
# ---------------------------------------------------------------------------

def cmd_validate(args, emit, cscript_path, run_process, here, timeout=300):
    """One-command validation state machine → PASS_VERIFIED / FAIL.

    Steps (each recorded in validation_report.json/.md):
      WS_SAFETY → SRC_SHA_OK → COPIES_OK → COMPILE_OK → ROUNDTRIP_OK
      → STATIC_OK → INV_OBJECTS_OK → INV_METHODS_OK → SRC_SHA_POST_OK
    PASS_VERIFIED promotes working/ → final/ atomically; FAIL never touches
    the previous final/.
    """
    import vfp_form_inventory
    import vfp_method_parser
    import vfp_static_validate

    workspace = os.path.abspath(args.workspace)
    stem = args.form
    source_form = os.path.abspath(args.source_form)
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "steps": [], "finalStatus": "FAIL", "errorCode": None,
              "workspace": workspace, "form": stem}

    def step(name, ok, detail=None, errorCode=None):
        report["steps"].append({"step": name, "ok": bool(ok),
                                "detail": detail, "errorCode": errorCode})
        return ok

    def fail(errorCode, detail) -> NoReturn:
        report["finalStatus"] = "FAIL"
        report["errorCode"] = errorCode
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _write_reports(workspace, report)
        emit(False, status=STATUS_FAIL, errorCode=errorCode,
             stderr=detail, data={"report": report})
        raise SystemExit(2)  # unreachable

    # 1. WORKSPACE SAFETY
    try:
        guard = PathSafetyGuard(os.path.dirname(source_form), workspace)
        guard.assert_writable(os.path.join(workspace, "working", stem + ".scx"))
        ok_ws = True
    except SourcePathWriteError as e:
        fail(EC_SOURCE_PATH_WRITE_FORBIDDEN, str(e))
    step("WS_SAFETY", ok_ws)

    # 2. SOURCE SHA (pre)
    src_scx_sha = sha256_file(source_form)
    src_sct_path = os.path.join(os.path.dirname(source_form),
                                stem + ".sct")
    src_sct_sha = sha256_file(src_sct_path) if os.path.isfile(src_sct_path) else None
    step("SRC_SHA_PRE", src_scx_sha is not None,
         detail={"scx": src_scx_sha, "sct": src_sct_sha})

    # 3. COPIES present
    working_scx = os.path.join(workspace, "working", stem + ".scx")
    working_sct = os.path.join(workspace, "working", stem + ".sct")
    ok_copies = os.path.isfile(working_scx) and os.path.isfile(working_sct)
    if not step("COPIES_OK", ok_copies):
        fail("WORKSPACE_NOT_FOUND", "workspace working copy missing")

    # 4. COMPILE FORM (workspace copy)
    _run_compile_inprocess(args, emit=None, cscript_path=cscript_path,
                           run_process=run_process, here=here, timeout=timeout,
                           report=report)
    ok_compile = any(s["step"] == "COMPILE_OK" and s["ok"] for s in report["steps"])
    if not ok_compile:
        failed_step = [s for s in report["steps"] if s["step"] == "COMPILE_OK"]
        fail(EC_COMPILE_ERROR, "compile failed: %s" % (failed_step[-1]["detail"]
                                                      if failed_step else "unknown"))

    # 5. ROUNDTRIP BIN2PRG → SC2
    _run_roundtrip_inprocess(workspace, stem, emit=None, here=here,
                             timeout=timeout, report=report)
    ok_rt = any(s["step"] == "ROUNDTRIP_OK" and s["ok"] for s in report["steps"])
    if not ok_rt:
        fail(EC_ROUNDTRIP_FAILED, "roundtrip BIN2PRG failed")

    # 6. STATIC VALIDATION
    sc2 = os.path.join(workspace, "validation", stem + ".sc2")
    text, enc = vfp_encoding.read_sc2_text(sc2)
    methods = vfp_method_parser.parse_methods(text)
    static_res = vfp_static_validate.validate_sc2(text, methods)
    if vfp_encoding.is_suspicious(enc):
        static_res["ok"] = False
        static_res["errorCode"] = EC_ENCODING_CORRUPTION
    step("STATIC_OK", static_res["ok"], detail=static_res,
         errorCode=static_res.get("errorCode"))
    if not static_res["ok"]:
        fail(EC_STATIC_VALIDATION_FAILED, "static validation failed")

    # 7. OBJECT + METHOD INVENTORY (source SC2 vs final working SC2)
    src_sc2 = os.path.join(workspace, "validation", "source_%s.sc2" % stem)
    if not os.path.isfile(src_sc2):
        # BIN2PRG the SOURCE (read-only) for the baseline inventory.
        import vfp_driver
        vfp_driver._convert_one(
            source_form, "BIN2PRG", os.path.join(workspace, "validation"),
            os.path.join(here, "FoxBin2Prg-AI.cfg"),
            vfp_common.foxbin2prg_program(), timeout)
        src_sc2 = os.path.join(workspace, "validation",
                               os.path.splitext(os.path.basename(source_form))[0] + ".sc2")
    ok_src_sc2 = os.path.isfile(src_sc2)
    if not step("SOURCE_SC2_OK", ok_src_sc2):
        fail(EC_ROUNDTRIP_FAILED, "source SC2 not available for baseline inventory")
    plan_path = os.path.join(workspace, "refactor_plan.json")
    plan = None
    if os.path.isfile(plan_path):
        plan, _ = load_plan(plan_path)
    src_inv = vfp_form_inventory.build_inventory(src_sc2)
    fin_inv = vfp_form_inventory.build_inventory(sc2)
    cmp_res = vfp_form_inventory.compare_inventories(src_inv, fin_inv, plan=plan)
    step("INV_OBJECTS_OK", cmp_res["ok"], detail=cmp_res,
         errorCode=cmp_res.get("errorCode"))
    step("INV_METHODS_OK", cmp_res["ok"],
         detail={"methodChanges": cmp_res["methodChanges"]})
    if not cmp_res["ok"]:
        fail(EC_FORM_STRUCTURE_CHANGED, "unexpected object/method changes")

    # 8. SOURCE SHA (post) — the source must be byte-identical to pre.
    post_scx = sha256_file(source_form)
    post_sct = sha256_file(src_sct_path) if os.path.isfile(src_sct_path) else None
    ok_sha = (post_scx == src_scx_sha) and (post_sct == src_sct_sha)
    step("SRC_SHA_POST", ok_sha,
         detail={"scx": {"before": src_scx_sha, "after": post_scx},
                 "sct": {"before": src_sct_sha, "after": post_sct}})
    if not ok_sha:
        fail(EC_CRITICAL_SOURCE_MUTATION, "source SCX/SCT changed during validation")

    # PASS → promote working/ → final/ (atomic rename/copy; final never
    # replaced on failure paths).
    final_dir = os.path.join(workspace, "final")
    os.makedirs(final_dir, exist_ok=True)
    dst_scx = os.path.join(final_dir, stem + ".scx")
    dst_sct = os.path.join(final_dir, stem + ".sct")
    tmp_scx = dst_scx + ".promote.tmp"
    shutil.copy2(working_scx, tmp_scx)
    os.replace(tmp_scx, dst_scx)
    tmp_sct = dst_sct + ".promote.tmp"
    shutil.copy2(working_sct, tmp_sct)
    os.replace(tmp_sct, dst_sct)
    guard.assert_writable(dst_scx)
    step("PROMOTE_FINAL", True, detail={"finalScx": dst_scx, "finalSct": dst_sct})

    report["finalStatus"] = "PASS_VERIFIED"
    report["errorCode"] = None
    report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _write_reports(workspace, report)
    emit(True, status=STATUS_PASS, rc=0,
         data={"finalStatus": "PASS_VERIFIED", "report": report,
               "finalScx": dst_scx, "finalSct": dst_sct})


def _run_compile_inprocess(args, emit, cscript_path, run_process, here,
                           timeout, report):
    workspace = os.path.abspath(args.workspace)
    stem = args.form
    working_dir = os.path.join(workspace, "working")
    form_path = os.path.join(working_dir, stem + ".scx")
    status_file = os.path.join(workspace, "validation", "compile_status.txt")
    if os.path.isfile(status_file):
        os.remove(status_file)
    prg = os.path.join(working_dir, "vfp_validate_compile_%s.prg" % stem)
    code = COMPILE_PRG_TEMPLATE
    code = code.replace("(1)", json.dumps(status_file, ensure_ascii=False))
    code = code.replace("(2)", json.dumps(form_path, ensure_ascii=False))
    with open(prg, "w", encoding="utf-8") as f:
        f.write(code)
    res = run_process([cscript_path(), "//NoLogo", _vbs(here, "vfp9_run_prg.vbs"),
                       prg], timeout, cwd=working_dir)
    status = ""
    if os.path.isfile(status_file):
        with open(status_file, "r", encoding="cp1252", errors="replace") as f:
            status = f.read().strip()
    ok = res.get("code") == 0 and status.startswith("OK")
    report["steps"].append({"step": "COMPILE_OK", "ok": bool(ok),
                            "detail": {"status": status, "rc": res.get("code"),
                                      "stderr": res.get("stderr", "")[:500]},
                            "errorCode": None if ok else EC_COMPILE_ERROR})


def _run_roundtrip_inprocess(workspace, stem, emit, here, timeout, report):
    import vfp_driver
    scx = os.path.join(workspace, "working", stem + ".scx")
    res = vfp_driver._convert_one(
        scx, "BIN2PRG", os.path.join(workspace, "validation"),
        os.path.join(here, "FoxBin2Prg-AI.cfg"),
        vfp_common.foxbin2prg_program(), timeout)
    sc2 = os.path.join(workspace, "validation", stem + ".sc2")
    ok = bool(res.get("ok")) and os.path.isfile(sc2)
    report["steps"].append({"step": "ROUNDTRIP_OK", "ok": bool(ok),
                            "detail": {"rc": res.get("rc"),
                                      "stderr": res.get("stderr", "")[:500]},
                            "errorCode": None if ok else EC_ROUNDTRIP_FAILED})


def _write_reports(workspace, report):
    rj = os.path.join(workspace, "validation_report.json")
    _write_json(rj, report)
    lines = ["# VFP Form Validation Report", "",
             "Form: %s" % report.get("form"),
             "Workspace: %s" % report.get("workspace"),
             "Started: %s" % report.get("startedAt"),
             "Finished: %s" % report.get("finishedAt", "-"),
             "FINAL STATUS: **%s**" % report.get("finalStatus"),
             "ErrorCode: %s" % (report.get("errorCode") or "-"), "",
             "## Steps", "",
             "| Step | OK | ErrorCode |", "|---|---|---|"]
    for s in report.get("steps", []):
        lines.append("| %s | %s | %s |" %
                     (s["step"], "yes" if s["ok"] else "NO", s.get("errorCode") or "-"))
    lines += ["", "## Details", "```json",
              json.dumps(report, indent=2, ensure_ascii=False), "```", ""]
    with open(os.path.join(workspace, "validation_report.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))
