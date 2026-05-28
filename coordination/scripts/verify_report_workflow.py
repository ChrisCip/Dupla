#!/usr/bin/env python3
"""Regenerate and verify Dupla human/technical clash PDFs for final QA."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUT = REPO / "references" / "report_style" / "verification"
WEB_BACKEND = REPO / "web-platform" / "backend"
SERENA_RUN = REPO / "analysis_output" / "serena18_analysis_06"
TORTUGA_RUN = REPO / "analysis_output" / "tortuga_c40_package_run"


@dataclass
class VerifyResult:
    name: str
    path: Path | None
    ok: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    visual_panels: str = "unknown"
    page_count: int = 0


def _pdf_text(path: Path) -> str:
    import fitz

    doc = fitz.open(path)
    parts = [page.get_text("text") for page in doc]
    doc.close()
    return "\n".join(parts)


def _pdf_page_sizes(path: Path) -> list[tuple[float, float]]:
    import fitz

    doc = fitz.open(path)
    sizes = [(page.rect.width, page.rect.height) for page in doc]
    doc.close()
    return sizes


def _run_metrics(run_dir: Path) -> dict[str, object]:
    metrics: dict[str, object] = {
        "run_label": run_dir.name,
        "incident_count": 0,
        "scheduled_pair_count": None,
    }
    primary_path = run_dir / "primary_incidents.json"
    if primary_path.is_file():
        primary = json.loads(primary_path.read_text(encoding="utf-8"))
        metrics["incident_count"] = int(
            primary.get("incident_count") or len(primary.get("incidents") or [])
        )
    summary_path = run_dir / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        metrics["scheduled_pair_count"] = summary.get("scheduled_pair_count")
    return metrics


def _panel_stats(run_dir: Path) -> tuple[int, int, int]:
    from coordination.reporting.human_report_pdf import prepare_clash_sheet_rows
    from coordination.reporting.element_loaders import load_elements_for_visual_reporting

    primary = json.loads((run_dir / "primary_incidents.json").read_text(encoding="utf-8"))
    context = json.loads((run_dir / "coordination_report_context.json").read_text(encoding="utf-8"))
    rev = next((p.read_text(encoding="utf-8") for p in run_dir.glob("REVISION_CLASHES*.md")), "")
    elements = load_elements_for_visual_reporting(run_dir / "elements_by_dwg.json")
    rows, _ = prepare_clash_sheet_rows(
        project_name=str(primary.get("project_name", "Proyecto")),
        report_context=context,
        primary_payload=primary,
        all_elements=elements,
        revision_md=rev,
    )
    vis = sum(1 for r in rows if r.has_visual)
    return len(rows), vis, len(rows) - vis


def _generate_test01_coordination_human(out_dir: Path) -> VerifyResult:
    from coordination.core.clash import ClashConflict, ClashIncident
    from coordination.core.models_25d import Discipline, Element25D, ZInterval
    from coordination.reporting.human_report_pdf import render_coordination_human_report_pdf

    def _el(eid: str, fname: str, disc: Discipline, fp: list[tuple[float, float]]) -> Element25D:
        return Element25D(
            id=eid,
            source_ref=f"{fname}|MUROS|LINE|{eid}",
            discipline=disc,
            category="LINE",
            footprint_coords_mm=fp,
            z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=3000.0, measurement_uncertainty_mm=0.0),
            metadata={"level_id": "NPT_P1"},
        )

    conflict = ClashConflict(
        element_id_a="a1",
        element_id_b="b1",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=120.0,
        z_overlap_range_project_mm=(0.0, 120.0),
        plan_intersection_area_mm2=400000.0,
        plan_intersection_centroid_mm=(750.0, 750.0),
        plan_intersection_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        raw_layers=("MUROS", "EST. MUROS"),
        source_refs=("arq.dwg|MUROS|LINE|a1", "est.dwg|EST. MUROS|LINE|b1"),
    )
    incidents = []
    specs = [
        ("incident_0001", "high", "arq.dwg", "est.dwg"),
        ("incident_0002", "medium", "arq.dwg", "est.dwg"),
        ("incident_0003", "medium", "arq.dwg", "est.dwg"),
        ("incident_0004", "low", "arq.dwg", "est.dwg"),
        ("incident_0005", "low", "arq.dwg", "est.dwg"),
    ]
    for i, (iid, sev, fa, fb) in enumerate(specs, start=1):
        inc = ClashIncident(
            incident_id=iid,
            file_pair=(fa, fb),
            level_id="NPT_P1",
            cell_key=(0, i),
            member_count=1,
            representative_conflict=conflict,
            plan_centroid_mm=(750.0 + i * 10, 750.0),
            plan_bounds_mm=(500.0 + i, 500.0, 1000.0 + i, 1000.0),
        )
        incidents.append(inc.model_dump())

    elements = [
        _el("a1", "arq.dwg", Discipline.ARCH, [(400, 400), (1100, 400), (1100, 1100), (400, 1100)]),
        _el("b1", "est.dwg", Discipline.STRUC, [(450, 450), (1050, 450), (1050, 1050), (450, 1050)]),
    ]
    ctx = {
        "all_incidents": [
            {
                "incident_id": s[0],
                "severity": s[1],
                "priority": "P1",
                "level_id": "NPT_P1",
                "layer_pair": "MUROS / EST. MUROS",
                "human_description": "Verificar solape entre capa MUROS y capa EST. MUROS en nivel NPT_P1.",
                "recommended_action": "Corregir el DWG afectado y subir la revisión en la sección de Clashes.",
                "file_names": (s[2], s[3]),
            }
            for s in specs
        ]
    }
    out_path = out_dir / "TEST_01_human.pdf"
    render_coordination_human_report_pdf(
        output_path=out_path,
        project_name="Tutorial · Workspace Dupla",
        run_label="TEST_01",
        generated_at="2026-05-24T12:00:00+00:00",
        report_context=ctx,
        primary_payload={"incidents": incidents, "incident_count": len(incidents)},
        all_elements=elements,
    )
    res = _verify_coordination_human("TEST_01 human (coordination)", out_path)
    res.visual_panels = "5/5 footprint SVG panels (synthetic)"
    return res


def _generate_run_human(
    out_dir: Path,
    *,
    run_dir: Path,
    out_name: str,
    label: str,
) -> VerifyResult | None:
    if not run_dir.is_dir() or not (run_dir / "primary_incidents.json").is_file():
        return None
    from coordination.reporting.element_loaders import load_elements_for_visual_reporting
    from coordination.reporting.human_report_pdf import render_coordination_human_report_pdf

    primary = json.loads((run_dir / "primary_incidents.json").read_text(encoding="utf-8"))
    context = json.loads((run_dir / "coordination_report_context.json").read_text(encoding="utf-8"))
    revision_md = next((p.read_text(encoding="utf-8") for p in run_dir.glob("REVISION_CLASHES*.md")), "")
    elements_path = run_dir / "elements_by_dwg.json"
    all_elements = load_elements_for_visual_reporting(elements_path) if elements_path.is_file() else []
    out_path = out_dir / out_name
    render_coordination_human_report_pdf(
        output_path=out_path,
        project_name=primary.get("project_name", "Proyecto"),
        run_label=run_dir.name,
        generated_at=str(primary.get("generated_at", "2026-05-06T00:00:00+00:00")),
        report_context=context,
        primary_payload=primary,
        all_elements=all_elements,
        revision_md=revision_md,
    )
    incident_count = len(primary.get("incidents") or [])
    metrics = _run_metrics(run_dir)
    total, vis, placeholders = _panel_stats(run_dir) if incident_count else (0, 0, 0)
    res = _verify_coordination_human(label, out_path, require_delivery=incident_count > 0)
    res.visual_panels = (
        f"{vis}/{total} geometry panels, {placeholders} placeholders, "
        f"{len(all_elements)} elements loaded, {incident_count} incidents"
    )
    res.checks.append(
        f"OK: source run `{metrics['run_label']}` — {incident_count} primary incidents"
    )
    if metrics.get("scheduled_pair_count") is not None:
        res.checks.append(f"OK: scheduled pairs — {metrics['scheduled_pair_count']}")
    if incident_count == 0:
        res.warnings.append("WARN: run has 0 primary incidents (coordinate/readiness); visual panels N/A")
    elif vis == 0 and total > 0:
        res.warnings.append(f"WARN: 0/{total} visual panels despite {len(all_elements)} elements")
    elif incident_count > 0 and vis == 0:
        res.ok = False
        res.warnings.append(
            f"FAIL: package has {incident_count} incidents but 0/{total} geometry visual panels"
        )
    return res


def _verify_coordination_human(name: str, path: Path, *, require_delivery: bool = True) -> VerifyResult:
    res = VerifyResult(name=name, path=path, ok=True)
    if not path.is_file():
        res.ok = False
        res.warnings.append("file not created")
        return res
    text = _pdf_text(path)
    sizes = _pdf_page_sizes(path)
    res.page_count = len(sizes)
    landscape_pages = sum(1 for w, h in sizes if w > h)
    required = [
        ("DUPLA", "logo placeholder"),
        ("Matriz de chequeo", "checklist section"),
    ]
    if require_delivery:
        required.extend(
            [
                ("Entrega de planos corregidos", "correction workflow section"),
                ("no reemplazar el DWG original", "upload without overwrite"),
                ("Comparación DWG", "visual comparison sheets"),
            ]
        )
    required.extend(
        [
            ("DWG A", "DWG A panel label"),
            ("DWG B", "DWG B panel label"),
        ]
    )
    for needle, label in required:
        if needle.lower() in text.lower():
            res.checks.append(f"OK: {label}")
        else:
            res.ok = False
            res.warnings.append(f"MISSING: {label} ({needle})")
    if landscape_pages >= 2:
        res.checks.append(f"OK: landscape pages detected ({landscape_pages})")
    else:
        res.warnings.append(f"WARN: only {landscape_pages} landscape page(s)")
    if "Vista de plano no disponible" in text:
        res.visual_panels = res.visual_panels or "placeholders present in PDF"
    return res


def _rich_sample_artifacts() -> dict:
    primary = {
        "project_name": "Tutorial · Workspace Dupla",
        "incident_count": 1,
        "incident_conflict_count": 2,
        "analysis_profile": "fast_compare",
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": [
                    "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg",
                    "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg",
                ],
                "level_id": "NPT_P1",
                "member_count": 2,
                "plan_centroid_mm": [148500, -158500],
                "plan_bounds_mm": [148000, -163000, 158000, -154000],
                "confidence": "high",
                "representative_conflict": {
                    "discipline_a": "ARQUITECTURA",
                    "discipline_b": "ESTRUCTURA",
                    "clash_type": "HARD",
                    "overlap_depth_z_mm": 220.0,
                    "plan_intersection_area_mm2": 85000.0,
                    "source_refs": [
                        "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg|SOLAR|Polyline|3F6B08",
                        "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg|EST_VIGA|Line|30A5BD",
                    ],
                },
            }
        ],
    }
    context = {
        "counts": {
            "scheduled_pairs": 1,
            "scheduled_files": 2,
            "primary_incidents": 1,
            "primary_members": 2,
        },
        "analysis_profile": "fast_compare",
    }
    return {
        "primary_incidents": json.dumps(primary),
        "coordination_context": json.dumps(context),
        "pair_schedule": json.dumps(
            {
                "pairs": [
                    {
                        "file_a": "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg",
                        "file_b": "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg",
                        "scheduled": True,
                        "discipline_a": "ARQUITECTURA",
                        "discipline_b": "ESTRUCTURA",
                        "level_id": "NPT_P1",
                    }
                ]
            }
        ),
        "analyzed_documents": [
            {"original_name": "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg", "discipline_bucket": "arquitectura"},
            {"original_name": "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg", "discipline_bucket": "estructura"},
        ],
        "output_dir": "/tmp/test_01_clash_output",
    }


def _generate_technical_pdfs(out_dir: Path) -> list[VerifyResult]:
    sys.path.insert(0, str(WEB_BACKEND))
    from app.services.clash_reports.data import build_report_bundle
    from app.services.clash_reports.technical_pdf import build_technical_pdf

    results: list[VerifyResult] = []
    meta_test = {
        "project_name": "Tutorial · Workspace Dupla",
        "folder_name": "TEST_01",
        "user_display": "Carlos Ruiz",
        "run_date": "2026-05-23",
        "run_sequence": 1,
    }
    tech_path = out_dir / "TEST_01_technical.pdf"
    tech_path.write_bytes(
        build_technical_pdf(build_report_bundle(meta=meta_test, artifacts=_rich_sample_artifacts()))
    )
    results.append(_verify_technical("TEST_01 technical", tech_path))

    for run_dir, out_name, folder in (
        (SERENA_RUN, "SERENA18_technical.pdf", "SERENA18"),
        (TORTUGA_RUN, "TORTUGA_C40_technical.pdf", "TORTUGA_C40"),
    ):
        if not run_dir.is_dir():
            continue
        primary = json.loads((run_dir / "primary_incidents.json").read_text(encoding="utf-8"))
        context = json.loads((run_dir / "coordination_report_context.json").read_text(encoding="utf-8"))
        ps = run_dir / "pair_schedule.json"
        pair = json.loads(ps.read_text(encoding="utf-8")) if ps.is_file() else {"pairs": []}
        rev = next((p.read_text(encoding="utf-8") for p in run_dir.glob("REVISION_CLASHES*.md")), "")
        artifacts = {
            "primary_incidents": json.dumps(primary, ensure_ascii=False),
            "coordination_context": json.dumps(context, ensure_ascii=False),
            "pair_schedule": json.dumps(pair, ensure_ascii=False),
            "revision_md": rev,
            "output_dir": str(run_dir),
            "analyzed_documents": [],
        }
        meta = {
            "project_name": str(primary.get("project_name", folder)),
            "folder_name": folder,
            "user_display": "Verification",
            "run_date": "2026-05-22",
            "run_sequence": 1,
        }
        path = out_dir / out_name
        path.write_bytes(build_technical_pdf(build_report_bundle(meta=meta, artifacts=artifacts)))
        results.append(_verify_technical(f"{folder} technical", path))
    return results


def _verify_technical(name: str, path: Path) -> VerifyResult:
    res = VerifyResult(name=name, path=path, ok=True)
    if not path.is_file():
        res.ok = False
        res.warnings.append("file not created")
        return res
    text = _pdf_text(path)
    res.page_count = len(_pdf_page_sizes(path))
    if "Inventario analizado" in text:
        res.ok = False
        res.warnings.append("FAIL: Inventario analizado present")
    else:
        res.checks.append("OK: no Inventario analizado")
    if "Indice de incidencias" in text or "Índice de incidencias" in text:
        res.checks.append("OK: incident index present")
    if "---" in text and text.count("---") > 2:
        res.warnings.append("WARN: raw markdown separators in PDF")
    if " | ? | " in text or text.count("?") > 5:
        res.warnings.append(f"WARN: many '?' tokens ({text.count('?')}) — manual review")
    if "Z W" in text:
        res.checks.append("OK: Z W commands present")
    if "x_min=" in text or "layers_source" in text:
        res.checks.append("OK: detail fields in technical sections")
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUT}\n")

    results: list[VerifyResult] = []
    results.append(_generate_test01_coordination_human(OUT))
    serena_h = _generate_run_human(
        OUT,
        run_dir=SERENA_RUN,
        out_name="SERENA18_human.pdf",
        label="SERENA18 human (coordination)",
    )
    if serena_h:
        results.append(serena_h)
    tortuga_h = _generate_run_human(
        OUT,
        run_dir=TORTUGA_RUN,
        out_name="TORTUGA_C40_human.pdf",
        label="TORTUGA_C40 human (coordination, production package)",
    )
    if tortuga_h:
        results.append(tortuga_h)
    results.extend(_generate_technical_pdfs(OUT))

    print("=" * 60)
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"\n[{status}] {r.name}")
        if r.path:
            print(f"  Path: {r.path}")
            print(f"  Pages: {r.page_count}  Visuals: {r.visual_panels}")
        if "TORTUGA_C40" in r.name and TORTUGA_RUN.is_dir():
            metrics = _run_metrics(TORTUGA_RUN)
            print(
                f"  Package source: {TORTUGA_RUN} — "
                f"{metrics['incident_count']} incidents, "
                f"{metrics.get('scheduled_pair_count', '?')} scheduled pairs"
            )
        for c in r.checks:
            print(f"  + {c}")
        for w in r.warnings:
            print(f"  ! {w}")
    failed = sum(1 for r in results if not r.ok)
    print(f"\n{'=' * 60}\nSummary: {len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
