from agents.quantifier_agent import quantify_inventory
from core.schemas import Door, LevelInventory, Window
from rules_engine import default_rules_engine


def test_rules_engine_expands_door_and_window_takeoffs_without_duplicates() -> None:
    level = LevelInventory(
        level_id="level_30",
        level_name="Level 30",
        doors=[
            Door(
                id="door_30",
                source="hybrid",
                count=3,
                material_hint="wood",
                source_refs=["vision:door_30"],
            )
        ],
        windows=[
            Window(
                id="window_30",
                source="hybrid",
                count=4,
                width_m=1.5,
                height_m=1.0,
                source_refs=["vision:window_30"],
            )
        ],
    )

    base_takeoffs = quantify_inventory([level])
    expanded = default_rules_engine().apply(base_takeoffs)
    expanded_by_type = {takeoff.item_type: takeoff for takeoff in expanded}

    assert expanded_by_type["door_frame_count"].quantity == 3.0
    assert expanded_by_type["door_hardware_set"].quantity == 3.0
    assert expanded_by_type["window_installation_count"].quantity == 4.0
    assert expanded_by_type["window_sealant_area"].quantity == 6.0
    assert len([takeoff.item_key for takeoff in expanded]) == len(
        {takeoff.item_key for takeoff in expanded}
    )
