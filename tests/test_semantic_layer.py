from core.quality_engine import evaluate_semantic_quality
from core.schemas import LevelInventory, Wall
from core.semantic_adapter import adapt_semantic_to_inventory
from core.semantic_enrichment import enrich_architecture_semantics


def test_semantic_quality_blocks_elements_without_space_assignment() -> None:
    level = LevelInventory(
        level_id="level_01",
        level_name="Nivel 1",
        source="hybrid",
        walls=[
            Wall(
                id="wall_01",
                source="hybrid",
                level_id="level_01",
                length_m=10.0,
                height_m=2.8,
                source_refs=[],
            )
        ],
    )

    building = enrich_architecture_semantics(
        project_id="p1",
        project_name="demo",
        levels=[level],
    )
    report = evaluate_semantic_quality(building)

    assert report.total_elements == 1
    assert report.blocked_count == 1
    assert report.blocked_items[0].element_id == "wall_01"
    assert report.blocked_items[0].code == "missing_space"


def test_semantic_adapter_filters_blocked_entities_from_quant_inventory() -> None:
    level = LevelInventory(
        level_id="level_01",
        level_name="Nivel 1",
        source="hybrid",
        walls=[
            Wall(
                id="wall_01",
                source="hybrid",
                level_id="level_01",
                length_m=10.0,
                height_m=2.8,
                source_refs=[],
            ),
            Wall(
                id="wall_02",
                source="hybrid",
                level_id="level_01",
                length_m=8.0,
                height_m=2.8,
                source_refs=["vision:kitchen"],
            ),
        ],
    )

    building = enrich_architecture_semantics(
        project_id="p1",
        project_name="demo",
        levels=[level],
    )
    report = evaluate_semantic_quality(building)
    filtered_levels = adapt_semantic_to_inventory(building, report, [level])

    assert len(filtered_levels) == 1
    remaining_ids = {wall.id for wall in filtered_levels[0].walls}
    assert "wall_01" not in remaining_ids
    assert "wall_02" in remaining_ids
