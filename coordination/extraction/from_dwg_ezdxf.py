"""Extract 2.5D footprints from local DWG/DXF files using ezdxf."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import units
from shapely.geometry import Polygon
from shapely.ops import unary_union

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.core.nasas_paths import translate_footprint
from coordination.core.tolerances import ClashTolerances
from coordination.extraction._geometry_builders import buffered_arc, buffered_linestring
from coordination.extraction.odafc_bridge import convert_to_dxf
from coordination.selection.layer_rules import (
    LayerRule,
    is_suppressed_role,
    load_project_layer_rules,
    resolve_layer_role,
)

logger = logging.getLogger("dupla.coordination.dwg")


def _looks_like_binary_dwg(path: Path) -> bool:
    try:
        with open(path, "rb") as handle:
            head = handle.read(8)
    except OSError:
        return False
    return head.startswith(b"AC10") or head.startswith(b"AC1")


def _insunits_to_mm_factor(doc: Any) -> float:
    try:
        return float(units.conversion_factor(doc.units, units.MM))
    except Exception:
        return 1.0


def _polyline_footprint_mm(entity: Any, factor: float) -> list[tuple[float, float]] | None:
    try:
        pts = [(p[0] * factor, p[1] * factor) for p in entity.get_points("xy")]
    except Exception:
        return None
    if len(pts) < 3:
        return None
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.area < 1.0:
        return None
    return [(float(x), float(y)) for x, y in poly.exterior.coords[:-1]]


def _circle_footprint_mm(entity: Any, factor: float) -> list[tuple[float, float]] | None:
    try:
        center = entity.dxf.center
        radius = float(entity.dxf.radius) * factor
        cx, cy = float(center.x) * factor, float(center.y) * factor
    except Exception:
        return None
    if radius < 1.0:
        return None
    steps = 24
    return [
        (cx + radius * math.cos(2 * math.pi * i / steps), cy + radius * math.sin(2 * math.pi * i / steps))
        for i in range(steps)
    ]


def _buffer_line(points: list[tuple[float, float]], *, width_mm: float) -> list[tuple[float, float]] | None:
    poly = buffered_linestring(points, width_mm=width_mm)
    if not poly:
        return None
    return poly


def _hatch_footprint_mm(entity: Any, factor: float) -> list[tuple[float, float]] | None:
    polygons = []
    try:
        paths = entity.paths.paths
    except Exception:
        return None
    for path in paths:
        vertices = []
        try:
            if hasattr(path, "vertices"):
                vertices = [(float(v[0]) * factor, float(v[1]) * factor) for v in path.vertices]
            elif hasattr(path, "edges"):
                for edge in path.edges:
                    if edge.EDGE_TYPE == "LineEdge":
                        vertices.append((float(edge.start[0]) * factor, float(edge.start[1]) * factor))
                        vertices.append((float(edge.end[0]) * factor, float(edge.end[1]) * factor))
        except Exception:
            continue
        if len(vertices) < 3:
            continue
        if vertices[0] != vertices[-1]:
            vertices.append(vertices[0])
        poly = Polygon(vertices)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if not poly.is_empty and poly.area > 1.0:
            polygons.append(poly)
    if not polygons:
        return None
    merged = unary_union(polygons)
    if merged.geom_type == "MultiPolygon":
        merged = max(merged.geoms, key=lambda item: item.area, default=merged)
    if merged.is_empty:
        return None
    return [(float(x), float(y)) for x, y in merged.exterior.coords[:-1]]


def _entity_footprint_mm(
    entity: Any,
    *,
    factor: float,
    tolerances: ClashTolerances,
) -> list[tuple[float, float]] | None:
    dxftype = entity.dxftype()
    if dxftype == "LWPOLYLINE":
        if entity.closed:
            return _polyline_footprint_mm(entity, factor)
        points = [(float(p[0]) * factor, float(p[1]) * factor) for p in entity.get_points("xy")]
        return _buffer_line(points, width_mm=tolerances.linear_buffer_mm)
    if dxftype == "POLYLINE":
        try:
            if entity.is_closed:
                return _polyline_footprint_mm(entity, factor)
            points = [(float(p[0]) * factor, float(p[1]) * factor) for p in entity.get_points("xy")]
            return _buffer_line(points, width_mm=tolerances.linear_buffer_mm)
        except Exception:
            return None
    if dxftype == "LINE":
        try:
            start = entity.dxf.start
            end = entity.dxf.end
            return _buffer_line(
                [(float(start.x) * factor, float(start.y) * factor), (float(end.x) * factor, float(end.y) * factor)],
                width_mm=tolerances.linear_buffer_mm,
            )
        except Exception:
            return None
    if dxftype == "ARC":
        try:
            center = entity.dxf.center
            radius = float(entity.dxf.radius) * factor
            start_deg = float(entity.dxf.start_angle or 0.0)
            end_deg = float(entity.dxf.end_angle or 0.0)
            if end_deg <= start_deg:
                end_deg += 360.0
            return buffered_arc(
                center_x=float(center.x) * factor,
                center_y=float(center.y) * factor,
                radius=radius,
                start_angle_rad=math.radians(start_deg),
                end_angle_rad=math.radians(end_deg),
                width_mm=tolerances.linear_buffer_mm,
                chord_error_mm=tolerances.tesselation_chord_error_mm,
            )
        except Exception:
            return None
    if dxftype == "SPLINE":
        try:
            points = [(float(v.x) * factor, float(v.y) * factor) for v in entity.flattening(0.1)]
            return _buffer_line(points, width_mm=tolerances.linear_buffer_mm)
        except Exception:
            return None
    if dxftype == "CIRCLE":
        return _circle_footprint_mm(entity, factor)
    if dxftype == "HATCH":
        return _hatch_footprint_mm(entity, factor)
    return None


def _iter_entities(modelspace: Any) -> list[Any]:
    out: list[Any] = []
    for entity in modelspace:
        if entity.dxftype() != "INSERT":
            out.append(entity)
            continue
        try:
            out.extend(list(entity.virtual_entities()))
        except Exception:
            out.append(entity)
    return out


def extract_elements_from_dwg(
    path: Path,
    discipline: Discipline,
    *,
    level_id: str,
    translation_mm: tuple[float, float] = (0.0, 0.0),
    min_area_mm2: float = 50_000.0,
    max_entities: int = 400,
    z_thickness_mm: float = 250.0,
    z_ref_mm: float | None = None,
    layer_rules: list[LayerRule] | None = None,
    tolerances: ClashTolerances | None = None,
    cache_root: Path | None = None,
) -> list[Element25D]:
    active_tolerances = tolerances or ClashTolerances(min_plan_area_mm2=min_area_mm2)
    active_layer_rules = layer_rules if layer_rules is not None else load_project_layer_rules(project_name="default")
    cad_kind = path.suffix.lower().lstrip(".") or "cad"
    source_path = path
    if path.suffix.lower() == ".dwg" and _looks_like_binary_dwg(path):
        converted = convert_to_dxf(path, cache_dir=cache_root)
        if converted is None:
            logger.warning("Omitiendo DWG binario %s (ODA File Converter no disponible).", path.name)
            return []
        source_path = converted
        cad_kind = "dwg_odafc"

    try:
        doc = ezdxf.readfile(str(source_path))
    except Exception:
        try:
            from ezdxf import recover

            doc, auditor = recover.readfile(str(source_path))
            if auditor.has_errors:
                logger.warning("DXF %s: auditor con errores o advertencias", source_path.name)
        except Exception as exc:
            logger.warning("No se pudo leer %s: %s", source_path, exc)
            return []

    factor = _insunits_to_mm_factor(doc)
    modelspace = doc.modelspace()
    candidates: list[tuple[float, Element25D]] = []
    z0 = 0.0 if z_ref_mm is None else float(z_ref_mm)

    idx = 0
    for entity in _iter_entities(modelspace):
        dxftype = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "") or "0"
        layer_resolution = resolve_layer_role(layer, discipline, rules=active_layer_rules)
        footprint = _entity_footprint_mm(entity, factor=factor, tolerances=active_tolerances)

        if not footprint:
            continue
        footprint = translate_footprint(footprint, translation_mm[0], translation_mm[1])
        polygon = Polygon(footprint if footprint[0] == footprint[-1] else footprint + [footprint[0]])
        area = float(polygon.area)
        if area < max(min_area_mm2, active_tolerances.min_plan_area_mm2):
            continue

        elevation = z0
        try:
            elevation = float(getattr(entity.dxf, "elevation", 0.0)) * factor + z0
        except Exception:
            pass

        candidates.append(
            (
                area,
                Element25D(
                    id=f"dwg_{path.stem}_{idx}_{layer.replace('|', '_')}",
                    source_ref=f"{path.as_posix()}|{layer}|{dxftype}",
                    discipline=discipline,
                    category=f"{dxftype}:{layer}",
                    layer_raw=layer,
                    footprint_coords_mm=footprint,
                    z_data=ZInterval(
                        level_id=level_id,
                        z_ref_raw_mm=elevation,
                        thickness_mm=z_thickness_mm,
                        reference_point="bottom",
                    ),
                    metadata={
                        "file": path.name,
                        "layer": layer,
                        "raw_layer": layer,
                        "normalized_layer": layer_resolution.normalized_layer,
                        "canonical_role": layer_resolution.canonical_role.value,
                        "layer_rule_confidence": layer_resolution.rule_confidence,
                        "layer_rule_reason": layer_resolution.rule_reason,
                        "area_mm2": area,
                        "source": "cad_ezdxf",
                        "geometry_source": f"{cad_kind}_ezdxf",
                        "geometry_quality": "high",
                        "geometry_role": (
                            "suppressed"
                            if is_suppressed_role(
                                layer_resolution.canonical_role,
                                confidence=layer_resolution.rule_confidence,
                            )
                            else "primary"
                        ),
                        "level_assignment_source": "default_level",
                        "sheet_or_view_name": path.stem,
                    },
                ),
            )
        )
        idx += 1

    candidates.sort(key=lambda item: -item[0])
    return [element for _, element in candidates[:max_entities]]
