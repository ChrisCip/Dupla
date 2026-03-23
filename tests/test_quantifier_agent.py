from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, Opening, Wall


def test_quantify_inventory_generates_wall_net_floor_and_ceiling_takeoffs() -> None:
    level = LevelInventory(
        level_id="level_01",
        level_name="Level 01",
        floor_area_m2=120.0,
        ceiling_area_m2=115.0,
        walls=[
            Wall(
                id="wall_01",
                source="hybrid",
                length_m=10.0,
                height_m=3.0,
                thickness_m=0.15,
                source_layers=["A-WALL"],
                source_refs=["geometry:wall_01"],
                evidence=["Wall length measured from CAD and height confirmed visually."],
            )
        ],
        openings=[
            Opening(
                id="opening_01",
                source="vision",
                wall_id="wall_01",
                opening_type="door",
                count=1,
                width_m=1.0,
                height_m=2.0,
                source_refs=["vision:opening_01"],
            ),
            Opening(
                id="opening_02",
                source="vision",
                wall_id="wall_01",
                opening_type="window",
                count=1,
                area_m2=1.5,
                source_refs=["vision:opening_02"],
            ),
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["level_01:floor_area"].quantity == 120.0
    assert takeoff_map["level_01:floor_area"].formula == "level.floor_area_m2"
    assert takeoff_map["level_01:ceiling_area"].quantity == 115.0
    assert takeoff_map["wall_01:gross_area"].quantity == 30.0
    assert takeoff_map["wall_01:net_area"].quantity == 26.5
    assert takeoff_map["wall_01:net_area"].formula == "wall.length_m * wall.height_m - openings_area_m2"
    assert takeoff_map["wall_01:net_area"].inputs["openings_area_m2"] == 3.5
    assert "opening_01" in takeoff_map["wall_01:net_area"].trace.source_entity_ids


def test_quantify_inventory_records_assumption_when_opening_data_is_incomplete() -> None:
    level = LevelInventory(
        level_id="level_02",
        level_name="Level 02",
        walls=[
            Wall(
                id="wall_02",
                source="json",
                area_m2=24.0,
                source_refs=["hatch:wall_02"],
            )
        ],
        openings=[
            Opening(
                id="opening_unknown",
                source="vision",
                wall_id="wall_02",
                opening_type="window",
                count=1,
            )
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["wall_02:net_area"].quantity == 24.0
    assert any(
        "Incomplete opening data prevented full deduction" in note
        for note in takeoff_map["wall_02:net_area"].assumptions
    )
