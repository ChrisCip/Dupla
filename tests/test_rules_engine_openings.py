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
    door_count = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "door_count")
    window_count = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "window_count")
    window_area = next(takeoff for takeoff in base_takeoffs if takeoff.item_type == "window_area")
    assert door_count.inputs["context_tags"] == ["door"]
    assert window_count.inputs["context_tags"] == ["window"]
    assert window_area.inputs["context_tags"] == ["window", "area"]
    expanded = default_rules_engine().apply(base_takeoffs)
    expanded_by_type = {takeoff.item_type: takeoff for takeoff in expanded}

    assert expanded_by_type["door_frame_count"].quantity == 3.0
    assert expanded_by_type["door_hardware_set"].quantity == 3.0
    assert expanded_by_type["window_installation_count"].quantity == 4.0
    assert expanded_by_type["window_sealant_area"].quantity == 6.0
    assert expanded_by_type["door_frame_count"].trace.metadata["context_tags"] == [
        "door",
        "frame",
    ]
    assert expanded_by_type["window_sealant_area"].inputs["context_tags"] == [
        "window",
        "area",
        "sealant",
    ]
    assert len([takeoff.item_key for takeoff in expanded]) == len(
        {takeoff.item_key for takeoff in expanded}
    )
