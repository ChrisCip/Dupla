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
_BEAM_TOKENS = ("beam", "viga")
_COLUMN_TOKENS = ("column", "colum", "columna", "pillar", "pil")
_SLAB_TOKENS = ("slab", "losa")
_FOOTING_TOKENS = ("footing", "zapata", "foundation")
_STRUCTURAL_TOKENS = ("struct", "estruct", "load", "bearing", "portant")
_INTERIOR_TOKENS = ("interior", "int", "inside")
_EXTERIOR_TOKENS = ("exterior", "ext", "facade", "fachada", "outside")
_FINISH_TOKENS = ("finish", "acab", "paint", "tile", "rev")
_CONCRETE_TOKENS = ("concrete", "conc", "horm", "rc", "reinforced concrete")
_STEEL_TOKENS = ("steel", "acero", "metal", "stl")
_MASONRY_TOKENS = ("masonry", "block", "brick", "cmu", "ladr", "mamp")
_DRYWALL_TOKENS = ("drywall", "gypsum", "tablaroca", "yeso")
_WOOD_TOKENS = ("wood", "madera", "timber")

_SPACE_TYPE_TOKENS: dict[str, tuple[str, ...]] = {
    "bathroom": ("bath", "bano", "baño", "wc", "toilet"),
    "kitchen": ("kitchen", "cocina"),
    "bedroom": ("bedroom", "dorm", "habit"),
    "living_room": ("living", "estar", "sala"),
    "corridor": ("corridor", "hall", "pasillo", "circulation"),
    "laundry": ("laundry", "lavander", "lavado"),
    "office": ("office", "oficina"),
    "stair": ("stair", "escal"),
}


def _contains_token(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in tokens)


def _joined_hint_text(*values: Any) -> str:
    return " ".join(str(value).strip() for value in values if value).lower()


def _infer_material_hint(*values: Any) -> str | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _CONCRETE_TOKENS):
        return "concrete"
    if _contains_token(hint_text, _STEEL_TOKENS):
        return "steel"
    if _contains_token(hint_text, _MASONRY_TOKENS):
        return "masonry"
    if _contains_token(hint_text, _DRYWALL_TOKENS):
        return "drywall"
    if _contains_token(hint_text, _WOOD_TOKENS):
        return "wood"
    return None


def _infer_wall_system_hint(*values: Any) -> str | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _DRYWALL_TOKENS):
        return "drywall_partition"
    if _contains_token(hint_text, _MASONRY_TOKENS):
        return "masonry_wall"
    if _contains_token(hint_text, _CONCRETE_TOKENS):
        return "concrete_wall"
    if _contains_token(hint_text, _STEEL_TOKENS) and _contains_token(hint_text, _WALL_TOKENS):
        return "steel_stud_wall"
    return None


def _infer_interior_exterior_hint(*values: Any) -> str | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _INTERIOR_TOKENS):
        return "interior"
    if _contains_token(hint_text, _EXTERIOR_TOKENS):
        return "exterior"
    return None


def _infer_finish_required(*values: Any) -> bool | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _FINISH_TOKENS):
        return True
    return None


def _infer_load_bearing_hint(*values: Any) -> bool | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _STRUCTURAL_TOKENS):
        return True
    return None


def _infer_reinforcement_hint(*values: Any) -> str | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if "rebar" in hint_text or "armad" in hint_text or "reinf" in hint_text or "rc" in hint_text:
        return "reinforced"
    return None


def _infer_concrete_grade_hint(*values: Any) -> str | None:
    import re

    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None

    patterns = (
        r"\b(?:h|c)\s*[-/]?\s*(\d{2,3}(?:/\d{2})?)\b",
        r"\bf[' ]?c\s*[-/]?\s*(\d{2,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, hint_text, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper().replace(" ", "")
    return None


def _infer_steel_grade_hint(*values: Any) -> str | None:
    import re

    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None

    patterns = (
        r"\bfy\s*[-/]?\s*(\d{3,4})\b",
        r"\ba\s*(36|572|992)\b",
        r"\bs\s*(275|355)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, hint_text, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper().replace(" ", "")
    return None


def _infer_structural_element_type(*values: Any) -> str | None:
    hint_text = _joined_hint_text(*values)
    if not hint_text:
        return None
    if _contains_token(hint_text, _BEAM_TOKENS):
        return "beam"
    if _contains_token(hint_text, _COLUMN_TOKENS):
        return "column"
    if _contains_token(hint_text, _SLAB_TOKENS):
        return "slab"
    if _contains_token(hint_text, _FOOTING_TOKENS):
        return "footing"
    if _contains_token(hint_text, _WALL_TOKENS) and _contains_token(hint_text, _STRUCTURAL_TOKENS):
        return "wall"
    return None


def _extract_space_types(cad_facts: dict[str, Any]) -> list[str]:
    texts = cad_facts.get("cad_facts", {}).get("texts", [])
    detected: list[str] = []
    for text in texts:
        content = str(text.get("content", ""))
        for space_type, tokens in _SPACE_TYPE_TOKENS.items():
            if _contains_token(content, tokens):
                detected.append(space_type)
    return _unique_strings(detected)


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
        material_hint = _infer_material_hint(layer)
        wall_system = _infer_wall_system_hint(layer)
        interior_exterior_hint = _infer_interior_exterior_hint(layer)
        finish_required = _infer_finish_required(layer)
        structural_hint = _infer_load_bearing_hint(layer)
        walls.append(
            Wall(
                id=f"json-wall-{layer.lower()}",
                level_id=level_id,
                source="json",
                source_layers=[layer],
                length_m=length,
                material_hint=material_hint,
                wall_system=wall_system,
                interior_exterior_hint=interior_exterior_hint,
                finish_required=finish_required,
                structural=structural_hint,
                source_refs=_unique_strings(wall_refs.get(layer, [])),
                inputs={
                    "json_layer": layer,
                    "json_length_m": length,
                },
                evidence=[
                    f"Aggregated linework length from layer {layer}.",
                    *(
                        [f"Detected wall system hint '{wall_system}' from layer {layer}."]
                        if wall_system
                        else []
                    ),
                    *(
                        [f"Detected wall material hint '{material_hint}' from layer {layer}."]
                        if material_hint
                        else []
                    ),
                ],
            )
        )
    return walls


def _build_json_structural_elements(level_id: str, cad_facts: dict[str, Any]) -> list[StructuralElement]:
    geometry_hints = cad_facts.get("cad_facts", {}).get("geometry_hints", [])
    blocks = cad_facts.get("cad_facts", {}).get("blocks", [])
    hatches = cad_facts.get("cad_facts", {}).get("hatches", [])

    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    def ensure_group(element_type: str, layer: str, name_hint: str = "") -> dict[str, Any]:
        key = (element_type, layer)
        if key not in grouped:
            hint_text = _joined_hint_text(layer, name_hint)
            grouped[key] = {
                "id": f"json-{element_type}-{layer.lower()}",
                "level_id": level_id,
                "source": "json",
                "element_type": element_type,
                "count": 0,
                "length_m": None,
                "area_m2": None,
                "volume_m3": None,
                "material_hint": _infer_material_hint(hint_text),
                "orientation": "vertical" if element_type == "column" else "horizontal",
                "load_bearing": True if element_type in {"beam", "column", "slab", "footing"} else _infer_load_bearing_hint(hint_text),
                "reinforcement_hint": _infer_reinforcement_hint(hint_text),
                "concrete_grade_hint": _infer_concrete_grade_hint(hint_text),
                "steel_grade_hint": _infer_steel_grade_hint(hint_text),
                "host_level": level_id,
                "adjacent_elements": [],
                "source_refs": [],
                "assumptions": [],
                "inputs": {"json_layer": layer, "json_name_hints": []},
                "conflict_notes": [],
                "evidence": [],
            }
        if name_hint and name_hint not in grouped[key]["inputs"]["json_name_hints"]:
            grouped[key]["inputs"]["json_name_hints"].append(name_hint)
        return grouped[key]

    def add_numeric(group: dict[str, Any], field_name: str, value: float | None) -> None:
        if value is None:
            return
        existing = group.get(field_name)
        group[field_name] = float(value) if existing is None else float(existing) + float(value)

    for hint in geometry_hints:
        layer = str(hint.get("layer", ""))
        name_hint = str(hint.get("name", ""))
        entity_type = _infer_structural_element_type(layer, name_hint)
        if not entity_type:
            continue

        group = ensure_group(entity_type, layer, name_hint)
        add_numeric(group, "length_m", hint.get("length"))
        add_numeric(group, "area_m2", hint.get("area"))
        if hint.get("handle"):
            group["source_refs"].append(f"geometry:{hint['handle']}")
        group["evidence"].append(
            f"Aggregated geometry hint for structural {entity_type} from layer {layer}."
        )

    for block in blocks:
        layer = str(block.get("layer", ""))
        block_name = str(block.get("block_name", ""))
        element_type = _infer_structural_element_type(layer, block_name)
        if not element_type:
            continue

        group = ensure_group(element_type, layer, block_name)
        group["count"] += 1
        if block.get("handle"):
            group["source_refs"].append(f"block:{block['handle']}")
        group["evidence"].append(
            f"Counted explicit structural block '{block_name}' on layer {layer}."
        )

    for hatch in hatches:
        layer = str(hatch.get("layer", ""))
        pattern_name = str(hatch.get("pattern_name", ""))
        element_type = _infer_structural_element_type(layer, pattern_name)
        if element_type != "slab":
            continue

        group = ensure_group(element_type, layer, pattern_name)
        add_numeric(group, "area_m2", hatch.get("area"))
        if hatch.get("handle"):
            group["source_refs"].append(f"hatch:{hatch['handle']}")
        group["evidence"].append(
            f"Aggregated slab hatch area from layer {layer}."
        )

    structural_elements: list[StructuralElement] = []
    for _, payload in sorted(grouped.items(), key=lambda item: item[0]):
        payload["count"] = max(int(payload["count"]), 1)
        payload["source_refs"] = _unique_strings(payload["source_refs"])
        payload["evidence"] = _unique_strings(payload["evidence"])
        structural_elements.append(StructuralElement(**payload))

    return structural_elements


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
    structural_elements = _build_json_structural_elements(level_id, cad_facts)
    space_types = _extract_space_types(cad_facts)
    structural_types = _unique_strings(
        element.element_type for element in structural_elements if element.element_type
    )
    material_hints = _unique_strings(
        [wall.material_hint for wall in walls if wall.material_hint],
        [element.material_hint for element in structural_elements if element.material_hint],
    )

    return LevelInventory(
        level_id=level_id,
        level_name=level_name,
        source="json",
        cad_hints={
            "material_hints": material_hints,
            "structural_types": structural_types,
            "space_types": space_types,
        },
        source_refs=_unique_strings(
            floor_refs,
            ceiling_refs,
            *(element.source_refs for element in structural_elements),
        ),
        space_types=space_types,
        system_notes=[
            *(
                [
                    "CAD facts suggest probable material systems: "
                    + ", ".join(material_hints)
                    + "."
                ]
                if material_hints
                else []
            )
        ],
        structural_notes=[
            *(
                [
                    "Explicit structural CAD hints detected for: "
                    + ", ".join(structural_types)
                    + "."
                ]
                if structural_types
                else []
            )
        ],
        inputs={"cad_summary": cad_facts.get("project")},
        floor_area_m2=floor_area_m2,
        ceiling_area_m2=ceiling_area_m2,
        walls=walls,
        doors=list(doors),
        windows=list(windows),
        structural_elements=structural_elements,
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
        cad_hints=_merge_inputs(json_level.cad_hints, vision_level.cad_hints),
        floor_area_m2=floor_area_m2,
        ceiling_area_m2=ceiling_area_m2,
        space_types=_unique_strings(json_level.space_types, vision_level.space_types),
        system_notes=_unique_strings(json_level.system_notes, vision_level.system_notes),
        structural_notes=_unique_strings(json_level.structural_notes, vision_level.structural_notes),
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
