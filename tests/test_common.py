#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_common.py - unit tests for vfp_common.

Run:  py -m pytest tests/ -v   (or:  py tests/test_common.py)
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_common


def test_default_excludes_includes_required():
    """Canonical list must include the core exclusions."""
    excl = set(vfp_common.default_excludes())
    for required in ("backup", "backups", "archive", "tmp", "node_modules"):
        assert required in excl, "missing %r in default_excludes: %s" % (required, excl)


def test_default_excludes_is_lowercase():
    """All entries must be lowercase."""
    for x in vfp_common.default_excludes():
        assert x == x.lower(), "not lowercase: %r" % x


def test_should_skip_dir_dot_prefix():
    """Any dot-prefixed directory is skipped."""
    assert vfp_common.should_skip_dir(".git")
    assert vfp_common.should_skip_dir(".vfp-ai")
    assert vfp_common.should_skip_dir(".opencode")


def test_should_skip_dir_known():
    """Known exclusions are skipped."""
    assert vfp_common.should_skip_dir("backup")
    assert vfp_common.should_skip_dir("backups")
    assert vfp_common.should_skip_dir("archive")
    assert vfp_common.should_skip_dir("tmp")


def test_should_skip_dir_normal():
    """Normal directories are NOT skipped."""
    assert not vfp_common.should_skip_dir("src")
    assert not vfp_common.should_skip_dir("DANE")
    assert not vfp_common.should_skip_dir("project")


def test_foxbin2prg_program_returns_path():
    """Must return an absolute path ending with foxbin2prg.prg."""
    p = vfp_common.foxbin2prg_program()
    assert os.path.isabs(p), "not absolute: %s" % p
    assert os.path.basename(p).lower() == "foxbin2prg.prg", "wrong basename: %s" % p


@pytest.mark.skipif(
    os.name != "nt",
    reason="asserts Windows path semantics (C:\\ prefix); target platform is Windows")
def test_foxbin2prg_env_override():
    """VFP_FOXBIN2PRG_DIR must override the default (Windows path semantics)."""
    orig = os.environ.get("VFP_FOXBIN2PRG_DIR")
    try:
        os.environ["VFP_FOXBIN2PRG_DIR"] = r"C:\fake\foxbin2prg"
        p = vfp_common.foxbin2prg_program()
        assert p.startswith(r"C:\fake\foxbin2prg"), "env override not respected: %s" % p
    finally:
        if orig is None:
            os.environ.pop("VFP_FOXBIN2PRG_DIR", None)
        else:
            os.environ["VFP_FOXBIN2PRG_DIR"] = orig


def test_binary_companion_pairs():
    """Primary VFP binary artifacts must use their real binary memo companions."""
    assert vfp_common.COMPANIONS[".scx"] == (".sct",)
    assert vfp_common.COMPANIONS[".vcx"] == (".vct",)
    assert vfp_common.COMPANIONS[".frx"] == (".frt",)
    assert vfp_common.COMPANIONS[".mnx"] == (".mnt",)
    assert vfp_common.COMPANIONS[".pjx"] == (".pjt",)
    assert vfp_common.COMPANIONS[".lbx"] == (".lbt",)
    assert vfp_common.COMPANIONS[".dbc"] == (".dcx", ".dct")


def test_label_text_representation_is_not_binary_companion():
    """FoxBin2Prg .lb2 text output must never be mistaken for Label Designer .lbt."""
    assert ".lb2" not in vfp_common.COMPANIONS[".lbx"]


if __name__ == "__main__":
    fns = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print("  PASS  %s" % fn.__name__)
    print("\n%d/%d passed" % (passed, len(fns)))
