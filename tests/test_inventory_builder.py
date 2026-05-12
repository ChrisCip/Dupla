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

    assert merged.floor_area_m2 == 95.0
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


def test_json_wall_defaults_infer_height_material_and_thickness_from_layer() -> None:
    cad_facts = {
        "project": "sample.json",
        "cad_facts": {
            "hatches": [],
            "blocks": [],
            "geometry_hints": [
                {"layer": "MB", "length": 20.0, "handle": "wall_g1"},
                {"layer": "MB", "length": 15.0, "handle": "wall_g2"},
            ],
        },
    }

    merged = build_level_inventory(cad_facts, None, level_id="level_01", level_name="Level 01")
    wall = merged.walls[0]

    assert wall.id == "json-wall-mb"
    assert wall.length_m == 35.0
    assert wall.height_m == 2.8
    assert wall.material_hint == "masonry"
    assert wall.thickness_m == 0.15


def test_inventory_builder_crosswalks_vision_wall_classification_onto_json_geometry() -> None:
    cad_facts = {
        "project": "sample.json",
        "cad_facts": {
            "hatches": [],
            "blocks": [],
            "geometry_hints": [
                {"layer": "MB", "length": 30.0, "handle": "wall_g1"},
                {"layer": "MB", "length": 25.0, "handle": "wall_g2"},
            ],
        },
    }

    vision_inventory = {
        "level_id": "level_01",
        "level_name": "Level 01",
        "source": "vision",
        "walls": [
            {
                "id": "muro_int_bloque6",
                "source": "vision",
                "material_hint": "masonry",
                "wall_system": "masonry_wall",
                "interior_exterior_hint": "interior",
                "thickness_m": 0.15,
                "source_refs": ["vision:wall_bloque6"],
            }
        ],
        "openings": [
            {
                "id": "vision-door-opening",
                "source": "vision",
                "wall_id": "muro_int_bloque6",
                "opening_type": "door",
                "count": 1,
                "width_m": 1.0,
                "height_m": 2.1,
                "source_refs": ["vision:door_01"],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)
    assert len(merged.walls) == 1
    wall = merged.walls[0]

    assert wall.id == "json-wall-mb"
    assert wall.source == "hybrid"
    assert wall.length_m == 55.0
    assert wall.material_hint == "masonry"
    assert wall.wall_system == "masonry_wall"
    assert wall.interior_exterior_hint == "interior"
    assert wall.thickness_m == 0.15
    assert "vision:wall_bloque6" in wall.source_refs
    assert merged.openings[0].wall_id == "json-wall-mb"


def test_inventory_builder_merges_structural_and_material_hints() -> None:
    cad_facts = {
        "project": "structural.json",
        "cad_facts": {
            "texts": [
                {"layer": "A-ROOM", "content": "Kitchen", "handle": "text_01"},
            ],
            "hatches": [
                {
                    "layer": "S-SLAB-CONC",
                    "area": 30.0,
                    "handle": "slab_h1",
                    "pattern_name": "Concrete",
                },
            ],
            "blocks": [
                {"layer": "S-COLUMN-CONC", "block_name": "Column RC", "handle": "col_b1"},
                {"layer": "S-COLUMN-CONC", "block_name": "Column RC", "handle": "col_b2"},
            ],
            "geometry_hints": [
                {
                    "layer": "S-BEAM-CONC",
                    "name": "RC Beam",
                    "length": 12.0,
                    "handle": "beam_g1",
                },
                {
                    "layer": "A-WALL-MASONRY-INT",
                    "name": "Masonry Wall Interior",
                    "length": 8.0,
                    "handle": "wall_g1",
                },
            ],
        },
    }

    vision_inventory = {
        "level_id": "level_structural",
        "level_name": "Level Structural",
        "source": "vision",
        "space_types": ["kitchen"],
        "system_notes": ["Vision suggests reinforced concrete frame."],
        "structural_notes": ["Vision detected a regular beam-column structural grid."],
        "walls": [
            {
                "id": "json-wall-a-wall-masonry-int",
                "source": "vision",
                "source_layers": ["A-WALL-MASONRY-INT"],
                "material_hint": "masonry",
                "wall_system": "masonry_wall",
                "interior_exterior_hint": "interior",
                "finish_required": True,
                "source_refs": ["vision:wall_01"],
            }
        ],
        "structural_elements": [
            {
                "id": "json-beam-s-beam-conc",
                "source": "vision",
                "element_type": "beam",
                "section_width_m": 0.25,
                "section_height_m": 0.5,
                "material_hint": "steel",
                "reinforcement_hint": "reinforced",
                "source_refs": ["vision:beam_01"],
                "evidence": ["Beam depth was inferred visually from elevation graphics."],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)

    assert merged.space_types == ["kitchen"]
    assert "Vision suggests reinforced concrete frame." in merged.system_notes
    assert any("Explicit structural CAD hints detected" in note for note in merged.structural_notes)
    assert merged.walls[0].material_hint == "masonry"
    assert merged.walls[0].wall_system == "masonry_wall"
    assert merged.walls[0].interior_exterior_hint == "interior"
    assert merged.walls[0].finish_required is True

    beam = next(element for element in merged.structural_elements if element.element_type == "beam")
    slab = next(element for element in merged.structural_elements if element.element_type == "slab")
    column = next(element for element in merged.structural_elements if element.element_type == "column")

    assert beam.length_m == 12.0
    assert beam.section_width_m == 0.25
    assert beam.section_height_m == 0.5
    assert beam.material_hint == "concrete"
    assert any("material_hint" in note for note in beam.conflict_notes)
    assert beam.reinforcement_hint == "reinforced"
    assert "vision:beam_01" in beam.source_refs
    assert any("Beam depth was inferred visually" in item for item in beam.evidence)
    assert slab.area_m2 == 30.0
    assert slab.material_hint == "concrete"
    assert column.count == 2
