from budget.composer import compose_budget, compose_budget_rows
from core.schemas import BudgetCandidate, ProjectContext, QuantityTakeoff, QuantityTrace


def _sample_takeoffs() -> tuple[ProjectContext, list[QuantityTakeoff], dict[str, list[BudgetCandidate]]]:
    context = ProjectContext(project_id="demo_budget", project_name="Demo Budget")
    takeoffs = [
        QuantityTakeoff(
            item_key="beam_01:concrete_volume",
            item_type="beam_concrete_volume",
            level_id="level_01",
            unit="m3",
            quantity=12.5,
            formula="beam.volume",
            inputs={
                "material_hint": "concrete",
                "context_tags": ["structural", "beam", "concrete", "volume"],
            },
            trace=QuantityTrace(
                source_entity_ids=["beam_01"],
                source_entity_sources=["hybrid"],
                metadata={
                    "material_hint": "concrete",
                    "context_tags": ["structural", "beam", "concrete", "volume"],
                },
            ),
        ),
        QuantityTakeoff(
            item_key="wall_01:paint",
            item_type="wall_finish_paint",
            level_id="level_01",
            unit="m2",
            quantity=30.0,
            formula="wall.finish",
            inputs={
                "context_tags": ["wall", "finish", "paint", "interior", "dry_area"],
            },
            assumptions=["Interior paint finish derived from wall net area."],
            trace=QuantityTrace(
                source_entity_ids=["wall_01"],
                source_entity_sources=["hybrid"],
                metadata={
                    "derived_from": "wall_01:net_area",
                    "context_tags": ["wall", "finish", "paint", "interior", "dry_area"],
                },
            ),
        ),
        QuantityTakeoff(
            item_key="door_01:leaf",
            item_type="door_leaf_wood_count",
            level_id="level_01",
            unit="unit",
            quantity=2.0,
            formula="door.count",
            inputs={
                "material_hint": "wood",
                "context_tags": ["door", "wood", "leaf"],
            },
            trace=QuantityTrace(
                source_entity_ids=["door_01"],
                source_entity_sources=["hybrid"],
                metadata={"context_tags": ["door", "wood", "leaf"]},
            ),
        ),
    ]
    candidates = {
        "beam_01:concrete_volume": [
            BudgetCandidate(
                takeoff_key="beam_01:concrete_volume",
                bc3_code="E300100",
                summary="Hormigon armado en vigas",
                unit="m3",
                score=0.82,
                rationale="Strong token overlap with structural concrete beam item.",
            )
        ],
        "wall_01:paint": [
            BudgetCandidate(
                takeoff_key="wall_01:paint",
                bc3_code="P500100",
                summary="Pintura latex interior",
                unit="m2",
                score=0.22,
                rationale="Weak keyword overlap only.",
            )
        ],
        "door_01:leaf": [],
    }
    return context, takeoffs, candidates


def test_budget_composer_groups_rows_and_generates_codes_and_subtotals() -> None:
    context, takeoffs, candidates = _sample_takeoffs()
    chapters, lines, rows = compose_budget_rows(context, takeoffs, candidates)

    chapter_titles = [chapter.title for chapter in chapters]
    line_by_key = {line.takeoff_key: line for line in lines}

    assert "ESTRUCTURA" in chapter_titles
    assert "HORMIGON ARMADO" in chapter_titles
    assert "TERMINACION DE SUPERFICIES" in chapter_titles
    assert "PUERTAS" in chapter_titles

    assert line_by_key["beam_01:concrete_volume"].code == "E300100"
    assert line_by_key["wall_01:paint"].code == "DUP-0001"
    assert line_by_key["door_01:leaf"].code == "DUP-0002"
    assert line_by_key["wall_01:paint"].summary == "Pintura en muros interiores"
    assert line_by_key["wall_01:paint"].summary != "wall_finish_paint"

    chapter_rows = [row for row in rows if row.row_type == "chapter"]
    detail_rows = [row for row in rows if row.row_type == "line"]
    subtotal_rows = [row for row in rows if row.row_type == "subtotal"]

    assert chapter_rows
    assert detail_rows
    assert subtotal_rows
    assert any(str(row.amount).startswith("=") for row in detail_rows)
    assert any(str(row.amount).startswith("=G") for row in chapter_rows)
    assert all(row.excel_row is not None for row in rows)


def test_budget_composer_returns_serializable_budget_payload() -> None:
    context, takeoffs, candidates = _sample_takeoffs()
    composed = compose_budget(context, takeoffs, candidates)

    assert composed["project_context"]["project_name"] == "Demo Budget"
    assert "budget_diagnostics" in composed
    assert composed["budget_diagnostics"]["takeoffs_budgetable"] >= 1
    assert composed["rows"]
    assert composed["lines"]
    assert any(row["nat"] == "Capítulo" for row in composed["rows"])
    assert any(row["nat"] == "Subtotal/Cierre de capítulo" for row in composed["rows"])
