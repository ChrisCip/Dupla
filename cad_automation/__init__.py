"""Compatibilidad para exponer el paquete CAD principal desde la raiz.

El codigo fuente historico vive en ``_legacy/cad_automation``. Este
``__init__`` extiende el path del paquete para que los imports
``cad_automation.*`` sigan funcionando sin mover todo el arbol.
"""

from pathlib import Path

__version__ = "0.1.0"
__author__ = "Dupla Engineering"

_PKG_DIR = Path(__file__).resolve().parent
_LEGACY_DIR = _PKG_DIR.parent / "_legacy" / "cad_automation"

if _LEGACY_DIR.is_dir():
    __path__.append(str(_LEGACY_DIR))
