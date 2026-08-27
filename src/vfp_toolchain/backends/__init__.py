# -*- coding: utf-8 -*-
"""backends - offline dependency adapters for the VFP9 SP2 Core Service.

Each backend wraps one external dependency (pure Python, dbfbridge,
DBF_Anonymizer, FoxBin2Prg, VFP9 runtime) behind a stable, side-effect-free
interface. Importing a backend module must not launch VFP, create files,
open DBF tables, run subprocesses or touch the network; actual work only
happens when an operation is invoked.
"""

from .pure_python import PurePythonBackend  # noqa: F401
from .dbfbridge_backend import DBFBridgeBackend  # noqa: F401
from .dbf_anonymizer_backend import DBFAnonymizerBackend  # noqa: F401
from .foxbin2prg_backend import FoxBin2PrgBackend  # noqa: F401
from .vfp9_backend import VFP9Backend  # noqa: F401

__all__ = [
    "PurePythonBackend",
    "DBFBridgeBackend",
    "DBFAnonymizerBackend",
    "FoxBin2PrgBackend",
    "VFP9Backend",
]
