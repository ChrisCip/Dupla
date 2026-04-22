"""
Abre en Windows el Preliminary Budget de referencia (hojas OBRA GRIS, TERMINACIONES, GENERAL, …)
y los dupla_presupuesto* copiados bajo corrida_*/excel/.

Uso: python scripts/open_nasas09_excels.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "data" / "NASAS09_Preliminary_Budget.xlsx"
CORRIDAS = REPO / "aps_integration" / "NASAS 09" / "outputs" / "corridas"


def main() -> int:
    if sys.platform != "win32":
        print("Solo Windows (os.startfile).", file=sys.stderr)
        return 1
    if BASELINE.is_file():
        print("Abriendo referencia (GENERAL = totales):", BASELINE)
        os.startfile(BASELINE)  # noqa: S606
    else:
        print("No se encontró:", BASELINE, file=sys.stderr)
    n = 0
    for p in sorted(CORRIDAS.glob("corrida_*/excel/*.xlsx")):
        if p.is_file():
            print("Abriendo generado:", p)
            os.startfile(p)  # noqa: S606
            n += 1
    if n == 0:
        print("Aún no hay Excels bajo corrida_*/excel/ (corre run_nasas09_full_local.ps1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
