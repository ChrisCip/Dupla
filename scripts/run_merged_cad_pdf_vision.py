"""
CAD fusionado (varios DWG → project_merged.normalized.json) + PDF del mismo proyecto
→ render → GPT-4o visión → BC3 → Excel **dupla_presupuesto_generado_cad_vision_<proyecto>.xlsx**.

Por defecto **no** usa PRES.xlsx (suele ser de otro trabajo). Opcional: ``--use-pres-training``.

Requiere OPENAI_API_KEY en .env y PyMuPDF (pip install pymupdf).

Uso:
    python scripts/run_merged_cad_pdf_vision.py --pdf "Batch_Publish_20260406 (Conflicted Copy).pdf"
    python scripts/run_merged_cad_pdf_vision.py --pdf ruta.pdf --merged-json output/.../project_merged.normalized.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from budget.export_excel import export_budget_workbook
from core.logging_config import setup_logging
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from dupla_run_full_analysis_local import (
    AUTO_UNIQUE_OBJECT_NAME,
    FAILED_MANIFEST_GRACE_POLLS,
    FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
    MAX_PROPERTY_WAIT_SECONDS,
    POLL_INTERVAL_SECONDS,
    TRANSLATION_TIMEOUT_SECONDS,
    TRANSLATION_VIEWS,
    UPLOAD_OBJECT_NAME,
    _pdf_pages_cache_dir,
    render_pdf_to_images,
    stage_excel_export,
    stage_knowledge_inputs,
    stage_vision_analysis,
)

logger = logging.getLogger("dupla.merged_pdf_vision")


def _find_latest_merged_json() -> Path | None:
    roots = [
        REPO_ROOT / "output" / "prueba_web_01",
        REPO_ROOT / "output" / "multi_dwg_project",
    ]
    candidates: list[Path] = []
    for base in roots:
        if base.is_dir():
            candidates.extend(base.rglob("project_merged.normalized.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _cad_facts_for_pipeline(merged: dict) -> dict:
    return {k: v for k, v in merged.items() if not str(k).startswith("_")}


def _slug_for_excel_filename(project_id: str) -> str:
    s = project_id.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_") or "proyecto"
    return s[:80]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merged CAD + PDF → visión GPT → presupuesto")
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(REPO_ROOT / "Batch_Publish_20260406 (Conflicted Copy).pdf"),
        help="PDF del batch de planos",
    )
    parser.add_argument(
        "--merged-json",
        type=str,
        default="",
        help="project_merged.normalized.json (por defecto: el más reciente bajo output/multi_dwg_project/)",
    )
    parser.add_argument(
        "--vision-output-dir",
        default="",
        help="Carpeta para renders, visión, Excel e JSON (recomendado: …/run_xxx/pdf_vision). "
        "Si se omite: <carpeta_del_merge>/pdf_vision/",
    )
    parser.add_argument(
        "--project-id",
        default="prueba_web_01",
    )
    parser.add_argument(
        "--project-name",
        default="Prueba web 01 — CAD fusionado + PDF (GPT visión)",
    )
    parser.add_argument(
        "--excel-suffix",
        default="",
        help="Sufijo del .xlsx (por defecto = project-id saneado). "
        "Salida: dupla_presupuesto_generado_cad_vision_<sufijo>.xlsx",
    )
    parser.add_argument(
        "--use-pres-training",
        action="store_true",
        help="Cargar PRES.xlsx como pares few-shot (por defecto NO: PRES suele ser de otro proyecto).",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        logger.error("No existe el PDF: %s", pdf_path)
        return 1

    merged_path = Path(args.merged_json).resolve() if args.merged_json else None
    if merged_path is None or not merged_path.is_file():
        latest = _find_latest_merged_json()
        if latest is None:
            logger.error(
                "No hay project_merged.normalized.json. Ejecuta antes scripts/run_multi_dwg_project_cad.py "
                "o pasa --merged-json explícito.",
            )
            return 1
        merged_path = latest
        logger.info("Usando merge más reciente: %s", merged_path)

    merge_dir = merged_path.parent
    raw_sibling = merge_dir / "BLCAD14001.autodesk_raw.json"
    if not raw_sibling.is_file():
        raw_sibling = merged_path

    if args.vision_output_dir:
        out_dir = Path(args.vision_output_dir).resolve()
    else:
        out_dir = (merge_dir / "pdf_vision").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(console_level=logging.INFO, log_file=out_dir / "run.log")

    merged = json.loads(merged_path.read_text(encoding="utf-8"))
    cad_facts = _cad_facts_for_pipeline(merged)
    sources = merged.get("_merge_sources") or []

    import dupla_run_full_analysis_local as dr

    dr.PROJECT_ID = args.project_id
    dr.PROJECT_NAME = args.project_name
    dr.PRES_TEMPLATE_TAKEOFFS = False
    suffix = _slug_for_excel_filename(args.excel_suffix or args.project_id)
    dr.OUTPUT_NAME = f"dupla_presupuesto_generado_cad_vision_{suffix}"
    dr.BC3_PATH = "./data/TGIU.bc3"
    if args.use_pres_training:
        pres_root = REPO_ROOT / "PRES.xlsx"
        dr.XLSX_TRAINING_PATH = "PRES.xlsx" if pres_root.is_file() else "./data/PRES.xlsx"
        logger.info("Pares de entrenamiento: desde PRES (modo explícito --use-pres-training)")
    else:
        dr.XLSX_TRAINING_PATH = "__no_pres_training__.xlsx"
        logger.info("Sin PRES: matching BC3 solo con catálogo / embeddings (no otro proyecto).")

    logger.info("PDF: %s", pdf_path)
    logger.info("CAD fusionado: %s", merged_path)
    logger.info("Salida: %s", out_dir)

    pages_dir = _pdf_pages_cache_dir(out_dir, pdf_path)
    image_paths = render_pdf_to_images(pdf_path, pages_dir)
    logger.info("Renderizadas %d páginas → %s", len(image_paths), pages_dir)

    vision = stage_vision_analysis(pages_dir, cad_facts, out_dir)

    k = stage_knowledge_inputs(out_dir)
    if not k.get("bc3_catalog"):
        logger.error("BC3 vacío o no cargado. Revisa dupla_run_full_analysis_local.BC3_PATH / data/TGIU.bc3")
        return 1

    page_paths = sorted(
        str(p)
        for p in pages_dir.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    xlsx_training = k.get("xlsx_training_path") if args.use_pres_training else None

    context = ProjectContext(
        project_id=args.project_id,
        project_name=args.project_name,
        source_json_path=str(raw_sibling),
        plan_image_paths=page_paths,
        bc3_path=str(k["bc3_catalog"].get("_source_path", "")) if k.get("bc3_catalog") else None,
        metadata={
            "dwg_path": str(merged_path),
            "pdf_path": str(pdf_path),
            "raw_autodesk_json": str(raw_sibling),
            "normalized_json": str(merged_path),
            "merge_sources": sources,
            "vision_pages_dir": str(pages_dir),
            "vision_inventory_json": str(vision["vision_json_path"]),
            "uploaded_object_name": "merged_cad_plus_pdf_vision",
            "upload_object_name_override": UPLOAD_OBJECT_NAME,
            "auto_unique_object_name": AUTO_UNIQUE_OBJECT_NAME,
            "translation_views": list(TRANSLATION_VIEWS),
            "translation_timeout_seconds": TRANSLATION_TIMEOUT_SECONDS,
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "max_property_wait_seconds": MAX_PROPERTY_WAIT_SECONDS,
            "failed_manifest_grace_polls": FAILED_MANIFEST_GRACE_POLLS,
            "failed_manifest_grace_sleep_seconds": FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
            "xlsx_path": xlsx_training or "",
            "pres_training_used": args.use_pres_training,
            "pres_template_takeoffs": False,
            "pipeline_mode": "merged_multi_dwg_pdf_vision",
        },
    )

    budget = build_budget_from_sources(
        context=context,
        cad_facts=cad_facts,
        vision_payloads=vision["vision_results"],
        bc3_catalog=k["bc3_catalog"],
        embedding_index=k["embedding_index"],
        training_pairs=k["training_pairs"],
    )

    budget_json = out_dir / "dupla_full_budget_output.json"
    budget_json.write_text(json.dumps(budget, indent=2, ensure_ascii=False), encoding="utf-8")

    export = stage_excel_export(context, budget, out_dir)

    readme = out_dir / "README_CORRIDA.txt"
    readme.write_text(
        "\n".join(
            [
                f"pdf={pdf_path}",
                f"merged_normalized={merged_path}",
                f"vision_results={vision['vision_json_path']}",
                f"budget_json={budget_json}",
                f"excel={export['saved_workbook_path']}",
                f"pages={len(page_paths)}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    logger.info("Listo: %s", export["saved_workbook_path"])
    print(export["saved_workbook_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
