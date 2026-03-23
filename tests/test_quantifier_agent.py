from agents.quantifier_agent import quantify_inventory
from core.schemas import Door, LevelInventory, Wall


def test_quantify_inventory_generates_traceable_formulas() -> None:
    level = LevelInventory(
        level_id="level_01",
        level_name="Level 01",
        walls=[
            Wall(
                id="wall_01",
                length_m=10.0,
                height_m=3.0,
                thickness_m=0.15,
                source_layers=["A-WALL"],
            )
        ],
        doors=[Door(id="door_01", count=2, source_layers=["A-DOOR"])],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["wall_01:length"].quantity == 10.0
    assert takeoff_map["wall_01:area"].quantity == 30.0
    assert takeoff_map["wall_01:area"].formula == "wall.length_m * wall.height_m"
    assert takeoff_map["wall_01:volume"].quantity == 4.5
    assert takeoff_map["door_01:count"].quantity == 2.0
