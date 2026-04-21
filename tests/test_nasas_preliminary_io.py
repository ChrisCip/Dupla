from pathlib import Path

import pytest

from budget.nasas_preliminary_io import load_nasas_preliminary_budget_rows


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parent.parent
        / "aps_integration"
        / "NASAS 09"
        / "NASAS presupuesto"
        / "ACTUAL"
        / "Prelimary Budget NASAS 9-2, 17-02-2026.xlsx"
    ).is_file(),
    reason="NASAS baseline xlsx not in workspace",
)
def test_load_nasas_preliminary_rows_non_empty() -> None:
    repo = Path(__file__).resolve().parent.parent
    p = (
        repo
        / "aps_integration"
        / "NASAS 09"
        / "NASAS presupuesto"
        / "ACTUAL"
        / "Prelimary Budget NASAS 9-2, 17-02-2026.xlsx"
    )
    rows = load_nasas_preliminary_budget_rows(p)
    assert len(rows) > 50
    partidas = [r for r in rows if "partida" in str(r.get("nat", "")).lower()]
    assert partidas
