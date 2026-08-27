# -*- coding: utf-8 -*-
"""
service.py - the transport-neutral Python Core Service.

Public surface (Phase 1):

    from vfp_toolchain.service import VFPToolchainService
    service = VFPToolchainService()
    result = service.capabilities()           # OperationResult
    result = service.detect_project(path)     # OperationResult
    result = service.anonymization_status()   # OperationResult (read-only)

Rules:
  * no global singleton — each transport (CLI/OpenCode/future MCP) may create
    its own instance (future MCP needs per-project/session state),
  * every method returns an OperationResult; the service never prints and
    never calls sys.exit (that is the CLI adapter's job),
  * operations declare their capability classes from the single model,
  * source projects are immutable: PURE_READ operations never write.
"""

import os
import platform

from . import config
from .capabilities import (
    BACKEND_DBF_ANONYMIZER,
    BACKEND_PURE_PYTHON,
    OPERATION_CAPABILITIES,
    Capability,
)
from .errors import (
    EC_ANON_DICTIONARY_SENSITIVE,
    EC_ANONYMIZER_NOT_AVAILABLE,
    EC_CDX_REBUILD_REQUIRES_VFP9,
    EC_CONFIG_ERROR,
    EC_DEPENDENCY_NOT_AVAILABLE,
    EC_DEPENDENCY_PARTIAL,
    EC_DEPENDENCY_VERSION_MISMATCH,
    EC_FOXBIN2PRG_NOT_AVAILABLE,
    EC_KNOWLEDGE_INCOMPLETE,
    EC_VFP9_NOT_INSTALLED,
)
from .models import OperationResult

_TOOLCHAIN_VERSION = "0.3.0"


class VFPToolchainService(object):
    """Transport-neutral service over the VFP9 SP2 toolchain backends."""

    def __init__(self, root=None):
        """Create a service instance.

        root (optional) overrides the repository root for tests/isolation.
        No I/O, no VFP, no network at construction time.
        """
        self._root = root  # reserved for per-project/session state (future MCP)

    # -- capability discovery (PURE_READ, no VFP launch) --------------------

    def capabilities(self):
        """vfp_capabilities — fast, PURE_READ capability discovery.

        Must work on a machine without VFP9, FoxBin2Prg, COM, OpenCode or
        Bun. Deliberately does NOT launch VFP or run verno (exact version
        verification is a separate, later operation).

        Semantics contract:
          errors  = real execution failures of the discovery operation itself
                    (e.g. corrupt config.json, unverifiable vendored pins);
          warnings = limited / optionally-missing capabilities (VFP9 absent,
                    FoxBin2Prg not configured, anonymizer unavailable, ...);
          data    = the raw state of each component.
        An optional backend being absent on a PURE_READ host is a warning,
        never an error.
        """
        requires = list(OPERATION_CAPABILITIES.get("vfp_capabilities",
                                                   (Capability.PURE_READ.value,)))
        data = {}
        warnings = []
        errors = []

        # Load config once; a corrupt file is a real discovery problem ->
        # PARTIAL. A missing file is legitimate on a bare host (not an error).
        cfg = config.load_config(self._root)
        cfg_error = config.config_error(self._root)
        if cfg_error:
            errors.append(EC_CONFIG_ERROR + ": " + cfg_error)

        data["target"] = cfg.get("target", {}).get("dialect",
                             "microsoft.visual-foxpro.9.0.sp2")
        data["platform"] = {
            "os": os.name,
            "pythonVersion": platform.python_version(),
        }
        data["mcp"] = {"implemented": False}  # README/config contract

        # VFP9 (cheap existence checks only) — optional for PURE_READ.
        from .backends import VFP9Backend
        v9 = VFP9Backend(root=self._root).status()
        v9_exists = bool(v9.get("executableExists", False))
        data["vfp9"] = {
            "configured": v9.get("configured", False),
            "executableExists": v9_exists,
            "versionVerified": False,
        }
        if not v9_exists:
            warnings.append(EC_VFP9_NOT_INSTALLED +
                            ": VFP9 not installed — VFP_READ_ENHANCED and "
                            "workspace/build modes unavailable on this host")

        # FoxBin2Prg (EXTERNAL_CONFIGURED) — prerequisite for BIN2PRG
        # conversion operations only, NOT for VFP_READ_ENHANCED in general.
        from .backends import FoxBin2PrgBackend
        fb = FoxBin2PrgBackend(root=self._root).status()
        fb_program = bool(fb.get("programExists", False))
        data["foxbin2prg"] = {
            "configured": fb.get("configured", False),
            "programExists": fb_program,
            "available": fb_program and v9_exists,  # conversion needs VFP9 too
            "usableForConversion": fb_program and v9_exists,
            "vendored": fb.get("vendored", False),
            "mode": fb.get("mode", "EXTERNAL_CONFIGURED"),
        }
        if not fb_program:
            warnings.append(EC_FOXBIN2PRG_NOT_AVAILABLE +
                            ": set VFP_FOXBIN2PRG_DIR to a FoxBin2Prg "
                            "installation (BIN2PRG conversion unavailable)")

        # dbfbridge (VENDORED)
        from .backends import DBFBridgeBackend
        db = DBFBridgeBackend(root=self._root).status()
        data["dbfbridge"] = {
            "available": db.get("available", False),
            "vendored": db.get("vendored", False),
            "version": db.get("version"),
            "pinVerified": db.get("pinVerified", False),
            "moduleOriginVerified": db.get("moduleOriginVerified", False),
        }
        if not db.get("available", False):
            if not db.get("pinVerified", False):
                errors.append(EC_DEPENDENCY_VERSION_MISMATCH +
                              ": dbfbridge vendored pin does not match the "
                              "expected upstream commit")
            else:
                errors.append(EC_DEPENDENCY_NOT_AVAILABLE +
                              ": dbfbridge snapshot unavailable")

        # DBF_Anonymizer (VENDORED, status-only in this phase)
        from .backends import DBFAnonymizerBackend
        an = DBFAnonymizerBackend(root=self._root).status()
        data["dbfAnonymizer"] = {
            "available": an.get("available", False),
            "vendored": an.get("vendored", False),
            "version": an.get("version"),
            "pinVerified": an.get("pinVerified", False),
            "moduleOriginVerified": an.get("moduleOriginVerified", False),
            "dbfbridgeCompatible": an.get("dbfbridgeCompatible", False),
        }
        if not an.get("available", False):
            errors.append(EC_ANONYMIZER_NOT_AVAILABLE +
                          ": vendored snapshot unavailable (pin, version or "
                          "dbfbridge compatibility not verified)")

        # Knowledge (offline contract)
        k = cfg.get("knowledge") or {}
        data["knowledge"] = {
            "offlineRequired": bool(k.get("offlineRequired", True)),
            "status": k.get("knowledgeStatus",
                            "DOMAIN_READY_EXACT_LANGUAGE_CATALOG_INCOMPLETE"),
        }
        if "INCOMPLETE" in str(data["knowledge"].get("status", "")).upper():
            warnings.append(EC_KNOWLEDGE_INCOMPLETE + ": "
                            + str(data["knowledge"].get("status")))

        # Derived mode availability.
        # vfpEnhancedRead (VFP_READ_ENHANCED) == VFP9 runtime present. It does
        # NOT depend on FoxBin2Prg: runtime inventory, SYS(3054) profiling and
        # snippet validation need only the VFP9 runtime.
        modes = {
            "pureRead": True,
            "pureWriteCopy": bool(db.get("available", False)),
            "vfpEnhancedRead": v9_exists,
            "workspaceWrite": False,
            "buildValidate": False,
        }
        data["modes"] = modes
        data["backendAvailability"] = {
            "PURE_PYTHON": True,
            "DBFBRIDGE": bool(db.get("available", False)),
            "DBF_ANONYMIZER": bool(an.get("available", False)),
            "FOXBIN2PRG": bool(fb_program and v9_exists),
            "VFP9_RUNTIME": v9_exists,
        }

        metadata = {"version": _TOOLCHAIN_VERSION}  # type: dict
        metadata["modesReason"] = {
            "workspaceWrite": "not yet exposed through the Core Service "
                              "(legacy refactor plane exists but is not "
                              "routed here yet)",
            "buildValidate": "not yet exposed through the Core Service "
                             "(legacy compile/round-trip plane exists but "
                             "is not routed here yet)",
        }

        # Discovery that completed with only optional backends missing is a
        # PASS. A real discovery failure (config error / unverifiable pins)
        # is a controlled PARTIAL with an explicit domain code.
        if errors:
            return OperationResult.partial(
                EC_DEPENDENCY_PARTIAL,
                operation="vfp_capabilities", requires=requires,
                backend=BACKEND_PURE_PYTHON,
                data=data, warnings=warnings, errors=errors,
                metadata=metadata,
            )
        return OperationResult.success(
            operation="vfp_capabilities", requires=requires,
            backend=BACKEND_PURE_PYTHON,
            data=data, warnings=warnings, metadata=metadata,
        )

    # -- project detection (PURE_READ) --------------------------------------

    def detect_project(self, directory):
        """vfp_detect — VFP artifact detection (PURE_READ, no VFP).

        Single source of truth for the walk/extension/exclude logic
        (replaces the recursive walk previously duplicated in tools/vfp.ts).
        Never writes to the source tree.
        """
        requires = list(OPERATION_CAPABILITIES.get("vfp_detect",
                                                   (Capability.PURE_READ.value,)))
        from .backends import PurePythonBackend
        data, warnings = PurePythonBackend().detect_project(directory)
        if data is None:
            return OperationResult.failure(
                EC_DEPENDENCY_NOT_AVAILABLE,
                operation="vfp_detect", requires=requires,
                backend=BACKEND_PURE_PYTHON,
                stderr="; ".join(warnings) if warnings else "directory not found",
                errors=list(warnings),
            )
        return OperationResult.success(
            operation="vfp_detect", requires=requires,
            backend=BACKEND_PURE_PYTHON,
            data=data, warnings=warnings,
            metadata={"version": _TOOLCHAIN_VERSION},
        )

    def artifact_inventory(self, directory):
        """Grouped artifact inventory (PURE_READ, wraps PurePythonBackend)."""
        requires = [Capability.PURE_READ.value]
        from .backends import PurePythonBackend
        data, warnings = PurePythonBackend().artifact_inventory(directory)
        if data is None:
            return OperationResult.failure(
                "MISSING_FILE", operation="vfp_artifact_inventory",
                requires=requires, backend=BACKEND_PURE_PYTHON,
                stderr="; ".join(warnings) if warnings else "no data",
                errors=list(warnings),
            )
        return OperationResult.success(
            operation="vfp_artifact_inventory", requires=requires,
            backend=BACKEND_PURE_PYTHON, data=data, warnings=warnings,
            metadata={"version": _TOOLCHAIN_VERSION},
        )

    # -- anonymization status (read-only, NOT a mutating tool) --------------

    def anonymization_status(self):
        """vfp_anonymization_status — read-only subsystem status.

        Does NOT anonymize, recover, create dictionaries or modify DBF.
        Reports: availability, version, vendored commit, dbfbridge
        compatibility, recovery capability, privacy/CDX constraints.
        """
        requires = [Capability.PURE_READ.value]
        from .backends import DBFAnonymizerBackend
        be = DBFAnonymizerBackend(root=self._root)
        meta = be.status()
        warnings = []
        errors = []

        warnings.append(
            EC_ANON_DICTIONARY_SENSITIVE + ": dictionary.sqlite3 is SENSITIVE — "
            "never commit, never log original values, store only under "
            "configured sensitive roots")
        warnings.append(
            EC_CDX_REBUILD_REQUIRES_VFP9 + ": structural CDX output after "
            "changed indexed values requires VFP9 REINDEX on the copy")
        error_code = EC_ANONYMIZER_NOT_AVAILABLE
        if not meta.get("dbfbridgeCompatible", False):
            error_code = EC_DEPENDENCY_VERSION_MISMATCH
            errors.append("dbfbridge snapshot pin mismatch — anonymizer "
                          "requires dbfbridge @ "
                          + meta.get("dbfbridgeRequiredCommit", "pinned commit"))
        elif not meta.get("pinVerified", False):
            error_code = EC_DEPENDENCY_VERSION_MISMATCH
            errors.append("anonymizer VERSION.txt commit does not match the "
                          "expected pinned commit")
        if not meta.get("available", False):
            if meta.get("error"):
                errors.append(str(meta["error"]))

        data = {
            "available": bool(meta.get("available", False)),
            "version": meta.get("version"),
            "vendored": bool(meta.get("vendored", False)),
            "upstreamCommit": meta.get("upstreamCommit"),
            "expectedUpstreamCommit": meta.get("expectedUpstreamCommit"),
            "dbfbridgeCompatible": bool(meta.get("dbfbridgeCompatible", False)),
            "recoveryCapabilityPresent": bool(meta.get("recoveryCapabilityPresent", False)),
            "structuralCdxRequiresVfp9": True,
            "dictionarySensitive": True,
            "productionAnonymizationExposed": False,  # next phase
            "publicApi": meta.get("publicApi"),
        }
        # An availability query that completed and reports the subsystem as
        # unavailable is a controlled PARTIAL (explained, domain-coded) —
        # not an unexplained FAIL and never UNEXPECTED_ERROR.
        if data["available"]:
            return OperationResult.success(
                operation="vfp_anonymization_status",
                requires=requires, backend=BACKEND_DBF_ANONYMIZER,
                data=data, warnings=warnings,
                metadata={"version": _TOOLCHAIN_VERSION},
            )
        return OperationResult.partial(
            error_code,
            operation="vfp_anonymization_status",
            requires=requires, backend=BACKEND_DBF_ANONYMIZER,
            data=data, warnings=warnings, errors=errors,
            metadata={"version": _TOOLCHAIN_VERSION},
        )


__all__ = ["VFPToolchainService"]
