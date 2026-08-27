# -*- coding: utf-8 -*-
"""
capabilities.py - runtime capability model (one truth).

The capability CLASSES come from docs/mcp_capability_model.json — this
module mirrors that file as a Python enum. Do not create a second,
competing list of capability classes: the JSON model is the contract and
this enum must match it exactly.

Importing this module has no side effects and requires no VFP.
"""

import enum
import json
import os


class Capability(str, enum.Enum):
    """Runtime/safety capability classes (values == docs/mcp_capability_model.json)."""

    PURE_READ = "PURE_READ"
    PURE_WRITE_COPY = "PURE_WRITE_COPY"
    VFP_READ_ENHANCED = "VFP_READ_ENHANCED"
    VFP_WRITE_WORKSPACE = "VFP_WRITE_WORKSPACE"
    VFP_BUILD_VALIDATE = "VFP_BUILD_VALIDATE"
    PRIVACY_SENSITIVE = "PRIVACY_SENSITIVE"


# Capability classes that never require Visual FoxPro.
NO_VFP_REQUIRED = (Capability.PURE_READ, Capability.PURE_WRITE_COPY)

# Capability classes that require an installed VFP9 SP2 backend.
VFP_REQUIRED = (
    Capability.VFP_READ_ENHANCED,
    Capability.VFP_WRITE_WORKSPACE,
    Capability.VFP_BUILD_VALIDATE,
)

# Operations and their required capabilities (mirrors the JSON model).
OPERATION_CAPABILITIES = {
    "vfp_capabilities": ("PURE_READ",),
    "vfp_detect": ("PURE_READ",),
    "vfp_snapshot": ("PURE_READ",),
    "vfp_read_artifact": ("PURE_READ",),
    "vfp_read_table_schema": ("PURE_READ",),
    "vfp_read_table_data": ("PURE_READ",),
    "vfp_find_symbol": ("PURE_READ",),
    "vfp_find_references": ("PURE_READ",),
    "vfp_audit": ("PURE_READ",),
    "vfp_analyze_indexes": ("PURE_READ",),
    "vfp_language_lookup": ("PURE_READ",),
    "vfp_known_issue_lookup": ("PURE_READ",),
    "vfp_anonymization_status": ("PURE_READ",),
    "vfp_export_bin2prg": ("VFP_READ_ENHANCED",),
    "vfp_runtime_inventory": ("VFP_READ_ENHANCED",),
    "vfp_profile_rushmore": ("VFP_READ_ENHANCED",),
    "vfp_validate_snippet": ("VFP_READ_ENHANCED",),
    "vfp_anonymize_no_structural_cdx": ("PURE_WRITE_COPY", "PRIVACY_SENSITIVE"),
    "vfp_anonymize_structural_cdx": ("PURE_WRITE_COPY", "PRIVACY_SENSITIVE", "VFP_WRITE_WORKSPACE"),
    "vfp_anonymize_self_test": ("PRIVACY_SENSITIVE",),
    "vfp_recover_data": ("PRIVACY_SENSITIVE",),
    "vfp_create_refactor_workspace": ("VFP_WRITE_WORKSPACE",),
    "vfp_apply_refactor_plan": ("VFP_WRITE_WORKSPACE",),
    "vfp_validate_form": ("VFP_BUILD_VALIDATE",),
    "vfp_build_project": ("VFP_BUILD_VALIDATE",),
}

# Backend names used in OperationResult.backend (stable strings).
BACKEND_PURE_PYTHON = "PURE_PYTHON"
BACKEND_DBFBRIDGE = "DBFBRIDGE"
BACKEND_DBF_ANONYMIZER = "DBF_ANONYMIZER"
BACKEND_FOXBIN2PRG = "FOXBIN2PRG"
BACKEND_VFP9_RUNTIME = "VFP9_RUNTIME"
BACKEND_KNOWLEDGE = "KNOWLEDGE"


def _capability_model_path():
    """Path to docs/mcp_capability_model.json relative to the repository root."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "docs", "mcp_capability_model.json")


def verify_model_consistency(model_path=None):
    """Verify the Python Capability enum matches the JSON capability model.

    Returns a list of mismatch strings (empty when consistent).
    The JSON model is the contract: the enum must mirror it exactly.
    No network, no VFP.
    """
    problems = []
    path = model_path or _capability_model_path()
    if not os.path.isfile(path):
        return ["capability model file not found: %s" % path]
    try:
        with open(path, "r", encoding="utf-8") as f:
            model = json.load(f)
    except (OSError, ValueError):
        return ["capability model unreadable: %s" % path]
    json_classes = set((model.get("capabilityClasses") or {}).keys())
    enum_values = set(c.value for c in Capability)
    for cls in sorted(json_classes - enum_values):
        problems.append("enum missing class: %s" % cls)
    for cls in sorted(enum_values - json_classes):
        problems.append("enum has extra class not in model: %s" % cls)
    for op, requires in (model.get("operations") or {}).items():
        if op in OPERATION_CAPABILITIES:
            if tuple(OPERATION_CAPABILITIES[op]) != tuple(requires):
                problems.append("operation %s requires mismatch" % op)
        else:
            problems.append("operation map missing: %s" % op)
    for op in OPERATION_CAPABILITIES:
        if op not in (model.get("operations") or {}):
            # extra entries in the Python map are allowed (forward-compat),
            # but the core set must be present in the model
            pass
    return problems


__all__ = [
    "Capability",
    "NO_VFP_REQUIRED",
    "VFP_REQUIRED",
    "OPERATION_CAPABILITIES",
    "BACKEND_PURE_PYTHON",
    "BACKEND_DBFBRIDGE",
    "BACKEND_DBF_ANONYMIZER",
    "BACKEND_FOXBIN2PRG",
    "BACKEND_VFP9_RUNTIME",
    "BACKEND_KNOWLEDGE",
    "verify_model_consistency",
]
