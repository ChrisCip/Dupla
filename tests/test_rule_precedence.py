from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, Wall
from rules_engine import default_rules_engine


def test_wet_area_wall_rule_overrides_generic_wall_finish_rule() -> None:
    level = LevelInventory(
        level_id="level_rule_precedence",
        level_name="Rule Precedence",
        walls=[
            Wall(
                id="wall_wet_override",
                source="hybrid",
                length_m=4.0,
                height_m=2.5,
                material_hint="block",
                inputs={"context_tags": ["interior", "wet_area"]},
                source_refs=["geometry:wall_wet_override"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wall_net = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wall_net_area")
    assert wall_net.inputs["context_tags"] == ["wall", "net_area", "interior", "wet_area"]

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wall_net.item_key
    ]

    derived_types = {takeoff.item_type for takeoff in derived}
    assert derived_types == {"wall_waterproofing", "wall_finish_tile"}
    assert len(derived) == 2

    waterproofing = next(takeoff for takeoff in derived if takeoff.item_type == "wall_waterproofing")
    assert waterproofing.quantity == 10.0
    assert waterproofing.trace.metadata["derivation_rule_id"] == "wall_finish_wet_area_standard"
    assert waterproofing.trace.metadata["derivation_strategy"] == "conditional_faces"
    assert waterproofing.trace.metadata["priority"] == 60
    assert waterproofing.trace.metadata["resolved_faces"] == 1
    assert waterproofing.trace.metadata["inherited_context_tags"] == [
        "wall",
        "net_area",
        "interior",
        "wet_area",
    ]
