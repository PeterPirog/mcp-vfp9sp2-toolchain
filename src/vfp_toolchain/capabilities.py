# -*- coding: utf-8 -*-
"""Truthful capability discovery.

REQ-G00-008 / REQ-P01-005 / REQ-P01-012: capability discovery MUST be
side-effect-free and MUST expose only truthful state.  At the bootstrap
foundation no domain capability is implemented; every entry reports
``NOT_IMPLEMENTED`` with the canonical milestone that will activate it.
No placeholder success is possible from this module.
"""

from __future__ import annotations

from typing import Any

CATALOG_VERSION = 1

# Requirement state vocabulary (REQ-AUTO-040).
STATE_VOCABULARY = (
    "UNASSESSED",
    "PLANNED",
    "NOT_IMPLEMENTED",
    "PARTIAL",
    "BLOCKED",
    "PASS",
    "NOT_APPLICABLE",
)

# Capability classes (REQ-P01-006) — closed vocabulary.
CAPABILITY_CLASSES = (
    "PURE_READ",
    "PURE_WRITE_COPY",
    "VFP_READ_ENHANCED",
    "VFP_WRITE_WORKSPACE",
    "VFP_BUILD_VALIDATE",
    "PRIVACY_SENSITIVE",
    "SOURCE_PROMOTION",
)

# Canonical milestone activation map for declared domain capabilities.
# `milestone` is the first canonical milestone whose release closure makes the
# capability usable; availability stays false until that milestone's release
# gate passes.
_DOMAIN_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {"id": "core.service", "title": "Transport-neutral Core Service", "milestone": "P01_CORE"},
    {"id": "core.jobs", "title": "Long-operation job management", "milestone": "P01_CORE"},
    {"id": "platform.windows_policy", "title": "Windows path/source policy", "milestone": "P02_SECURITY"},
    {"id": "platform.execution_isolation", "title": "Subprocess/execution isolation", "milestone": "P02_SECURITY"},
    {"id": "mcp.shell", "title": "Minimal MCP v2 server shell", "milestone": "P01_MCP_MIN"},
    {"id": "knowledge.vfp9sp2_help", "title": "VFPX VFP9 SP2 offline Help search", "milestone": "P03_KNOWLEDGE"},
    {"id": "data.dbf_schema", "title": "DBF schema inspection via dbfbridge", "milestone": "P04_DATA"},
    {"id": "data.dbf_rows_memo", "title": "DBF/FPT row and Memo reading", "milestone": "P04_DATA"},
    {"id": "data.datasets_lineage", "title": "Original/anonymized dataset roles and lineage", "milestone": "P04_DATA"},
    {"id": "data.value_search", "title": "Bounded value search", "milestone": "P04_DATA"},
    {"id": "semantic.graph", "title": "Whole-application semantic graph", "milestone": "P05_SEMANTIC_GRAPH"},
    {"id": "vfp.foxbin_bridge", "title": "FoxBin2Prg analysis bridge", "milestone": "P06_FOXBIN_ANALYSIS"},
    {"id": "forms.analysis", "title": "Deep form analysis", "milestone": "P07_FORMS_CLASSES"},
    {"id": "classes.analysis", "title": "Deep class analysis", "milestone": "P07_FORMS_CLASSES"},
    {"id": "dbc.model", "title": "DBC/views/unified data model", "milestone": "P08_DBC_MODEL"},
    {"id": "reasoning.questions", "title": "Structured cross-domain questions", "milestone": "P09_REASONING"},
    {"id": "performance.indexes", "title": "CDX/IDX and Rushmore evidence", "milestone": "P10_OPTIMIZATION"},
    {"id": "vfp.runtime_execution", "title": "Interactive VFP runtime execution", "milestone": "P10_OPTIMIZATION"},
    {"id": "vfp.sys3054", "title": "SYS(3054) Rushmore plan analysis", "milestone": "P10_OPTIMIZATION"},
    {"id": "refactor.workspace", "title": "Controlled refactoring with round-trip validation", "milestone": "P11_REFACTOR"},
    {"id": "vfp.compile_build", "title": "VFP9 SP2 compile/build validation", "milestone": "P11_REFACTOR"},
    {"id": "privacy.anonymization", "title": "DBF_Anonymizer integration and lineage", "milestone": "P12_PRIVACY"},
    {"id": "relational.target_model", "title": "Canonical relational target model", "milestone": "P13_RELATIONAL_MODEL"},
    {"id": "postgres.schema_design", "title": "PostgreSQL schema design (DDL)", "milestone": "P13_RELATIONAL_MODEL"},
    {"id": "translation.vfp_sql", "title": "VFP SQL/xBase translation", "milestone": "P14_TRANSLATION"},
    {"id": "postgres.shadow_migration", "title": "PostgreSQL shadow migration and parity", "milestone": "P15_SHADOW_MIGRATION"},
    {"id": "postgres.transition", "title": "VFP-to-PostgreSQL transition/cutover", "milestone": "P16_TRANSITION"},
    {"id": "mcp.stabilized_surface", "title": "Stabilized MCP 2026-07-28 surface", "milestone": "P17_MCP_STABILIZATION"},
    {"id": "release.final_acceptance", "title": "Complete-system acceptance evidence", "milestone": "P18_FINAL"},
)


def discover() -> dict[str, Any]:
    """Return the truthful capability state. Pure function: no I/O, no network,
    no subprocess, no COM, no filesystem access (REQ-P01-005)."""
    capabilities = [
        {
            "id": entry["id"],
            "title": entry["title"],
            "available": False,
            "state": "NOT_IMPLEMENTED",
            "activation_milestone": entry["milestone"],
            "capability_classes": [],
        }
        for entry in _DOMAIN_CAPABILITIES
    ]
    return {
        "catalog_version": CATALOG_VERSION,
        "state_vocabulary": list(STATE_VOCABULARY),
        "capability_classes": list(CAPABILITY_CLASSES),
        "capabilities": capabilities,
        "implemented_count": 0,
        "declared_count": len(capabilities),
        "note": (
            "Bootstrap-only build: every declared domain capability is "
            "truthfully NOT_IMPLEMENTED. No placeholder success is exposed."
        ),
    }


def is_implemented(capability_id: str) -> bool:
    """Truthful implemented check (always False at the bootstrap foundation)."""
    for entry in _DOMAIN_CAPABILITIES:
        if entry["id"] == capability_id:
            return False
    return False