"""
Processor for Autodesk Model Derivative JSON payloads.

The active output of this module is a normalized fact set that downstream
modules can use to build inventory, quantify deterministically, and match
budget candidates. It intentionally stops before project-specific discipline
mapping or final budget generation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

# Autodesk Model Derivative returns all numeric property values as strings with
# unit suffixes, e.g. '0.075 m', '3.839 m', '0.124 m2', '180.000 deg'.
# This regex extracts the leading number so float() can parse it.
_NUMERIC_UNIT_RE = re.compile(r"^[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


def _load_collection(data: Any) -> list[dict[str, Any]]:
    collection: list[dict[str, Any]] = []

    if isinstance(data, dict):
        if "views" in data:
            for view in data.get("views", []):
                if isinstance(view, dict):
                    collection.extend(view.get("objects", []))
        elif "data" in data and isinstance(data["data"], dict):
            collection = list(data["data"].get("collection", []))
    elif isinstance(data, list):
        collection = list(data)

    return [item for item in collection if isinstance(item, dict)]


def _iter_property_maps(properties: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for section_name, section_value in properties.items():
        if isinstance(section_value, dict):
            yield section_name, section_value


def _find_property(properties: dict[str, Any], *needle_parts: str) -> Any:
    normalized_needles = tuple(part.lower() for part in needle_parts if part)

    for _, section in _iter_property_maps(properties):
        for key, value in section.items():
            normalized_key = key.strip().lower()
            if all(part in normalized_key for part in normalized_needles):
                return value
    return None


def _extract_layer(properties: dict[str, Any]) -> str:
    layer_value = _find_property(properties, "layer")
    return str(layer_value).strip() if layer_value else "UNKNOWN"


def _extract_entity_type(obj: dict[str, Any], properties: dict[str, Any]) -> str:
    general = properties.get("General", {})
    if isinstance(general, dict):
        for key, value in general.items():
            if key.strip().lower() == "name" and value:
                return str(value).strip()

    fallback_name = str(obj.get("name", "")).strip()
    return fallback_name or "Entity"


def _extract_handle(properties: dict[str, Any]) -> str:
    handle = _find_property(properties, "handle")
    return str(handle).strip() if handle else ""


def _extract_text_content(properties: dict[str, Any]) -> str:
    for key in ("Contents", "Text", "Value"):
        value = _find_property(properties, key)
        if value:
            return str(value).strip()
    return ""


def _extract_measurement(properties: dict[str, Any]) -> float | None:
    return _extract_numeric(properties, "Measurement", "Measurement Value")


def _extract_bbox(properties: dict[str, Any]) -> dict[str, Any]:
    minimum = _find_property(properties, "min")
    maximum = _find_property(properties, "max")
    if minimum is None and maximum is None:
        extents = _find_property(properties, "extents")
        if isinstance(extents, dict):
            return extents
        return {}
    return {"min": minimum, "max": maximum}


def _extract_block_name(obj: dict[str, Any]) -> str:
    name = str(obj.get("name", "")).strip()
    return re.sub(r"\s*\[[0-9A-Fa-f]+\]\s*$", "", name).strip()


def _extract_numeric(properties: dict[str, Any], *candidate_keys: str) -> float | None:
    for candidate_key in candidate_keys:
        value = _find_property(properties, candidate_key)
        if value is None:
            continue
        raw = str(value).replace(",", ".").strip()
        try:
            return float(raw)
        except ValueError:
            # Property value is a string with a unit suffix (e.g. '0.075 m',
            # '3.839 m', '180.000 deg'). Strip the suffix and retry.
            match = _NUMERIC_UNIT_RE.match(raw)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    pass
    return None


def _geometry_hint_record(
    obj: dict[str, Any],
    layer: str,
    entity_type: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    return {
        "layer": layer,
        "entity_type": entity_type,
        "name": str(obj.get("name", "")).strip(),
        "handle": _extract_handle(properties),
        "length": _extract_numeric(properties, "Length", "Perimeter"),
        "area": _extract_numeric(properties, "Area"),
        "radius": _extract_numeric(properties, "Radius"),
        "bbox": _extract_bbox(properties),
    }


def process_autodesk_json(json_path: str) -> dict[str, Any]:
    """
    Convert Autodesk JSON into normalized CAD facts.

    The returned payload is designed for inventory construction, not direct
    budget discipline assignment.
    """
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    collection = _load_collection(data)
    layer_summary: dict[str, dict[str, Any]] = {}
    layer_metrics: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "object_count": 0,
            "entity_types": Counter(),
            "sample_names": [],
            "handles": [],
        }
    )

    texts: list[dict[str, Any]] = []
    dimensions: list[dict[str, Any]] = []
    hatches: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    geometry_hints: list[dict[str, Any]] = []
    level_markers: list[dict[str, Any]] = []

    for obj in collection:
        properties = obj.get("properties", {})
        if not isinstance(properties, dict):
            continue

        layer = _extract_layer(properties)
        entity_type = _extract_entity_type(obj, properties)
        entity_type_normalized = entity_type.lower()

        metrics = layer_metrics[layer]
        metrics["object_count"] += 1
        metrics["entity_types"][entity_type] += 1

        sample_names = metrics["sample_names"]
        obj_name = str(obj.get("name", "")).strip()
        if obj_name and len(sample_names) < 5 and obj_name not in sample_names:
            sample_names.append(obj_name)

        handle = _extract_handle(properties)
        if handle and len(metrics["handles"]) < 5:
            metrics["handles"].append(handle)

        if "text" in entity_type_normalized:
            content = _extract_text_content(properties)
            text_record = {
                "layer": layer,
                "entity_type": entity_type,
                "handle": handle,
                "content": content,
                "bbox": _extract_bbox(properties),
            }
            texts.append(text_record)
            if re.search(r"\b(nivel|level|npt|elev|elevation)\b", content, flags=re.IGNORECASE):
                level_markers.append(text_record)

        elif "dimension" in entity_type_normalized:
            dimensions.append(
                {
                    "layer": layer,
                    "entity_type": entity_type,
                    "handle": handle,
                    "measurement": _extract_measurement(properties),
                    "text": _extract_text_content(properties),
                    "bbox": _extract_bbox(properties),
                }
            )

        elif "hatch" in entity_type_normalized:
            hatches.append(
                {
                    "layer": layer,
                    "entity_type": entity_type,
                    "handle": handle,
                    "area": _extract_numeric(properties, "Area"),
                    "pattern_name": _find_property(properties, "Pattern name") or "",
                    "fill_type": _find_property(properties, "Fill type") or "",
                    "bbox": _extract_bbox(properties),
                }
            )

        elif "block reference" in entity_type_normalized or "insert" in entity_type_normalized:
            blocks.append(
                {
                    "layer": layer,
                    "entity_type": entity_type,
                    "handle": handle,
                    "block_name": _extract_block_name(obj),
                    "bbox": _extract_bbox(properties),
                }
            )

        if entity_type_normalized in {
            "line",
            "polyline",
            "lwpolyline",
            "arc",
            "circle",
            "ellipse",
            "spline",
            "solid",
        }:
            geometry_hints.append(_geometry_hint_record(obj, layer, entity_type, properties))

    for layer, metrics in layer_metrics.items():
        layer_summary[layer] = {
            "object_count": metrics["object_count"],
            "entity_types": dict(metrics["entity_types"]),
            "sample_names": metrics["sample_names"],
            "handles": metrics["handles"],
        }

    block_frequency = Counter(
        block["block_name"] for block in blocks if block.get("block_name")
    ).most_common(25)

    dimension_scale_hints = [
        item
        for item in dimensions
        if isinstance(item.get("measurement"), (int, float))
    ][:25]

    return {
        "project": os.path.basename(json_path),
        "total_objects": len(collection),
        "cad_facts": {
            "layers": layer_summary,
            "texts": texts,
            "dimensions": dimensions,
            "hatches": hatches,
            "blocks": blocks,
            "geometry_hints": geometry_hints,
        },
        "inventory_hints": {
            "level_markers": level_markers[:25],
            "scale_dimensions": dimension_scale_hints,
            "block_frequency": [
                {"block_name": name, "count": count} for name, count in block_frequency
            ],
            "layer_names": sorted(layer_summary.keys()),
        },
    }


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize Autodesk JSON facts.")
    parser.add_argument("json_path", help="Path to the Autodesk JSON file")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to <input>.normalized.json",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    result = process_autodesk_json(args.json_path)
    output_path = args.output or f"{Path(args.json_path).stem}.normalized.json"

    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(result, out, indent=2, ensure_ascii=False)

    print(f"Normalized CAD facts written to {output_path}")
