# -*- coding: utf-8 -*-
"""Canonical JSON hashing for portable contract artifacts.

Implements the deterministic logical serialization profile required by
REQ-PORT-017: an RFC 8785 (JCS) compatible canonical form for the closed value
domain used by all generated control-plane artifacts (objects, arrays,
strings, booleans, integers, null; BMP code points; no floating-point
numbers).  For this closed domain the canonical form is byte-equivalent to
RFC 8785 canonical JSON: object keys are sorted by code point (equivalent to
UTF-16 code unit order for BMP), string escaping is minimal, numbers are
integers only, and no insignificant whitespace is emitted.

Generated artifacts never contain floats, NaN, or non-BMP characters, so this
profile is exact for the artifact set it hashes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Fields that are metadata rather than logical content. They may appear in an
# artifact for human/operational convenience but are excluded from the
# canonical logical-content hash so regeneration stays logically stable
# (REQ-PORT-018: timestamp as non-authoritative metadata).
LOGICAL_EXCLUDED_FIELDS = frozenset({"generated_at_utc", "content_sha256"})


def _assert_closed_domain(obj: Any, path: str = "$") -> None:
    """Reject values outside the closed canonical domain (fail closed)."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return
    if isinstance(obj, float):
        raise TypeError(f"canonical domain: float forbidden at {path}")
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(f"canonical domain: non-string key at {path}")
            _assert_closed_domain(value, f"{path}.{key}")
        return
    if isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            _assert_closed_domain(value, f"{path}[{index}]")
        return
    raise TypeError(f"canonical domain: unsupported type {type(obj)!r} at {path}")


def canonical_bytes(obj: Any) -> bytes:
    """Return the canonical JCS-profile serialization of *obj* as UTF-8 bytes."""
    _assert_closed_domain(obj)
    text = json.dumps(
        obj,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def canonical_sha256(obj: Any) -> str:
    """SHA-256 of the canonical logical serialization, uppercase hex."""
    return hashlib.sha256(canonical_bytes(obj)).hexdigest().upper()


def strip_logical_metadata(obj: Any) -> Any:
    """Deep-copy *obj* without LOGICAL_EXCLUDED_FIELDS at any object level."""
    if isinstance(obj, dict):
        return {
            key: strip_logical_metadata(value)
            for key, value in obj.items()
            if key not in LOGICAL_EXCLUDED_FIELDS
        }
    if isinstance(obj, list):
        return [strip_logical_metadata(value) for value in obj]
    return obj


def logical_sha256(obj: Any) -> str:
    """Canonical logical-content hash excluding non-authoritative metadata."""
    return canonical_sha256(strip_logical_metadata(obj))


def sorted_id_digest(ids: list[str]) -> str:
    """Deterministic digest over a requirement-ID list (canonical JSON form)."""
    ordered = sorted(ids)
    return canonical_sha256(ordered)


def artifact_json_bytes(artifact: dict) -> bytes:
    """Deterministic on-disk JSON for a generated artifact (pretty, sorted)."""
    _assert_closed_domain(artifact)
    text = json.dumps(
        artifact,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    )
    return (text + "\n").encode("utf-8")