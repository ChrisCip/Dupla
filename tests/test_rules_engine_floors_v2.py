from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, WetArea
from rules_engine import default_rules_engine


def test_rules_engine_expands_dry_floor_finishes_from_explicit_context() -> None:
    level = LevelInventory(
        level_id="level_floor_dry",
        level_name="Floor Dry",
        floor_area_m2=80.0,
        inputs={"context_tags": ["dry_area"]},
        source="hybrid",
    )

    base_takeoffs = quantify_inventory([level])
    floor_area = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "floor_area")
    assert floor_area.inputs["context_tags"] == ["floor", "area", "dry_area"]

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == floor_area.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert set(derived_by_type) == {"floor_screed", "floor_finish"}
    assert derived_by_type["floor_screed"].quantity == 80.0
    assert derived_by_type["floor_finish"].quantity == 80.0
    assert derived_by_type["floor_finish"].trace.metadata["derivation_rule_id"] == "floor_finish_dry_standard"
    assert derived_by_type["floor_finish"].trace.metadata["priority"] == 40
    assert derived_by_type["floor_finish"].trace.metadata["derivation_strategy"] == "identity"


def test_rules_engine_expands_wet_floor_and_suppresses_generic_wet_area_fallback() -> None:
    level = LevelInventory(
        level_id="level_floor_wet",
        level_name="Floor Wet",
        wet_areas=[
            WetArea(
                id="wet_floor_surface",
                source="vision",
                kind="bathroom",
                estimated_area_m2=12.0,
                inputs={"context_tags": ["floor"]},
                source_refs=["vision:wet_floor_surface"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wet_area = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wet_area_area")
    assert wet_area.inputs["context_tags"] == ["wet_area", "bathroom", "area", "floor"]

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wet_area.item_key
    ]
    derived_types = {takeoff.item_type for takeoff in derived}

    assert derived_types == {"floor_waterproofing", "floor_finish_tile"}
    assert "wet_area_waterproofing" not in derived_types
    assert "wet_area_finish" not in derived_types

    waterproofing = next(takeoff for takeoff in derived if takeoff.item_type == "floor_waterproofing")
    assert waterproofing.quantity == 12.0
    assert waterproofing.trace.metadata["derivation_rule_id"] == "floor_finish_wet_area_standard"
    assert waterproofing.trace.metadata["priority"] == 50
