from core.inventory_builder import build_level_inventory


def test_inventory_builder_prefers_json_and_preserves_conflicts() -> None:
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

    vision_inventory = {
        "level_id": "level_01",
        "level_name": "Level 01",
        "source": "vision",
        "floor_area_m2": 95.0,
        "walls": [
            {
                "id": "json-wall-a-wall",
                "length_m": 9.0,
                "height_m": 3.0,
                "source": "vision",
                "source_layers": ["A-WALL"],
                "source_refs": ["vision:wall_01"],
            }
        ],
        "doors": [
            {
                "id": "json-door-1",
                "count": 1,
                "height_m": 2.1,
                "source": "vision",
                "source_layers": ["A-DOOR"],
                "source_refs": ["vision:door_01"],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)

    assert merged.floor_area_m2 == 100.0
    assert any("floor_area_m2" in note for note in merged.conflict_notes)
    assert merged.walls[0].length_m == 10.0
    assert merged.walls[0].height_m == 3.0
    assert any("length_m" in note for note in merged.walls[0].conflict_notes)
    assert merged.walls[0].source == "hybrid"
    assert merged.doors[0].count == 2
    assert merged.doors[0].height_m == 2.1
    assert merged.doors[0].source == "hybrid"


def test_inventory_builder_uses_vision_when_json_is_incomplete() -> None:
    cad_facts = {
        "project": "sample.json",
        "cad_facts": {
            "hatches": [],
            "blocks": [],
            "geometry_hints": [
                {"layer": "A-WALL", "length": 8.0, "handle": "wall_g1"},
            ],
        },
    }

    vision_inventory = {
        "level_id": "level_02",
        "level_name": "Level 02",
        "source": "vision",
        "walls": [
            {
                "id": "json-wall-a-wall",
                "height_m": 2.8,
                "source": "vision",
                "source_layers": ["A-WALL"],
                "source_refs": ["vision:wall_02"],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)

    assert merged.walls[0].length_m == 8.0
    assert merged.walls[0].height_m == 2.8
    assert "vision:wall_02" in merged.walls[0].source_refs
