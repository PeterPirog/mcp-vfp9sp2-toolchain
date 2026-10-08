# -*- coding: utf-8 -*-
"""Tool-neutral bootstrap invocation logical object (REQ-G00-039..041).

The invocation is a run-control input, not a time-zero file.  Required
operator fields: ``project_home`` and ``bootstrap_sot_path``.  Optional
fields carry scope/authoring/adapter/routing/authorization/origin/ref/role
bindings.  Path fields are canonicalized before use; the canonical
logical-content hash is independent of transport serialization and is bound
into start-state/preflight/readiness/provenance evidence.  Secrets are
forbidden; machine-specific absolute paths stay in run evidence only, never
inside portable product contract artifacts.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PureWindowsPath
from typing import Any

from ..canonical import canonical_sha256, logical_sha256
from ..errors import ToolchainError

INVOCATION_SCHEMA_VERSION = 1

REQUIRED_FIELDS = ("project_home", "bootstrap_sot_path")

OPTIONAL_FIELDS = (
    "operation_scope",
    "authoring_mode",
    "execution_adapter",
    "autonomous_model_routing_ref",
    "remote_authorization_ref",
    "repository_origin",
    "target_ref",
    "temp_root",
    "venv_root",
    "cache_roots",
    "tool_roots",
)

SCOPES = ("LOCAL_QUALIFICATION", "REMOTE_INTEGRATION", "PUBLICATION")
AUTHORING_MODES = ("MANUAL", "AUTONOMOUS", "HYBRID")
DEFAULT_SCOPE = "LOCAL_QUALIFICATION"
DEFAULT_AUTHORING_MODE = "MANUAL"

PATH_FIELDS = (
    "project_home",
    "bootstrap_sot_path",
    "temp_root",
    "venv_root",
)
PATH_LIST_FIELDS = ("cache_roots", "tool_roots")

_CANONICAL_REPO_CHILD = "mcp-vfp9sp2-toolchain"


class InvocationFieldError(ToolchainError):
    """Raised for omitted required fields or invalid values (fail before mutation)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("START_STATE_AMBIGUOUS", message, details)


def _canonicalize_windows_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvocationFieldError("path fields must be non-empty strings")
    return str(PureWindowsPath(os.path.normcase(value.strip())))


def build_invocation(inputs: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize operator inputs into the effective invocation object."""
    missing = [field for field in REQUIRED_FIELDS if not str(inputs.get(field, "")).strip()]
    if missing:
        raise InvocationFieldError(
            "omitted required bootstrap invocation fields",
            {"missing_required_fields": missing},
        )

    invocation: dict[str, Any] = {
        "invocation_schema_version": INVOCATION_SCHEMA_VERSION,
    }
    for field in PATH_FIELDS:
        if inputs.get(field):
            invocation[field] = _canonicalize_windows_path(str(inputs[field]))
    for field in PATH_LIST_FIELDS:
        values = inputs.get(field) or []
        if not isinstance(values, list):
            raise InvocationFieldError(f"{field} must be a list of paths")
        invocation[field] = [_canonicalize_windows_path(str(v)) for v in values]

    scope = inputs.get("operation_scope") or DEFAULT_SCOPE
    if scope not in SCOPES:
        raise InvocationFieldError("invalid operation_scope", {"operation_scope": scope})
    invocation["operation_scope"] = scope

    authoring = inputs.get("authoring_mode") or DEFAULT_AUTHORING_MODE
    if authoring not in AUTHORING_MODES:
        raise InvocationFieldError("invalid authoring_mode", {"authoring_mode": authoring})
    invocation["authoring_mode"] = authoring

    for passthrough in (
        "execution_adapter",
        "autonomous_model_routing_ref",
        "remote_authorization_ref",
        "repository_origin",
        "target_ref",
    ):
        if inputs.get(passthrough):
            invocation[passthrough] = str(inputs[passthrough])

    invocation["repo_root"] = derive_repo_root(invocation["project_home"])
    invocation["resolved_defaults"] = {
        "operation_scope_default": DEFAULT_SCOPE,
        "authoring_mode_default": DEFAULT_AUTHORING_MODE,
    }
    return invocation


def derive_repo_root(project_home: str) -> str:
    """REQ-G00-026: repo_root is the direct canonical child of project_home."""
    home = PureWindowsPath(_canonicalize_windows_path(project_home))
    return str(home / _CANONICAL_REPO_CHILD)


def invocation_hashes(invocation: dict[str, Any]) -> dict[str, str]:
    """Canonical logical hash plus full logical hash of the invocation object."""
    return {
        "bootstrap_invocation_logical_sha256": logical_sha256(invocation),
        "bootstrap_invocation_canonical_sha256": canonical_sha256(invocation),
    }


def secret_scan(invocation: dict[str, Any]) -> list[str]:
    """Reject secret-shaped values in the invocation (no embedded secrets)."""
    findings: list[str] = []
    secret_pattern = re.compile(
        r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)"
    )
    for field, value in invocation.items():
        if isinstance(value, str) and secret_pattern.search(field):
            findings.append(field)
    return findings