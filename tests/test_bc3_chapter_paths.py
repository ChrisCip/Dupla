from pathlib import Path

from budget.chapter_rules import chapter_path_from_bc3_catalog
from budget.composer import compose_budget_rows
from core.schemas import BudgetCandidate, ProjectContext, QuantityTakeoff, QuantityTrace
from processors.bc3_parser import parse_bc3


def test_chapter_path_from_bc3_catalog_follows_decomposition_chain() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    catalog = parse_bc3(str(data_dir / "TGIU.bc3"))
    path = chapter_path_from_bc3_catalog(catalog, "A.0073")
    assert path is not None
    codes = [seg.code for seg in path]
    assert "A.024ASA04" in codes
    titles = [seg.title for seg in path]
    assert any("APARATOS SANITARIOS" in t.upper() for t in titles)


def test_compose_budget_rows_respects_use_bc3_catalog_chapters_flag() -> None:
    bc3_path = Path(__file__).resolve().parents[1] / "data" / "TGIU.bc3"
    catalog = parse_bc3(str(bc3_path))

    context = ProjectContext(
        project_id="p1",
        project_name="BC3 path test",
        metadata={"use_bc3_catalog_chapters": True},
    )
    takeoff = QuantityTakeoff(
        item_key="fixture-1:count",
        item_type="fixture_count",
        level_id="L1",
        unit="ud",
        quantity=7.0,
        formula="n",
        inputs={"discipline": "plumbing"},
        trace=QuantityTrace(source_entity_ids=[], source_entity_sources=[], metadata={}),
    )
    candidates = {
        takeoff.item_key: [
            BudgetCandidate(
                takeoff_key=takeoff.item_key,
                bc3_code="A.0073",
                summary="Lavamanos vitrificado",
                unit="ud",
                score=0.9,
                rationale="{}",
            )
        ]
    }

    _, lines, _ = compose_budget_rows(
        context, [takeoff], candidates, bc3_catalog=catalog
    )
    assert len(lines) == 1
    meta = lines[0].metadata
    assert "A.024ASA04" in meta.get("chapter_codes", [])
