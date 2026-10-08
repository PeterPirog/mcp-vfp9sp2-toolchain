# -*- coding: utf-8 -*-
"""Transport-neutral Core Service boundary (B0 foundation state).

REQ-G00-020 / REQ-P01-001: both console entry points delegate to this one
Core Service; adapters stay thin.  At the bootstrap foundation the Core
exposes only bootstrap-level operations (describe/capabilities) and returns a
typed truthful refusal for every declared domain operation until the owning
milestone activates it.  No fabricated success response is possible.
"""

from __future__ import annotations

from typing import Any

from . import capabilities
from .errors import CapabilityNotImplementedError, OperationUnknownError

CORE_SCHEMA_VERSION = 1

# Operations the Core can already answer truthfully at B0.
_BOOTSTRAP_OPERATIONS = (
    "core.describe",
    "core.capabilities",
)

# Declared domain operation families that stay refused until implemented.
_DECLARED_DOMAIN_OPERATIONS = (
    "project.register",
    "dataset.register",
    "knowledge.search",
    "data.schema_inspect",
    "data.rows_read",
    "data.value_search",
    "semantic.graph_query",
    "forms.analyze",
    "reasoning.question",
    "performance.analyze",
    "refactor.plan",
    "refactor.apply",
    "privacy.anonymize",
    "relational.design",
    "translation.translate",
    "postgres.migrate",
    "postgres.transition_plan",
)


def _envelope(operation: str, status: str, data: Any = None, errors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Bounded common envelope (REQ-P01-003 shape, foundation subset)."""
    return {
        "schema_version": CORE_SCHEMA_VERSION,
        "status": status,
        "operation": operation,
        "capability_classes": [],
        "backend": "bootstrap_foundation",
        "data": data,
        "errors": errors or [],
        "evidence": [],
    }


class CoreService:
    """Single domain owner behind both transport adapters."""

    def __init__(self) -> None:
        self._operations = {op: self._truthful_refusal_factory(op) for op in _DECLARED_DOMAIN_OPERATIONS}

    def describe(self) -> dict[str, Any]:
        return _envelope(
            "core.describe",
            "PASS",
            {
                "product": "mcp-vfp9sp2-toolchain",
                "core_schema_version": CORE_SCHEMA_VERSION,
                "transport_adapters": ["cli", "mcp"],
                "declared_domain_operations": list(_DECLARED_DOMAIN_OPERATIONS),
                "implemented_domain_operations": [],
            },
        )

    def capabilities(self) -> dict[str, Any]:
        return _envelope("core.capabilities", "PASS", capabilities.discover())

    def execute(self, operation: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if operation in _BOOTSTRAP_OPERATIONS:
            if operation == "core.describe":
                return self.describe()
            if operation == "core.capabilities":
                return self.capabilities()
        if operation in self._operations:
            raise CapabilityNotImplementedError(
                "CAPABILITY_NOT_IMPLEMENTED",
                f"Operation {operation!r} is declared but not implemented in this build.",
                {"operation": operation, "truthful_state": "NOT_IMPLEMENTED"},
            )
        raise OperationUnknownError(
            "OPERATION_UNKNOWN",
            f"Operation {operation!r} is not part of any registered capability.",
            {"operation": operation},
        )

    @staticmethod
    def _truthful_refusal_factory(operation: str):  # pragma: no cover - factory
        def _refuse(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
            raise CapabilityNotImplementedError(
                "CAPABILITY_NOT_IMPLEMENTED",
                f"Operation {operation!r} is declared but not implemented in this build.",
                {"operation": operation, "truthful_state": "NOT_IMPLEMENTED"},
            )

        return _refuse