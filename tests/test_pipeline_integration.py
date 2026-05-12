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


def test_hybrid_pipeline_distributes_project_wide_json_geometry_across_levels() -> None:
    cad_facts = {
        "project": "sample.json",
        "cad_facts": {
            "hatches": [],
            "blocks": [],
            "geometry_hints": [
                {"layer": "A-WALL", "length": 30.0, "handle": "wall_g1"},
                {"layer": "A-WALL", "length": 30.0, "handle": "wall_g2"},
                {"layer": "A-WALL", "length": 30.0, "handle": "wall_g3"},
            ],
        },
    }
    vision_payloads = [
        {"level_id": "level_01", "level_name": "Level 01", "source": "vision"},
        {"level_id": "level_02", "level_name": "Level 02", "source": "vision"},
        {"level_id": "level_03", "level_name": "Level 03", "source": "vision"},
    ]

    hybrid_inventory, takeoffs = build_takeoffs_from_sources(cad_facts, vision_payloads)

    assert [level.walls[0].length_m for level in hybrid_inventory] == [30.0, 30.0, 30.0]
    assert sum(level.walls[0].length_m for level in hybrid_inventory) == 90.0
    assert all(
        level.walls[0].inputs["json_geometry_scope"] == "project_total_distributed"
        for level in hybrid_inventory
    )

    wall_lengths = [
        takeoff.quantity
        for takeoff in takeoffs
        if takeoff.item_key == "json-wall-a-wall:length"
    ]
    assert wall_lengths == [30.0, 30.0, 30.0]
    assert sum(wall_lengths) == 90.0
