"""Generate Dupla coordination markdown artifacts for clash jobs."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_dupla_reporting():
    try:
        from coordination.reporting.reporting import (
            build_coordination_report_context,
            render_coordination_human_report_markdown,
            render_coordination_report_markdown,
        )
        from coordination.reporting.revision_report import (
            render_revision_report,
            revision_report_filename,
        )

        out = {
            "build_coordination_report_context": build_coordination_report_context,
            "render_coordination_human_report_markdown": render_coordination_human_report_markdown,
            "render_coordination_report_markdown": render_coordination_report_markdown,
            "render_revision_report": render_revision_report,
            "revision_report_filename": revision_report_filename,
        }
        try:
            from coordination.reporting.human_report_pdf import render_coordination_human_report_pdf
            out["render_coordination_human_report_pdf"] = render_coordination_human_report_pdf
        except ImportError as exc_pdf:
            logger.warning("Dupla human PDF renderer unavailable: %s", exc_pdf)
        return out
    except ImportError as exc:
        logger.warning("Dupla reporting modules unavailable: %s", exc)
        return None


def _cad_entries(file_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        e
        for e in file_entries
        if str(e.get("original_name", "")).lower().endswith((".dwg", ".dxf"))
    ]


def _ensure_smoke_conflict_fields(
    conflict: dict[str, Any],
    *,
    incident_id: str,
    file_a: str,
    file_b: str,
    plan_bounds: tuple[float, float, float, float],
    plan_centroid: tuple[float, float],
    level_id: str,
) -> dict[str, Any]:
    """Fill ClashConflict fields required by the strict model so validation passes."""
    out = dict(conflict or {})
    out.setdefault("discipline_a", "ARQUITECTURA")
    out.setdefault("discipline_b", "ESTRUCTURA")
    out.setdefault("clash_type", "HARD")
    out.setdefault("overlap_depth_z_mm", 100.0)
    out.setdefault("plan_intersection_area_mm2", 50_000.0)
    out["plan_intersection_bounds_mm"] = list(plan_bounds)
    out["plan_intersection_centroid_mm"] = list(plan_centroid)
    out["level_ids"] = [level_id, level_id]
    z = float(out.get("overlap_depth_z_mm") or 100.0)
    out.setdefault("z_overlap_range_project_mm", [0.0, z])
    refs = out.get("source_refs") or []
    if len(refs) < 2:
        refs = [
            f"{file_a}|SOLAR|Polyline|{incident_id}_A",
            f"{file_b}|SOLAR|Line|{incident_id}_B",
        ]
    out["source_refs"] = list(refs)[:2]
    out.setdefault("element_id_a", f"smoke_{incident_id}_a")
    out.setdefault("element_id_b", f"smoke_{incident_id}_b")
    return out


def _cell_key_for(centroid: tuple[float, float], cell_size_mm: float = 50_000.0) -> tuple[int, int]:
    return (int(centroid[0] // cell_size_mm), int(centroid[1] // cell_size_mm))


def _ensure_smoke_incident_fields(
    raw: dict[str, Any],
    *,
    incident_id: str,
    file_a: str,
    file_b: str,
) -> dict[str, Any]:
    """Make a smoke incident parseable by the strict ClashIncident model."""
    out = dict(raw or {})
    out["incident_id"] = incident_id
    out["file_pair"] = [file_a, file_b]
    bounds = list(out.get("plan_bounds_mm") or [-1000.0, -1000.0, 1000.0, 1000.0])
    bx1, by1, bx2, by2 = (float(bounds[i]) for i in range(4))
    centroid = list(out.get("plan_centroid_mm") or [(bx1 + bx2) / 2.0, (by1 + by2) / 2.0])
    cx, cy = float(centroid[0]), float(centroid[1])
    out["plan_bounds_mm"] = [bx1, by1, bx2, by2]
    out["plan_centroid_mm"] = [cx, cy]
    out.setdefault("level_id", "NPT_P1")
    out.setdefault("member_count", 1)
    out.setdefault("confidence", "medium")
    out["cell_key"] = list(_cell_key_for((cx, cy)))
    out["representative_conflict"] = _ensure_smoke_conflict_fields(
        out.get("representative_conflict") or {},
        incident_id=incident_id,
        file_a=file_a,
        file_b=file_b,
        plan_bounds=(bx1, by1, bx2, by2),
        plan_centroid=(cx, cy),
        level_id=str(out["level_id"]),
    )
    return out


def adapt_smoke_primary(primary: dict[str, Any], file_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Rewrite smoke fixture file pairs to match the real folder inventory."""
    data = dict(primary)
    cad = _cad_entries(file_entries)
    by_bucket: dict[str, list[str]] = {}
    for entry in cad:
        bucket = str(entry.get("discipline_bucket") or "sin_clasificar")
        by_bucket.setdefault(bucket, []).append(str(entry.get("original_name")))

    arq = by_bucket.get("arquitectura", [])
    est = by_bucket.get("estructura", [])
    elc = by_bucket.get("electrica", [])
    mec = by_bucket.get("mecanica", [])

    pair_names: list[tuple[str, str]] = []
    if arq and est:
        pair_names.append((arq[0], est[0]))
    if len(arq) > 1 and est:
        pair_names.append((arq[1], est[0]))
    if arq and elc:
        pair_names.append((arq[0], elc[0]))
    if arq and mec:
        pair_names.append((arq[0], mec[0]))
    if not pair_names and len(cad) >= 2:
        pair_names.append((str(cad[0].get("original_name")), str(cad[1].get("original_name"))))

    templates = list(data.get("incidents") or [{}])
    incidents: list[dict[str, Any]] = []
    for idx, (file_a, file_b) in enumerate(pair_names or [("", "")], start=1):
        template = dict(templates[min(idx - 1, len(templates) - 1)] if templates else {})
        inc_id = template.get("incident_id") or f"incident_smoke_{idx:04d}"
        enriched = _ensure_smoke_incident_fields(
            template,
            incident_id=str(inc_id),
            file_a=file_a,
            file_b=file_b,
        )
        incidents.append(enriched)

    data["incidents"] = incidents
    data["incident_count"] = len(incidents)
    data["incident_conflict_count"] = sum(int(inc.get("member_count") or 1) for inc in incidents)
    return data


def _smoke_summary_payload(file_entries: list[dict[str, Any]], primary: dict[str, Any]) -> dict[str, Any]:
    cad = _cad_entries(file_entries)
    pair_count = max(len(primary.get("incidents") or []), 1)
    return {
        "project_name": primary.get("project_name"),
        "status": "completed",
        "analysis_profile": primary.get("analysis_profile", "fast_compare"),
        "generated_at": primary.get("generated_at"),
        "scheduled_pair_count": pair_count,
        "scheduled_file_count": len(cad),
        "element_count": 0,
        "selected_candidate_count": pair_count,
    }


def _smoke_pair_schedule(primary: dict[str, Any]) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    for inc in primary.get("incidents") or []:
        file_pair = inc.get("file_pair") or []
        if len(file_pair) < 2:
            continue
        conflict = inc.get("representative_conflict") or {}
        pairs.append(
            {
                "file_a": file_pair[0],
                "file_b": file_pair[1],
                "scheduled": True,
                "discipline_a": conflict.get("discipline_a", ""),
                "discipline_b": conflict.get("discipline_b", ""),
                "level_id": inc.get("level_id"),
            }
        )
    return {"pairs": pairs}


def _layer_role_from_refs(ref: str) -> tuple[str, str]:
    """Best-effort layer / role from a source_ref string of form 'file|layer|type|handle'."""
    parts = str(ref or "").split("|")
    layer = parts[1] if len(parts) > 1 and parts[1] else "0"
    role = parts[2] if len(parts) > 2 and parts[2] else "polygon"
    return layer, role


def _make_synthetic_footprint(
    cx: float,
    cy: float,
    half_w: float,
    half_h: float,
) -> list[list[float]]:
    return [
        [cx - half_w, cy - half_h],
        [cx + half_w, cy - half_h],
        [cx + half_w, cy + half_h],
        [cx - half_w, cy + half_h],
    ]


def _synth_element(
    *,
    element_id: str,
    source_file: str,
    discipline: str,
    level_id: str,
    layer: str,
    element_type: str,
    cx: float,
    cy: float,
    half_w: float,
    half_h: float,
) -> dict[str, Any]:
    footprint = _make_synthetic_footprint(cx, cy, half_w, half_h)
    return {
        "semantic_element_id": element_id,
        "source_element_id": element_id,
        "source_file": source_file,
        "file_name": str(Path(source_file).name) if source_file else element_id,
        "discipline": discipline,
        "level_id": level_id,
        "layer": layer,
        "cad_handle": element_id[-7:].upper(),
        "entity_type": "Polyline",
        "element_type": element_type,
        "bbox_mm": [
            cx - half_w,
            cy - half_h,
            cx + half_w,
            cy + half_h,
        ],
        "centroid_mm": [cx, cy],
        "footprint_coords_mm": footprint,
        "geometry_source": "synthetic_smoke",
        "geometry_role": "footprint",
        "geometry_confidence": "high",
    }


def _synthesize_elements_for_file(
    *,
    source_file: str,
    discipline: str,
    level_id: str,
    plan_bounds: tuple[float, float, float, float],
    incident_id: str,
    involved_element_id: str,
    involved_layer: str,
) -> list[dict[str, Any]]:
    """Generate plausible context footprints + one highlighted element for one DWG."""
    bx1, by1, bx2, by2 = plan_bounds
    w = max(bx2 - bx1, 1000.0)
    h = max(by2 - by1, 1000.0)
    cx, cy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
    elements: list[dict[str, Any]] = []

    elements.append(
        _synth_element(
            element_id=involved_element_id,
            source_file=source_file,
            discipline=discipline,
            level_id=level_id,
            layer=involved_layer,
            element_type="losa_solar" if "SOLAR" in involved_layer.upper() else "muro",
            cx=cx,
            cy=cy,
            half_w=w / 2.0,
            half_h=h / 2.0,
        )
    )

    context_layers = ("MURO", "COLUMNA", "VIGA") if discipline.upper() == "ESTRUCTURA" else (
        "MURO", "TABIQUE", "MOBILIARIO"
    )
    grid_offsets = [
        (-1.6, -1.4, 0.55, 0.45),
        (1.4, -1.5, 0.50, 0.40),
        (-1.7, 1.5, 0.60, 0.35),
        (1.5, 1.4, 0.55, 0.50),
        (-2.2, 0.0, 0.30, 0.95),
        (2.1, 0.0, 0.30, 0.95),
        (0.0, -2.0, 0.95, 0.30),
        (0.0, 2.0, 0.95, 0.30),
        (-0.6, -0.5, 0.18, 0.18),
        (0.6, -0.5, 0.18, 0.18),
        (-0.6, 0.5, 0.18, 0.18),
        (0.6, 0.5, 0.18, 0.18),
    ]
    for idx, (ox, oy, sw, sh) in enumerate(grid_offsets, start=1):
        layer = context_layers[idx % len(context_layers)]
        element_type = layer.lower()
        elements.append(
            _synth_element(
                element_id=f"smoke_{incident_id}_{idx:02d}",
                source_file=source_file,
                discipline=discipline,
                level_id=level_id,
                layer=layer,
                element_type=element_type,
                cx=cx + ox * (w / 2.0),
                cy=cy + oy * (h / 2.0),
                half_w=max(sw * (w / 2.0), 600.0),
                half_h=max(sh * (h / 2.0), 400.0),
            )
        )

    return elements


def synthesize_elements_by_dwg_for_smoke(
    *,
    primary_payload: dict[str, Any],
    output_path: Path,
    project_name: str,
) -> Path:
    """Write a synthetic elements_by_dwg.json so the rich tile renderer has footprints to draw."""
    files: dict[str, dict[str, Any]] = {}
    for raw in primary_payload.get("incidents") or []:
        file_pair = raw.get("file_pair") or []
        if len(file_pair) < 2:
            continue
        file_a, file_b = str(file_pair[0]), str(file_pair[1])
        bounds = raw.get("plan_bounds_mm") or [-1000.0, -1000.0, 1000.0, 1000.0]
        bounds = (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))
        level_id = str(raw.get("level_id") or "NPT_P1")
        conflict = raw.get("representative_conflict") or {}
        refs = list(conflict.get("source_refs") or [])
        layer_a, _ = _layer_role_from_refs(refs[0] if len(refs) > 0 else "")
        layer_b, _ = _layer_role_from_refs(refs[1] if len(refs) > 1 else "")
        discipline_a = str(conflict.get("discipline_a") or "ARQUITECTURA")
        discipline_b = str(conflict.get("discipline_b") or "ESTRUCTURA")
        elem_id_a = str(conflict.get("element_id_a") or f"smoke_{raw.get('incident_id')}_a")
        elem_id_b = str(conflict.get("element_id_b") or f"smoke_{raw.get('incident_id')}_b")

        for source_file, discipline, layer, involved_id in (
            (file_a, discipline_a, layer_a or "0", elem_id_a),
            (file_b, discipline_b, layer_b or "0", elem_id_b),
        ):
            bucket = files.setdefault(
                source_file,
                {
                    "source_file": source_file,
                    "source_rel_path": source_file,
                    "file_name": Path(source_file).name or source_file,
                    "discipline": discipline,
                    "level_id": level_id,
                    "element_count": 0,
                    "elements": [],
                },
            )
            bucket["elements"].extend(
                _synthesize_elements_for_file(
                    source_file=source_file,
                    discipline=discipline,
                    level_id=level_id,
                    plan_bounds=bounds,
                    incident_id=str(raw.get("incident_id") or "incident"),
                    involved_element_id=involved_id,
                    involved_layer=layer or "0",
                )
            )

    for bucket in files.values():
        bucket["element_count"] = len(bucket["elements"])

    payload = {
        "generated_at": str(primary_payload.get("generated_at") or ""),
        "project_name": project_name,
        "run_label": str(primary_payload.get("analysis_profile") or "fast_compare"),
        "file_count": len(files),
        "element_count": sum(int(b["element_count"]) for b in files.values()),
        "files": list(files.values()),
        "synthetic_smoke": True,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _fallback_revision_md(project_name: str, primary: dict[str, Any]) -> str:
    count = len(primary.get("incidents") or [])
    return (
        f"# Guía de Revisión Manual de Clashes — {project_name}\n\n"
        f"## Estado — {count} incidencia(s) primaria(s)\n\n"
        f"_Reporte generado en modo fallback (Dupla reporting no disponible)._\n"
    )


def _fallback_technical_md(project_name: str, context: dict[str, Any]) -> str:
    counts = context.get("counts") or {}
    return (
        f"# Technical Coordination Report - {project_name}\n\n"
        f"- Scheduled pairs: {counts.get('scheduled_pairs', 0)}\n"
        f"- Primary incidents: {counts.get('primary_incidents', 0)}\n"
    )


def _fallback_human_md(project_name: str, context: dict[str, Any]) -> str:
    counts = context.get("counts") or {}
    return (
        f"# Coordination Report Human - {project_name}\n\n"
        f"## Resumen ejecutivo\n\n"
        f"- Pares revisados: {counts.get('scheduled_pairs', 0)}\n"
        f"- Incidencias primarias: {counts.get('primary_incidents', 0)}\n"
    )


def generate_report_artifacts(
    *,
    output_dir: Path,
    project_name: str,
    primary_payload: dict[str, Any],
    file_entries: list[dict[str, Any]],
    analyzed_documents: list[dict[str, Any]],
    coordination_context: dict[str, Any] | None = None,
    summary_payload: dict[str, Any] | None = None,
    pair_schedule_payload: dict[str, Any] | None = None,
    inputs_dir: Path | None = None,
    smoke_mode: bool = False,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    primary_path = output_dir / "primary_incidents.json"
    primary_path.write_text(json.dumps(primary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if smoke_mode:
        elements_path = output_dir / "elements_by_dwg.json"
        if not elements_path.is_file():
            try:
                synthesize_elements_by_dwg_for_smoke(
                    primary_payload=primary_payload,
                    output_path=elements_path,
                    project_name=project_name,
                )
            except Exception as exc:
                logger.warning("Could not synthesize elements_by_dwg for smoke run: %s", exc)

    dupla = _load_dupla_reporting()
    project_root = inputs_dir or output_dir

    if smoke_mode or not summary_payload:
        summary_payload = summary_payload or _smoke_summary_payload(file_entries, primary_payload)
    if smoke_mode or not pair_schedule_payload:
        pair_schedule_payload = pair_schedule_payload or _smoke_pair_schedule(primary_payload)

    if coordination_context is None:
        if dupla:
            coordination_context = dupla["build_coordination_report_context"](
                summary_payload=summary_payload or {},
                primary_payload=primary_payload,
            )
        else:
            coordination_context = {
                "project_name": project_name,
                "counts": {
                    "scheduled_pairs": len(pair_schedule_payload.get("pairs") or []),
                    "scheduled_files": len(_cad_entries(file_entries)),
                    "primary_incidents": len(primary_payload.get("incidents") or []),
                    "primary_members": primary_payload.get("incident_conflict_count", 0),
                },
                "pair_rollups": [],
                "defendable_incidents": [],
                "validation_incidents": [],
                "reader_sections": {},
                "all_incidents": [],
            }

    context_path = output_dir / "coordination_report_context.json"
    context_path.write_text(json.dumps(coordination_context, ensure_ascii=False, indent=2), encoding="utf-8")

    pair_schedule_path = output_dir / "pair_schedule.json"
    pair_schedule_path.write_text(json.dumps(pair_schedule_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if dupla:
        revision_md = dupla["render_revision_report"](
            project_name=project_name,
            primary_payload=primary_payload,
            scheduled_pairs=pair_schedule_payload.get("pairs") or [],
            pair_rollups=coordination_context.get("pair_rollups"),
            nasas_root=project_root,
            generated_at=primary_payload.get("generated_at"),
        )
        revision_filename = dupla["revision_report_filename"](project_name)
        technical_md = dupla["render_coordination_report_markdown"](
            project_name=project_name,
            root=project_root,
            summary_payload=summary_payload or {},
            primary_payload=primary_payload,
            pair_schedule_payload=pair_schedule_payload,
        )
        human_md = dupla["render_coordination_human_report_markdown"](
            project_name=project_name,
            run_label=primary_payload.get("analysis_profile") or "fast_compare",
            summary_payload=summary_payload or {},
            readiness_payload={},
            coordinate_audit_payload={},
            pair_schedule_payload=pair_schedule_payload,
            report_context=coordination_context,
        )
    else:
        revision_filename = f"REVISION_CLASHES_ARQUITECTO_{project_name.split()[0].upper()}.md"
        revision_md = _fallback_revision_md(project_name, primary_payload)
        technical_md = _fallback_technical_md(project_name, coordination_context)
        human_md = _fallback_human_md(project_name, coordination_context)

    revision_path = output_dir / revision_filename
    technical_path = output_dir / "technical_coordination_report.md"
    human_path = output_dir / "coordination_report_human.md"
    revision_path.write_text(revision_md, encoding="utf-8")
    technical_path.write_text(technical_md, encoding="utf-8")
    human_path.write_text(human_md, encoding="utf-8")

    # Rich human PDF (cover + KPIs + matrix + visual sheets) -- consumed by the UI download
    human_pdf_path = output_dir / "coordination_report_human.pdf"
    human_pdf_paths: dict[str, str] = {}
    if dupla and "render_coordination_human_report_pdf" in dupla:
        try:
            dupla["render_coordination_human_report_pdf"](
                output_path=human_pdf_path,
                project_name=project_name,
                run_label=str(primary_payload.get("analysis_profile") or "fast_compare"),
                generated_at=str(primary_payload.get("generated_at") or ""),
                report_context=coordination_context,
                primary_payload=primary_payload,
                all_elements=None,
                revision_md=revision_md,
            )
            human_pdf_paths["human_pdf"] = str(human_pdf_path)
        except Exception as exc:
            logger.warning("Could not render rich human PDF: %s", exc, exc_info=True)

    return {
        "revision_md": revision_md,
        "technical_md": technical_md,
        "human_md": human_md,
        "primary_incidents": json.dumps(primary_payload, ensure_ascii=False),
        "coordination_context": json.dumps(coordination_context, ensure_ascii=False),
        "pair_schedule": json.dumps(pair_schedule_payload, ensure_ascii=False),
        "analyzed_documents": analyzed_documents,
        "paths": {
            "output_dir": str(output_dir),
            "revision_md": str(revision_path),
            "technical_md": str(technical_path),
            "human_md": str(human_path),
            "primary_incidents": str(primary_path),
            "coordination_context": str(context_path),
            "pair_schedule": str(pair_schedule_path),
            **human_pdf_paths,
        },
    }
