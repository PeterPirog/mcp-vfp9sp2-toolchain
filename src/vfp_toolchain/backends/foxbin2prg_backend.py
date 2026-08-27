# -*- coding: utf-8 -*-
"""
backends/foxbin2prg_backend.py - adapter for the FoxBin2Prg dependency.

FoxBin2Prg is an EXTERNAL_CONFIGURED dependency: the runtime source is NOT
vendored in this repository (see THANKS.md and tools/VENDORED_DEPENDENCIES.json).
Resolution follows the existing contract (vfp_common.foxbin2prg_program):
  1. VFP_FOXBIN2PRG_DIR environment variable
  2. config.json -> foxbin2prg (directoryDefault)

The backend wraps the existing resolution logic; it does not re-implement
the BIN2PRG conversion pipeline. Importing this module launches nothing.
"""

import os

from .. import config
from ..capabilities import BACKEND_FOXBIN2PRG

UPSTREAM = "https://github.com/fdbozzo/foxbin2prg"
SOURCE_DIRECTION = "BIN2PRG_ONLY"  # config.json contract; PRG2BIN forbidden


class FoxBin2PrgBackend(object):
    """Configuration/provenance adapter for FoxBin2Prg (EXTERNAL_CONFIGURED)."""

    name = "foxbin2prg"
    backend = BACKEND_FOXBIN2PRG

    def __init__(self, root=None):
        # root: optional repository-root override (tests / per-project later).
        self._root = root

    def configured_path(self):
        """Resolved foxbin2prg.prg path per the existing contract."""
        return config.foxbin2prg_program(self._root)

    def program_exists(self):
        return os.path.isfile(self.configured_path())

    def available(self):
        """FoxBin2Prg is available only when VFP9 + the program file both exist.

        Capability discovery is deliberately cheap: it does NOT launch VFP.
        The authoritative version check stays in vfp_driver `verno`.
        """
        from .vfp9_backend import VFP9Backend
        vfp9 = VFP9Backend(root=self._root)
        return self.program_exists() and vfp9.executable_exists()

    def status(self):
        """Read-only provenance/availability report (no VFP launch)."""
        path = self.configured_path()
        meta = {
            "configured": True,
            "path": path,
            "programExists": os.path.isfile(path),
            "vendored": False,  # runtime source is NOT in this repository
            "mode": "EXTERNAL_CONFIGURED",
            "upstream": UPSTREAM,
            "sourceDirection": SOURCE_DIRECTION,
            "vfpRequired": True,
        }
        return meta


__all__ = ["FoxBin2PrgBackend", "UPSTREAM", "SOURCE_DIRECTION"]
