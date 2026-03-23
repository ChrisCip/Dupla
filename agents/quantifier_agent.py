"""
Deterministic inventory quantifier.

This module converts normalized inventory into traceable quantity takeoffs.
It intentionally avoids project-specific calibration tables and opaque heuristics.
"""

from __future__ import annotations

from typing import Iterable

from core.schemas import LevelInventory, QuantityTakeoff


def _wall_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for wall in level.walls:
        if wall.length_m is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{wall.id}:length",
                    source_element_type="wall",
                    level_id=level.level_id,
                    quantity=wall.length_m,
                    unit="m",
                    formula="wall.length_m",
                    trace={"wall_id": wall.id, "source_layers": wall.source_layers},
                )
            )

        if wall.area_m2 is not None:
            formula = "wall.area_m2"
            quantity = wall.area_m2
            trace = {"wall_id": wall.id, "source_layers": wall.source_layers}
        elif wall.length_m is not None and wall.height_m is not None:
            formula = "wall.length_m * wall.height_m"
            quantity = wall.length_m * wall.height_m
            trace = {
                "wall_id": wall.id,
                "length_m": wall.length_m,
                "height_m": wall.height_m,
                "source_layers": wall.source_layers,
            }
        else:
            formula = ""
            quantity = None
            trace = {}

        if formula and quantity is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{wall.id}:area",
                    source_element_type="wall",
                    level_id=level.level_id,
                    quantity=quantity,
                    unit="m2",
                    formula=formula,
                    trace=trace,
                )
            )

        if wall.length_m is not None and wall.height_m is not None and wall.thickness_m is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{wall.id}:volume",
                    source_element_type="wall",
                    level_id=level.level_id,
                    quantity=wall.length_m * wall.height_m * wall.thickness_m,
                    unit="m3",
                    formula="wall.length_m * wall.height_m * wall.thickness_m",
                    trace={
                        "wall_id": wall.id,
                        "length_m": wall.length_m,
                        "height_m": wall.height_m,
                        "thickness_m": wall.thickness_m,
                        "source_layers": wall.source_layers,
                    },
                )
            )

    return takeoffs


def _door_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        QuantityTakeoff(
            item_key=f"{door.id}:count",
            source_element_type="door",
            level_id=level.level_id,
            quantity=float(door.count),
            unit="unit",
            formula="door.count",
            trace={
                "door_id": door.id,
                "type_hint": door.type_hint,
                "material_hint": door.material_hint,
                "source_layers": door.source_layers,
            },
        )
        for door in level.doors
    ]


def _window_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for window in level.windows:
        takeoffs.append(
            QuantityTakeoff(
                item_key=f"{window.id}:count",
                source_element_type="window",
                level_id=level.level_id,
                quantity=float(window.count),
                unit="unit",
                formula="window.count",
                trace={
                    "window_id": window.id,
                    "type_hint": window.type_hint,
                    "glazing_hint": window.glazing_hint,
                    "source_layers": window.source_layers,
                },
            )
        )

        if window.width_m is not None and window.height_m is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{window.id}:area",
                    source_element_type="window",
                    level_id=level.level_id,
                    quantity=window.width_m * window.height_m * max(window.count, 1),
                    unit="m2",
                    formula="window.width_m * window.height_m * window.count",
                    trace={
                        "window_id": window.id,
                        "width_m": window.width_m,
                        "height_m": window.height_m,
                        "count": window.count,
                        "source_layers": window.source_layers,
                    },
                )
            )
    return takeoffs


def _area_group_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for wet_area in level.wet_areas:
        takeoffs.append(
            QuantityTakeoff(
                item_key=f"{wet_area.id}:count",
                source_element_type="wet_area",
                level_id=level.level_id,
                quantity=float(wet_area.count),
                unit="unit",
                formula="wet_area.count",
                trace={"wet_area_id": wet_area.id, "kind": wet_area.kind},
            )
        )
        if wet_area.estimated_area_m2 is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{wet_area.id}:area",
                    source_element_type="wet_area",
                    level_id=level.level_id,
                    quantity=wet_area.estimated_area_m2,
                    unit="m2",
                    formula="wet_area.estimated_area_m2",
                    trace={"wet_area_id": wet_area.id, "kind": wet_area.kind},
                )
            )

    for kitchen in level.kitchens:
        takeoffs.append(
            QuantityTakeoff(
                item_key=f"{kitchen.id}:count",
                source_element_type="kitchen",
                level_id=level.level_id,
                quantity=float(kitchen.count),
                unit="unit",
                formula="kitchen.count",
                trace={"kitchen_id": kitchen.id},
            )
        )
        if kitchen.estimated_area_m2 is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{kitchen.id}:area",
                    source_element_type="kitchen",
                    level_id=level.level_id,
                    quantity=kitchen.estimated_area_m2,
                    unit="m2",
                    formula="kitchen.estimated_area_m2",
                    trace={"kitchen_id": kitchen.id},
                )
            )

    return takeoffs


def _stair_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        QuantityTakeoff(
            item_key=f"{stair.id}:count",
            source_element_type="stair",
            level_id=level.level_id,
            quantity=float(stair.count),
            unit="unit",
            formula="stair.count",
            trace={"stair_id": stair.id, "flights": stair.flights},
        )
        for stair in level.stairs
    ]


def _fixture_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        QuantityTakeoff(
            item_key=f"{fixture.id}:count",
            source_element_type="fixture",
            level_id=level.level_id,
            quantity=float(fixture.count),
            unit=fixture.unit,
            formula="fixture.count",
            trace={
                "fixture_id": fixture.id,
                "fixture_type": fixture.fixture_type,
                "location_hint": fixture.location_hint,
            },
        )
        for fixture in level.fixtures
    ]


def _structural_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for element in level.structural_elements:
        takeoffs.append(
            QuantityTakeoff(
                item_key=f"{element.id}:count",
                source_element_type="structural_element",
                level_id=level.level_id,
                quantity=float(element.count),
                unit="unit",
                formula="structural_element.count",
                trace={
                    "element_id": element.id,
                    "element_type": element.element_type,
                    "material_hint": element.material_hint,
                },
            )
        )

        if element.length_m is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{element.id}:length",
                    source_element_type="structural_element",
                    level_id=level.level_id,
                    quantity=element.length_m,
                    unit="m",
                    formula="structural_element.length_m",
                    trace={"element_id": element.id, "element_type": element.element_type},
                )
            )

        if element.area_m2 is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{element.id}:area",
                    source_element_type="structural_element",
                    level_id=level.level_id,
                    quantity=element.area_m2,
                    unit="m2",
                    formula="structural_element.area_m2",
                    trace={"element_id": element.id, "element_type": element.element_type},
                )
            )

        if element.volume_m3 is not None:
            takeoffs.append(
                QuantityTakeoff(
                    item_key=f"{element.id}:volume",
                    source_element_type="structural_element",
                    level_id=level.level_id,
                    quantity=element.volume_m3,
                    unit="m3",
                    formula="structural_element.volume_m3",
                    trace={"element_id": element.id, "element_type": element.element_type},
                )
            )

    return takeoffs


def quantify_inventory(levels: Iterable[LevelInventory]) -> list[QuantityTakeoff]:
    """
    Convert normalized inventory into deterministic quantities.

    TODO: Expand to net/gross quantity handling once opening subtraction and
    multi-level aggregation rules are fully defined.
    """
    takeoffs: list[QuantityTakeoff] = []

    for level in levels:
        takeoffs.extend(_wall_takeoffs(level))
        takeoffs.extend(_door_takeoffs(level))
        takeoffs.extend(_window_takeoffs(level))
        takeoffs.extend(_area_group_takeoffs(level))
        takeoffs.extend(_stair_takeoffs(level))
        takeoffs.extend(_fixture_takeoffs(level))
        takeoffs.extend(_structural_takeoffs(level))

    return takeoffs
