"""Ensure ``api/lib`` domain packages are importable (``core``, ``agents``, …)."""

from __future__ import annotations

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "lib"
_lib_str = str(_LIB)
if _lib_str not in sys.path:
    sys.path.insert(0, _lib_str)
