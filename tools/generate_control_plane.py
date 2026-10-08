# -*- coding: utf-8 -*-
"""Deterministic GREENFIELD control-plane generator for mcp-vfp9sp2-toolchain.

Parses the frozen Source of Truth (``spec/SOURCE_OF_TRUTH.md``) and generates
every canonical portable contract artifact required by Rev.35:

    spec/requirements.graph.json
    spec/verification.manifest.json
    spec/compatibility.manifest.json
    spec/acquisition.manifest.json
    spec/dependency-lock.json            (pending state until an approved
                                          dependency origin is authorized)
    spec/threat-model.json
    release-gates/readiness-b0.json
    release-gates/readiness-br0.json
    release-gates/greenfield-scenario.json
    release-gates/release-<version>.json (0.4.0 .. 1.0.0)
    release-gates/index.json

Determinism contract (REQ-PORT-017/018, WP Part R):
  * logical content contains no timestamps, no machine paths, no TEMP dirs;
  * ``generated_at_utc`` is non-authoritative metadata and is excluded from
    every logical hash together with the self-hash field;
  * logical hashes use the RFC 8785-compatible canonical JSON profile in
    ``vfp_toolchain.canonical``;
  * regenerating from the same SOT bytes yields logical identity equality.

The requirement graph implements the corrected canonical milestone semantics
from WP-SOT-REV35-SEMANTIC-AUDIT-001 (see
vfp_toolchain.verification.sotparse).  Dependency resolution is NOT performed
here: it requires an explicitly operator-approved package-index origin
(REQ-G00-022); the generated lock is a truthful pending-state declaration.

Usage:
    python tools/generate_control_plane.py [--repo-root REPO_ROOT] [--out DIR]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT_CANDIDATE / "src"))

from vfp_toolchain.canonical import (  # noqa: E402
    artifact_json_bytes,
    logical_sha256,
    sorted_id_digest,
)
from vfp_toolchain.bootstrap.invocation import (  # noqa: E402
    DEFAULT_AUTHORING_MODE,
    DEFAULT_SCOPE,
    derive_repo_root,
)
from vfp_toolchain.errors import SotIdentityMismatchError  # noqa: E402
from vfp_toolchain.verification.sotparse import (  # noqa: E402
    CycleError,
    RequirementGraphBuilder,
    SotParseError,
    evaluate_applicability,
    readiness_closure,
    release_closure,
)

GENERATOR_IDENTITY = "vfp-toolchain-control-plane-generator"
GENERATOR_VERSION = "1.0.0"
MANIFEST_SCHEMA_VERSION = 1

# Canonical artifact/schema identities (offline; network dereferencing is
# forbidden — REQ-PORT-022).
SCHEMA_ID_BASE = "https://mcp-vfp9sp2-toolchain.dev/schemas"

SCHEMA_FILES = (
    "requirement-graph.schema.json",
    "verification-manifest.schema.json",
    "compatibility-manifest.schema.json",
    "acquisition-manifest.schema.json",
    "dependency-lock.schema.json",
    "threat-model.schema.json",
    "bootstrap-invocation.schema.json",
    "brownfield-start-baseline.schema.json",
    "release-gate.schema.json",
    "evidence-index.schema.json",
    "capability-snapshot.schema.json",
    "provenance-record.schema.json",
    "execution-profile.schema.json",
)

RELEASE_VERSIONS = ("0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "1.0.0")

# ----------------------------------------------------------------------
# The bootstrap invocation context that this candidate is bound to. These
# values mirror the operator-supplied invocation for the current run; they
# are context bindings (logical), not machine paths.
# ----------------------------------------------------------------------
CANDIDATE_CONTEXT = {
    "operation_scope": "LOCAL_QUALIFICATION",
    "authoring_mode": "HYBRID",
    "release_context": "NONE",
    "release_profile": "NONE",
}

# ----------------------------------------------------------------------
# Declared compatibility baselines (SOT section 11; REQ-P00-012/016/027).
# These are architecture declarations, NOT installed dependencies.
# ----------------------------------------------------------------------
TESTED_BASELINES: tuple[dict[str, Any], ...] = (
    {
        "component": "dbfbridge",
        "tested_baseline": "1.1.1",
        "compatibility_range": ">=1.1.1,<2",
        "origin": "https://github.com/PeterPirog/dbfbridge",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P04_DATA",
    },
    {
        "component": "dbf_anonymizer",
        "tested_baseline": "1.0.0.dev0 @ 02763d7c34b19335e560ef9597a54aed7790968d",
        "compatibility_range": ">=1.0.0.dev0,<2",
        "origin": "https://github.com/PeterPirog/DBF_Anonymizer",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P12_PRIVACY",
    },
    {
        "component": "mcp_protocol",
        "tested_baseline": "2026-07-28",
        "compatibility_range": None,
        "origin": "https://modelcontextprotocol.io/specification/2026-07-28",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P01_MCP_MIN",
    },
    {
        "component": "mcp_python_sdk",
        "tested_baseline": "2.2.0",
        "compatibility_range": None,
        "origin": "https://github.com/modelcontextprotocol/python-sdk",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P01_MCP_MIN",
    },
    {
        "component": "mcp_conformance",
        "tested_baseline": "@modelcontextprotocol/conformance@0.2.0-alpha.10 / requirements 2026-07-28",
        "compatibility_range": None,
        "origin": "https://github.com/modelcontextprotocol/conformance",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P17_MCP_STABILIZATION",
    },
    {
        "component": "psycopg",
        "tested_baseline": "3.3.6",
        "compatibility_range": None,
        "origin": "https://www.psycopg.org/",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P13_RELATIONAL_MODEL",
    },
    {
        "component": "postgresql_server",
        "tested_baseline": "18.6",
        "compatibility_range": "18.x (production-major)",
        "origin": "https://www.postgresql.org/",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P15_SHADOW_MIGRATION",
    },
    {
        "component": "psqlodbc",
        "tested_baseline": "REL-18_00_0002 (32-bit trusted VFP transition profile)",
        "compatibility_range": None,
        "origin": "OPERATOR_PROVIDED_TRUSTED_HOST (origin URL not pinned by Rev.35)",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P16_TRANSITION",
    },
    {
        "component": "foxbin2prg",
        "tested_baseline": "1.21.05 @ 32715d06b84753401b7262c3cc48bde758ee3c8d",
        "compatibility_range": None,
        "origin": "https://github.com/fdbozzo/foxbin2prg",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P06_FOXBIN_ANALYSIS",
    },
    {
        "component": "vfpx_helpfile",
        "tested_baseline": "1.08 @ b911ff18b06f421ece242c1d4dfa9fb140864a4a",
        "compatibility_range": None,
        "origin": "https://github.com/VFPX/HelpFile",
        "status": "DECLARED_ARCHITECTURE_BASELINE",
        "installed_in_this_build": False,
        "first_capability_milestone": "P03_KNOWLEDGE",
    },
)

# ----------------------------------------------------------------------
# Acquisition declarations (REQ-G00-019; WP Part N).
# ----------------------------------------------------------------------
ACQUISITION_DECLARATIONS: tuple[dict[str, Any], ...] = (
    {
        "acquisition_id": "foxbin2prg",
        "role": "CANONICAL_VFP_BINARY_TEXT_ENGINE",
        "origin": "https://github.com/fdbozzo/foxbin2prg",
        "immutable_identity": {"kind": "git_commit", "value": "32715d06b84753401b7262c3cc48bde758ee3c8d"},
        "declared_version": "1.21.05",
        "allowed_acquisition_modes": ["BOUND_TOOL_ROOT", "CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "external_tool_root (never inside REPO_ROOT unless byte-exact vendored snapshot is explicitly required)",
        "availability_milestone": "P06_FOXBIN_ANALYSIS",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "vfpx_helpfile",
        "role": "NORMATIVE_VFP_DOCUMENTATION_CORPUS",
        "origin": "https://github.com/VFPX/HelpFile",
        "immutable_identity": {"kind": "git_commit", "value": "b911ff18b06f421ece242c1d4dfa9fb140864a4a"},
        "declared_version": "1.08",
        "allowed_acquisition_modes": ["BOUND_TOOL_ROOT", "CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {
            "declared": None,
            "policy": "OPERATOR_PROVIDED_LOCAL_CORPUS; redistribution rights MUST be proven for that exact asset before any redistribution (REQ-P00-025)",
        },
        "destination_role": "operator-provided local corpus root (never vendored by default)",
        "availability_milestone": "P03_KNOWLEDGE",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "dbfbridge",
        "role": "DBF_FPT_ENGINE_PUBLIC_API",
        "origin": "https://github.com/PeterPirog/dbfbridge",
        "immutable_identity": {"kind": "version", "value": "1.1.1"},
        "declared_version": "1.1.1",
        "allowed_acquisition_modes": ["CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "locked Python dependency (public 1.x API boundary only; internals never copied)",
        "availability_milestone": "P04_DATA",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "dbf_anonymizer",
        "role": "PRIVACY_ENGINE_PUBLIC_API",
        "origin": "https://github.com/PeterPirog/DBF_Anonymizer",
        "immutable_identity": {
            "kind": "version_at_commit",
            "value": "1.0.0.dev0 @ 02763d7c34b19335e560ef9597a54aed7790968d",
        },
        "declared_version": "1.0.0.dev0",
        "allowed_acquisition_modes": ["CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "locked Python dependency (public clean-slate 1.x boundary only; internals never copied)",
        "availability_milestone": "P12_PRIVACY",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "converge-orchestrator",
        "role": "DEFAULT_AUTONOMOUS_CONTROLLER",
        "origin": "https://github.com/PeterPirog/converge-orchestrator",
        "immutable_identity": {
            "kind": "git_commit_and_tree",
            "commit": "1be97b75cf3b51f5ad0c2f212288f0a9edb3899b",
            "tree": "d47b3c74b7b597dec503b4d3dca9db60e5488c93",
        },
        "declared_version": None,
        "allowed_acquisition_modes": ["BOUND_TOOL_ROOT", "CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "dedicated canonicalized tool_root (REQ-G00-059..061); required only for the AUTONOMOUS controller path",
        "availability_milestone": "B0_CONTROLLER_ACQUISITION",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "mcp_python_sdk",
        "role": "MCP_SERVER_SDK",
        "origin": "https://pypi.org/project/mcp/",
        "immutable_identity": {"kind": "version", "value": "2.2.0"},
        "declared_version": "2.2.0",
        "allowed_acquisition_modes": ["CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "locked Python dependency; installed only when the MCP milestone work begins",
        "availability_milestone": "P01_MCP_MIN",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "mcp_conformance",
        "role": "MCP_CONFORMANCE_REFEREE",
        "origin": "https://www.npmjs.com/package/@modelcontextprotocol/conformance",
        "immutable_identity": {"kind": "package_version", "value": "0.2.0-alpha.10 / requirements 2026-07-28"},
        "declared_version": "0.2.0-alpha.10",
        "allowed_acquisition_modes": ["CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "trusted-host conformance referee; used by later MCP stabilization gates",
        "availability_milestone": "P17_MCP_STABILIZATION",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "psycopg",
        "role": "POSTGRESQL_PYTHON_DRIVER",
        "origin": "https://pypi.org/project/psycopg/",
        "immutable_identity": {"kind": "version", "value": "3.3.6"},
        "declared_version": "3.3.6",
        "allowed_acquisition_modes": ["CONNECTED_PINNED", "OFFLINE_CACHE"],
        "license_expectation": {"declared": None, "policy": "VERIFY_UPSTREAM_LICENSE_AT_ACQUISITION"},
        "destination_role": "locked Python dependency; installed only when PostgreSQL work begins",
        "availability_milestone": "P13_RELATIONAL_MODEL",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "postgresql_server",
        "role": "POSTGRESQL_SERVER_TRUSTED_HOST",
        "origin": "https://www.postgresql.org/download/windows/",
        "immutable_identity": {"kind": "version", "value": "18.6"},
        "declared_version": "18.6",
        "allowed_acquisition_modes": ["OPERATOR_PROVIDED_TRUSTED_HOST"],
        "license_expectation": {"declared": None, "policy": "TRUSTED_HOST_INSTALLATION; no redistribution by this repository"},
        "destination_role": "trusted host service; never vendored",
        "availability_milestone": "P15_SHADOW_MIGRATION",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "psqlodbc",
        "role": "PSQL_ODBC_DRIVER_TRUSTED_HOST",
        "origin": "OPERATOR_PROVIDED_TRUSTED_HOST (origin URL not pinned by Rev.35)",
        "immutable_identity": {"kind": "version", "value": "REL-18_00_0002 (32-bit)"},
        "declared_version": "REL-18_00_0002",
        "allowed_acquisition_modes": ["OPERATOR_PROVIDED_TRUSTED_HOST"],
        "license_expectation": {"declared": None, "policy": "TRUSTED_HOST_INSTALLATION; 32-bit VFP transition profile"},
        "destination_role": "trusted host driver; never vendored",
        "availability_milestone": "P16_TRANSITION",
        "acquired_for_current_gate": False,
    },
    {
        "acquisition_id": "microsoft_vfp9sp2",
        "role": "VFP_RUNTIME_TRUSTED_HOST",
        "origin": "OPERATOR_PROVIDED (licensed Microsoft product)",
        "immutable_identity": {"kind": "operator_asset", "value": "local VFP9 SP2 installation"},
        "declared_version": "9.0 SP2",
        "allowed_acquisition_modes": ["OPERATOR_PROVIDED_TRUSTED_HOST"],
        "license_expectation": {
            "declared": "Microsoft license",
            "policy": "MUST NOT be vendored into public source or release artifacts unless explicit redistribution rights and provenance are recorded (REQ-P00-025)",
        },
        "destination_role": "operator-provided local runtime",
        "availability_milestone": "P10_OPTIMIZATION",
        "acquired_for_current_gate": False,
    },
)

# ----------------------------------------------------------------------
# Threat model content (REQ-P02-017; WP Part Q). Statuses are DECLARED /
# PLANNED — never PASS for unimplemented mitigations.
# ----------------------------------------------------------------------
THREAT_BOUNDARIES: tuple[dict[str, Any], ...] = (
    {
        "boundary_id": "REPOSITORY_MUTATION",
        "description": "Git repository, refs, working tree, generated contract artifacts.",
        "assets": ["git refs", "spec/ contract artifacts", "source tree", "evidence/"],
        "trust_boundary": "Only the trusted integration layer may advance refs; ordinary credentials cannot.",
        "threats": [
            {"id": "THR-REPO-01", "name": "Unauthorized ref advance", "description": "Agent or external actor advances main without gates."},
            {"id": "THR-REPO-02", "name": "Hand-edited generated artifact", "description": "Editing a generated file to fake compliance."},
            {"id": "THR-REPO-03", "name": "History rewrite", "description": "Rewriting existing history to hide provenance."},
        ],
        "controls": [
            {"id": "CTL-REPO-01", "threats": ["THR-REPO-01", "THR-REPO-03"], "requirements": ["REQ-G00-053", "REQ-AUTO-031", "REQ-AUTO-054", "REQ-AUTO-055"], "status": "PLANNED", "note": "Trusted integration layer implementation is future work."},
            {"id": "CTL-REPO-02", "threats": ["THR-REPO-02"], "requirements": ["REQ-AUTO-038", "REQ-PORT-018"], "status": "DECLARED", "note": "Determinism checks reject hand-edited logical content."},
        ],
    },
    {
        "boundary_id": "FILESYSTEM_PATHS_REPARSE",
        "description": "Windows path normalization, traversal, junction/symlink/reparse attacks.",
        "assets": ["allowed roots", "immutable source zones", "workspace/output roots"],
        "trust_boundary": "Path policy rejects traversal, reparse escape, alias confusion before any access.",
        "threats": [
            {"id": "THR-PATH-01", "name": "Path traversal / reparse escape", "description": "Junction or symlink redirection escapes allowed roots."},
            {"id": "THR-PATH-02", "name": "Case/short-name alias confusion", "description": "8.3 or case-insensitive aliases bypass policy."},
        ],
        "controls": [
            {"id": "CTL-PATH-01", "threats": ["THR-PATH-01", "THR-PATH-02"], "requirements": ["REQ-P02-001", "REQ-P02-010", "REQ-P02-020"], "status": "PLANNED", "note": "Path policy engine is a Phase 2 deliverable."},
        ],
    },
    {
        "boundary_id": "EXTERNAL_PROCESS_EXECUTION",
        "description": "Subprocess/COM/VFP/FoxBin2Prg execution surfaces.",
        "assets": ["allowlisted executables", "subprocess env", "VFP workers"],
        "trust_boundary": "Explicit allowlist, argument arrays, minimal env, isolated workspace.",
        "threats": [
            {"id": "THR-PROC-01", "name": "Injection through project content", "description": "VFP source/data content must never become shell commands."},
            {"id": "THR-PROC-02", "name": "Env secret leakage to helpers", "description": "Inherited secrets reaching helper processes."},
        ],
        "controls": [
            {"id": "CTL-PROC-01", "threats": ["THR-PROC-01"], "requirements": ["REQ-P02-013", "REQ-P02-011"], "status": "PLANNED", "note": "Phase 2 deliverable."},
            {"id": "CTL-PROC-02", "threats": ["THR-PROC-02"], "requirements": ["REQ-P02-014"], "status": "PLANNED", "note": "Phase 2 deliverable."},
        ],
    },
    {
        "boundary_id": "DEPENDENCY_ORIGINS",
        "description": "Package-index and repository origins for every dependency.",
        "assets": ["dependency lock", "wheelhouse", "SBOM"],
        "trust_boundary": "Approved origins only; exact artifact hashes; no floating re-resolution after sealing.",
        "threats": [
            {"id": "THR-DEP-01", "name": "Unapproved origin / shadow package", "description": "Dependency installed from an unapproved index."},
            {"id": "THR-DEP-02", "name": "Floating re-resolution", "description": "Re-resolving after the candidate tree is sealed."},
        ],
        "controls": [
            {"id": "CTL-DEP-01", "threats": ["THR-DEP-01", "THR-DEP-02"], "requirements": ["REQ-G00-018", "REQ-G00-022", "REQ-P00-024", "REQ-AUTO-045"], "status": "PLANNED", "note": "Canonical GREENFIELD dependency lock resolved exactly once from the approved PyPI origin (authorization OPERATOR-GREENFIELD-PYPI-B0-2026-10-08) and frozen before candidate-tree sealing; automated origin/integrity tamper rejection and lock-update automation remain future work."},
        ],
    },
    {
        "boundary_id": "VFP_INTEGRATION",
        "description": "Operator-provided VFP9 SP2 runtime, COM automation, interactive sessions.",
        "assets": ["VFP executables", "COM registrations", "operator apps"],
        "trust_boundary": "Operator-provided assets only; never vendored; trusted-profile execution only.",
        "threats": [
            {"id": "THR-VFP-01", "name": "Proprietary asset redistribution", "description": "Vendoring licensed Microsoft assets into public artifacts."},
            {"id": "THR-VFP-02", "name": "Application source execution", "description": "Executing analyzed project code outside an isolated workspace."},
        ],
        "controls": [
            {"id": "CTL-VFP-01", "threats": ["THR-VFP-01"], "requirements": ["REQ-P00-025"], "status": "DECLARED", "note": "No VFP assets exist in this repository; scan-based control."},
            {"id": "CTL-VFP-02", "threats": ["THR-VFP-02"], "requirements": ["REQ-P02-013"], "status": "PLANNED", "note": "Phase 2/6 deliverable."},
        ],
    },
    {
        "boundary_id": "DBF_BINARY_DATA_HANDLING",
        "description": "DBF/FPT/CDX binary parsing, Memo handling, original-value exposure.",
        "assets": ["datasets", "Memo content", "profiles"],
        "trust_boundary": "dbfbridge public API only; original values never leak into logs/evidence/prompts.",
        "threats": [
            {"id": "THR-DATA-01", "name": "Memo/original-value leakage", "description": "Private values appearing in logs, evidence, or MCP responses."},
            {"id": "THR-DATA-02", "name": "Corrupt/malicious DBF input", "description": "Malformed binaries crashing or confusing the engine."},
        ],
        "controls": [
            {"id": "CTL-DATA-01", "threats": ["THR-DATA-01"], "requirements": ["REQ-P02-006", "REQ-AUTO-046"], "status": "PLANNED", "note": "Redaction engine is Phase 2+ deliverable."},
            {"id": "CTL-DATA-02", "threats": ["THR-DATA-02"], "requirements": ["REQ-AUTO-016"], "status": "PLANNED", "note": "Fuzz/property coverage is Phase 4+ deliverable."},
        ],
    },
    {
        "boundary_id": "POSTGRESQL_BOUNDARY",
        "description": "Shadow/migration target database, credentials, cross-engine parity.",
        "assets": ["shadow database", "migration state", "credentials"],
        "trust_boundary": "Explicit target references; bounded connections; no implicit prod writes.",
        "threats": [
            {"id": "THR-PG-01", "name": "Credential exposure", "description": "PostgreSQL secrets in config/evidence/logs."},
            {"id": "THR-PG-02", "name": "Unbounded writes to target", "description": "Migration writing outside controlled staging."},
        ],
        "controls": [
            {"id": "CTL-PG-01", "threats": ["THR-PG-01"], "requirements": ["REQ-P01-019", "REQ-AUTO-046"], "status": "PLANNED", "note": "Phase 13+ deliverable."},
            {"id": "CTL-PG-02", "threats": ["THR-PG-02"], "requirements": ["REQ-P13-024"], "status": "PLANNED", "note": "Bounded connection management is Phase 13 deliverable."},
        ],
    },
    {
        "boundary_id": "MCP_TRANSPORT",
        "description": "MCP protocol transport (stdio/HTTP), tool/resource schemas, client trust.",
        "assets": ["tool registry", "resource templates", "protocol envelopes"],
        "trust_boundary": "Thin adapter over Core; unavailable capabilities reported truthfully.",
        "threats": [
            {"id": "THR-MCP-01", "name": "Placeholder success for missing capability", "description": "Simulating unfinished features as success."},
            {"id": "THR-MCP-02", "name": "Injection via tool arguments/data", "description": "Project-controlled content altering protocol structure."},
        ],
        "controls": [
            {"id": "CTL-MCP-01", "threats": ["THR-MCP-01"], "requirements": ["REQ-P01-012", "REQ-G00-004"], "status": "DECLARED", "note": "Truthful capability state enforced by design and tests."},
            {"id": "CTL-MCP-02", "threats": ["THR-MCP-02"], "requirements": ["REQ-P02-012"], "status": "PLANNED", "note": "Phase 2 deliverable."},
        ],
    },
    {
        "boundary_id": "EVIDENCE_PROVENANCE",
        "description": "Machine-readable evidence, hashes, provenance bundles.",
        "assets": ["evidence/", "provenance records", "qualified-release records"],
        "trust_boundary": "Evidence is freshness-bound to exact commit/tree/SOT/lock identities; sensitive classes redacted.",
        "threats": [
            {"id": "THR-EVID-01", "name": "Stale evidence reuse", "description": "Old PASS evidence reused after bound inputs changed."},
            {"id": "THR-EVID-02", "name": "Sensitive data in evidence", "description": "Original DBF values or secrets entering evidence."},
        ],
        "controls": [
            {"id": "CTL-EVID-01", "threats": ["THR-EVID-01"], "requirements": ["REQ-AUTO-049"], "status": "PLANNED", "note": "Compliance store is Phase 2A deliverable."},
            {"id": "CTL-EVID-02", "threats": ["THR-EVID-02"], "requirements": ["REQ-AUTO-046"], "status": "PLANNED", "note": "Leakage scans are Phase 2A deliverable."},
        ],
    },
    {
        "boundary_id": "AGENT_CONTROLLER_TRUST",
        "description": "Coding-agent/controller boundary, model routing, write protection.",
        "assets": ["controller checkout", "runtime config", "external SOT copy"],
        "trust_boundary": "Builder never self-approves; controller pinned by commit/tree; SOT write-protected for model-authored runs.",
        "threats": [
            {"id": "THR-AGT-01", "name": "Builder self-approval", "description": "Authoring agent counting its own review as independent."},
            {"id": "THR-AGT-02", "name": "SOT mutation by model identity", "description": "Model-authored process editing the frozen contract."},
        ],
        "controls": [
            {"id": "CTL-AGT-01", "threats": ["THR-AGT-01"], "requirements": ["REQ-G00-057", "REQ-AUTO-048"], "status": "PLANNED", "note": "Independent review executions are workflow-level."},
            {"id": "CTL-AGT-02", "threats": ["THR-AGT-02"], "requirements": ["REQ-G00-074", "REQ-PORT-039"], "status": "PLANNED", "note": "OS write-protection boundary is AUTONOMOUS-path work."},
        ],
    },
    {
        "boundary_id": "REMOTE_INTEGRATION_PUBLICATION",
        "description": "Remote refs, PRs, CI checks, releases, package publication.",
        "assets": ["canonical remote", "release assets", "attestations"],
        "trust_boundary": "Explicit operator authorization bound to invocation hash and destination identity; local qualification stays available.",
        "threats": [
            {"id": "THR-REM-01", "name": "Unauthorized push/publication", "description": "Remote mutation without authorization."},
            {"id": "THR-REM-02", "name": "Publishing unqualified content", "description": "Release artifacts without a qualified-release record."},
        ],
        "controls": [
            {"id": "CTL-REM-01", "threats": ["THR-REM-01"], "requirements": ["REQ-G00-053", "REQ-AUTO-031"], "status": "PLANNED", "note": "Remote scopes inactive under LOCAL_QUALIFICATION."},
            {"id": "CTL-REM-02", "threats": ["THR-REM-02"], "requirements": ["REQ-AUTO-027", "REQ-AUTO-029", "REQ-AUTO-047"], "status": "PLANNED", "note": "Publication automation is future work."},
        ],
    },
)


# ----------------------------------------------------------------------
# Verifier registry — the EXECUTABLE entries map to commands that exist in
# this candidate tree and run offline with the supported Python stdlib
# (schema validation requires the jsonschema capability, declared explicitly).
# Every other requirement carries a PLANNED verifier stub with no command, so
# no dangling executable reference and no fabricated PASS is possible.
# ----------------------------------------------------------------------
EXECUTABLE_VERIFIERS: tuple[dict[str, Any], ...] = (
    {
        "verifier_id": "VER-CONTRACT-SELF-CONSISTENCY",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "self-consistency"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": [
            "REQ-B00-004",
            "REQ-PORT-009",
            "REQ-PORT-010",
            "REQ-PORT-014",
            "REQ-PORT-015",
            "REQ-PORT-019",
            "REQ-PORT-020",
            "REQ-PORT-021",
            "REQ-PORT-024",
            "REQ-PORT-025",
            "REQ-PORT-026",
            "REQ-AUTO-003",
        ],
        "notes": "Full contract self-consistency engine over the frozen SOT and generated graph.",
    },
    {
        "verifier_id": "VER-CONTRACT-SCHEMAS",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "schemas"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": ["PYTHON_JSONSCHEMA_4X"],
        "covers": ["REQ-G00-025", "REQ-PORT-022"],
        "notes": "Schema document validation plus artifact-against-schema conformance; BLOCKED without the jsonschema capability.",
    },
    {
        "verifier_id": "VER-CONTROL-PLANE-LAYOUT",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "layout"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-G00-004", "REQ-G00-005", "REQ-G00-006", "REQ-G00-016", "REQ-G00-017"],
        "notes": "Canonical layout, required file set, license and .gitattributes policy checks.",
    },
    {
        "verifier_id": "VER-CONTROL-PLANE-DETERMINISM",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "determinism"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-PORT-017", "REQ-PORT-018", "REQ-AUTO-038"],
        "notes": "Double generation into independent scratch dirs; logical identity equality.",
    },
    {
        "verifier_id": "VER-PACKAGE-FOUNDATION",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "package"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-G00-004", "REQ-G00-020", "REQ-G00-009"],
        "notes": "Package metadata, console entry points, import, truthful capability state. Actual build/install execution from the frozen lock is qualified in the dependency-finalization and gate work packets.",
    },
    {
        "verifier_id": "VER-NO-RUNTIME-DOWNLOAD",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "no-download"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-G00-008", "REQ-P00-009"],
        "notes": "Static network/package-install sentinel over the package source. Runtime-sentinel execution remains PLANNED.",
    },
    {
        "verifier_id": "VER-TEST-SUITE",
        "state": "EXECUTABLE",
        "command": ["python", "-m", "unittest", "tests.contract.test_graph_integrity", "tests.contract.test_cycle_regression", "tests.contract.test_b0_closure", "tests.contract.test_layout", "tests.contract.test_manifest", "tests.contract.test_profiles", "tests.contract.test_release_gates", "tests.contract.test_threat_model", "tests.package.test_package", "tests.package.test_no_runtime_download", "tests.bootstrap.test_start_state", "tests.contract.test_determinism"],
        "evidence_class": "UNITTEST_REPORT",
        "required_capabilities": [],
        "covers": [
            "REQ-G00-001",
            "REQ-G00-002",
            "REQ-G00-004",
            "REQ-G00-005",
            "REQ-G00-006",
            "REQ-G00-007",
            "REQ-G00-016",
            "REQ-G00-017",
            "REQ-G00-020",
            "REQ-G00-028",
            "REQ-G00-034",
            "REQ-G00-036",
            "REQ-B00-002",
            "REQ-B00-004",
            "REQ-PORT-004",
            "REQ-PORT-007",
            "REQ-PORT-008",
            "REQ-PORT-009",
            "REQ-PORT-010",
            "REQ-PORT-014",
            "REQ-PORT-015",
            "REQ-PORT-017",
            "REQ-PORT-018",
            "REQ-PORT-021",
            "REQ-PORT-022",
            "REQ-PORT-024",
            "REQ-PORT-025",
            "REQ-PORT-026",
            "REQ-PORT-027",
            "REQ-PORT-034",
            "REQ-P00-013",
            "REQ-P02-017",
            "REQ-AUTO-002",
            "REQ-AUTO-003",
            "REQ-AUTO-004",
            "REQ-AUTO-005",
            "REQ-AUTO-025",
            "REQ-AUTO-036",
            "REQ-AUTO-038",
        ],
        "notes": "Deterministic offline unittest/pytest-compatible suite. Every test module declares its requirement IDs (REQ-AUTO-005).",
    },
    {
        "verifier_id": "VER-TEST-EVIDENCE-MAP",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "test-map"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-AUTO-005"],
        "notes": "Collects test-module -> requirement-ID mapping from the suite registry.",
    },
    {
        "verifier_id": "VER-DEPENDENCY-LOCK",
        "state": "EXECUTABLE",
        "command": ["python", "tools/verify.py", "dependency-lock"],
        "evidence_class": "MACHINE_READABLE_REPORT",
        "required_capabilities": ["PYTHON_JSONSCHEMA_4X", "PYTHON_PACKAGING", "FROZEN_WHEELHOUSE_FOR_FULL_CHECKS"],
        "covers": ["REQ-G00-018", "REQ-G00-022", "REQ-P00-024", "REQ-AUTO-045"],
        "notes": "Independent verification of the frozen canonical dependency lock: schema, SOT/invocation/resolver/origin bindings, declaration equality, profile separation, single-version (no-floating), artifact inventory consistency, and - when the frozen wheelhouse is provided - artifact hashes, wheelhouse equality, and closure recomputation from wheel metadata. Without the wheelhouse the wheelhouse checks surface BLOCKED, never PASS.",
    },
)


def _requirement_verifier_ids(graph: dict[str, Any]) -> dict[str, list[str]]:
    covered: dict[str, list[str]] = {}
    for verifier in EXECUTABLE_VERIFIERS:
        for rid in verifier["covers"]:
            covered.setdefault(rid, []).append(verifier["verifier_id"])
    return covered


# ----------------------------------------------------------------------
# artifact assembly
# ----------------------------------------------------------------------

def _meta(sot_sha256: str, generator_hash: str, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "sot_revision": 35,
        "sot_sha256": sot_sha256,
        "generator": {
            "identity": GENERATOR_IDENTITY,
            "version": GENERATOR_VERSION,
            "source_sha256": generator_hash,
        },
        "generated_at_utc": generated_at,
    }


def _with_content_hash(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact = dict(artifact)
    artifact["content_sha256"] = logical_sha256(artifact)
    return artifact


def build_requirements_graph(sot_text: str, generator_hash: str, generated_at: str) -> dict[str, Any]:
    builder = RequirementGraphBuilder(sot_text)
    graph_core = builder.build()
    context = dict(CANDIDATE_CONTEXT)
    context["start_mode"] = "GREENFIELD"
    b0 = readiness_closure(graph_core, "B0", context)
    brownfield_context = dict(CANDIDATE_CONTEXT)
    brownfield_context["start_mode"] = "BROWNFIELD"
    br0 = readiness_closure(graph_core, "BR0", brownfield_context)
    for closure in (b0, br0):
        closure["requirement_id_digest"] = sorted_id_digest(closure["requirement_ids"])

    release_closures: dict[str, Any] = {}
    for version in RELEASE_VERSIONS:
        closure = release_closure(graph_core, version, context)
        closure["requirement_id_digest"] = sorted_id_digest(closure["requirement_ids"])
        release_closures[version] = closure

    by_id = {r["id"]: r for r in graph_core["requirements"]}
    for req in graph_core["requirements"]:
        deps = []
        if req["id"] in set(b0["requirement_ids"]):
            deps.append("B0")
        if req["id"] in set(br0["requirement_ids"]):
            deps.append("BR0")
        for version, closure in release_closures.items():
            if req["id"] in set(closure["requirement_ids"]):
                deps.append(f"release:{version}")
        req["closure_membership"] = deps

    artifact: dict[str, Any] = {
        **_meta(builder.sot_sha256, generator_hash, generated_at),
        "artifact_kind": "REQUIREMENT_GRAPH",
        "requirement_count": len(graph_core["requirements"]),
        "first_id": graph_core["requirements"][0]["id"],
        "last_id": graph_core["requirements"][-1]["id"],
        "selector_vocabulary": ["EXACT_ID", "FAMILY_RANGE", "FAMILY_WILDCARD"],
        "canonical_semantics": {
            "source_audit": "WP-SOT-REV35-SEMANTIC-AUDIT-001",
            "decision": "DECISION_A",
            "rules": [
                "physical Markdown phase position is not an execution prerequisite",
                "requirement numbering is not an execution prerequisite",
                "canonical milestone selectors own activation",
                "execution prerequisite basis = earliest selecting milestone in the explicit after:-derived DAG order",
                "later re-selection does not import later milestone ancestors",
                "explicit prerequisite IDs remain authoritative (Rev.35 declares none; scan re-run each generation)",
                "structured applicability and lifecycle mappings remain authoritative",
                "full semantic graph cycle detection is mandatory (Tarjan SCC)",
            ],
        },
        "readiness_closures": {"B0": b0, "BR0": br0},
        "release_closures": release_closures,
        **graph_core,
    }
    return _with_content_hash(artifact)


def build_verification_manifest(
    graph_artifact: dict[str, Any], generator_hash: str, generated_at: str
) -> dict[str, Any]:
    requirements: dict[str, Any] = {}
    covered = _requirement_verifier_ids(graph_artifact)
    for record in graph_artifact["requirements"]:
        rid = record["id"]
        # A requirement covered by executable verifiers references only those;
        # the PLANNED stub exists solely to guarantee every requirement has a
        # mapped verifier (REQ-AUTO-002) until real ones cover it.
        verifier_ids = covered.get(rid) or [f"VER-{rid}"]
        requirements[rid] = {
            "lifecycle": record["lifecycle"],
            "applicability": record["applicability"],
            "execution_milestone": record["execution_milestone"],
            "closure_membership": record["closure_membership"],
            "verifier_ids": verifier_ids,
            "current_state": "PLANNED",
            "state_evidence": None,
        }
    registry: dict[str, Any] = {}
    for verifier in EXECUTABLE_VERIFIERS:
        registry[verifier["verifier_id"]] = {k: v for k, v in verifier.items() if k != "covers"}
        registry[verifier["verifier_id"]]["covers"] = list(verifier["covers"])
    for record in graph_artifact["requirements"]:
        stub_id = f"VER-{record['id']}"
        if record["id"] not in covered and stub_id not in registry:
            registry[stub_id] = {
                "verifier_id": stub_id,
                "state": "PLANNED",
                "command": None,
                "evidence_class": "MACHINE_READABLE_REPORT",
                "required_capabilities": [],
                "covers": [record["id"]],
                "notes": "Mapped but not implemented; must become executable before this requirement can transition to PASS (REQ-G00-007, REQ-AUTO-002).",
            }
    artifact: dict[str, Any] = {
        **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
        "artifact_kind": "VERIFICATION_MANIFEST",
        "requirement_count": len(requirements),
        "verifier_count": len(registry),
        "executable_verifier_count": sum(1 for v in registry.values() if v["state"] == "EXECUTABLE"),
        "pass_count": 0,
        "graph_ref": "spec/requirements.graph.json",
        "graph_content_sha256": graph_artifact["content_sha256"],
        "state_vocabulary": [
            "UNASSESSED",
            "PLANNED",
            "NOT_IMPLEMENTED",
            "PARTIAL",
            "BLOCKED",
            "PASS",
            "NOT_APPLICABLE",
        ],
        "verifiers": registry,
        "requirements": requirements,
    }
    return _with_content_hash(artifact)


def build_compatibility_manifest(generator_hash: str, generated_at: str, sot_sha256: str) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        **_meta(sot_sha256, generator_hash, generated_at),
        "artifact_kind": "COMPATIBILITY_MANIFEST",
        "supported_python_range": ">=3.10,<3.15",
        "supported_operating_systems": ["Windows"],
        "target_dialect": "microsoft.visual-foxpro.9.0.sp2",
        "windows_only": True,
        "tested_baselines": [dict(entry) for entry in TESTED_BASELINES],
        "windows_support_matrix": {
            "TESTED": ["development hosts used for local qualification (recorded per qualification run)"],
            "COMPATIBLE_UNVERIFIED": [],
            "UNSUPPORTED": ["non-Windows operating systems"],
            "note": "REQ-P00-026: a successful test on one Windows build is never generalized.",
        },
        "capability_availability": [
            {
                "capability": entry["id"],
                "activation_milestone": entry["activation_milestone"],
                "available": False,
                "state": "NOT_IMPLEMENTED",
            }
            for entry in _domain_capabilities()
        ],
    }
    return _with_content_hash(artifact)


def _domain_capabilities() -> list[dict[str, Any]]:
    from vfp_toolchain import capabilities as _caps

    return _caps.discover()["capabilities"]


def build_acquisition_manifest(generator_hash: str, generated_at: str, sot_sha256: str) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        **_meta(sot_sha256, generator_hash, generated_at),
        "artifact_kind": "ACQUISITION_MANIFEST",
        "declared_architecture_baseline": [dict(entry) for entry in ACQUISITION_DECLARATIONS],
        "acquired_for_current_gate": [],
        "policy": {
            "connected_preparation": "approved immutable origin -> verify -> local cache",
            "offline_preparation": "preseeded local cache -> verify",
            "runtime_requests": "no dependency acquisition (REQ-P00-009)",
            "post_acquisition_fingerprint": "content fingerprint recorded at acquisition time",
        },
    }
    return _with_content_hash(artifact)


def build_dependency_lock(
    generator_hash: str, generated_at: str, sot_sha256: str
) -> dict[str, Any]:
    direct = {
        "runtime": [],
        "build": [
            {"distribution": "build", "constraint": ">=1", "reason": "PEP 517/621 build frontend invoked by the deterministic B0 build step"},
            {"distribution": "setuptools", "constraint": ">=68", "reason": "PEP 517 build backend (wheel/sdist)"},
            {"distribution": "wheel", "constraint": ">=0.43", "reason": "wheel packaging helper for the wheel build"},
        ],
        "test": [
            {"distribution": "pytest", "constraint": ">=8", "reason": "deterministic pytest runner for the candidate suite"},
        ],
        "schema_validation": [
            {"distribution": "jsonschema", "constraint": ">=4.21", "reason": "JSON Schema 2020-12 artifact validation"},
            {"distribution": "rpds-py", "constraint": "==0.30.0", "reason": "matrix-coherent exact pin of the referencing persistence engine (wheel tags for the full supported matrix)"},
        ],
    }
    artifact: dict[str, Any] = {
        **_meta(sot_sha256, generator_hash, generated_at),
        "artifact_kind": "DEPENDENCY_LOCK",
        "lock_role": "GREENFIELD_BOOTSTRAP",
        "resolution_status": "PENDING_AWAITING_APPROVED_ORIGIN",
        "blocker": {
            "code": "GREENFIELD_APPROVED_DEPENDENCY_ORIGIN_REQUIRED",
            "message": (
                "Dependency resolution was not performed: no explicit operator-approved "
                "GREENFIELD package-index origin exists for this bootstrap invocation. "
                "The previous PyPI approval was scoped to WP-BR0-007B (brownfield) only."
            ),
        },
        "approved_origins": [],
        "resolver_identity": None,
        "python_range": ">=3.10,<3.15",
        "direct_constraints": direct,
        "optional_profiles": {
            "dev": ["pytest", "jsonschema", "rpds-py", "build", "setuptools", "wheel"],
        },
        "resolved": None,
        "transitive_artifacts": [],
        "post_seal_policy": "after candidate-tree sealing: no floating re-resolution (REQ-G00-022)",
    }
    return _with_content_hash(artifact)


def build_threat_model(generator_hash: str, generated_at: str, sot_sha256: str) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        **_meta(sot_sha256, generator_hash, generated_at),
        "artifact_kind": "THREAT_MODEL",
        "model_version": 1,
        "methodology": "STRIDE-style structured boundaries; statuses DECLARED/PLANNED only",
        "control_status_vocabulary": ["DECLARED", "PLANNED", "PASS"],
        "boundaries": [dict(boundary) for boundary in THREAT_BOUNDARIES],
        "notes": "Mitigations are never marked PASS merely because they are declared; PASS requires executed deterministic evidence.",
    }
    return _with_content_hash(artifact)


def _gate_evidence_fields(closure: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "derivation": closure["derivation"],
        "context": closure["context"],
        "requirement_count": closure["requirement_count"],
        "requirement_ids": closure["requirement_ids"],
        "requirement_id_digest": closure["requirement_id_digest"],
        "directly_selected_count": closure["directly_selected_count"],
        "transitive_prerequisites_added": closure["transitive_prerequisites_added"],
        "excluded_by_applicability": closure["excluded_by_applicability"],
        "graph_content_sha256": graph["content_sha256"],
        "gate_result": "PLANNED",
        "qualified": False,
    }


def build_release_gate_artifacts(
    graph_artifact: dict[str, Any], generator_hash: str, generated_at: str
) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    context = dict(CANDIDATE_CONTEXT)
    context["start_mode"] = "GREENFIELD"

    artifacts["readiness-b0.json"] = {
        **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
        "artifact_kind": "READINESS_GATE",
        "gate": "B0",
        "start_mode": "GREENFIELD",
        **_gate_evidence_fields(graph_artifact["readiness_closures"]["B0"], graph_artifact),
    }
    artifacts["readiness-br0.json"] = {
        **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
        "artifact_kind": "READINESS_GATE",
        "gate": "BR0",
        "start_mode": "BROWNFIELD",
        **_gate_evidence_fields(graph_artifact["readiness_closures"]["BR0"], graph_artifact),
    }

    scenario = {
        **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
        "artifact_kind": "GREENFIELD_SCENARIO_DEFINITIONS",
        "parameter": "authoring_mode",
        "target": "first qualified release (0.4.0) without hand-created generated manifests",
        "execution_timing": "complete scenario execution belongs to the first release-qualification gate, not to B0 (REQ-G00-015)",
        "variants": {
            "MANUAL": {
                "embedded_contract": "MANUAL_BOOTSTRAP_V1",
                "human_source_editing_allowed": True,
                "actor_attribution": "not required beyond MANUAL provenance",
                "phases": [
                    "bind_and_canonicalize_inputs",
                    "hash_source_of_truth",
                    "derive_repo_root",
                    "inspect_and_classify_before_mutation",
                    "prepare_start_mode_workspace",
                    "materialize_exact_source_of_truth",
                    "build_bootstrap_control_plane_candidate",
                    "generate_generic_profile_and_verifier_dispatch",
                    "seal_candidate_tree",
                    "run_bootstrap_preflight",
                    "create_or_advance_trusted_local_bootstrap_commit",
                    "verify_committed_tree_and_working_state",
                    "evaluate_B0_or_BR0",
                    "handoff_to_committed_generic_profile",
                ],
            },
            "AUTONOMOUS": {
                "embedded_contract": "AUTONOMOUS_BOOTSTRAP_V1",
                "human_source_editing_allowed": False,
                "undeclared_human_source_edit": "forbidden",
                "phases": [
                    "bind_and_canonicalize_inputs",
                    "hash_source_of_truth",
                    "derive_and_classify_repo_root",
                    "acquire_and_verify_controller",
                    "resolve_and_freeze_model_routing",
                    "create_or_prepare_bootstrap_seed",
                    "seal_and_verify_bootstrap_candidate",
                    "run_bootstrap_or_brownfield_preflight",
                    "create_or_advance_trusted_bootstrap_seed_commit",
                    "evaluate_B0_or_BR0",
                    "generate_external_controller_runtime_config",
                    "establish_and_verify_external_sot_write_protection",
                    "run_controller_environment_preflight",
                    "run_autonomous_model_preflight",
                    "handoff_seed_config_protection_and_routing",
                ],
            },
            "HYBRID": {
                "embedded_contract": "MANUAL_BOOTSTRAP_V1",
                "human_source_editing_allowed": True,
                "agent_source_editing_allowed": True,
                "actor_attribution": "required for every candidate change (REQ-G00-055)",
                "phases_note": "manual or agent authoring steps permitted; both carry actor attribution; phases mirror MANUAL_BOOTSTRAP_V1",
                "phases": [
                    "bind_and_canonicalize_inputs",
                    "hash_source_of_truth",
                    "derive_repo_root",
                    "inspect_and_classify_before_mutation",
                    "prepare_start_mode_workspace",
                    "materialize_exact_source_of_truth",
                    "build_bootstrap_control_plane_candidate",
                    "generate_generic_profile_and_verifier_dispatch",
                    "seal_candidate_tree",
                    "run_bootstrap_preflight",
                    "create_or_advance_trusted_local_bootstrap_commit",
                    "verify_committed_tree_and_working_state",
                    "evaluate_B0_or_BR0",
                    "handoff_to_committed_generic_profile",
                ],
            },
        },
        "all_scenario_inputs_declared": True,
        "scenario_hash_algorithm": "canonical logical sha256 per variant",
    }
    artifacts["greenfield-scenario.json"] = _with_content_hash(scenario)

    for version in RELEASE_VERSIONS:
        closure = graph_artifact["release_closures"][version]
        artifacts[f"release-{version}.json"] = {
            **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
            "artifact_kind": "RELEASE_GATE",
            "release": version,
            "closure_milestones_declared": closure["closure_milestones_declared"],
            "cumulative_milestones": closure["cumulative_milestones"],
            "cumulative_regression_releases": closure["cumulative_regression_releases"],
            "requirement_count": closure["requirement_count"],
            "requirement_ids": closure["requirement_ids"],
            "requirement_id_digest": closure["requirement_id_digest"],
            "governance_requirement_ids": closure["governance_requirement_ids"],
            "qualified": False,
            "qualified_release_record": None,
            "graph_content_sha256": graph_artifact["content_sha256"],
        }

    index = {
        **_meta(graph_artifact["sot_sha256"], generator_hash, generated_at),
        "artifact_kind": "RELEASE_GATE_INDEX",
        "gates": {},
    }
    hashed = {name: _with_content_hash(dict(artifact)) for name, artifact in artifacts.items()}
    for name in sorted(hashed):
        index["gates"][name] = hashed[name]["content_sha256"]
    hashed["index.json"] = index
    return hashed


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

def _existing_frozen_dependency_lock(repo_root: Path) -> dict[str, Any] | None:
    """Load an already-frozen canonical dependency lock, if one exists.

    The generator NEVER re-resolves dependencies (REQ-G00-022: resolution
    happens exactly once, before the candidate tree is sealed). When a
    RESOLVED_FROZEN lock is present it is consumed as-is and preserved
    byte-stably through regeneration; only a pending-state placeholder is
    ever (re)built here.
    """
    lock_path = repo_root / "spec" / "dependency-lock.json"
    if not lock_path.is_file():
        return None
    try:
        existing = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        isinstance(existing, dict)
        and existing.get("artifact_kind") == "DEPENDENCY_LOCK"
        and existing.get("resolution_status") == "RESOLVED_FROZEN"
    ):
        return existing
    return None


def generate(repo_root: Path, out_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    out_root = (out_root or repo_root).resolve()
    sot_path = repo_root / "spec" / "SOURCE_OF_TRUTH.md"
    sot_bytes = sot_path.read_bytes()
    sot_text = sot_bytes.decode("utf-8")
    sot_sha256 = hashlib.sha256(sot_bytes).hexdigest().upper()

    generator_path = Path(__file__).resolve()
    generator_hash = __import__("hashlib").sha256(generator_path.read_bytes()).hexdigest().upper()

    generated_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    graph = build_requirements_graph(sot_text, generator_hash, generated_at)
    if graph["sot_sha256"] != sot_sha256:  # pragma: no cover - defensive
        raise SotIdentityMismatchError("SOT identity mismatch during generation")
    verification = build_verification_manifest(graph, generator_hash, generated_at)
    compatibility = build_compatibility_manifest(generator_hash, generated_at, sot_sha256)
    acquisition = build_acquisition_manifest(generator_hash, generated_at, sot_sha256)
    frozen_lock = _existing_frozen_dependency_lock(repo_root)
    dependency_lock = frozen_lock if frozen_lock is not None else build_dependency_lock(generator_hash, generated_at, sot_sha256)
    threat_model = build_threat_model(generator_hash, generated_at, sot_sha256)
    gates = build_release_gate_artifacts(graph, generator_hash, generated_at)

    artifacts: dict[str, dict[str, Any]] = {
        "spec/requirements.graph.json": graph,
        "spec/verification.manifest.json": verification,
        "spec/compatibility.manifest.json": compatibility,
        "spec/acquisition.manifest.json": acquisition,
        "spec/dependency-lock.json": dependency_lock,
        "spec/threat-model.json": threat_model,
    }
    artifacts.update({f"release-gates/{name}": gate for name, gate in gates.items()})
    artifacts = {name: _with_content_hash(artifact) for name, artifact in artifacts.items()}

    written: dict[str, str] = {}
    for relative, artifact in sorted(artifacts.items()):
        destination = out_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(artifact_json_bytes(artifact))
        written[relative] = artifact["content_sha256"]

    return {
        "repo_root": str(repo_root),
        "out_root": str(out_root),
        "sot_sha256": sot_sha256,
        "requirement_count": graph["requirement_count"],
        "b0_requirement_count": graph["readiness_closures"]["B0"]["requirement_count"],
        "b0_requirement_id_digest": graph["readiness_closures"]["B0"]["requirement_id_digest"],
        "br0_requirement_count": graph["readiness_closures"]["BR0"]["requirement_count"],
        "graph_content_sha256": graph["content_sha256"],
        "verification_content_sha256": verification["content_sha256"],
        "written": written,
        "warnings": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT_CANDIDATE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = generate(args.repo_root, args.out)
    except (SotParseError, CycleError, SotIdentityMismatchError) as error:
        print(f"GENERATION_FAILED: {error}", file=sys.stderr)
        return 1
    print(f"GENERATION_OK sot_sha256={result['sot_sha256']} requirements={result['requirement_count']}")
    for name, digest in sorted(result["written"].items()):
        print(f"{digest}  {name}")
    print(f"B0_REQUIREMENT_COUNT: {result['b0_requirement_count']}")
    print(f"B0_REQUIREMENT_ID_DIGEST: {result['b0_requirement_id_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())