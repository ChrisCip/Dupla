"""Technical clash audit PDF for developers/coordinators."""

from __future__ import annotations

from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Spacer

from app.services.clash_reports.data import ReportBundle
from app.services.clash_reports.formatting import (
    SEVERITY_HIGH_AREA_M2,
    SEVERITY_HIGH_Z_MM,
    SEVERITY_MEDIUM_AREA_M2,
    SEVERITY_MEDIUM_Z_MM,
    format_center_index,
    format_optional,
    format_zoom_index,
)
from app.services.clash_reports.pdf_base import (
    P,
    P_alias,
    P_alias_pair,
    P_cell,
    P_cell_id,
    P_cell_lines,
    build_pdf,
    data_table,
    field_table,
    landscape_page_width,
    meta_block,
    page_break_landscape,
    page_break_portrait,
    section,
)

_PAGE_W = A4[0] - 36 * mm
_LS_W = landscape_page_width()

# Index column weight fractions (sum = 1.0); scaled to landscape width in data_table.
_INDEX_COL_WEIGHTS = [
    0.09,  # ID
    0.05,  # Codigo
    0.15,  # Par
    0.06,  # Nivel
    0.06,  # Tipo
    0.05,  # Conf.
    0.05,  # Sev.
    0.06,  # Area
    0.05,  # Z prof.
    0.13,  # Centro
    0.25,  # Z W
]


def _index_col_widths() -> list[float]:
    return [w * _LS_W for w in _INDEX_COL_WEIGHTS]


def _run_metadata(bundle: ReportBundle) -> list:
    primary = bundle.primary
    context = bundle.context
    counts = context.get("counts") or {}
    tolerances = context.get("tolerances") or {}
    rows = [
        ("Directorio de salida", format_optional(bundle.output_dir)),
        ("Perfil de analisis", format_optional(primary.get("analysis_profile") or context.get("analysis_profile"))),
        ("Modo de deteccion", "2.5D (coord. plana + solape Z)"),
        ("Unidades", "milimetros (mm)"),
        ("Sistema de coordenadas", "origen compartido del proyecto / site origin"),
        (
            "Umbrales de severidad (regla)",
            f"Alta: Z>={SEVERITY_HIGH_Z_MM} mm o area>={SEVERITY_HIGH_AREA_M2} m2; "
            f"Media: Z>={SEVERITY_MEDIUM_Z_MM} mm o area>={SEVERITY_MEDIUM_AREA_M2} m2",
        ),
        ("Tolerancias", str(tolerances) if tolerances else "no disponible"),
        ("Pares programados", str(counts.get("scheduled_pairs", "no disponible"))),
        ("Archivos fuente", str(counts.get("scheduled_files", "no disponible"))),
    ]
    return [meta_block(rows), Spacer(1, 8)]


def _pair_schedule_table(bundle: ReportBundle) -> list:
    pairs = [p for p in (bundle.pair_schedule.get("pairs") or []) if isinstance(p, dict)]
    if not pairs:
        return [P("Programacion de pares no disponible.", "body"), Spacer(1, 6)]
    rows = []
    for idx, pair in enumerate(pairs, start=1):
        fa = str(pair.get("file_a") or pair.get("dwg_a") or "")
        fb = str(pair.get("file_b") or pair.get("dwg_b") or "")
        alias_a = bundle.alias_registry.alias_for(fa, discipline=str(pair.get("discipline_a") or ""))
        alias_b = bundle.alias_registry.alias_for(fb, discipline=str(pair.get("discipline_b") or ""))
        rows.append(
            [
                P_cell(f"P{idx:03d}", dense=True),
                P_alias_pair(alias_a, alias_b),
                P_cell(format_optional(pair.get("level_id") or pair.get("level")), dense=True),
                P_cell(
                    f"{format_optional(pair.get('discipline_a'))} / {format_optional(pair.get('discipline_b'))}",
                    dense=True,
                ),
                P_cell("programado" if pair.get("scheduled", True) else "omitido", dense=True),
            ]
        )
    return [
        data_table(
            ["Par #", "Archivos (alias)", "Nivel", "Disciplinas", "Estado"],
            rows,
            col_widths=[w * _PAGE_W for w in (0.08, 0.34, 0.14, 0.32, 0.12)],
            page_width=_PAGE_W,
            dense=True,
        ),
        Spacer(1, 8),
    ]


def _metrics_dashboard(bundle: ReportBundle) -> list:
    primary = bundle.primary
    context = bundle.context
    counts = context.get("counts") or {}
    conf_mix = context.get("confidence_mix") or Counter(i.confidence for i in bundle.incidents)
    sev_mix = context.get("severity_mix") or Counter(i.severity for i in bundle.incidents)
    level_mix = Counter(i.level_id for i in bundle.incidents)

    rows = [
        ["Archivos analizados", str(counts.get("scheduled_files", len(bundle.analyzed_documents)))],
        ["Pares programados", str(counts.get("scheduled_pairs", len(bundle.pair_schedule.get("pairs") or [])))],
        ["Incidencias primarias", str(len(bundle.incidents))],
        ["Conflictos primarios", str(primary.get("incident_conflict_count", sum(i.member_count for i in bundle.incidents)))],
        ["Area total", f"{sum(i.area_mm2 for i in bundle.incidents) / 1_000_000:.2f} m2"],
        ["Por confianza", ", ".join(f"{k}: {v}" for k, v in dict(conf_mix).items()) or "no disponible"],
        ["Por severidad", ", ".join(f"{k}: {v}" for k, v in dict(sev_mix).items()) or "no disponible"],
        ["Por nivel", ", ".join(f"{k}: {v}" for k, v in dict(level_mix).items()) or "no disponible"],
    ]
    return [
        field_table([(str(r[0]), str(r[1])) for r in rows], label_width=55 * mm),
        Spacer(1, 8),
    ]


def _incident_index(bundle: ReportBundle) -> list:
    """Landscape index with wrapped Paragraph cells; full fields in detail section."""
    if not bundle.incidents:
        return [P("Sin incidencias.", "body"), Spacer(1, 6)]

    rows = [
        [
            P_cell_id(inc.incident_id),
            P_cell(inc.human_code, index=True),
            P_alias_pair(inc.file_a_alias, inc.file_b_alias),
            P_cell(inc.level_id, index=True),
            P_cell(inc.clash_type, index=True),
            P_cell(inc.confidence, index=True),
            P_cell(inc.severity, index=True),
            P_cell(inc.area_m2_text, index=True),
            P_cell(inc.z_depth_text, index=True),
            P_cell_lines(format_center_index(inc.center_text), index=True),
            P_cell(format_zoom_index(inc.zoom_command), index=True),
        ]
        for inc in bundle.incidents
    ]
    headers = [
        "ID",
        "Codigo",
        "Par",
        "Nivel",
        "Tipo",
        "Conf.",
        "Sev.",
        "Area",
        "Z",
        "Centro",
        "Z W",
    ]
    return [
        *page_break_landscape(),
        P("Indice de incidencias", "h2"),
        Spacer(1, 4),
        P(
            "Campos completos (limites, handles, provenance) en la seccion "
            "Detalle tecnico por incidencia.",
            "small",
        ),
        Spacer(1, 4),
        data_table(
            headers,
            rows,
            col_widths=_index_col_widths(),
            page_width=_LS_W,
            index_mode=True,
        ),
        Spacer(1, 8),
        *page_break_portrait(),
    ]


def _incident_details(bundle: ReportBundle) -> list:
    blocks: list = []
    for inc in bundle.incidents:
        p = inc.provenance
        blocks.append(P(f"Detalle tecnico - {inc.human_code} ({inc.incident_id})", "h3"))
        blocks.append(
            field_table(
                [
                    ("ID programa", inc.incident_id),
                    ("Codigo humano", inc.human_code),
                    ("Grupo", inc.group_code),
                    ("Par completo", f"{inc.file_a_full} x {inc.file_b_full}"),
                    ("Par alias", f"{inc.file_a_alias} x {inc.file_b_alias}"),
                    ("Nivel", inc.level_id),
                    ("Tipo", inc.clash_type),
                    ("Confianza", inc.confidence),
                    ("Severidad (regla)", inc.severity),
                    ("Area", inc.area_m2_text),
                    ("Profundidad Z", inc.z_depth_text),
                    ("Centro", inc.center_text),
                    ("Limites", inc.bounds_text),
                    ("Comando AutoCAD", inc.zoom_command or inc.zoom_fallback or "no disponible"),
                    ("Capas", f"{format_optional(inc.layer_a)} / {format_optional(inc.layer_b)}"),
                    ("Handles", f"{format_optional(inc.handle_a)} / {format_optional(inc.handle_b)}"),
                    ("Elementos", str(inc.member_count)),
                    ("layers_source", p.layers_source),
                    ("center_source", p.center_source),
                    ("bounds_source", p.bounds_source),
                    ("zoom_source", p.zoom_source),
                    ("discipline_source", p.discipline_source),
                    ("level_source", p.level_source),
                    ("Advertencias", "; ".join(inc.warnings) if inc.warnings else "ninguna"),
                ],
                label_width=42 * mm,
            )
        )
        blocks.append(Spacer(1, 8))
    return blocks


def _alias_legend_table(bundle: ReportBundle) -> list:
    legend = bundle.alias_registry.legend
    if not legend:
        return []
    rows = [
        [P_alias(e["alias"]), P_cell(e["full_name"], dense=True)]
        for e in legend
    ]
    return [
        data_table(
            ["Alias", "Nombre completo"],
            rows,
            col_widths=[0.22 * _PAGE_W, 0.78 * _PAGE_W],
            page_width=_PAGE_W,
            dense=True,
        ),
        Spacer(1, 8),
    ]


def _warnings_section(bundle: ReportBundle) -> list:
    if not bundle.warnings:
        return [P("Sin advertencias de calidad de datos.", "body"), Spacer(1, 6)]
    rows = [[P_cell(w, dense=True)] for w in bundle.warnings[:80]]
    return [
        data_table(["Advertencia"], rows, col_widths=[_PAGE_W], page_width=_PAGE_W, dense=True),
        Spacer(1, 8),
    ]


def build_technical_pdf(bundle: ReportBundle) -> bytes:
    meta = bundle.meta
    story: list = [
        P("Reporte Tecnico de Clashes", "title"),
        meta_block(
            [
                ("Proyecto", str(meta.get("project_name", ""))),
                ("Carpeta", str(meta.get("folder_name", ""))),
                ("Corrida N.", f"{int(meta.get('run_sequence') or 1):02d}"),
                ("Fecha", str(meta.get("run_date", ""))),
                ("Exportado por", str(meta.get("user_display", ""))),
                ("Pipeline", "Dupla coordination / fast_compare"),
            ]
        ),
        Spacer(1, 10),
        *section("Metadatos de corrida"),
        *_run_metadata(bundle),
        *section("Pares programados"),
        *_pair_schedule_table(bundle),
        *section("Metricas"),
        *_metrics_dashboard(bundle),
        *_incident_index(bundle),
        *section("Detalle tecnico por incidencia"),
        *_incident_details(bundle),
        *section("Advertencias / calidad de datos"),
        *_warnings_section(bundle),
        *section("Apendice - Leyenda de alias"),
        *_alias_legend_table(bundle),
    ]
    if bundle.output_dir:
        story.append(P(f"Ruta de artefactos JSON/MD: {bundle.output_dir}", "small"))

    meta_line = (
        f"{meta.get('project_name', '')} | tecnico | "
        f"Corrida {int(meta.get('run_sequence') or 1):02d}"
    )
    return build_pdf(story, title="Reporte Tecnico de Clashes", meta_line=meta_line)
