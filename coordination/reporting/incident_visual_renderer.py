"""Full-plan base SVG + per-incident overlays for workflow visuals.

Architecture:
  base_full_plan.svg       = full base DWG plan, once per (base_dwg, level)
  {id}_overlay.svg         = severity cloud + short label on shared viewBox
  {id}_full_page.svg       = base + overlay composed
  {id}_zoom.svg            = optional inset around confirmed clash bounds

Rule:
  AABB / bbox helps locate and frame; overlap_geometry defines the real clash.
  candidate_pair / broad phase must NOT produce final overlays.
  confirmed_clash produces overlay artifacts.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coordination.core.clash import ClashIncident
from coordination.core.models_25d import Element25D
from coordination.reporting.tile_renderer import (
    BG_COLOR,
    NORMAL_STROKE_WIDTH,
    collect_elements_in_bbox,
)
from coordination.reporting.tile_renderer import (
    _cad_to_svg,
    _discipline_color,
    _element_polygon,
    _escape_svg,
    _filter_elements_for_file,
    _polygon_to_svg_points,
    _render_grid,
)

logger = logging.getLogger(__name__)

DEFAULT_WIDTH_PX = 800
DEFAULT_EXTENT_PADDING = 0.05
DEFAULT_ZOOM_PADDING = 0.35
FALLBACK_EXTENT_MM = 20_000.0
SHORT_LABEL_MAX_LEN = 90
VISUAL_PROVENANCE = "coordination_incident_visual_renderer"

INCIDENT_SEVERITY_COLORS = {
    "critical": "#DC2626",
    "high": "#EA580C",
    "medium": "#CA8A04",
    "low": "#2563EB",
}

_ARCH_MARKERS = ("ARQUITECTURA", "ARCH", "ARQ")
_STRUCT_MARKERS = ("ESTRUCTURA", "STRUC", "EST")
_CANDIDATE_PHASES = {"broad", "candidate", "candidate_pair", "aabb"}


@dataclass
class FullExtentResult:
    bounds: tuple[float, float, float, float]
    warnings: list[str] = field(default_factory=list)
    element_count: int = 0


@dataclass
class ViewBoxSpec:
    cad_bounds: tuple[float, float, float, float]
    width_px: int
    height_px: int
    scale: float

    @property
    def min_x(self) -> float:
        return self.cad_bounds[0]

    @property
    def min_y(self) -> float:
        return self.cad_bounds[1]

    @property
    def max_x(self) -> float:
        return self.cad_bounds[2]

    @property
    def max_y(self) -> float:
        return self.cad_bounds[3]


@dataclass
class BasePlanArtifact:
    cache_key: str
    base_dwg: str
    level_id: str
    viewbox: ViewBoxSpec
    svg_content: str
    relative_path: str
    metadata: dict[str, Any]


@dataclass
class IncidentVisualArtifact:
    incident_id: str
    incident_code: str
    base_plan_key: str
    overlay_path: str | None
    composed_path: str | None
    zoom_path: str | None
    base_full_plan_tile_path: str
    has_real_visual: bool
    visual_provenance: str
    visual_warnings: list[str]
    cad_viewbox: list[float]
    short_label: str
    severity: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _incident_dict(incident: ClashIncident | dict[str, Any]) -> dict[str, Any]:
    if isinstance(incident, dict):
        return incident
    if hasattr(incident, "model_dump"):
        return incident.model_dump()
    return {}


def is_confirmed_incident_visual(incident: ClashIncident | dict[str, Any]) -> bool:
    """Reject broad-phase / candidate-only payloads for overlay generation."""
    data = _incident_dict(incident)
    if data.get("candidate_only") is True:
        return False
    phase = str(data.get("phase") or data.get("detection_phase") or "").strip().lower()
    if phase in _CANDIDATE_PHASES:
        return False
    if data.get("confirmed") is False:
        return False

    rep = data.get("representative_conflict") or {}
    if not isinstance(rep, dict) or not rep:
        return False

    try:
        area = float(rep.get("plan_intersection_area_mm2") or 0.0)
    except (TypeError, ValueError):
        area = 0.0
    z_raw = rep.get("overlap_depth_z_mm")
    clash_type = rep.get("clash_type")
    has_z = z_raw is not None
    if area <= 0.0 and not has_z and not clash_type:
        return False
    return True


def _discipline_marker(discipline: str | None, markers: tuple[str, ...]) -> bool:
    text = str(discipline or "").strip().upper()
    return any(text.startswith(m) or m in text for m in markers)


def resolve_base_file_index(
    *,
    discipline_a: str | None,
    discipline_b: str | None,
    user_base_index: int | None = None,
) -> tuple[int, int]:
    if user_base_index in (0, 1):
        return user_base_index, 1 - user_base_index
    if _discipline_marker(discipline_a, _ARCH_MARKERS):
        return 0, 1
    if _discipline_marker(discipline_b, _ARCH_MARKERS):
        return 1, 0
    if _discipline_marker(discipline_a, _STRUCT_MARKERS):
        return 0, 1
    if _discipline_marker(discipline_b, _STRUCT_MARKERS):
        return 1, 0
    return 0, 1


def compute_dwg_full_extent(
    elements: list[Element25D],
    *,
    base_file: str,
    level_id: str | None = None,
    padding_factor: float = DEFAULT_EXTENT_PADDING,
) -> FullExtentResult:
    """Union of valid element AABBs for the base DWG (optionally filtered by level)."""
    warnings: list[str] = []
    base_elements = _filter_elements_for_file(elements, base_file)
    if level_id:
        from coordination.reporting.tile_renderer import _element_matches_level

        base_elements = [el for el in base_elements if _element_matches_level(el, level_id)]

    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    used = 0
    for element in base_elements:
        polygon = _element_polygon(element)
        if polygon is None:
            warnings.append(f"ignored_invalid_element:{element.id}")
            continue
        bx1, by1, bx2, by2 = polygon.bounds
        min_x = min(min_x, bx1)
        min_y = min(min_y, by1)
        max_x = max(max_x, bx2)
        max_y = max(max_y, by2)
        used += 1

    if used == 0 or not all(map(lambda v: abs(v) != float("inf"), [min_x, min_y, max_x, max_y])):
        warnings.append("full_extent_fallback_default")
        half = FALLBACK_EXTENT_MM / 2.0
        return FullExtentResult(bounds=(-half, -half, half, half), warnings=warnings, element_count=0)

    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    pad_x = width * padding_factor
    pad_y = height * padding_factor
    return FullExtentResult(
        bounds=(min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y),
        warnings=warnings,
        element_count=used,
    )


def viewbox_from_bounds(
    bounds: tuple[float, float, float, float],
    *,
    width_px: int = DEFAULT_WIDTH_PX,
) -> ViewBoxSpec:
    min_x, min_y, max_x, max_y = bounds
    cad_width = max(max_x - min_x, 1.0)
    cad_height = max(max_y - min_y, 1.0)
    scale = width_px / cad_width
    height_px = max(1, int(round(cad_height * scale)))
    return ViewBoxSpec(cad_bounds=bounds, width_px=width_px, height_px=height_px, scale=scale)


def _base_plan_cache_key(base_file: str, level_id: str) -> str:
    stem = Path(str(base_file or "plan")).stem or "plan"
    safe_level = re.sub(r"[^\w\-]+", "_", str(level_id or "default"))
    return f"{stem}_{safe_level}"


def _normalize_incident_code(incident_id: str) -> str:
    match = re.search(r"(\d+)", str(incident_id or ""))
    if match:
        return f"INC-{int(match.group(1)):03d}"
    text = str(incident_id or "").strip().upper()
    return text if text.startswith("INC-") else "INC-000"


def _layer_label(layer: str | None) -> str:
    if not layer:
        return "elemento"
    text = str(layer).strip().upper()
    mapping = {
        "MURO": "muro",
        "COLUMN": "columna",
        "COLUM": "columna",
        "VIGA": "viga",
        "TUB": "tubería",
        "SAN": "bajante sanitaria",
        "BAJ": "bajante",
        "MANIF": "manifold",
    }
    for key, label in mapping.items():
        if key in text:
            return label
    return text.split("_")[-1].lower() or "elemento"


def build_overlay_short_label(incident: ClashIncident | dict[str, Any]) -> str:
    data = _incident_dict(incident)
    code = _normalize_incident_code(str(data.get("incident_id") or ""))
    rep = data.get("representative_conflict") or {}
    layers = rep.get("raw_layers") or []
    layer_a = str(layers[0]) if len(layers) > 0 and layers[0] else None
    layer_b = str(layers[1]) if len(layers) > 1 and layers[1] else None
    la = _layer_label(layer_a)
    lb = _layer_label(layer_b)
    label_set = {la, lb}
    if "tubería" in label_set and label_set & {"muro", "columna", "viga"}:
        structural = next(x for x in ("muro", "columna", "viga") if x in label_set)
        problem = f"Tubería cruza {structural} estructural"
    elif la != "elemento" and lb != "elemento":
        problem = f"{la.capitalize()} interfiere con {lb}"
    else:
        problem = "Solape constructivo entre capas"
    label = f"{code}: {problem}. Coordinar desvío."
    if len(label) > SHORT_LABEL_MAX_LEN:
        return label[: SHORT_LABEL_MAX_LEN - 1].rstrip() + "…"
    return label


def _resolve_severity(incident: dict[str, Any]) -> str:
    for key in ("severity",):
        raw = incident.get(key)
        if raw:
            return str(raw).strip().lower()
    rep = incident.get("representative_conflict") or {}
    raw = rep.get("severity")
    if raw:
        return str(raw).strip().lower()
    return "medium"


def resolve_cloud_bounds(incident: ClashIncident | dict[str, Any]) -> tuple[tuple[float, float, float, float], str, list[str]]:
    """Return (bounds_mm, source, warnings) for overlay cloud geometry."""
    data = _incident_dict(incident)
    warnings: list[str] = []
    rep = data.get("representative_conflict") or {}

    overlap = data.get("overlap_geometry") or rep.get("overlap_geometry")
    if isinstance(overlap, dict):
        bounds = overlap.get("bounds") or overlap.get("bounds_mm")
        if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
            return tuple(float(v) for v in bounds), "overlap_geometry.bounds", warnings

    for key, source in (
        ("bbox_cad_base", "bbox_cad_base"),
        ("plan_intersection_bounds_mm", "confirmed_clash.bounds"),
    ):
        raw = data.get(key) if key != "plan_intersection_bounds_mm" else rep.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) == 4:
            return tuple(float(v) for v in raw), source, warnings

    plan_bounds = data.get("plan_bounds_mm")
    if isinstance(plan_bounds, (list, tuple)) and len(plan_bounds) == 4:
        warnings.append("cloud_bounds_fallback_plan_bounds")
        return tuple(float(v) for v in plan_bounds), "plan_bounds_mm", warnings

    centroid = data.get("plan_centroid_mm") or rep.get("plan_intersection_centroid_mm")
    if isinstance(centroid, (list, tuple)) and len(centroid) == 2:
        warnings.append("cloud_bounds_fallback_centroid")
        cx, cy = float(centroid[0]), float(centroid[1])
        half = 1000.0
        return (cx - half, cy - half, cx + half, cy + half), "centroid_fallback", warnings

    warnings.append("cloud_bounds_fallback_default")
    half = 1000.0
    return (-half, -half, half, half), "default", warnings


def _svg_open_tag(viewbox: ViewBoxSpec, *, transparent: bool = False) -> str:
    fill = "none" if transparent else BG_COLOR
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {viewbox.width_px} {viewbox.height_px}" '
        f'width="{viewbox.width_px}" height="{viewbox.height_px}" '
        f'data-cad-bounds="{",".join(f"{v:.3f}" for v in viewbox.cad_bounds)}">'
        f'<rect width="100%" height="100%" fill="{fill}"/>'
    )


def render_base_full_plan_svg(
    *,
    base_file: str,
    level_id: str,
    elements: list[Element25D],
    viewbox: ViewBoxSpec | None = None,
    extent: FullExtentResult | None = None,
) -> tuple[str, ViewBoxSpec, list[str]]:
    """Render the full base DWG plan once for a (base_file, level) pair."""
    extent = extent or compute_dwg_full_extent(elements, base_file=base_file, level_id=level_id)
    viewbox = viewbox or viewbox_from_bounds(extent.bounds)
    min_x, min_y, max_x, max_y = viewbox.cad_bounds
    scale = viewbox.scale

    plan_elements = _filter_elements_for_file(
        collect_elements_in_bbox(elements, viewbox.cad_bounds, level_id=level_id),
        base_file,
    )

    parts = [
        _svg_open_tag(viewbox),
        f'<metadata><dupla-visual base-dwg="{_escape_svg(Path(base_file).name)}" '
        f'level="{_escape_svg(level_id)}" visual-provenance="{VISUAL_PROVENANCE}" has-real-visual="true"/></metadata>',
        f'<g class="base-full-plan" data-base-dwg="{_escape_svg(base_file)}">',
    ]
    parts.extend(_render_grid(min_x, min_y, max_x, max_y, scale, viewbox.width_px, viewbox.height_px))

    for element in plan_elements:
        polygon = _element_polygon(element)
        if polygon is None:
            continue
        color = _discipline_color(element)
        points = _polygon_to_svg_points(list(polygon.exterior.coords), min_x, max_y, scale)
        parts.append(
            f'<polygon points="{points}" fill="{color}20" stroke="{color}" '
            f'stroke-width="{NORMAL_STROKE_WIDTH}" vector-effect="non-scaling-stroke"/>'
        )

    if not plan_elements:
        parts.append(
            f'<text x="{viewbox.width_px / 2:.1f}" y="{viewbox.height_px / 2:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="#6B7280">'
            "Sin geometría base en extent</text>"
        )

    parts.extend(["</g>", "</svg>"])
    warnings = list(extent.warnings)
    if not plan_elements:
        warnings.append("base_plan_no_elements_in_extent")
    return "\n".join(parts), viewbox, warnings


def render_incident_overlay_svg(
    incident: ClashIncident | dict[str, Any],
    *,
    viewbox: ViewBoxSpec,
    short_label: str | None = None,
    severity: str | None = None,
) -> tuple[str, list[str]]:
    """Render transparent overlay with severity cloud and short label."""
    if not is_confirmed_incident_visual(incident):
        raise ValueError("candidate-only incidents cannot produce overlay SVG")

    data = _incident_dict(incident)
    incident_code = _normalize_incident_code(str(data.get("incident_id") or ""))
    sev = (severity or _resolve_severity(data)).lower()
    color = INCIDENT_SEVERITY_COLORS.get(sev, INCIDENT_SEVERITY_COLORS["medium"])
    label = short_label or build_overlay_short_label(data)
    cloud_bounds, bounds_source, warnings = resolve_cloud_bounds(data)

    min_x, min_y, max_x, max_y = viewbox.cad_bounds
    scale = viewbox.scale
    bx1, by1, bx2, by2 = cloud_bounds
    pad = max(bx2 - bx1, by2 - by1) * 0.12 + 80.0
    mx1, my1, mx2, my2 = bx1 - pad, by1 - pad, bx2 + pad, by2 + pad
    top_left = _cad_to_svg(mx1, my2, min_x, max_y, scale)
    bottom_right = _cad_to_svg(mx2, my1, min_x, max_y, scale)
    width = max(bottom_right[0] - top_left[0], 12.0)
    height = max(bottom_right[1] - top_left[1], 12.0)

    tech_tl = _cad_to_svg(bx1, by2, min_x, max_y, scale)
    tech_br = _cad_to_svg(bx2, by1, min_x, max_y, scale)
    tech_w = max(tech_br[0] - tech_tl[0], 4.0)
    tech_h = max(tech_br[1] - tech_tl[1], 4.0)

    label_x = top_left[0]
    label_y = max(14.0, top_left[1] - 8.0)
    label_w = min(viewbox.width_px - 20, max(120, len(label) * 6.5 + 16))

    parts = [
        _svg_open_tag(viewbox, transparent=True),
        f'<metadata><dupla-visual incident="{_escape_svg(incident_code)}" '
        f'severity="{_escape_svg(sev)}" bounds-source="{_escape_svg(bounds_source)}" '
        f'has-real-visual="true"/></metadata>',
        f'<g class="incident-overlay" data-incident="{_escape_svg(incident_code)}">',
        f'<rect x="{tech_tl[0]:.2f}" y="{tech_tl[1]:.2f}" width="{tech_w:.2f}" height="{tech_h:.2f}" '
        f'fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.85"/>',
        f'<rect x="{top_left[0]:.2f}" y="{top_left[1]:.2f}" width="{width:.2f}" height="{height:.2f}" '
        f'fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="2.4" '
        f'rx="6" ry="6" vector-effect="non-scaling-stroke"/>',
        f'<rect x="{label_x:.2f}" y="{label_y - 16:.2f}" width="{label_w:.2f}" height="34" '
        f'fill="#111827" fill-opacity="0.88" rx="4"/>',
        f'<text x="{label_x + 8:.2f}" y="{label_y:.2f}" font-family="Segoe UI,Arial,sans-serif" '
        f'font-size="11" font-weight="700" fill="#FFFFFF">{_escape_svg(incident_code)}</text>',
        f'<text x="{label_x + 8:.2f}" y="{label_y + 14:.2f}" font-family="Segoe UI,Arial,sans-serif" '
        f'font-size="10" fill="#F9FAFB">{_escape_svg(label)}</text>',
        "</g>",
        "</svg>",
    ]
    return "\n".join(parts), warnings


def _svg_inner_content(svg_content: str) -> str:
    start = svg_content.find("<svg")
    if start < 0:
        return svg_content
    open_end = svg_content.find(">", start)
    close = svg_content.rfind("</svg>")
    if open_end < 0 or close < 0:
        return svg_content
    return svg_content[open_end + 1 : close].strip()


def compose_full_plan_incident_svg(base_svg: str, overlay_svg: str) -> str:
    """Compose base full-plan + overlay into one full-page SVG."""
    overlay_inner = _svg_inner_content(overlay_svg)
    marker = '<g class="base-full-plan"'
    if marker not in base_svg:
        return base_svg.replace("</svg>", f'<g class="incident-overlay-composed">{overlay_inner}</g>\n</svg>', 1)
    return base_svg.replace("</svg>", f"{overlay_inner}\n</svg>", 1)


def render_incident_zoom_svg(
    incident: ClashIncident | dict[str, Any],
    *,
    elements: list[Element25D],
    base_file: str,
    level_id: str,
    padding_factor: float = DEFAULT_ZOOM_PADDING,
    width_px: int = DEFAULT_WIDTH_PX,
) -> tuple[str, ViewBoxSpec, list[str]]:
    """Optional zoom/inset around confirmed clash bounds (secondary view)."""
    if not is_confirmed_incident_visual(incident):
        raise ValueError("candidate-only incidents cannot produce zoom SVG")

    cloud_bounds, _, warnings = resolve_cloud_bounds(incident)
    bx1, by1, bx2, by2 = cloud_bounds
    width = max(bx2 - bx1, 1.0)
    height = max(by2 - by1, 1.0)
    pad_x = width * padding_factor
    pad_y = height * padding_factor
    zoom_bounds = (bx1 - pad_x, by1 - pad_y, bx2 + pad_x, by2 + pad_y)
    viewbox = viewbox_from_bounds(zoom_bounds, width_px=width_px)
    zoom_extent = FullExtentResult(bounds=zoom_bounds, warnings=list(warnings))
    base_svg, _, base_warnings = render_base_full_plan_svg(
        base_file=base_file,
        level_id=level_id,
        elements=elements,
        viewbox=viewbox,
        extent=zoom_extent,
    )
    overlay_svg, overlay_warnings = render_incident_overlay_svg(incident, viewbox=viewbox)
    composed = compose_full_plan_incident_svg(base_svg, overlay_svg)
    return composed, viewbox, [*warnings, *overlay_warnings]


def _ensure_base_plan(
    *,
    cache: dict[str, BasePlanArtifact],
    base_file: str,
    level_id: str,
    elements: list[Element25D],
    output_dir: Path,
    width_px: int,
) -> BasePlanArtifact:
    key = _base_plan_cache_key(base_file, level_id)
    if key in cache:
        return cache[key]

    extent = compute_dwg_full_extent(elements, base_file=base_file, level_id=level_id)
    viewbox = viewbox_from_bounds(extent.bounds, width_px=width_px)
    svg_content, _, warnings = render_base_full_plan_svg(
        base_file=base_file,
        level_id=level_id,
        elements=elements,
        viewbox=viewbox,
        extent=extent,
    )
    rel_path = f"base_full/{key}.svg"
    out_path = output_dir / "tiles" / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg_content, encoding="utf-8")

    artifact = BasePlanArtifact(
        cache_key=key,
        base_dwg=base_file,
        level_id=level_id,
        viewbox=viewbox,
        svg_content=svg_content,
        relative_path=rel_path,
        metadata={
            "cad_viewbox": list(viewbox.cad_bounds),
            "has_real_visual": True,
            "visual_provenance": VISUAL_PROVENANCE,
            "visual_warnings": warnings,
            "base_dwg": Path(base_file).name,
            "level": level_id,
        },
    )
    cache[key] = artifact
    return artifact


def render_all_incident_visual_artifacts(
    incidents: list[ClashIncident | dict[str, Any]],
    *,
    all_elements: list[Element25D],
    output_dir: str | Path,
    width_px: int = DEFAULT_WIDTH_PX,
    incident_severities: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Render base plans, overlays, composed pages, zoom tiles; return manifest dict."""
    output_dir = Path(output_dir)
    base_cache: dict[str, BasePlanArtifact] = {}
    incident_entries: dict[str, dict[str, Any]] = {}
    skipped_candidates = 0

    for incident in incidents:
        data = _incident_dict(incident)
        incident_id = str(data.get("incident_id") or "").strip()
        if not incident_id:
            continue
        if not is_confirmed_incident_visual(data):
            skipped_candidates += 1
            continue

        rep = data.get("representative_conflict") or {}
        pair = data.get("file_pair") or ("", "")
        paths = list(pair) if isinstance(pair, (list, tuple)) else ["", ""]
        while len(paths) < 2:
            paths.append("")
        discipline_a = str(rep.get("discipline_a") or "") or None
        discipline_b = str(rep.get("discipline_b") or "") or None
        base_idx, _ = resolve_base_file_index(discipline_a=discipline_a, discipline_b=discipline_b)
        base_file = paths[base_idx]
        level_id = str(data.get("level_id") or "default")

        base_plan = _ensure_base_plan(
            cache=base_cache,
            base_file=base_file,
            level_id=level_id,
            elements=all_elements,
            output_dir=output_dir,
            width_px=width_px,
        )
        severity = (incident_severities or {}).get(incident_id) or _resolve_severity(data)
        short_label = build_overlay_short_label(data)

        overlay_svg, overlay_warnings = render_incident_overlay_svg(
            data,
            viewbox=base_plan.viewbox,
            short_label=short_label,
            severity=severity,
        )
        overlay_rel = f"overlays/{incident_id}_overlay.svg"
        (output_dir / "tiles" / overlay_rel).parent.mkdir(parents=True, exist_ok=True)
        (output_dir / "tiles" / overlay_rel).write_text(overlay_svg, encoding="utf-8")

        composed_svg = compose_full_plan_incident_svg(base_plan.svg_content, overlay_svg)
        composed_rel = f"composed/{incident_id}_full_page.svg"
        (output_dir / "tiles" / composed_rel).parent.mkdir(parents=True, exist_ok=True)
        (output_dir / "tiles" / composed_rel).write_text(composed_svg, encoding="utf-8")

        zoom_svg, _, zoom_warnings = render_incident_zoom_svg(
            data,
            elements=all_elements,
            base_file=base_file,
            level_id=level_id,
            width_px=width_px,
        )
        zoom_rel = f"zoom/{incident_id}_zoom.svg"
        (output_dir / "tiles" / zoom_rel).parent.mkdir(parents=True, exist_ok=True)
        (output_dir / "tiles" / zoom_rel).write_text(zoom_svg, encoding="utf-8")

        incident_code = _normalize_incident_code(incident_id)
        visual_warnings = [*overlay_warnings, *zoom_warnings]
        incident_entries[incident_id] = {
            "incident_id": incident_id,
            "incident_code": incident_code,
            "base_plan_key": base_plan.cache_key,
            "base_full_plan_tile_path": base_plan.relative_path,
            "incident_overlay_tile_path": overlay_rel,
            "composed_full_page_tile_path": composed_rel,
            "zoom_tile_path": zoom_rel,
            "has_real_visual": True,
            "visual_provenance": VISUAL_PROVENANCE,
            "visual_warnings": visual_warnings,
            "cad_viewbox": list(base_plan.viewbox.cad_bounds),
            "short_label": short_label,
            "severity": severity,
        }

    base_plans = {
        key: {
            "base_full_plan_tile_path": art.relative_path,
            "cad_viewbox": list(art.viewbox.cad_bounds),
            "has_real_visual": True,
            "visual_provenance": VISUAL_PROVENANCE,
            "visual_warnings": art.metadata.get("visual_warnings") or [],
            "base_dwg": art.metadata.get("base_dwg"),
            "level": art.level_id,
        }
        for key, art in base_cache.items()
    }

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "visual_provenance": VISUAL_PROVENANCE,
        "skipped_candidates": skipped_candidates,
        "base_plans": base_plans,
        "incidents": incident_entries,
        "broad_narrow_note": (
            "AABB/STRtree overlap = candidate_pair; "
            "exact XY intersection + Z overlap = confirmed_clash; "
            "only confirmed_clash creates overlay SVG."
        ),
    }
    manifest_path = output_dir / "incident_visual_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def load_incident_visual_manifest(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}
