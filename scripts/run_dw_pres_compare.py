"""
DWG (APS) + opcional visión (PDF) -> presupuesto Dupla -> comparación vs PRES.

Modos:
  --pipeline full     APS + render PDF + GPT-4o visión + BC3 + Excel (programa completo).
  --pipeline cad-only   Solo APS + CAD (sin imágenes).

Baseline de comparación:
  --compare-baseline structural   PRES filtrado a partidas/capítulos estructurales (recomendado para planos estructurales).
  --compare-baseline full         PRES completo.

Uso:
    python scripts/run_dw_pres_compare.py --pipeline full --pdf plano.pdf
    python scripts/run_dw_pres_compare.py --pipeline cad-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aps_integration.oss_manager import APS_BUCKET_NAME
from budget.export_excel import export_budget_workbook
from budget.pres_structural_filter import filter_pres_workbook_structural
from compare_budget import build_comparison_markdown, build_comparison_report
from core.logging_config import setup_logging
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from core.stage import PipelineRunner
from dupla_run_full_analysis_local import (
    AUTO_UNIQUE_OBJECT_NAME,
    BUCKET_NAME,
    FAILED_MANIFEST_GRACE_POLLS,
    FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
    MAX_PROPERTY_WAIT_SECONDS,
    POLL_INTERVAL_SECONDS,
    TRANSLATION_TIMEOUT_SECONDS,
    TRANSLATION_VIEWS,
    UPLOAD_OBJECT_NAME,
    _finish,
    stage_aps_extraction,
    stage_build_budget,
    stage_excel_export,
    stage_knowledge_inputs,
    stage_resolve_pages,
    stage_vision_analysis,
)
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import parse_bc3

logger = logging.getLogger("dupla.dw_pres_compare")


def _slug_from_dwg(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = stem.strip("_")
    return stem[:70] if stem else "proyecto"


def _path_for_dupla_config(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def _default_dwg() -> Path | None:
    hits = list(REPO_ROOT.glob("*.dwg"))
    if hits:
        return max(hits, key=lambda p: p.stat().st_mtime)
    for p in REPO_ROOT.glob("inputs/**/*.dwg"):
        return p
    return None


def _default_pres() -> Path:
    root_pres = REPO_ROOT / "PRES.xlsx"
    if root_pres.exists():
        return root_pres
    return REPO_ROOT / "data" / "PRES.xlsx"


def _find_pdf_for_dwg(dwg_path: Path) -> Path | None:
    p = dwg_path.with_suffix(".pdf")
    if p.is_file():
        return p
    pattern = dwg_path.stem.split("(")[0].strip() + "*.pdf"
    sibs = list(dwg_path.parent.glob(pattern))
    if sibs:
        return max(sibs, key=lambda x: x.stat().st_mtime)
    return None


def _open_in_excel(paths: list[Path]) -> None:
    if sys.platform != "win32":
        logger.info("Abre manualmente: %s", paths)
        return
    for path in paths:
        if path.exists():
            try:
                os.startfile(str(path.resolve()))  # type: ignore[attr-defined]
            except OSError as exc:
                logger.warning("No se pudo abrir %s: %s", path, exc)


def _apply_dupla_config(
    *,
    dwg_path: Path,
    run_dir: Path,
    bc3_path: Path,
    xlsx_training_relative: str,
    pdf_relative: str | None,
    use_pdf: bool,
    project_name: str,
    project_id: str,
    pres_template_takeoffs: bool,
) -> None:
    import dupla_run_full_analysis_local as dr

    dr.DWG_PATH = _path_for_dupla_config(dwg_path)
    dr.OUTPUTS_DIR = _path_for_dupla_config(run_dir)
    dr.BC3_PATH = _path_for_dupla_config(bc3_path)
    dr.XLSX_TRAINING_PATH = xlsx_training_relative
    dr.PROJECT_NAME = project_name
    dr.PROJECT_ID = project_id
    dr.PRES_TEMPLATE_TAKEOFFS = pres_template_takeoffs
    dr.OUTPUT_NAME = "dupla_presupuesto_generado"
    dr.USE_PDF = use_pdf
    if pdf_relative:
        dr.PDF_PATH = pdf_relative


def _run_pipeline_full(
    dwg_path: Path,
    run_dir: Path,
    pdf_path: Path,
    bc3_path: Path,
    training_xlsx_relative: str,
    slug: str,
    pres_template_takeoffs: bool,
) -> Path:
    _apply_dupla_config(
        dwg_path=dwg_path,
        run_dir=run_dir,
        bc3_path=bc3_path,
        xlsx_training_relative=training_xlsx_relative,
        pdf_relative=_path_for_dupla_config(pdf_path),
        use_pdf=True,
        project_name=f"Dupla — {dwg_path.stem}",
        project_id=slug,
        pres_template_takeoffs=pres_template_takeoffs,
    )

    import dupla_run_full_analysis_local as dr

    bucket_name = dr.BUCKET_NAME or APS_BUCKET_NAME
    runner = PipelineRunner("dw_pres_compare_full")

    s1 = runner.run_stage("aps_extraction", stage_aps_extraction, dwg_path, run_dir, bucket_name)
    if not s1.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo APS: " + "; ".join(s1.errors))

    s2 = runner.run_stage("vision_pages", stage_resolve_pages, run_dir)
    if not s2.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo vision_pages: " + "; ".join(s2.errors))

    s3 = runner.run_stage(
        "vision_analysis",
        stage_vision_analysis,
        s2.output["pages_dir"],
        s1.output["cad_facts"],
        run_dir,
    )
    if not s3.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo vision_analysis: " + "; ".join(s3.errors))

    s4 = runner.run_stage("knowledge_inputs", stage_knowledge_inputs, run_dir)
    if not s4.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo knowledge_inputs: " + "; ".join(s4.errors))

    s5 = runner.run_stage(
        "build_budget",
        stage_build_budget,
        s1.output["cad_facts"],
        s3.output["vision_results"],
        s4.output["bc3_catalog"],
        s4.output["embedding_index"],
        s4.output["training_pairs"],
        s1.output["raw_json_path"],
        s1.output["normalized_json_path"],
        s1.output["uploaded_object_name"],
        s2.output["pages_dir"],
        s4.output["xlsx_training_path"],
        run_dir,
    )
    if not s5.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo build_budget: " + "; ".join(s5.errors))

    s6 = runner.run_stage(
        "excel_export",
        stage_excel_export,
        s5.output["context"],
        s5.output["budget"],
        run_dir,
    )
    if not s6.ok:
        _finish(runner, run_dir)
        raise RuntimeError("Fallo excel_export: " + "; ".join(s6.errors))

    summary = {
        "pipeline": "full",
        "dwg": str(dwg_path),
        "pdf": str(pdf_path),
        "budget_excel": str(s6.output["saved_workbook_path"]),
    }
    _finish(runner, run_dir, summary)
    return Path(s6.output["saved_workbook_path"])


def _run_pipeline_cad_only(
    dwg_path: Path,
    run_dir: Path,
    bc3_path: Path,
    training_pres: Path,
    slug: str,
    pres_template_takeoffs: bool,
) -> Path:
    bucket_name = BUCKET_NAME or APS_BUCKET_NAME
    logger.info("APS: extrayendo (puede tardar varios minutos)…")
    aps = stage_aps_extraction(dwg_path, run_dir, bucket_name)

    bc3_catalog = parse_bc3(str(bc3_path))
    bc3_catalog["_source_path"] = str(bc3_path)

    training_pairs: list = []
    try:
        training_pairs = extract_training_pairs(str(training_pres))
        logger.info("Pares de entrenamiento desde PRES: %d", len(training_pairs))
    except Exception:
        logger.warning("No se pudieron leer pares desde PRES", exc_info=True)

    embedding_index = None
    if bc3_catalog.get("items"):
        try:
            embedding_index = load_or_build_embeddings(bc3_catalog)
            logger.info("Embeddings BC3 listos (%d items)", len(embedding_index.metadata))
        except Exception:
            logger.warning("Embeddings no disponibles", exc_info=True)

    raw_json_path = Path(aps["raw_json_path"])
    normalized_json_path = Path(aps["normalized_json_path"])
    cad_facts = aps["cad_facts"]
    uploaded_object_name = str(aps.get("uploaded_object_name", ""))

    context = ProjectContext(
        project_id=slug,
        project_name=f"Dupla — {dwg_path.stem}",
        source_json_path=str(raw_json_path),
        plan_image_paths=[],
        bc3_path=str(bc3_path),
        metadata={
            "dwg_path": str(dwg_path),
            "raw_autodesk_json": str(raw_json_path),
            "normalized_json": str(normalized_json_path),
            "vision_pages_dir": "",
            "uploaded_object_name": uploaded_object_name,
            "upload_object_name_override": UPLOAD_OBJECT_NAME,
            "auto_unique_object_name": AUTO_UNIQUE_OBJECT_NAME,
            "translation_views": list(TRANSLATION_VIEWS),
            "translation_timeout_seconds": TRANSLATION_TIMEOUT_SECONDS,
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "max_property_wait_seconds": MAX_PROPERTY_WAIT_SECONDS,
            "failed_manifest_grace_polls": FAILED_MANIFEST_GRACE_POLLS,
            "failed_manifest_grace_sleep_seconds": FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
            "xlsx_path": str(training_pres),
            "pres_template_takeoffs": pres_template_takeoffs,
            "pipeline_mode": "cad_only_no_vision",
        },
    )

    logger.info("Presupuesto: inventario híbrido solo CAD…")
    budget = build_budget_from_sources(
        context=context,
        cad_facts=cad_facts,
        vision_payloads=[],
        bc3_catalog=bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
    )

    (run_dir / "dupla_full_budget_output.json").write_text(
        json.dumps(budget, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    gen_xlsx = run_dir / "dupla_presupuesto_generado.xlsx"
    export_budget_workbook(context, budget["rows"], gen_xlsx)
    return gen_xlsx


def main() -> int:
    parser = argparse.ArgumentParser(description="DWG + PRES: pipeline y comparación")
    parser.add_argument("--dwg", type=str, default="", help="Ruta al .dwg")
    parser.add_argument("--pres", type=str, default="", help="PRES.xlsx de referencia")
    parser.add_argument("--pdf", type=str, default="", help="PDF para visión (modo full). Si se omite, se busca junto al DWG.")
    parser.add_argument(
        "--bc3",
        type=str,
        default=str(REPO_ROOT / "data" / "TGIU.bc3"),
        help="Catálogo BC3",
    )
    parser.add_argument(
        "--pipeline",
        choices=("full", "cad-only"),
        default="full",
        help="full = APS+PDF+visión+presupuesto; cad-only = solo APS+CAD.",
    )
    parser.add_argument(
        "--compare-baseline",
        choices=("structural", "full"),
        default="structural",
        help="structural = comparar contra PRES filtrado (estructura/cimentación); full = PRES completo.",
    )
    parser.add_argument(
        "--pres-template-takeoffs",
        action="store_true",
        help="Inyectar takeoffs sintéticos desde PRES (sube cobertura; revisar trazabilidad).",
    )
    parser.add_argument("--no-open-excel", action="store_true", help="No abrir Excel al final")
    args = parser.parse_args()

    dwg_path = Path(args.dwg).resolve() if args.dwg else None
    if dwg_path is None or not dwg_path.is_file():
        candidate = _default_dwg()
        if candidate is None:
            print("No se encontró ningún .dwg. Usa --dwg.", file=sys.stderr)
            return 1
        dwg_path = candidate

    pres_path = Path(args.pres).resolve() if args.pres else _default_pres()
    if not pres_path.is_file():
        print(f"No existe el PRES: {pres_path}", file=sys.stderr)
        return 1

    bc3_path = Path(args.bc3).resolve()
    if not bc3_path.is_file():
        print(f"No existe el BC3: {bc3_path}", file=sys.stderr)
        return 1

    pdf_path: Path | None = None
    if args.pipeline == "full":
        if args.pdf:
            pdf_path = Path(args.pdf).resolve()
        else:
            pdf_path = _find_pdf_for_dwg(dwg_path)
        if pdf_path is None or not pdf_path.is_file():
            print(
                "Modo --pipeline full requiere un PDF. Usa --pdf ruta.pdf o coloca un .pdf junto al DWG. "
                "Alternativa: --pipeline cad-only",
                file=sys.stderr,
            )
            return 1

    now = datetime.now()
    run_date = now.strftime("%Y-%m-%d")
    run_folder = now.strftime("%Y-%m-%d_%H%M%S")
    run_tag = run_folder
    slug = _slug_from_dwg(dwg_path)
    run_dir = REPO_ROOT / "comparisons" / "budget" / slug / run_folder
    run_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(console_level=logging.INFO, log_file=run_dir / "run.log")
    logger.info("DWG: %s", dwg_path)
    logger.info("PRES: %s", pres_path)
    logger.info("Pipeline: %s", args.pipeline)
    logger.info("Comparar contra: %s", args.compare_baseline)
    logger.info("Salida: %s", run_dir)

    pres_full_copy = run_dir / "PRES_referencia_completo.xlsx"
    shutil.copy2(pres_path, pres_full_copy)

    pres_structural_path = run_dir / "PRES_estructural_filtrado.xlsx"
    stats = filter_pres_workbook_structural(pres_path, pres_structural_path)
    logger.info(
        "PRES estructural: filas cuerpo=%s, conservadas=%s, partidas=%s",
        stats["input_body_rows"],
        stats["kept_rows"],
        stats["partidas_kept"],
    )

    if args.compare_baseline == "structural":
        pres_compare = pres_structural_path
        training_source = pres_structural_path
    else:
        pres_compare = pres_full_copy
        training_source = pres_full_copy

    training_rel = _path_for_dupla_config(training_source)

    try:
        if args.pipeline == "full":
            assert pdf_path is not None
            gen_xlsx = _run_pipeline_full(
                dwg_path,
                run_dir,
                pdf_path,
                bc3_path,
                training_rel,
                slug,
                args.pres_template_takeoffs,
            )
        else:
            gen_xlsx = _run_pipeline_cad_only(
                dwg_path,
                run_dir,
                bc3_path,
                training_source,
                slug,
                args.pres_template_takeoffs,
            )
    except RuntimeError as exc:
        logger.error("%s", exc)
        print(exc, file=sys.stderr)
        return 1

    logger.info("Excel generado: %s", gen_xlsx)

    notes_lines = [
        f"- **Pipeline:** `{args.pipeline}`"
        + (
            f" (PDF visión: `{pdf_path}`)"
            if args.pipeline == "full" and pdf_path
            else ""
        ),
        "- **Baseline de comparación:** "
        + (
            "`PRES_estructural_filtrado.xlsx` (heurística: movimiento de tierra, hormigón armado, acero; "
            "excluye instalaciones y acabados típicos)."
            if args.compare_baseline == "structural"
            else "`PRES_referencia_completo.xlsx`."
        ),
    ]
    if args.pres_template_takeoffs:
        notes_lines.append(
            "- **pres_template_takeoffs:** activo (líneas sintéticas desde PRES; validar cantidades)."
        )
    notes = "\n".join(notes_lines)

    md_title = f"Comparación presupuesto — {dwg_path.stem}"
    md_body = build_comparison_markdown(
        gen_xlsx,
        pres_compare,
        title=md_title,
        run_date=run_date,
        run_tag=run_tag,
        notes=notes,
    )
    suffix = "estructural" if args.compare_baseline == "structural" else "completo"
    md_path = run_dir / f"diferencias_{run_date}_{suffix}.md"
    md_path.write_text(md_body, encoding="utf-8")
    build_comparison_report(gen_xlsx, pres_compare, run_dir)

    manifest_path = run_dir / "README_CORRIDA.txt"
    manifest_path.write_text(
        "\n".join(
            [
                f"fecha={run_date}",
                f"etiqueta_carpeta={run_tag}",
                f"pipeline={args.pipeline}",
                f"compare_baseline={args.compare_baseline}",
                f"dwg={dwg_path}",
                f"pres_origen={pres_path}",
                f"pdf={pdf_path or 'N/A'}",
                f"generado_xlsx={gen_xlsx}",
                f"pres_comparado={pres_compare}",
                f"pres_completo_copia={pres_full_copy}",
                f"markdown={md_path}",
                f"pres_template_takeoffs={args.pres_template_takeoffs}",
                f"pres_filter_stats={stats}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(gen_xlsx)
    print(pres_compare)
    print(md_path)

    if not args.no_open_excel:
        _open_in_excel([gen_xlsx, pres_compare])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
