# -*- coding: utf-8 -*-
"""Frozen-SOT parsing and canonical requirement-graph construction.

Implements the corrected canonical semantics established by
WP-SOT-REV35-SEMANTIC-AUDIT-001 (DECISION_A — the Rev.35 SOT is valid; the
former brownfield generator's "union ancestor chains over every milestone
membership" rule was a generator defect and is explicitly NOT implemented):

1. Physical Markdown phase position is NOT an execution prerequisite.
2. Requirement numbering is NOT an execution prerequisite.
3. Canonical milestone selectors own activation.
4. A requirement selected by more than one implementation milestone has the
   EARLIEST selecting milestone (in the explicit ``after:``-derived DAG
   order) as its execution prerequisite basis.
5. Later re-selection MUST NOT import the later milestone's ancestors.
6. Explicit prerequisite IDs, when the SOT declares them, remain
   authoritative (Rev.35 declares none; the scan is re-run every generation).
7. Structured applicability and lifecycle mappings remain authoritative.
8. Full-graph cycle detection (Tarjan SCC) is mandatory.

The module is deterministic and offline: the only input is the frozen SOT
text plus a context binding for applicability evaluation.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

REQ_RE = re.compile(r"^`(REQ-[A-Z0-9]+-\d{3})`\s*[—-]\s*(.*)$")
MALFORMED_RECORD_RE = re.compile(r"^`(REQ-[A-Z0-9]+-\d{3})`(?!\s*[—-])")
SECTION_RE = re.compile(r"^#{1,3}\s+(.*)$")

APPLICABILITY_DEFAULT = "ALWAYS"
GATE_START_READY = "START_READY"
GATE_GREENFIELD = "B0"
GATE_BROWNFIELD = "BR0"

# Explicit per-ID prerequisite extraction (narrow declaration forms only;
# prose references to other requirement IDs are NOT prerequisites). The ID
# must immediately follow the declaration word (optionally via "is"/"are"
# or a colon) so governance references like "governed by `REQ-x`" or
# "prerequisite IDs ... MUST satisfy `REQ-y`" never match.
_EXPLICIT_PREREQ_PATTERNS = (
    re.compile(r"prerequisites?[:\s]+(?:is\s+|are\s+)?`?(REQ-[A-Z0-9]+-\d{3})"),
    re.compile(r"(?:depends on|requires|after)\s+`?(REQ-[A-Z0-9]+-\d{3})"),
)


class SotParseError(ValueError):
    """Raised when the SOT text violates the contract shape (fail closed)."""


class CycleError(ValueError):
    """Raised when a semantic graph contains a cycle (mandatory rejection)."""

    def __init__(self, cycle: list[str], graph_name: str) -> None:
        self.cycle = cycle
        self.graph_name = graph_name
        super().__init__(f"{graph_name} contains a cycle: {' -> '.join(cycle)}")


# ----------------------------------------------------------------------
# fenced-block discovery and minimal YAML-subset parsing (document shape)
# ----------------------------------------------------------------------

def find_fenced_blocks(lines: list[str]) -> list[tuple[int, list[str]]]:
    blocks: list[tuple[int, list[str]]] = []
    in_fence = False
    buf: list[str] | None = None
    start = 0
    for index, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            if in_fence:
                blocks.append((start, buf or []))
                in_fence = False
                buf = None
            else:
                in_fence = True
                start = index
                buf = []
        elif in_fence:
            buf.append(raw)  # type: ignore[union-attr]
    if in_fence:  # pragma: no cover - defensive
        raise SotParseError("unterminated fenced block in SOT")
    return blocks


def block_with_key(blocks: list[tuple[int, list[str]]], topkey: str) -> list[str]:
    pattern = re.compile(r"^" + re.escape(topkey) + r"\s*$")
    for _start, body in blocks:
        for raw in body:
            if pattern.match(raw.strip()):
                return body
    raise SotParseError(f"fenced block with top-level key {topkey!r} not found")


def parse_yamlish(body: list[str]) -> dict[str, Any]:
    """Parse the SOT's YAML-subset blocks (maps, inline lists, block lists)."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    pending: tuple[int, dict[str, Any], str] | None = None
    for raw in body:
        content = raw.rstrip().strip()
        if not content or content.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if content.startswith("- "):
            if pending is None:
                raise SotParseError(f"list item without pending key: {content!r}")
            pind, pcont, pkey = pending
            if indent <= pind:
                raise SotParseError(f"bad list indent for {pkey!r}: {content!r}")
            if pcont[pkey] is None:
                pcont[pkey] = []
            if not isinstance(pcont[pkey], list):
                raise SotParseError(f"mixed map/list for key {pkey!r}")
            pcont[pkey].append(content[2:].strip())
            continue
        if pending is not None and indent > pending[0]:
            pind, pcont, pkey = pending
            pcont[pkey] = {}
            stack.append((pind, pcont[pkey]))
            pending = None
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        match = re.match(r"^([A-Za-z0-9_.\-]+):\s*(.*)$", content)
        if not match:
            raise SotParseError(f"unparsed line in YAML-subset block: {content!r}")
        key, value = match.group(1), match.group(2).strip()
        if value == "":
            parent[key] = None
            pending = (indent, parent, key)
        elif value.startswith("[") and value.endswith("]"):
            parent[key] = [item.strip() for item in value[1:-1].split(",") if item.strip()]
            pending = None
        else:
            parent[key] = value
            pending = None
    return root


# ----------------------------------------------------------------------
# selector expansion (REQ-PORT-024 forms only)
# ----------------------------------------------------------------------

def expand_selector_item(item: str, defs: dict[str, str]) -> list[str]:
    exact = re.match(r"^(REQ-[A-Z0-9]+-\d{3})$", item)
    if exact:
        if item not in defs:
            raise SotParseError(f"unknown exact requirement ID in selector: {item}")
        return [item]
    ranged = re.match(r"^(REQ-[A-Z0-9]+)-(\d{3})\.\.(REQ-[A-Z0-9]+)-(\d{3})$", item)
    if ranged:
        family_a, num_a = ranged.group(1), int(ranged.group(2))
        family_b, num_b = ranged.group(3), int(ranged.group(4))
        if family_a != family_b:
            raise SotParseError(f"cross-family range rejected (REQ-PORT-024): {item}")
        out = []
        for number in range(num_a, num_b + 1):
            rid = f"{family_a}-{number:03d}"
            if rid in defs:
                out.append(rid)
        return out
    wildcard = re.match(r"^(REQ-[A-Z0-9]+)-\*$", item)
    if wildcard:
        prefix = wildcard.group(1) + "-"
        return [rid for rid in defs if rid.startswith(prefix)]
    raise SotParseError(f"unsupported selector form (REQ-PORT-024): {item}")


def expand_selector_list(items: list[str], defs: dict[str, str]) -> list[str]:
    out: list[str] = []
    for item in items:
        out.extend(expand_selector_item(item, defs))
    return out


# ----------------------------------------------------------------------
# Tarjan SCC (independent cycle detection, mandatory per audit Part I.4)
# ----------------------------------------------------------------------

def strongly_connected_components(graph: dict[str, list[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    result: list[list[str]] = []
    counter = [0]

    def strong(vertex: str) -> None:
        index[vertex] = low[vertex] = counter[0]
        counter[0] += 1
        stack.append(vertex)
        on_stack[vertex] = True
        for neighbour in graph.get(vertex, ()):
            if neighbour not in index:
                strong(neighbour)
                low[vertex] = min(low[vertex], low[neighbour])
            elif on_stack.get(neighbour):
                low[vertex] = min(low[vertex], index[neighbour])
        if low[vertex] == index[vertex]:
            component: list[str] = []
            while True:
                popped = stack.pop()
                on_stack[popped] = False
                component.append(popped)
                if popped == vertex:
                    break
            result.append(sorted(component))

    for vertex in graph:
        if vertex not in index:
            strong(vertex)
    return result


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Iterative DFS cycle finder returning one concrete cycle or None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    parent: dict[str, str] = {}
    for start in graph:
        if color.get(start, WHITE) != WHITE:
            continue
        color[start] = GRAY
        grey_path = [start]
        path_stack = [(start, iter(graph.get(start, ())))]
        while path_stack:
            node, neighbours = path_stack[-1]
            advanced = False
            for neighbour in neighbours:
                state = color.get(neighbour, WHITE)
                if state == GRAY:
                    cycle = grey_path[grey_path.index(neighbour):] + [neighbour]
                    return cycle
                if state == WHITE:
                    color[neighbour] = GRAY
                    grey_path.append(neighbour)
                    parent[neighbour] = node
                    path_stack.append((neighbour, iter(graph.get(neighbour, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                path_stack.pop()
                grey_path.pop()
    return None


# ----------------------------------------------------------------------
# RequirementGraphBuilder — corrected canonical semantics
# ----------------------------------------------------------------------

class RequirementGraphBuilder:
    """Builds the canonical requirement graph from frozen SOT bytes."""

    def __init__(self, sot_text: str) -> None:
        self.sot_text = sot_text
        self.sot_sha256 = hashlib.sha256(sot_text.encode("utf-8")).hexdigest().upper()
        self.lines = sot_text.splitlines()
        self._parse()

    # ------------------------------------------------------------------
    def _parse(self) -> None:
        defs: dict[str, str] = {}
        def_line: dict[str, int] = {}
        doc_phase: dict[str, str] = {}
        current_section: str | None = None
        doc_order: list[str] = []
        seen: set[str] = set()
        for index, raw in enumerate(self.lines, start=1):
            stripped = raw.strip()
            heading = SECTION_RE.match(stripped)
            if heading:
                current_section = heading.group(1)
            malformed = MALFORMED_RECORD_RE.match(stripped)
            if malformed:
                raise SotParseError(
                    f"malformed requirement record at line {index}: backticked ID without canonical separator "
                    f"(REQ-P00-013 contract shape): {malformed.group(1)}"
                )
            record = REQ_RE.match(stripped)
            if not record:
                continue
            rid = record.group(1)
            if rid in seen:
                raise SotParseError(f"duplicate requirement ID: {rid}")
            seen.add(rid)
            defs[rid] = record.group(2)
            def_line[rid] = index
            doc_order.append(rid)
            doc_phase[rid] = current_section or ""
        if not defs:
            raise SotParseError("no requirement records found")
        self.defs = defs
        self.def_line = def_line
        self.doc_order = doc_order
        self.doc_phase = doc_phase

        blocks = find_fenced_blocks(self.lines)
        ms_root = parse_yamlish(block_with_key(blocks, "milestones:"))
        lc_root = parse_yamlish(block_with_key(blocks, "lifecycle_mapping:"))
        ap_root = parse_yamlish(block_with_key(blocks, "applicability_mapping:"))
        self.milestones_raw: dict[str, dict[str, Any]] = ms_root["milestones"]
        self.release_closure_raw: dict[str, list[str]] = ms_root["release_closure"]
        self.start_readiness_raw: dict[str, str] = ms_root["start_readiness"]
        self.lifecycle_raw: dict[str, dict[str, Any]] = lc_root["lifecycle_mapping"]
        self.applicability_raw: dict[str, Any] = ap_root["applicability_mapping"]

    # ------------------------------------------------------------------
    def build(self) -> dict[str, Any]:
        req_ids = self.doc_order

        lifecycle_class = self._classify_lifecycle()
        applicability = self._assign_applicability()
        members, req_memberships = self._milestone_membership(lifecycle_class)
        topo, ancestors = self._milestone_dag()

        requirements = []
        for rid in req_ids:
            memberships = req_memberships.get(rid, [])
            exec_milestone = None
            prereq_milestones: list[str] = []
            prereq_ids: set[str] = set()
            if memberships:
                exec_milestone = min(memberships, key=lambda ms: topo.index(ms))
                prereq_milestones = sorted(ancestors[exec_milestone])
                for ancestor in prereq_milestones:
                    prereq_ids.update(members[ancestor])
            explicit = self._scan_explicit_prerequisites(rid)
            prereq_ids.update(explicit)
            requirements.append(
                {
                    "id": rid,
                    "document_line": self.def_line[rid],
                    "document_phase": self.doc_phase[rid],
                    "text": self.defs[rid],
                    "lifecycle": lifecycle_class[rid],
                    "applicability": applicability[rid],
                    "milestones": sorted(memberships),
                    "execution_milestone": exec_milestone,
                    "prerequisite_milestones": prereq_milestones,
                    "explicit_prerequisite_ids": sorted(explicit),
                    "prerequisite_ids": sorted(prereq_ids),
                }
            )

        graph: dict[str, Any] = {
            "requirements": requirements,
            "milestones": self._milestone_records(members, topo, ancestors),
            "milestone_topological_order": topo,
            "release_closure_milestones": {
                version: list(closure) for version, closure in self.release_closure_raw.items()
            },
            "start_readiness": dict(self.start_readiness_raw),
            "applicability_default": APPLICABILITY_DEFAULT,
            "applicability_overrides": self._override_records(),
            "lifecycle_classes": list(self.lifecycle_raw),
        }

        edges = {r["id"]: list(r["prerequisite_ids"]) for r in requirements}
        cycle = find_cycle(edges)
        if cycle is not None:
            raise CycleError(cycle, "canonical requirement graph")
        return graph

    # ------------------------------------------------------------------
    def _classify_lifecycle(self) -> dict[str, str]:
        lifecycle_class: dict[str, str] = {}
        for rid in self.doc_order:
            assigned = None
            for class_name in self.lifecycle_raw:
                include = self.lifecycle_raw[class_name].get("include", [])
                if rid in set(expand_selector_list(include, self.defs)):
                    assigned = class_name
                    break
            if assigned is None:
                raise SotParseError(f"unclassified requirement (lifecycle): {rid}")
            lifecycle_class[rid] = assigned
        return lifecycle_class

    def _assign_applicability(self) -> dict[str, dict[str, Any]]:
        overrides = self.applicability_raw.get("overrides", {})
        assignment: dict[str, dict[str, Any]] = {}
        matched: dict[str, list[str]] = {}
        for override_name, spec in overrides.items():
            include = spec.get("selector", {}).get("include", [])
            for rid in expand_selector_list(include, self.defs):
                matched.setdefault(rid, []).append(override_name)
        for rid in self.doc_order:
            names = matched.get(rid, [])
            if len(names) > 1:
                raise SotParseError(f"requirement matches multiple applicability overrides: {rid} {names}")
            if names:
                override = overrides[names[0]]
                assignment[rid] = {
                    "override": names[0],
                    "expression": dict(override.get("expression", {})),
                }
            else:
                assignment[rid] = {"override": None, "expression": {"default": APPLICABILITY_DEFAULT}}
        return assignment

    def _milestone_membership(
        self, lifecycle_class: dict[str, str]
    ) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
        members: dict[str, set[str]] = {}
        for name, spec in self.milestones_raw.items():
            selector = spec.get("selector", {})
            include = set(expand_selector_list(selector.get("include", []), self.defs))
            exclude = set(expand_selector_list(selector.get("exclude", []), self.defs))
            allowed = set(selector.get("lifecycle", []))
            if not allowed:
                raise SotParseError(f"milestone {name} declares no lifecycle filter")
            members[name] = {rid for rid in (include - exclude) if lifecycle_class[rid] in allowed}
        req_memberships: dict[str, list[str]] = {}
        for name in self.milestones_raw:
            for rid in members[name]:
                req_memberships.setdefault(rid, []).append(name)
        return members, req_memberships

    def _milestone_dag(self) -> tuple[list[str], dict[str, set[str]]]:
        parents: dict[str, list[str]] = {}
        for name, spec in self.milestones_raw.items():
            after = [a for a in spec.get("after", []) if a != GATE_START_READY]
            unknown = [a for a in after if a not in self.milestones_raw]
            if unknown:
                raise SotParseError(f"milestone {name} references unknown after targets: {unknown}")
            parents[name] = after
        cycle = find_cycle(parents)
        if cycle is not None:
            raise CycleError(cycle, "milestone DAG")
        topo: list[str] = []
        seen: set[str] = set()

        def visit(node: str) -> None:
            if node in seen:
                return
            seen.add(node)
            for parent in parents.get(node, ()):
                visit(parent)
            topo.append(node)

        for name in self.milestones_raw:
            visit(name)
        ancestors: dict[str, set[str]] = {}

        def collect(node: str) -> set[str]:
            if node in ancestors:
                return ancestors[node]
            out: set[str] = set()
            for parent in parents.get(node, ()):
                out.add(parent)
                out |= collect(parent)
            ancestors[node] = out
            return out

        for name in self.milestones_raw:
            collect(name)
        return topo, ancestors

    def _milestone_records(
        self,
        members: dict[str, set[str]],
        topo: list[str],
        ancestors: dict[str, set[str]],
    ) -> list[dict[str, Any]]:
        records = []
        for name, spec in self.milestones_raw.items():
            selector = spec.get("selector", {})
            records.append(
                {
                    "name": name,
                    "after": [a for a in spec.get("after", []) if a != GATE_START_READY],
                    "gates_after": [a for a in spec.get("after", []) if a == GATE_START_READY],
                    "include": list(selector.get("include", [])),
                    "exclude": list(selector.get("exclude", [])),
                    "lifecycle_filter": list(selector.get("lifecycle", [])),
                    "members": sorted(members[name]),
                    "member_count": len(members[name]),
                    "ancestor_milestones": [m for m in topo if m in ancestors[name]],
                    "topological_index": topo.index(name),
                }
            )
        return records

    def _override_records(self) -> list[dict[str, Any]]:
        records = []
        for name, spec in self.applicability_raw.get("overrides", {}).items():
            records.append(
                {
                    "name": name,
                    "selector_include": list(spec.get("selector", {}).get("include", [])),
                    "expression": dict(spec.get("expression", {})),
                }
            )
        return records

    def _scan_explicit_prerequisites(self, rid: str) -> set[str]:
        body = self.defs[rid]
        found: set[str] = set()
        for pattern in _EXPLICIT_PREREQ_PATTERNS:
            for match in pattern.finditer(body):
                found.add(match.group(1))
        found.discard(rid)
        return found


# ----------------------------------------------------------------------
# applicability evaluation (closed vocabulary, mechanical — REQ-PORT-023/030)
# ----------------------------------------------------------------------

CONTEXT_FIELDS = ("start_mode", "operation_scope", "authoring_mode", "release_profile", "release_context")


def evaluate_applicability(expression: dict[str, Any], context: dict[str, str]) -> bool:
    """Evaluate a structured applicability expression against a context.

    Single-key expressions; a string value requires equality, a list value
    requires membership (REQ-PORT-030: PUBLICATION satisfies predicates that
    list it; LOCAL_QUALIFICATION never activates remote/publication-only
    requirements).
    """
    unknown_predicates = [key for key in expression if key not in CONTEXT_FIELDS]
    if unknown_predicates:
        raise SotParseError(f"unknown applicability predicates: {unknown_predicates}")
    for key, expected in expression.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def evaluate_requirement(requirement: dict[str, Any], context: dict[str, str]) -> tuple[bool, str]:
    applicability = requirement["applicability"]
    if applicability.get("override") is None:
        return True, APPLICABILITY_DEFAULT
    return (
        evaluate_applicability(applicability["expression"], context),
        applicability["override"],
    )


# ----------------------------------------------------------------------
# closures (graph-derived; no manual lists — REQ-B00-002/003)
# ----------------------------------------------------------------------

def readiness_closure(
    graph: dict[str, Any],
    gate: str,
    context: dict[str, str],
) -> dict[str, Any]:
    """Derive a readiness-gate closure from the canonical requirement graph.

    gate ``B0``: lifecycle BOOTSTRAP AND applicability true for
    start_mode=GREENFIELD. gate ``BR0``: same with start_mode=BROWNFIELD.
    Plus all transitive prerequisites (explicit IDs only in Rev.35; milestone
    members are excluded because no BOOTSTRAP requirement is milestone
    selected in Rev.35).
    """
    start_mode = "GREENFIELD" if gate == GATE_GREENFIELD else "BROWNFIELD"
    ctx = dict(context)
    ctx["start_mode"] = start_mode
    selected: list[str] = []
    excluded: list[dict[str, str]] = []
    for requirement in graph["requirements"]:
        applicable, rule = evaluate_requirement(requirement, ctx)
        if requirement["lifecycle"] == "BOOTSTRAP":
            if applicable:
                selected.append(requirement["id"])
            else:
                excluded.append({"id": requirement["id"], "rule": rule})
    selected_set = set(selected)
    closure = set(selected_set)
    frontier = list(selected_set)
    while frontier:
        rid = frontier.pop()
        requirement = next(r for r in graph["requirements"] if r["id"] == rid)
        for dep in requirement["prerequisite_ids"]:
            if dep not in closure:
                closure.add(dep)
                frontier.append(dep)
    added = sorted(closure - selected_set)
    return {
        "gate": gate,
        "start_mode": start_mode,
        "context": ctx,
        "derivation": "lifecycle=BOOTSTRAP AND applicability(ctx) = true, plus transitive prerequisites",
        "directly_selected_count": len(selected_set),
        "requirement_ids": sorted(closure),
        "requirement_count": len(closure),
        "transitive_prerequisites_added": added,
        "excluded_by_applicability": sorted(excluded, key=lambda item: item["id"]),
    }


def _release_predecessors(graph: dict[str, Any], release_version: str) -> list[str]:
    """Earlier releases in the canonical lineage (declared by closure lists)."""
    declared = graph["release_closure_milestones"][release_version]
    predecessors: list[str] = []
    for item in declared:
        if item in graph["release_closure_milestones"]:
            for previous in _release_predecessors(graph, item):
                if previous not in predecessors:
                    predecessors.append(previous)
            if item not in predecessors:
                predecessors.append(item)
    return predecessors


def release_closure(
    graph: dict[str, Any],
    release_version: str,
    context: dict[str, str],
) -> dict[str, Any]:
    """Derive a cumulative release closure from the canonical graph.

    Closure = union of canonical release-closure milestones' members, plus
    active governance (MERGE_GUARD always, RELEASE_GUARD for this release
    profile, FINAL_ACCEPTANCE only at 1.0.0), plus transitive prerequisites.
    Earlier release-family gate definitions (REQ-R0x-*) belong to their own
    release's closure; a later gate reruns the earlier qualified releases'
    smoke/compatibility suites (REQ-AUTO-026), recorded here as
    ``cumulative_regression_releases``.
    """
    milestone_list = graph["release_closure_milestones"][release_version]
    cumulative_milestones = _cumulative_milestone_list(graph, release_version)
    ctx = dict(context)
    ctx["release_profile"] = release_version
    is_final = release_version == "1.0.0"

    selected: set[str] = set()
    milestone_selected: set[str] = set()
    for requirement in graph["requirements"]:
        applicable, _rule = evaluate_requirement(requirement, ctx)
        if requirement["execution_milestone"] in cumulative_milestones and applicable:
            milestone_selected.add(requirement["id"])
            selected.add(requirement["id"])
        lifecycle = requirement["lifecycle"]
        if lifecycle == "MERGE_GUARD" and applicable:
            selected.add(requirement["id"])
        elif lifecycle == "RELEASE_GUARD" and applicable:
            selected.add(requirement["id"])
        elif lifecycle == "FINAL_ACCEPTANCE" and is_final and applicable:
            selected.add(requirement["id"])
        elif lifecycle == "DEPLOYMENT_GUARD":
            # Not activated unless deployment qualification explicitly requested.
            pass

    closure = set(selected)
    frontier = list(selected)
    while frontier:
        rid = frontier.pop()
        requirement = next(r for r in graph["requirements"] if r["id"] == rid)
        for dep in requirement["prerequisite_ids"]:
            if dep not in closure:
                closure.add(dep)
                frontier.append(dep)
    prerequisite_added = sorted(closure - selected)
    return {
        "release": release_version,
        "context": ctx,
        "closure_milestones_declared": list(milestone_list),
        "cumulative_milestones": cumulative_milestones,
        "cumulative_regression_releases": _release_predecessors(graph, release_version),
        "milestone_selected_requirement_ids": sorted(milestone_selected),
        "governance_requirement_ids": sorted(selected - milestone_selected),
        "transitive_prerequisites_added": prerequisite_added,
        "requirement_ids": sorted(closure),
        "requirement_count": len(closure),
        "qualified": False,
        "qualified_release_record": None,
    }


def _cumulative_milestone_list(graph: dict[str, Any], release_version: str) -> list[str]:
    """Expand the declared closure list: releases accumulate predecessors."""
    declared = graph["release_closure_milestones"][release_version]
    accumulated: list[str] = []
    for item in declared:
        if item in graph["release_closure_milestones"]:
            previous = _cumulative_milestone_list(graph, item)
            for ms in previous:
                if ms not in accumulated:
                    accumulated.append(ms)
        elif item in ("START_READY", "activated_governance", "all_applicable_final_governance"):
            continue
        else:
            if item not in graph["milestone_topological_order"]:
                raise SotParseError(f"release closure references unknown token: {item}")
            if item not in accumulated:
                accumulated.append(item)
    return accumulated