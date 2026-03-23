from core.schemas import Door, QuantityTrace, level_inventory_from_dict


def test_invalid_inventory_source_raises_value_error() -> None:
    try:
        Door(id="door_invalid", source="legacy")  # type: ignore[arg-type]
    except ValueError:
        pass
    else:  # pragma: no cover - defensive guard for direct execution
        raise AssertionError("Expected invalid inventory source to raise ValueError.")


def test_level_inventory_from_dict_applies_default_source_to_nested_entities() -> None:
    level = level_inventory_from_dict(
        {
            "level_id": "level_01",
            "level_name": "Level 01",
            "doors": [{"id": "door_01", "count": 2}],
            "openings": [{"id": "opening_01", "wall_id": "wall_01"}],
        },
        default_source="vision",
    )

    assert level.source == "vision"
    assert level.doors[0].source == "vision"
    assert level.openings[0].source == "vision"


def test_quantity_trace_validates_nested_sources() -> None:
    try:
        QuantityTrace(source_entity_sources=["json", "bad"])  # type: ignore[list-item]
    except ValueError:
        pass
    else:  # pragma: no cover - defensive guard for direct execution
        raise AssertionError("Expected invalid nested quantity trace source to raise ValueError.")


def test_level_inventory_from_dict_supports_structural_and_material_fields() -> None:
    level = level_inventory_from_dict(
        {
            "level_id": "level_structural",
            "level_name": "Level Structural",
            "space_types": ["kitchen", "bathroom"],
            "system_notes": ["Probable reinforced concrete frame."],
            "structural_notes": ["Grid-aligned beam pattern is visible."],
            "walls": [
                {
                    "id": "wall_structural",
                    "material_hint": "masonry",
                    "wall_system": "masonry_wall",
                    "interior_exterior_hint": "interior",
                    "finish_required": True,
                }
            ],
            "structural_elements": [
                {
                    "id": "beam_01",
                    "element_type": "beam",
                    "material_hint": "concrete",
                    "section_width_m": 0.25,
                    "section_height_m": 0.5,
                    "span_m": 6.0,
                    "orientation": "horizontal",
                    "load_bearing": True,
                    "reinforcement_hint": "reinforced",
                    "concrete_grade_hint": "H25",
                    "steel_grade_hint": "FY420",
                    "host_level": "level_structural",
                    "adjacent_elements": ["column_a", "column_b"],
                }
            ],
        },
        default_source="vision",
    )

    assert level.space_types == ["kitchen", "bathroom"]
    assert level.system_notes == ["Probable reinforced concrete frame."]
    assert level.structural_notes == ["Grid-aligned beam pattern is visible."]
    assert level.walls[0].wall_system == "masonry_wall"
    assert level.walls[0].interior_exterior_hint == "interior"
    assert level.walls[0].finish_required is True
    assert level.structural_elements[0].section_width_m == 0.25
    assert level.structural_elements[0].section_height_m == 0.5
    assert level.structural_elements[0].span_m == 6.0
    assert level.structural_elements[0].orientation == "horizontal"
    assert level.structural_elements[0].load_bearing is True
    assert level.structural_elements[0].reinforcement_hint == "reinforced"
    assert level.structural_elements[0].concrete_grade_hint == "H25"
    assert level.structural_elements[0].steel_grade_hint == "FY420"
    assert level.structural_elements[0].host_level == "level_structural"
    assert level.structural_elements[0].adjacent_elements == ["column_a", "column_b"]
