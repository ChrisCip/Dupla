from core.pipeline import build_takeoffs_from_sources


def test_hybrid_pipeline_merges_inventory_and_quantifies_end_to_end() -> None:
    cad_facts = {
        "project": "sample.json",
        "cad_facts": {
            "hatches": [
                {"layer": "A-FLOR", "area": 100.0, "handle": "floor_h1"},
            ],
            "blocks": [
                {"layer": "A-DOOR", "block_name": "Door Single", "handle": "door_b1"},
                {"layer": "A-DOOR", "block_name": "Door Single", "handle": "door_b2"},
            ],
            "geometry_hints": [
                {"layer": "A-WALL", "length": 10.0, "handle": "wall_g1"},
            ],
        },
    }

    vision_payload = {
        "level_id": "level_01",
        "level_name": "Level 01",
        "source": "vision",
        "floor_area_m2": 95.0,
        "walls": [
            {
                "id": "json-wall-a-wall",
                "source": "vision",
                "source_layers": ["A-WALL"],
                "length_m": 9.0,
                "height_m": 3.0,
                "source_refs": ["vision:wall_01"],
            }
        ],
        "doors": [
            {
                "id": "json-door-1",
                "source": "vision",
                "source_layers": ["A-DOOR"],
                "count": 1,
                "height_m": 2.1,
                "source_refs": ["vision:door_01"],
            }
        ],
        "openings": [
            {
                "id": "json-door-1:opening",
                "source": "vision",
                "wall_id": "json-wall-a-wall",
                "opening_type": "door",
                "count": 1,
                "width_m": 1.0,
                "height_m": 2.1,
                "source_refs": ["vision:door_01"],
            }
        ],
    }

    hybrid_inventory, takeoffs = build_takeoffs_from_sources(cad_facts, [vision_payload])
    level = hybrid_inventory[0]
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert level.floor_area_m2 == 95.0
    assert any("floor_area_m2" in note for note in level.conflict_notes)
    assert level.walls[0].length_m == 10.0
    assert level.walls[0].height_m == 3.0
    assert any("length_m" in note for note in level.walls[0].conflict_notes)
    assert any("count" in note for note in level.openings[0].conflict_notes)

    assert takeoff_map["level_01:floor_area"].quantity == 95.0
    assert takeoff_map["json-wall-a-wall:net_area"].quantity == 27.9
    assert takeoff_map["json-wall-a-wall:net_area"].formula == "wall.length_m * wall.height_m - openings_area_m2"
    assert any(
        "Deducted one observed instance only" in note
        for note in takeoff_map["json-wall-a-wall:net_area"].assumptions
    )
