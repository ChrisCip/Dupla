from pathlib import Path

import pytest

from analysis.detail_inventory import DetailReport, MissingElement
from budget.composer import compose_budget
from core.schemas import BudgetCandidate, ProjectContext, QuantityTakeoff, QuantityTrace
from validation.budget_validator import (
    detect_cross_discipline_duplicates,
    load_discipline_rules,
    run_budget_validation,
    validate_discipline_assignment,
    validate_pricing,
    validate_quantities,
)


def test_load_discipline_rules() -> None:
    rules = load_discipline_rules()
    assert "discipline_to_chapters" in rules
    assert "06" in rules["discipline_to_chapters"]["electrica"]


def test_v1_rejects_electric_line_under_terminaciones() -> None:
    rules = load_discipline_rules()
    issues = validate_discipline_assignment(
        partida={"takeoff_key": "x", "summary": "Tomacorriente"},
        chapter_prefix="04",
        source_discipline="electrica",
        rules=rules,
    )
    assert any(i.code == "V1_DISCIPLINE_CHAPTER_MISMATCH" for i in issues)


def test_v2_duplicate_fingerprint_across_disciplines() -> None:
    issues = detect_cross_discipline_duplicates(
        {
            "arquitectonica": [
                {"takeoff_key": "wall-a:net", "metadata": {"inventory_entity_id": "WALL-A"}},
            ],
            "electrica": [
                {"takeoff_key": "other:count", "metadata": {"inventory_entity_id": "WALL-A"}},
            ],
        }
    )
    assert any(i.code == "V2_CROSS_DISCIPLINE_DUPLICATE" for i in issues)


def test_v3_missing_element_with_quantity_is_error() -> None:
    rep = DetailReport(
        discipline="estructural",
        missing_elements=[MissingElement(element_id="COL-1", kind="columna", expected_in="despiece", impact="alto")],
    )
    partidas = [
        {
            "takeoff_key": "k1",
            "quantity": 4.0,
            "metadata": {"inventory_entity_id": "COL-1"},
        }
    ]
    issues = validate_quantities(partidas, rep, takeoff_by_key={})
    assert any(i.code == "V3_QUANTITY_FOR_MISSING_ELEMENT" for i in issues)


def test_v4_sin_precio_bc3_warning() -> None:
    cat = {"concepts_by_code": {"NOPRICE": {"price": 0.0, "unit": "m2"}}}
    issues = validate_pricing(
        [{"takeoff_key": "t1", "code": "NOPRICE", "candidate_code": "NOPRICE", "unit_price": 0.0}],
        cat,
    )
    assert any(i.code == "V4_SIN_PRECIO_BC3" for i in issues)


def test_run_budget_validation_on_composed_budget(tmp_path: Path) -> None:
    bc3_path = Path(__file__).resolve().parents[1] / "data" / "GIV00001 (1).bc3"
    if not bc3_path.is_file():
        pytest.skip("GIV BC3 fixture not present")
    from processors.bc3_parser import parse_bc3

    catalog = parse_bc3(str(bc3_path))
    context = ProjectContext(
        project_id="pv",
        project_name="Validation",
        metadata={"discipline_id": "arquitectonica", "run_budget_validation": True},
    )
    takeoff = QuantityTakeoff(
        item_key="wall_01:net_area",
        item_type="wall_net_area",
        level_id="L1",
        unit="m2",
        quantity=100.0,
        formula="area",
        inputs={},
        trace=QuantityTrace(metadata={}, source_entity_ids=[], source_entity_sources=[]),
    )
    candidates = {
        takeoff.item_key: [
            BudgetCandidate(
                takeoff_key=takeoff.item_key,
                bc3_code="P0501101",
                summary="Panete",
                unit="m2",
                score=0.95,
                rationale="{}",
            )
        ]
    }
    composed = compose_budget(context, [takeoff], candidates, bc3_catalog=catalog)
    assert "budget_validation" in composed
    bv = composed["budget_validation"]
    assert "issues" in bv
    assert "stats" in bv


def test_detail_inventory_prompt_loads() -> None:
    from analysis.detail_inventory import load_discipline_prompt

    text = load_discipline_prompt("electrica")
    assert "electrica" in text.lower() or "eléctrica" in text.lower() or "tomacorriente" in text.lower()
