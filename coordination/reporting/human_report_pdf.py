"""Human-facing clash coordination PDF (architectural review package style)."""

from __future__ import annotations

import io
import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from coordination.core.clash import ClashIncident
from coordination.core.models_25d import Element25D
from coordination.reporting.incident_normalizer import (
    NormalizedIncident,
    normalize_incidents_for_run,
)
from coordination.reporting.element_loaders import load_elements_for_visual_reporting
from coordination.reporting.dwg_visual_adapter import (
    RUN_NO_VISUAL_WARNING,
    build_incident_comparison_panels,
    build_schematic_clash_panel,
    run_has_dwg_visual_preview,
)
from coordination.reporting.human_report_copy import (
    CORRECTION_LIFECYCLE,
    build_architectural_action,
    build_architectural_observation,
    corrected_delivery_section_lines,
    corrected_delivery_steps,
    filter_human_warnings,
    format_clash_type,
    format_correction_status,
    format_dwg_to_correct,
    format_reviewer_decision,
    format_upload_status,
    format_ubicacion_zw,
    format_ubicacion_zw_lines,
    humanize_confidence,
    humanize_discipline_label,
)

REPORT_TITLE = "Informe de Coordinación de Clashes"
REPORT_SUBTITLE = "Comparación DWG vs DWG, revisión en obra y entrega de planos corregidos"

logger = logging.getLogger(__name__)

_NA = "no disponible"

FORM_CODE = "DU-FO-CLASH-01"
FORM_VERSION = "V.01"
CONFIDENTIAL_FOOTER = "Este documento es confidencial"

PAGE_SIZE = landscape(A3)
PAGE_W, PAGE_H = PAGE_SIZE

MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_T = 16 * mm
MARGIN_B = 22 * mm

DISCIPLINE_ES = {
    "ARQUITECTURA": "Arquitectura",
    "ESTRUCTURA": "Estructura",
    "FONTANERIA": "Fontanería",
    "ELECTRICIDAD": "Eléctrico",
    "CLIMATIZACION": "Mecánico",
}

SEVERITY_ES = {
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
    "crítica": "Crítica",
    "critica": "Crítica",
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}

PRIORITY_PALETTE = {
    "critical": colors.HexColor("#D32F2F"),
    "high":     colors.HexColor("#F57C00"),
    "medium":   colors.HexColor("#F9A825"),
    "low":      colors.HexColor("#1976D2"),
    "resolved": colors.HexColor("#388E3C"),
}

# Brand palette — matches web-platform/frontend/src/index.css (--color-primary: #c10d12)
DUPLA_BRAND = {
    "primary":      colors.HexColor("#C10D12"),
    "primary_dark": colors.HexColor("#9A0A0E"),
    "muted":        colors.HexColor("#666666"),
    "ink":          colors.HexColor("#1A1A1A"),
    "surface":      colors.HexColor("#FAFAFA"),
    "surface_tint": colors.HexColor("#FDF2F2"),
}

_DUPLA_LOGO_PATH = (
    Path(__file__).resolve().parents[2] / "web-platform" / "frontend" / "public" / "logo-dupla.png"
)

SEVERITY_BADGE_COLORS = {
    "critical": PRIORITY_PALETTE["critical"],
    "high":     PRIORITY_PALETTE["high"],
    "medium":   PRIORITY_PALETTE["medium"],
    "low":      PRIORITY_PALETTE["low"],
}

DECISION_CHIP_COLORS = {
    "real":           PRIORITY_PALETTE["critical"],
    "falso_positivo": PRIORITY_PALETTE["low"],
    "pendiente":      DUPLA_BRAND["muted"],
}

CORRECTION_STATUS_CHIP = {
    "Detectado":              "#666666",
    "Revisado":               "#1976D2",
    "Corrección requerida":   "#C10D12",
    "Corrección cargada":     "#9A0A0E",
    "Pendiente re-análisis":  "#9A0A0E",
    "Resuelto":               "#388E3C",
    "Aún presente":           "#D32F2F",
    "Falso positivo":         "#1976D2",
}

UPLOAD_STATUS_CHIP = {
    "Cargado en Dupla":   "#388E3C",
    "Pendiente de carga": "#C10D12",
    "No requerido":       "#666666",
}

LIFECYCLE_STEPS = ("Detectado", "Revisado", "Cargado", "Re-análisis", "Resuelto")

PLACEHOLDER_MSG = "Vista de plano no disponible en esta corrida"

CHECKLIST_CORE_COLUMNS = [
    "CÓDIGO",
    "PLANO A",
    "PLANO B",
    "NIVEL",
    "PRIORIDAD",
    "UBICACIÓN",
    "OBSERVACIÓN",
    "DECISIÓN",
]

CHECKLIST_CORE_COL_WIDTHS = [0.08, 0.1, 0.1, 0.07, 0.08, 0.17, 0.22, 0.1]

CHECKLIST_CORRECTION_COLUMNS = [
    "CÓDIGO",
    "DWG A CORREGIR",
    "ESTADO CORRECCIÓN",
    "ESTADO CARGA",
    "NOTAS",
]

CHECKLIST_CORRECTION_COL_WIDTHS = [0.1, 0.28, 0.18, 0.18, 0.26]

BITACORA_COLUMNS = [
    "CÓDIGO",
    "DWG A CORREGIR",
    "ESTADO CORRECCIÓN",
    "ESTADO CARGA",
    "NOTAS",
    "FECHA",
    "RESP.",
]

BITACORA_COL_WIDTHS = [0.08, 0.18, 0.14, 0.14, 0.28, 0.09, 0.09]

def _coerce_plan_bounds(raw: Any) -> tuple[float, float, float, float] | None:
    """Read plan_bounds_mm out of a raw incident dict in a tolerant way."""
    if not raw:
        return None
    try:
        seq = list(raw)
    except TypeError:
        return None
    if len(seq) < 4:
        return None
    try:
        x1, y1, x2, y2 = (float(seq[i]) for i in range(4))
    except (TypeError, ValueError):
        return None
    if not (x2 > x1 and y2 > y1):
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        if x2 - x1 < 1.0:
            x2 = x1 + 1000.0
        if y2 - y1 < 1.0:
            y2 = y1 + 1000.0
    return (x1, y1, x2, y2)


_DWG_ALIAS_BY_BASENAME: dict[str, str] = {
    "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg": "ARQ_REV1",
    "PLANOS ARQ TORTUGA C-40 20260129.dwg": "ARQ_REV2",
    "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg": "EST_REV1",
}


@dataclass
class ClashSheetRow:
    incident_id: str
    code: str
    group_code: str
    disciplina_a: str
    plano_a: str
    disciplina_b: str
    plano_b: str
    nivel: str
    tipo: str
    tipo_conflicto: str
    prioridad: str
    ubicacion_comando: str
    observacion: str
    accion_sugerida: str
    estado_correccion: str
    estado_carga: str
    decision_revisor: str
    dwg_corregir: str
    comparacion_dwg: str
    par_dwg_original: str
    severity: str
    severity_bucket: str
    clash_type: str
    area_m2_text: str
    z_depth_text: str
    discipline_pair: str
    layer_a: str
    layer_b: str
    layer_pair: str
    zoom_command: str
    zoom_fallback: str | None
    center_text: str
    bounds_text: str
    file_a_path: str
    file_b_path: str
    member_count: int
    confidence: str
    correction_status: str
    upload_status: str
    dwg_to_correct: str
    provenance_layers: str
    provenance_center: str
    provenance_bounds: str
    provenance_zoom: str
    has_visual: bool = True
    left_svg: str = ""
    right_svg: str = ""
    warnings: list[str] | None = None


def _professional_table_style(*, header_bg: str = "#1F2937") -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _dominant_priority(rows: list["ClashSheetRow"]) -> str:
    """Highest-severity bucket present in the run; medium when no rows."""
    if not rows:
        return "medium"
    for bucket in ("critical", "high", "medium", "low"):
        if any(r.severity_bucket == bucket for r in rows):
            return bucket
    return "medium"


def _decision_bucket(text: str) -> str:
    key = str(text or "").strip().lower()
    if "real" in key:
        return "real"
    if "falso" in key:
        return "falso_positivo"
    return "pendiente"


def _draw_priority_band(c: canvas.Canvas, color: colors.Color, height: float) -> None:
    """Top-of-page color band used on the cover."""
    c.setFillColor(color)
    c.rect(0, PAGE_H - height, PAGE_W, height, stroke=0, fill=1)


def _draw_kpi_card(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: str,
    accent: colors.Color,
    emphasize: bool = False,
) -> None:
    """Draw one KPI card on the cover page."""
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.setLineWidth(0.6)
    c.setFillColor(colors.white)
    c.rect(x, y, width, height, stroke=1, fill=1)
    c.setFillColor(accent)
    c.rect(x, y + height - 4, width, 4, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 10, y + height - 18, label.upper())
    c.setFont("Helvetica-Bold", 28 if emphasize else 24)
    c.setFillColor(accent if emphasize else colors.HexColor("#111827"))
    c.drawString(x + 10, y + 14, value)


def _safe_pie_data(counts_by_bucket: dict[str, int]) -> tuple[list[int], list[str], list[colors.Color]]:
    data, labels, palette = [], [], []
    for bucket, label in (
        ("critical", "Crítica"),
        ("high", "Alta"),
        ("medium", "Media"),
        ("low", "Baja"),
    ):
        n = int(counts_by_bucket.get(bucket, 0))
        if n > 0:
            data.append(n)
            labels.append(f"{label} ({n})")
            palette.append(PRIORITY_PALETTE[bucket])
    return data, labels, palette


def _draw_donut(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    size: float,
    counts_by_bucket: dict[str, int],
) -> None:
    data, labels, palette = _safe_pie_data(counts_by_bucket)
    if not data:
        c.setFillColor(colors.HexColor("#9CA3AF"))
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + size / 2, y + size / 2, "Sin datos")
        return
    drawing = Drawing(size, size)
    pie = Pie()
    pie.x = 18
    pie.y = 18
    pie.width = size - 36
    pie.height = size - 36
    pie.data = data
    pie.labels = labels
    pie.innerRadiusFraction = 0.55
    pie.sideLabels = 1
    pie.simpleLabels = 1
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1.2
    pie.slices.fontSize = 8
    pie.slices.fontName = "Helvetica-Bold"
    for i, color in enumerate(palette):
        pie.slices[i].fillColor = color
    drawing.add(pie)
    renderPDF.draw(drawing, c, x, y)


def _draw_lifecycle_bar(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float = 16,
    current_step: str = "Detectado",
    completed_steps: set[str] | None = None,
) -> None:
    completed_steps = completed_steps or set()
    seg_gap = 3
    seg_w = (width - seg_gap * (len(LIFECYCLE_STEPS) - 1)) / len(LIFECYCLE_STEPS)
    try:
        current_idx = LIFECYCLE_STEPS.index(current_step)
    except ValueError:
        current_idx = 0
    for i, step in enumerate(LIFECYCLE_STEPS):
        sx = x + i * (seg_w + seg_gap)
        if step in completed_steps or i < current_idx:
            bg, fg = PRIORITY_PALETTE["resolved"], colors.white
        elif i == current_idx:
            bg, fg = DUPLA_BRAND["primary"], colors.white
        else:
            bg, fg = colors.HexColor("#E5E7EB"), colors.HexColor("#374151")
        c.setFillColor(bg)
        c.roundRect(sx, y, seg_w, height, 3, stroke=0, fill=1)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(sx + seg_w / 2, y + 5, step)


def _precompute_total_pages(rows: list["ClashSheetRow"]) -> int:
    """Estimate total page count so the footer can show 'Pág. N de M'."""
    checklist_chunk = 14
    bitacora_chunk = 18
    n = len(rows)
    critical_high = sum(1 for r in rows if r.severity_bucket in {"critical", "high"})
    medium = sum(1 for r in rows if r.severity_bucket == "medium")
    low = sum(1 for r in rows if r.severity_bucket == "low")
    pages = 0
    pages += 1                                                # cover
    pages += 1                                                # priority summary
    pages += max(1, math.ceil(max(n, 1) / checklist_chunk))   # checklist matrix
    pages += critical_high                                    # one per high/critical incident
    pages += math.ceil(medium / 2) if medium else 0
    pages += math.ceil(low / 2) if low else 0
    pages += max(1, math.ceil(max(n, 1) / bitacora_chunk))    # bitácora
    pages += 1                                                # entrega
    pages += 1                                                # leyenda alias
    return pages


def _normalize_dwg_basename(name: str) -> str:
    return " ".join(str(name or "").split())


def build_file_alias_map(file_paths: list[str]) -> dict[str, str]:
    """Map full file path to a short, stable display label (alias codes when known)."""
    paths = sorted({str(path) for path in file_paths if path})
    name_counts = Counter(_normalize_dwg_basename(Path(path).name) for path in paths)
    aliases: dict[str, str] = {}
    for path in paths:
        p = Path(path)
        base = _normalize_dwg_basename(p.name)
        known = _DWG_ALIAS_BY_BASENAME.get(base)
        if known:
            aliases[path] = known
            continue
        if name_counts[base] > 1:
            parent = p.parent.name
            label = f"{parent}/{p.name}" if parent else p.name
        else:
            label = p.name
        aliases[path] = _truncate(label, 24)
    return aliases


def _truncate(text: str, max_len: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def _discipline_es(value: str) -> str:
    return humanize_discipline_label(str(value or ""))


def _severity_es(value: str) -> str:
    return SEVERITY_ES.get(str(value or "").lower(), str(value or "—"))


def _wrap(text: str, max_len: int = 120) -> str:
    return _truncate(text.replace("\n", " "), max_len)


def _severity_bucket(value: str) -> str:
    key = str(value or "").lower().strip()
    if key in {"critical", "crítica", "critica"}:
        return "critical"
    if key in {"high", "alta"}:
        return "high"
    if key in {"medium", "media"}:
        return "medium"
    if key in {"low", "baja"}:
        return "low"
    return "medium"


def _format_area_m2(area_mm2: float) -> str:
    if area_mm2 <= 0:
        return _NA
    return f"{area_mm2 / 1_000_000.0:.2f} m²"


def _layer_display(layer: str | None) -> str:
    if layer and layer.strip() and layer.strip() not in {"?", "-", _NA}:
        return layer.strip()
    return _NA


def _norm_to_sheet_row(
    norm: NormalizedIncident,
    *,
    aliases: dict[str, str],
    left_svg: str = "",
    right_svg: str = "",
    has_visual: bool = False,
) -> ClashSheetRow:
    file_a = norm.file_a_full
    file_b = norm.file_b_full
    plano_a = aliases.get(file_a) or (_truncate(Path(file_a).name, 48) if file_a != _NA else _NA)
    plano_b = aliases.get(file_b) or (_truncate(Path(file_b).name, 48) if file_b != _NA else _NA)

    layer_a = _layer_display(norm.layer_a)
    layer_b = _layer_display(norm.layer_b)
    layer_pair = f"{layer_a} / {layer_b}" if layer_a != _NA or layer_b != _NA else _NA
    disc_a = _discipline_es(norm.discipline_a)
    disc_b = _discipline_es(norm.discipline_b)
    disc_pair = f"{disc_a} / {disc_b}"
    area_m2 = norm.area_mm2 / 1_000_000.0 if norm.area_mm2 > 0 else None
    area_text = _format_area_m2(norm.area_mm2)

    tipo = format_clash_type(norm.clash_type)
    observacion = build_architectural_observation(
        layer_a=layer_a,
        layer_b=layer_b,
        nivel=norm.level_id,
        disciplina_a=disc_a,
        disciplina_b=disc_b,
        plano_a=plano_a,
        plano_b=plano_b,
        area_m2=area_m2,
        human_description=norm.human_description if norm.human_description != _NA else "",
    )
    accion = build_architectural_action(
        dwg_to_correct=norm.dwg_to_correct,
        plano_a=plano_a,
        plano_b=plano_b,
        recommended_action=norm.recommended_action if norm.recommended_action != _NA else "",
    )
    dwg_corregir = format_dwg_to_correct(
        norm.dwg_to_correct if norm.dwg_to_correct != _NA else "",
        plano_a=plano_a,
        plano_b=plano_b,
        disciplina_a=disc_a,
        disciplina_b=disc_b,
    )
    ubicacion = format_ubicacion_zw(
        center_text=norm.center_text,
        zoom_command=norm.zoom_command or "",
        zoom_fallback=norm.zoom_fallback,
    )
    prioridad = norm.priority if norm.priority != _NA else _severity_es(str(norm.severity))

    return ClashSheetRow(
        incident_id=norm.incident_id,
        code=norm.human_code,
        group_code=norm.group_code,
        disciplina_a=disc_a,
        plano_a=plano_a,
        disciplina_b=disc_b,
        plano_b=plano_b,
        nivel=norm.level_id,
        tipo=tipo,
        tipo_conflicto=tipo,
        prioridad=prioridad,
        ubicacion_comando=ubicacion,
        observacion=_wrap(observacion, 220),
        accion_sugerida=_wrap(accion, 180),
        estado_correccion=format_correction_status(norm.correction_status),
        estado_carga=format_upload_status(norm.upload_status),
        decision_revisor=format_reviewer_decision(norm.reviewer_decision),
        dwg_corregir=dwg_corregir,
        comparacion_dwg=f"{plano_a} ↔ {plano_b}",
        par_dwg_original=f"DWG A: {plano_a} · DWG B: {plano_b}",
        severity=str(norm.severity).lower(),
        severity_bucket=_severity_bucket(str(norm.severity)),
        clash_type=norm.clash_type if norm.clash_type != _NA else "HARD",
        area_m2_text=area_text,
        z_depth_text=_NA,
        discipline_pair=disc_pair,
        layer_a=layer_a,
        layer_b=layer_b,
        layer_pair=layer_pair,
        zoom_command=norm.zoom_command or norm.zoom_fallback or _NA,
        zoom_fallback=norm.zoom_fallback,
        center_text=norm.center_text,
        bounds_text=norm.bounds_text,
        file_a_path=file_a,
        file_b_path=file_b,
        member_count=norm.member_count,
        confidence=humanize_confidence(norm.confidence),
        correction_status=norm.correction_status or "detected",
        upload_status=norm.upload_status or "",
        dwg_to_correct=dwg_corregir,
        provenance_layers=norm.provenance.layers_source,
        provenance_center=norm.provenance.center_source,
        provenance_bounds=norm.provenance.bounds_source,
        provenance_zoom=norm.provenance.zoom_source,
        has_visual=has_visual,
        left_svg=left_svg,
        right_svg=right_svg,
        warnings=filter_human_warnings(list(norm.warnings)),
    )


def prepare_clash_sheet_rows(
    *,
    project_name: str,
    report_context: dict[str, Any],
    primary_payload: dict[str, Any],
    all_elements: list[Element25D] | None = None,
    file_aliases: dict[str, str] | None = None,
    revision_md: str = "",
) -> tuple[list[ClashSheetRow], dict[str, str]]:
    """Build structured rows for checklist and visual pages via normalized incidents."""
    normalized = normalize_incidents_for_run(
        project_name=project_name,
        primary_payload=primary_payload,
        report_context=report_context,
        revision_md=revision_md,
    )

    file_paths: list[str] = []
    for norm in normalized:
        if norm.file_a_full != _NA:
            file_paths.append(norm.file_a_full)
        if norm.file_b_full != _NA:
            file_paths.append(norm.file_b_full)
    aliases = file_aliases or build_file_alias_map(file_paths)

    incident_models: dict[str, ClashIncident] = {}
    for raw in primary_payload.get("incidents") or []:
        try:
            incident_models[str(raw.get("incident_id"))] = ClashIncident.model_validate(raw)
        except Exception:
            continue

    rows: list[ClashSheetRow] = []
    raw_by_id = {str(r.get("incident_id")): r for r in (primary_payload.get("incidents") or []) if isinstance(r, dict)}
    for norm in normalized:
        left_svg = ""
        right_svg = ""
        has_visual = False
        bucket = _severity_bucket(str(norm.severity))
        marker_style = "cloud" if bucket == "critical" else "rectangle"
        panel_width = 720 if bucket in {"critical", "high"} else 480
        incident_model = incident_models.get(norm.incident_id)
        panel_warnings: list[str] = []
        if incident_model is not None:
            try:
                left_panel, right_panel, has_visual, panel_warnings = build_incident_comparison_panels(
                    incident_model,
                    all_elements,
                    marker_code=norm.human_code,
                    file_aliases=aliases,
                    width_px=panel_width,
                    marker_style=marker_style,
                )
                left_svg = left_panel.svg_content
                right_svg = right_panel.svg_content
            except Exception as exc:
                logger.warning("DWG comparison panels failed for %s: %s", norm.incident_id, exc)
        if not left_svg or not right_svg:
            raw_row = raw_by_id.get(norm.incident_id) or {}
            schematic_bounds = _coerce_plan_bounds(raw_row.get("plan_bounds_mm"))
            if schematic_bounds is not None:
                file_a_path = norm.file_a_full if norm.file_a_full != _NA else (raw_row.get("file_pair") or [""])[0]
                file_b_path = norm.file_b_full if norm.file_b_full != _NA else (
                    (raw_row.get("file_pair") or ["", ""])[1] if len(raw_row.get("file_pair") or []) > 1 else ""
                )
                label_a = aliases.get(file_a_path) or Path(str(file_a_path)).name or norm.file_a
                label_b = aliases.get(file_b_path) or Path(str(file_b_path)).name or norm.file_b
                left_schematic = build_schematic_clash_panel(
                    panel_id=f"{norm.incident_id}_panel_a",
                    file_label=f"Plano A — {label_a}",
                    file_path=str(file_a_path or ""),
                    clash_bounds_mm=schematic_bounds,
                    marker_code=norm.human_code,
                    width_px=panel_width,
                )
                right_schematic = build_schematic_clash_panel(
                    panel_id=f"{norm.incident_id}_panel_b",
                    file_label=f"Plano B — {label_b}",
                    file_path=str(file_b_path or ""),
                    clash_bounds_mm=schematic_bounds,
                    marker_code=norm.human_code,
                    width_px=panel_width,
                )
                left_svg = left_schematic.svg_content
                right_svg = right_schematic.svg_content
                has_visual = True
                if RUN_NO_VISUAL_WARNING in panel_warnings:
                    panel_warnings = [w for w in panel_warnings if w != RUN_NO_VISUAL_WARNING]

        row = _norm_to_sheet_row(
            norm,
            aliases=aliases,
            left_svg=left_svg,
            right_svg=right_svg,
            has_visual=has_visual,
        )
        for warning in panel_warnings:
            human_warning = filter_human_warnings([warning])
            for item in human_warning:
                if item not in row.warnings:
                    row.warnings.append(item)
        rep = (raw_by_id.get(norm.incident_id) or {}).get("representative_conflict") or {}
        z_val = rep.get("overlap_depth_z_mm")
        if z_val is not None:
            try:
                row.z_depth_text = f"{float(z_val):.0f} mm"
            except (TypeError, ValueError):
                pass
        rows.append(row)
    return rows, aliases


def render_coordination_human_report_pdf(
    *,
    output_path: str | Path,
    project_name: str,
    run_label: str,
    generated_at: str,
    report_context: dict[str, Any],
    primary_payload: dict[str, Any],
    all_elements: list[Element25D] | None = None,
    exported_by: str = "Sistema Dupla",
    revision_md: str = "",
) -> Path:
    """Write the architectural-style human clash PDF."""
    elements = all_elements
    if not elements:
        elements_path = Path(output_path).parent / "elements_by_dwg.json"
        elements = load_elements_for_visual_reporting(elements_path)
    rows, aliases = prepare_clash_sheet_rows(
        project_name=project_name,
        report_context=report_context,
        primary_payload=primary_payload,
        all_elements=elements or None,
        revision_md=revision_md,
    )
    builder = _HumanReportPDFBuilder(
        output_path=Path(output_path),
        project_name=project_name,
        run_label=run_label,
        generated_at=generated_at,
        exported_by=exported_by,
        rows=rows,
        aliases=aliases,
    )
    return builder.build()


class _HumanReportPDFBuilder:
    def __init__(
        self,
        *,
        output_path: Path,
        project_name: str,
        run_label: str,
        generated_at: str,
        exported_by: str,
        rows: list[ClashSheetRow],
        aliases: dict[str, str],
    ) -> None:
        self.output_path = output_path
        self.project_name = _truncate(project_name.split("—")[0].split("–")[0].strip(), 80)
        self.run_label = run_label
        self.generated_at = generated_at
        self.exported_by = exported_by
        self.rows = rows
        self.aliases = aliases
        self.page_num = 0
        self.total_pages = max(1, _precompute_total_pages(rows))
        self.dominant_bucket = _dominant_priority(rows)
        self.brand_color = DUPLA_BRAND["primary"]
        self.canvas: canvas.Canvas | None = None

    def build(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.canvas = canvas.Canvas(str(self.output_path), pagesize=PAGE_SIZE)
        self._cover_page()
        self._priority_summary_pages()
        self._checklist_matrix_pages()

        critical_high = [r for r in self.rows if r.severity_bucket in {"critical", "high"}]
        medium = [r for r in self.rows if r.severity_bucket == "medium"]
        low = [r for r in self.rows if r.severity_bucket == "low"]

        for row in critical_high:
            self._visual_full_page(row)

        for index in range(0, len(medium), 2):
            self._visual_compact_page(medium[index : index + 2], section="Prioridad media")

        for index in range(0, len(low), 2):
            self._visual_compact_page(low[index : index + 2], section="Prioridad baja")

        self._validation_log_pages()
        self._corrected_delivery_page()
        self._alias_legend_page()
        self.canvas.save()
        return self.output_path

    def _new_page(self) -> None:
        if self.page_num > 0 and self.canvas is not None:
            self.canvas.showPage()
        self.page_num += 1

    def _draw_header(self, *, subtitle: str = "", cover: bool = False) -> float:
        """Top band on every page. On the cover, the priority colour band sits above.

        Returns the Y coordinate where content can start.
        """
        assert self.canvas is not None
        c = self.canvas
        y_top = PAGE_H - MARGIN_T
        if cover:
            return y_top - 8
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#E5E7EB"))
        c.setLineWidth(0.6)
        c.rect(MARGIN_L, y_top - 34, 52, 22, stroke=1, fill=1)
        self._draw_brand_logo(c, MARGIN_L + 4, y_top - 32, 44, 18)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN_L + 62, y_top - 14, self.project_name)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(MARGIN_L + 62, y_top - 28, f"Proyecto · {self.project_name}")
        c.setFont("Courier-Bold", 8.5)
        c.drawRightString(PAGE_W - MARGIN_R, y_top - 14, f"Run · {self.run_label}")
        if subtitle:
            c.setFont("Helvetica-Bold", 10.5)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawRightString(PAGE_W - MARGIN_R, y_top - 28, subtitle)
        c.setStrokeColor(self.brand_color)
        c.setLineWidth(1.2)
        c.line(MARGIN_L, y_top - 38, PAGE_W - MARGIN_R, y_top - 38)
        return y_top - 48

    def _draw_brand_logo(self, c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
        """Draw Dupla logo when available; fall back to a branded text badge."""
        if _DUPLA_LOGO_PATH.is_file():
            try:
                c.drawImage(
                    str(_DUPLA_LOGO_PATH),
                    x,
                    y,
                    width=width,
                    height=height,
                    preserveAspectRatio=True,
                    anchor="sw",
                    mask="auto",
                )
                return
            except Exception:
                logger.debug("Could not render Dupla logo from %s", _DUPLA_LOGO_PATH)
        c.setFillColor(DUPLA_BRAND["primary"])
        c.rect(x, y, width, height, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(x + width / 2, y + height / 2 - 4, "DUPLA")

    def _draw_footer(self) -> None:
        assert self.canvas is not None
        c = self.canvas
        y = MARGIN_B - 6
        progress = min(1.0, self.page_num / max(self.total_pages, 1))
        bar_y = y + 16
        c.setFillColor(colors.HexColor("#E5E7EB"))
        c.rect(MARGIN_L, bar_y, PAGE_W - MARGIN_L - MARGIN_R, 1.6, stroke=0, fill=1)
        c.setFillColor(self.brand_color)
        c.rect(MARGIN_L, bar_y, (PAGE_W - MARGIN_L - MARGIN_R) * progress, 1.6, stroke=0, fill=1)
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(MARGIN_L, y + 10, PAGE_W - MARGIN_R, y + 10)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#6B7280"))
        date_label = self.generated_at[:10] if self.generated_at else datetime.utcnow().date().isoformat()
        c.drawString(MARGIN_L, y, f"{FORM_CODE} · {FORM_VERSION} · Exportado: {date_label}")
        c.drawCentredString(PAGE_W / 2, y, CONFIDENTIAL_FOOTER)
        c.drawRightString(
            PAGE_W - MARGIN_R,
            y,
            f"Pág. {self.page_num} de {self.total_pages} · {self.exported_by}",
        )

    def _finish_page(self, *, subtitle: str = "", cover: bool = False) -> None:
        self._new_page()
        self._draw_header(subtitle=subtitle, cover=cover)
        self._draw_footer()

    def _cover_page(self) -> None:
        self._finish_page(subtitle="Portada", cover=True)
        assert self.canvas is not None
        c = self.canvas
        band_h = PAGE_H * 0.25
        _draw_priority_band(c, self.brand_color, band_h)

        date_label = self.generated_at[:19] if self.generated_at else datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_L, PAGE_H - MARGIN_T - 6, "DUPLA · COORDINACIÓN BIM")
        c.setFont("Courier-Bold", 8.5)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T - 6, f"Run · {self.run_label}")

        c.setFont("Helvetica-Bold", 28)
        c.drawString(MARGIN_L, PAGE_H - band_h * 0.55, self.project_name)
        c.setFont("Helvetica", 13)
        c.drawString(MARGIN_L, PAGE_H - band_h * 0.55 - 22, REPORT_TITLE)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN_L, PAGE_H - band_h * 0.55 - 38, REPORT_SUBTITLE)
        c.setFont("Helvetica", 9)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - band_h + 18, f"Fecha de emisión · {date_label}")

        kpi_top = PAGE_H - band_h - 28
        kpi_h = 78
        gap = 12
        kpi_w = (PAGE_W - MARGIN_L - MARGIN_R - 2 * gap) / 3
        total = len(self.rows)
        crit_high = sum(1 for r in self.rows if r.severity_bucket in {"critical", "high"})
        pending = sum(
            1
            for r in self.rows
            if _decision_bucket(r.decision_revisor) == "pendiente"
        )
        cards = [
            ("Total clashes", str(total), PRIORITY_PALETTE["resolved"], False),
            (
                "Críticos + Altos",
                str(crit_high),
                PRIORITY_PALETTE["critical"],
                crit_high > 0,
            ),
            (
                "Pendientes de decisión",
                str(pending),
                PRIORITY_PALETTE["medium"],
                pending > 0,
            ),
        ]
        for i, (label, value, accent, emphasize) in enumerate(cards):
            _draw_kpi_card(
                c,
                x=MARGIN_L + i * (kpi_w + gap),
                y=kpi_top - kpi_h,
                width=kpi_w,
                height=kpi_h,
                label=label,
                value=value,
                accent=accent,
                emphasize=emphasize,
            )

        if not run_has_dwg_visual_preview(self.rows):
            warn_y = kpi_top - kpi_h - 20
            c.setFillColor(colors.HexColor("#92400E"))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(MARGIN_L, warn_y, RUN_NO_VISUAL_WARNING)

        index_top = kpi_top - kpi_h - 44
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 13)
        c.drawString(MARGIN_L, index_top, "Contenido del entregable")
        index_y = index_top - 22
        section_items = [
            ("Resumen de clashes por prioridad", colors.HexColor("#388E3C")),
            ("Matriz de chequeo (tabla principal y tabla de corrección)", colors.HexColor("#1976D2")),
            ("Láminas de comparación DWG A vs DWG B", colors.HexColor("#7B1FA2")),
            ("Bitácora de validación y corrección", colors.HexColor("#F57C00")),
            ("Entrega de planos corregidos", colors.HexColor("#00838F")),
            ("Leyenda de alias de archivos", colors.HexColor("#546E7A")),
        ]
        for idx, (item, color) in enumerate(section_items, start=1):
            c.setFillColor(color)
            c.rect(MARGIN_L, index_y - 10, 14, 14, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(MARGIN_L + 7, index_y - 7, str(idx))
            c.setFillColor(colors.HexColor("#111827"))
            c.setFont("Helvetica", 10.5)
            c.drawString(MARGIN_L + 22, index_y - 6, item)
            index_y -= 20

        sig_y = MARGIN_B + 30
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.line(MARGIN_L, sig_y + 24, MARGIN_L + 220, sig_y + 24)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#374151"))
        c.drawString(MARGIN_L, sig_y + 12, "Elaborado por: Dupla — Coordinación BIM")
        c.drawString(MARGIN_L, sig_y, f"Exportado por: {self.exported_by}")
        c.drawString(PAGE_W / 2, sig_y, "Revisado por: ___________________________   Fecha: _______________")

    def _priority_summary_pages(self) -> None:
        self._finish_page(subtitle="Resumen por prioridad")
        assert self.canvas is not None
        c = self.canvas
        y = PAGE_H - MARGIN_T - 58
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(self.brand_color)
        c.drawString(MARGIN_L, y, "Resumen de clashes por prioridad")
        y -= 20
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(
            MARGIN_L,
            y,
            "Distribución de códigos para planificación de revisión en obra y coordinación entre disciplinas.",
        )
        y -= 22

        buckets = [
            ("critical", "Crítica"),
            ("high", "Alta"),
            ("medium", "Media"),
            ("low", "Baja"),
        ]
        counts_by_bucket: dict[str, int] = {}
        summary_rows: list[list[str]] = []
        for bucket, label in buckets:
            codes = [r.code for r in self.rows if r.severity_bucket == bucket]
            counts_by_bucket[bucket] = len(codes)
            pairs = sorted({r.comparacion_dwg for r in self.rows if r.severity_bucket == bucket})
            summary_rows.append(
                [
                    label,
                    str(len(codes)),
                    ", ".join(codes) if codes else "—",
                    "; ".join(_truncate(p, 40) for p in pairs[:6]) if pairs else "—",
                ]
            )

        headers = ["PRIORIDAD", "CANTIDAD", "CÓDIGOS", "PARES DWG COMPARADOS"]
        table_data = [headers] + summary_rows
        donut_size = 170
        donut_x = PAGE_W - MARGIN_R - donut_size
        donut_y = y - donut_size + 10
        usable_w_total = PAGE_W - MARGIN_L - MARGIN_R
        table_w = usable_w_total - donut_size - 18
        col_widths = [table_w * 0.18, table_w * 0.13, table_w * 0.34, table_w * 0.35]

        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle("psum_cell", parent=styles["Normal"], fontSize=8.5, leading=10.5)
        header_style = ParagraphStyle("psum_header", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white)
        priority_cell_style = ParagraphStyle(
            "psum_prio", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white, alignment=1
        )

        def _p(text: str, *, header: bool = False, priority: bool = False) -> Paragraph:
            style = header_style if header else (priority_cell_style if priority else cell_style)
            return _paragraph_from_text(text, style)

        rl_rows: list[list[Paragraph]] = [[_p(h, header=True) for h in headers]]
        for i, summary in enumerate(summary_rows):
            rl_rows.append(
                [
                    _p(summary[0], priority=True),
                    _p(summary[1]),
                    _p(summary[2]),
                    _p(summary[3]),
                ]
            )
        table = Table(rl_rows, colWidths=col_widths, repeatRows=1)
        style = _professional_table_style(header_bg="#1F2937")
        for i, (bucket, _) in enumerate(buckets, start=1):
            color = PRIORITY_PALETTE[bucket]
            style.add("BACKGROUND", (0, i), (0, i), color)
        table.setStyle(style)
        _, table_h = table.wrapOn(c, table_w, y)
        table.drawOn(c, MARGIN_L, y - table_h)

        _draw_donut(
            c,
            x=donut_x,
            y=donut_y,
            size=donut_size,
            counts_by_bucket=counts_by_bucket,
        )
        c.setFillColor(colors.HexColor("#6B7280"))
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(donut_x + donut_size / 2, donut_y - 8, "Distribución por prioridad")

        lifecycle_y = min(y - table_h, donut_y) - 36
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(MARGIN_L, lifecycle_y + 22, "Ciclo de vida de corrección")
        _draw_lifecycle_bar(
            c,
            x=MARGIN_L,
            y=lifecycle_y,
            width=PAGE_W - MARGIN_L - MARGIN_R,
            height=18,
            current_step="Detectado",
            completed_steps=set(),
        )
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#374151"))
        c.drawString(MARGIN_L, lifecycle_y - 14, _truncate(CORRECTION_LIFECYCLE, 170))

    def _checklist_matrix_pages(self) -> None:
        self._finish_page(subtitle="Matriz de chequeo")
        assert self.canvas is not None
        c = self.canvas
        y = PAGE_H - MARGIN_T - 58
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(self.brand_color)
        c.drawString(MARGIN_L, y, "Matriz de chequeo — coordinación de planos")
        y -= 18
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(
            MARGIN_L,
            y,
            "Use alias de plano (ver leyenda). La tabla de corrección registra DWG a corregir y estados en Dupla.",
        )
        y -= 22

        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            "checklist_cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            wordWrap="CJK",
        )
        header_style = ParagraphStyle(
            "checklist_header",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
        chip_style = ParagraphStyle(
            "checklist_chip",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=1,
            fontSize=7,
            leading=8,
        )
        coord_style = ParagraphStyle(
            "checklist_coord",
            parent=cell_style,
            fontName="Courier",
            fontSize=6.8,
            leading=8.2,
            wordWrap="CJK",
        )

        usable_w = PAGE_W - MARGIN_L - MARGIN_R

        def _p(text: str, *, header: bool = False, style: ParagraphStyle | None = None) -> Paragraph:
            base = header_style if header else (style or cell_style)
            return _paragraph_from_text(text, base)

        chunk_size = 14
        chunks = [self.rows[i : i + chunk_size] for i in range(0, max(len(self.rows), 1), chunk_size)] or [[]]
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index > 0:
                self._finish_page(subtitle="Matriz de chequeo (continuación)")
                y = PAGE_H - MARGIN_T - 58

            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(MARGIN_L, y, "Tabla principal")
            y -= 10

            core_widths = [usable_w * w for w in CHECKLIST_CORE_COL_WIDTHS]
            core_data = [[_p(col, header=True) for col in CHECKLIST_CORE_COLUMNS]]
            for row in chunk:
                core_data.append(
                    [
                        _p(row.code),
                        _p(row.plano_a),
                        _p(row.plano_b),
                        _p(row.nivel),
                        _p(_severity_es(row.severity_bucket), style=chip_style),
                        _p(row.ubicacion_comando, style=coord_style),
                        _p(_truncate(row.observacion, 90)),
                        _p(row.decision_revisor, style=chip_style),
                    ]
                )
            if not chunk:
                core_data.append([_p("—")] * len(CHECKLIST_CORE_COLUMNS))
            core_table = Table(core_data, colWidths=core_widths, repeatRows=1)
            core_style = _professional_table_style(header_bg="#1F2937")
            PRIORITY_COL, DECISION_COL = 4, 7
            for i, row in enumerate(chunk, start=1):
                core_style.add(
                    "BACKGROUND",
                    (PRIORITY_COL, i),
                    (PRIORITY_COL, i),
                    PRIORITY_PALETTE.get(row.severity_bucket, PRIORITY_PALETTE["medium"]),
                )
                core_style.add(
                    "BACKGROUND",
                    (DECISION_COL, i),
                    (DECISION_COL, i),
                    DECISION_CHIP_COLORS[_decision_bucket(row.decision_revisor)],
                )
            core_table.setStyle(core_style)
            _, core_h = core_table.wrapOn(c, usable_w, y)
            core_table.drawOn(c, MARGIN_L, y - core_h)
            y = y - core_h - 16

            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN_L, y, "Tabla de corrección y carga")
            y -= 10

            corr_widths = [usable_w * w for w in CHECKLIST_CORRECTION_COL_WIDTHS]
            corr_data = [[_p(col, header=True) for col in CHECKLIST_CORRECTION_COLUMNS]]
            for row in chunk:
                corr_data.append(
                    [
                        _p(row.code),
                        _p(row.dwg_corregir),
                        _p(row.estado_correccion, style=chip_style),
                        _p(row.estado_carga, style=chip_style),
                        _p(""),
                    ]
                )
            if not chunk:
                corr_data.append([_p("—")] * len(CHECKLIST_CORRECTION_COLUMNS))
            corr_table = Table(corr_data, colWidths=corr_widths, repeatRows=1)
            corr_style = _professional_table_style(header_bg="#374151")
            CORR_STATUS_COL, UPLOAD_COL = 2, 3
            for i, row in enumerate(chunk, start=1):
                corr_color = CORRECTION_STATUS_CHIP.get(row.estado_correccion, "#6B7280")
                up_color = UPLOAD_STATUS_CHIP.get(row.estado_carga, "#6B7280")
                corr_style.add(
                    "BACKGROUND", (CORR_STATUS_COL, i), (CORR_STATUS_COL, i), colors.HexColor(corr_color)
                )
                corr_style.add(
                    "BACKGROUND", (UPLOAD_COL, i), (UPLOAD_COL, i), colors.HexColor(up_color)
                )
            corr_table.setStyle(corr_style)
            _, corr_h = corr_table.wrapOn(c, usable_w, y)
            corr_table.drawOn(c, MARGIN_L, y - corr_h)

    def _draw_table(
        self,
        c: canvas.Canvas,
        table_data: list[list[str]],
        x: float,
        y: float,
        col_widths: list[float],
        *,
        font_size: float = 8,
    ) -> float:
        """Draw a table and return the Y coordinate below it."""
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle("tbl_cell", parent=styles["Normal"], fontSize=font_size, leading=font_size + 2)
        header_style = ParagraphStyle(
            "tbl_header", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white
        )

        def _p(text: str, *, header: bool = False) -> Paragraph:
            return _paragraph_from_text(text, header_style if header else cell_style)

        rows = [[_p(cell, header=(row_idx == 0)) for cell in row] for row_idx, row in enumerate(table_data)]
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(_professional_table_style(header_bg="#374151"))
        _, th = table.wrapOn(c, sum(col_widths), y)
        table.drawOn(c, x, y - th)
        return y - th

    def _visual_full_page(self, row: ClashSheetRow) -> None:
        """One critical/high incident per page with large DWG A vs DWG B panels."""
        self._finish_page(subtitle=f"Comparación DWG · {row.code}")
        assert self.canvas is not None
        content_top = PAGE_H - MARGIN_T - 52
        block_h = content_top - MARGIN_B - 8
        self._draw_incident_block(row, MARGIN_L, MARGIN_B + 8, PAGE_W - MARGIN_L - MARGIN_R, block_h, large=True)

    def _visual_compact_page(self, rows: list[ClashSheetRow], *, section: str) -> None:
        """Up to two medium/low incidents per page."""
        if not rows:
            return
        codes = ", ".join(r.code for r in rows)
        self._finish_page(subtitle=f"{section} · {codes}")
        assert self.canvas is not None
        content_top = PAGE_H - MARGIN_T - 52
        usable_h = content_top - MARGIN_B - 12
        gap = 10
        if len(rows) == 1:
            self._draw_incident_block(
                rows[0], MARGIN_L, MARGIN_B + 8, PAGE_W - MARGIN_L - MARGIN_R, usable_h - 8, large=False
            )
            return
        block_h = (usable_h - gap) / 2.0
        self._draw_incident_block(rows[0], MARGIN_L, MARGIN_B + 8 + block_h + gap, PAGE_W - MARGIN_L - MARGIN_R, block_h, large=False)
        self._draw_incident_block(rows[1], MARGIN_L, MARGIN_B + 8, PAGE_W - MARGIN_L - MARGIN_R, block_h, large=False)

    def _draw_incident_block(
        self,
        row: ClashSheetRow,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        large: bool,
    ) -> None:
        assert self.canvas is not None
        c = self.canvas
        priority_color = PRIORITY_PALETTE.get(row.severity_bucket, PRIORITY_PALETTE["medium"])

        c.setStrokeColor(priority_color)
        c.setLineWidth(1.0)
        c.rect(x, y, width, height, stroke=1, fill=0)

        header_h = 24 if large else 20
        c.setFillColor(priority_color)
        c.rect(x, y + height - header_h, width, header_h, stroke=0, fill=1)

        title_fs = 12 if large else 10
        meta_fs = 8.5 if large else 7.5
        header_text_y = y + height - header_h + (header_h - title_fs) / 2
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", title_fs)
        c.drawString(
            x + 10,
            header_text_y + 1,
            f"{row.code} · {row.tipo}  ·  {row.layer_pair}",
        )
        c.setFont("Helvetica-Bold", 9 if large else 8)
        c.drawRightString(
            x + width - 10,
            header_text_y + 1,
            f"Prioridad {_severity_es(row.severity_bucket)}",
        )

        cursor_y = y + height - header_h - 6

        zw_display = row.zoom_command if row.zoom_command != _NA else "Localizar en AutoCAD (Z E)"
        meta_lines = [
            (f"DWG A: {row.plano_a}  |  DWG B: {row.plano_b}", "bold"),
            (f"Nivel: {row.nivel}  ·  Capas: {row.layer_pair}", "regular"),
            (f"DWG a corregir: {row.dwg_corregir}  ·  Decisión: {row.decision_revisor}", "regular"),
            (f"Comando AutoCAD: {zw_display}", "mono"),
        ]
        for text, fmt in meta_lines:
            if fmt == "bold":
                c.setFont("Helvetica-Bold", meta_fs)
                c.setFillColor(colors.HexColor("#111827"))
            elif fmt == "mono":
                c.setFont("Courier", meta_fs)
                c.setFillColor(colors.HexColor("#374151"))
            else:
                c.setFont("Helvetica", meta_fs)
                c.setFillColor(colors.HexColor("#374151"))
            c.drawString(x + 10, cursor_y - meta_fs, _truncate(text, 150 if large else 135))
            cursor_y -= meta_fs + 3

        action_h = 50 if large else 40
        action_y = y + 12
        panel_gap = 8
        panel_area_top = cursor_y - 4
        panel_area_bottom = action_y + action_h + 6
        panel_h = max(panel_area_top - panel_area_bottom, 40)
        panel_w = (width - panel_gap - 20) / 2.0
        left_x = x + 10
        right_x = left_x + panel_w + panel_gap

        for idx, (svg_content, label, path) in enumerate(
            ((row.left_svg, row.plano_a, row.file_a_path), (row.right_svg, row.plano_b, row.file_b_path))
        ):
            px = left_x if idx == 0 else right_x
            c.setFont("Helvetica-Bold", meta_fs)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(px, panel_area_top - 2, f"{'DWG A' if idx == 0 else 'DWG B'} — {label}  [m]")
            frame_bottom = panel_area_bottom
            frame_h = panel_h - 12
            c.setStrokeColor(colors.HexColor("#9CA3AF"))
            c.rect(px, frame_bottom, panel_w, frame_h, stroke=1, fill=0)
            if svg_content and svg_content.strip():
                if not _draw_svg_in_rect(c, svg_content, px + 2, frame_bottom + 2, panel_w - 4, frame_h - 4):
                    _draw_visual_placeholder(c, px, frame_bottom, panel_w, frame_h, path, compact=not large)
            else:
                _draw_visual_placeholder(c, px, frame_bottom, panel_w, frame_h, path, compact=not large)

        c.setStrokeColor(self.brand_color)
        c.setFillColor(DUPLA_BRAND["surface_tint"])
        c.rect(x + 4, action_y, width - 8, action_h, stroke=1, fill=1)
        c.setFillColor(self.brand_color)
        c.setFont("Helvetica-Bold", meta_fs)
        c.drawString(x + 10, action_y + action_h - 12, "ACCIÓN REQUERIDA")
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica", meta_fs)
        c.drawString(
            x + 110,
            action_y + action_h - 12,
            _truncate(row.observacion, 165 if large else 140),
        )
        c.setFillColor(colors.HexColor("#374151"))
        c.drawString(
            x + 10,
            action_y + action_h - 24,
            _truncate(f"Acción: {row.accion_sugerida}", 175 if large else 150),
        )
        c.setFillColor(colors.HexColor("#4B5563"))
        c.setFont("Helvetica", meta_fs - 0.5)
        c.drawString(
            x + 10,
            action_y + 6,
            _truncate(
                f"Corregir: {row.dwg_corregir} · Subir revisión en Clashes (corrida {self.run_label}) — no reemplazar el DWG original.",
                190 if large else 165,
            ),
        )

        decision_key = _decision_bucket(row.decision_revisor)
        choices = [
            ("Real", "real", DECISION_CHIP_COLORS["real"]),
            ("Falso positivo", "falso_positivo", DECISION_CHIP_COLORS["falso_positivo"]),
            ("Pendiente", "pendiente", DECISION_CHIP_COLORS["pendiente"]),
        ]
        box = 9
        cx = x + width - 10
        for label, key, color in reversed(choices):
            tw = c.stringWidth(label, "Helvetica-Bold", meta_fs - 0.5)
            cx -= tw + 4
            c.setFillColor(colors.HexColor("#111827"))
            c.setFont("Helvetica-Bold", meta_fs - 0.5)
            c.drawString(cx, action_y + 7, label)
            cx -= box + 4
            if key == decision_key:
                c.setFillColor(color)
                c.setStrokeColor(color)
                c.rect(cx, action_y + 5, box, box, stroke=1, fill=1)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", box - 2)
                c.drawCentredString(cx + box / 2, action_y + 7, "✓")
            else:
                c.setFillColor(colors.white)
                c.setStrokeColor(colors.HexColor("#9CA3AF"))
                c.rect(cx, action_y + 5, box, box, stroke=1, fill=1)
            cx -= 8

    def _visual_comparison_page(self, row: ClashSheetRow, *, section: str) -> None:
        """Deprecated alias — use _visual_full_page."""
        self._visual_full_page(row)

    def _validation_log_pages(self) -> None:
        self._finish_page(subtitle="Bitácora de validación / corrección")
        assert self.canvas is not None
        c = self.canvas
        y = PAGE_H - MARGIN_T - 58
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(self.brand_color)
        c.drawString(MARGIN_L, y, "Bitácora de validación y corrección")
        y -= 18
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(
            MARGIN_L,
            y,
            "Registre la decisión del revisor, el DWG corregido y el avance del estado de corrección.",
        )
        y -= 20

        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle("val_cell", parent=styles["Normal"], fontSize=7.5, leading=8.5)
        header_style = ParagraphStyle("val_header", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white)
        chip_style = ParagraphStyle(
            "val_chip",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=1,
            fontSize=7.5,
            leading=8.5,
        )
        totals_style = ParagraphStyle(
            "val_totals",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
        )
        usable_w = PAGE_W - MARGIN_L - MARGIN_R
        col_widths = [usable_w * w for w in BITACORA_COL_WIDTHS]

        def _p(text: str, *, header: bool = False, style: ParagraphStyle | None = None) -> Paragraph:
            base = header_style if header else (style or cell_style)
            return _paragraph_from_text(text, base)

        correction_totals = Counter(r.estado_correccion for r in self.rows)
        upload_totals = Counter(r.estado_carga for r in self.rows)
        top_correction = correction_totals.most_common(1)[0][0] if correction_totals else "—"
        top_upload = upload_totals.most_common(1)[0][0] if upload_totals else "—"

        chunk_size = 18
        chunks = [self.rows[i : i + chunk_size] for i in range(0, max(len(self.rows), 1), chunk_size)] or [[]]
        last_chunk_index = len(chunks) - 1
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index > 0:
                self._finish_page(subtitle="Bitácora (continuación)")
                y = PAGE_H - MARGIN_T - 58
            table_data = [[_p(h, header=True) for h in BITACORA_COLUMNS]]
            for row in chunk:
                initial = "—"
                resp_text = (row.warnings or []) and "" or ""
                if resp_text:
                    initial = resp_text[:1].upper()
                table_data.append(
                    [
                        _p(row.code),
                        _p(row.dwg_corregir),
                        _p(row.estado_correccion, style=chip_style),
                        _p(row.estado_carga, style=chip_style),
                        _p(""),
                        _p(""),
                        _p(initial),
                    ]
                )
            if not chunk:
                table_data.append([_p("—")] * len(BITACORA_COLUMNS))
            totals_row_idx: int | None = None
            if chunk_index == last_chunk_index and self.rows:
                totals_row_idx = len(table_data)
                table_data.append(
                    [
                        _p(f"Σ {len(self.rows)}", style=totals_style),
                        _p("Totales bitácora", style=totals_style),
                        _p(top_correction, style=chip_style),
                        _p(top_upload, style=chip_style),
                        _p("", style=totals_style),
                        _p("", style=totals_style),
                        _p("", style=totals_style),
                    ]
                )

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            style = _professional_table_style(header_bg="#374151")
            CORR_COL, UPLOAD_COL = 2, 3
            for i, row in enumerate(chunk, start=1):
                corr_color = CORRECTION_STATUS_CHIP.get(row.estado_correccion, "#6B7280")
                up_color = UPLOAD_STATUS_CHIP.get(row.estado_carga, "#6B7280")
                style.add("BACKGROUND", (CORR_COL, i), (CORR_COL, i), colors.HexColor(corr_color))
                style.add("BACKGROUND", (UPLOAD_COL, i), (UPLOAD_COL, i), colors.HexColor(up_color))
            if totals_row_idx is not None:
                style.add(
                    "BACKGROUND",
                    (0, totals_row_idx),
                    (-1, totals_row_idx),
                    colors.HexColor("#F3F4F6"),
                )
                style.add(
                    "LINEABOVE",
                    (0, totals_row_idx),
                    (-1, totals_row_idx),
                    1.2,
                    colors.HexColor("#9CA3AF"),
                )
                style.add(
                    "BACKGROUND",
                    (CORR_COL, totals_row_idx),
                    (CORR_COL, totals_row_idx),
                    colors.HexColor(CORRECTION_STATUS_CHIP.get(top_correction, "#6B7280")),
                )
                style.add(
                    "BACKGROUND",
                    (UPLOAD_COL, totals_row_idx),
                    (UPLOAD_COL, totals_row_idx),
                    colors.HexColor(UPLOAD_STATUS_CHIP.get(top_upload, "#6B7280")),
                )
            table.setStyle(style)
            _, th = table.wrapOn(c, usable_w, y)
            table.drawOn(c, MARGIN_L, y - th)

    def _corrected_delivery_page(self) -> None:
        self._finish_page(subtitle="Entrega de planos corregidos")
        assert self.canvas is not None
        c = self.canvas
        y = PAGE_H - MARGIN_T - 58
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(MARGIN_L, y, "Entrega de planos corregidos")
        y -= 22
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#111827"))
        for paragraph in corrected_delivery_section_lines():
            c.drawString(MARGIN_L, y, _truncate(paragraph, 155))
            y -= 16
        y -= 8
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_L, y, "Pasos operativos")
        y -= 16
        c.setFont("Helvetica", 10)
        for index, step in enumerate(corrected_delivery_steps(), start=1):
            c.drawString(MARGIN_L, y, _truncate(f"{index}. {step}", 155))
            y -= 15
        y -= 6
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#374151"))
        c.drawString(MARGIN_L, y, f"Ciclo de vida: {CORRECTION_LIFECYCLE}")

    def _upload_instructions_page(self) -> None:
        """Deprecated — use _corrected_delivery_page."""
        self._corrected_delivery_page()

    def _alias_legend_page(self) -> None:
        self._finish_page(subtitle="Leyenda de archivos / alias")
        assert self.canvas is not None
        c = self.canvas
        y = PAGE_H - MARGIN_T - 58
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN_L, y, "Leyenda de archivos y alias")
        y -= 20
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(MARGIN_L, y, "Alias usado en tablas y láminas visuales → ruta completa en el proyecto.")
        y -= 18

        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle("alias_cell", parent=styles["Normal"], fontSize=8, leading=9)
        header_style = ParagraphStyle("alias_header", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white)
        usable_w = PAGE_W - MARGIN_L - MARGIN_R
        col_widths = [usable_w * 0.28, usable_w * 0.72]

        def _p(text: str, *, header: bool = False) -> Paragraph:
            return _paragraph_from_text(text, header_style if header else cell_style)

        table_data = [[_p("Alias", header=True), _p("Archivo / ruta", header=True)]]
        for full_path, alias in sorted(self.aliases.items(), key=lambda item: item[1].lower()):
            table_data.append([_p(alias), _p(full_path)])
        if len(table_data) == 1:
            table_data.append([_p("—"), _p("No hay archivos en este run.")])
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(_professional_table_style(header_bg="#374151"))
        _, th = table.wrapOn(c, usable_w, y)
        table.drawOn(c, MARGIN_L, y - th)


def _paragraph_from_text(text: str, style: ParagraphStyle) -> Paragraph:
    """Build a ReportLab paragraph; newlines become visible line breaks (not literal &lt;br/&gt;)."""
    lines = [line for line in str(text or "—").split("\n") if line is not None]
    if not lines:
        lines = ["—"]
    safe_lines = [
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in lines
    ]
    markup = "<br/>".join(safe_lines)
    return Paragraph(markup, style)


def _draw_svg_in_rect(
    c: canvas.Canvas,
    svg_content: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> bool:
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF

        drawing = svg2rlg(BytesIO(svg_content.encode("utf-8")))
        if drawing is None or not drawing.width or not drawing.height:
            return _draw_svg_png_fallback(c, svg_content, x, y, width, height)
        scale = min(width / drawing.width, height / drawing.height)
        c.saveState()
        c.translate(x, y)
        c.scale(scale, scale)
        renderPDF.draw(drawing, c, 0, 0)
        c.restoreState()
        return True
    except Exception as exc:
        logger.debug("svglib render failed: %s", exc)
        return _draw_svg_png_fallback(c, svg_content, x, y, width, height)


def _draw_svg_png_fallback(
    c: canvas.Canvas,
    svg_content: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> bool:
    try:
        import cairosvg
        from reportlab.lib.utils import ImageReader

        png_bytes = cairosvg.svg2png(bytestring=svg_content.encode("utf-8"))
        c.drawImage(ImageReader(io.BytesIO(png_bytes)), x, y, width=width, height=height, preserveAspectRatio=True, anchor="sw")
        return True
    except Exception:
        return False


def _draw_visual_placeholder(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    file_path: str,
    *,
    compact: bool = False,
) -> None:
    c.setFillColor(colors.HexColor("#F3F4F6"))
    c.rect(x + 2, y + 2, width - 4, height - 4, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.setFont("Helvetica", 8 if compact else 9)
    c.drawCentredString(x + width / 2, y + height / 2 + 10, PLACEHOLDER_MSG)
    c.setFont("Helvetica", 7 if compact else 7.5)
    c.drawCentredString(x + width / 2, y + height / 2 - 4, _truncate(Path(file_path).name if file_path else _NA, 50))
