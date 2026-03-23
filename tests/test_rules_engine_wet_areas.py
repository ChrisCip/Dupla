from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, WetArea
from rules_engine import default_rules_engine


def test_rules_engine_expands_wet_area_surface_items_deterministically() -> None:
    level = LevelInventory(
        level_id="level_20",
        level_name="Level 20",
        wet_areas=[
            WetArea(
                id="wet_20",
                source="vision",
                kind="bathroom",
                estimated_area_m2=12.0,
                source_refs=["vision:wet_20"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wet_area_takeoff = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wet_area_area")
    assert wet_area_takeoff.inputs["context_tags"] == ["wet_area", "bathroom", "area"]
    assert wet_area_takeoff.trace.metadata["context_tags"] == ["wet_area", "bathroom", "area"]
    expanded = default_rules_engine().apply(base_takeoffs)

    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wet_area_takeoff.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert derived_by_type["wet_area_waterproofing"].quantity == 12.0
    assert derived_by_type["wet_area_finish"].quantity == 12.0
    assert derived_by_type["wet_area_waterproofing"].inputs["context_tags"] == [
        "wet_area",
        "bathroom",
        "area",
        "waterproofing",
    ]
    assert derived_by_type["wet_area_waterproofing"].trace.metadata["derivation_rule_id"] == "wet_area_surface_standard"
    assert derived_by_type["wet_area_finish"].source_refs == wet_area_takeoff.source_refs
