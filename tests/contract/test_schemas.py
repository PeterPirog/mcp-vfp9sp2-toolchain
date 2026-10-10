# -*- coding: utf-8 -*-
"""Schema document + artifact conformance tests (REQ-G00-025 / REQ-PORT-022)."""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-G00-025",
    "REQ-PORT-022",
)

EXPECTED_SCHEMAS = (
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


class SchemaValidationTests(unittest.TestCase):
    def test_required_schema_set_present(self) -> None:
        schemas_dir = REPO_ROOT / "spec" / "schemas"
        present = {p.name for p in schemas_dir.glob("*.schema.json")}
        missing = [name for name in EXPECTED_SCHEMAS if name not in present]
        self.assertEqual(missing, [])

    def test_schema_document_and_artifact_validation(self) -> None:
        try:
            import jsonschema  # type: ignore  # noqa: F401
        except ImportError:
            self.fail(
                "BLOCKED: SCHEMA_CAPABILITY_UNAVAILABLE — jsonschema is not importable; "
                "dependency resolution is pending an approved origin (fail closed, no silent skip)."
            )
        from vfp_toolchain.verification import engine

        report = engine.schema_validation_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["schema_document_count"], len(EXPECTED_SCHEMAS))
        self.assertGreaterEqual(report["artifact_instance_count"], 12)

    def test_no_network_dereferencing_in_schemas(self) -> None:
        # Local/bundled $ref only: every $ref in every schema document must be
        # local (relative or '#...'), and $id/$schema identities are allowed
        # URI strings that validators must resolve from the local registry.
        import json

        for name in EXPECTED_SCHEMAS:
            document = json.loads((REPO_ROOT / "spec" / "schemas" / name).read_text(encoding="utf-8"))
            self._assert_local_refs(document, name)

    def _assert_local_refs(self, node: object, name: str) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                self.assertTrue(
                    ref.startswith("#") or (not ref.startswith(("http://", "https://", "urn:"))),
                    f"{name}: non-local $ref {ref}",
                )
            for value in node.values():
                self._assert_local_refs(value, name)
        elif isinstance(node, list):
            for value in node:
                self._assert_local_refs(value, name)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()