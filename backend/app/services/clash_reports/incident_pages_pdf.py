"""Architectural checklist PDF: cover, table, index, per-incident pages, technical annex.

Consumes workflow rows and PR3 visual artifacts. Does not recalculate geometry or severity.

Future optimization (not PR4): rasterize/cache large SVG plates, PDF compression, or
incident caps when hundreds of full-page SVGs inflate file size.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    NextPageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.clash_incident_contract import is_confirmed_workflow_incident, normalize_incident_code
from app.domain.clash_severity import severity_label_es
from app.domain.clash_workflow_enums import ClashStatus, status_label
from app.models.project_clash_item import ProjectClashItem
from app.services.clash_reports.coordination_report_pdf import (
    BRAND_RED,
    GRID,
    MUTED,
    SEV_COLORS,
    SEV_ES,
    _CONTENT_W,
    _CoordDoc,
    _P,
    _chip,
    _data_table,
    _esc,
    _styles,
    _zoom_command,
)

TileResolver = Callable[[ProjectClashItem, str], Path | None]

VISUAL_UNAVAILABLE_MSG = (
    "Visual real no disponible para esta incidencia. Revisar anexo técnico."
)
SVG_EMBED_FAILED_SUFFIX = " No se pudo embeber el SVG compuesto."

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

def _workflow_contract(item: ProjectClashItem) -> dict[str, Any]:
    raw = item.raw_json if isinstance(item.raw_json, dict) else {}
    contract = raw.get("_workflow_contract")
    return contract if isinstance(contract, dict) else {}


def _has_real_visual(item: ProjectClashItem) -> bool:
    return bool(_workflow_contract(item).get("has_real_visual"))


def _pdf_eligible(item: ProjectClashItem) -> bool:
    raw = item.raw_json if isinstance(item.raw_json, dict) else {}
    if not raw:
        return True
    return is_confirmed_workflow_incident(raw)


def _incident_code(item: ProjectClashItem) -> str:
    return normalize_incident_code(item.clash_code)


def _title_semantic(item: ProjectClashItem) -> str:
    if item.title_semantic:
        return item.title_semantic
    base = item.base_plan_number or item.dwg_a or "PLAN"
    compared = item.compared_plan_number or item.dwg_b or "PLAN"
    sev = severity_label_es(item.severity or "low")
    return f"{base}_BASE / {_incident_code(item)} / Contra {compared} / Severidad {sev}"


def _table_comment(item: ProjectClashItem) -> str:
    return (item.table_comment or item.observation or "Sin observación registrada.").strip()


def _short_label(item: ProjectClashItem) -> str:
    return (item.short_label or item.recommended_action or _incident_code(item)).strip()


def _checklist_sort_key(item: ProjectClashItem) -> tuple[int, str, str, str]:
    severity = str(item.severity or "low").lower()
    return (
        _SEVERITY_ORDER.get(severity, 9),
        _incident_code(item),
        item.base_plan_number or item.dwg_a or "",
        item.compared_plan_number or item.dwg_b or "",
    )


def _sort_checklist_items(items: list[ProjectClashItem]) -> list[ProjectClashItem]:
    eligible = [i for i in items if _pdf_eligible(i)]
    return sorted(eligible, key=_checklist_sort_key)


def _warning_paragraph(message: str, st: dict) -> Paragraph:
    warn_style = ParagraphStyle(
        "visual_warn",
        parent=st["body"],
        backColor=colors.HexColor("#FEF3C7"),
        borderPadding=8,
        textColor=colors.HexColor("#92400E"),
    )
    return Paragraph(_esc(message), warn_style)


def _severity_summary(items: list[ProjectClashItem]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in items:
        key = str(item.severity or "low").lower()
        if key in counts:
            counts[key] += 1
    return counts


def _source_refs(item: ProjectClashItem) -> tuple[str, str]:
    raw = item.raw_json if isinstance(item.raw_json, dict) else {}
    rep = raw.get("representative_conflict") or {}
    refs = rep.get("source_refs") or []
    if not isinstance(refs, list):
        refs = []
    a = str(refs[0]) if len(refs) > 0 and refs[0] else "—"
    b = str(refs[1]) if len(refs) > 1 and refs[1] else "—"
    return a, b


def _handle_from_ref(ref: str) -> str:
    parts = str(ref or "").split("|")
    return parts[-1] if parts else "—"


def _svg_drawing(path: Path | None, *, max_w: float, max_h: float | None = None):
    if path is None or not path.is_file() or path.suffix.lower() != ".svg":
        return None
    try:
        from svglib.svglib import svg2rlg

        drawing = svg2rlg(str(path))
        if drawing is None or not drawing.width:
            return None
        scale = max_w / drawing.width
        if max_h is not None and drawing.height * scale > max_h:
            scale = min(scale, max_h / drawing.height)
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
        return drawing
    except Exception:
        return None


def _resolve_visual_paths(
    item: ProjectClashItem,
    tile_resolver: TileResolver | None,
) -> tuple[Path | None, Path | None]:
    if tile_resolver is None or not _has_real_visual(item):
        return None, None
    composed = tile_resolver(item, "composed")
    zoom = tile_resolver(item, "zoom")
    return composed, zoom


def _checklist_cover(meta: dict[str, Any], items: list[ProjectClashItem], st: dict, *, job_id: str | None) -> list:
    title = str(meta.get("project_name") or "Proyecto")
    emission = str(meta.get("run_date") or "")
    folder = str(meta.get("folder_name") or "")
    sev = _severity_summary(items)
    band = Table(
        [
            [_P(title, "cover_title", st)],
            [_P("Lista de chequeo arquitectónica — incidencias confirmadas", "cover_sub", st)],
            [_P(f"Carpeta · {folder} · Emisión {emission}", "cover_small", st)],
            [_P(f"Job · {job_id or '—'} · Incidencias · {len(items)}", "cover_small", st)],
        ],
        colWidths=[_CONTENT_W],
    )
    band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 16),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
            ]
        )
    )
    sev_rows = [
        [_chip(f"Crítica · {sev['critical']}", SEV_COLORS["critical"], st)],
        [_chip(f"Alta · {sev['high']}", SEV_COLORS["high"], st)],
        [_chip(f"Media · {sev['medium']}", SEV_COLORS["medium"], st)],
        [_chip(f"Baja · {sev['low']}", SEV_COLORS["low"], st)],
    ]
    sev_table = Table(sev_rows, colWidths=[(_CONTENT_W - 12 * mm) / 4] * 4)
    sev_table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return [
        band,
        Spacer(1, 12),
        _P("Resumen por severidad", "h3", st),
        sev_table,
        Spacer(1, 10),
        _P(
            "Cada incidencia confirmada incluye plano completo base + overlay. "
            "Los candidatos de fase amplia (broad/AABB) no aparecen en este informe.",
            "small",
            st,
        ),
        NextPageTemplate("content"),
        PageBreak(),
    ]


def _main_checklist_table(items: list[ProjectClashItem], st: dict) -> list:
    rows = []
    for item in items:
        try:
            st_label = status_label(ClashStatus(item.status))
        except ValueError:
            st_label = item.status or "—"
        rows.append(
            [
                _P(_incident_code(item), "cell", st),
                _P(item.base_plan_number or item.dwg_a or "—", "cell", st),
                _P(item.compared_plan_number or item.dwg_b or "—", "cell", st),
                _P(
                    " / ".join(x for x in (item.discipline_a, item.discipline_b) if x) or "—",
                    "cell",
                    st,
                ),
                _chip(SEV_ES.get(item.severity, item.severity or "—"), SEV_COLORS.get(item.severity, MUTED), st),
                _P(item.level_id or "—", "cell", st),
                _P(_table_comment(item), "cell", st),
                _P(item.recommended_action or item.short_label or "—", "cell", st),
                _P(st_label, "cell", st),
                _P(_zoom_command(item) or "—", "cell_mono", st),
            ]
        )
    return [
        _P("Tabla principal — lista de chequeo", "h2", st),
        _P("La columna Observación usa el comentario de tabla (table_comment).", "small", st),
        Spacer(1, 4),
        _data_table(
            [
                "INC",
                "Base",
                "Comparado",
                "Disciplinas",
                "Severidad",
                "Nivel",
                "Observación",
                "Acción",
                "Estado",
                "AutoCAD",
            ],
            rows,
            [16 * mm, 22 * mm, 22 * mm, 28 * mm, 18 * mm, 14 * mm, 48 * mm, 32 * mm, 20 * mm, 30 * mm],
            st,
        ),
        NextPageTemplate("content"),
        PageBreak(),
    ]


def _incident_index(items: list[ProjectClashItem], st: dict) -> list:
    rows = []
    for idx, item in enumerate(items, start=1):
        visual = "Sí" if _has_real_visual(item) else "No"
        try:
            st_label = status_label(ClashStatus(item.status))
        except ValueError:
            st_label = item.status or "—"
        rows.append(
            [
                _P(_incident_code(item), "cell", st),
                _P(_title_semantic(item), "cell", st),
                _chip(SEV_ES.get(item.severity, "—"), SEV_COLORS.get(item.severity, MUTED), st),
                _P(f"§{idx}", "cell", st),
                _P(st_label, "cell", st),
                _P(visual, "cell", st),
            ]
        )
    return [
        _P("Índice de incidencias", "h2", st),
        Spacer(1, 4),
        _data_table(
            ["INC", "Título semántico", "Severidad", "Sección", "Estado", "Visual real"],
            rows,
            [18 * mm, 78 * mm, 22 * mm, 16 * mm, 28 * mm, 20 * mm],
            st,
        ),
        NextPageTemplate("content"),
        PageBreak(),
    ]


def _incident_page(
    item: ProjectClashItem,
    st: dict,
    *,
    tile_resolver: TileResolver | None,
    section_no: int,
) -> list:
    composed_path, zoom_path = _resolve_visual_paths(item, tile_resolver)
    ref_a, ref_b = _source_refs(item)
    handle_a = _handle_from_ref(ref_a)
    handle_b = _handle_from_ref(ref_b)

    main_w = _CONTENT_W
    side_w = _CONTENT_W * 0.42
    main_visual = None
    if _has_real_visual(item):
        main_visual = _svg_drawing(composed_path, max_w=main_w, max_h=115 * mm)

    page_flow: list = [
        _P(f"Incidencia {section_no} · {_title_semantic(item)}", "h2", st),
        _P(_short_label(item), "body", st),
        Spacer(1, 6),
    ]
    if main_visual is not None:
        page_flow.append(main_visual)
    else:
        message = VISUAL_UNAVAILABLE_MSG
        if _has_real_visual(item) and composed_path is not None:
            message += SVG_EMBED_FAILED_SUFFIX
        page_flow.append(_warning_paragraph(message, st))
    page_flow.append(Spacer(1, 6))

    panel_rows = [
        [_P("Etiqueta corta", "small", st), _P(_short_label(item), "cell", st)],
        [_P("AutoCAD", "small", st), _P(_zoom_command(item) or "—", "cell_mono", st)],
        [_P("Plano base", "small", st), _P(item.base_plan_number or item.dwg_a or "—", "cell", st)],
        [_P("Plano comparado", "small", st), _P(item.compared_plan_number or item.dwg_b or "—", "cell", st)],
        [_P("Layer base", "small", st), _P(item.layer_a or "—", "cell", st)],
        [_P("Layer comparado", "small", st), _P(item.layer_b or "—", "cell", st)],
        [_P("Handle base", "small", st), _P(handle_a, "cell_mono", st)],
        [_P("Handle comparado", "small", st), _P(handle_b, "cell_mono", st)],
        [_P("Estado", "small", st), _P(item.status or "—", "cell", st)],
        [_P("Acción sugerida", "small", st), _P(item.recommended_action or "—", "cell", st)],
    ]
    panel = Table(panel_rows, colWidths=[side_w * 0.38, side_w * 0.62])
    panel.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    page_flow.append(panel)

    if zoom_path is not None and zoom_path.is_file() and _has_real_visual(item):
        inset = _svg_drawing(zoom_path, max_w=side_w, max_h=32 * mm)
        if inset is not None:
            page_flow += [Spacer(1, 6), _P("Zoom (inset secundario)", "small", st), inset]

    return [*page_flow, NextPageTemplate("content"), PageBreak()]


def _technical_annex(items: list[ProjectClashItem], st: dict) -> list:
    rows = []
    for item in items:
        contract = _workflow_contract(item)
        raw = item.raw_json if isinstance(item.raw_json, dict) else {}
        rep = raw.get("representative_conflict") or {}
        overlap = raw.get("overlap_geometry") or rep.get("overlap_geometry") or "—"
        ref_a, ref_b = _source_refs(item)
        warnings = ", ".join(contract.get("visual_warnings") or []) or "—"
        rows.append(
            [
                _P(item.clash_code, "cell_mono", st),
                _P(_title_semantic(item), "cell", st),
                _P(item.severity or "—", "cell", st),
                _P(severity_label_es(item.severity or "low"), "cell", st),
                _P(f"{item.base_plan_number or '—'} / {item.compared_plan_number or '—'}", "cell", st),
                _P(
                    f"({item.centroid_x_mm:.0f}, {item.centroid_y_mm:.0f})"
                    if item.centroid_x_mm is not None and item.centroid_y_mm is not None
                    else "—",
                    "cell_mono",
                    st,
                ),
                _P(
                    str(
                        [
                            item.bounds_minx_mm,
                            item.bounds_miny_mm,
                            item.bounds_maxx_mm,
                            item.bounds_maxy_mm,
                        ]
                    ),
                    "cell_mono",
                    st,
                ),
                _P(str(overlap)[:120], "cell_mono", st),
                _P(f"{ref_a} | {ref_b}", "cell_mono", st),
                _P(f"{item.layer_a or '—'} / {item.layer_b or '—'}", "cell", st),
                _P(str(contract.get("has_real_visual", False)), "cell", st),
                _P(warnings, "cell", st),
            ]
        )
    return [
        _P("Anexo técnico", "h2", st),
        _P("Metadatos de incidencia confirmada, geometría y procedencia visual.", "small", st),
        Spacer(1, 4),
        _data_table(
            [
                "ID",
                "Título",
                "Sev",
                "Etiqueta",
                "Planos",
                "Centroide",
                "BBox",
                "Overlap",
                "Source refs",
                "Layers",
                "Visual real",
                "Warnings",
            ],
            rows,
            [14 * mm] * 12,
            st,
        ),
    ]


def build_incident_checklist_pdf(
    *,
    meta: dict[str, Any],
    items: list[ProjectClashItem],
    revision_label: str = "V.01",
    tile_resolver: TileResolver | None = None,
    job_id: str | None = None,
) -> bytes:
    """Build the architectural checklist PDF (final human deliverable)."""
    st = _styles()
    ordered = _sort_checklist_items(items)
    breadcrumb = f"Checklist · {meta.get('project_name', '')}"

    story: list = []
    story += _checklist_cover(meta, ordered, st, job_id=job_id)
    story += _main_checklist_table(ordered, st)
    story += _incident_index(ordered, st)
    for idx, item in enumerate(ordered, start=1):
        story += _incident_page(item, st, tile_resolver=tile_resolver, section_no=idx)
    story += _technical_annex(ordered, st)

    buf = BytesIO()
    doc = _CoordDoc(buf, breadcrumb=breadcrumb, revision_label=revision_label)
    story.insert(0, NextPageTemplate("cover"))
    doc.build(story)
    return buf.getvalue()


def build_incident_checklist_flowables(
    *,
    items: list[ProjectClashItem],
    meta: dict[str, Any],
    st: dict | None = None,
    tile_resolver: TileResolver | None = None,
) -> list:
    """Optional flowables slice for embedding in other reports."""
    styles = st or _styles()
    ordered = _sort_checklist_items(items)
    flow: list = []
    flow += _main_checklist_table(ordered, styles)
    flow += _incident_index(ordered, styles)
    for idx, item in enumerate(ordered, start=1):
        flow += _incident_page(item, styles, tile_resolver=tile_resolver, section_no=idx)
    flow += _technical_annex(ordered, styles)
    return flow
