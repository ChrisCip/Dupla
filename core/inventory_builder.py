"""
Inventory merge helpers for the active APS/JSON-first pipeline.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Iterable, Mapping, TypeVar

from core.schemas import (
    Door,
    Fixture,
    InventoryEntity,
    InventorySource,
    Kitchen,
    LevelInventory,
    Opening,
    Stair,
    StructuralElement,
    Wall,
    WetArea,
    Window,
    level_inventory_from_dict,
)

EntityT = TypeVar("EntityT", bound=InventoryEntity)

_WALL_TOKENS = ("wall", "muro")
_FLOOR_TOKENS = ("floor", "flor", "piso", "slab", "losa")
_CEILING_TOKENS = ("ceiling", "clng", "cielo")
_DOOR_TOKENS = ("door", "puert")
_WINDOW_TOKENS = ("window", "vent", "glaz")


def _contains_token(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in tokens)


def _unique_strings(*groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _merge_inputs(json_inputs: dict[str, Any], vision_inputs: dict[str, Any]) -> dict[str, Any]:
    if json_inputs and vision_inputs:
        return {"json": dict(json_inputs), "vision": dict(vision_inputs)}
    if json_inputs:
        return dict(json_inputs)
    if vision_inputs:
        return dict(vision_inputs)
    return {}


def _scalar_merge(
    field_name: str,
    json_value: Any,
    vision_value: Any,
    conflict_notes: list[str],
) -> Any:
    if json_value is None:
        return vision_value
    if vision_value is None:
        return json_value
    if json_value == vision_value:
        return json_value

    conflict_notes.append(
        f"Conflict on {field_name}: kept JSON value {json_value!r}, vision suggested {vision_value!r}."
    )
    return json_value


def _merge_entity(json_entity: EntityT, vision_entity: EntityT) -> EntityT:
    payload: dict[str, Any] = {}
    conflict_notes = _unique_strings(json_entity.conflict_notes, vision_entity.conflict_notes)

    for field_def in fields(json_entity):
        name = field_def.name
        json_value = getattr(json_entity, name)
        vision_value = getattr(vision_entity, name)

        if name == "id":
            payload[name] = json_entity.id
        elif name == "level_id":
            payload[name] = json_entity.level_id or vision_entity.level_id
        elif name == "source":
            payload[name] = "hybrid"
        elif name in {"source_refs", "assumptions", "evidence", "conflict_notes"}:
            payload[name] = _unique_strings(json_value, vision_value)
        elif name == "inputs":
            payload[name] = _merge_inputs(json_value, vision_value)
        elif isinstance(json_value, list) and isinstance(vision_value, list):
            payload[name] = _unique_strings(json_value, vision_value)
        elif isinstance(json_value, dict) and isinstance(vision_value, dict):
            payload[name] = _merge_inputs(json_value, vision_value)
        else:
            payload[name] = _scalar_merge(name, json_value, vision_value, conflict_notes)

    payload["conflict_notes"] = _unique_strings(conflict_notes)
    return type(json_entity)(**payload)


def _entity_signature(entity: InventoryEntity) -> tuple[Any, ...]:
    layer_tuple = tuple(sorted(getattr(entity, "source_layers", []) or []))
    return (
        entity.id,
        layer_tuple,
        getattr(entity, "type_hint", None),
        getattr(entity, "fixture_type", None),
        getattr(entity, "element_type", None),
        getattr(entity, "kind", None),
        getattr(entity, "wall_id", None),
    )


def _merge_entities(
    json_entities: list[EntityT],
    vision_entities: list[EntityT],
) -> list[EntityT]:
    merged: list[EntityT] = []
    unmatched_vision = vision_entities.copy()

    for json_entity in json_entities:
        match = next(
            (
                candidate
                for candidate in unmatched_vision
                if candidate.id == json_entity.id or _entity_signature(candidate) == _entity_signature(json_entity)
            ),
            None,
        )
        if match is None:
            merged.append(json_entity)
            continue

        unmatched_vision.remove(match)
        merged.append(_merge_entity(json_entity, match))

    merged.extend(unmatched_vision)
    return merged


def _sum_hatch_area(cad_facts: dict[str, Any], tokens: tuple[str, ...]) -> tuple[float | None, list[str]]:
    hatches = cad_facts.get("cad_facts", {}).get("hatches", [])
    total = 0.0
    refs: list[str] = []
    for hatch in hatches:
        layer = str(hatch.get("layer", ""))
        area = hatch.get("area")
        if area is None or not _contains_token(layer, tokens):
            continue
        total += float(area)
        refs.append(f"hatch:{hatch.get('handle') or layer}")

    return (total if refs else None, refs)


def _build_json_walls(level_id: str, cad_facts: dict[str, Any]) -> list[Wall]:
    geometry_hints = cad_facts.get("cad_facts", {}).get("geometry_hints", [])
    wall_lengths: dict[str, float] = {}
    wall_refs: dict[str, list[str]] = {}

    for hint in geometry_hints:
        layer = str(hint.get("layer", ""))
        if not _contains_token(layer, _WALL_TOKENS):
            continue

        length = hint.get("length")
        if length is None:
            continue

        wall_lengths[layer] = wall_lengths.get(layer, 0.0) + float(length)
        wall_refs.setdefault(layer, []).append(f"geometry:{hint.get('handle') or layer}")

    walls: list[Wall] = []
    for layer, length in wall_lengths.items():
        walls.append(
            Wall(
                id=f"json-wall-{layer.lower()}",
                level_id=level_id,
                source="json",
                source_layers=[layer],
                length_m=length,
                source_refs=_unique_strings(wall_refs.get(layer, [])),
                inputs={"json_layer": layer, "json_length_m": length},
                evidence=[f"Aggregated linework length from layer {layer}."],
            )
        )
    return walls


def _build_json_openings(
    level_id: str,
    entities: list[Door] | list[Window],
    opening_type: str,
) -> list[Opening]:
    openings: list[Opening] = []
    for entity in entities:
        openings.append(
            Opening(
                id=f"{entity.id}:opening",
                level_id=level_id,
                source=entity.source,
                wall_id=getattr(entity, "wall_id", None),
                opening_type=opening_type,
                count=entity.count,
                width_m=getattr(entity, "width_m", None),
                height_m=getattr(entity, "height_m", None),
                source_layers=list(getattr(entity, "source_layers", [])),
                source_refs=list(entity.source_refs),
                assumptions=list(entity.assumptions),
                inputs=dict(entity.inputs),
                conflict_notes=list(entity.conflict_notes),
                evidence=list(entity.evidence),
                related_door_id=entity.id if opening_type == "door" else None,
                related_window_id=entity.id if opening_type == "window" else None,
            )
        )
    return openings


def _build_json_doors_or_windows(
    *,
    level_id: str,
    blocks: list[dict[str, Any]],
    token_set: tuple[str, ...],
    cls: type[Door] | type[Window],
    item_prefix: str,
) -> list[Door] | list[Window]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for block in blocks:
        block_name = str(block.get("block_name", ""))
        layer = str(block.get("layer", ""))
        if not (_contains_token(block_name, token_set) or _contains_token(layer, token_set)):
            continue
        grouped.setdefault((layer, block_name), []).append(block)

    entities: list[Door] | list[Window] = []
    for index, ((layer, block_name), items) in enumerate(grouped.items(), start=1):
        payload = dict(
            id=f"{item_prefix}-{index}",
            level_id=level_id,
            source="json",
            source_layers=[layer],
            count=len(items),
            source_refs=[f"block:{item.get('handle') or block_name}" for item in items],
            inputs={"json_layer": layer, "block_name": block_name, "json_count": len(items)},
            evidence=[f"Counted block references matching '{block_name or layer}'."],
        )
        if cls is Door:
            entities.append(Door(**payload))
        else:
            entities.append(Window(**payload))
    return entities


def build_json_inventory(
    cad_facts: dict[str, Any],
    *,
    level_id: str,
    level_name: str,
) -> LevelInventory:
    blocks = cad_facts.get("cad_facts", {}).get("blocks", [])
    floor_area_m2, floor_refs = _sum_hatch_area(cad_facts, _FLOOR_TOKENS)
    ceiling_area_m2, ceiling_refs = _sum_hatch_area(cad_facts, _CEILING_TOKENS)
    doors = _build_json_doors_or_windows(
        level_id=level_id,
        blocks=blocks,
        token_set=_DOOR_TOKENS,
        cls=Door,
        item_prefix="json-door",
    )
    windows = _build_json_doors_or_windows(
        level_id=level_id,
        blocks=blocks,
        token_set=_WINDOW_TOKENS,
        cls=Window,
        item_prefix="json-window",
    )
    walls = _build_json_walls(level_id, cad_facts)

    return LevelInventory(
        level_id=level_id,
        level_name=level_name,
        source="json",
        source_refs=_unique_strings(floor_refs, ceiling_refs),
        inputs={"cad_summary": cad_facts.get("project")},
        floor_area_m2=floor_area_m2,
        ceiling_area_m2=ceiling_area_m2,
        walls=walls,
        doors=list(doors),
        windows=list(windows),
        openings=_build_json_openings(level_id, list(doors), "door")
        + _build_json_openings(level_id, list(windows), "window"),
        notes=["Built from normalized CAD facts."],
    )


def _merge_level_scalar(
    field_name: str,
    json_value: Any,
    vision_value: Any,
    conflict_notes: list[str],
) -> Any:
    return _scalar_merge(field_name, json_value, vision_value, conflict_notes)


def build_level_inventory(
    cad_facts: dict[str, Any],
    vision_inventory: LevelInventory | Mapping[str, Any] | None = None,
    *,
    level_id: str | None = None,
    level_name: str | None = None,
) -> LevelInventory:
    """
    Merge normalized CAD facts with vision-derived inventory.

    JSON-derived values are preferred when explicit, vision fills gaps, and any
    disagreement is preserved as conflict notes instead of being silently overwritten.
    """
    if isinstance(vision_inventory, LevelInventory):
        vision_level = vision_inventory
    elif vision_inventory is not None:
        vision_level = level_inventory_from_dict(vision_inventory, default_source="vision")
    else:
        vision_level = None

    resolved_level_id = level_id or (vision_level.level_id if vision_level else "level")
    resolved_level_name = level_name or (vision_level.level_name if vision_level else resolved_level_id)
    json_level = build_json_inventory(cad_facts, level_id=resolved_level_id, level_name=resolved_level_name)

    if vision_level is None:
        return json_level

    conflict_notes = _unique_strings(json_level.conflict_notes, vision_level.conflict_notes)
    floor_area_m2 = _merge_level_scalar(
        "floor_area_m2",
        json_level.floor_area_m2,
        vision_level.floor_area_m2,
        conflict_notes,
    )
    ceiling_area_m2 = _merge_level_scalar(
        "ceiling_area_m2",
        json_level.ceiling_area_m2,
        vision_level.ceiling_area_m2,
        conflict_notes,
    )

    return LevelInventory(
        level_id=resolved_level_id,
        level_name=resolved_level_name,
        source="hybrid",
        source_image=vision_level.source_image,
        source_view=vision_level.source_view,
        cad_hints=dict(vision_level.cad_hints),
        floor_area_m2=floor_area_m2,
        ceiling_area_m2=ceiling_area_m2,
        source_refs=_unique_strings(json_level.source_refs, vision_level.source_refs),
        assumptions=_unique_strings(json_level.assumptions, vision_level.assumptions),
        inputs=_merge_inputs(json_level.inputs, vision_level.inputs),
        conflict_notes=conflict_notes,
        walls=_merge_entities(json_level.walls, vision_level.walls),
        openings=_merge_entities(json_level.openings, vision_level.openings),
        doors=_merge_entities(json_level.doors, vision_level.doors),
        windows=_merge_entities(json_level.windows, vision_level.windows),
        wet_areas=_merge_entities(json_level.wet_areas, vision_level.wet_areas),
        kitchens=_merge_entities(json_level.kitchens, vision_level.kitchens),
        stairs=_merge_entities(json_level.stairs, vision_level.stairs),
        fixtures=_merge_entities(json_level.fixtures, vision_level.fixtures),
        structural_elements=_merge_entities(
            json_level.structural_elements,
            vision_level.structural_elements,
        ),
        notes=_unique_strings(json_level.notes, vision_level.notes),
        confidence=vision_level.confidence,
    )
