from pathlib import Path

from budget.chapter_rules import chapter_path_from_bc3_catalog
from budget.composer import compose_budget_rows
from core.schemas import BudgetCandidate, ProjectContext, QuantityTakeoff, QuantityTrace
import pytest

from processors.bc3_parser import merge_bc3_catalogs, parse_bc3


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


def test_parse_bc3_tags_items_with_bc3_origin() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    path = data_dir / "TGIU.bc3"
    if not path.exists():
        pytest.skip("TGIU.bc3 not in data/")
    cat = parse_bc3(str(path))
    assert cat["items"]
    assert all(it.get("bc3_origin") == path.name for it in cat["items"][:20])


def test_merge_bc3_catalogs_unions_items_and_origins() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    paths = [data_dir / "TGIU.bc3", data_dir / "GIV00001 (1).bc3"]
    paths = [p for p in paths if p.exists()]
    if len(paths) < 2:
        pytest.skip("Need two BC3 fixtures under data/")
    merged = merge_bc3_catalogs(*[parse_bc3(str(p)) for p in paths])
    n_a = len(parse_bc3(str(paths[0]))["items"])
    n_b = len(parse_bc3(str(paths[1]))["items"])
    assert len(merged["items"]) == n_a + n_b
    origins = {it.get("bc3_origin") for it in merged["items"]}
    assert paths[0].name in origins and paths[1].name in origins
