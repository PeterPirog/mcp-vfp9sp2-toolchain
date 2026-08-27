#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_protocol.py - shared output protocol and process runner for the VFP toolchain.

SINGLE SOURCE OF TRUTH for:
  - the JSON output protocol (exactly one JSON object per CLI command),
  - status vocabulary (PASS / FAIL / PARTIAL) and machine-readable errorCodes,
  - running child processes with PID-scoped cleanup on timeout.

SAFETY: on timeout the toolchain terminates ONLY the child PID it spawned
(Windows: TerminateProcess via ctypes; POSIX: SIGKILL). It never kills
unrelated processes and never terminates vfp9.exe by image name. When the
owner of a stuck VFP9 COM host cannot be attributed to this operation, the
caller receives a VFP9_TIMEOUT diagnostic and must ask for manual
investigation.

Importable without side effects; no VFP9 required.
"""

import ctypes
import json
import os
import subprocess
import sys
from typing import NoReturn

# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_PARTIAL = "PARTIAL"

# ---------------------------------------------------------------------------
# Machine-readable error codes (stable; agents and CI rely on these)
# ---------------------------------------------------------------------------

EC_SOURCE_PATH_WRITE_FORBIDDEN = "SOURCE_PATH_WRITE_FORBIDDEN"
EC_SOURCE_HASH_CHANGED = "SOURCE_HASH_CHANGED"
EC_CRITICAL_SOURCE_MUTATION = "CRITICAL_SOURCE_MUTATION"
EC_MISSING_COMPANION = "MISSING_COMPANION"
EC_PATCH_PRECONDITION_FAILED = "PATCH_PRECONDITION_FAILED"
EC_VFP9_NOT_AVAILABLE = "VFP9_NOT_AVAILABLE"
EC_VFP9_TIMEOUT = "VFP9_TIMEOUT"
EC_COMPILE_ERROR = "COMPILE_ERROR"
EC_ROUNDTRIP_FAILED = "ROUNDTRIP_FAILED"
EC_FORM_STRUCTURE_CHANGED = "FORM_STRUCTURE_CHANGED"
EC_ENCODING_CORRUPTION = "ENCODING_CORRUPTION"
EC_STATIC_VALIDATION_FAILED = "STATIC_VALIDATION_FAILED"
EC_PLAN_SCHEMA_INVALID = "PLAN_SCHEMA_INVALID"
EC_WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
EC_OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
EC_METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
EC_WORKSPACE_WRITE_FORBIDDEN = "WORKSPACE_WRITE_FORBIDDEN"

ALL_ERROR_CODES = (
    EC_SOURCE_PATH_WRITE_FORBIDDEN,
    EC_SOURCE_HASH_CHANGED,
    EC_CRITICAL_SOURCE_MUTATION,
    EC_MISSING_COMPANION,
    EC_PATCH_PRECONDITION_FAILED,
    EC_VFP9_NOT_AVAILABLE,
    EC_VFP9_TIMEOUT,
    EC_COMPILE_ERROR,
    EC_ROUNDTRIP_FAILED,
    EC_FORM_STRUCTURE_CHANGED,
    EC_ENCODING_CORRUPTION,
    EC_STATIC_VALIDATION_FAILED,
    EC_PLAN_SCHEMA_INVALID,
    EC_WORKSPACE_NOT_FOUND,
    EC_OBJECT_NOT_FOUND,
    EC_METHOD_NOT_FOUND,
    EC_WORKSPACE_WRITE_FORBIDDEN,
)

__all__ = [n for n in list(globals()) if n.startswith(("STATUS_", "EC_", "ALL_"))] + [
    "emit", "run_process", "parse_driver_output", "result_payload",
]


# ---------------------------------------------------------------------------
# Output protocol
# ---------------------------------------------------------------------------

def result_payload(ok, status=None, errorCode=None, rc=None, version=None,
                   stdout="", stderr="", data=None, **extra):
    """Build the single-JSON-object payload used by every CLI subcommand.

    Protocol:
        {"ok": bool, "status": "PASS|FAIL|PARTIAL"|null, "errorCode": str|null,
         "rc": int|null, "version": str|null,
         "stdout": str, "stderr": str, "data": {...}}
    """
    if status is None:
        status = STATUS_PASS if ok else STATUS_FAIL
    if not ok and errorCode is None:
        errorCode = "UNEXPECTED_ERROR"
    payload = {
        "ok": bool(ok),
        "status": status,
        "errorCode": errorCode,
        "rc": rc,
        "version": version,
        "stdout": stdout,
        "stderr": stderr,
        "data": data if data is not None else {},
    }
    payload.update(extra)
    return payload


def emit(ok, status=None, errorCode=None, **kw) -> NoReturn:
    """Emit exactly one JSON object on stdout and exit (0 ok / 2 not ok).

    This function ALWAYS exits the process — callers must not return after it.
    (Annotated @NoReturn so static analyzers model the process exit.)
    """
    payload = result_payload(ok, status=status, errorCode=errorCode, **kw)
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    sys.exit(0 if ok else 2)


def parse_driver_output(stdout_text):
    """Parse the single JSON object a vfp_driver.py subcommand emits.

    Returns the dict, or None when stdout is not a single JSON object.
    """
    text = (stdout_text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        # Tolerate stray log lines: take the LAST line that parses as JSON.
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                return obj if isinstance(obj, dict) else None
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Process runner (PID-scoped cleanup only)
# ---------------------------------------------------------------------------

def _terminate_pid(pid):
    """Terminate a specific process by PID. Never a process *name*.

    Windows: TerminateProcess via ctypes. POSIX: SIGKILL via os.kill.
    Returns True if the termination call succeeded (the process may have
    already exited — that is still success).
    """
    try:
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.OpenProcess(0x0001  # PROCESS_TERMINATE
                                          | 0x0400,  # PROCESS_QUERY_INFORMATION
                                          False, int(pid))
            if not handle:
                return False
            try:
                return bool(kernel32.TerminateProcess(handle, 1))
            finally:
                kernel32.CloseHandle(handle)
        else:
            os.kill(int(pid), 9)
            return True
    except Exception:
        return False


def _decode(b):
    return (b or b"").decode("cp1252", "replace")


def run_process(cmd, timeout, cwd=None):
    """Run a command, capture stdout/stderr, enforce a timeout.

    Timeout handling: only the child process (and its direct children via the
    OS job when available) is terminated by PID. The toolchain never kills
    vfp9.exe by image name — other users' Visual FoxPro sessions must survive.

    Returns:
        {"stdout": str, "stderr": str, "code": int, "timeout": bool}
        code == -1  → could not start the process
        code == -2  → timed out (child terminated by PID, if possible)
    """
    try:
        p = subprocess.Popen(cmd, cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (FileNotFoundError, OSError) as e:
        return {"stdout": "", "stderr": "exec not found: %s" % e,
                "code": -1, "timeout": False}
    try:
        outb, errb = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # PID-scoped kill of the child we own (cscript / vfp9.exe COM host it
        # spawned dies with the COM client in the normal case; if a VFP9 host
        # legitimately outlives it, we MUST NOT kill arbitrary vfp9.exe).
        if p.poll() is None:
            _terminate_pid(p.pid)
            try:
                p.wait(timeout=10)
            except Exception:
                pass
        # Drain pipes so a stuck child cannot wedge us.
        try:
            outb = p.stdout.read() if p.stdout else b""
        except Exception:
            outb = b""
        try:
            errb = p.stderr.read() if p.stderr else b""
        except Exception:
            errb = b""
        msg = ("TIMEOUT after %ss. The toolchain only terminates the child "
               "process it spawned (PID %s). If a Visual FoxPro COM host "
               "remains, it may belong to ANOTHER user/session: inspect "
               "manually (Task Manager → vfp9.exe, verify ownership) and "
               "retry. errorCode=VFP9_TIMEOUT" % (timeout, p.pid))
        return {"stdout": _decode(outb), "stderr": msg, "code": -2, "timeout": True}
    return {"stdout": _decode(outb), "stderr": _decode(errb),
            "code": p.returncode, "timeout": False}
