"""
Deterministic inventory quantifier.

This module converts normalized inventory into traceable quantity takeoffs.
It intentionally avoids project-specific calibration tables and opaque heuristics.
"""

from __future__ import annotations

from typing import Any, Iterable

from core.schemas import (
    Door,
    Fixture,
    Kitchen,
    LevelInventory,
    Opening,
    QuantityTakeoff,
    QuantityTrace,
    Stair,
    StructuralElement,
    Wall,
    WetArea,
    Window,
)


def _make_takeoff(
    *,
    item_key: str,
    item_type: str,
    level_id: str | None,
    unit: str,
    quantity: float,
    formula: str,
    inputs: dict[str, Any],
    assumptions: list[str],
    source_refs: list[str],
    trace: QuantityTrace,
) -> QuantityTakeoff:
    return QuantityTakeoff(
        item_key=item_key,
        item_type=item_type,
        level_id=level_id,
        unit=unit,
        quantity=quantity,
        formula=formula,
        inputs=inputs,
        assumptions=assumptions,
        source_refs=source_refs,
        trace=trace,
    )


def _trace_from_entities(
    *,
    entities: list[Any],
    steps: list[str],
    metadata: dict[str, Any] | None = None,
) -> QuantityTrace:
    return QuantityTrace(
        source_entity_ids=[entity.id for entity in entities if getattr(entity, "id", None)],
        source_entity_sources=[entity.source for entity in entities if getattr(entity, "source", None)],
        steps=steps,
        evidence=[
            evidence
            for entity in entities
            for evidence in getattr(entity, "evidence", [])
        ],
        conflict_notes=[
            note
            for entity in entities
            for note in getattr(entity, "conflict_notes", [])
        ],
        metadata=metadata or {},
    )


def _find_input_value(inputs: dict[str, Any], key: str) -> Any:
    if key in inputs:
        return inputs[key]

    for value in inputs.values():
        if isinstance(value, dict) and key in value:
            return value[key]

    return None


def _bool_input(inputs: dict[str, Any], key: str) -> bool:
    value = _find_input_value(inputs, key)
    if isinstance(value, bool):
        return value
    return bool(value)


def _int_input(inputs: dict[str, Any], key: str) -> int | None:
    value = _find_input_value(inputs, key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_aggregated_json_count(opening: Opening) -> bool:
    return _find_input_value(opening.inputs, "json_count") is not None or any(
        ref.startswith("block:") for ref in opening.source_refs
    )


def _resolve_opening_area_deduction(opening: Opening) -> dict[str, Any]:
    assumptions = list(opening.assumptions)
    metadata: dict[str, Any] = {
        "opening_id": opening.id,
        "opening_type": opening.opening_type,
        "opening_source": opening.source,
        "aggregated_count": max(opening.count, 1),
        "count_source": "json_aggregated"
        if _has_aggregated_json_count(opening) and opening.source in {"json", "hybrid"}
        else opening.source,
    }

    if opening.area_m2 is not None:
        metadata.update(
            {
                "dimension_source": opening.source,
                "deducted_instance_count": 1,
                "multiplication_policy": "explicit_opening_area",
            }
        )
        return {
            "area_m2": opening.area_m2,
            "formula": "opening.area_m2",
            "assumptions": assumptions,
            "metadata": metadata,
        }

    if opening.width_m is None or opening.height_m is None:
        metadata["multiplication_policy"] = "missing_dimensions"
        return {
            "area_m2": None,
            "formula": None,
            "assumptions": assumptions,
            "metadata": metadata,
        }

    per_instance_area = opening.width_m * opening.height_m
    aggregated_count = max(opening.count, 1)
    explicit_homogeneous = _bool_input(opening.inputs, "homogeneous_instances")
    observed_instance_count = _int_input(opening.inputs, "observed_instance_count")
    hybrid_aggregated_dimensions = (
        opening.source == "hybrid"
        and aggregated_count > 1
        and _has_aggregated_json_count(opening)
    )

    if hybrid_aggregated_dimensions and not explicit_homogeneous:
        deducted_instances = 1
        policy = "single_observed_instance_only"
        assumptions.append(
            f"Opening {opening.id} count came from aggregated JSON evidence while width/height came from vision evidence. "
            "Deducted one observed instance only and did not assume all aggregated instances share the same dimensions."
        )
        formula = "opening.width_m * opening.height_m"
    else:
        deducted_instances = aggregated_count
        policy = "count_times_size"
        formula = "opening.width_m * opening.height_m * opening.count"
        if hybrid_aggregated_dimensions and explicit_homogeneous:
            assumptions.append(
                f"Opening {opening.id} deduction used count * size because homogeneous_instances was explicitly set true."
            )
            policy = "count_times_size_with_explicit_homogeneity"

    metadata.update(
        {
            "dimension_source": "vision" if opening.source in {"vision", "hybrid"} else opening.source,
            "observed_instance_count": observed_instance_count,
            "explicit_homogeneous_instances": explicit_homogeneous,
            "deducted_instance_count": deducted_instances,
            "per_instance_area_m2": per_instance_area,
            "deducted_area_m2": per_instance_area * deducted_instances,
            "multiplication_policy": policy,
        }
    )

    return {
        "area_m2": per_instance_area * deducted_instances,
        "formula": formula,
        "assumptions": assumptions,
        "metadata": metadata,
    }


def _openings_for_wall(level: LevelInventory, wall: Wall) -> list[Opening]:
    explicit = [opening for opening in level.openings if opening.wall_id == wall.id]
    if explicit:
        return explicit

    derived: list[Opening] = []
    for door in level.doors:
        if door.wall_id == wall.id:
            derived.append(
                Opening(
                    id=f"{door.id}:derived-opening",
                    level_id=door.level_id,
                    source=door.source,
                    wall_id=door.wall_id,
                    opening_type="door",
                    count=door.count,
                    width_m=door.width_m,
                    height_m=door.height_m,
                    source_layers=list(door.source_layers),
                    source_refs=list(door.source_refs),
                    assumptions=list(door.assumptions),
                    inputs=dict(door.inputs),
                    conflict_notes=list(door.conflict_notes),
                    evidence=list(door.evidence),
                    related_door_id=door.id,
                )
            )

    for window in level.windows:
        if window.wall_id == wall.id:
            derived.append(
                Opening(
                    id=f"{window.id}:derived-opening",
                    level_id=window.level_id,
                    source=window.source,
                    wall_id=window.wall_id,
                    opening_type="window",
                    count=window.count,
                    width_m=window.width_m,
                    height_m=window.height_m,
                    source_layers=list(window.source_layers),
                    source_refs=list(window.source_refs),
                    assumptions=list(window.assumptions),
                    inputs=dict(window.inputs),
                    conflict_notes=list(window.conflict_notes),
                    evidence=list(window.evidence),
                    related_window_id=window.id,
                )
            )

    return derived


def _wall_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for wall in level.walls:
        if wall.length_m is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:length",
                    item_type="wall_length",
                    level_id=level.level_id,
                    unit="m",
                    quantity=wall.length_m,
                    formula="wall.length_m",
                    inputs={"length_m": wall.length_m},
                    assumptions=list(wall.assumptions),
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Read explicit wall length from normalized inventory."],
                    ),
                )
            )

        gross_area: float | None = None
        gross_formula = ""
        gross_inputs: dict[str, Any] = {}
        gross_assumptions = list(wall.assumptions)

        if wall.area_m2 is not None:
            gross_area = wall.area_m2
            gross_formula = "wall.area_m2"
            gross_inputs = {"area_m2": wall.area_m2}
        elif wall.length_m is not None and wall.height_m is not None:
            gross_area = wall.length_m * wall.height_m
            gross_formula = "wall.length_m * wall.height_m"
            gross_inputs = {"length_m": wall.length_m, "height_m": wall.height_m}
        elif wall.length_m is not None and wall.height_m is None:
            gross_assumptions.append(
                f"Wall {wall.id} gross/net area was not quantified because wall height is missing."
            )

        if gross_area is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:gross_area",
                    item_type="wall_gross_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=gross_area,
                    formula=gross_formula,
                    inputs=gross_inputs,
                    assumptions=gross_assumptions,
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Computed gross wall area from explicit wall data."],
                        metadata={"gross_formula": gross_formula},
                    ),
                )
            )

            linked_openings = _openings_for_wall(level, wall)
            known_openings_area = 0.0
            opening_formula_parts: list[str] = []
            opening_deductions: list[dict[str, Any]] = []
            net_assumptions = list(wall.assumptions)
            net_source_refs = list(wall.source_refs)

            if not linked_openings:
                net_assumptions.append(
                    f"Wall {wall.id} net area equals gross area because no linked openings were provided."
                )
            else:
                incomplete_openings: list[str] = []
                for opening in linked_openings:
                    net_source_refs.extend(opening.source_refs)
                    deduction = _resolve_opening_area_deduction(opening)
                    opening_area = deduction["area_m2"]
                    opening_formula = deduction["formula"]
                    net_assumptions.extend(deduction["assumptions"])
                    opening_deductions.append(deduction["metadata"])
                    if opening_area is None:
                        incomplete_openings.append(opening.id)
                        continue
                    known_openings_area += opening_area
                    if opening_formula:
                        opening_formula_parts.append(f"{opening.id}({opening_formula})")

                if incomplete_openings:
                    net_assumptions.append(
                        "Incomplete opening data prevented full deduction for: "
                        + ", ".join(sorted(incomplete_openings))
                        + ". Only openings with explicit area or width/height were deducted."
                    )

            net_assumptions = list(dict.fromkeys(net_assumptions))

            net_formula = gross_formula
            if known_openings_area > 0:
                net_formula = f"{gross_formula} - openings_area_m2"

            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:net_area",
                    item_type="wall_net_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=gross_area - known_openings_area,
                    formula=net_formula,
                    inputs={
                        **gross_inputs,
                        "openings_area_m2": known_openings_area,
                        "opening_formulas": opening_formula_parts,
                    },
                    assumptions=net_assumptions,
                    source_refs=list(dict.fromkeys(net_source_refs)),
                    trace=_trace_from_entities(
                        entities=[wall, *linked_openings],
                        steps=[
                            "Computed wall gross area from explicit wall data.",
                            "Subtracted linked opening areas when explicit measurements were available.",
                        ],
                        metadata={
                            "gross_formula": gross_formula,
                            "opening_area_formula_parts": opening_formula_parts,
                            "opening_deductions": opening_deductions,
                        },
                    ),
                )
            )

        if wall.length_m is not None and wall.height_m is not None and wall.thickness_m is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:volume",
                    item_type="wall_volume",
                    level_id=level.level_id,
                    unit="m3",
                    quantity=wall.length_m * wall.height_m * wall.thickness_m,
                    formula="wall.length_m * wall.height_m * wall.thickness_m",
                    inputs={
                        "length_m": wall.length_m,
                        "height_m": wall.height_m,
                        "thickness_m": wall.thickness_m,
                    },
                    assumptions=list(wall.assumptions),
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Computed wall volume from length, height, and thickness."],
                    ),
                )
            )

    return takeoffs


def _level_surface_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    if level.floor_area_m2 is not None:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{level.level_id}:floor_area",
                item_type="floor_area",
                level_id=level.level_id,
                unit="m2",
                quantity=level.floor_area_m2,
                formula="level.floor_area_m2",
                inputs={"floor_area_m2": level.floor_area_m2},
                assumptions=list(level.assumptions),
                source_refs=list(level.source_refs),
                trace=QuantityTrace(
                    source_entity_ids=[level.level_id],
                    source_entity_sources=[level.source],
                    steps=["Read explicit floor area from merged level inventory."],
                    conflict_notes=list(level.conflict_notes),
                    metadata={"level_name": level.level_name},
                ),
            )
        )

    if level.ceiling_area_m2 is not None:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{level.level_id}:ceiling_area",
                item_type="ceiling_area",
                level_id=level.level_id,
                unit="m2",
                quantity=level.ceiling_area_m2,
                formula="level.ceiling_area_m2",
                inputs={"ceiling_area_m2": level.ceiling_area_m2},
                assumptions=list(level.assumptions),
                source_refs=list(level.source_refs),
                trace=QuantityTrace(
                    source_entity_ids=[level.level_id],
                    source_entity_sources=[level.source],
                    steps=["Read explicit ceiling area from merged level inventory."],
                    conflict_notes=list(level.conflict_notes),
                    metadata={"level_name": level.level_name},
                ),
            )
        )

    return takeoffs


def _door_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        _make_takeoff(
            item_key=f"{door.id}:count",
            item_type="door_count",
            level_id=level.level_id,
            unit="unit",
            quantity=float(door.count),
            formula="door.count",
            inputs={
                "count": door.count,
                "type_hint": door.type_hint,
                "material_hint": door.material_hint,
            },
            assumptions=list(door.assumptions),
            source_refs=list(door.source_refs),
            trace=_trace_from_entities(
                entities=[door],
                steps=["Read explicit door count from normalized inventory."],
            ),
        )
        for door in level.doors
    ]


def _window_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for window in level.windows:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{window.id}:count",
                item_type="window_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(window.count),
                formula="window.count",
                inputs={
                    "count": window.count,
                    "type_hint": window.type_hint,
                    "glazing_hint": window.glazing_hint,
                },
                assumptions=list(window.assumptions),
                source_refs=list(window.source_refs),
                trace=_trace_from_entities(
                    entities=[window],
                    steps=["Read explicit window count from normalized inventory."],
                ),
            )
        )

        if window.width_m is not None and window.height_m is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{window.id}:area",
                    item_type="window_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=window.width_m * window.height_m * max(window.count, 1),
                    formula="window.width_m * window.height_m * window.count",
                    inputs={
                        "width_m": window.width_m,
                        "height_m": window.height_m,
                        "count": window.count,
                    },
                    assumptions=list(window.assumptions),
                    source_refs=list(window.source_refs),
                    trace=_trace_from_entities(
                        entities=[window],
                        steps=["Computed window area from width, height, and count."],
                    ),
                )
            )
    return takeoffs


def _area_group_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for wet_area in level.wet_areas:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{wet_area.id}:count",
                item_type="wet_area_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(wet_area.count),
                formula="wet_area.count",
                inputs={"count": wet_area.count, "kind": wet_area.kind},
                assumptions=list(wet_area.assumptions),
                source_refs=list(wet_area.source_refs),
                trace=_trace_from_entities(
                    entities=[wet_area],
                    steps=["Read wet area count from normalized inventory."],
                ),
            )
        )
        if wet_area.estimated_area_m2 is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wet_area.id}:area",
                    item_type="wet_area_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=wet_area.estimated_area_m2,
                    formula="wet_area.estimated_area_m2",
                    inputs={"estimated_area_m2": wet_area.estimated_area_m2},
                    assumptions=list(wet_area.assumptions),
                    source_refs=list(wet_area.source_refs),
                    trace=_trace_from_entities(
                        entities=[wet_area],
                        steps=["Read wet area area from normalized inventory."],
                    ),
                )
            )

    for kitchen in level.kitchens:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{kitchen.id}:count",
                item_type="kitchen_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(kitchen.count),
                formula="kitchen.count",
                inputs={"count": kitchen.count},
                assumptions=list(kitchen.assumptions),
                source_refs=list(kitchen.source_refs),
                trace=_trace_from_entities(
                    entities=[kitchen],
                    steps=["Read kitchen count from normalized inventory."],
                ),
            )
        )
        if kitchen.estimated_area_m2 is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{kitchen.id}:area",
                    item_type="kitchen_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=kitchen.estimated_area_m2,
                    formula="kitchen.estimated_area_m2",
                    inputs={"estimated_area_m2": kitchen.estimated_area_m2},
                    assumptions=list(kitchen.assumptions),
                    source_refs=list(kitchen.source_refs),
                    trace=_trace_from_entities(
                        entities=[kitchen],
                        steps=["Read kitchen area from normalized inventory."],
                    ),
                )
            )

    return takeoffs


def _stair_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        _make_takeoff(
            item_key=f"{stair.id}:count",
            item_type="stair_count",
            level_id=level.level_id,
            unit="unit",
            quantity=float(stair.count),
            formula="stair.count",
            inputs={"count": stair.count, "flights": stair.flights},
            assumptions=list(stair.assumptions),
            source_refs=list(stair.source_refs),
            trace=_trace_from_entities(
                entities=[stair],
                steps=["Read stair count from normalized inventory."],
            ),
        )
        for stair in level.stairs
    ]


def _fixture_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    return [
        _make_takeoff(
            item_key=f"{fixture.id}:count",
            item_type="fixture_count",
            level_id=level.level_id,
            unit=fixture.unit,
            quantity=float(fixture.count),
            formula="fixture.count",
            inputs={
                "count": fixture.count,
                "fixture_type": fixture.fixture_type,
                "location_hint": fixture.location_hint,
            },
            assumptions=list(fixture.assumptions),
            source_refs=list(fixture.source_refs),
            trace=_trace_from_entities(
                entities=[fixture],
                steps=["Read fixture count from normalized inventory."],
            ),
        )
        for fixture in level.fixtures
    ]


def _structural_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for element in level.structural_elements:
        takeoffs.append(
            _make_takeoff(
                item_key=f"{element.id}:count",
                item_type="structural_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(element.count),
                formula="structural_element.count",
                inputs={"count": element.count, "element_type": element.element_type},
                assumptions=list(element.assumptions),
                source_refs=list(element.source_refs),
                trace=_trace_from_entities(
                    entities=[element],
                    steps=["Read structural element count from normalized inventory."],
                ),
            )
        )

        if element.length_m is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:length",
                    item_type="structural_length",
                    level_id=level.level_id,
                    unit="m",
                    quantity=element.length_m,
                    formula="structural_element.length_m",
                    inputs={"length_m": element.length_m, "element_type": element.element_type},
                    assumptions=list(element.assumptions),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural length from normalized inventory."],
                    ),
                )
            )

        if element.area_m2 is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:area",
                    item_type="structural_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=element.area_m2,
                    formula="structural_element.area_m2",
                    inputs={"area_m2": element.area_m2, "element_type": element.element_type},
                    assumptions=list(element.assumptions),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural area from normalized inventory."],
                    ),
                )
            )

        if element.volume_m3 is not None:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:volume",
                    item_type="structural_volume",
                    level_id=level.level_id,
                    unit="m3",
                    quantity=element.volume_m3,
                    formula="structural_element.volume_m3",
                    inputs={"volume_m3": element.volume_m3, "element_type": element.element_type},
                    assumptions=list(element.assumptions),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural volume from normalized inventory."],
                    ),
                )
            )

    return takeoffs


def quantify_inventory(levels: Iterable[LevelInventory]) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for level in levels:
        takeoffs.extend(_level_surface_takeoffs(level))
        takeoffs.extend(_wall_takeoffs(level))
        takeoffs.extend(_door_takeoffs(level))
        takeoffs.extend(_window_takeoffs(level))
        takeoffs.extend(_area_group_takeoffs(level))
        takeoffs.extend(_stair_takeoffs(level))
        takeoffs.extend(_fixture_takeoffs(level))
        takeoffs.extend(_structural_takeoffs(level))

    return takeoffs
