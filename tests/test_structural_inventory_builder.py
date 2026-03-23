from core.inventory_builder import build_level_inventory


def test_structural_inventory_builder_merges_json_explicit_values_with_vision_semantics() -> None:
    cad_facts = {
        "project": "structural-merge.json",
        "cad_facts": {
            "texts": [
                {"layer": "A-ROOM", "content": "Kitchen", "handle": "txt_01"},
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
            "blocks": [
                {"layer": "S-COLUMN-CONC", "block_name": "Column RC", "handle": "col_b1"},
                {"layer": "S-COLUMN-CONC", "block_name": "Column RC", "handle": "col_b2"},
            ],
            "hatches": [
                {
                    "layer": "S-SLAB-CONC",
                    "area": 30.0,
                    "pattern_name": "Concrete",
                    "handle": "slab_h1",
                }
            ],
        },
    }

    vision_inventory = {
        "level_id": "level_structural_merge",
        "level_name": "Level Structural Merge",
        "source": "vision",
        "space_types": ["kitchen"],
        "system_notes": ["Vision suggests a reinforced concrete frame."],
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
                "structural": True,
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
                "load_bearing": True,
                "host_level": "level_structural_merge",
                "adjacent_elements": ["json-column-s-column-conc"],
                "source_refs": ["vision:beam_01"],
                "evidence": ["Vision inferred beam depth from elevation graphics."],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)
    beam = next(element for element in merged.structural_elements if element.element_type == "beam")
    wall = merged.walls[0]
    slab = next(element for element in merged.structural_elements if element.element_type == "slab")
    column = next(element for element in merged.structural_elements if element.element_type == "column")

    assert merged.source == "hybrid"
    assert merged.space_types == ["kitchen"]
    assert "Vision suggests a reinforced concrete frame." in merged.system_notes
    assert any("Explicit structural CAD hints detected" in note for note in merged.structural_notes)

    assert wall.material_hint == "masonry"
    assert wall.wall_system == "masonry_wall"
    assert wall.interior_exterior_hint == "interior"
    assert wall.finish_required is True
    assert wall.structural is True

    assert beam.length_m == 12.0
    assert beam.section_width_m == 0.25
    assert beam.section_height_m == 0.5
    assert beam.material_hint == "concrete"
    assert beam.reinforcement_hint == "reinforced"
    assert beam.load_bearing is True
    assert beam.host_level == "level_structural_merge"
    assert beam.adjacent_elements == ["json-column-s-column-conc"]
    assert "vision:beam_01" in beam.source_refs
    assert any("material_hint" in note for note in beam.conflict_notes)
    assert any("Vision inferred beam depth" in item for item in beam.evidence)

    assert slab.area_m2 == 30.0
    assert slab.material_hint == "concrete"
    assert column.count == 2


def test_structural_inventory_builder_uses_vision_hints_when_json_is_not_explicit() -> None:
    cad_facts = {
        "project": "structural-semantic-gap.json",
        "cad_facts": {
            "geometry_hints": [
                {
                    "layer": "S-BEAM",
                    "name": "Beam",
                    "length": 9.0,
                    "handle": "beam_g1",
                }
            ],
            "blocks": [],
            "hatches": [],
            "texts": [],
        },
    }

    vision_inventory = {
        "level_id": "level_semantic_gap",
        "level_name": "Level Semantic Gap",
        "source": "vision",
        "structural_elements": [
            {
                "id": "json-beam-s-beam",
                "source": "vision",
                "element_type": "beam",
                "material_hint": "steel",
                "load_bearing": True,
                "orientation": "horizontal",
                "section_width_m": 0.20,
                "section_height_m": 0.40,
                "source_refs": ["vision:beam_steel_01"],
            }
        ],
    }

    merged = build_level_inventory(cad_facts, vision_inventory)
    beam = merged.structural_elements[0]

    assert beam.length_m == 9.0
    assert beam.material_hint == "steel"
    assert beam.load_bearing is True
    assert beam.orientation == "horizontal"
    assert beam.section_width_m == 0.20
    assert beam.section_height_m == 0.40
    assert "vision:beam_steel_01" in beam.source_refs
    assert not any("material_hint" in note for note in beam.conflict_notes)
