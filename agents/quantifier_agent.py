"""
Deterministic inventory quantifier.

This module converts normalized inventory into traceable quantity takeoffs.
It intentionally avoids project-specific calibration tables and opaque heuristics.

Default dimensions are applied when CAD/vision sources do not provide explicit
measurements, enabling volume/area calculations even for incomplete inventories.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger("dupla.quantifier")

# ---------------------------------------------------------------------------
# Default dimensions for MVP — applied when explicit values are missing
# ---------------------------------------------------------------------------

_DEFAULT_WALL_HEIGHT_M = 2.80
_DEFAULT_WALL_THICKNESS: dict[str | None, float] = {
    "masonry": 0.15,
    "concrete": 0.20,
    "drywall": 0.12,
    "wood": 0.10,
    None: 0.15,
}

_DEFAULT_SLAB_THICKNESS_M = 0.20
_DEFAULT_BEAM_WIDTH_M = 0.30
_DEFAULT_BEAM_HEIGHT_M = 0.50
_DEFAULT_COLUMN_WIDTH_M = 0.40
_DEFAULT_COLUMN_HEIGHT_M = 0.40
_DEFAULT_COLUMN_FLOOR_HEIGHT_M = 2.80
_DEFAULT_FOOTING_THICKNESS_M = 0.40

_REBAR_KG_PER_M3: dict[str, float] = {
    "beam": 100.0,
    "column": 120.0,
    "slab": 80.0,
    "footing": 60.0,
    "other": 90.0,
}


def _merge_inputs_with_description(base: dict[str, Any], description: str) -> dict[str, Any]:
    merged = dict(base)
    merged["takeoff_description"] = description
    return merged


def _legacy_wall_entity_description(wall: Wall) -> str:
    inp = getattr(wall, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    typ = (
        inp.get("wall_typology")
        or raw.get("wall_typology")
        or raw.get("tipo")
        or raw.get("type_label")
        or ""
    )
    typ = str(typ).strip()
    thick = wall.thickness_m
    thick_cm = int(round(thick * 100)) if thick is not None else None
    mat_code = str(raw.get("original_material_code") or wall.material_hint or "")
    loc = str(raw.get("ubicacion") or "").strip()
    parts: list[str] = []
    if typ:
        parts.append(f"Muro tipo {typ}")
    else:
        parts.append("[Tipo no identificado en plano] — muro")
    if mat_code.startswith("block_"):
        parts.append(f"bloque {mat_code.replace('block_', '').replace('in', '')}\"")
    elif mat_code:
        parts.append(mat_code.replace("_", " "))
    if thick_cm is not None:
        parts.append(f"espesor {thick_cm} cm")
    if loc:
        parts.append(f"ubicación {loc}")
    return ", ".join(parts)


def _door_entity_description(door: Door) -> str:
    inp = getattr(door, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    label = (inp.get("door_label") or raw.get("label") or "").strip()
    th = (door.type_hint or raw.get("type") or "").replace("_", " ")
    mat = (door.material_hint or raw.get("material") or "").replace("_", " ")
    w, h = door.width_m, door.height_m
    dim = ""
    if w is not None and h is not None:
        dim = f"{w:.2f}×{h:.2f} m"
    parts: list[str] = []
    if label:
        parts.append(label)
    else:
        parts.append("Puerta")
        if th:
            parts.append(th)
        if mat:
            parts.append(mat)
    if dim:
        parts.append(dim)
    return " — ".join(parts) if len(parts) > 1 else (parts[0] if parts else "Puerta")


def _window_entity_description(window: Window) -> str:
    inp = getattr(window, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    label = (inp.get("window_label") or raw.get("label") or "").strip()
    th = (window.type_hint or raw.get("type") or "").replace("_", " ")
    w, h = window.width_m, window.height_m
    dim = ""
    if w is not None and h is not None:
        dim = f"{w:.2f}×{h:.2f} m"
    parts: list[str] = []
    if label:
        parts.append(label)
    else:
        parts.append("Ventana")
        if th:
            parts.append(th)
    if dim:
        parts.append(dim)
    return " — ".join(parts) if len(parts) > 1 else (parts[0] if parts else "Ventana")


def _clean_wall_entity_description(wall: Wall) -> str:
    inp = getattr(wall, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    typ = (
        inp.get("wall_typology")
        or raw.get("wall_typology")
        or raw.get("tipo")
        or raw.get("type_label")
        or ""
    )
    typ = str(typ).strip()
    thick = wall.thickness_m
    thick_cm = int(round(thick * 100)) if thick is not None else None
    mat_code = str(raw.get("original_material_code") or wall.material_hint or "")
    loc = str(raw.get("ubicacion") or "").strip()
    if not loc:
        loc = str(wall.interior_exterior_hint or raw.get("location") or "").strip()

    parts: list[str] = []
    technical_typ = typ.lower().startswith(("json-wall-", "vis-wall-"))
    if typ and not technical_typ:
        parts.append(f"Muro tipo {typ}")
    elif wall.wall_system == "masonry_wall" or wall.material_hint == "masonry":
        parts.append("Muro de bloques")
    elif wall.wall_system == "concrete_wall" or wall.material_hint == "concrete":
        parts.append("Muro de hormigon")
    else:
        parts.append("Muro")
    if mat_code.startswith("block_"):
        parts.append(f"bloque {mat_code.replace('block_', '').replace('in', '')}\"")
    elif mat_code and mat_code not in {"masonry", "concrete", "drywall"} and not mat_code.startswith("json-wall"):
        parts.append(mat_code.replace("_", " "))
    if thick_cm is not None:
        parts.append(f"espesor {thick_cm} cm")
    if loc:
        parts.append(f"ubicacion {loc}")
    return ", ".join(parts)


def _wall_block_inputs(wall: Wall) -> tuple[dict[str, Any], list[str]]:
    inputs: dict[str, Any] = {
        "wall_system": wall.wall_system,
        "interior_exterior_hint": wall.interior_exterior_hint,
    }
    assumptions: list[str] = []
    if wall.thickness_m is not None:
        inputs["thickness_m"] = wall.thickness_m
        thickness_in = round(wall.thickness_m / 0.0254)
        if thickness_in in {4, 6, 8, 12}:
            inputs["thickness_in"] = f'{thickness_in}"'
            inputs["block_size"] = f'{thickness_in}"'
            inputs["block_nominal_cm"] = int(round(wall.thickness_m * 100))
    if wall.material_hint == "masonry" or wall.wall_system == "masonry_wall":
        spec = "BNP" if wall.structural or wall.interior_exterior_hint == "exterior" else "SNP"
        spacing = "0.80" if inputs.get("thickness_in") == '4"' else "0.40"
        inputs["block_spec"] = spec
        inputs["reinforcement_main_bars"] = f"3/8@{spacing}"
        assumptions.append(
            f"Wall {wall.id} block APU matching uses {spec} and 3/8@{spacing} as default constructability hints pending explicit reinforcement notes."
        )
    return inputs, assumptions


_wall_entity_description = _clean_wall_entity_description


def _structural_entity_description(element: StructuralElement) -> str:
    """Human-readable label from rotulo, tipo y sección (B1 — partidas específicas)."""
    inp = getattr(element, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    label = str(inp.get("structural_label") or element.id or "").strip()
    etype = element.element_type
    type_es = {
        "column": "Columna",
        "beam": "Viga",
        "slab": "Losa",
        "footing": "Zapata",
        "other": "Elemento estructural",
    }.get(etype, str(etype).replace("_", " "))
    head = f"{type_es} {label}".strip() if label else type_es
    parts: list[str] = [head]
    sw, sh = element.section_width_m, element.section_height_m
    if sw is not None and sh is not None:
        parts.append(f"sección {sw:.2f}×{sh:.2f} m")
    elif sw is not None or sh is not None:
        sws = f"{sw:.2f}" if sw is not None else "-"
        shs = f"{sh:.2f}" if sh is not None else "-"
        parts.append(f"sección {sws}×{shs} m")
    sched = str(inp.get("schedule_row_text") or "").strip()
    if sched and sched != label:
        clip = 100
        parts.append(f"tabla: {sched[:clip]}{'…' if len(sched) > clip else ''}")
    ubi = str(raw.get("ubicacion") or "").strip()
    if ubi:
        parts.append(f"ubicación {ubi}")
    return ", ".join(parts)


def _fixture_entity_description(fixture: Fixture) -> str:
    inp = getattr(fixture, "inputs", None) or {}
    raw = inp.get("raw") if isinstance(inp.get("raw"), dict) else {}
    label = (inp.get("fixture_label") or raw.get("label") or "").strip()
    if label:
        loc = str(fixture.location_hint or "").strip()
        return f"{label} ({loc})" if loc else label
    disc = str(inp.get("discipline") or "").lower()
    ftype = str(fixture.fixture_type or "").lower()
    loc = str(fixture.location_hint or "").strip()
    loc_part = f" ({loc})" if loc else ""
    if disc == "electrical" or disc == "electric":
        labels = {
            "outlet_110v": "Salida tomacorriente 110V",
            "outlet_220v": "Salida tomacorriente 220V",
            "switch_single": "Interruptor sencillo",
            "switch_double": "Interruptor doble",
            "luminaire_ceiling": "Luminaria de techo",
        }
        base = labels.get(ftype, f"Punto eléctrico ({ftype or 'tipo'})")
        return f"{base}{loc_part}"
    if disc == "plumbing":
        return f"Punto sanitario / plomería ({ftype or 'tipo'}){loc_part}"
    return f"Equipo / accesorio ({ftype or 'fixture'}){loc_part}"


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


def _positive_count(value: Any, *, default: float = 1.0) -> float:
    try:
        count = float(value)
    except (TypeError, ValueError):
        return default
    return count if count > 0 else default


def _coerce_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def _dedupe_tags(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        tag = str(value)
        if tag in seen:
            continue
        seen.add(tag)
        result.append(tag)
    return result


def _merge_context_tags(base_tags: Any, *sources: Any) -> list[str]:
    merged: list[str] = []
    merged.extend(_coerce_tags(base_tags))
    for source in sources:
        merged.extend(_coerce_tags(source))
    return _dedupe_tags(merged)


def _entity_context_tags(entity: Any, *base_tags: str) -> list[str]:
    entity_inputs = getattr(entity, "inputs", {})
    explicit_tags = entity_inputs.get("context_tags", []) if isinstance(entity_inputs, dict) else []
    return _merge_context_tags(list(base_tags), explicit_tags)


def _structural_length_payload(
    element: StructuralElement,
) -> tuple[float | None, str | None, dict[str, Any], list[str]]:
    if element.length_m is not None:
        return (
            element.length_m,
            "structural_element.length_m",
            {"length_m": element.length_m},
            [],
        )

    if element.element_type == "beam" and element.span_m is not None:
        count = _positive_count(element.count)
        return (
            element.span_m * count,
            "structural_element.span_m * structural_element.count",
            {"span_m": element.span_m, "count": element.count},
            [
                f"Beam {element.id} total length was inferred from span_m * count because explicit total length was not provided."
            ],
        )

    return None, None, {}, []


def _structural_volume_payload(
    element: StructuralElement,
    length_quantity: float | None,
    length_formula: str | None,
    length_inputs: dict[str, Any],
) -> tuple[float | None, str | None, dict[str, Any], list[str]]:
    if element.volume_m3 is not None:
        return (
            element.volume_m3,
            "structural_element.volume_m3",
            {"volume_m3": element.volume_m3},
            [],
        )

    if (
        element.element_type in {"beam", "column"}
        and length_quantity is not None
        and element.section_width_m is not None
        and element.section_height_m is not None
    ):
        return (
            length_quantity * element.section_width_m * element.section_height_m,
            f"{length_formula} * structural_element.section_width_m * structural_element.section_height_m",
            {
                **length_inputs,
                "section_width_m": element.section_width_m,
                "section_height_m": element.section_height_m,
            },
            [],
        )

    if (
        element.element_type == "slab"
        and element.area_m2 is not None
        and element.section_height_m is not None
    ):
        return (
            element.area_m2 * element.section_height_m,
            "structural_element.area_m2 * structural_element.section_height_m",
            {
                "area_m2": element.area_m2,
                "section_height_m": element.section_height_m,
            },
            [],
        )

    return None, None, {}, []


def _structural_formwork_payload(
    element: StructuralElement,
    length_quantity: float | None,
    length_inputs: dict[str, Any],
) -> tuple[float | None, str | None, dict[str, Any], list[str]]:
    if not _structural_requires_reinforcement_hint(element):
        return None, None, {}, []

    if (
        element.element_type == "beam"
        and length_quantity is not None
        and element.section_width_m is not None
        and element.section_height_m is not None
    ):
        return (
            (2 * element.section_height_m + element.section_width_m) * length_quantity,
            "(2 * structural_element.section_height_m + structural_element.section_width_m) * structural_length_total_m",
            {
                **length_inputs,
                "structural_length_total_m": length_quantity,
                "section_width_m": element.section_width_m,
                "section_height_m": element.section_height_m,
            },
            [
                f"Beam {element.id} formwork area hint excludes the top face and includes two sides plus soffit."
            ],
        )

    if (
        element.element_type == "column"
        and length_quantity is not None
        and element.section_width_m is not None
        and element.section_height_m is not None
    ):
        return (
            2 * (element.section_width_m + element.section_height_m) * length_quantity,
            "2 * (structural_element.section_width_m + structural_element.section_height_m) * structural_length_total_m",
            {
                **length_inputs,
                "structural_length_total_m": length_quantity,
                "section_width_m": element.section_width_m,
                "section_height_m": element.section_height_m,
            },
            [],
        )

    if element.element_type == "slab" and element.area_m2 is not None:
        return (
            element.area_m2,
            "structural_element.area_m2",
            {"area_m2": element.area_m2},
            [
                f"Slab {element.id} formwork area hint assumes underside formwork only."
            ],
        )

    return None, None, {}, []


def _structural_requires_reinforcement_hint(element: StructuralElement) -> bool:
    if element.reinforcement_hint is not None:
        return True
    if element.concrete_grade_hint is not None:
        return True
    if (element.material_hint or "").lower() == "concrete":
        return True
    if element.material_hint is None and element.element_type in {"beam", "column", "slab", "footing"}:
        return True
    return False


def _has_aggregated_json_count(opening: Opening) -> bool:
    return _find_input_value(opening.inputs, "json_count") is not None or any(
        ref.startswith("block:") for ref in opening.source_refs
    )


def _resolve_opening_area_deduction(opening: Opening) -> dict[str, Any]:
    assumptions = list(opening.assumptions)
    opening_count = _positive_count(opening.count)
    metadata: dict[str, Any] = {
        "opening_id": opening.id,
        "opening_type": opening.opening_type,
        "opening_source": opening.source,
        "aggregated_count": opening_count,
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
    aggregated_count = opening_count
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
        wall_desc = _wall_entity_description(wall)
        block_inputs, block_assumptions = _wall_block_inputs(wall)
        if wall.length_m is not None:
            finish_h = wall.height_m
            finish_h_eff = finish_h if finish_h is not None else _DEFAULT_WALL_HEIGHT_M
            finish_src = "plan_measurement" if finish_h is not None else "default_estimate"
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:length",
                    item_type="wall_length",
                    level_id=level.level_id,
                    unit="m",
                    quantity=wall.length_m,
                    formula="wall.length_m",
                    inputs=_merge_inputs_with_description(
                        {
                            "length_m": wall.length_m,
                            "finish_height_m": finish_h_eff,
                            "finish_height_source": finish_src,
                            **block_inputs,
                        },
                        wall_desc,
                    ),
                    assumptions=list(dict.fromkeys([*wall.assumptions, *block_assumptions])),
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Read explicit wall length from normalized inventory."],
                    ),
                )
            )

        effective_height = wall.height_m
        height_assumed = False
        if effective_height is None and wall.length_m is not None:
            effective_height = _DEFAULT_WALL_HEIGHT_M
            height_assumed = True

        effective_thickness = wall.thickness_m
        thickness_assumed = False
        if effective_thickness is None and wall.length_m is not None:
            mat = (wall.material_hint or "").lower() or None
            effective_thickness = _DEFAULT_WALL_THICKNESS.get(mat, _DEFAULT_WALL_THICKNESS[None])
            thickness_assumed = True

        gross_area: float | None = None
        gross_formula = ""
        gross_inputs: dict[str, Any] = {}
        gross_assumptions = list(wall.assumptions)

        if wall.area_m2 is not None:
            gross_area = wall.area_m2
            gross_formula = "wall.area_m2"
            gross_inputs = {"area_m2": wall.area_m2}
        elif wall.length_m is not None and effective_height is not None:
            gross_area = wall.length_m * effective_height
            gross_formula = "wall.length_m * wall.height_m"
            gross_inputs = {"length_m": wall.length_m, "height_m": effective_height}
            if height_assumed:
                gross_assumptions.append(
                    f"Wall {wall.id} height assumed at {_DEFAULT_WALL_HEIGHT_M}m (standard residential floor-to-ceiling)."
                )

        if gross_area is not None:
            gross_context_tags = _entity_context_tags(wall, "wall", "gross_area")
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:gross_area",
                    item_type="wall_gross_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=gross_area,
                    formula=gross_formula,
                    inputs=_merge_inputs_with_description(
                        {
                            **gross_inputs,
                            "material_hint": wall.material_hint,
                            "structural": wall.structural,
                            **block_inputs,
                            "context_tags": gross_context_tags,
                        },
                        wall_desc,
                    ),
                    assumptions=list(dict.fromkeys([*gross_assumptions, *block_assumptions])),
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Computed gross wall area from explicit wall data."],
                        metadata={
                            "gross_formula": gross_formula,
                            "context_tags": gross_context_tags,
                        },
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

            net_context_tags = _entity_context_tags(wall, "wall", "net_area")
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:net_area",
                    item_type="wall_net_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=gross_area - known_openings_area,
                    formula=net_formula,
                    inputs=_merge_inputs_with_description(
                        {
                            **gross_inputs,
                            "material_hint": wall.material_hint,
                            "structural": wall.structural,
                            "openings_area_m2": known_openings_area,
                            "opening_formulas": opening_formula_parts,
                            **block_inputs,
                            "context_tags": net_context_tags,
                        },
                        wall_desc,
                    ),
                    assumptions=list(dict.fromkeys([*net_assumptions, *block_assumptions])),
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
                            "context_tags": net_context_tags,
                        },
                    ),
                )
            )

        if wall.length_m is not None and effective_height is not None and effective_thickness is not None:
            wall_volume_context_tags = _entity_context_tags(wall, "wall", "volume")
            vol_assumptions = list(wall.assumptions)
            if height_assumed:
                vol_assumptions.append(
                    f"Wall {wall.id} height assumed at {_DEFAULT_WALL_HEIGHT_M}m (standard residential)."
                )
            if thickness_assumed:
                vol_assumptions.append(
                    f"Wall {wall.id} thickness assumed at {effective_thickness}m "
                    f"(default for {wall.material_hint or 'generic'} wall)."
                )
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wall.id}:volume",
                    item_type="wall_volume",
                    level_id=level.level_id,
                    unit="m3",
                    quantity=wall.length_m * effective_height * effective_thickness,
                    formula="wall.length_m * wall.height_m * wall.thickness_m",
                    inputs=_merge_inputs_with_description(
                        {
                            "length_m": wall.length_m,
                            "height_m": effective_height,
                            "thickness_m": effective_thickness,
                            "material_hint": wall.material_hint,
                            "structural": wall.structural,
                            **block_inputs,
                            "context_tags": wall_volume_context_tags,
                            "height_assumed": height_assumed,
                            "thickness_assumed": thickness_assumed,
                        },
                        wall_desc,
                    ),
                    assumptions=list(dict.fromkeys([*vol_assumptions, *block_assumptions])),
                    source_refs=list(wall.source_refs),
                    trace=_trace_from_entities(
                        entities=[wall],
                        steps=["Computed wall volume from length, height, and thickness."],
                        metadata={"context_tags": wall_volume_context_tags},
                    ),
                )
            )

    return takeoffs


def _level_surface_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    level_surface_context_tags = ["has_wet_areas"] if level.wet_areas else []
    explicit_level_tags = level.inputs.get("context_tags", []) if isinstance(level.inputs, dict) else []

    if level.floor_area_m2 is not None:
        floor_context_tags = _merge_context_tags(
            ["floor", "area"],
            level_surface_context_tags,
            explicit_level_tags,
        )
        floor_desc = f"Área de piso — nivel {level.level_name}"
        takeoffs.append(
            _make_takeoff(
                item_key=f"{level.level_id}:floor_area",
                item_type="floor_area",
                level_id=level.level_id,
                unit="m2",
                quantity=level.floor_area_m2,
                formula="level.floor_area_m2",
                inputs=_merge_inputs_with_description(
                    {
                        "floor_area_m2": level.floor_area_m2,
                        "context_tags": floor_context_tags,
                    },
                    floor_desc,
                ),
                assumptions=list(level.assumptions),
                source_refs=list(level.source_refs),
                trace=QuantityTrace(
                    source_entity_ids=[level.level_id],
                    source_entity_sources=[level.source],
                    steps=["Read explicit floor area from merged level inventory."],
                    conflict_notes=list(level.conflict_notes),
                    metadata={
                        "level_name": level.level_name,
                        "context_tags": floor_context_tags,
                    },
                ),
            )
        )

    if level.ceiling_area_m2 is not None:
        ceiling_context_tags = _merge_context_tags(
            ["ceiling", "area"],
            level_surface_context_tags,
            explicit_level_tags,
        )
        ceiling_desc = f"Área de cielo raso / techo — nivel {level.level_name}"
        takeoffs.append(
            _make_takeoff(
                item_key=f"{level.level_id}:ceiling_area",
                item_type="ceiling_area",
                level_id=level.level_id,
                unit="m2",
                quantity=level.ceiling_area_m2,
                formula="level.ceiling_area_m2",
                inputs=_merge_inputs_with_description(
                    {
                        "ceiling_area_m2": level.ceiling_area_m2,
                        "context_tags": ceiling_context_tags,
                    },
                    ceiling_desc,
                ),
                assumptions=list(level.assumptions),
                source_refs=list(level.source_refs),
                trace=QuantityTrace(
                    source_entity_ids=[level.level_id],
                    source_entity_sources=[level.source],
                    steps=["Read explicit ceiling area from merged level inventory."],
                    conflict_notes=list(level.conflict_notes),
                    metadata={
                        "level_name": level.level_name,
                        "context_tags": ceiling_context_tags,
                    },
                ),
            )
        )

    return takeoffs


def _door_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for door in level.doors:
        door_desc = _door_entity_description(door)
        door_context_tags = _entity_context_tags(door, "door")
        takeoffs.append(
            _make_takeoff(
                item_key=f"{door.id}:count",
                item_type="door_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(door.count),
                formula="door.count",
                inputs=_merge_inputs_with_description(
                    {
                    "count": door.count,
                    "type_hint": door.type_hint,
                    "material_hint": door.material_hint,
                    "context_tags": door_context_tags,
                    },
                    door_desc,
                ),
                assumptions=list(door.assumptions),
                source_refs=list(door.source_refs),
                trace=_trace_from_entities(
                    entities=[door],
                    steps=["Read explicit door count from normalized inventory."],
                    metadata={"context_tags": door_context_tags},
                ),
            )
        )
    return takeoffs


def _window_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for window in level.windows:
        win_desc = _window_entity_description(window)
        window_count_context_tags = _entity_context_tags(window, "window")
        takeoffs.append(
            _make_takeoff(
                item_key=f"{window.id}:count",
                item_type="window_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(window.count),
                formula="window.count",
                inputs=_merge_inputs_with_description(
                    {
                    "count": window.count,
                    "type_hint": window.type_hint,
                    "glazing_hint": window.glazing_hint,
                    "context_tags": window_count_context_tags,
                    },
                    win_desc,
                ),
                assumptions=list(window.assumptions),
                source_refs=list(window.source_refs),
                trace=_trace_from_entities(
                    entities=[window],
                    steps=["Read explicit window count from normalized inventory."],
                    metadata={"context_tags": window_count_context_tags},
                ),
            )
        )

        if window.width_m is not None and window.height_m is not None:
            window_area_context_tags = _entity_context_tags(window, "window", "area")
            window_count = _positive_count(window.count)
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{window.id}:area",
                    item_type="window_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=window.width_m * window.height_m * window_count,
                    formula="window.width_m * window.height_m * window.count",
                    inputs=_merge_inputs_with_description(
                        {
                            "width_m": window.width_m,
                            "height_m": window.height_m,
                            "count": window.count,
                            "glazing_hint": window.glazing_hint,
                            "context_tags": window_area_context_tags,
                        },
                        win_desc,
                    ),
                    assumptions=list(window.assumptions),
                    source_refs=list(window.source_refs),
                    trace=_trace_from_entities(
                        entities=[window],
                        steps=["Computed window area from width, height, and count."],
                        metadata={"context_tags": window_area_context_tags},
                    ),
                )
            )
    return takeoffs


def _area_group_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for wet_area in level.wet_areas:
        wet_area_count_context_tags = _entity_context_tags(wet_area, "wet_area", wet_area.kind, "count")
        wa_desc = f"Área húmeda ({wet_area.kind}) — {wet_area.id}"
        raw_w = wet_area.inputs.get("raw") if isinstance(wet_area.inputs, dict) else {}
        est_m2 = wet_area.estimated_area_m2
        if est_m2 is None and isinstance(raw_w, dict) and raw_w.get("area_m2") is not None:
            try:
                est_m2 = float(raw_w["area_m2"])
            except (TypeError, ValueError):
                est_m2 = None
        count_payload: dict[str, Any] = {
            "count": wet_area.count,
            "kind": wet_area.kind,
            "context_tags": wet_area_count_context_tags,
        }
        if est_m2 is not None:
            count_payload["estimated_area_m2"] = est_m2
        takeoffs.append(
            _make_takeoff(
                item_key=f"{wet_area.id}:count",
                item_type="wet_area_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(wet_area.count),
                formula="wet_area.count",
                inputs=_merge_inputs_with_description(
                    count_payload,
                    wa_desc,
                ),
                assumptions=list(wet_area.assumptions),
                source_refs=list(wet_area.source_refs),
                trace=_trace_from_entities(
                    entities=[wet_area],
                    steps=["Read wet area count from normalized inventory."],
                    metadata={"context_tags": wet_area_count_context_tags},
                ),
            )
        )
        if wet_area.estimated_area_m2 is not None:
            wet_area_area_context_tags = _entity_context_tags(wet_area, "wet_area", wet_area.kind, "area")
            wa_area_desc = f"Superficie área húmeda ({wet_area.kind}) — {wet_area.id}"
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{wet_area.id}:area",
                    item_type="wet_area_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=wet_area.estimated_area_m2,
                    formula="wet_area.estimated_area_m2",
                    inputs=_merge_inputs_with_description(
                        {
                            "estimated_area_m2": wet_area.estimated_area_m2,
                            "kind": wet_area.kind,
                            "context_tags": wet_area_area_context_tags,
                        },
                        wa_area_desc,
                    ),
                    assumptions=list(wet_area.assumptions),
                    source_refs=list(wet_area.source_refs),
                    trace=_trace_from_entities(
                        entities=[wet_area],
                        steps=["Read wet area area from normalized inventory."],
                        metadata={"context_tags": wet_area_area_context_tags},
                    ),
                )
            )

    for kitchen in level.kitchens:
        kit_desc = f"Cocina — {kitchen.id}"
        kit_count_inputs: dict[str, Any] = {"count": kitchen.count}
        if kitchen.estimated_area_m2 is not None:
            kit_count_inputs["estimated_area_m2"] = kitchen.estimated_area_m2
        takeoffs.append(
            _make_takeoff(
                item_key=f"{kitchen.id}:count",
                item_type="kitchen_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(kitchen.count),
                formula="kitchen.count",
                inputs=_merge_inputs_with_description(kit_count_inputs, kit_desc),
                assumptions=list(kitchen.assumptions),
                source_refs=list(kitchen.source_refs),
                trace=_trace_from_entities(
                    entities=[kitchen],
                    steps=["Read kitchen count from normalized inventory."],
                ),
            )
        )
        if kitchen.estimated_area_m2 is not None:
            kit_area_desc = f"Superficie cocina — {kitchen.id}"
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{kitchen.id}:area",
                    item_type="kitchen_area",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=kitchen.estimated_area_m2,
                    formula="kitchen.estimated_area_m2",
                    inputs=_merge_inputs_with_description(
                        {"estimated_area_m2": kitchen.estimated_area_m2},
                        kit_area_desc,
                    ),
                    assumptions=list(kitchen.assumptions),
                    source_refs=list(kitchen.source_refs),
                    trace=_trace_from_entities(
                        entities=[kitchen],
                        steps=["Read kitchen area from normalized inventory."],
                    ),
                )
            )

    return takeoffs


# Piezas sanitarias típicas de baño/cocina — van como wet_area_fixture_count si hay wet_areas (B3).
_SKIP_FIXTURE_COUNT_IF_WET_AREAS: frozenset[str] = frozenset(
    {"toilet", "sink", "shower_base", "bathtub", "bidet", "urinal", "laundry_sink"}
)

_WET_AREA_KIND_LABEL: dict[str, str] = {
    "full_bathroom": "baño",
    "half_bathroom": "medio baño",
    "service_bathroom": "baño de servicio",
    "laundry": "lavandería",
    "utility": "área de servicio",
    "bathroom": "baño",
}

# (raw flag from vision wet_areas JSON, fixture_type token, Spanish label for description)
_WET_AREA_FLAG_PIECES: tuple[tuple[str, str, str], ...] = (
    ("has_toilet", "toilet", "Inodoro"),
    ("has_sink", "sink", "Lavamano"),
    ("has_shower", "shower_base", "Ducha"),
    ("has_bathtub", "bathtub", "Bañera"),
    ("has_bidet", "bidet", "Bidet"),
)


def _wet_area_fixture_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    """Emit wet_area_fixture_count from wet-area booleans (Vision raw) × count (B3)."""
    takeoffs: list[QuantityTakeoff] = []
    for wet_area in level.wet_areas:
        raw = wet_area.inputs.get("raw") if isinstance(wet_area.inputs, dict) else {}
        if not isinstance(raw, dict):
            raw = {}
        n_units = max(int(wet_area.count or 1), 1)
        kind = (wet_area.kind or "bathroom").strip().lower()
        area_label = _WET_AREA_KIND_LABEL.get(kind, kind.replace("_", " "))
        tags = _entity_context_tags(wet_area, "wet_area", wet_area.kind, "fixture")

        for flag, fixture_type, label_es in _WET_AREA_FLAG_PIECES:
            if not raw.get(flag):
                continue
            qty = float(n_units)
            desc = f"{label_es} en {area_label}"
            item_key = f"{wet_area.id}:wet_fixture:{fixture_type}"
            takeoffs.append(
                _make_takeoff(
                    item_key=item_key,
                    item_type="wet_area_fixture_count",
                    level_id=level.level_id,
                    unit="ud",
                    quantity=qty,
                    formula=f"wet_area.count * {flag}",
                    inputs=_merge_inputs_with_description(
                        {
                            "fixture_type": fixture_type,
                            "area_type": wet_area.kind,
                            "wet_area_id": wet_area.id,
                            "wet_area_flag": flag,
                            "context_tags": tags,
                        },
                        desc,
                    ),
                    assumptions=list(wet_area.assumptions),
                    source_refs=list(wet_area.source_refs),
                    trace=_trace_from_entities(
                        entities=[wet_area],
                        steps=[
                            "Counted sanitary fixture from wet-area schedule "
                            f"({flag}=true, {n_units} unit(s)).",
                        ],
                        metadata={
                            "context_tags": tags,
                            "source_discipline": "sanitaria",
                        },
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
            inputs=_merge_inputs_with_description(
                {"count": stair.count, "flights": stair.flights},
                f"Escalera — {stair.id}",
            ),
            assumptions=list(stair.assumptions),
            source_refs=list(stair.source_refs),
            trace=_trace_from_entities(
                entities=[stair],
                steps=["Read stair count from normalized inventory."],
            ),
        )
        for stair in level.stairs
    ]


def _fixture_takeoffs(
    level: LevelInventory,
    *,
    skip_sanitary_fixture_dupes: bool = False,
) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for fixture in level.fixtures:
        ftype = str(fixture.fixture_type or "").lower()
        disc = str((fixture.inputs or {}).get("discipline") or "").lower()
        if skip_sanitary_fixture_dupes and ftype in _SKIP_FIXTURE_COUNT_IF_WET_AREAS:
            if disc not in {"electrical", "electric"}:
                continue
        fx_desc = _fixture_entity_description(fixture)
        takeoffs.append(
            _make_takeoff(
                item_key=f"{fixture.id}:count",
                item_type="fixture_count",
                level_id=level.level_id,
                unit=fixture.unit,
                quantity=float(fixture.count),
                formula="fixture.count",
                inputs=_merge_inputs_with_description(
                    {
                        **(dict(fixture.inputs) if fixture.inputs else {}),
                        "count": fixture.count,
                        "fixture_type": fixture.fixture_type,
                        "location_hint": fixture.location_hint,
                    },
                    fx_desc,
                ),
                assumptions=list(fixture.assumptions),
                source_refs=list(fixture.source_refs),
                trace=_trace_from_entities(
                    entities=[fixture],
                    steps=["Read fixture count from normalized inventory."],
                ),
            )
        )
    return takeoffs


def _apply_structural_defaults(element: StructuralElement) -> tuple[StructuralElement, list[str]]:
    """Return element with filled-in defaults and a list of assumption notes."""
    assumptions: list[str] = []
    updates: dict[str, Any] = {}

    etype = element.element_type

    if etype == "beam":
        if element.section_width_m is None:
            updates["section_width_m"] = _DEFAULT_BEAM_WIDTH_M
            assumptions.append(
                f"Beam {element.id} section width assumed at {_DEFAULT_BEAM_WIDTH_M}m (standard rectangular beam)."
            )
        if element.section_height_m is None:
            updates["section_height_m"] = _DEFAULT_BEAM_HEIGHT_M
            assumptions.append(
                f"Beam {element.id} section height assumed at {_DEFAULT_BEAM_HEIGHT_M}m (standard rectangular beam)."
            )

    elif etype == "column":
        if element.section_width_m is None:
            updates["section_width_m"] = _DEFAULT_COLUMN_WIDTH_M
            assumptions.append(
                f"Column {element.id} section width assumed at {_DEFAULT_COLUMN_WIDTH_M}m."
            )
        if element.section_height_m is None:
            updates["section_height_m"] = _DEFAULT_COLUMN_HEIGHT_M
            assumptions.append(
                f"Column {element.id} section height assumed at {_DEFAULT_COLUMN_HEIGHT_M}m."
            )
        if element.length_m is None and element.span_m is None:
            count = _positive_count(element.count)
            updates["length_m"] = _DEFAULT_COLUMN_FLOOR_HEIGHT_M * count
            assumptions.append(
                f"Column {element.id} total length inferred from floor height "
                f"{_DEFAULT_COLUMN_FLOOR_HEIGHT_M}m x {count} units."
            )

    elif etype == "slab":
        if element.section_height_m is None:
            updates["section_height_m"] = _DEFAULT_SLAB_THICKNESS_M
            assumptions.append(
                f"Slab {element.id} thickness assumed at {_DEFAULT_SLAB_THICKNESS_M}m (standard solid slab)."
            )

    elif etype == "footing":
        if element.section_height_m is None:
            updates["section_height_m"] = _DEFAULT_FOOTING_THICKNESS_M
            assumptions.append(
                f"Footing {element.id} depth assumed at {_DEFAULT_FOOTING_THICKNESS_M}m."
            )

    if not updates:
        return element, assumptions

    from dataclasses import fields as dc_fields
    payload = {f.name: getattr(element, f.name) for f in dc_fields(element)}
    payload.update(updates)
    payload["assumptions"] = list(dict.fromkeys([*element.assumptions, *assumptions]))
    return StructuralElement(**payload), assumptions


def _rebar_takeoffs(
    element: StructuralElement,
    level_id: str | None,
    volume_quantity: float,
    volume_formula: str | None,
    *,
    struct_desc: str = "",
) -> list[QuantityTakeoff]:
    """Estimate reinforcement steel weight from concrete volume using standard ratios."""
    etype = element.element_type
    ratio = _REBAR_KG_PER_M3.get(etype, _REBAR_KG_PER_M3["other"])
    rebar_kg = volume_quantity * ratio
    ratio_note = (
        f"Estimado por ratio {ratio:g} kg/m³. Requiere verificación con despiece real."
    )

    context_tags = _entity_context_tags(element, "structural", etype, "reinforcement", "kg")
    desc = struct_desc or _structural_entity_description(element)
    return [
        _make_takeoff(
            item_key=f"{element.id}:reinforcement_kg",
            item_type=f"{etype}_reinforcement_kg",
            level_id=level_id,
            unit="kg",
            quantity=rebar_kg,
            formula=f"concrete_volume_m3 * {ratio} kg/m3",
            inputs=_merge_inputs_with_description(
                {
                    "concrete_volume_m3": volume_quantity,
                    "rebar_ratio_kg_m3": ratio,
                    "element_type": etype,
                    "material_hint": element.material_hint,
                    "reinforcement_hint": element.reinforcement_hint,
                    "context_tags": context_tags,
                    "quantity_source": "ratio_estimate",
                    "quantity_source_note": ratio_note,
                },
                f"Acero estimado ({etype}) — {desc}" if desc else f"Acero estimado ({etype})",
            ),
            assumptions=[
                f"{etype.title()} {element.id} reinforcement estimated at {ratio} kg/m3 "
                f"(standard preliminary ratio for {etype} elements).",
            ],
            source_refs=list(element.source_refs),
            trace=_trace_from_entities(
                entities=[element],
                steps=[
                    f"Estimated reinforcement steel from concrete volume ({volume_quantity:.3f} m3) "
                    f"using standard ratio of {ratio} kg/m3.",
                ],
                metadata={
                    "context_tags": context_tags,
                    "quantity_source": "ratio_estimate",
                    "quantity_source_note": ratio_note,
                },
            ),
        )
    ]


def _structural_takeoffs(level: LevelInventory) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []
    for element in level.structural_elements:
        element, default_assumptions = _apply_structural_defaults(element)
        base_context_tags = _entity_context_tags(element, "structural", element.element_type)
        base_inputs = {
            "element_type": element.element_type,
            "material_hint": element.material_hint,
            "structural_label": str(element.id or "").strip(),
            "section_width_m": element.section_width_m,
            "section_height_m": element.section_height_m,
            "span_m": element.span_m,
            "load_bearing": element.load_bearing,
            "orientation": element.orientation,
            "reinforcement_hint": element.reinforcement_hint,
            "concrete_grade_hint": element.concrete_grade_hint,
            "steel_grade_hint": element.steel_grade_hint,
            "host_level": element.host_level,
            "adjacent_elements": list(element.adjacent_elements),
        }
        base_metadata = {
            "context_tags": base_context_tags,
            "material_hint": element.material_hint,
            "section_width_m": element.section_width_m,
            "section_height_m": element.section_height_m,
            "span_m": element.span_m,
            "load_bearing": element.load_bearing,
            "orientation": element.orientation,
            "reinforcement_hint": element.reinforcement_hint,
            "concrete_grade_hint": element.concrete_grade_hint,
            "steel_grade_hint": element.steel_grade_hint,
            "host_level": element.host_level,
            "adjacent_elements": list(element.adjacent_elements),
        }
        struct_desc = _structural_entity_description(element)
        count_in: dict[str, Any] = {
            "count": element.count,
            **base_inputs,
            "context_tags": _entity_context_tags(
                element, "structural", element.element_type, "count"
            ),
        }
        if element.element_type == "column" and element.count and element.length_m is not None:
            count_in["length_m_per_column"] = float(element.length_m) / _positive_count(element.count)
        takeoffs.append(
            _make_takeoff(
                item_key=f"{element.id}:count",
                item_type="structural_count",
                level_id=level.level_id,
                unit="unit",
                quantity=float(element.count),
                formula="structural_element.count",
                inputs=_merge_inputs_with_description(
                    count_in,
                    struct_desc,
                ),
                assumptions=list(element.assumptions),
                source_refs=list(element.source_refs),
                trace=_trace_from_entities(
                    entities=[element],
                    steps=["Read structural element count from normalized inventory."],
                    metadata={
                        **base_metadata,
                        "context_tags": _entity_context_tags(
                            element,
                            "structural",
                            element.element_type,
                            "count",
                        ),
                        "used_default_dimensions": bool(default_assumptions),
                    },
                ),
            )
        )

        length_quantity, length_formula, length_inputs, length_assumptions = _structural_length_payload(element)
        if length_quantity is not None and length_formula:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:length",
                    item_type="structural_length",
                    level_id=level.level_id,
                    unit="m",
                    quantity=length_quantity,
                    formula=length_formula,
                    inputs=_merge_inputs_with_description(
                        {
                            **length_inputs,
                            **base_inputs,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "length",
                            ),
                        },
                        struct_desc,
                    ),
                    assumptions=list(dict.fromkeys([*element.assumptions, *length_assumptions])),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural length from normalized inventory."],
                        metadata={
                            **base_metadata,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "length",
                            ),
                        },
                    ),
                )
            )

            if element.element_type != "other":
                takeoffs.append(
                    _make_takeoff(
                        item_key=f"{element.id}:{element.element_type}_length",
                        item_type=f"{element.element_type}_length",
                        level_id=level.level_id,
                        unit="m",
                        quantity=length_quantity,
                        formula=length_formula,
                        inputs=_merge_inputs_with_description(
                            {
                                **length_inputs,
                                **base_inputs,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "length",
                                ),
                            },
                            struct_desc,
                        ),
                        assumptions=list(dict.fromkeys([*element.assumptions, *length_assumptions])),
                        source_refs=list(element.source_refs),
                        trace=_trace_from_entities(
                            entities=[element],
                            steps=["Read typed structural length from normalized inventory."],
                            metadata={
                                **base_metadata,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "length",
                                ),
                            },
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
                    inputs=_merge_inputs_with_description(
                        {
                            "area_m2": element.area_m2,
                            **base_inputs,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "area",
                            ),
                        },
                        struct_desc,
                    ),
                    assumptions=list(element.assumptions),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural area from normalized inventory."],
                        metadata={
                            **base_metadata,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "area",
                            ),
                        },
                    ),
                )
            )

            if element.element_type != "other":
                takeoffs.append(
                    _make_takeoff(
                        item_key=f"{element.id}:{element.element_type}_area",
                        item_type=f"{element.element_type}_area",
                        level_id=level.level_id,
                        unit="m2",
                        quantity=element.area_m2,
                        formula="structural_element.area_m2",
                        inputs=_merge_inputs_with_description(
                            {
                                "area_m2": element.area_m2,
                                **base_inputs,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "area",
                                ),
                            },
                            struct_desc,
                        ),
                        assumptions=list(element.assumptions),
                        source_refs=list(element.source_refs),
                        trace=_trace_from_entities(
                            entities=[element],
                            steps=["Read typed structural area from normalized inventory."],
                            metadata={
                                **base_metadata,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "area",
                                ),
                            },
                        ),
                    )
                )

        volume_quantity, volume_formula, volume_inputs, volume_assumptions = _structural_volume_payload(
            element,
            length_quantity,
            length_formula,
            length_inputs,
        )
        if volume_quantity is not None and volume_formula:
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:volume",
                    item_type="structural_volume",
                    level_id=level.level_id,
                    unit="m3",
                    quantity=volume_quantity,
                    formula=volume_formula,
                    inputs=_merge_inputs_with_description(
                        {
                            **volume_inputs,
                            **base_inputs,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "volume",
                            ),
                        },
                        struct_desc,
                    ),
                    assumptions=list(dict.fromkeys([*element.assumptions, *volume_assumptions])),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Read structural volume from normalized inventory."],
                        metadata={
                            **base_metadata,
                            "context_tags": _entity_context_tags(
                                element,
                                "structural",
                                element.element_type,
                                "volume",
                            ),
                        },
                    ),
                )
            )

            if element.element_type != "other":
                takeoffs.append(
                    _make_takeoff(
                        item_key=f"{element.id}:{element.element_type}_volume",
                        item_type=f"{element.element_type}_volume",
                        level_id=level.level_id,
                        unit="m3",
                        quantity=volume_quantity,
                        formula=volume_formula,
                        inputs=_merge_inputs_with_description(
                            {
                                **volume_inputs,
                                **base_inputs,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "volume",
                                ),
                            },
                            struct_desc,
                        ),
                        assumptions=list(dict.fromkeys([*element.assumptions, *volume_assumptions])),
                        source_refs=list(element.source_refs),
                        trace=_trace_from_entities(
                            entities=[element],
                            steps=["Read typed structural volume from normalized inventory."],
                            metadata={
                                **base_metadata,
                                "context_tags": _entity_context_tags(
                                    element,
                                    "structural",
                                    element.element_type,
                                    "volume",
                                ),
                            },
                        ),
                    )
                )

        if (
            element.element_type in {"beam", "column", "slab"}
            and _structural_requires_reinforcement_hint(element)
            and volume_quantity is not None
        ):
            concrete_context_tags = _entity_context_tags(
                element,
                "structural",
                element.element_type,
                "concrete",
                "volume",
            )
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:concrete_volume",
                    item_type=f"{element.element_type}_concrete_volume",
                    level_id=level.level_id,
                    unit="m3",
                    quantity=volume_quantity,
                    formula=volume_formula or "structural_element.volume_m3",
                    inputs=_merge_inputs_with_description(
                        {
                            **(volume_inputs or {"volume_m3": volume_quantity}),
                            **base_inputs,
                            "context_tags": concrete_context_tags,
                        },
                        struct_desc,
                    ),
                    assumptions=list(
                        dict.fromkeys(
                            [
                                *element.assumptions,
                                *volume_assumptions,
                                f"{element.element_type.title()} {element.id} concrete volume was produced only because the inventory carried explicit concrete or reinforcement hints.",
                            ]
                        )
                    ),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Computed structural concrete volume from normalized inventory."],
                        metadata={
                            **base_metadata,
                            "context_tags": concrete_context_tags,
                        },
                    ),
                )
            )

        formwork_quantity, formwork_formula, formwork_inputs, formwork_assumptions = _structural_formwork_payload(
            element,
            length_quantity,
            length_inputs,
        )
        if formwork_quantity is not None and formwork_formula:
            formwork_context_tags = _entity_context_tags(
                element,
                "structural",
                element.element_type,
                "formwork",
                "hint",
            )
            takeoffs.append(
                _make_takeoff(
                    item_key=f"{element.id}:formwork_area_hint",
                    item_type=f"{element.element_type}_formwork_area_hint",
                    level_id=level.level_id,
                    unit="m2",
                    quantity=formwork_quantity,
                    formula=formwork_formula,
                    inputs=_merge_inputs_with_description(
                        {
                            **formwork_inputs,
                            **base_inputs,
                            "context_tags": formwork_context_tags,
                        },
                        struct_desc,
                    ),
                    assumptions=list(dict.fromkeys([*element.assumptions, *formwork_assumptions])),
                    source_refs=list(element.source_refs),
                    trace=_trace_from_entities(
                        entities=[element],
                        steps=["Computed structural formwork area hint from normalized inventory."],
                        metadata={
                            **base_metadata,
                            "context_tags": formwork_context_tags,
                        },
                    ),
                )
            )

        if element.element_type in {"beam", "column", "slab", "footing"}:
            effective_volume = volume_quantity
            if effective_volume is None and element.volume_m3 is not None:
                effective_volume = element.volume_m3
            if effective_volume is not None and effective_volume > 0:
                takeoffs.extend(
                    _rebar_takeoffs(
                        element,
                        level.level_id,
                        effective_volume,
                        volume_formula,
                        struct_desc=struct_desc,
                    )
                )

    return takeoffs


def quantify_inventory(
    levels: Iterable[LevelInventory],
    *,
    runner_source_discipline: str | None = None,
) -> list[QuantityTakeoff]:
    takeoffs: list[QuantityTakeoff] = []

    for level in levels:
        takeoffs.extend(_level_surface_takeoffs(level))
        takeoffs.extend(_wall_takeoffs(level))
        takeoffs.extend(_door_takeoffs(level))
        takeoffs.extend(_window_takeoffs(level))
        takeoffs.extend(_area_group_takeoffs(level))
        wet_area_fixtures = _wet_area_fixture_takeoffs(level)
        takeoffs.extend(wet_area_fixtures)
        takeoffs.extend(_stair_takeoffs(level))
        takeoffs.extend(
            _fixture_takeoffs(
                level,
                skip_sanitary_fixture_dupes=bool(wet_area_fixtures),
            )
        )
        takeoffs.extend(_structural_takeoffs(level))

    if runner_source_discipline:
        for takeoff in takeoffs:
            takeoff.trace.metadata["source_discipline"] = runner_source_discipline

    return takeoffs
