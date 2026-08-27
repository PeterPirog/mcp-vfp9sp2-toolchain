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
    EC_DEPENDENCY_NOT_AVAILABLE,
    EC_FOXBIN2PRG_NOT_AVAILABLE,
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
        """
        requires = list(OPERATION_CAPABILITIES.get("vfp_capabilities",
                                                   (Capability.PURE_READ.value,)))
        data = {}
        warnings = []
        errors = []

        data["target"] = config.target_dialect()
        data["platform"] = {
            "os": os.name,
            "pythonVersion": platform.python_version(),
        }
        data["mcp"] = {"implemented": False}  # README/config contract

        # VFP9 (cheap existence checks only)
        from .backends import VFP9Backend
        v9 = VFP9Backend().status()
        data["vfp9"] = {
            "configured": v9.get("configured", False),
            "executableExists": v9.get("executableExists", False),
            "versionVerified": False,
        }
        if v9.get("configured") and not v9.get("executableExists"):
            errors.append(EC_VFP9_NOT_INSTALLED + ": configured path does not exist")

        # FoxBin2Prg (EXTERNAL_CONFIGURED)
        from .backends import FoxBin2PrgBackend
        fb = FoxBin2PrgBackend().status()
        data["foxbin2prg"] = {
            "configured": fb.get("configured", False),
            "available": fb.get("programExists", False),
            "vendored": fb.get("vendored", False),
            "mode": fb.get("mode", "EXTERNAL_CONFIGURED"),
        }
        if not fb.get("programExists", False):
            warnings.append(EC_FOXBIN2PRG_NOT_AVAILABLE +
                            ": set VFP_FOXBIN2PRG_DIR to a FoxBin2Prg installation")

        # dbfbridge (VENDORED)
        from .backends import DBFBridgeBackend
        db = DBFBridgeBackend().status()
        data["dbfbridge"] = {
            "available": db.get("available", False),
            "vendored": db.get("vendored", False),
            "version": db.get("version"),
        }
        if not db.get("available", False):
            errors.append(EC_DEPENDENCY_NOT_AVAILABLE + ": dbfbridge snapshot unavailable")

        # DBF_Anonymizer (VENDORED, status-only in this phase)
        from .backends import DBFAnonymizerBackend
        an = DBFAnonymizerBackend().status()
        data["dbfAnonymizer"] = {
            "available": an.get("available", False),
            "vendored": an.get("vendored", False),
            "version": an.get("version"),
        }
        if not an.get("available", False):
            errors.append(EC_ANONYMIZER_NOT_AVAILABLE +
                          ": vendored snapshot unavailable or version mismatch")

        # Knowledge (offline contract)
        cfg = config.load_config()
        k = cfg.get("knowledge") or {}
        data["knowledge"] = {
            "offlineRequired": bool(k.get("offlineRequired", True)),
            "status": k.get("knowledgeStatus",
                            "DOMAIN_READY_EXACT_LANGUAGE_CATALOG_INCOMPLETE"),
        }
        if "INCOMPLETE" in str(data["knowledge"].get("status", "")).upper():
            warnings.append("knowledge gate is NOT complete: "
                            + str(data["knowledge"].get("status")))

        # Derived mode availability (single source: backends above)
        modes = {
            "pureRead": True,
            "pureWriteCopy": bool(db.get("available", False)),
            "vfpEnhancedRead": bool(v9.get("executableExists", False)
                                    and fb.get("programExists", False)),
            "workspaceWrite": False,   # roadmap (write plane not yet exposed)
            "buildValidate": False,    # roadmap
        }
        data["modes"] = modes

        ok = modes["pureRead"]
        return OperationResult(
            ok=ok,
            status="PASS" if ok else "FAIL",
            errorCode=None,
            operation="vfp_capabilities",
            requires=requires,
            backend=BACKEND_PURE_PYTHON,
            sourceModified=False,
            data=data,
            warnings=warnings,
            errors=errors,
            metadata={"version": _TOOLCHAIN_VERSION},
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
        be = DBFAnonymizerBackend()
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
        if not meta.get("dbfbridgeCompatible", False):
            errors.append("dbfbridge snapshot pin mismatch — anonymizer "
                          "requires dbfbridge @ "
                          + meta.get("dbfbridgeRequiredCommit", "pinned commit"))
        if not meta.get("available", False):
            errors.append(meta.get("error") or EC_ANONYMIZER_NOT_AVAILABLE)

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
        return OperationResult(
            ok=data["available"],
            status="PASS" if data["available"] else "FAIL",
            errorCode=None if data["available"] else EC_ANONYMIZER_NOT_AVAILABLE,
            operation="vfp_anonymization_status",
            requires=requires,
            backend=BACKEND_DBF_ANONYMIZER,
            sourceModified=False,
            data=data,
            warnings=warnings,
            errors=errors,
            metadata={"version": _TOOLCHAIN_VERSION},
        )


__all__ = ["VFPToolchainService"]
