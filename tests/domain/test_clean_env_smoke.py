# -*- coding: utf-8 -*-
"""REQ-P00-011: clean-environment smoke acceptance definition + mechanics (deterministic).

The heavy five-minor acceptance itself is executed by
``tools/clean_env_smoke.py``.  This module deterministically validates:

* the DEFINITION of that acceptance (required minors, required check names,
  deterministic plan output, stdlib-only implementation, typed
  host-prerequisite blocker vocabulary); and
* the per-minor INTERPRETER MECHANICS that remediate FINDING-P00A3R-001:
  every per-minor venv must be created by the exact probed interpreter for
  that minor (``<interpreter> -m venv --clear <venv_root>``), the venv's own
  interpreter must be the one whose identity is attested, and any
  executed-vs-requested mismatch must fail closed with a typed code —
  never PASS.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-P00-011",
    "REQ-AUTO-004",
)

SMOKE_TOOL = REPO_ROOT / "tools" / "clean_env_smoke.py"

EXPECTED_MINORS = ["3.10", "3.11", "3.12", "3.13", "3.14"]
EXPECTED_CHECKS = (
    "clean_wheel_install",
    "import_vfp_toolchain",
    "package_metadata_version_readable",
    "canonical_python_contract_readable",
    "canonical_dialect_identity_readable",
    "no_unsupported_capability_falsely_reported",
    "executed_minor_matches_expected",
)


def _load_tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location("clean_env_smoke_tool_mechanics", SMOKE_TOOL)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def plan_blocker_for(minor: str) -> str:
    return f"PYTHON_{minor.replace('.', '')}_HOST_PREREQUISITE_MISSING"


class CleanEnvironmentSmokeDefinitionTests(unittest.TestCase):
    def test_smoke_tool_exists(self) -> None:
        self.assertTrue(SMOKE_TOOL.is_file(), "tools/clean_env_smoke.py must exist")

    def test_plan_is_deterministic_and_complete(self) -> None:
        first = subprocess.run(
            [sys.executable, str(SMOKE_TOOL), "--plan"], capture_output=True, text=True, timeout=120
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run(
            [sys.executable, str(SMOKE_TOOL), "--plan"], capture_output=True, text=True, timeout=120
        )
        plan_a = json.loads(first.stdout)
        plan_b = json.loads(second.stdout)
        self.assertEqual(plan_a, plan_b)
        self.assertEqual(plan_a["required_minors"], EXPECTED_MINORS)
        self.assertEqual(plan_a["required_check_names"], list(EXPECTED_CHECKS))
        self.assertEqual(plan_a["canonical_python_range"], ">=3.10,<3.15")
        self.assertEqual(plan_a["canonical_dialect"], "microsoft.visual-foxpro.9.0.sp2")
        self.assertIn("<interpreter> -m venv --clear <venv_root>", plan_a["venv_creation_policy"])
        for minor in EXPECTED_MINORS:
            code = f"PYTHON_{minor.replace('.', '')}_HOST_PREREQUISITE_MISSING"
            self.assertIn(code, plan_a["blocker_vocabulary"])

    def test_smoke_tool_is_stdlib_only_and_offline(self) -> None:
        text = SMOKE_TOOL.read_text(encoding="utf-8")
        network_pattern = re.compile(
            r"^\s*(import|from)\s+(socket|ssl|urllib\.request|http\.client|requests|httpx|aiohttp|urllib3)\b",
            re.MULTILINE,
        )
        self.assertIsNone(network_pattern.search(text))
        self.assertNotIn("--index-url", text)
        self.assertIn("--no-index", text)
        self.assertIn("--no-deps", text)

    def test_missing_interpreter_is_typed_blocker_not_skip(self) -> None:
        # The run path must classify a missing interpreter as a typed
        # BLOCKED entry — never as a skipped PASS (REQ-AUTO-004).
        module = _load_tool()
        for minor in EXPECTED_MINORS:
            self.assertEqual(module._blocker_code(minor), plan_blocker_for(minor))
        self.assertIn('"BLOCKED"', SMOKE_TOOL.read_text(encoding="utf-8"))
        self.assertNotIn('"SKIPPED"', SMOKE_TOOL.read_text(encoding="utf-8"))
        plan = module.plan()
        self.assertEqual(
            plan["blocker_vocabulary"],
            [plan_blocker_for(minor) for minor in EXPECTED_MINORS],
        )


class CleanEnvVenvMechanicsTests(unittest.TestCase):
    """Regression coverage for FINDING-P00A3R-001 (per-minor interpreter integrity).

    The discovered defect: venv.create() silently based every per-minor venv
    on the interpreter running the smoke tool, so all "per-minor" clean
    environments executed one interpreter (3.12.10) while the sealed evidence
    recorded the probed versions of other minors.  These tests prove the
    remediated tool cannot reproduce that behavior.
    """

    PROBED_311 = {"path": r"C:\Host\Python311\python.exe", "version": "3.11.9", "minor": "3.11"}
    IDENTITY_311 = {
        "python_version": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]",
        "version_info": {"major": 3, "minor": 11, "micro": 9},
        "executable": r"C:\Host\Python311\python.exe",
        "implementation": "cpython",
        "architecture": ["64bit", "WindowsPE"],
    }
    IDENTITY_312 = {
        "python_version": "3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]",
        "version_info": {"major": 3, "minor": 12, "micro": 10},
        "executable": r"C:\Host\Python312\python.exe",
        "implementation": "cpython",
        "architecture": ["64bit", "WindowsPE"],
    }

    def setUp(self) -> None:
        self.tool = _load_tool()
        self.tmp = Path(tempfile.mkdtemp(prefix="clean-env-mechanics-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.venv_root = self.tmp / "venv-3.11"
        (self.venv_root / "Scripts").mkdir(parents=True)
        self.venv_python = self.venv_root / "Scripts" / "python.exe"
        self.venv_python.write_text("# simulated venv interpreter\n", encoding="utf-8")
        self.wheel = self.tmp / "product.whl"

    # -- static defect guard ------------------------------------------------

    def test_tool_never_uses_venv_module_or_venv_create(self) -> None:
        tree = ast.parse(SMOKE_TOOL.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(
                    any(alias.name == "venv" for alias in node.names),
                    "per-minor venvs must not be created via the venv API",
                )
            if isinstance(node, ast.Attribute) and node.attr == "create":
                self.assertFalse(
                    isinstance(node.value, ast.Name) and node.value.id == "venv",
                    "venv.create() must not be called (FINDING-P00A3R-001)",
                )

    # -- venv creation command mechanics -------------------------------------

    def test_venv_command_uses_exact_probed_interpreter(self) -> None:
        command = self.tool._build_venv_command(Path(self.PROBED_311["path"]), Path(r"W:\venv-3.11"))
        self.assertEqual(command[0], self.PROBED_311["path"])
        self.assertEqual(command[1:4], ["-m", "venv", "--clear"])
        self.assertEqual(command[4], r"W:\venv-3.11")
        self.assertNotEqual(command[0], sys.executable)

    def test_different_requested_interpreters_produce_different_commands(self) -> None:
        a = self.tool._build_venv_command(Path(r"C:\Host\Python310\python.exe"), Path(r"W:\venv-3.10"))
        b = self.tool._build_venv_command(Path(r"C:\Host\Python311\python.exe"), Path(r"W:\venv-3.11"))
        self.assertNotEqual(a[0], b[0])
        self.assertEqual(a[1:4], b[1:4])
        self.assertNotEqual(a[4], b[4])

    def _fake_run_recording(self, calls: list, identity: dict) -> object:
        def fake_run(cmd, capture_output=False, text=False, timeout=None):
            calls.append(list(cmd))
            if cmd[1:3] == ["-m", "venv"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if len(cmd) > 1 and cmd[1] == "-c":
                return SimpleNamespace(returncode=0, stdout=json.dumps(identity) + "\n", stderr="")
            if cmd[1:3] == ["-m", "pip"]:
                return SimpleNamespace(returncode=0, stdout="installed", stderr="")
            # check program invocation
            self.assertEqual(cmd[2], self.PROBED_311["minor"])
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "checks": [{"name": name, "status": "PASS"} for name in self.tool.REQUIRED_CHECK_NAMES],
                        "python_version": identity["python_version"],
                    }
                )
                + "\n",
                stderr="",
            )

        return fake_run

    def test_run_minor_smoke_uses_probed_interpreter_and_venv_python(self) -> None:
        calls: list = []
        with mock.patch.object(self.tool.subprocess, "run", side_effect=self._fake_run_recording(calls, self.IDENTITY_311)):
            entry = self.tool._run_minor_smoke(dict(self.PROBED_311), self.wheel, self.venv_root)
        self.assertEqual(entry["status"], "PASS", entry)
        # 1. venv created by the exact probed interpreter, never the tool runner
        self.assertEqual(calls[0][0], self.PROBED_311["path"])
        self.assertEqual(calls[0][1:4], ["-m", "venv", "--clear"])
        # 2. executed-version attestation executed by the VENV's own python
        self.assertEqual(calls[1][0], str(self.venv_python))
        # 3. installation uses the venv python with the offline policy
        install = next(c for c in calls if c[1:3] == ["-m", "pip"])
        self.assertEqual(install[0], str(self.venv_python))
        self.assertIn("--no-index", install)
        self.assertIn("--no-deps", install)
        # 4. checks run inside the per-minor environment with expected minor argv
        check = next(c for c in calls if str(c[1]).endswith("check.py"))
        self.assertEqual(check[0], str(self.venv_python))
        self.assertEqual(check[2], "3.11")
        # executed identity fields come from the venv interpreter itself
        self.assertEqual(entry["executed_interpreter_version"], "3.11.9")
        self.assertEqual(entry["executed_major_minor"], "3.11")
        self.assertEqual(entry["discovered_interpreter_version"], "3.11.9")
        self.assertEqual(entry["executed_python_version_at_checks"], self.IDENTITY_311["python_version"])

    # -- fail-closed executed-identity attestation ---------------------------

    def test_executed_minor_mismatch_fails_closed(self) -> None:
        blockers = self.tool._validate_executed_identity("3.11", self.IDENTITY_312, "3.11.9")
        self.assertEqual(blockers[0], "EXECUTED_PYTHON_MINOR_MISMATCH")

    def test_executed_implementation_mismatch_fails_closed(self) -> None:
        identity = dict(self.IDENTITY_311, implementation="pypy")
        blockers = self.tool._validate_executed_identity("3.11", identity, "3.11.9")
        self.assertIn("EXECUTED_PYTHON_IMPLEMENTATION_MISMATCH", blockers)

    def test_creator_interpreter_switch_within_minor_detected(self) -> None:
        identity = dict(self.IDENTITY_311)
        identity["version_info"] = {"major": 3, "minor": 11, "micro": 8}
        blockers = self.tool._validate_executed_identity("3.11", identity, "3.11.9")
        self.assertIn("EXECUTED_PYTHON_VERSION_MISMATCH", blockers)

    # -- the exact discovered defect cannot recur ----------------------------

    def test_regression_expected_311_probed_311_executed_312_never_pass(self) -> None:
        # Defect shape: requested/probed minor 3.11 (3.11.9) while the venv
        # actually executes 3.12.10 — the tool must FAIL with the typed
        # mismatch and must not run any check that could report PASS.
        calls: list = []
        with mock.patch.object(self.tool.subprocess, "run", side_effect=self._fake_run_recording(calls, self.IDENTITY_312)):
            entry = self.tool._run_minor_smoke(dict(self.PROBED_311), self.wheel, self.venv_root)
        self.assertNotEqual(entry["status"], "PASS")
        self.assertEqual(entry["status"], "FAIL")
        self.assertEqual(entry["blocker_code"], "EXECUTED_PYTHON_MINOR_MISMATCH")
        # the executed record carries the ACTUAL executed version, not the probed label
        self.assertEqual(entry["executed_interpreter_version"], "3.12.10")
        self.assertEqual(entry["discovered_interpreter_version"], "3.11.9")
        self.assertNotEqual(entry["executed_interpreter_version"], entry["discovered_interpreter_version"])
        # no wheel installation and no checks ran after the mismatch
        self.assertFalse(any(c[1:3] == ["-m", "pip"] for c in calls))
        self.assertFalse(any(len(c) > 1 and str(c[1]).endswith("check.py") for c in calls))

    def test_run_smoke_report_derives_from_executed_records_not_probe_labels(self) -> None:
        executed_entry = {
            "expected_minor": "3.11",
            "discovered_interpreter_path": self.PROBED_311["path"],
            "discovered_interpreter_version": "3.11.9",
            "venv_python_path": str(self.venv_python),
            "executed_interpreter_version": "3.12.10",
            "executed_major_minor": "3.12",
            "status": "FAIL",
            "blocker_code": "EXECUTED_PYTHON_MINOR_MISMATCH",
            "error": "executed venv interpreter identity does not match the requested minor (fail closed)",
        }
        with mock.patch.object(self.tool, "probe_interpreter", return_value=dict(self.PROBED_311)), mock.patch.object(
            self.tool, "_build_wheel", return_value=self.wheel
        ), mock.patch.object(self.tool, "_run_minor_smoke", return_value=executed_entry):
            report = self.tool.run_smoke([Path(self.PROBED_311["path"])], REPO_ROOT, self.tmp / "work")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["per_minor"]["3.11"]["executed_interpreter_version"], "3.12.10")
        self.assertEqual(report["per_minor"]["3.11"]["discovered_interpreter_version"], "3.11.9")
        self.assertNotEqual(
            report["per_minor"]["3.11"]["executed_interpreter_version"],
            report["per_minor"]["3.11"]["discovered_interpreter_version"],
        )
        self.assertIn("executed", report["evidence_source"])
        for minor in ("3.10", "3.12", "3.13", "3.14"):
            self.assertEqual(report["per_minor"][minor]["status"], "BLOCKED")
            self.assertEqual(report["per_minor"][minor]["blocker_code"], plan_blocker_for(minor))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()