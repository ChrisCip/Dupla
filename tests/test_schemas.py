import pytest

from core.schemas import Door, LevelInventory, QuantityTrace, level_inventory_from_dict


def test_invalid_inventory_source_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Door(id="door_invalid", source="legacy")  # type: ignore[arg-type]


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
    with pytest.raises(ValueError):
        QuantityTrace(source_entity_sources=["json", "bad"])  # type: ignore[list-item]
