# -*- coding: utf-8 -*-
"""
tests/test_offline_builder_versions.py - regression test for the offline
builder's Python version resolution contract (Phase 2 hardening, item 8).

The contract lives in ONE place (scripts/offline_build_common.ps1, dotted
into scripts/build_offline_bundle.ps1) so the CLI and this test cannot drift
apart. This test exercises that SAME function through a PowerShell
subprocess:

  * default (empty -PythonVersions) -> manifest supportedPython
    (runtime/runtime-dependencies.json: 3.10, 3.12, 3.14),
  * comma-separated CLI override "3.10,3.14" -> exactly [3.10, 3.14],
  * single "3.12" -> [3.12],
  * whitespace tolerance,
  * dedup,
  * invalid entry ("foo") -> controlled failure BEFORE pip
    (OFFLINE_DEPENDENCY_RESOLUTION_ERROR, non-zero exit),
  * pyTag derivation: 3.10->310, 3.12->312, 3.14->314.

The full end-to-end proof that a comma-separated CLI input reaches pip as
two separate --python-version arguments is the single-Python and full
bundle builds (dist/ wheelhouse layout wheels/310|312|314).
"""

import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
MANIFEST = os.path.join(ROOT, "runtime", "runtime-dependencies.json")
COMMON = os.path.join(SCRIPTS, "offline_build_common.ps1")
BUILDER = os.path.join(SCRIPTS, "build_offline_bundle.ps1")


def _pwsh():
    for exe in ("pwsh", "powershell"):
        try:
            subprocess.run([exe, "-NoProfile", "-Command", "Write-Host ok"],
                           capture_output=True, timeout=60, check=True)
            return exe
        except (OSError, subprocess.CalledProcessError):
            continue
    pytest.skip("no PowerShell 7 / Windows PowerShell available")


PWSH = _pwsh() or "pwsh"


def _psq(s):
    return "'" + s.replace("'", "''") + "'"


def _resolve2(override):
    code = (
        "$ErrorActionPreference = 'Stop'\n"
        f". {_psq(COMMON)}\n"
        f"$r = Resolve-BuildPythonVersions -ManifestPath {_psq(MANIFEST)} -Override {_psq(override)}\n"
        "($r.resolved -join ',')\n"
        "if ($r.rejected.Count -gt 0) { exit 1 }\n"
    )
    res = subprocess.run([PWSH, "-NoProfile", "-Command", code],
                         capture_output=True, text=True, timeout=120, cwd=ROOT)
    return res.returncode, res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""


def test_default_uses_manifest_supported_python():
    rc, got = _resolve2("")
    assert rc == 0, "default resolution must succeed"
    assert got.split(",") == ["3.10", "3.12", "3.14"], got


def test_comma_separated_cli_override():
    rc, got = _resolve2("3.10,3.14")
    assert rc == 0
    assert got == "3.10,3.14", got


def test_single_override():
    rc, got = _resolve2("3.12")
    assert rc == 0
    assert got == "3.12"


def test_whitespace_tolerance_and_dedup():
    rc, got = _resolve2(" 3.14 , 3.12 ,3.12")
    assert rc == 0
    assert got.split(",") == ["3.12", "3.14"], got


def test_invalid_entry_fails_before_pip():
    rc, got = _resolve2("foo")
    assert rc != 0, "invalid version must fail closed (OFFLINE_DEPENDENCY_RESOLUTION_ERROR before pip)"
    # and nothing that looks like a pip invocation happened (no wheelhouse writes
    # are possible: resolution throws before the staging step)
    assert "310" not in got and "312" not in got


def test_pytag_derivation():
    code = (
        "$ErrorActionPreference = 'Stop'\n"
        f". {_psq(COMMON)}\n"
        "'3.10 3.12 3.14' -split ' ' | ForEach-Object { Get-PythonTag $_ } | Join-String -Separator ','\n"
    )
    res = subprocess.run([PWSH, "-NoProfile", "-Command", code],
                         capture_output=True, text=True, timeout=120, cwd=ROOT)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "310,312,314"


def test_builder_declares_string_parameter_contract():
    """The builder param must be [string]$PythonVersions (single string),
    never [string[]] — the CLI passes strings; the script owns the split."""
    with open(BUILDER, "r", encoding="utf-8") as f:
        src = f.read()
    assert "[string]$PythonVersions" in src, (
        "builder must declare [string]$PythonVersions (single-string contract)")
    assert "[string[]]$PythonVersions" not in src
    # the resolved list lives in its own variable — the param is never overwritten
    assert "$resolvedPythonVersions" in src
    # one shared implementation of the contract
    assert "offline_build_common.ps1" in src
