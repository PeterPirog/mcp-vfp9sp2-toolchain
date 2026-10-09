# -*- coding: utf-8 -*-
"""REQ-P00-001: canonical VFP9 SP2 dialect identity gate + negative fixtures.

Deterministic evidence:
* canonical dialect-identity report (identifier/family/version/SP/classification);
* exact identifier equality;
* runtime/version reporting through the package and Core-visible constants;
* negative fixtures: older FoxPro / Visual FoxPro identities are rejected as
  product dialect identities;
* no generic "FoxPro" fallback identity exists.
"""

from __future__ import annotations

import unittest

from tests.support import REPO_ROOT

REQUIREMENT_IDS = (
    "REQ-P00-001",
)

import vfp_toolchain  # noqa: E402
from vfp_toolchain import domain  # noqa: E402
from vfp_toolchain.verification import engine  # noqa: E402

CANONICAL = "microsoft.visual-foxpro.9.0.sp2"


class DialectIdentityTests(unittest.TestCase):
    def test_canonical_dialect_identifier_exact(self) -> None:
        self.assertEqual(domain.TARGET_DIALECT, CANONICAL)
        self.assertEqual(vfp_toolchain.TARGET_DIALECT, CANONICAL)

    def test_identity_report_fields(self) -> None:
        identity = domain.dialect_identity()
        self.assertEqual(identity["dialect_identifier"], CANONICAL)
        self.assertEqual(identity["product_family"], "Microsoft Visual FoxPro")
        self.assertEqual(identity["major_version"], 9)
        self.assertEqual(identity["service_pack_baseline"], "SP2")
        self.assertEqual(identity["support_classification"], "SOLE_SUPPORTED_DIALECT")
        self.assertIs(identity["sole_dialect_target"], True)
        self.assertEqual(identity["older_release_semantics"], "NOT_AUTOMATICALLY_SUPPORTED")
        self.assertEqual(identity["older_element_relevance_rule"], "RELEVANT_ONLY_WHEN_DOCUMENTED_IN_PINNED_VFP9SP2_CORPUS")

    def test_identity_report_is_deterministic(self) -> None:
        self.assertEqual(domain.dialect_identity(), domain.dialect_identity())

    def test_only_exact_identifier_is_supported(self) -> None:
        self.assertTrue(domain.is_supported_product_dialect(CANONICAL))
        self.assertFalse(domain.is_supported_product_dialect(CANONICAL + " "))
        self.assertFalse(domain.is_supported_product_dialect("Microsoft.Visual-FoxPro.9.0.SP2"))
        self.assertFalse(domain.is_supported_product_dialect("microsoft.visual-foxpro.9.0.SP2"))

    def test_negative_older_version_identities_rejected(self) -> None:
        older_identities = (
            "microsoft.visual-foxpro.9.0",       # VFP9 without SP2 baseline
            "microsoft.visual-foxpro.9.0.sp1",   # earlier service pack
            "microsoft.visual-foxpro.8.0.sp1",   # Visual FoxPro 8
            "microsoft.visual-foxpro.7.0",       # Visual FoxPro 7
            "microsoft.visual-foxpro.6.0",       # Visual FoxPro 6
            "microsoft.visual-foxpro.5.0",       # Visual FoxPro 5
            "microsoft.visual-foxpro.3.0",       # Visual FoxPro 3
            "microsoft.foxpro.2.6",              # FoxPro 2.x
            "microsoft.foxpro.2.6.sp1",          # FoxPro 2.x service pack
        )
        for identifier in older_identities:
            classification = domain.classify_dialect_identity(identifier)
            self.assertEqual(classification, domain.CLASSIFICATION_REJECTED_OTHER_VERSION, identifier)
            self.assertFalse(domain.is_supported_product_dialect(identifier), identifier)

    def test_negative_generic_foxpro_fallback_rejected(self) -> None:
        generic_identities = ("vfp", "foxpro", "visual-foxpro", "microsoft.visual-foxpro", "xbase", "dbase")
        for identifier in generic_identities:
            self.assertEqual(domain.classify_dialect_identity(identifier), domain.CLASSIFICATION_REJECTED_GENERIC, identifier)
            self.assertFalse(domain.is_supported_product_dialect(identifier), identifier)

    def test_negative_unrecognized_identities_rejected(self) -> None:
        for identifier in ("", "microsoft", "microsoft.visual-foxpro.9.0.sp2-x", "vfp9sp2"):
            self.assertEqual(domain.classify_dialect_identity(identifier), domain.CLASSIFICATION_REJECTED_UNRECOGNIZED, identifier)

    def test_report_negative_probe_gate(self) -> None:
        report = engine.dialect_identity_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        negative = report["negative_gate"]
        self.assertEqual(negative["expectation"], "ALL_REJECTED_AS_NON_PRODUCT_DIALECT")
        self.assertEqual(negative["rejected_probe_count"], len(domain.DIALECT_NEGATIVE_PROBES))
        for check in report["checks"]:
            self.assertEqual(check["status"], "PASS", check)

    def test_no_duplicate_dialect_literal_in_product_modules(self) -> None:
        import re

        src_root = REPO_ROOT / "src" / "vfp_toolchain"
        offenders: list[str] = []
        for path in sorted(src_root.rglob("*.py")):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative in ("src/vfp_toolchain/domain.py", "src/vfp_toolchain/__init__.py"):
                continue
            if relative.startswith("src/vfp_toolchain/verification/"):
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"[\"']microsoft\.visual-foxpro\.", text):
                offenders.append(relative)
        self.assertEqual(offenders, [])

    def test_runtime_version_reporting(self) -> None:
        self.assertEqual(vfp_toolchain.domain.dialect_identity()["major_version"], 9)
        self.assertEqual(vfp_toolchain.domain.dialect_identity()["service_pack_baseline"], "SP2")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
