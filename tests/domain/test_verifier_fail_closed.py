# -*- coding: utf-8 -*-
"""REQ-AUTO-004 negative controls for the verifier command runner.

Every listed failure mode must fail closed instead of converting to PASS:

* zero collected tests from an EXECUTABLE verifier;
* unexpected skip/xfail in a passing exit code;
* timeout;
* crashed/non-zero verifier process;
* PLANNED verifier can never PASS;
* unknown requirement ID fails closed.
"""

from __future__ import annotations

import json
import sys
import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-AUTO-004",
    "REQ-AUTO-002",
    "REQ-PORT-007",
)

from vfp_toolchain.verification import engine  # noqa: E402

_ZERO_TESTS_PROG = (
    "import unittest as u\n"
    "class T(u.TestCase):\n"
    "    pass\n"
    "u.main(module='__main__', argv=['prog'], exit=False)\n"
)
_SKIPPED_PROG = (
    "import unittest as u\n"
    "@u.skip('deliberate')\n"
    "class T(u.TestCase):\n"
    "    def test_x(self):\n"
    "        pass\n"
    "u.main(module='__main__', argv=['prog'], exit=False)\n"
)


def _verifier(command: list[str]) -> dict:
    return {
        "verifier_id": "VER-NEGATIVE-CONTROL",
        "state": "EXECUTABLE",
        "command": command,
        "evidence_class": "UNITTEST_REPORT",
        "required_capabilities": [],
        "covers": ["REQ-AUTO-004"],
        "notes": "synthetic negative-control verifier",
    }


class VerifierRunnerFailClosedTests(unittest.TestCase):
    def test_zero_collected_tests_fails_closed(self) -> None:
        result = engine._execute_verifier_command(
            _verifier([sys.executable, "-c", _ZERO_TESTS_PROG]), REPO_ROOT
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result.get("error_code"), "ZERO_COLLECTED_TESTS", result)

    def test_zero_collected_tests_via_discover_fails_closed(self) -> None:
        result = engine._execute_verifier_command(
            _verifier([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", "no_such_tests_*.py"]),
            REPO_ROOT,
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result.get("error_code"), "ZERO_COLLECTED_TESTS", result)

    def test_unexpected_skip_fails_closed(self) -> None:
        result = engine._execute_verifier_command(
            _verifier([sys.executable, "-c", _SKIPPED_PROG]), REPO_ROOT
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result.get("error_code"), "UNEXPECTED_SKIP_XFAIL", result)

    def test_timeout_fails_closed(self) -> None:
        result = engine._execute_verifier_command(
            _verifier([sys.executable, "-c", "import time; time.sleep(8)"]),
            REPO_ROOT,
            timeout=1,
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result.get("error_code"), "VERIFIER_TIMEOUT", result)

    def test_crashed_verifier_fails_closed(self) -> None:
        result = engine._execute_verifier_command(
            _verifier([sys.executable, "-c", "raise SystemExit(3)"]),
            REPO_ROOT,
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result.get("error_code"), "VERIFIER_NONZERO_EXIT", result)
        self.assertEqual(result.get("exit_code"), 3, result)

    def test_planned_verifier_cannot_pass(self) -> None:
        planned = _verifier([sys.executable, "-c", "print('would be pass')"])
        planned["state"] = "PLANNED"
        planned["command"] = None
        graph = json.loads((REPO_ROOT / "spec" / "requirements.graph.json").read_text(encoding="utf-8"))
        result = engine.dispatch_requirement(
            "REQ-AUTO-004",
            {
                "start_mode": "GREENFIELD",
                "authoring_mode": "HYBRID",
                "operation_scope": "LOCAL_QUALIFICATION",
                "release_profile": "NONE",
                "release_context": "NONE",
            },
            REPO_ROOT,
            graph=graph,
            manifest={
                "requirements": {
                    "REQ-AUTO-004": {
                        "lifecycle": "BOOTSTRAP",
                        "applicability": {"override": None, "expression": {"default": "ALWAYS"}},
                        "verifier_ids": ["VER-NEGATIVE-CONTROL"],
                    }
                },
                "verifiers": {"VER-NEGATIVE-CONTROL": planned},
            },
        )
        self.assertEqual(result["status"], "PLANNED", result)
        self.assertNotEqual(result["status"], "PASS")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
