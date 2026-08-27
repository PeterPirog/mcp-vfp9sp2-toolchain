# -*- coding: utf-8 -*-
"""pytest conftest: make the repo root and src/ importable for tests."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")

for _p in (ROOT, SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)
