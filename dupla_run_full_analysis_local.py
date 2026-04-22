
"""
Dupla local full-run wrapper.

Edit the CONFIG section and run:
    python dupla_run_full_analysis_local.py

Or pass a manifest (rutas relativas al YAML o absolutas):
    python dupla_run_full_analysis_local.py --project inputs/projects/mi.yaml
    python dupla_run_full_analysis_local.py --project inputs/projects/mi.yaml --validate-only

Recommended location:
- Save this file in the ROOT of your Dupla repo

Pipeline stages (each tracked with timing and error capture):
1. APS extraction — upload DWG, translate, normalize CAD facts
2. Vision pages — render PDF or locate image directory
3. Vision analysis — GPT-4o vision per page → inventory dicts
4. Knowledge inputs — BC3 catalog, training pairs, embeddings
5. Budget core — hybrid inventory → takeoffs → BC3 match → compose
6. Excel export — styled workbook + reviewer sheet

Notes:
- Requires the Dupla repo dependencies installed
- Requires .env with Autodesk + OpenAI keys
- If USE_PDF = True, it requires PyMuPDF for PDF rendering
- Pipeline report saved to outputs as pipeline_report.json
- Full debug log saved to outputs as dupla_debug.log
- Evolución del criterio de visión: editar `knowledge/office_methodology.md` y re-ejecutar
  (mismo diseño; `OFFICE_METHODOLOGY_PATH` en CONFIG apunta al markdown).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

# ========= CONFIG: EDIT THIS SECTION =========
PROJECT_NAME = "Torre Giualca I"
PROJECT_ID = "torre_giualca_i"

# Input files
DWG_PATH = r"C:\Users\chris\Downloads\archivos dupla\dwg\2- PLANTAS ARQUITECTONICAS.dwg"
PDF_PATH = r"C:\Users\chris\Downloads\archivos dupla\dwg\prueba dupla pdf\prueba dupla full.pdf"   # Used only if USE_PDF = True
IMAGES_DIR = r"./inputs/rendered_pages"   # Used only if USE_PDF = False
BC3_PATH = r"./data/TGIU.bc3"             # Optional: can be blank ""
XLSX_TRAINING_PATH = r"./data/NASAS09_Preliminary_Budget.xlsx"
# Presupuesto Excel de referencia (NASAS 09, formato Preliminary) para few-shot BC3.
# Set True only to clone PRES rows into takeoffs (calibration); default is measured takeoffs only.
PRES_TEMPLATE_TAKEOFFS = False

# Visual stage selection
USE_PDF = True  # True = render PDF pages; False = use IMAGES_DIR directly

# Autodesk Model Derivative behavior
TRANSLATION_VIEWS = ("2d",)  # Add "3d" only when a workflow explicitly needs it
TRANSLATION_TIMEOUT_SECONDS = 3600
POLL_INTERVAL_SECONDS = 10
MAX_PROPERTY_WAIT_SECONDS = 3600
FAILED_MANIFEST_GRACE_POLLS = 3
FAILED_MANIFEST_GRACE_SLEEP_SECONDS = 20

# Autodesk OSS upload naming
UPLOAD_OBJECT_NAME = None  # Set a string to override the uploaded Autodesk object name
AUTO_UNIQUE_OBJECT_NAME = True

# Office methodology (step 1 evolution loop) — markdown injected into every vision page prompt.
# Edit knowledge/office_methodology.md between runs; set to "" to disable.
OFFICE_METHODOLOGY_PATH = "./knowledge/office_methodology.md"

# Outputs (ruta relativa al repo por defecto — evita depender de otra cuenta de Windows)
OUTPUTS_DIR = "./output/run"
OUTPUT_NAME = "dupla_budget_ready_full"

# Optional Autodesk bucket override (or leave None to use APS_BUCKET_NAME from .env)
BUCKET_NAME = None
# ============================================

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.project_manifest import ProjectManifest, load_project_manifest, validate_manifest


def _load_office_methodology(rel_path: str | None) -> tuple[str, str | None]:
    """
    Load markdown text for vision prompts. Returns (text, resolved_path_or_none).
    Empty string if disabled or file missing.
    """
    if not rel_path or not str(rel_path).strip():
        return "", None
    path = (REPO_ROOT / rel_path).resolve()
    if not path.exists():
        logging.getLogger("dupla.local").warning(
            "OFFICE_METHODOLOGY_PATH not found (%s) — vision runs without office block.",
            path,
        )
        return "", str(path)
    text = path.read_text(encoding="utf-8").strip()
    return text, str(path)

from aps_integration.aps_auth import get_aps_token
from aps_integration.model_derivative import extract_dwg_data
from aps_integration.oss_manager import APS_BUCKET_NAME, create_bucket, upload_file_to_bucket
from agents.vision_agent import run_full_vision_analysis
from budget.export_bc3 import export_budget_bc3
from budget.export_excel import export_budget_workbook
from core.logging_config import setup_logging
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from core.stage import PipelineRunner
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.methodology_generator import generate_methodology_context
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import parse_bc3
from processors.json_processor import process_autodesk_json

logger = logging.getLogger("dupla.runner")


def _build_run_defaults() -> SimpleNamespace:
    """Config efectiva desde el bloque CONFIG (sin project.yaml)."""
    dwg = Path(DWG_PATH)
    if not dwg.is_absolute():
        dwg = (REPO_ROOT / dwg).resolve()
    else:
        dwg = dwg.resolve()
    pdf = (REPO_ROOT / Path(PDF_PATH)).resolve() if PDF_PATH else None
    images = (REPO_ROOT / Path(IMAGES_DIR)).resolve()
    bc3 = (REPO_ROOT / Path(BC3_PATH)).resolve() if BC3_PATH else None
    xlsx = (REPO_ROOT / Path(XLSX_TRAINING_PATH)).resolve() if XLSX_TRAINING_PATH else None
    out = (REPO_ROOT / Path(OUTPUTS_DIR)).resolve()
    return SimpleNamespace(
        project_name=PROJECT_NAME,
        project_id=PROJECT_ID,
        dwg_path=dwg,
        pdf_path=pdf,
        images_dir=images,
        use_pdf=USE_PDF,
        bc3_path=bc3,
        xlsx_training_path=xlsx,
        outputs_dir=out,
        output_name=OUTPUT_NAME,
        bucket_name=BUCKET_NAME,
        vision_profile=None,
        vision_sources=[],
        pres_template_takeoffs=PRES_TEMPLATE_TAKEOFFS,
        translation_views=TRANSLATION_VIEWS,
        translation_timeout_seconds=TRANSLATION_TIMEOUT_SECONDS,
        poll_interval_seconds=POLL_INTERVAL_SECONDS,
        max_property_wait_seconds=MAX_PROPERTY_WAIT_SECONDS,
        failed_manifest_grace_polls=FAILED_MANIFEST_GRACE_POLLS,
        failed_manifest_grace_sleep_seconds=FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
        auto_unique_object_name=AUTO_UNIQUE_OBJECT_NAME,
        upload_object_name=UPLOAD_OBJECT_NAME,
    )


RUN = _build_run_defaults()


def apply_project_manifest(m: ProjectManifest) -> None:
    global RUN
    RUN = SimpleNamespace(
        project_name=m.project_name,
        project_id=m.project_id,
        dwg_path=m.dwg_path,
        pdf_path=m.pdf_path,
        images_dir=m.images_dir or (REPO_ROOT / Path(IMAGES_DIR)).resolve(),
        use_pdf=m.use_pdf,
        bc3_path=m.bc3_path,
        xlsx_training_path=m.xlsx_training_path,
        outputs_dir=m.outputs_dir,
        output_name=m.output_name,
        bucket_name=m.bucket_name,
        vision_profile=m.vision_profile,
        vision_sources=list(m.vision_sources),
        pres_template_takeoffs=m.pres_template_takeoffs,
        translation_views=m.translation_views,
        translation_timeout_seconds=m.translation_timeout_seconds,
        poll_interval_seconds=m.poll_interval_seconds,
        max_property_wait_seconds=m.max_property_wait_seconds,
        failed_manifest_grace_polls=m.failed_manifest_grace_polls,
        failed_manifest_grace_sleep_seconds=m.failed_manifest_grace_sleep_seconds,
        auto_unique_object_name=m.auto_unique_object_name,
        upload_object_name=m.upload_object_name,
    )


# ---------------------------------------------------------------------------
# Stage functions — each returns its output (or a tuple for metrics)
# ---------------------------------------------------------------------------

def _pdf_pages_cache_dir(outputs_dir: Path, pdf_path: Path) -> Path:
    """
    Carpeta corta bajo rendered_pages/ para evitar MAX_PATH en Windows cuando el
    nombre del PDF es muy largo (fitz no abre rutas truncadas).
    """
    key = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return outputs_dir / "rendered_pages" / f"p_{key}"


def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "USE_PDF=True but PyMuPDF is not installed.\n"
            "Install it with:\n"
            "    pip install pymupdf"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    image_paths: list[Path] = []

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = output_dir / f"page_{page_index + 1:04d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)

    return image_paths


def stage_aps_extraction(
    dwg_path: Path,
    outputs_dir: Path,
    bucket_name: str,
) -> dict:
    """Stage 1: Upload DWG to APS, extract and normalize CAD facts."""
    token = get_aps_token()
    create_bucket(token, bucket_name)

    unique_suffix = None
    if RUN.auto_unique_object_name:
        unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.debug("Auto-unique upload suffix: %s", unique_suffix)

    object_name = upload_file_to_bucket(
        token,
        bucket_name,
        str(dwg_path),
        object_name=RUN.upload_object_name,
        unique_suffix=unique_suffix,
    )
    if not object_name:
        raise RuntimeError("DWG upload to Autodesk failed.")
    logger.info("DWG uploaded as %r to bucket %r", object_name, bucket_name)

    raw_data = extract_dwg_data(
        token,
        bucket_name,
        object_name,
        views=RUN.translation_views,
        translation_timeout_seconds=RUN.translation_timeout_seconds,
        poll_interval_seconds=RUN.poll_interval_seconds,
        max_property_wait_seconds=RUN.max_property_wait_seconds,
        failed_manifest_grace_polls=RUN.failed_manifest_grace_polls,
        failed_manifest_grace_sleep_seconds=RUN.failed_manifest_grace_sleep_seconds,
    )
    raw_json_path = outputs_dir / f"{dwg_path.stem}.autodesk_raw.json"
    raw_json_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Raw Autodesk JSON saved: %s", raw_json_path)

    normalized = process_autodesk_json(str(raw_json_path))
    normalized_json_path = outputs_dir / f"{dwg_path.stem}.normalized.json"
    normalized_json_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Normalized CAD facts saved: %s (%d keys)", normalized_json_path, len(normalized))

    return {
        "cad_facts": normalized,
        "raw_json_path": raw_json_path,
        "normalized_json_path": normalized_json_path,
        "uploaded_object_name": object_name,
    }


def stage_resolve_pages(outputs_dir: Path) -> dict:
    """Stage 2: Render PDF(s) o imágenes; opcionalmente varios PDF por disciplina (vision.sources)."""
    if RUN.vision_sources:
        bundles: list[dict] = []
        total_pages = 0
        for src in RUN.vision_sources:
            if src.use_pdf and src.pdf:
                if not src.pdf.exists():
                    raise FileNotFoundError(f"PDF file not found: {src.pdf}")
                rendered_dir = _pdf_pages_cache_dir(outputs_dir, src.pdf)
                image_paths = render_pdf_to_images(src.pdf, rendered_dir)
                total_pages += len(image_paths)
                bundles.append(
                    {"pages_dir": rendered_dir, "discipline": src.discipline, "page_count": len(image_paths)}
                )
                logger.info(
                    "Rendered %d pages from PDF [%s]: %s",
                    len(image_paths),
                    src.discipline,
                    src.pdf.name,
                )
            elif not src.use_pdf and src.images_dir:
                images_dir = src.images_dir.resolve()
                if not images_dir.exists():
                    raise FileNotFoundError(f"Images directory not found: {images_dir}")
                count = sum(
                    1 for p in images_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                )
                bundles.append({"pages_dir": images_dir, "discipline": src.discipline, "page_count": count})
                total_pages += count
                logger.info("Using images [%s]: %s (%d)", src.discipline, images_dir, count)
            else:
                raise ValueError("Each vision.sources entry needs pdf (use_pdf true) or images_dir (use_pdf false)")
        return {
            "multi": True,
            "bundles": bundles,
            "page_count": total_pages,
            "source": "multi_input",
            "pages_dir": bundles[0]["pages_dir"] if bundles else None,
        }

    if RUN.use_pdf:
        pdf_path = RUN.pdf_path
        if not pdf_path or not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        rendered_dir = _pdf_pages_cache_dir(outputs_dir, pdf_path)
        image_paths = render_pdf_to_images(pdf_path, rendered_dir)
        logger.info("Rendered %d pages from PDF: %s", len(image_paths), pdf_path.name)
        return {
            "multi": False,
            "bundles": [],
            "pages_dir": rendered_dir,
            "page_count": len(image_paths),
            "source": "pdf",
        }

    images_dir = RUN.images_dir.resolve()
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    count = sum(1 for p in images_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    logger.info("Using existing images directory: %s (%d images)", images_dir, count)
    return {
        "multi": False,
        "bundles": [],
        "pages_dir": images_dir,
        "page_count": count,
        "source": "directory",
    }


def stage_vision_analysis(
    pages_input: Path | dict,
    cad_facts: dict,
    outputs_dir: Path,
    *,
    auto_methodology: str | None = None,
) -> dict:
    """GPT-4o visión: metodología + perfil por disciplina; multi-PDF si vision.sources."""
    manual_text, manual_path = _load_office_methodology(OFFICE_METHODOLOGY_PATH)
    parts: list[str] = []
    if auto_methodology and auto_methodology.strip():
        parts.append(auto_methodology.strip())
        logger.info("Auto methodology from PRES/BC3: %d chars", len(auto_methodology))
    if manual_text.strip():
        parts.append(manual_text.strip())
        logger.info("Manual methodology from %s: %d chars", manual_path, len(manual_text))
    methodology = "\n\n---\n\n".join(parts) if parts else None
    if methodology:
        logger.info("Combined methodology for vision: %d chars", len(methodology))
    else:
        logger.info("No methodology context for vision (PRES/BC3/manual all empty)")

    vision_results: list[dict]
    if isinstance(pages_input, dict) and pages_input.get("multi"):
        vision_results = []
        for bundle in pages_input["bundles"]:
            pages_dir = bundle["pages_dir"]
            profile_key = bundle["discipline"]
            part = run_full_vision_analysis(
                str(pages_dir),
                cad_facts,
                office_methodology=methodology,
                vision_profile_key=profile_key,
            )
            for row in part:
                if isinstance(row, dict):
                    md = row.setdefault("_metadata", {})
                    md["source_discipline"] = profile_key
            vision_results.extend(part)
    else:
        assert isinstance(pages_input, Path)
        vision_results = run_full_vision_analysis(
            str(pages_input),
            cad_facts,
            office_methodology=methodology,
            vision_profile_key=RUN.vision_profile,
        )

    if methodology:
        snap = outputs_dir / "office_methodology_snapshot.md"
        snap.write_text(methodology, encoding="utf-8")
        logger.info("Methodology snapshot for this run: %s", snap.name)

    vision_json_path = outputs_dir / "vision_inventory_results.json"
    vision_json_path.write_text(json.dumps(vision_results, indent=2, ensure_ascii=False), encoding="utf-8")

    error_count = sum(1 for r in vision_results if isinstance(r, dict) and "error" in r)
    ok_count = len(vision_results) - error_count
    logger.info("Vision analysis: %d pages OK, %d errors", ok_count, error_count)
    if error_count:
        for r in vision_results:
            if isinstance(r, dict) and "error" in r:
                logger.warning("Vision error on %s: %s", r.get("file", "?"), r.get("error"))

    return {
        "vision_results": vision_results,
        "vision_json_path": vision_json_path,
        "pages_ok": ok_count,
        "pages_with_errors": error_count,
        "methodology_chars": len(methodology or ""),
    }


def stage_knowledge_inputs(outputs_dir: Path) -> dict:
    """Stage 4: Load BC3 catalog, training pairs, and build embeddings."""
    bc3_catalog: dict = {}
    bc3_path_value = None
    if RUN.bc3_path:
        bc3_path = RUN.bc3_path
        if not bc3_path.exists():
            raise FileNotFoundError(f"BC3 file not found: {bc3_path}")
        bc3_catalog = parse_bc3(str(bc3_path))
        bc3_path_value = str(bc3_path)
        logger.info("BC3 catalog loaded: %d items from %s", len(bc3_catalog.get("items", [])), bc3_path.name)
    else:
        logger.info("BC3 catalog: skipped (no BC3_PATH configured)")

    training_pairs = []
    if not RUN.xlsx_training_path or str(RUN.xlsx_training_path).startswith("__no_pres_training"):
        xlsx_training_path = (REPO_ROOT / "_skipped_training.xlsx").resolve()
        logger.info("XLSX training omitido (sin PRES / proyecto independiente).")
    else:
        xlsx_training_path = RUN.xlsx_training_path.resolve()
        if xlsx_training_path.exists():
            training_pairs = extract_training_pairs(xlsx_training_path)
            logger.info("Training pairs loaded: %d from %s", len(training_pairs), xlsx_training_path.name)
        else:
            logger.warning("XLSX training file not found: %s", xlsx_training_path)

    embedding_index = None
    if bc3_catalog.get("items"):
        embedding_index = load_or_build_embeddings(bc3_catalog)
        logger.info(
            "Embeddings ready: %d items, model=%s",
            len(embedding_index.metadata), embedding_index.model,
        )
    else:
        logger.info("Embeddings skipped (BC3 catalog empty)")

    auto_methodology = generate_methodology_context(
        training_pairs=training_pairs or None,
        bc3_catalog=bc3_catalog or None,
    )
    if auto_methodology:
        logger.info("Auto methodology generated: %d chars", len(auto_methodology))
    else:
        logger.info("Auto methodology: empty (no PRES/BC3 data)")

    return {
        "bc3_catalog": bc3_catalog,
        "bc3_path_value": bc3_path_value,
        "training_pairs": training_pairs,
        "embedding_index": embedding_index,
        "xlsx_training_path": str(xlsx_training_path) if xlsx_training_path.exists() else None,
        "auto_methodology": auto_methodology,
    }


def _collect_image_paths(pages_dir: Path) -> list[str]:
    return sorted(
        str(path)
        for path in pages_dir.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )


def stage_build_budget(
    cad_facts: dict,
    vision_results: list,
    bc3_catalog: dict,
    embedding_index,
    training_pairs: list,
    raw_json_path: Path,
    normalized_json_path: Path,
    uploaded_object_name: str,
    pages_resolution: Path | dict,
    xlsx_path: str | None,
    outputs_dir: Path,
) -> dict:
    """Stage 5: Build hybrid inventory, quantify, match BC3, compose budget."""
    if isinstance(pages_resolution, dict) and pages_resolution.get("multi"):
        page_paths: list[str] = []
        vision_dir_parts: list[str] = []
        for bundle in pages_resolution["bundles"]:
            pd = bundle["pages_dir"]
            page_paths.extend(_collect_image_paths(pd))
            vision_dir_parts.append(str(pd))
        page_paths = sorted(set(page_paths))
        vision_pages_dir_meta = "|".join(vision_dir_parts)
    else:
        assert isinstance(pages_resolution, Path)
        page_paths = _collect_image_paths(pages_resolution)
        vision_pages_dir_meta = str(pages_resolution)

    logger.info("Building budget with %d rendered pages", len(page_paths))

    context = ProjectContext(
        project_id=RUN.project_id,
        project_name=RUN.project_name,
        source_json_path=str(raw_json_path),
        plan_image_paths=page_paths,
        bc3_path=str(bc3_catalog.get("_source_path", "")) if bc3_catalog else None,
        metadata={
            "dwg_path": str(RUN.dwg_path.resolve()),
            "raw_autodesk_json": str(raw_json_path),
            "normalized_json": str(normalized_json_path),
            "vision_pages_dir": vision_pages_dir_meta,
            "uploaded_object_name": uploaded_object_name,
            "upload_object_name_override": RUN.upload_object_name,
            "auto_unique_object_name": RUN.auto_unique_object_name,
            "translation_views": list(RUN.translation_views),
            "translation_timeout_seconds": RUN.translation_timeout_seconds,
            "poll_interval_seconds": RUN.poll_interval_seconds,
            "max_property_wait_seconds": RUN.max_property_wait_seconds,
            "failed_manifest_grace_polls": RUN.failed_manifest_grace_polls,
            "failed_manifest_grace_sleep_seconds": RUN.failed_manifest_grace_sleep_seconds,
            "xlsx_path": xlsx_path,
            "pres_template_takeoffs": RUN.pres_template_takeoffs,
        },
    )

    budget = build_budget_from_sources(
        context=context,
        cad_facts=cad_facts,
        vision_payloads=vision_results,
        bc3_catalog=bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
    )

    budget_json_path = outputs_dir / "dupla_full_budget_output.json"
    budget_json_path.write_text(json.dumps(budget, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Budget JSON saved: %s", budget_json_path)

    return {
        "budget": budget,
        "context": context,
        "budget_json_path": budget_json_path,
        "page_paths": page_paths,
    }


def stage_excel_export(
    context: ProjectContext,
    budget: dict,
    outputs_dir: Path,
) -> dict:
    """Stage 6: Export styled Excel workbook + reviewer sheet."""
    workbook_path = outputs_dir / f"{RUN.output_name}.xlsx"
    saved_workbook_path = export_budget_workbook(
        context=context,
        rows=budget["rows"],
        output_path=workbook_path,
    )
    if saved_workbook_path != workbook_path:
        logger.warning(
            "Workbook path was not writable, saved to alternate: %s", saved_workbook_path
        )

    review_workbook_path = _save_for_review(budget, outputs_dir)
    logger.info("Excel export done: %s + reviewer: %s", saved_workbook_path, review_workbook_path)

    return {
        "saved_workbook_path": saved_workbook_path,
        "review_workbook_path": review_workbook_path,
    }


def stage_bc3_export(
    context: ProjectContext,
    budget: dict,
    outputs_dir: Path,
) -> dict:
    """Stage 7: Export BC3 (FIEBDC) file for Presto import."""
    bc3_output_path = outputs_dir / f"{RUN.output_name}.bc3"
    saved_bc3_path = export_budget_bc3(
        context=context,
        rows=budget["rows"],
        output_path=bc3_output_path,
    )
    logger.info("BC3 (Presto) export done: %s", saved_bc3_path)
    return {"saved_bc3_path": saved_bc3_path}


def _save_for_review(budget: dict, output_dir: Path) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Revision"
    headers = [
        "Código", "Nat", "Ud", "Resumen", "CanPres", "PrPres", "ImpPres",
        "Corrección Código", "Corrección Cantidad", "Corrección Unidad",
        "Tipo Corrección", "Notas Revisor",
    ]
    worksheet.append(headers)
    for row in budget.get("rows", []):
        if not isinstance(row, dict):
            continue
        worksheet.append([
            row.get("code", ""), row.get("nat", ""), row.get("unit", ""),
            row.get("summary", ""), row.get("quantity", ""),
            row.get("unit_price", ""), row.get("amount", ""),
            "", "", "", "", "",
        ])

    for column in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"):
        worksheet.column_dimensions[column].width = 22 if column == "D" else 15

    review_path = output_dir / "dupla_budget_for_review.xlsx"
    workbook.save(review_path)
    return review_path


# ---------------------------------------------------------------------------
# Main — orchestrate via PipelineRunner
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dupla full local pipeline (APS + visión + presupuesto)")
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Ruta a project.yaml (sobrescribe rutas del bloque CONFIG).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Solo validar rutas del manifiesto / CONFIG y salir (sin APS ni OpenAI).",
    )
    args = parser.parse_args()

    global RUN
    if args.project:
        manifest = load_project_manifest(Path(args.project))
        v_errs = validate_manifest(manifest)
        if v_errs:
            raise SystemExit("Manifest validation failed:\n" + "\n".join(f"  - {e}" for e in v_errs))
        apply_project_manifest(manifest)
    else:
        RUN = _build_run_defaults()

    outputs_dir = RUN.outputs_dir.resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(
        console_level=logging.INFO,
        log_file=outputs_dir / "dupla_debug.log",
    )
    logger.info("Dupla pipeline starting — project: %s", RUN.project_name)

    if args.validate_only:
        extra: list[str] = []
        if not RUN.dwg_path.exists():
            extra.append(f"DWG not found: {RUN.dwg_path}")
        if RUN.use_pdf and RUN.pdf_path and not RUN.pdf_path.exists():
            extra.append(f"PDF not found: {RUN.pdf_path}")
        if not RUN.use_pdf and RUN.images_dir and not RUN.images_dir.is_dir():
            extra.append(f"images_dir not found: {RUN.images_dir}")
        if RUN.bc3_path and not RUN.bc3_path.exists():
            extra.append(f"BC3 not found: {RUN.bc3_path}")
        if (
            RUN.xlsx_training_path
            and not str(RUN.xlsx_training_path).startswith("__no_pres")
            and not RUN.xlsx_training_path.exists()
        ):
            extra.append(f"PRES / training xlsx not found: {RUN.xlsx_training_path}")
        if extra:
            raise SystemExit("validate-only failed:\n" + "\n".join(f"  - {e}" for e in extra))
        logger.info("validate-only: rutas OK.")
        return

    dwg_path = RUN.dwg_path.resolve()
    if not dwg_path.exists():
        raise FileNotFoundError(f"DWG file not found: {dwg_path}")

    bucket_name = RUN.bucket_name or APS_BUCKET_NAME
    runner = PipelineRunner("dupla_full_analysis")

    # --- Stage 1: APS extraction ---
    s1 = runner.run_stage("aps_extraction", stage_aps_extraction, dwg_path, outputs_dir, bucket_name)
    if not s1.ok:
        _finish(runner, outputs_dir)
        return
    aps = s1.output
    runner.add_metrics("aps_extraction", {"cad_fact_keys": len(aps["cad_facts"])})

    # --- Stage 2: Resolve vision pages ---
    s2 = runner.run_stage("vision_pages", stage_resolve_pages, outputs_dir)
    if not s2.ok:
        _finish(runner, outputs_dir)
        return
    runner.add_metrics("vision_pages", {"page_count": s2.output["page_count"], "source": s2.output["source"]})

    # --- Stage 3: Knowledge inputs (BC3 + training + embeddings) ---
    #     Loaded BEFORE vision so the auto methodology context is available.
    s3 = runner.run_stage("knowledge_inputs", stage_knowledge_inputs, outputs_dir)
    if not s3.ok:
        _finish(runner, outputs_dir)
        return
    runner.add_metrics("knowledge_inputs", {
        "bc3_items": len(s3.output["bc3_catalog"].get("items", [])),
        "training_pairs": len(s3.output["training_pairs"]),
        "has_embeddings": s3.output["embedding_index"] is not None,
    })

    # --- Stage 4: Vision analysis (uses auto methodology from stage 3) ---
    vision_pages_input: Path | dict = s2.output if s2.output.get("multi") else s2.output["pages_dir"]
    s4 = runner.run_stage(
        "vision_analysis",
        stage_vision_analysis,
        vision_pages_input,
        aps["cad_facts"],
        outputs_dir,
        auto_methodology=s3.output.get("auto_methodology") or None,
    )
    if not s4.ok:
        _finish(runner, outputs_dir)
        return
    runner.add_metrics("vision_analysis", {
        "pages_ok": s4.output["pages_ok"],
        "pages_with_errors": s4.output["pages_with_errors"],
        "methodology_chars": s4.output.get("methodology_chars", 0),
    })

    # --- Stage 5: Build budget ---
    pages_resolution: Path | dict = s2.output if s2.output.get("multi") else s2.output["pages_dir"]
    s5 = runner.run_stage(
        "build_budget",
        stage_build_budget,
        aps["cad_facts"],
        s4.output["vision_results"],
        s3.output["bc3_catalog"],
        s3.output["embedding_index"],
        s3.output["training_pairs"],
        aps["raw_json_path"],
        aps["normalized_json_path"],
        aps["uploaded_object_name"],
        pages_resolution,
        s3.output["xlsx_training_path"],
        outputs_dir,
    )
    if not s5.ok:
        _finish(runner, outputs_dir)
        return
    budget = s5.output["budget"]
    runner.add_metrics("build_budget", {
        "hybrid_levels": len(budget.get("hybrid_inventory", [])),
        "base_takeoffs": len(budget.get("base_takeoffs", [])),
        "expanded_takeoffs": len(budget.get("takeoffs", [])),
        "budget_rows": len(budget.get("rows", [])),
        "budget_lines": len(budget.get("lines", [])),
        "chapters": len(budget.get("chapters", [])),
    })

    # --- Stage 6: Excel export ---
    s6 = runner.run_stage("excel_export", stage_excel_export, s5.output["context"], budget, outputs_dir)
    if not s6.ok:
        _finish(runner, outputs_dir)
        return

    # --- Stage 7: BC3 export (Presto) ---
    s7 = runner.run_stage("bc3_export", stage_bc3_export, s5.output["context"], budget, outputs_dir)
    if not s7.ok:
        logger.warning("BC3 export failed — continuing with Excel output only")

    # --- Final summary ---
    summary = {
        "dwg": str(dwg_path),
        "raw_autodesk_json": str(aps["raw_json_path"]),
        "normalized_json": str(aps["normalized_json_path"]),
        "vision_inventory_json": str(s4.output["vision_json_path"]),
        "budget_json": str(s5.output["budget_json_path"]),
        "budget_excel": str(s6.output["saved_workbook_path"]),
        "budget_review_excel": str(s6.output["review_workbook_path"]),
        "budget_bc3": str(s7.output["saved_bc3_path"]) if s7.ok else None,
        "pages_dir": (
            "|".join(str(b["pages_dir"]) for b in s2.output["bundles"])
            if s2.output.get("multi")
            else str(s2.output["pages_dir"])
        ),
        "vision_pages_count": len(s5.output["page_paths"]),
        "uploaded_object_name": aps["uploaded_object_name"],
        "hybrid_levels": len(budget.get("hybrid_inventory", [])),
        "base_takeoffs": len(budget.get("base_takeoffs", [])),
        "expanded_takeoffs": len(budget.get("takeoffs", [])),
        "budget_rows": len(budget.get("rows", [])),
        "budget_lines": len(budget.get("lines", [])),
        "chapters": len(budget.get("chapters", [])),
    }

    summary_path = outputs_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    _finish(runner, outputs_dir, summary)


def _finish(runner: PipelineRunner, outputs_dir: Path, summary: dict | None = None) -> None:
    report = runner.report(summary=summary or {})
    report_path = report.save(outputs_dir / "pipeline_report.json")

    logger.info("=" * 60)
    logger.info("Pipeline finished: %s", report.final_status.upper())
    logger.info("Total duration: %.1fs", report.total_duration_seconds)
    for stage in report.stages:
        status_icon = {
            "success": "OK", "warning": "WARN", "error": "FAIL", "skipped": "SKIP"
        }.get(stage["status"], "?")
        logger.info(
            "  [%4s] %-20s  %.2fs  %s",
            status_icon,
            stage["stage_name"],
            stage["duration_seconds"],
            ", ".join(stage["errors"][:1]) if stage["errors"] else "",
        )
    logger.info("Report saved: %s", report_path)
    logger.info("Debug log: %s", outputs_dir / "dupla_debug.log")
    logger.info("=" * 60)

    if report.final_status == "error":
        logger.error("Pipeline failed — check pipeline_report.json and dupla_debug.log for details")


if __name__ == "__main__":
    main()
