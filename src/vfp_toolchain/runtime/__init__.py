# -*- coding: utf-8 -*-
"""vfp_toolchain.runtime - offline runtime dependency closure (Phase 2).

Transport-neutral, PURE_READ: lock manifest handling + offline verification.
No network, no install, no writes.
"""

from .dependency_manifest import (  # noqa: F401
    load_manifest,
    locked_wheels_for_python,
    verify_wheelhouse,
)
from .offline_runtime import (  # noqa: F401
    check_imports,
    expected_versions_from_manifest,
    lock_manifest_path,
    offline_runtime_status,
    verify_offline_runtime,
    wheelhouse_path,
)

__all__ = [
    "load_manifest",
    "locked_wheels_for_python",
    "verify_wheelhouse",
    "check_imports",
    "expected_versions_from_manifest",
    "lock_manifest_path",
    "offline_runtime_status",
    "verify_offline_runtime",
    "wheelhouse_path",
]
