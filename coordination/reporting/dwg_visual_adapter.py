"""DWG visual source adapter for report generation.

Discovers real sidecar exports (PNG/PDF plots) when present, falls back to
extracted footprint geometry SVG (not a DWG plot), and never fabricates plan
imagery or marker positions without a known coordinate transform.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from coordination.core.clash import ClashConflict, ClashIncident
from coordination.core.models_25d import Element25D
from coordination.reporting.dwg_identity import dwg_basename_key
from coordination.reporting.tile_renderer import (
    compute_tile_bbox,
    render_dwg_panel_svg,
    _incident_conflicts,
    _render_clash_marker,
)

logger = logging.getLogger(__name__)

RUN_NO_VISUAL_WARNING = "No DWG visual preview available for this run."
COORD_TRANSFORM_UNAVAILABLE = (
    "Coordinate-to-image transform unavailable; use AutoCAD Z W command for exact location."
)
PLACEHOLDER_PANEL_TITLE = "Vista de plano no disponible en esta corrida"

_SIDECAR_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".pdf")
_SIDECAR_NAME_PATTERNS = ("", "_preview", "_plot", "_export")


class VisualSourceKind(str, Enum):
    NONE = "none"
    SIDECAR_RASTER = "sidecar_raster"
    SIDECAR_PDF = "sidecar_pdf"
    FOOTPRINT_GEOMETRY = "footprint_geometry"
    RUN_TILE = "run_tile"


class LocalizationStatus(str, Enum):
    EXACT = "exact"
    UNAVAILABLE = "unavailable"
    FULL_IMAGE_ONLY = "full_image_only"


@dataclass(frozen=True)
class VisualSource:
    kind: VisualSourceKind
    file_path: Path
    image_path: Path | None = None
    cad_bounds_mm: tuple[float, float, float, float] | None = None
    width_px: int | None = None
    height_px: int | None = None
    localization: LocalizationStatus = LocalizationStatus.UNAVAILABLE
    note: str | None = None


@dataclass
class VisualPanel:
    panel_id: str
    file_label: str
    svg_content: str
    source_kind: VisualSourceKind
    localization: LocalizationStatus
    has_geometry: bool = False
    warning: str | None = None
    bbox_cad_mm: tuple[float, float, float, float] | None = None


class DwgExportBackend(Protocol):
    """Extension point for future AutoCAD / ODA plot export."""

    def export_plot_png(self, dwg_path: Path, output_path: Path) -> Path | None:
        ...


_EXPORT_BACKENDS: list[DwgExportBackend] = []


def register_dwg_export_backend(backend: DwgExportBackend) -> None:
    _EXPORT_BACKENDS.append(backend)


def _resolve_dwg_path(file_id_or_name: str, *, search_roots: list[Path] | None = None) -> Path | None:
    raw = str(file_id_or_name or "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_file():
        return candidate.resolve()
    name = candidate.name
    basename_key = dwg_basename_key(raw)
    roots = search_roots or []
    if candidate.parent != Path("."):
        roots = [candidate.parent, *roots]
    seen: set[Path] = set()
    for root in roots:
        root = Path(root)
        if not root.is_dir() or root in seen:
            continue
        seen.add(root)
        for hit in (root / name, root / f"{Path(name).stem}.dwg"):
            if hit.is_file():
                return hit.resolve()
        try:
            for dwg in root.rglob("*.dwg"):
                if dwg_basename_key(dwg.name) == basename_key:
                    return dwg.resolve()
        except OSError:
            continue
    return None


def _discover_sidecar_image(dwg_path: Path) -> Path | None:
    stem = dwg_path.stem
    parent = dwg_path.parent
    candidates: list[Path] = []
    for pattern in _SIDECAR_NAME_PATTERNS:
        base = f"{stem}{pattern}"
        for suffix in _SIDECAR_SUFFIXES:
            candidates.append(parent / f"{base}{suffix}")
    pdf_images = parent / "PDF Images"
    if pdf_images.is_dir():
        for pattern in _SIDECAR_NAME_PATTERNS:
            base = f"{stem}{pattern}"
            for suffix in (".png", ".jpg", ".jpeg", ".webp", ".pdf"):
                candidates.append(pdf_images / f"{base}{suffix}")
    for path in candidates:
        if path.is_file() and path.suffix.lower() in _SIDECAR_SUFFIXES:
            return path.resolve()
    return None


def _load_raster_dimensions(image_path: Path) -> tuple[int, int, bytes]:
    suffix = image_path.suffix.lower()
    if suffix == ".pdf":
        import fitz

        doc = fitz.open(image_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        data = pix.tobytes("png")
        width, height = pix.width, pix.height
        doc.close()
        return width, height, data
    import fitz

    doc = fitz.open(image_path)
    page = doc[0]
    pix = page.get_pixmap(alpha=False)
    data = pix.tobytes("png")
    width, height = pix.width, pix.height
    doc.close()
    return width, height, data


def get_visual_source_for_dwg(
    file_id_or_name: str,
    *,
    search_roots: list[Path] | None = None,
    file_cad_bounds_mm: dict[str, tuple[float, float, float, float]] | None = None,
    run_tiles_dir: Path | None = None,
) -> VisualSource:
    """Locate a raster/PDF sidecar or run tile for a DWG; never invent imagery."""
    dwg_path = _resolve_dwg_path(file_id_or_name, search_roots=search_roots)
    if dwg_path is None:
        return VisualSource(kind=VisualSourceKind.NONE, file_path=Path(file_id_or_name))

    sidecar = _discover_sidecar_image(dwg_path)
    if sidecar is not None:
        kind = (
            VisualSourceKind.SIDECAR_PDF
            if sidecar.suffix.lower() == ".pdf"
            else VisualSourceKind.SIDECAR_RASTER
        )
        width, height, _ = _load_raster_dimensions(sidecar)
        cad_bounds = _lookup_file_bounds(dwg_path, file_cad_bounds_mm)
        localization = (
            LocalizationStatus.EXACT if cad_bounds is not None else LocalizationStatus.FULL_IMAGE_ONLY
        )
        note = None if cad_bounds is not None else COORD_TRANSFORM_UNAVAILABLE
        return VisualSource(
            kind=kind,
            file_path=dwg_path,
            image_path=sidecar,
            cad_bounds_mm=cad_bounds,
            width_px=width,
            height_px=height,
            localization=localization,
            note=note,
        )

    if run_tiles_dir and run_tiles_dir.is_dir():
        stem = dwg_path.stem.lower()
        for tile in sorted(run_tiles_dir.glob("*.svg")):
            if stem in tile.stem.lower():
                return VisualSource(
                    kind=VisualSourceKind.RUN_TILE,
                    file_path=dwg_path,
                    image_path=tile,
                    localization=LocalizationStatus.UNAVAILABLE,
                    note=COORD_TRANSFORM_UNAVAILABLE,
                )

    for backend in _EXPORT_BACKENDS:
        try:
            out = dwg_path.parent / f"{dwg_path.stem}__dupla_export.png"
            exported = backend.export_plot_png(dwg_path, out)
            if exported and exported.is_file():
                width, height, _ = _load_raster_dimensions(exported)
                cad_bounds = _lookup_file_bounds(dwg_path, file_cad_bounds_mm)
                localization = (
                    LocalizationStatus.EXACT if cad_bounds is not None else LocalizationStatus.FULL_IMAGE_ONLY
                )
                return VisualSource(
                    kind=VisualSourceKind.SIDECAR_RASTER,
                    file_path=dwg_path,
                    image_path=exported,
                    cad_bounds_mm=cad_bounds,
                    width_px=width,
                    height_px=height,
                    localization=localization,
                    note=None if cad_bounds is not None else COORD_TRANSFORM_UNAVAILABLE,
                )
        except Exception as exc:
            logger.debug("DWG export backend failed for %s: %s", dwg_path, exc)

    return VisualSource(kind=VisualSourceKind.NONE, file_path=dwg_path)


def _lookup_file_bounds(
    dwg_path: Path,
    file_cad_bounds_mm: dict[str, tuple[float, float, float, float]] | None,
) -> tuple[float, float, float, float] | None:
    if not file_cad_bounds_mm:
        return None
    keys = (
        dwg_path.as_posix(),
        str(dwg_path),
        dwg_path.name,
        dwg_path.name.lower(),
    )
    for key in keys:
        bounds = file_cad_bounds_mm.get(key)
        if bounds and len(bounds) == 4:
            return tuple(float(v) for v in bounds)
    return None


def project_dwg_bounds_to_image_coords(
    bounds_cad_mm: tuple[float, float, float, float],
    *,
    image_cad_bounds: tuple[float, float, float, float],
    image_width_px: int,
    image_height_px: int,
) -> tuple[int, int, int, int] | None:
    """Map a CAD window to pixel coordinates within a georeferenced raster."""
    bx1, by1, bx2, by2 = (float(v) for v in bounds_cad_mm)
    ix1, iy1, ix2, iy2 = (float(v) for v in image_cad_bounds)
    cad_w = ix2 - ix1
    cad_h = iy2 - iy1
    if cad_w <= 0 or cad_h <= 0 or image_width_px <= 0 or image_height_px <= 0:
        return None
    px1 = int(round((bx1 - ix1) / cad_w * image_width_px))
    px2 = int(round((bx2 - ix1) / cad_w * image_width_px))
    py1 = int(round((iy2 - by2) / cad_h * image_height_px))
    py2 = int(round((iy2 - by1) / cad_h * image_height_px))
    x0, x1 = sorted((max(0, px1), min(image_width_px, px2)))
    y0, y1 = sorted((max(0, py1), min(image_height_px, py2)))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def crop_visual_to_bounds(
    image_png: bytes,
    *,
    image_cad_bounds: tuple[float, float, float, float],
    crop_cad_bounds: tuple[float, float, float, float],
    padding_mm: float = 0.0,
) -> tuple[bytes, int, int] | None:
    """Crop a PNG raster to CAD bounds with optional padding."""
    cx1, cy1, cx2, cy2 = (float(v) for v in crop_cad_bounds)
    if padding_mm:
        cx1 -= padding_mm
        cy1 -= padding_mm
        cx2 += padding_mm
        cy2 += padding_mm
    import fitz

    doc = fitz.open(stream=image_png, filetype="png")
    page = doc[0]
    width, height = int(page.rect.width), int(page.rect.height)
    pixel_bounds = project_dwg_bounds_to_image_coords(
        (cx1, cy1, cx2, cy2),
        image_cad_bounds=image_cad_bounds,
        image_width_px=width,
        image_height_px=height,
    )
    if pixel_bounds is None:
        doc.close()
        return None
    x0, y0, x1, y1 = pixel_bounds
    clip = fitz.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(clip=clip, alpha=False)
    out = pix.tobytes("png")
    doc.close()
    return out, pix.width, pix.height


def draw_clash_marker(
    *,
    clash_bounds_mm: tuple[float, float, float, float],
    marker_code: str,
    min_x: float,
    max_y: float,
    scale: float,
    marker_style: str = "rectangle",
) -> list[str]:
    """Return SVG fragment lines for a clash marker in CAD-mapped SVG space."""
    return _render_clash_marker(
        clash_bounds_mm=clash_bounds_mm,
        marker_code=marker_code,
        min_x=min_x,
        max_y=max_y,
        scale=scale,
        marker_style=marker_style,
    )


def _escape_svg(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_placeholder_panel(
    *,
    panel_id: str,
    file_label: str,
    file_path: str = "",
    width_px: int = 520,
    height_px: int = 360,
    message: str = PLACEHOLDER_PANEL_TITLE,
) -> VisualPanel:
    """Professional placeholder when no visual source exists."""
    fname = Path(file_path).name if file_path else ""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
        f'width="{width_px}" height="{height_px}">'
        f'<rect width="100%" height="100%" fill="#F3F4F6"/>'
        f'<rect x="12" y="12" width="{width_px - 24}" height="{height_px - 24}" '
        f'fill="none" stroke="#D1D5DB" stroke-width="1.5" stroke-dasharray="6 4"/>'
        f'<text x="{width_px / 2:.1f}" y="{height_px / 2 - 8:.1f}" text-anchor="middle" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="11" fill="#6B7280">'
        f"{_escape_svg(message)}</text>"
    )
    if fname:
        svg += (
            f'<text x="{width_px / 2:.1f}" y="{height_px / 2 + 14:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="9" fill="#9CA3AF">'
            f"{_escape_svg(fname)}</text>"
        )
    svg += "</svg>"
    return VisualPanel(
        panel_id=panel_id,
        file_label=file_label,
        svg_content=svg,
        source_kind=VisualSourceKind.NONE,
        localization=LocalizationStatus.UNAVAILABLE,
        has_geometry=False,
        warning=message,
    )


def build_schematic_clash_panel(
    *,
    panel_id: str,
    file_label: str,
    file_path: str,
    clash_bounds_mm: tuple[float, float, float, float],
    bbox_cad_mm: tuple[float, float, float, float] | None = None,
    marker_code: str = "",
    width_px: int = 520,
    height_px: int = 360,
) -> VisualPanel:
    """Diagram showing where the clash sits in CAD coordinates when no DWG visual is loaded.

    Produces a labelled rectangle + crosshair + grid. Coordinates rendered in meters
    so the architect can correlate with the AutoCAD Z W command without an actual plot.
    """
    cx1, cy1, cx2, cy2 = (float(v) for v in clash_bounds_mm)
    if bbox_cad_mm and len(bbox_cad_mm) == 4:
        bx1, by1, bx2, by2 = (float(v) for v in bbox_cad_mm)
    else:
        pad_x = max(abs(cx2 - cx1), 1000.0) * 1.4
        pad_y = max(abs(cy2 - cy1), 1000.0) * 1.4
        bx1, by1, bx2, by2 = cx1 - pad_x, cy1 - pad_y, cx2 + pad_x, cy2 + pad_y
    view_w = max(bx2 - bx1, 1.0)
    view_h = max(by2 - by1, 1.0)
    margin = 26
    plot_w = width_px - 2 * margin
    plot_h = height_px - 2 * margin
    sx = plot_w / view_w
    sy = plot_h / view_h
    s = min(sx, sy)
    plot_w_used = view_w * s
    plot_h_used = view_h * s
    ox = margin + (plot_w - plot_w_used) / 2
    oy = margin + (plot_h - plot_h_used) / 2

    def to_px(x: float, y: float) -> tuple[float, float]:
        px = ox + (x - bx1) * s
        py = (margin + plot_h) - (y - by1) * s
        return px, py

    crit_x1, crit_y1 = to_px(cx1, cy2)
    crit_x2, crit_y2 = to_px(cx2, cy1)
    rect_x = min(crit_x1, crit_x2)
    rect_y = min(crit_y1, crit_y2)
    rect_w = max(abs(crit_x2 - crit_x1), 4)
    rect_h = max(abs(crit_y2 - crit_y1), 4)
    cxc, cyc = to_px((cx1 + cx2) / 2.0, (cy1 + cy2) / 2.0)

    grid_lines: list[str] = []
    for i in range(1, 6):
        gx = ox + (plot_w_used / 6) * i
        grid_lines.append(
            f'<line x1="{gx:.1f}" y1="{margin}" x2="{gx:.1f}" y2="{margin + plot_h:.1f}" '
            f'stroke="#E5E7EB" stroke-width="0.6"/>'
        )
        gy = margin + (plot_h_used / 6) * i
        grid_lines.append(
            f'<line x1="{ox:.1f}" y1="{gy:.1f}" x2="{ox + plot_w_used:.1f}" y2="{gy:.1f}" '
            f'stroke="#E5E7EB" stroke-width="0.6"/>'
        )

    code_label = f"{marker_code} · " if marker_code else ""
    cx_m, cy_m = ((cx1 + cx2) / 2.0) / 1000.0, ((cy1 + cy2) / 2.0) / 1000.0
    width_m = (cx2 - cx1) / 1000.0
    height_m = (cy2 - cy1) / 1000.0

    title = file_label
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
        f'width="{width_px}" height="{height_px}">',
        '<rect width="100%" height="100%" fill="#FAFAFA"/>',
        f'<rect x="{ox - 6:.1f}" y="{margin - 6:.1f}" width="{plot_w_used + 12:.1f}" '
        f'height="{plot_h_used + 12:.1f}" fill="#FFFFFF" stroke="#9CA3AF" stroke-width="0.8"/>',
        *grid_lines,
        f'<line x1="{ox:.1f}" y1="{cyc:.1f}" x2="{ox + plot_w_used:.1f}" y2="{cyc:.1f}" '
        f'stroke="#D32F2F" stroke-width="0.6" stroke-dasharray="4 3" opacity="0.55"/>',
        f'<line x1="{cxc:.1f}" y1="{margin:.1f}" x2="{cxc:.1f}" y2="{margin + plot_h:.1f}" '
        f'stroke="#D32F2F" stroke-width="0.6" stroke-dasharray="4 3" opacity="0.55"/>',
        f'<rect x="{rect_x:.1f}" y="{rect_y:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" '
        f'fill="#D32F2F" fill-opacity="0.22" stroke="#D32F2F" stroke-width="1.4"/>',
        f'<circle cx="{cxc:.1f}" cy="{cyc:.1f}" r="6" fill="#D32F2F" stroke="#FFFFFF" stroke-width="1.4"/>',
        f'<text x="{cxc + 8:.1f}" y="{cyc - 8:.1f}" font-family="Courier New,Courier,monospace" '
        f'font-size="9" fill="#7F1D1D">({cx_m:.2f}, {cy_m:.2f}) m</text>',
        f'<text x="{ox:.1f}" y="{margin - 10:.1f}" font-family="Segoe UI,Arial,sans-serif" '
        f'font-size="10" font-weight="600" fill="#111827">{_escape_svg(title)}</text>',
        f'<text x="{ox:.1f}" y="{margin + plot_h + 14:.1f}" font-family="Courier New,Courier,monospace" '
        f'font-size="8" fill="#374151">{code_label}Zona clash: {width_m:.2f} × {height_m:.2f} m '
        f'· vista esquemática (coords CAD en metros)</text>',
        f'<text x="{ox + plot_w_used - 4:.1f}" y="{margin + plot_h + 14:.1f}" text-anchor="end" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="8" fill="#6B7280">'
        f'{_escape_svg(Path(file_path).name)}</text>',
        '</svg>',
    ]
    svg = "".join(parts)
    return VisualPanel(
        panel_id=panel_id,
        file_label=file_label,
        svg_content=svg,
        source_kind=VisualSourceKind.FOOTPRINT_GEOMETRY,
        localization=LocalizationStatus.EXACT,
        has_geometry=True,
        bbox_cad_mm=(bx1, by1, bx2, by2),
    )


def _wrap_raster_in_svg(
    png_bytes: bytes,
    *,
    width_px: int,
    height_px: int,
    title: str,
    warning: str | None = None,
    marker_lines: list[str] | None = None,
) -> str:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
        f'width="{width_px}" height="{height_px}">',
        f'<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<image href="data:image/png;base64,{encoded}" x="0" y="0" '
        f'width="{width_px}" height="{height_px}" preserveAspectRatio="xMidYMid meet"/>',
    ]
    if marker_lines:
        parts.extend(marker_lines)
    if warning:
        parts.append(
            f'<rect x="8" y="{height_px - 52}" width="{width_px - 16}" height="44" '
            f'fill="#FEF3C7" fill-opacity="0.92" stroke="#F59E0B" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="14" y="{height_px - 32}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="8" fill="#92400E">{_escape_svg(warning)}</text>'
        )
    parts.append(
        f'<text x="10" y="16" font-family="Segoe UI,Arial,sans-serif" font-size="10" '
        f'font-weight="600" fill="#374151">{_escape_svg(title)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _scale_png_to_width(png_bytes: bytes, target_width: int) -> tuple[bytes, int, int]:
    import fitz

    doc = fitz.open(stream=png_bytes, filetype="png")
    page = doc[0]
    src_w, src_h = page.rect.width, page.rect.height
    if src_w <= 0:
        doc.close()
        return png_bytes, target_width, max(1, target_width // 2)
    scale = target_width / src_w
    target_h = max(1, int(round(src_h * scale)))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    out = pix.tobytes("png")
    doc.close()
    return out, target_width, target_h


def build_visual_panel(
    *,
    panel_id: str,
    file_path: str,
    file_label: str,
    visual_source: VisualSource | None,
    clash_bounds_mm: tuple[float, float, float, float] | None,
    marker_code: str = "",
    marker_style: str = "rectangle",
    width_px: int = 520,
    bbox_cad_mm: tuple[float, float, float, float] | None = None,
    all_elements: list[Element25D] | None = None,
    level_id: str = "",
    clash_conflicts: list[ClashConflict] | None = None,
    alias_map: dict[str, str] | None = None,
) -> VisualPanel:
    """Build a report-ready panel from the best available honest visual source."""
    source = visual_source or VisualSource(kind=VisualSourceKind.NONE, file_path=Path(file_path))

    if source.kind in {VisualSourceKind.SIDECAR_RASTER, VisualSourceKind.SIDECAR_PDF} and source.image_path:
        _, _, png_bytes = _load_raster_dimensions(source.image_path)
        warning = source.note

        if (
            source.localization == LocalizationStatus.EXACT
            and source.cad_bounds_mm is not None
            and clash_bounds_mm is not None
        ):
            pad = max(clash_bounds_mm[2] - clash_bounds_mm[0], clash_bounds_mm[3] - clash_bounds_mm[1]) * 0.15
            cropped = crop_visual_to_bounds(
                png_bytes,
                image_cad_bounds=source.cad_bounds_mm,
                crop_cad_bounds=clash_bounds_mm,
                padding_mm=pad + 500.0,
            )
            if cropped is not None:
                crop_png, crop_w, crop_h = cropped
                scaled, out_w, out_h = _scale_png_to_width(crop_png, width_px)
                cx1, cy1, cx2, cy2 = clash_bounds_mm
                pad_mm = pad + 500.0
                view_bounds = (cx1 - pad_mm, cy1 - pad_mm, cx2 + pad_mm, cy2 + pad_mm)
                scale = out_w / max(view_bounds[2] - view_bounds[0], 1.0)
                marker_lines = draw_clash_marker(
                    clash_bounds_mm=clash_bounds_mm,
                    marker_code=marker_code,
                    min_x=view_bounds[0],
                    max_y=view_bounds[3],
                    scale=scale,
                    marker_style=marker_style,
                )
                svg = _wrap_raster_in_svg(
                    scaled,
                    width_px=out_w,
                    height_px=out_h,
                    title=file_label,
                    marker_lines=marker_lines,
                )
                return VisualPanel(
                    panel_id=panel_id,
                    file_label=file_label,
                    svg_content=svg,
                    source_kind=source.kind,
                    localization=LocalizationStatus.EXACT,
                    has_geometry=True,
                    bbox_cad_mm=view_bounds,
                )

        scaled, out_w, out_h = _scale_png_to_width(png_bytes, width_px)
        svg = _wrap_raster_in_svg(
            scaled,
            width_px=out_w,
            height_px=out_h,
            title=file_label,
            warning=warning or COORD_TRANSFORM_UNAVAILABLE,
        )
        return VisualPanel(
            panel_id=panel_id,
            file_label=file_label,
            svg_content=svg,
            source_kind=source.kind,
            localization=LocalizationStatus.FULL_IMAGE_ONLY,
            has_geometry=True,
            warning=warning or COORD_TRANSFORM_UNAVAILABLE,
        )

    if all_elements and bbox_cad_mm and clash_bounds_mm and level_id:
        tile = render_dwg_panel_svg(
            panel_id=panel_id,
            file_path=file_path,
            file_label=file_label,
            bbox_cad_mm=bbox_cad_mm,
            all_elements=all_elements,
            clash_bounds_mm=clash_bounds_mm,
            marker_code=marker_code,
            level_id=level_id,
            clash_conflicts=clash_conflicts,
            width_px=width_px,
            marker_style=marker_style,
            alias_map=alias_map,
        )
        has_geometry = bool(tile.elements_in_tile)
        if has_geometry:
            return VisualPanel(
                panel_id=panel_id,
                file_label=file_label,
                svg_content=tile.svg_content,
                source_kind=VisualSourceKind.FOOTPRINT_GEOMETRY,
                localization=LocalizationStatus.EXACT,
                has_geometry=has_geometry,
                bbox_cad_mm=bbox_cad_mm,
            )

    if clash_bounds_mm is not None:
        return build_schematic_clash_panel(
            panel_id=panel_id,
            file_label=file_label,
            file_path=file_path,
            clash_bounds_mm=clash_bounds_mm,
            bbox_cad_mm=bbox_cad_mm,
            marker_code=marker_code,
            width_px=width_px,
        )

    return build_placeholder_panel(
        panel_id=panel_id,
        file_label=file_label,
        file_path=file_path,
        width_px=width_px,
    )


def build_incident_comparison_panels(
    incident: ClashIncident,
    all_elements: list[Element25D] | None,
    *,
    marker_code: str,
    file_aliases: dict[str, str] | None = None,
    file_cad_bounds_mm: dict[str, tuple[float, float, float, float]] | None = None,
    search_roots: list[Path] | None = None,
    run_tiles_dir: Path | None = None,
    padding_factor: float = 0.35,
    width_px: int = 520,
    marker_style: str = "rectangle",
) -> tuple[VisualPanel, VisualPanel, bool, list[str]]:
    """Build DWG A / DWG B panels for one incident."""
    bbox = compute_tile_bbox(incident, padding_factor=padding_factor)
    file_a, file_b = incident.file_pair
    aliases = file_aliases or {}
    label_a = f"Plano A — {aliases.get(file_a) or Path(file_a).name}"
    label_b = f"Plano B — {aliases.get(file_b) or Path(file_b).name}"
    clash_bounds = tuple(float(v) for v in incident.plan_bounds_mm)
    conflicts = _incident_conflicts(incident)

    source_a = get_visual_source_for_dwg(
        file_a,
        search_roots=search_roots,
        file_cad_bounds_mm=file_cad_bounds_mm,
        run_tiles_dir=run_tiles_dir,
    )
    source_b = get_visual_source_for_dwg(
        file_b,
        search_roots=search_roots,
        file_cad_bounds_mm=file_cad_bounds_mm,
        run_tiles_dir=run_tiles_dir,
    )

    left = build_visual_panel(
        panel_id=f"{incident.incident_id}_panel_a",
        file_path=file_a,
        file_label=label_a,
        visual_source=source_a if source_a.kind != VisualSourceKind.NONE else None,
        clash_bounds_mm=clash_bounds,
        marker_code=marker_code,
        marker_style=marker_style,
        width_px=width_px,
        bbox_cad_mm=bbox,
        all_elements=all_elements,
        level_id=incident.level_id,
        clash_conflicts=conflicts,
        alias_map=aliases,
    )
    right = build_visual_panel(
        panel_id=f"{incident.incident_id}_panel_b",
        file_path=file_b,
        file_label=label_b,
        visual_source=source_b if source_b.kind != VisualSourceKind.NONE else None,
        clash_bounds_mm=clash_bounds,
        marker_code=marker_code,
        marker_style=marker_style,
        width_px=width_px,
        bbox_cad_mm=bbox,
        all_elements=all_elements,
        level_id=incident.level_id,
        clash_conflicts=conflicts,
        alias_map=aliases,
    )

    has_visual = left.has_geometry or right.has_geometry
    warnings: list[str] = []
    for panel in (left, right):
        if panel.warning and panel.warning not in warnings:
            warnings.append(panel.warning)
    if not has_visual and RUN_NO_VISUAL_WARNING not in warnings:
        warnings.append(RUN_NO_VISUAL_WARNING)
    return left, right, has_visual, warnings


def run_has_dwg_visual_preview(rows: list[Any]) -> bool:
    """True when at least one incident row has real geometry in a visual panel."""
    return any(getattr(row, "has_visual", False) for row in rows)
