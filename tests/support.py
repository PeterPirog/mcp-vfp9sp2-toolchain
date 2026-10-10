# -*- coding: utf-8 -*-
"""Shared test support: independent SOT parser (oracle) + repo paths.

The parser below is deliberately a SECOND, independent implementation of the
frozen-SOT parsing/graph semantics (mirroring the WP-SOT-REV35-SEMANTIC-AUDIT-001
scratch oracle). It exists so tests can validate the production generator and
engine without reusing their code. The FAILED (union-over-memberships) rule is
also reproduced here to power the cycle-regression fixture.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

REQ_RE = re.compile(r"^`(REQ-[A-Z0-9]+-\d{3})`\s*[—-]\s*(.*)$")
SECTION_RE = re.compile(r"^#{1,3}\s+(.*)$")


def independent_sot_text() -> str:
    return (REPO_ROOT / "spec" / "SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")


def independent_parse(sot_text: str) -> dict[str, Any]:
    """Independent requirement/model extraction from the frozen SOT."""
    lines = sot_text.splitlines()
    defs: dict[str, str] = {}
    order: list[str] = []
    phase: dict[str, str] = {}
    current: str | None = None
    for raw in lines:
        stripped = raw.strip()
        heading = SECTION_RE.match(stripped)
        if heading:
            current = heading.group(1)
        record = REQ_RE.match(stripped)
        if record and record.group(1) not in defs:
            defs[record.group(1)] = record.group(2)
            order.append(record.group(1))
            phase[record.group(1)] = current or ""

    blocks: list[list[str]] = []
    inside = False
    body: list[str] = []
    for raw in lines:
        if raw.strip().startswith("```"):
            if inside:
                blocks.append(body)
                body = []
            inside = not inside
        elif inside:
            body.append(raw)
    assert len(blocks) >= 3, "expected the canonical fenced blocks"

    def pick(top: str) -> dict[str, Any]:
        for candidate in blocks:
            for raw in candidate:
                if raw.strip() == top:
                    return yamlish(candidate)
        raise AssertionError("missing block " + top)

    return {
        "defs": defs,
        "order": order,
        "phase": phase,
        "milestones": pick("milestones:")["milestones"],
        "release_closure": pick("milestones:")["release_closure"],
        "lifecycle_mapping": pick("lifecycle_mapping:")["lifecycle_mapping"],
        "applicability_mapping": pick("applicability_mapping:")["applicability_mapping"],
    }


def yamlish(body: list[str]) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    pending: tuple[int, dict[str, Any], str] | None = None
    for raw in body:
        content = raw.rstrip().strip()
        if not content or content.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if content.startswith("- "):
            assert pending is not None
            pind, pcont, pkey = pending
            if pcont[pkey] is None:
                pcont[pkey] = []
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
        m = re.match(r"^([A-Za-z0-9_.\-]+):\s*(.*)$", content)
        assert m, content
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            parent[key] = None
            pending = (indent, parent, key)
        elif val.startswith("[") and val.endswith("]"):
            parent[key] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
            pending = None
        else:
            parent[key] = val
            pending = None
    return root


def expand(item: str, defs: dict[str, str]) -> list[str]:
    m = re.match(r"^(REQ-[A-Z0-9]+-\d{3})$", item)
    if m:
        assert item in defs, item
        return [item]
    m = re.match(r"^(REQ-[A-Z0-9]+)-(\d{3})\.\.(REQ-[A-Z0-9]+)-(\d{3})$", item)
    if m:
        assert m.group(1) == m.group(3), item
        out = []
        for number in range(int(m.group(2)), int(m.group(4)) + 1):
            rid = f"{m.group(1)}-{number:03d}"
            if rid in defs:
                out.append(rid)
        return out
    m = re.match(r"^(REQ-[A-Z0-9]+)-\*$", item)
    if m:
        return [rid for rid in defs if rid.startswith(m.group(1) + "-")]
    raise AssertionError("bad selector: " + item)


def expand_all(items: list[str], defs: dict[str, str]) -> list[str]:
    out: list[str] = []
    for item in items:
        out.extend(expand(item, defs))
    return out


def tarjan_scc(graph: dict[str, list[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    onstack: dict[str, bool] = {}
    stack: list[str] = []
    result: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        onstack[v] = True
        for w in graph.get(v, ()):  # type: ignore[arg-type]
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif onstack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                onstack[w] = False
                comp.append(w)
                if w == v:
                    break
            result.append(sorted(comp))

    for v in graph:
        if v not in index:
            strong(v)
    return result


def topo_ancestors(milestones: dict[str, dict[str, Any]]) -> tuple[list[str], dict[str, list[str]]]:
    parents = {name: [a for a in spec.get("after", []) if a != "START_READY"] for name, spec in milestones.items()}
    topo: list[str] = []
    seen: set[str] = set()

    def visit(node: str) -> None:
        if node in seen:
            return
        seen.add(node)
        for parent in parents.get(node, ()):  # type: ignore[arg-type]
            visit(parent)
        topo.append(node)

    for name in milestones:
        visit(name)
    ancestors: dict[str, set[str]] = {}

    def collect(node: str) -> set[str]:
        if node in ancestors:
            return ancestors[node]
        out: set[str] = set()
        for parent in parents.get(node, ()):  # type: ignore[arg-type]
            out.add(parent)
            out |= collect(parent)
        ancestors[node] = out
        return out

    for name in milestones:
        collect(name)
    return topo, {name: [m for m in topo if m in ancestors[name]] for name in milestones}


def canonical_requirement_edges(
    model: dict[str, Any],
    topo: list[str],
    ancestors: dict[str, list[str]],
) -> dict[str, set[str]]:
    """CANONICAL rule: deps = members of ancestors(exec(R)) + explicit IDs."""
    defs: dict[str, str] = model["defs"]
    lifecycle = independent_lifecycle(model)
    memberships: dict[str, list[str]] = {}
    for ms, spec in model["milestones"].items():
        sel = spec["selector"]
        inc = set(expand_all(sel.get("include", []), defs))
        exc = set(expand_all(sel.get("exclude", []), defs))
        allowed = set(sel.get("lifecycle", []))
        for rid in inc - exc:
            if lifecycle[rid] in allowed:
                memberships.setdefault(rid, []).append(ms)
    edges: dict[str, set[str]] = {}
    for rid in model["order"]:
        mems = memberships.get(rid, [])
        deps: set[str] = set()
        if mems:
            exec_ms = min(mems, key=lambda m: topo.index(m))
            for pm in ancestors[exec_ms]:
                deps |= {q for q in memberships if pm in memberships[q]}
        deps |= scan_explicit_prerequisites(defs[rid], rid)
        edges[rid] = deps
    return edges, memberships


_EXPLICIT_PATTERNS = (
    re.compile(r"prerequisites?[:\s]+(?:is\s+|are\s+)?`?(REQ-[A-Z0-9]+-\d{3})"),
    re.compile(r"(?:depends on|requires|after)\s+`?(REQ-[A-Z0-9]+-\d{3})"),
)


def scan_explicit_prerequisites(body: str, rid: str) -> set[str]:
    found: set[str] = set()
    for pattern in _EXPLICIT_PATTERNS:
        for match in pattern.finditer(body):
            found.add(match.group(1))
    found.discard(rid)
    return found


def failed_requirement_edges(
    model: dict[str, Any],
    topo: list[str],
    ancestors: dict[str, list[str]],
) -> dict[str, set[str]]:
    """FAILED rule (the removed brownfield generator defect): union of the
    ancestor chains over EVERY milestone membership."""
    edges, memberships = canonical_requirement_edges(model, topo, ancestors)
    failed: dict[str, set[str]] = {}
    for rid in model["order"]:
        mems = memberships.get(rid, [])
        deps: set[str] = set()
        for ms in mems:
            for pm in ancestors[ms]:
                for q, qm in memberships.items():
                    if pm in qm:
                        deps.add(q)
        deps |= scan_explicit_prerequisites(model["defs"][rid], rid)
        failed[rid] = deps
    return failed


def independent_lifecycle(model: dict[str, Any]) -> dict[str, str]:
    lifecycle_class: dict[str, str] = {}
    for rid in model["order"]:
        assigned = None
        for class_name in model["lifecycle_mapping"]:
            include = model["lifecycle_mapping"][class_name].get("include", [])
            if rid in set(expand_all(include, model["defs"])):
                assigned = class_name
                break
        assert assigned, rid
        lifecycle_class[rid] = assigned
    return lifecycle_class


def independent_b0_closure(model: dict[str, Any], context: dict[str, str]) -> set[str]:
    """Independent B0 closure: lifecycle BOOTSTRAP AND applicability true,
    plus transitive explicit prerequisites (none in Rev.35)."""
    lifecycle = independent_lifecycle(model)
    overrides = model["applicability_mapping"]["overrides"]
    matched: dict[str, str] = {}
    for name, spec in overrides.items():
        for rid in expand_all(spec["selector"].get("include", []), model["defs"]):
            assert rid not in matched, rid
            matched[rid] = name

    def applicable(rid: str, ctx: dict[str, str]) -> bool:
        if rid not in matched:
            return True
        expression = overrides[matched[rid]]["expression"]
        for key, expected in expression.items():
            actual = ctx.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    selected: set[str] = set()
    for rid in model["order"]:
        if lifecycle[rid] == "BOOTSTRAP" and applicable(rid, context):
            selected.add(rid)
    closure = set(selected)
    for rid in selected:
        closure |= scan_explicit_prerequisites(model["defs"][rid], rid)
    return closure


def load_repo_json(relative: str) -> Any:
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def graph_by_id() -> dict[str, dict[str, Any]]:
    graph = load_repo_json("spec/requirements.graph.json")
    return {r["id"]: r for r in graph["requirements"]}, graph