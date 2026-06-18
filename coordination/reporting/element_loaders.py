"""Load Element25D lists from in-memory runs or elements_by_dwg.json artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.semantic.semantic_elements import SemanticElement25D

logger = logging.getLogger(__name__)

_DISCIPLINE_MAP = {
    "ARQUITECTURA": Discipline.ARCH,
    "ESTRUCTURA": Discipline.STRUC,
    "FONTANERIA": Discipline.MEP_PLUMBING,
    "CLIMATIZACION": Discipline.MEP_HVAC,
    "ELECTRICIDAD": Discipline.MEP_ELEC,
}


def _discipline_from_value(value: str) -> Discipline:
    key = str(value or "").strip().upper()
    return _DISCIPLINE_MAP.get(key, Discipline.ARCH)


def _footprint_from_bbox(bbox: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    x1, y1, x2, y2 = (float(v) for v in bbox)
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


_SEMANTIC_FIELDS = set(SemanticElement25D.model_fields.keys())


def _coerce_bbox(raw: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = raw.get("bbox_mm") or raw.get("bbox")
    if not bbox or len(bbox) < 4:
        return None
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def _coerce_footprint(raw: dict[str, Any]) -> list[tuple[float, float]]:
    coords = raw.get("footprint_coords_mm") or []
    if len(coords) >= 3:
        return [(float(x), float(y)) for x, y in coords]
    bbox = _coerce_bbox(raw)
    if bbox is not None:
        return _footprint_from_bbox(bbox)
    return []


def semantic_element_from_export_dict(raw: dict[str, Any]) -> SemanticElement25D | None:
    """Parse export JSON row tolerating legacy/extra keys."""
    if not raw:
        return None
    filtered = {key: raw[key] for key in _SEMANTIC_FIELDS if key in raw}
    if "semantic_element_id" not in filtered:
        filtered["semantic_element_id"] = str(
            raw.get("semantic_element_id") or raw.get("element_id") or raw.get("id") or ""
        )
    if "source_element_id" not in filtered:
        filtered["source_element_id"] = str(raw.get("source_element_id") or raw.get("source_entity_id") or "")
    if "source_file" not in filtered:
        filtered["source_file"] = str(raw.get("source_file") or "")
    if "file_name" not in filtered:
        filtered["file_name"] = str(raw.get("file_name") or Path(filtered.get("source_file", "")).name)
    if "discipline" not in filtered:
        filtered["discipline"] = str(raw.get("discipline") or "ARQUITECTURA")
    if "level_id" not in filtered:
        filtered["level_id"] = str(raw.get("level_id") or "NPT_P1")
    if "layer" not in filtered:
        filtered["layer"] = str(raw.get("layer") or "0")
    if "element_type" not in filtered:
        filtered["element_type"] = str(raw.get("element_type") or "unknown")
    bbox = _coerce_bbox(raw)
    if bbox is not None:
        filtered["bbox_mm"] = bbox
    footprint = _coerce_footprint(raw)
    if footprint:
        filtered["footprint_coords_mm"] = footprint
    if not filtered.get("semantic_element_id") or not filtered.get("source_file"):
        return None
    return SemanticElement25D.model_validate(filtered)


def semantic_to_element25d(semantic: SemanticElement25D) -> Element25D:
    """Convert a semantic export row to Element25D for tile rendering."""
    layer = str(semantic.layer or "0")
    entity_type = str(semantic.entity_type or "unknown")
    handle = str(semantic.cad_handle or semantic.source_element_id or semantic.semantic_element_id)
    source_file = str(semantic.source_file or semantic.file_name)
    footprint = list(semantic.footprint_coords_mm or [])
    if len(footprint) < 3 and semantic.bbox_mm is not None:
        footprint = _footprint_from_bbox(semantic.bbox_mm)
    level_id = str(semantic.level_id or "NPT_P1")
    return Element25D(
        id=str(semantic.semantic_element_id or semantic.source_element_id),
        source_ref=f"{source_file}|{layer}|{entity_type}|{handle}",
        discipline=_discipline_from_value(semantic.discipline),
        category=str(semantic.metadata.get("category") or entity_type or "unknown"),
        footprint_coords_mm=footprint,
        z_data=ZInterval(
            level_id=level_id,
            z_ref_raw_mm=0.0,
            thickness_mm=3000.0,
            measurement_uncertainty_mm=0.0,
        ),
        metadata={
            "level_id": level_id,
            "file_level_id": f"{source_file}|{level_id}",
            "source_file": source_file,
            "file_name": semantic.file_name,
            "layer": layer,
            "cad_handle": handle,
            "geometry_source": semantic.geometry_source,
            "geometry_role": semantic.geometry_role,
        },
    )


def _load_from_payload(payload: dict[str, Any]) -> list[Element25D]:
    out: list[Element25D] = []
    for file_entry in payload.get("files") or []:
        for raw in file_entry.get("elements") or []:
            if not isinstance(raw, dict):
                continue
            try:
                out.append(Element25D.model_validate(raw))
                continue
            except Exception:
                pass
            semantic = semantic_element_from_export_dict(raw)
            if semantic is not None:
                out.append(semantic_to_element25d(semantic))
                continue
            try:
                semantic = SemanticElement25D.model_validate(raw)
                out.append(semantic_to_element25d(semantic))
            except Exception as exc:
                logger.debug("Skipping element row: %s", exc)
    return out


def load_elements_for_visual_reporting(
    elements_by_dwg_path: Path | None = None,
    *,
    in_memory: list[Element25D] | None = None,
) -> list[Element25D]:
    """Load elements for human PDF visual panels."""
    if in_memory:
        return list(in_memory)
    if elements_by_dwg_path is None or not elements_by_dwg_path.is_file():
        return []
    payload = json.loads(elements_by_dwg_path.read_text(encoding="utf-8"))
    elements = _load_from_payload(payload)
    logger.info("Loaded %d elements from %s", len(elements), elements_by_dwg_path)
    return elements
