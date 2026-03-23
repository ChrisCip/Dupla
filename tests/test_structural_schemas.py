from core.schemas import level_inventory_from_dict


def test_structural_schema_validation_supports_richer_inventory_fields() -> None:
    level = level_inventory_from_dict(
        {
            "level_id": "level_structural_schema",
            "level_name": "Level Structural Schema",
            "source": "vision",
            "space_types": ["kitchen", "bathroom"],
            "system_notes": ["Probable reinforced concrete frame with masonry infill."],
            "structural_notes": ["Beam-column grid inferred from repeated bays."],
            "confidence": 0.81,
            "walls": [
                {
                    "id": "wall_lb_01",
                    "material_hint": "masonry",
                    "wall_system": "masonry_wall",
                    "interior_exterior_hint": "interior",
                    "finish_required": True,
                    "structural": True,
                    "confidence": 0.74,
                }
            ],
            "structural_elements": [
                {
                    "id": "beam_01",
                    "element_type": "beam",
                    "count": 2,
                    "span_m": 5.5,
                    "section_width_m": 0.25,
                    "section_height_m": 0.45,
                    "orientation": "horizontal",
                    "load_bearing": True,
                    "material_hint": "concrete",
                    "reinforcement_hint": "reinforced",
                    "concrete_grade_hint": "H25",
                    "steel_grade_hint": "FY420",
                    "host_level": "level_structural_schema",
                    "adjacent_elements": ["column_a", "column_b"],
                    "confidence": 0.69,
                    "assumptions": [
                        "Beam section depth was inferred from elevation graphics."
                    ],
                }
            ],
        },
        default_source="vision",
    )

    wall = level.walls[0]
    beam = level.structural_elements[0]

    assert level.source == "vision"
    assert level.space_types == ["kitchen", "bathroom"]
    assert level.system_notes == ["Probable reinforced concrete frame with masonry infill."]
    assert level.structural_notes == ["Beam-column grid inferred from repeated bays."]
    assert level.confidence == 0.81

    assert wall.wall_system == "masonry_wall"
    assert wall.interior_exterior_hint == "interior"
    assert wall.finish_required is True
    assert wall.structural is True
    assert wall.confidence == 0.74

    assert beam.span_m == 5.5
    assert beam.section_width_m == 0.25
    assert beam.section_height_m == 0.45
    assert beam.orientation == "horizontal"
    assert beam.load_bearing is True
    assert beam.material_hint == "concrete"
    assert beam.reinforcement_hint == "reinforced"
    assert beam.concrete_grade_hint == "H25"
    assert beam.steel_grade_hint == "FY420"
    assert beam.host_level == "level_structural_schema"
    assert beam.adjacent_elements == ["column_a", "column_b"]
    assert beam.assumptions == ["Beam section depth was inferred from elevation graphics."]
    assert beam.confidence == 0.69
