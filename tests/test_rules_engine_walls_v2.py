from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, Wall
from rules_engine import default_rules_engine


def test_rules_engine_expands_interior_dry_wall_finishes_with_traceability() -> None:
    level = LevelInventory(
        level_id="level_wall_v2",
        level_name="Wall V2",
        walls=[
            Wall(
                id="wall_dry_interior",
                source="hybrid",
                length_m=6.0,
                height_m=2.5,
                material_hint="block",
                assumptions=["Wall measured from normalized inventory."],
                inputs={"context_tags": ["interior", "dry_area"]},
                source_refs=["geometry:wall_dry_interior"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wall_net = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wall_net_area")
    assert wall_net.inputs["context_tags"] == ["wall", "net_area", "interior", "dry_area"]

    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wall_net.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert derived_by_type["wall_finish_plaster"].quantity == 30.0
    assert derived_by_type["wall_finish_paint"].quantity == 30.0
    assert derived_by_type["wall_finish_plaster"].trace.metadata["derivation_rule_id"] == "wall_finish_interior_dry_standard"
    assert derived_by_type["wall_finish_plaster"].trace.metadata["derivation_strategy"] == "conditional_faces"
    assert derived_by_type["wall_finish_plaster"].trace.metadata["priority"] == 40
    assert derived_by_type["wall_finish_plaster"].trace.metadata["resolved_faces"] == 2
    assert derived_by_type["wall_finish_plaster"].inputs["context_tags"] == [
        "wall",
        "net_area",
        "interior",
        "dry_area",
        "finish",
        "plaster",
    ]
    assert "Wall measured from normalized inventory." in derived_by_type["wall_finish_plaster"].assumptions
    assert any(
        "Interior dry wall rule assumes" in note
        for note in derived_by_type["wall_finish_plaster"].assumptions
    )


def test_rules_engine_uses_one_face_for_generic_exterior_wall_finish() -> None:
    level = LevelInventory(
        level_id="level_wall_exterior",
        level_name="Wall Exterior",
        walls=[
            Wall(
                id="wall_exterior",
                source="hybrid",
                length_m=5.0,
                height_m=2.0,
                material_hint="block",
                inputs={"context_tags": ["exterior"]},
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    wall_net = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "wall_net_area")
    expanded = default_rules_engine().apply(base_takeoffs)
    plaster = next(
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == wall_net.item_key
        and takeoff.item_type == "wall_finish_plaster"
    )

    assert plaster.quantity == 10.0
    assert plaster.trace.metadata["derivation_rule_id"] == "wall_finish_standard"
    assert plaster.trace.metadata["resolved_faces"] == 1
    assert plaster.trace.metadata["face_selector_tag"] == "exterior"
