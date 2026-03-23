from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, Wall
from rules_engine import default_rules_engine


def test_rules_engine_expands_wall_net_area_into_finish_takeoffs() -> None:
    level = LevelInventory(
        level_id="level_10",
        level_name="Level 10",
        walls=[
            Wall(
                id="wall_10",
                source="hybrid",
                length_m=5.0,
                height_m=2.0,
                material_hint="block",
                source_refs=["geometry:wall_10"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wall_net = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wall_net_area")

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wall_net.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert derived_by_type["wall_finish_plaster"].quantity == 20.0
    assert derived_by_type["wall_finish_paint"].quantity == 20.0
    assert all(
        takeoff.trace.metadata["derivation_rule_id"] == "wall_finish_standard"
        for takeoff in derived
    )
    assert all(takeoff.source_refs == wall_net.source_refs for takeoff in derived)
    assert any(
        "both exposed wall faces" in note
        for note in derived_by_type["wall_finish_plaster"].assumptions
    )
    assert len([takeoff.item_key for takeoff in expanded]) == len(
        {takeoff.item_key for takeoff in expanded}
    )
