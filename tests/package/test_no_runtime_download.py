# -*- coding: utf-8 -*-
"""No-runtime-download sentinel tests (REQ-G00-008 / REQ-P00-009)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-G00-008",
    "REQ-P00-009",
)

FORBIDDEN_IMPORTS = (
    "socket", "ssl", "urllib.request", "urllib.parse", "http.client", "http.server",
    "ftplib", "smtplib", "telnetlib", "xmlrpc.client", "requests", "httpx", "aiohttp", "urllib3",
)

FORBIDDEN_INSTALL_PATTERNS = ("pip install", "pip_main", "ensurepip", "Invoke-WebRequest", "curl ", "wget ")


class NoRuntimeDownloadTests(unittest.TestCase):
    def test_package_source_has_no_network_imports(self) -> None:
        hits = []
        for path in sorted((REPO_ROOT / "src" / "vfp_toolchain").rglob("*.py")):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue
                for token in FORBIDDEN_IMPORTS:
                    if stripped == f"import {token}" or stripped.startswith(f"import {token} ") or stripped.startswith(f"from {token} "):
                        hits.append(f"{path.name}: {stripped}")
        self.assertEqual(hits, [])

    def test_package_source_has_no_install_calls(self) -> None:
        hits = []
        for path in sorted((REPO_ROOT / "src" / "vfp_toolchain").rglob("*.py")):
            text = path.read_text(encoding="utf-8").lower()
            for pattern in FORBIDDEN_INSTALL_PATTERNS:
                if pattern in text:
                    hits.append(f"{path.name}: {pattern}")
        self.assertEqual(hits, [])

    def test_runtime_dependency_declaration_is_empty(self) -> None:
        import re
        from pathlib import Path

        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        section = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL).group(1)
        match = re.search(r"(?m)^dependencies\s*=\s*\[([^\]]*)\]", section)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "")

    def test_dependency_lock_is_frozen_not_floating(self) -> None:
        import json

        lock = json.loads((REPO_ROOT / "spec" / "dependency-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["resolution_status"], "RESOLVED_FROZEN")
        self.assertIsNone(lock["blocker"])
        resolved = lock["resolved"]
        self.assertTrue(resolved["distributions"])
        self.assertEqual(
            lock["approved_origins"],
            [
                {"origin": "https://pypi.org/simple", "authorization_ref": "OPERATOR-GREENFIELD-PYPI-B0-2026-10-08"},
                {"origin": "https://files.pythonhosted.org", "authorization_ref": "OPERATOR-GREENFIELD-PYPI-B0-2026-10-08"},
            ],
        )
        # Exact resolved versions only: one distinct version per distribution,
        # every entry hash-pinned, and the runtime profile stays empty.
        versions: dict[str, set] = {}
        for entry in resolved["distributions"]:
            self.assertNotIn("runtime", entry["profile_membership"], entry["distribution"])
            versions.setdefault(entry["distribution"], set()).add(entry["version"])
        self.assertEqual({name: sorted(v) for name, v in versions.items() if len(v) != 1}, {})
        for artifact in lock["transitive_artifacts"]:
            self.assertRegex(artifact["sha256"], r"^[0-9A-Fa-f]{64}$", artifact["filename"])
        # The runtime wheel set is exactly the product wheel: no runtime
        # dependency artifact carries a runtime role membership.
        runtime_members = [entry for entry in resolved["distributions"] if "runtime" in entry["profile_membership"]]
        self.assertEqual(runtime_members, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()