from agents.quantifier_agent import quantify_inventory
from core.schemas import Door, LevelInventory, Window
from rules_engine import default_rules_engine


def test_rules_engine_uses_material_specific_door_rule_without_duplicates() -> None:
    level = LevelInventory(
        level_id="level_openings_door_v2",
        level_name="Door V2",
        doors=[
            Door(
                id="door_wood_v2",
                source="hybrid",
                count=2,
                material_hint="wood",
                source_refs=["vision:door_wood_v2"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    door_count = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "door_count")
    expanded = default_rules_engine().apply(base_takeoffs)
    derived = [
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == door_count.item_key
    ]
    derived_by_type = {takeoff.item_type: takeoff for takeoff in derived}

    assert set(derived_by_type) == {
        "door_leaf_wood_count",
        "door_frame_count",
        "door_hardware_set",
    }
    assert all(takeoff.trace.metadata["derivation_rule_id"] == "door_assembly_wood" for takeoff in derived)
    assert derived_by_type["door_leaf_wood_count"].quantity == 2.0
    assert derived_by_type["door_frame_count"].quantity == 2.0
    assert derived_by_type["door_hardware_set"].quantity == 2.0
    assert derived_by_type["door_leaf_wood_count"].inputs["material_context"] == "wood"
    assert len({takeoff.item_key for takeoff in derived}) == 3


def test_rules_engine_expands_window_installation_and_sealant_v2() -> None:
    level = LevelInventory(
        level_id="level_openings_window_v2",
        level_name="Window V2",
        windows=[
            Window(
                id="window_v2",
                source="hybrid",
                count=4,
                width_m=1.5,
                height_m=1.0,
                source_refs=["vision:window_v2"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    window_count = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "window_count")
    window_area = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "window_area")
    expanded = default_rules_engine().apply(base_takeoffs)

    installation = next(
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == window_count.item_key
        and takeoff.item_type == "window_installation_count"
    )
    sealant = next(
        takeoff
        for takeoff in expanded
        if takeoff.trace.metadata.get("derived_from") == window_area.item_key
        and takeoff.item_type == "window_sealant_area"
    )

    assert installation.quantity == 4.0
    assert installation.trace.metadata["derivation_strategy"] == "count_multiplier"
    assert installation.trace.metadata["priority"] == 20
    assert sealant.quantity == 6.0
    assert sealant.trace.metadata["derivation_rule_id"] == "window_seal_standard"
    assert sealant.trace.metadata["derivation_strategy"] == "surface_multiplier"
    assert sealant.trace.metadata["inherited_context_tags"] == ["window", "area"]
