# -*- coding: utf-8 -*-
"""Typed, machine-readable error vocabulary for the toolchain.

The registry is the single stable error surface shared by the Core Service,
both transport adapters, and the deterministic verifier dispatcher
(REQ-P01-004 foundation state; categories extended as phases activate).
"""

from __future__ import annotations

from typing import Any

REGISTRY_VERSION = 1

# Stable machine-readable error codes. Values are closed; new codes are added
# only with explicit contract evolution.
ERROR_CODES: dict[str, str] = {
    "CAPABILITY_NOT_IMPLEMENTED": "The requested capability exists in the target architecture but is not implemented in this build.",
    "OPERATION_UNKNOWN": "The requested operation is not part of any registered capability.",
    "START_STATE_AMBIGUOUS": "The target repository occupancy is UNKNOWN_NONEMPTY; fail closed until an explicit operator decision.",
    "BOOTSTRAP_REQUIRED": "The repository requires deterministic bootstrap before ordinary implementation.",
    "VERIFIER_PLANNED": "The mapped verifier is PLANNED and cannot produce a PASS result.",
    "VERIFIER_UNKNOWN": "The verifier or requirement ID is unknown to the verification manifest.",
    "VERIFICATION_FAILED": "A deterministic verifier executed and returned a non-PASS result.",
    "SCHEMA_VALIDATION_FAILED": "A JSON Schema document or artifact instance failed validation.",
    "SCHEMA_CAPABILITY_UNAVAILABLE": "JSON Schema validation capability is not available in this interpreter.",
    "SOT_IDENTITY_MISMATCH": "The Source of Truth hash does not match the bound identity.",
    "GENERATION_NOT_DETERMINISTIC": "Regenerated control-plane content differs logically.",
    "DEPENDENCY_ORIGIN_NOT_APPROVED": "Dependency resolution requires an explicitly approved package-index origin.",
    "NO_RUNTIME_NETWORK": "Runtime network access is prohibited by policy.",
    "PATH_POLICY_VIOLATION": "A path access violated the configured Windows path policy.",
    "RESOURCE_LIMIT_EXCEEDED": "A configured resource limit was exceeded.",
    "PROVENANCE_INVALID": "Authoring or run provenance is missing, stale, or inconsistent.",
}


class ToolchainError(Exception):
    """Base class for typed toolchain failures."""

    code = "TOOLCHAIN_ERROR"

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        if code not in ERROR_CODES:
            raise ValueError(f"unknown error code: {code}")
        self.code = code
        self.message = message
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


class CapabilityNotImplementedError(ToolchainError):
    """Truthful refusal for a declared-but-unimplemented capability."""

    code = "CAPABILITY_NOT_IMPLEMENTED"


class OperationUnknownError(ToolchainError):
    code = "OPERATION_UNKNOWN"


class StartStateAmbiguousError(ToolchainError):
    code = "START_STATE_AMBIGUOUS"


class VerificationError(ToolchainError):
    code = "VERIFICATION_FAILED"


class SchemaValidationError(ToolchainError):
    code = "SCHEMA_VALIDATION_FAILED"


class SchemaCapabilityUnavailableError(ToolchainError):
    code = "SCHEMA_CAPABILITY_UNAVAILABLE"


class SotIdentityMismatchError(ToolchainError):
    code = "SOT_IDENTITY_MISMATCH"


class GenerationNotDeterministicError(ToolchainError):
    code = "GENERATION_NOT_DETERMINISTIC"


class DependencyOriginNotApprovedError(ToolchainError):
    code = "DEPENDENCY_ORIGIN_NOT_APPROVED"


class VerifierPlannedError(ToolchainError):
    code = "VERIFIER_PLANNED"


class VerifierUnknownError(ToolchainError):
    code = "VERIFIER_UNKNOWN"