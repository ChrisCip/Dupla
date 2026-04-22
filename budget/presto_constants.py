"""
Contrato de layout Presto / primera hoja — alineado con `budget.export_excel` y `compare_budget`.

Cualquier export que deba importarse en Presto debe respetar estas constantes.
"""

from __future__ import annotations

# Primera fila de datos de partidas/capítulos (filas 1–3 reservadas a encabazados de plantilla).
PRESTO_FIRST_DATA_ROW: int = 4

# Orden de columnas en `export_excel.HEADERS` (mismo orden que filas de datos Presto importables).
PRESTO_HEADER_CODES: tuple[str, ...] = (
    "Código",
    "Nat",
    "Ud",
    "Resumen",
    "CanPres",
    "PrPres",
    "ImpPres",
    "Fuente Cantidad",
    "Fuente Precio",
    "BC3 Origen",
    "Método de Precio",
)


def assert_presto_header_row_matches_export() -> None:
    """Aserción barata para tests: HEADERS del export coinciden con el contrato Presto."""
    from budget.export_excel import HEADERS

    if tuple(HEADERS) != PRESTO_HEADER_CODES:
        raise AssertionError("export_excel.HEADERS desalineado con budget.presto_constants")
