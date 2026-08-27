# -*- coding: utf-8 -*-
"""
models.py - transport-neutral result model for the VFP9 SP2 Core Service.

One shared result envelope for every operation, regardless of transport
(CLI today, OpenCode today, MCP later).

Backward compatibility: the base fields (ok, status, errorCode, rc, version,
stdout, stderr, data) exactly match vfp_protocol.result_payload, so existing
consumers keep working. The Core Service adds new optional fields
(operation, requires, backend, sourceModified, warnings, errors, metadata)
without changing the meaning of PASS / PARTIAL / FAIL.

The service NEVER prints and NEVER calls sys.exit. Transport adapters
(vfp_driver.py / tools/vfp.ts) serialize to JSON and set exit codes.
"""

from typing import Any, Dict, List, Optional

# Status vocabulary — identical to vfp_protocol (single meaning, do not change).
STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"

STATUS_VALUES = (STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL)


class OperationResult(object):
    """Single JSON-serializable result envelope for a Core Service operation."""

    def __init__(self,
                 ok: bool = True,
                 status: Optional[str] = None,
                 errorCode: Optional[str] = None,
                 rc: Optional[int] = None,
                 version: Optional[str] = None,
                 stdout: str = "",
                 stderr: str = "",
                 data: Optional[Dict[str, Any]] = None,
                 operation: Optional[str] = None,
                 requires: Optional[List[str]] = None,
                 backend: Optional[str] = None,
                 sourceModified: bool = False,
                 warnings: Optional[List[str]] = None,
                 errors: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        if status is None:
            status = STATUS_PASS if ok else STATUS_FAIL
        if status not in STATUS_VALUES:
            raise ValueError("invalid status: %r" % (status,))
        if not ok and errorCode is None:
            errorCode = "UNEXPECTED_ERROR"
        self.ok = bool(ok)
        self.status = status
        self.errorCode = errorCode
        self.rc = rc
        self.version = version
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        self.data = data if data is not None else {}
        self.operation = operation
        self.requires = list(requires) if requires else []
        self.backend = backend
        self.sourceModified = bool(sourceModified)
        self.warnings = list(warnings) if warnings else []
        self.errors = list(errors) if errors else []
        self.metadata = metadata if metadata is not None else {}

    # -- factories ----------------------------------------------------------

    @classmethod
    def success(cls, operation=None, requires=None, backend=None,
                data=None, warnings=None, metadata=None, **base):
        return cls(ok=True, status=STATUS_PASS, errorCode=None,
                   operation=operation, requires=requires, backend=backend,
                   data=data, warnings=warnings, metadata=metadata, **base)

    @classmethod
    def failure(cls, errorCode, operation=None, requires=None, backend=None,
                stderr="", data=None, warnings=None, errors=None,
                metadata=None, status=None, **base):
        if status is None:
            status = STATUS_FAIL
        errs = list(errors or [])
        if stderr and stderr not in errs:
            errs.append(stderr)
        return cls(ok=False, status=status, errorCode=errorCode,
                   stderr=stderr, operation=operation, requires=requires,
                   backend=backend, data=data, warnings=warnings,
                   errors=errs, metadata=metadata, **base)

    @classmethod
    def partial(cls, operation=None, requires=None, backend=None,
                data=None, warnings=None, errors=None, metadata=None, **base):
        return cls(ok=False, status=STATUS_PARTIAL, errorCode=None,
                   operation=operation, requires=requires, backend=backend,
                   data=data, warnings=warnings, errors=errors,
                   metadata=metadata, **base)

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable dict in stable field order (legacy fields first)."""
        return {
            "ok": self.ok,
            "status": self.status,
            "errorCode": self.errorCode,
            "rc": self.rc,
            "version": self.version,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "data": self.data,
            "operation": self.operation,
            "requires": self.requires,
            "backend": self.backend,
            "sourceModified": self.sourceModified,
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    def __repr__(self):  # pragma: no cover - debug aid
        return ("OperationResult(ok=%s status=%s errorCode=%s operation=%s)"
                % (self.ok, self.status, self.errorCode, self.operation))


__all__ = [
    "STATUS_PASS", "STATUS_PARTIAL", "STATUS_FAIL", "STATUS_VALUES",
    "OperationResult",
]
