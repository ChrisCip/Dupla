from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory
from rules_engine import default_rules_engine


def test_rules_engine_expands_ceiling_finishes_with_complete_traceability() -> None:
    level = LevelInventory(
        level_id="level_ceiling_v2",
        level_name="Ceiling V2",
        ceiling_area_m2=42.0,
        source="hybrid",
    )

    base_takeoffs = quantify_inventory([level])
    ceiling_area = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "ceiling_area")
    assert ceiling_area.inputs["context_tags"] == ["ceiling", "area"]

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == ceiling_area.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert derived_by_type["ceiling_finish_plaster"].quantity == 42.0
    assert derived_by_type["ceiling_finish_paint"].quantity == 42.0
    assert derived_by_type["ceiling_finish_paint"].trace.metadata["derivation_rule_id"] == "ceiling_finish_standard"
    assert derived_by_type["ceiling_finish_paint"].trace.metadata["derivation_strategy"] == "identity"
    assert derived_by_type["ceiling_finish_paint"].trace.metadata["priority"] == 20
    assert derived_by_type["ceiling_finish_paint"].trace.metadata["inherited_context_tags"] == [
        "ceiling",
        "area",
    ]
