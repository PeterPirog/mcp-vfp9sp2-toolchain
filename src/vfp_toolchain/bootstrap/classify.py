# -*- coding: utf-8 -*-
"""Start-state classification (REQ-G00-001 / REQ-G00-034 / REQ-G00-036).

Read-only inspection of the declared REPO_ROOT occupancy.  Classification is
scoped to REPO_ROOT only; PROJECT_HOME siblings never influence the result.
At the bootstrap foundation the classifier is conservative and fail-closed:
it recognizes ABSENT, EMPTY, and verified MATCHING_BOOTSTRAP_RESUME states;
every other non-empty state maps to UNKNOWN_NONEMPTY (hence AMBIGUOUS for the
start mode), which fails closed before autonomous coding.  Brownfield
eligibility recognition (REQ-G00-043) is intentionally not implemented yet;
its verifier remains PLANNED and no brownfield write path is exposed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CLASSIFICATION_SCHEMA_VERSION = 1

OCCUPANCY_STATES = (
    "ABSENT",
    "EMPTY",
    "MATCHING_BOOTSTRAP_RESUME",
    "BROWNFIELD_PRODUCT",
    "UNKNOWN_NONEMPTY",
)

START_MODES = ("GREENFIELD", "BROWNFIELD", "AMBIGUOUS")

RESUME_PROVENANCE_FILENAME = "evidence/bootstrap/candidate-provenance.json"


class StartStateClassifier:
    """Deterministic REPO_ROOT occupancy classifier."""

    def __init__(self, repo_root: Path, expected_sot_sha256: str | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.expected_sot_sha256 = expected_sot_sha256.upper() if expected_sot_sha256 else None

    def classify(self) -> dict[str, Any]:
        """Return machine-readable classification without mutating anything."""
        root = self.repo_root
        if not root.exists():
            return self._result("ABSENT", "GREENFIELD", ["no_directory"])
        if not root.is_dir():
            return self._result("UNKNOWN_NONEMPTY", "AMBIGUOUS", ["not_a_directory"])
        entries = [entry for entry in root.iterdir() if entry.name not in (".git",)]
        if not entries:
            git_dir = root / ".git"
            if git_dir.exists():
                return self._result("EMPTY", "GREENFIELD", ["empty_git_repository"])
            return self._result("EMPTY", "GREENFIELD", ["empty_directory"])
        resume = self._matching_resume(root)
        if resume is not None:
            return self._result("MATCHING_BOOTSTRAP_RESUME", "GREENFIELD", resume)
        return self._result("UNKNOWN_NONEMPTY", "AMBIGUOUS", ["nonempty_unknown_content"])

    # ------------------------------------------------------------------
    def _matching_resume(self, root: Path) -> list[str] | None:
        provenance_path = root / RESUME_PROVENANCE_FILENAME
        if not provenance_path.is_file():
            return None
        try:
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if payload.get("schema_version") != CLASSIFICATION_SCHEMA_VERSION:
            return None
        kind = payload.get("provenance_kind")
        if kind not in ("GREENFIELD_BOOTSTRAP_RESUME", "BROWNFIELD_BOOTSTRAP_RESUME"):
            return None
        sot_hash = payload.get("sot_sha256")
        if not isinstance(sot_hash, str) or not re.fullmatch(r"[0-9A-Fa-f]{64}", sot_hash):
            return None
        if self.expected_sot_sha256 and sot_hash.upper() != self.expected_sot_sha256:
            return None
        tree = payload.get("candidate_tree_sha256")
        if not isinstance(tree, str) or not re.fullmatch(r"[0-9A-Fa-f]{40,64}", tree):
            return None
        return [
            "provenance_bound_to_sot_sha256",
            "provenance_bound_to_candidate_tree",
        ]

    def _result(self, occupancy: str, start_mode: str, signals: list[str]) -> dict[str, Any]:
        return {
            "classification_schema_version": CLASSIFICATION_SCHEMA_VERSION,
            "repo_root": str(self.repo_root),
            "occupancy": occupancy,
            "start_mode": start_mode,
            "signals": signals,
            "mutation_performed": False,
            "notes": (
                "Conservative foundation classifier: recognizes ABSENT/EMPTY/"
                "MATCHING_BOOTSTRAP_RESUME only. Full brownfield eligibility "
                "recognition (REQ-G00-043) is PLANNED; unknown content fails "
                "closed as AMBIGUOUS."
            ),
        }


def classify_start_state(repo_root: Path, expected_sot_sha256: str | None = None) -> dict[str, Any]:
    """Convenience wrapper used by bootstrap integration tooling."""
    return StartStateClassifier(repo_root, expected_sot_sha256).classify()


def sha256_file(path: Path) -> str:
    """SHA-256 of file bytes, uppercase hex (hash-before-mutation helper)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()