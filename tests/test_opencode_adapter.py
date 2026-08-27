# -*- coding: utf-8 -*-
"""
tests/test_opencode_adapter.py — OpenCode tools are thin adapters.

Guarantee: vfp_detect in tools/vfp.ts no longer performs its own recursive
filesystem walk as the source of truth. Detection logic lives once, in the
Python Core Service (vfp_driver.py detect -> vfp_toolchain). The TypeScript
tool only spawns the driver.

Run: py -m pytest tests/test_opencode_adapter.py -v
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tool_block(source, name):
    """Extract `export const <name> = tool({ ... })` (brace-balanced)."""
    marker = "export const %s = tool(" % name
    start = source.find(marker)
    assert start != -1, "tool %s not found in tools/vfp.ts" % name
    i = source.find("{", start)
    depth = 0
    for j in range(i, len(source)):
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
            if depth == 0:
                return source[start:j + 1]
    raise AssertionError("unbalanced tool block for %s" % name)


def test_vfp_detect_is_thin_adapter():
    with open(os.path.join(ROOT, "tools", "vfp.ts"), "r", encoding="utf-8") as f:
        source = f.read()
    block = _tool_block(source, "vfp_detect")
    # must route through the Core Service driver
    assert "runDriver" in block and '"detect"' in block
    # must NOT walk the filesystem itself
    assert "readdirSync" not in block
    assert "walk(" not in block
    # extension list must not be duplicated as the detection source of truth
    assert '".scx", ".vcx"' not in block


def test_vfp_capabilities_is_thin_adapter():
    with open(os.path.join(ROOT, "tools", "vfp.ts"), "r", encoding="utf-8") as f:
        source = f.read()
    block = _tool_block(source, "vfp_capabilities")
    assert "runDriver" in block and '"capabilities"' in block
    assert "readdirSync" not in block


def test_vfp_anonymization_status_is_thin_adapter():
    with open(os.path.join(ROOT, "tools", "vfp.ts"), "r", encoding="utf-8") as f:
        source = f.read()
    block = _tool_block(source, "vfp_anonymization_status")
    assert "runDriver" in block and '"anonymization_status"' in block
    # must not call mutating operations
    for forbidden in ("anonymize_directory", "make_dbf_recovery", "self_test"):
        assert forbidden not in block
