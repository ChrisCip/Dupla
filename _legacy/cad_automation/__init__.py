"""
CAD Automation System
====================
Automatizacion de archivos CAD: separacion de disciplinas,
normalizacion de unidades y separacion de planos.

Soporta: DXF (nativo), DWG (via ODA File Converter)
"""

from pathlib import Path

__version__ = "0.1.0"
__author__ = "Dupla Engineering"

_PKG_DIR = Path(__file__).resolve().parent
_ROOT_COMPAT_DIR = _PKG_DIR.parent.parent / "cad_automation"

if _ROOT_COMPAT_DIR.is_dir():
    __path__.append(str(_ROOT_COMPAT_DIR))
