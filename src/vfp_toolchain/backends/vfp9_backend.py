# -*- coding: utf-8 -*-
"""
backends/vfp9_backend.py - adapter for the VFP9 SP2 runtime (authoritative).

VFP9 SP2 is the authoritative backend for exact VFP behavior (FoxBin2Prg,
runtime introspection, SYS(3054), COMPILE/BUILD, REINDEX). This PR only
exposes cheap availability checks:

    configured()                config.json + env are consulted
    executable_exists()         VFP9_EXE / config.vfp.exeDefault on disk
    enhanced_backend_available() executable + FoxBin2Prg program present

It deliberately does NOT launch VFP, open COM or run verno: capability
discovery (vfp_capabilities) must stay a fast PURE_READ probe. The runtime
version verification (build 5815 / 7423) happens later via the existing
`verno`/`env` operations.
"""

import os

from .. import config
from ..capabilities import BACKEND_VFP9_RUNTIME

# Authoritative VFP9 SP2 build baselines (offline knowledge, README/THANKS):
KNOWN_BUILD_BASELINES = ("9.0.0.5815", "9.0.0.7423")


class VFP9Backend(object):
    """Cheap availability adapter for the installed VFP9 SP2 (no launch)."""

    name = "vfp9"
    backend = BACKEND_VFP9_RUNTIME

    def __init__(self, root=None):
        # root: optional repository-root override (tests / per-project later).
        self._root = root

    def configured(self):
        """True when a VFP9 executable path is resolvable from config/env."""
        try:
            return bool(config.vfp_exe_candidate(self._root))
        except Exception:
            return False

    def executable_exists(self):
        """True when the configured vfp9.exe exists on disk."""
        path = config.vfp_exe_candidate(self._root)
        return bool(path) and os.path.isfile(path)

    def enhanced_backend_available(self):
        """VFP9-enhanced operations available only when VFP + FoxBin2Prg exist."""
        if not self.executable_exists():
            return False
        try:
            from .foxbin2prg_backend import FoxBin2PrgBackend
            return FoxBin2PrgBackend(root=self._root).program_exists()
        except Exception:
            return False

    def status(self):
        """Read-only availability report (does not launch VFP)."""
        exe = config.vfp_exe_candidate(self._root)
        exists = self.executable_exists()
        return {
            "configured": self.configured(),
            "executablePath": exe,
            "executableExists": exists,
            "versionVerified": False,  # deferred to vfp_driver `verno`/`env`
            "knownBuildBaselines": list(KNOWN_BUILD_BASELINES),
            "vfpRequired": True,
        }


__all__ = ["VFP9Backend", "KNOWN_BUILD_BASELINES"]
