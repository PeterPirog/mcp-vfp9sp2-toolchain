# -*- coding: utf-8 -*-
"""Deterministic verification engine and verifier dispatcher.

Contains the contract self-consistency checks (REQ-B00-004 / REQ-PORT-019 /
REQ-PORT-020), the schema/layout/package/determinism/no-download report
builders used by ``tools/verify.py``, and the requirement-level verifier
dispatch semantics (REQ-AUTO-004):

* a PLANNED verifier can never produce PASS;
* an unknown requirement ID fails closed;
* applicability refusals surface as NOT_APPLICABLE with the deterministic
  applicability rule as evidence;
* a failed capability check surfaces as BLOCKED, never as PASS.

All report payloads are logical (no timestamps, no machine paths).
"""

from __future__ import annotations

import email.parser
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from ..canonical import artifact_json_bytes, logical_sha256, sorted_id_digest, strip_logical_metadata, canonical_sha256
from ..errors import SchemaCapabilityUnavailableError, SotIdentityMismatchError
from .sotparse import (
    CycleError,
    RequirementGraphBuilder,
    SotParseError,
    evaluate_requirement,
    find_cycle,
    readiness_closure,
    release_closure,
    strongly_connected_components,
)

NETWORK_IMPORT_PATTERN = re.compile(
    r"^\s*(import|from)\s+(socket|ssl|urllib\.request|urllib\.parse|http\.client|http\.server|"
    r"ftplib|smtplib|telnetlib|xmlrpc\.client|requests|httpx|aiohttp|urllib3)\b",
    re.MULTILINE,
)

# Assembled via concatenation so this file's own source does not literally
# contain the forbidden tokens it scans for (the sentinel must not self-match).
_INSTALL_TOKEN_A = "pip"
_INSTALL_TOKEN_B = "_main"
_INSTALL_TOKEN_C = "ensure"
_INSTALL_CALL_PATTERN = re.compile(
    "("
    + _INSTALL_TOKEN_A
    + r"\s+install|"
    + _INSTALL_TOKEN_A
    + _INSTALL_TOKEN_B
    + "|"
    + _INSTALL_TOKEN_C
    + _INSTALL_TOKEN_A
    + r"|subprocess\.[^\n]*("
    + _INSTALL_TOKEN_A
    + r"|npm|curl|wget|Invoke-WebRequest))"
)

# Assembled via token concatenation so this source file does not literally
# contain the phrases it scans for (the sentinel must not self-match).
_PHRASE_A = "simul"
_PHRASE_B = "fake"
_PLACEHOLDER_SUCCESS_PATTERNS = (
    re.compile(r"(?i)return\s+\{\s*[\"']status[\"']\s*:\s*[\"']PASS[\"'].*placeholder"),
    re.compile(r"(?i)" + _PHRASE_A + r"ate.*(success|result)"),
    re.compile(r"(?i)" + _PHRASE_B + r"e.*(success|result)"),
)

EXPECTED_LAYOUT = {
    "spec/SOURCE_OF_TRUTH.md": "file",
    "spec/requirements.graph.json": "file",
    "spec/verification.manifest.json": "file",
    "spec/compatibility.manifest.json": "file",
    "spec/acquisition.manifest.json": "file",
    "spec/dependency-lock.json": "file",
    "spec/dependency-lock.wheelhouse.txt": "file",
    "spec/threat-model.json": "file",
    "spec/schemas/requirement-graph.schema.json": "file",
    "spec/schemas/verification-manifest.schema.json": "file",
    "spec/schemas/compatibility-manifest.schema.json": "file",
    "spec/schemas/acquisition-manifest.schema.json": "file",
    "spec/schemas/dependency-lock.schema.json": "file",
    "spec/schemas/threat-model.schema.json": "file",
    "spec/schemas/bootstrap-invocation.schema.json": "file",
    "spec/schemas/brownfield-start-baseline.schema.json": "file",
    "spec/schemas/release-gate.schema.json": "file",
    "spec/schemas/evidence-index.schema.json": "file",
    "spec/schemas/capability-snapshot.schema.json": "file",
    "spec/schemas/provenance-record.schema.json": "file",
    "spec/schemas/execution-profile.schema.json": "file",
    "execution-profiles/generic.json": "file",
    "execution-profiles/converge.yaml": "file",
    "src/vfp_toolchain/__init__.py": "file",
    "src/vfp_toolchain/py.typed": "file",
    "tests/__init__.py": "file",
    "docs/architecture.md": "file",
    "docs/bootstrap.md": "file",
    "docs/verification.md": "file",
    "docs/capability-state.md": "file",
    "tools/generate_control_plane.py": "file",
    "tools/verify.py": "file",
    "third_party/README.md": "file",
    "evidence/README.md": "file",
    "README.md": "file",
    "LICENSE": "file",
    "CHANGELOG.md": "file",
    "SECURITY.md": "file",
    "CONTRIBUTING.md": "file",
    ".gitignore": "file",
    ".gitattributes": "file",
    "pyproject.toml": "file",
    ".github/workflows/ci.yml": "file",
}

REQUIRED_FILE_SET = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".gitignore",
    ".gitattributes",
    "pyproject.toml",
)

REPO_DIR_PREFIXES = ("release-gates", "evidence", "third_party", "src/vfp_toolchain", "tests", "docs", "tools", ".github/workflows")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_repo_artifacts(repo_root: Path) -> tuple[str, dict[str, Any], dict[str, Any]]:
    sot_bytes = (repo_root / "spec" / "SOURCE_OF_TRUTH.md").read_bytes()
    sot_text = sot_bytes.decode("utf-8")
    sot_sha256 = hashlib.sha256(sot_bytes).hexdigest().upper()
    graph = load_json(repo_root / "spec" / "requirements.graph.json")
    manifest = load_json(repo_root / "spec" / "verification.manifest.json")
    return sot_text, graph, manifest


def _check(check_name: str, ok: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"check": check_name, "status": "PASS" if ok else "FAIL", "details": details or {}}
    return entry


# ----------------------------------------------------------------------
# self-consistency (REQ-B00-004)
# ----------------------------------------------------------------------

def self_consistency_report(
    repo_root: Path,
    graph: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
    sot_text: str | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        if sot_text is None or graph is None or manifest is None:
            sot_text_l, graph_l, manifest_l = load_repo_artifacts(repo_root)
            sot_text = sot_text if sot_text is not None else sot_text_l
            graph = graph if graph is not None else graph_l
            manifest = manifest if manifest is not None else manifest_l
        assert sot_text is not None and graph is not None and manifest is not None
        builder = RequirementGraphBuilder(sot_text)
        regenerated = builder.build()
    except (SotParseError, CycleError) as error:
        return {
            "report": "CONTRACT_SELF_CONSISTENCY",
            "status": "FAIL",
            "checks": [_check("sot_reparse", False, {"error": str(error)})],
        }

    # 1. meta-contract (REQ-PORT-020)
    expected_shape = _parse_expected_shape(sot_text)
    checks.append(_check("meta_requirement_count", len(regenerated["requirements"]) == expected_shape["mandatory_records"], expected_shape))
    checks.append(
        _check(
            "meta_first_last_id",
            regenerated["requirements"][0]["id"] == expected_shape["first_id"]
            and regenerated["requirements"][-1]["id"] == expected_shape["last_id"],
            {"first": regenerated["requirements"][0]["id"], "last": regenerated["requirements"][-1]["id"]},
        )
    )
    revision_match = re.search(r"\*\*Revision:\*\*\s*(\d+)", sot_text)
    checks.append(
        _check(
            "meta_revision",
            bool(revision_match) and graph.get("sot_revision") == int(revision_match.group(1)),
            {"declared": revision_match.group(1) if revision_match else None, "graph": graph.get("sot_revision")},
        )
    )

    # 2. exact ID set equality + requirement text equality (REQ-PORT-009)
    sot_ids = [r["id"] for r in regenerated["requirements"]]
    graph_ids = [r["id"] for r in graph["requirements"]]
    checks.append(_check("graph_id_set_equality", sot_ids == graph_ids, {"count": len(graph_ids)}))
    sot_text_by_id = {r["id"]: r["text"] for r in regenerated["requirements"]}
    text_mismatches = [
        gid
        for gid in graph_ids
        if gid in sot_text_by_id and sot_text_by_id[gid] != next(r["text"] for r in graph["requirements"] if r["id"] == gid)
    ]
    checks.append(_check("requirement_text_equality", not text_mismatches, {"mismatches": text_mismatches[:10]}))
    checks.append(_check("no_duplicate_ids", len(set(graph_ids)) == len(graph_ids), {}))
    checks.append(
        _check("graph_document_order", graph_ids == sorted(graph_ids, key=graph_ids.index) and graph_ids[0] == "REQ-G00-001" and graph_ids[-1] == "REQ-P18-030", {})
    )

    # 3. lifecycle coverage and exactly-once assignment (REQ-PORT-014/021)
    lifecycles = {c: 0 for c in graph["lifecycle_classes"]}
    for record in graph["requirements"]:
        lifecycles[record["lifecycle"]] = lifecycles.get(record["lifecycle"], 0) + 1
    checks.append(_check("lifecycle_full_coverage", sum(lifecycles.values()) == len(graph_ids), dict(lifecycles)))
    recomputed_lifecycle = {r["id"]: r["lifecycle"] for r in regenerated["requirements"]}
    recorded_lifecycle = {r["id"]: r["lifecycle"] for r in graph["requirements"]}
    checks.append(
        _check(
            "lifecycle_canonical_equality",
            recomputed_lifecycle == recorded_lifecycle,
            {"mismatched": [rid for rid in recorded_lifecycle if recomputed_lifecycle.get(rid) != recorded_lifecycle[rid]][:10]},
        )
    )

    # 4. applicability coverage and schema-valid expressions (REQ-PORT-023/025)
    unknown_override_names = {
        r["applicability"]["override"]
        for r in graph["requirements"]
        if r["applicability"]["override"] is not None
        and r["applicability"]["override"] not in {o["name"] for o in graph["applicability_overrides"]}
    }
    checks.append(_check("applicability_override_coverage", not unknown_override_names, {"unknown": sorted(unknown_override_names)}))
    bad_expressions = []
    for record in graph["requirements"]:
        expression = record["applicability"]["expression"]
        if record["applicability"]["override"] is None and expression.get("default") != "ALWAYS":
            bad_expressions.append(record["id"])
    checks.append(_check("applicability_default_always", not bad_expressions, {"bad": bad_expressions[:10]}))

    # 5. milestone DAG acyclic + member count sanity (REQ-PORT-015/026)
    ms_parents = {m["name"]: m["after"] for m in graph["milestones"]}
    cycle = find_cycle(ms_parents)
    checks.append(_check("milestone_dag_acyclic", cycle is None, {"cycle": cycle}))

    # 6. requirement graph acyclic via INDEPENDENT SCC (REQ-PORT-010; audit rule 8)
    edges = {record["id"]: list(record["prerequisite_ids"]) for record in graph["requirements"]}
    big_sccs = [c for c in strongly_connected_components(edges) if len(c) > 1]
    checks.append(_check("requirement_graph_acyclic_independent_scc", not big_sccs, {"scc_over_1": big_sccs[:5]}))
    dfs_cycle = find_cycle(edges)
    checks.append(_check("requirement_graph_acyclic_dfs", dfs_cycle is None, {"cycle": dfs_cycle}))

    # 7. old four-node cycle negative control (audit Part E)
    old_back_edge = "REQ-P00-005" in edges.get("REQ-P17-001", [])
    checks.append(
        _check(
            "old_four_node_cycle_absent",
            not old_back_edge,
            {
                "regression_ids": ["REQ-P00-005", "REQ-P00-006", "REQ-P03-001", "REQ-P17-001"],
                "back_edge_REQ-P17-001->REQ-P00-005": old_back_edge,
            },
        )
    )

    # 8. readiness closures exactly equal graph-derived closures (REQ-B00-004)
    context = dict(graph["readiness_closures"]["B0"]["context"])
    b0_re = readiness_closure(regenerated, "B0", context)
    b0_re["requirement_id_digest"] = sorted_id_digest(b0_re["requirement_ids"])
    recorded_b0 = graph["readiness_closures"]["B0"]
    checks.append(
        _check(
            "b0_closure_equality",
            recorded_b0["requirement_ids"] == b0_re["requirement_ids"]
            and recorded_b0["requirement_count"] == b0_re["requirement_count"]
            and recorded_b0["requirement_id_digest"] == b0_re["requirement_id_digest"],
            {"recorded_count": recorded_b0["requirement_count"], "recomputed": b0_re["requirement_count"]},
        )
    )
    brownfield_context = dict(graph["readiness_closures"]["BR0"]["context"])
    br0_re = readiness_closure(regenerated, "BR0", brownfield_context)
    br0_re["requirement_id_digest"] = sorted_id_digest(br0_re["requirement_ids"])
    recorded_br0 = graph["readiness_closures"]["BR0"]
    checks.append(
        _check(
            "br0_closure_equality",
            recorded_br0["requirement_ids"] == br0_re["requirement_ids"] and recorded_br0["requirement_count"] == br0_re["requirement_count"],
            {"recorded_count": recorded_br0["requirement_count"], "recomputed": br0_re["requirement_count"]},
        )
    )

    # 9. release closures: cumulative + transitive prerequisites + no earlier->later dependency (REQ-B00-004)
    release_failures: list[dict[str, Any]] = []
    exec_index = {record["id"]: record["execution_milestone"] for record in graph["requirements"]}
    for version, closure in graph["release_closures"].items():
        recomputed = release_closure(regenerated, version, closure["context"])
        if recomputed["requirement_ids"] != closure["requirement_ids"]:
            release_failures.append({"release": version, "reason": "closure_mismatch"})
        topo_order = graph["milestone_topological_order"]
        for rid in closure["requirement_ids"]:
            exec_ms = exec_index.get(rid)
            if exec_ms is not None and exec_ms in topo_order:
                if rid not in closure["requirement_ids"]:
                    release_failures.append({"release": version, "reason": "member_missing", "id": rid})
        # no earlier-gate depends on later milestone: every member's exec milestone must be in the closure's cumulative set
        for rid in closure["requirement_ids"]:
            exec_ms = exec_index.get(rid)
            if exec_ms is not None and exec_ms not in closure["cumulative_milestones"]:
                release_failures.append({"release": version, "reason": "later_milestone_dependency", "id": rid, "exec_milestone": exec_ms})
    checks.append(_check("release_closures_consistent", not release_failures, {"failures": release_failures[:10]}))

    # 10. verification manifest set equality (REQ-AUTO-003)
    manifest_ids = list(manifest["requirements"].keys())
    checks.append(_check("verification_manifest_set_equality", sorted(manifest_ids) == sorted(graph_ids), {"count": len(manifest_ids)}))
    checks.append(_check("verification_manifest_no_false_pass", _manifest_has_no_false_pass(manifest), {}))
    if repo_root is not None:
        dangling = _dangling_executable_references(manifest, repo_root)
        checks.append(_check("no_dangling_executable_references", not dangling, {"dangling": dangling}))

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "report": "CONTRACT_SELF_CONSISTENCY",
        "status": "FAIL" if failed else "PASS",
        "sot_sha256": graph.get("sot_sha256"),
        "graph_content_sha256": graph.get("content_sha256"),
        "requirement_count": len(graph_ids),
        "checks": checks,
        "failed_check_count": len(failed),
    }


def _parse_expected_shape(sot_text: str) -> dict[str, Any]:
    text_block = re.search(r"```text\s*\n(.*?)```", sot_text, re.DOTALL)
    expected = {"mandatory_records": None, "first_id": None, "last_id": None}
    if text_block:
        body = text_block.group(1)
        m = re.search(r"mandatory records:\s*(\d+)", body)
        if m:
            expected["mandatory_records"] = int(m.group(1))
        m = re.search(r"first id:\s*(REQ-[A-Z0-9]+-\d{3})", body)
        if m:
            expected["first_id"] = m.group(1)
        m = re.search(r"last id:\s*(REQ-[A-Z0-9]+-\d{3})", body)
        if m:
            expected["last_id"] = m.group(1)
    return expected


def _manifest_has_no_false_pass(manifest: dict[str, Any]) -> bool:
    for record in manifest["requirements"].values():
        if record.get("current_state") == "PASS" and not record.get("state_evidence"):
            return False
    for verifier in manifest["verifiers"].values():
        if verifier.get("state") == "PLANNED" and verifier.get("command") is not None:
            return False
    return True


def _dangling_executable_references(manifest: dict[str, Any], repo_root: Path) -> list[str]:
    dangling: list[str] = []
    for verifier_id, verifier in manifest["verifiers"].items():
        if verifier.get("state") != "EXECUTABLE":
            continue
        command = verifier.get("command")
        if not command:
            dangling.append(f"{verifier_id}: executable without command")
            continue
        for arg in command:
            if isinstance(arg, str) and ("/" in arg or "\\" in arg) and not arg.startswith("-"):
                candidate = repo_root / arg
                if not candidate.exists():
                    dangling.append(f"{verifier_id}: missing path {arg}")
    return dangling


# ----------------------------------------------------------------------
# schema validation (REQ-G00-025 / REQ-PORT-022)
# ----------------------------------------------------------------------

def schema_validation_report(repo_root: Path) -> dict[str, Any]:
    schemas_dir = repo_root / "spec" / "schemas"
    documents = sorted(path.name for path in schemas_dir.glob("*.schema.json"))
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return {
            "report": "SCHEMA_VALIDATION",
            "status": "BLOCKED",
            "reason": "SCHEMA_CAPABILITY_UNAVAILABLE",
            "message": "jsonschema is not importable in this interpreter; install the locked dev profile offline from spec/dependency-lock.wheelhouse.txt.",
            "schema_document_count": len(documents),
        }

    validator_cls = jsonschema.Draft202012Validator
    checks: list[dict[str, Any]] = []
    schemas: dict[str, Any] = {}
    for name in documents:
        document = load_json(schemas_dir / name)
        try:
            validator_cls.check_schema(document)
            checks.append(_check(f"schema_document:{name}", True, {}))
            schemas[name] = document
        except jsonschema.exceptions.SchemaError as error:  # type: ignore[attr-defined]
            checks.append(_check(f"schema_document:{name}", False, {"error": str(error)[:400]}))

    artifact_bindings = {
        "requirements.graph.json": "requirement-graph.schema.json",
        "verification.manifest.json": "verification-manifest.schema.json",
        "compatibility.manifest.json": "compatibility-manifest.schema.json",
        "acquisition.manifest.json": "acquisition-manifest.schema.json",
        "dependency-lock.json": "dependency-lock.schema.json",
        "threat-model.json": "threat-model.schema.json",
        "readiness-b0.json": "release-gate.schema.json",
        "readiness-br0.json": "release-gate.schema.json",
        "greenfield-scenario.json": "release-gate.schema.json",
        "index.json": "release-gate.schema.json",
    }
    for release_version in ("0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "1.0.0"):
        artifact_bindings[f"release-{release_version}.json"] = "release-gate.schema.json"

    instance_failures: list[dict[str, Any]] = []
    for artifact_name, schema_name in sorted(artifact_bindings.items()):
        if schema_name not in schemas:
            instance_failures.append({"artifact": artifact_name, "schema": schema_name, "error": "required schema document missing"})
            continue
        artifact_path = repo_root / "release-gates" / artifact_name
        if not artifact_path.exists():
            artifact_path = repo_root / "spec" / artifact_name
        if not artifact_path.exists():
            instance_failures.append({"artifact": artifact_name, "error": "missing artifact"})
            continue
        instance = load_json(artifact_path)
        schema = schemas[schema_name]
        validator = jsonschema.validators.validator_for(schema)(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        if errors:
            first = errors[0]
            instance_failures.append(
                {
                    "artifact": artifact_name,
                    "schema": schema_name,
                    "error": f"{'/'.join(str(p) for p in first.absolute_path) or '$'}: {first.message[:300]}",
                }
            )
    checks.append(_check("artifact_schema_conformance", not instance_failures, {"failures": instance_failures[:10]}))

    profiles: list[tuple[str, str]] = [
        ("execution-profiles/generic.json", "execution-profile.schema.json"),
    ]
    profile_failures = []
    for profile_path, schema_name in profiles:
        if schema_name not in schemas:
            profile_failures.append({"profile": profile_path, "error": "required schema document missing"})
            continue
        profile = load_json(repo_root / profile_path)
        schema = schemas[schema_name]
        validator = jsonschema.validators.validator_for(schema)(schema)
        errors = sorted(validator.iter_errors(profile), key=lambda e: list(e.absolute_path))
        if errors:
            first = errors[0]
            profile_failures.append({"profile": profile_path, "error": f"{'/'.join(str(p) for p in first.absolute_path) or '$'}: {first.message[:300]}"})
    checks.append(_check("profile_schema_conformance", not profile_failures, {"failures": profile_failures}))

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "report": "SCHEMA_VALIDATION",
        "status": "FAIL" if failed else "PASS",
        "schema_document_count": len(documents),
        "artifact_instance_count": len(artifact_bindings) + len(profiles),
        "checks": checks,
    }


# ----------------------------------------------------------------------
# layout / package / determinism / no-download / test-map reports
# ----------------------------------------------------------------------

def layout_report(repo_root: Path) -> dict[str, Any]:
    missing = [path for path, kind in sorted(EXPECTED_LAYOUT.items()) if not (repo_root / path).is_file()]
    wrong_kind = [path for path, kind in sorted(EXPECTED_LAYOUT.items()) if kind == "file" and (repo_root / path).is_dir()]
    required_missing = [name for name in REQUIRED_FILE_SET if not (repo_root / name).is_file()]

    sot_candidate = repo_root / "spec" / "SOURCE_OF_TRUTH.md"
    sot_ok = sot_candidate.is_file() and hashlib.sha256(sot_candidate.read_bytes()).hexdigest().upper() == load_json(repo_root / "spec" / "requirements.graph.json")["sot_sha256"]

    license_ok = (repo_root / "LICENSE").is_file() and "MIT License" in (repo_root / "LICENSE").read_text(encoding="utf-8")
    gitattributes = (repo_root / ".gitattributes").read_text(encoding="utf-8") if (repo_root / ".gitattributes").is_file() else ""
    sot_protected = "SOURCE_OF_TRUTH.md" in gitattributes and "-text" in gitattributes.split("SOURCE_OF_TRUTH.md", 1)[1][:12]
    binary_families = all(family in gitattributes for family in ("*.dbf", "*.fpt", "*.cdx", "*.scx", "*.vcx"))

    checks = [
        _check("canonical_layout_complete", not missing, {"missing": missing}),
        _check("canonical_layout_kinds", not wrong_kind, {"wrong_kind": wrong_kind}),
        _check("required_file_set", not required_missing, {"missing": required_missing}),
        _check("sot_byte_identity", sot_ok, {}),
        _check("mit_license", license_ok, {}),
        _check("gitattributes_sot_non_text", sot_protected, {}),
        _check("gitattributes_vfp_binary_families", binary_families, {}),
    ]
    failed = [c for c in checks if c["status"] != "PASS"]
    return {"report": "CONTROL_PLANE_LAYOUT", "status": "FAIL" if failed else "PASS", "checks": checks}


def _parse_project_metadata(pyproject_text: str) -> dict[str, Any]:
    """Deterministic stdlib-only extraction of the [project] fields we verify
    (tomllib is 3.11+; the supported range starts at 3.10)."""
    section = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", pyproject_text, re.MULTILINE | re.DOTALL)
    body = section.group(1) if section else ""
    metadata: dict[str, Any] = {}
    for key in ("name", "version", "requires-python"):
        match = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\"]+)\"", body, re.MULTILINE)
        if match:
            metadata[key] = match.group(1)
    scripts = {}
    for script in ("vfp-toolchain", "mcp-vfp9sp2"):
        match = re.search(rf"^{re.escape(script)}\s*=\s*\"([^\"]+)\"", pyproject_text, re.MULTILINE)
        if match:
            scripts[script] = match.group(1)
    metadata["scripts"] = scripts
    dependencies_match = re.search(r"^dependencies\s*=\s*\[([^\]]*)\]", body, re.MULTILINE)
    metadata["dependencies"] = [] if dependencies_match else ["UNPARSED"]
    if dependencies_match and dependencies_match.group(1).strip():
        metadata["dependencies"] = ["NON_EMPTY"]
    build_match = re.search(r"^build-backend\s*=\s*\"([^\"]+)\"", pyproject_text, re.MULTILINE)
    metadata["build_backend"] = build_match.group(1) if build_match else None
    return metadata


def package_report(repo_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(repo_root / "src"))
    checks: list[dict[str, Any]] = []
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    project = _parse_project_metadata(pyproject)
    checks.append(_check("distribution_name", project.get("name") == "mcp-vfp9sp2-toolchain", {"name": project.get("name")}))
    checks.append(_check("requires_python", project.get("requires-python") == ">=3.10,<3.15", {"value": project.get("requires-python")}))
    scripts = project.get("scripts", {})
    checks.append(
        _check(
            "console_entry_points",
            scripts.get("vfp-toolchain") == "vfp_toolchain.cli:main" and scripts.get("mcp-vfp9sp2") == "vfp_toolchain.mcp:main",
            scripts,
        )
    )
    checks.append(_check("no_runtime_dependencies", project.get("dependencies") == [], {"dependencies": project.get("dependencies")}))
    checks.append(_check("typed_package_marker", (repo_root / "src" / "vfp_toolchain" / "py.typed").is_file(), {}))
    checks.append(_check("pep517_build_backend", "setuptools.build_meta" in str(project.get("build_backend", "")), {}))

    import importlib

    import vfp_toolchain
    from vfp_toolchain import capabilities as caps
    from vfp_toolchain.core import CoreService

    checks.append(_check("import_vfp_toolchain", bool(vfp_toolchain.__version__), {"version": vfp_toolchain.__version__}))
    discovery = caps.discover()
    truthful = all(not entry["available"] and entry["state"] == "NOT_IMPLEMENTED" for entry in discovery["capabilities"])
    checks.append(_check("truthful_empty_capability_state", truthful and discovery["implemented_count"] == 0, {}))
    side_effect_free = caps.discover() == discovery
    checks.append(_check("capability_discovery_deterministic", side_effect_free, {}))

    core = CoreService()
    describe = core.describe()
    checks.append(_check("core_describe_envelope", describe["status"] == "PASS" and describe["operation"] == "core.describe", {}))
    refusal_ok = True
    try:
        core.execute("data.schema_inspect")
        refusal_ok = False
    except Exception as error:  # noqa: BLE001 - typed refusal expected
        refusal_ok = getattr(error, "code", "") == "CAPABILITY_NOT_IMPLEMENTED"
    checks.append(_check("truthful_domain_refusal", refusal_ok, {}))
    version_pep440_dev = bool(re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+|a\d+|b\d+|rc\d+)?", str(vfp_toolchain.__version__))) and ".dev" in str(vfp_toolchain.__version__)
    checks.append(_check("dev_version_cannot_be_confused_with_release", version_pep440_dev, {"version": vfp_toolchain.__version__}))

    src_dir = repo_root / "src" / "vfp_toolchain"
    network_hits: list[str] = []
    install_hits: list[str] = []
    placeholder_hits: list[str] = []
    for path in sorted(src_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if NETWORK_IMPORT_PATTERN.search(text):
            network_hits.append(path.relative_to(repo_root).as_posix())
        if _INSTALL_CALL_PATTERN.search(text):
            install_hits.append(path.relative_to(repo_root).as_posix())
        for pattern in _PLACEHOLDER_SUCCESS_PATTERNS:
            if pattern.search(text):
                placeholder_hits.append(path.relative_to(repo_root).as_posix())
    checks.append(_check("no_network_imports_in_package", not network_hits, {"hits": network_hits}))
    checks.append(_check("no_package_install_calls_in_package", not install_hits, {"hits": install_hits}))
    checks.append(_check("no_placeholder_success_patterns", not placeholder_hits, {"hits": placeholder_hits}))

    failed = [c for c in checks if c["status"] != "PASS"]
    return {"report": "PACKAGE_FOUNDATION", "status": "FAIL" if failed else "PASS", "checks": checks}


def no_download_report(repo_root: Path) -> dict[str, Any]:
    src_dir = repo_root / "src" / "vfp_toolchain"
    hits: list[str] = []
    for path in sorted(src_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if NETWORK_IMPORT_PATTERN.search(text) or _INSTALL_CALL_PATTERN.search(text):
            hits.append(path.relative_to(repo_root).as_posix())
    runtime_deps_ok = 'dependencies = []' in (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    checks = [
        _check("no_network_or_install_imports", not hits, {"hits": hits}),
        _check("empty_runtime_dependency_declaration", runtime_deps_ok, {}),
    ]
    failed = [c for c in checks if c["status"] != "PASS"]
    return {"report": "NO_RUNTIME_DOWNLOAD", "status": "FAIL" if failed else "PASS", "checks": checks}


def determinism_report(repo_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(repo_root / "tools"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("candidate_generator", repo_root / "tools" / "generate_control_plane.py")
    generator = importlib.util.module_from_spec(spec)
    sys.modules["candidate_generator"] = generator
    spec.loader.exec_module(generator)  # type: ignore[union-attr]

    artifacts: list[dict[str, tuple[str, str]]] = []
    with tempfile.TemporaryDirectory(prefix="vfp-determinism-") as tmp:
        for run_index in (1, 2):
            out_dir = Path(tmp) / f"run{run_index}"
            result = generator.generate(repo_root, out_dir)
            digests = dict(result["written"])
            artifacts.append((out_dir, digests))
        (dir_a, digests_a), (dir_b, digests_b) = artifacts
        mismatches: list[str] = []
        for name in sorted(set(digests_a) | set(digests_b)):
            if digests_a.get(name) != digests_b.get(name):
                mismatches.append(name)
            else:
                bytes_a = (dir_a / name).read_bytes()
                bytes_b = (dir_b / name).read_bytes()
                content_a = strip_logical_metadata(load_json(dir_a / name))
                content_b = strip_logical_metadata(load_json(dir_b / name))
                if content_a != content_b or canonical_sha256(content_a) != digests_a[name]:
                    mismatches.append(name + " (logical)")
        checks = [
            _check("double_generation_logical_identity", not mismatches, {"mismatched": mismatches}),
            _check(
                "content_hash_self_consistency",
                all(canonical_sha256(strip_logical_metadata(load_json(dir_a / name))) == digests_a[name] for name in digests_a),
                {},
            ),
        ]
    failed = [c for c in checks if c["status"] != "PASS"]
    return {"report": "CONTROL_PLANE_DETERMINISM", "status": "FAIL" if failed else "PASS", "checks": checks}


def test_map_report(repo_root: Path) -> dict[str, Any]:
    tests_root = repo_root / "tests"
    mapping: dict[str, list[str]] = {}
    for path in sorted(tests_root.rglob("test_*.py")):
        module = path.stem
        package = path.parent.relative_to(repo_root).as_posix().replace("/", ".")
        dotted = f"{package}.{module}"
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^REQUIREMENT_IDS\s*=\s*\(([^)]*)\)", text, re.MULTILINE | re.DOTALL)
        if match:
            ids = re.findall(r"REQ-[A-Z0-9]+-\d{3}", match.group(1))
            for rid in ids:
                mapping.setdefault(rid, []).append(dotted)
    return {
        "report": "TEST_EVIDENCE_MAP",
        "status": "PASS",
        "requirement_to_test_modules": {rid: sorted(set(mods)) for rid, mods in sorted(mapping.items())},
    }


def invocation_report(evidence_path: Path) -> dict[str, Any]:
    from ..bootstrap.invocation import build_invocation, invocation_hashes, secret_scan

    payload = load_json(Path(evidence_path))
    inputs = payload.get("invocation_inputs", {})
    invocation = build_invocation(inputs)
    hashes = invocation_hashes(invocation)
    expected = payload.get("hashes", {}).get("bootstrap_invocation_logical_sha256")
    ok = expected == hashes["bootstrap_invocation_logical_sha256"]
    secrets = secret_scan(invocation)
    return {
        "report": "BOOTSTRAP_INVOCATION_VALIDATION",
        "status": "PASS" if ok and not secrets else "FAIL",
        "checks": [
            _check("invocation_hash_recomputation", ok, {"recorded": expected, "recomputed": hashes["bootstrap_invocation_logical_sha256"]}),
            _check("no_secret_shaped_fields", not secrets, {"findings": secrets}),
        ],
        "hashes": hashes,
    }


# ----------------------------------------------------------------------
# canonical dependency lock verification (REQ-G00-018 / REQ-G00-022 /
# REQ-P00-024 / REQ-AUTO-045)
# ----------------------------------------------------------------------

DEPENDENCY_LOCK_RELPATH = "spec/dependency-lock.json"
DEPENDENCY_LOCK_WHEELHOUSE_MANIFEST_RELPATH = "spec/dependency-lock.wheelhouse.txt"
DEPENDENCY_LOCK_WHEELHOUSE_ENV_VAR = "VFP_TOOLCHAIN_WHEELHOUSE"
APPROVED_GREENFIELD_PACKAGE_INDEX = "https://pypi.org/simple"
APPROVED_GREENFIELD_ARTIFACT_HOST = "https://files.pythonhosted.org"

# Deterministic role classification for the materialized pyproject
# declarations. A dev-profile entry outside every table is a classification
# failure (fail closed; never silently resolved into a guessed role).
_BUILD_ROLE_TOOL_NAMES = ("build", "wheel")
_TEST_ROLE_TOOL_NAMES = ("pytest",)
_SCHEMA_VALIDATION_ROLE_TOOL_NAMES = ("jsonschema", "rpds-py")

# Fixed reason strings for declared direct constraints (deterministic, shared
# by the lock builder and this verifier so both emit identical content).
_DECLARATION_REASONS: dict[tuple[str, str], str] = {
    ("build", "setuptools"): "PEP 517 build backend (wheel/sdist)",
    ("build", "build"): "PEP 517/621 build frontend invoked by the deterministic B0 build step",
    ("build", "wheel"): "wheel packaging helper for the wheel build",
    ("test", "pytest"): "deterministic pytest runner for the candidate suite",
    ("schema_validation", "jsonschema"): "JSON Schema 2020-12 artifact validation",
    ("schema_validation", "rpds-py"): "matrix-coherent exact pin of the referencing persistence engine (wheel tags for the full supported matrix)",
}

_REQUIREMENT_SPLIT_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[.*\])?(.*)$")
_CONSTRAINT_OPERATOR_RE = re.compile(r"^(>=|<=|==|!=|<|>|~=)\s*([0-9][0-9A-Za-z._*+-]*)$")
_RELEASE_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


class DependencyDeclarationClassificationError(Exception):
    """A declared dependency entry could not be classified deterministically."""


def _pep503_normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _split_requirement_declaration(entry: str) -> tuple[str, str]:
    """Split a declared requirement like ``setuptools>=68`` into (name, constraint)."""
    match = _REQUIREMENT_SPLIT_RE.match(entry.strip())
    if match is None:
        raise DependencyDeclarationClassificationError(f"unparseable requirement declaration: {entry!r}")
    name, extras, constraint = match.group(1), match.group(2), match.group(3).strip()
    if extras:
        raise DependencyDeclarationClassificationError(
            f"extras are outside the B0 dependency-declaration vocabulary: {entry!r}"
        )
    return name, constraint


def _toml_section_body(text: str, section: str) -> str:
    match = re.search(rf"^\[{re.escape(section)}\]\s*$(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def _toml_string_array(section_body: str, key: str) -> list[str]:
    """Extract the string values of ``key = [ ... ]`` inside a TOML section body."""
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\[(.*?)\]", section_body, re.DOTALL)
    if match is None:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def _declared_entry(role: str, name: str, constraint: str) -> dict[str, str]:
    return {
        "distribution": name,
        "constraint": constraint,
        "reason": _DECLARATION_REASONS.get(
            (role, _pep503_normalize(name)), f"declared {role} dependency ({name})"
        ),
    }


def declared_direct_constraints(pyproject_text: str) -> dict[str, list[dict[str, str]]]:
    """Deterministic B0 dependency-declaration extraction from pyproject.toml.

    Fail closed: an unclassifiable entry raises instead of guessing a role, so
    the lock can never declare a dependency whose role is not deterministic.
    """
    constraints: dict[str, list[dict[str, str]]] = {
        "runtime": [],
        "build": [],
        "test": [],
        "schema_validation": [],
    }
    build_backend = [
        _split_requirement_declaration(value)
        for value in _toml_string_array(_toml_section_body(pyproject_text, "build-system"), "requires")
    ]
    runtime = [
        _split_requirement_declaration(value)
        for value in _toml_string_array(_toml_section_body(pyproject_text, "project"), "dependencies")
    ]
    dev_profile = [
        _split_requirement_declaration(value)
        for value in _toml_string_array(_toml_section_body(pyproject_text, "project.optional-dependencies"), "dev")
    ]

    build_backend_names = {_pep503_normalize(name) for name, _ in build_backend}
    for name, constraint in build_backend:
        constraints["build"].append(_declared_entry("build", name, constraint))
    for name, constraint in runtime:
        constraints["runtime"].append(_declared_entry("runtime", name, constraint))
    for name, constraint in dev_profile:
        if _pep503_normalize(name) in build_backend_names:
            continue  # already declared by [build-system].requires
        normalized = _pep503_normalize(name)
        if normalized in _BUILD_ROLE_TOOL_NAMES:
            role = "build"
        elif normalized in _TEST_ROLE_TOOL_NAMES:
            role = "test"
        elif normalized in _SCHEMA_VALIDATION_ROLE_TOOL_NAMES:
            role = "schema_validation"
        else:
            raise DependencyDeclarationClassificationError(
                f"dev-profile entry {name!r} has no deterministic B0 role classification"
            )
        constraints[role].append(_declared_entry(role, name, constraint))
    for entries in constraints.values():
        entries.sort(key=lambda entry: entry["distribution"])
    return constraints


def declared_optional_profiles(pyproject_text: str) -> dict[str, list[str]]:
    """Deterministic optional-profile extraction (distribution names, sorted)."""
    dev_values = [
        _split_requirement_declaration(value)[0]
        for value in _toml_string_array(_toml_section_body(pyproject_text, "project.optional-dependencies"), "dev")
    ]
    return {"dev": sorted(_pep503_normalize(name) for name in dev_values)}


def _release_version_tuple(version: str) -> tuple[int, ...] | None:
    """PEP 440 subset: epoch-less, release-segment-only versions (B0 vocabulary)."""
    if not _RELEASE_VERSION_RE.fullmatch(version.strip()):
        return None
    return tuple(int(part) for part in version.strip().split("."))


def _compare_release_versions(left: str, right: str) -> int | None:
    left_tuple, right_tuple = _release_version_tuple(left), _release_version_tuple(right)
    if left_tuple is None or right_tuple is None:
        return None
    width = max(len(left_tuple), len(right_tuple))
    left_tuple = left_tuple + (0,) * (width - len(left_tuple))
    right_tuple = right_tuple + (0,) * (width - len(right_tuple))
    return (left_tuple > right_tuple) - (left_tuple < right_tuple)


def _release_constraint_satisfied(constraint: str, version: str) -> bool | None:
    """Evaluate a release-segment constraint (>=/<=/==/!=/</>) against *version*.

    Returns None when the constraint or version is outside the deterministic
    subset; callers must fail closed on None, never silently relax.
    """
    match = _CONSTRAINT_OPERATOR_RE.match(constraint.strip())
    if match is None:
        return None
    operator, bound = match.group(1), match.group(2)
    if "*" in bound:
        return None
    ordering = _compare_release_versions(version, bound)
    if ordering is None:
        return None
    return {
        "==": ordering == 0,
        "!=": ordering != 0,
        ">=": ordering >= 0,
        "<=": ordering <= 0,
        ">": ordering > 0,
        "<": ordering < 0,
    }.get(operator)


def _wheel_filename_parts(filename: str) -> tuple[str, str] | None:
    """Parse a wheel filename into (escaped distribution, version) per PEP 427."""
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) == 6:
        if not re.fullmatch(r"[0-9]+", parts[2]):
            return None
        del parts[2]
    if len(parts) != 5:
        return None
    distribution, version = parts[0], parts[1]
    if not distribution or not version:
        return None
    return distribution, version


def _wheel_artifact_record(filename: str) -> dict[str, Any] | None:
    """Validate one wheel filename against the lock's distribution/version data."""
    parts = _wheel_filename_parts(filename)
    if parts is None:
        return None
    return {"distribution": _pep503_normalize(parts[0]), "version": parts[1], "filename": filename}


def _wheel_dist_info_metadata(wheel_path: Path) -> dict[str, Any] | None:
    """Read the wheel's OWN .dist-info/METADATA payload (stdlib only).

    The wheel's own dist-info directory is the exact root-level
    ``{escaped_distribution}-{version}.dist-info`` name; wheels that vendor
    third-party packages carry additional nested dist-info trees which must
    never be mistaken for the wheel metadata.
    """
    parts = _wheel_filename_parts(wheel_path.name)
    if parts is None:
        return None
    expected_metadata_name = f"{parts[0]}-{parts[1]}.dist-info/METADATA"
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            if expected_metadata_name not in archive.namelist():
                return None
            message = email.parser.BytesParser().parsebytes(archive.read(expected_metadata_name))
    except (OSError, zipfile.BadZipFile):
        return None
    return {
        "name": message.get("Name", ""),
        "version": message.get("Version", ""),
        "requires_dist": [str(value) for value in (message.get_all("Requires-Dist") or [])],
    }


def _lock_marker_environments() -> list[dict[str, str]]:
    """The two extreme environments of the supported matrix (Windows-only).

    Every variable a PEP 508 marker can reference is pinned to a fixed
    deterministic value, so marker evaluation never depends on the machine
    running the verifier.
    """
    base = {
        "sys_platform": "win32",
        "platform_system": "Windows",
        "platform_machine": "AMD64",
        "platform_release": "",
        "platform_version": "",
        "os_name": "nt",
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
        "extra": "",
    }
    py310 = dict(base, python_version="3.10", python_full_version="3.10.11", implementation_version="3.10.11")
    py314 = dict(base, python_version="3.14", python_full_version="3.14.0", implementation_version="3.14.0")
    return [py310, py314]


def compute_lock_closure(
    wheelhouse: Path,
    direct_constraints: dict[str, list[dict[str, str]]],
    optional_profiles: dict[str, list[str]],
    resolved_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Recompute the dependency closure from the locked wheelhouse metadata.

    *resolved_artifacts* maps filename -> {distribution, version} for every
    locked artifact. Returns edges (parent -> children), the reached
    distribution set, and per-distribution profile membership. Failures are
    recorded as ``errors``; empty errors mean the recomputation is valid.
    """
    try:
        try:
            from packaging.requirements import Requirement as PackagingRequirement
        except ImportError:  # packaging < 26 module layout
            from packaging.requirement import Requirement as PackagingRequirement
    except ImportError:
        return {
            "status": "BLOCKED",
            "reason": "PACKAGING_CAPABILITY_UNAVAILABLE",
            "message": "packaging is not importable in this interpreter; install the locked dev profile offline.",
            "edges": {},
            "closure_names": [],
            "profile_membership": {},
            "errors": [],
        }

    resolved_names = {record["distribution"] for record in resolved_artifacts.values()}
    errors: list[str] = []
    edges: dict[str, set[str]] = {}
    metadata_by_name: dict[str, dict[str, Any]] = {}
    envs = _lock_marker_environments()

    for filename, record in sorted(resolved_artifacts.items()):
        wheel_path = wheelhouse / filename
        if not wheel_path.is_file():
            errors.append(f"missing wheel for metadata parse: {filename}")
            continue
        metadata = _wheel_dist_info_metadata(wheel_path)
        if metadata is None:
            errors.append(f"unreadable .dist-info/METADATA: {filename}")
            continue
        metadata_name = _pep503_normalize(metadata.get("name", ""))
        if metadata_name != record["distribution"]:
            errors.append(
                f"wheel metadata name mismatch for {filename}: {metadata_name} != {record['distribution']}"
            )
        if metadata.get("version", "") != record["version"]:
            errors.append(f"wheel metadata version mismatch for {filename}")
        metadata_by_name[record["distribution"]] = metadata

    for parent, metadata in sorted(metadata_by_name.items()):
        for raw in metadata["requires_dist"]:
            try:
                requirement = PackagingRequirement(raw)
            except Exception as error:  # noqa: BLE001 - any malformed declaration fails closed
                errors.append(f"unparseable Requires-Dist in {parent}: {raw[:120]} ({error})")
                continue
            required_in_environment = True
            if requirement.marker is not None:
                required_in_environment = any(requirement.marker.evaluate(env) for env in envs)
            if not required_in_environment:
                continue  # not part of any supported-environment closure (e.g. optional extras)
            if requirement.extras:
                errors.append(f"extras outside the B0 closure vocabulary in {parent}: {raw[:120]}")
                continue
            child = _pep503_normalize(requirement.name)
            if child == parent:
                continue
            if child not in resolved_names:
                errors.append(f"closure incomplete: {parent} requires {child}, which is not in the lock")
                continue
            edges.setdefault(parent, set()).add(child)

    closure_names: set[str] = set()
    stack = [
        _pep503_normalize(entry["distribution"])
        for entries in direct_constraints.values()
        for entry in entries
    ]
    while stack:
        name = stack.pop()
        if name in closure_names:
            continue
        closure_names.add(name)
        stack.extend(edges.get(name, ()))
    missing_from_resolved = sorted(closure_names - resolved_names)
    for name in missing_from_resolved:
        errors.append(f"closure requires {name}, which has no resolved artifact")

    direct_memberships: dict[str, set[str]] = {}
    for role, entries in direct_constraints.items():
        for entry in entries:
            direct_memberships.setdefault(_pep503_normalize(entry["distribution"]), set()).add(role)
    for profile_name, distributions in optional_profiles.items():
        for name in distributions:
            direct_memberships.setdefault(_pep503_normalize(name), set()).add(profile_name)

    profile_membership: dict[str, set[str]] = {name: set() for name in resolved_names}
    for name in resolved_names:
        profile_membership[name] |= direct_memberships.get(name, set())
    changed = True
    while changed:
        changed = False
        for parent, children in sorted(edges.items()):
            parent_membership = profile_membership.get(parent, set())
            if not parent_membership:
                continue
            for child in children:
                if not parent_membership <= profile_membership.get(child, set()):
                    profile_membership[child] = profile_membership.get(child, set()) | parent_membership
                    changed = True

    return {
        "status": "PASS" if not errors else "FAIL",
        "edges": {parent: sorted(children) for parent, children in sorted(edges.items())},
        "closure_names": sorted(closure_names),
        "profile_membership": {name: sorted(values) for name, values in sorted(profile_membership.items())},
        "errors": errors,
    }


def _blocked_check(name: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"check": name, "status": "BLOCKED", "details": details}


def dependency_lock_report(
    repo_root: Path,
    wheelhouse: Path | None = None,
    invocation_evidence: Path | None = None,
) -> dict[str, Any]:
    """Independent verification of the frozen canonical dependency lock.

    Lock-internal checks are stdlib-only. Wheelhouse-dependent checks
    (artifact hashes, wheelhouse equality, closure recomputation from wheel
    metadata) run only when *wheelhouse* is provided; they are BLOCKED
    (truthful) otherwise. All failures are deterministic.
    """
    lock_path = repo_root / DEPENDENCY_LOCK_RELPATH
    checks: list[dict[str, Any]] = []

    lock: dict[str, Any] | None = None
    if lock_path.is_file():
        try:
            lock = load_json(lock_path)
        except (OSError, ValueError) as error:
            checks.append(_check("lock_document_present_and_frozen", False, {"error": str(error)[:200]}))
    if lock is None and not any(c["check"] == "lock_document_present_and_frozen" for c in checks):
        checks.append(_check("lock_document_present_and_frozen", False, {"error": "dependency lock document missing"}))

    resolved: dict[str, Any] | None = None
    if lock is not None:
        frozen_ok = (
            lock.get("artifact_kind") == "DEPENDENCY_LOCK"
            and lock.get("resolution_status") == "RESOLVED_FROZEN"
            and lock.get("blocker") is None
        )
        checks.append(
            _check(
                "lock_document_present_and_frozen",
                frozen_ok,
                {"resolution_status": lock.get("resolution_status")},
            )
        )
        resolved = lock.get("resolved") if isinstance(lock.get("resolved"), dict) else None

        # 1. schema conformance (jsonschema capability; BLOCKED when absent)
        try:
            import jsonschema  # type: ignore
        except ImportError:
            checks.append(
                _blocked_check(
                    "lock_schema_conformance",
                    {"reason": "SCHEMA_CAPABILITY_UNAVAILABLE"},
                )
            )
        else:
            schema_document = load_json(repo_root / "spec" / "schemas" / "dependency-lock.schema.json")
            try:
                jsonschema.Draft202012Validator.check_schema(schema_document)
                validator = jsonschema.Draft202012Validator(schema_document)
                errors = sorted(validator.iter_errors(lock), key=lambda e: list(e.absolute_path))
                checks.append(
                    _check(
                        "lock_schema_conformance",
                        not errors,
                        {"first_error": f"{'/'.join(str(p) for p in errors[0].absolute_path) or '$'}: {errors[0].message[:300]}" if errors else {}},
                    )
                )
            except jsonschema.exceptions.SchemaError as error:  # type: ignore[attr-defined]
                checks.append(_check("lock_schema_conformance", False, {"error": str(error)[:300]}))

        # 2. content self-hash
        content_ok = lock.get("content_sha256") == logical_sha256(lock)
        checks.append(_check("lock_content_hash_self_consistency", content_ok, {}))

        # 3. SOT binding
        sot_sha256 = hashlib.sha256((repo_root / "spec" / "SOURCE_OF_TRUTH.md").read_bytes()).hexdigest().upper()
        graph = load_json(repo_root / "spec" / "requirements.graph.json")
        sot_ok = (
            lock.get("sot_sha256") == sot_sha256
            and lock.get("sot_sha256") == graph.get("sot_sha256")
            and lock.get("sot_revision") == graph.get("sot_revision") == 35
        )
        checks.append(_check("lock_sot_binding", sot_ok, {"sot_sha256": lock.get("sot_sha256")}))

        # 4. invocation binding
        invocation_hash = (resolved or {}).get("resolved_at_invocation_hash")
        invocation_details: dict[str, Any] = {"resolved_at_invocation_hash": invocation_hash}
        if invocation_evidence is not None:
            evidence_payload = load_json(invocation_evidence)
            invocation_details["invocation_evidence_hash"] = evidence_payload.get("hashes", {}).get(
                "bootstrap_invocation_logical_sha256"
            )
            invocation_ok = (
                isinstance(invocation_hash, str)
                and _SHA256_RE.fullmatch(invocation_hash) is not None
                and invocation_hash == invocation_details["invocation_evidence_hash"]
            )
        else:
            invocation_ok = isinstance(invocation_hash, str) and _SHA256_RE.fullmatch(invocation_hash) is not None
        checks.append(_check("lock_invocation_binding", invocation_ok, invocation_details))

        # 5. resolver identity
        resolver_identity = lock.get("resolver_identity")
        resolver_ok = (
            isinstance(resolver_identity, dict)
            and bool(resolver_identity.get("tool"))
            and bool(resolver_identity.get("version"))
        )
        checks.append(_check("lock_resolver_identity_recorded", resolver_ok, {"tool": (resolver_identity or {}).get("tool")}))

        # 6. approved origin
        approved_origins = lock.get("approved_origins") or []
        approved_indexes = {entry.get("origin") for entry in approved_origins if isinstance(entry, dict)}
        origin_ok = (
            bool(approved_origins)
            and all(isinstance(entry.get("authorization_ref"), str) and entry.get("authorization_ref") for entry in approved_origins)
            and APPROVED_GREENFIELD_PACKAGE_INDEX in approved_indexes
        )
        checks.append(_check("lock_approved_origin_recorded", origin_ok, {"approved_origins": sorted(o for o in approved_indexes if o)}))

        # 7. direct dependency declaration equality (fail closed on classification)
        declared: dict[str, list[dict[str, str]]] | None = None
        declaration_error: str | None = None
        try:
            declared = declared_direct_constraints((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
        except DependencyDeclarationClassificationError as error:
            declaration_error = str(error)
        if declared is not None:
            lock_direct = lock.get("direct_constraints") or {}
            declared_pairs = {
                role: sorted((entry["distribution"], entry["constraint"]) for entry in entries)
                for role, entries in declared.items()
            }
            lock_pairs = {
                role: sorted((entry["distribution"], entry["constraint"]) for entry in entries)
                for role, entries in lock_direct.items()
            }
            declaration_equal = declared_pairs == lock_pairs
            checks.append(_check("direct_dependency_declaration_equality", declaration_equal, {"declared": declared_pairs}))
        else:
            checks.append(_check("direct_dependency_declaration_equality", False, {"error": declaration_error}))

        # 8. optional profile equality
        try:
            declared_profiles = declared_optional_profiles((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
            lock_profiles = lock.get("optional_profiles") or {}
            profile_equal = lock_profiles.get("dev") == declared_profiles.get("dev")
            checks.append(_check("optional_profile_declaration_equality", profile_equal, {"declared": declared_profiles}))
        except DependencyDeclarationClassificationError as error:
            checks.append(_check("optional_profile_declaration_equality", False, {"error": str(error)}))

        # 9. runtime profile truthfully empty at B0
        runtime_entries = (lock.get("direct_constraints") or {}).get("runtime", [])
        runtime_empty = runtime_entries == []
        membership_runtime_hits: list[str] = []
        for entry in (resolved or {}).get("distributions", []):
            if "runtime" in (entry.get("profile_membership") or []):
                membership_runtime_hits.append(entry.get("distribution", ""))
        checks.append(
            _check(
                "runtime_profile_truthfully_empty",
                runtime_empty and not membership_runtime_hits,
                {"runtime_entries": runtime_entries, "runtime_resolved": membership_runtime_hits},
            )
        )

        # 10. artifact inventory internal consistency
        distributions = (resolved or {}).get("distributions", [])
        transitive_artifacts = lock.get("transitive_artifacts") or []
        artifact_by_filename: dict[str, dict[str, Any]] = {}
        inventory_errors: list[str] = []
        resolved_by_filename: dict[str, dict[str, Any]] = {}
        for entry in distributions:
            filename = entry.get("artifact_filename", "")
            if not filename:
                inventory_errors.append("resolved distribution entry without artifact_filename")
                continue
            if filename in resolved_by_filename:
                inventory_errors.append(f"duplicate resolved artifact_filename: {filename}")
            resolved_by_filename[filename] = entry
            if not _SHA256_RE.fullmatch(str(entry.get("sha256", ""))):
                inventory_errors.append(f"malformed sha256 for {filename}")
            parsed = _wheel_artifact_record(filename)
            if parsed is None:
                inventory_errors.append(f"non-wheel or unparseable artifact_filename: {filename}")
                continue
            if parsed["distribution"] != _pep503_normalize(str(entry.get("distribution", ""))):
                inventory_errors.append(f"filename distribution mismatch for {filename}")
            if parsed["version"] != entry.get("version"):
                inventory_errors.append(f"filename version mismatch for {filename}")
            origin = str(entry.get("origin", ""))
            if not origin.startswith(APPROVED_GREENFIELD_ARTIFACT_HOST + "/"):
                inventory_errors.append(f"artifact origin outside the approved host: {filename} -> {origin[:80]}")
        for artifact in transitive_artifacts:
            filename = artifact.get("filename", "")
            if filename in artifact_by_filename:
                inventory_errors.append(f"duplicate transitive artifact filename: {filename}")
            artifact_by_filename[filename] = artifact
            if not _SHA256_RE.fullmatch(str(artifact.get("sha256", ""))):
                inventory_errors.append(f"malformed sha256 for {filename}")
        resolved_files = set(resolved_by_filename)
        transitive_files = set(artifact_by_filename)
        if resolved_files != transitive_files:
            inventory_errors.append("resolved.distributions and transitive_artifacts filename sets differ")
        for filename in sorted(resolved_files & transitive_files):
            if resolved_by_filename[filename].get("sha256") != artifact_by_filename[filename].get("sha256"):
                inventory_errors.append(f"sha256 disagreement between resolved and transitive records: {filename}")
            if _pep503_normalize(str(resolved_by_filename[filename].get("distribution", ""))) != _pep503_normalize(
                str(artifact_by_filename[filename].get("distribution", ""))
            ):
                inventory_errors.append(f"distribution disagreement for {filename}")
            if str(resolved_by_filename[filename].get("version", "")) != str(artifact_by_filename[filename].get("version", "")):
                inventory_errors.append(f"version disagreement for {filename}")
        checks.append(_check("artifact_inventory_internal_consistency", not inventory_errors, {"errors": inventory_errors[:10]}))

        # 11. no floating versions
        versions_by_distribution: dict[str, set[str]] = {}
        for entry in distributions:
            versions_by_distribution.setdefault(_pep503_normalize(str(entry.get("distribution", ""))), set()).add(
                str(entry.get("version", ""))
            )
        for artifact in transitive_artifacts:
            versions_by_distribution.setdefault(_pep503_normalize(str(artifact.get("distribution", ""))), set()).add(
                str(artifact.get("version", ""))
            )
        floating = {name: sorted(values) for name, values in sorted(versions_by_distribution.items()) if len(values) != 1}
        checks.append(_check("no_floating_versions", not floating, {"floating": floating}))

        # 12. declared constraints satisfied by the resolved versions
        unsatisfied: list[str] = []
        undecidable: list[str] = []
        for role, entries in (lock.get("direct_constraints") or {}).items():
            for entry in entries:
                name = _pep503_normalize(entry["distribution"])
                resolved_versions = versions_by_distribution.get(name, set())
                if len(resolved_versions) != 1:
                    unsatisfied.append(f"{role}:{name}: no single resolved version")
                    continue
                version = next(iter(resolved_versions))
                satisfied = _release_constraint_satisfied(entry["constraint"], version)
                if satisfied is None:
                    undecidable.append(f"{role}:{name}: constraint {entry['constraint']} vs {version}")
                elif not satisfied:
                    unsatisfied.append(f"{role}:{name}: {entry['constraint']} not satisfied by {version}")
        checks.append(
            _check(
                "direct_constraints_satisfied",
                not unsatisfied and not undecidable,
                {"unsatisfied": unsatisfied, "undecidable_constraint_forms": undecidable},
            )
        )

        # 13. wheelhouse-dependent checks
        wheelhouse_status = "BLOCKED"
        wheelhouse_details: dict[str, Any] = {"wheelhouse_provided": wheelhouse is not None}
        if wheelhouse is None:
            env_value = os.environ.get(DEPENDENCY_LOCK_WHEELHOUSE_ENV_VAR)
            if env_value:
                wheelhouse = Path(env_value)
        if wheelhouse is not None:
            undeclared: list[str] = []
            missing: list[str] = []
            hash_mismatches: list[str] = []
            for filename, artifact in sorted(artifact_by_filename.items()):
                wheel_path = wheelhouse / filename
                if not wheel_path.is_file():
                    missing.append(filename)
                    continue
                digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest().upper()
                if digest != str(artifact.get("sha256", "")).upper():
                    hash_mismatches.append(filename)
            wheelhouse_files = {path.name for path in wheelhouse.iterdir() if path.is_file()}
            for filename in sorted(wheelhouse_files - set(artifact_by_filename)):
                undeclared.append(filename)
            wheelhouse_details.update(
                {
                    "wheelhouse_artifact_count": len(wheelhouse_files),
                    "undeclared_artifact_count": len(undeclared),
                    "missing_artifact_count": len(missing),
                    "hash_mismatch_count": len(hash_mismatches),
                    "undeclared": undeclared[:10],
                    "missing": missing[:10],
                    "hash_mismatches": hash_mismatches[:10],
                }
            )
            wheelhouse_equality_ok = not undeclared and not missing and not hash_mismatches
            checks.append(_check("wheelhouse_lock_equality", wheelhouse_equality_ok, dict(wheelhouse_details)))
            closure = compute_lock_closure(
                wheelhouse,
                lock.get("direct_constraints") or {},
                lock.get("optional_profiles") or {},
                {
                    filename: {
                        "distribution": _pep503_normalize(str(artifact.get("distribution", ""))),
                        "version": str(artifact.get("version", "")),
                    }
                    for filename, artifact in artifact_by_filename.items()
                },
            )
            if closure["status"] == "BLOCKED":
                checks.append(
                    _blocked_check(
                        "resolved_closure_matches_wheel_metadata",
                        {"reason": closure["reason"]},
                    )
                )
            else:
                membership_mismatches: list[str] = []
                for entry in distributions:
                    name = _pep503_normalize(str(entry.get("distribution", "")))
                    recomputed = closure["profile_membership"].get(name, [])
                    recorded = sorted(entry.get("profile_membership") or [])
                    if recomputed != recorded:
                        membership_mismatches.append(f"{name}: recomputed={recomputed} recorded={recorded}")
                closure_ok = closure["status"] == "PASS" and not membership_mismatches
                checks.append(
                    _check(
                        "resolved_closure_matches_wheel_metadata",
                        closure_ok,
                        {
                            "closure_errors": closure["errors"][:10],
                            "membership_mismatches": membership_mismatches[:10],
                            "edge_count": len(closure["edges"]),
                        },
                    )
                )
        else:
            checks.append(
                _blocked_check(
                    "wheelhouse_lock_equality",
                    {"reason": "WHEELHOUSE_UNAVAILABLE", **wheelhouse_details},
                )
            )
            checks.append(
                _blocked_check(
                    "resolved_closure_matches_wheel_metadata",
                    {"reason": "WHEELHOUSE_UNAVAILABLE", **wheelhouse_details},
                )
            )

    failed = [check for check in checks if check["status"] == "FAIL"]
    blocked = [check for check in checks if check["status"] == "BLOCKED"]
    status = "FAIL" if failed else ("BLOCKED" if blocked else "PASS")
    summary: dict[str, Any] = {}
    if lock is not None:
        summary = {
            "dependency_lock_file_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest().upper(),
            "dependency_lock_logical_sha256": lock.get("content_sha256"),
            "distribution_count": len({str(entry.get("distribution", "")) for entry in (resolved or {}).get("distributions", [])}),
            "artifact_count": len(lock.get("transitive_artifacts") or []),
            "approved_origins": [entry.get("origin") for entry in (lock.get("approved_origins") or [])],
            "resolver_identity": lock.get("resolver_identity"),
        }
    return {
        "report": "DEPENDENCY_LOCK",
        "status": status,
        "checks": checks,
        "failed_check_count": len(failed),
        "blocked_check_count": len(blocked),
        "summary": summary,
    }


# ----------------------------------------------------------------------
# requirement dispatch (REQ-AUTO-004 / REQ-AUTO-040)
# ----------------------------------------------------------------------

def dispatch_requirement(
    requirement_id: str,
    context: dict[str, str],
    repo_root: Path,
    graph: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if graph is None or manifest is None:
        _sot, graph, manifest = load_repo_artifacts(repo_root)
    record = manifest["requirements"].get(requirement_id)
    if record is None:
        known = next((r for r in graph["requirements"] if r["id"] == requirement_id), None)
        if known is None:
            return {
                "requirement_id": requirement_id,
                "status": "FAIL",
                "error_code": "VERIFIER_UNKNOWN",
                "message": "Unknown requirement ID — fail closed (REQ-AUTO-004).",
            }
        record = {"lifecycle": known["lifecycle"], "applicability": known["applicability"], "verifier_ids": []}
    applicable, rule = evaluate_requirement(
        {"applicability": record["applicability"]},
        context,
    )
    if not applicable:
        return {
            "requirement_id": requirement_id,
            "status": "NOT_APPLICABLE",
            "applicability_rule": rule,
            "expression": record["applicability"]["expression"],
            "message": "Deterministic applicability rule excludes this requirement in the current context.",
        }
    verifier_ids = record.get("verifier_ids", [])
    if not verifier_ids:
        return {
            "requirement_id": requirement_id,
            "status": "NOT_IMPLEMENTED",
            "message": "No verifier is mapped for this requirement yet.",
        }
    verifier_states = []
    for verifier_id in verifier_ids:
        verifier = manifest["verifiers"].get(verifier_id)
        if verifier is None:
            verifier_states.append({"verifier_id": verifier_id, "status": "FAIL", "error_code": "VERIFIER_UNKNOWN"})
            continue
        if verifier.get("state") != "EXECUTABLE" or not verifier.get("command"):
            verifier_states.append(
                {
                    "verifier_id": verifier_id,
                    "status": "PLANNED",
                    "message": "PLANNED verifier cannot produce PASS (REQ-AUTO-004).",
                }
            )
            continue
        executed = _execute_verifier_command(verifier, repo_root)
        verifier_states.append(executed)
    worst = "PASS"
    for state in verifier_states:
        candidate_status = state["status"]
        if candidate_status == "PASS":
            continue
        if candidate_status in ("NOT_APPLICABLE",):
            continue
        worst = candidate_status
        break
    return {
        "requirement_id": requirement_id,
        "status": worst,
        "applicability_rule": rule,
        "verifier_results": verifier_states,
    }


def _execute_verifier_command(verifier: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    command = list(verifier["command"])
    if command and command[0] == "python":
        command[0] = sys.executable or "python"
    completed = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=600,
    )
    status = "PASS" if completed.returncode == 0 else "FAIL"
    return {
        "verifier_id": verifier["verifier_id"],
        "status": status,
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }