"""
Multi-discipline project pipeline (reference: GEBSA IV).
Migrated from dupla_run_gebsa.process_discipline / shared loading.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz

from aps_integration.aps_auth import get_aps_token
from aps_integration.model_derivative import extract_dwg_data
from aps_integration.oss_manager import APS_BUCKET_NAME, create_bucket, upload_file_to_bucket
from agents.vision_agent import run_full_vision_analysis
from budget.export_bc3 import export_budget_bc3
from budget.export_excel import export_budget_workbook
from core.output_structure import RunOutputDir
from core.pipeline import build_budget_from_sources
from core.quality_engine import write_input_gaps_markdown, write_quality_report_json
from core.schemas import ProjectContext
from disciplines import get_engine
from disciplines.domain_rules import load_domain_rules_for_discipline
from disciplines.domain_validator import (
    validate_vision_output,
    write_missing_attributes_report,
    write_unclassified_report,
)
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.methodology_generator import generate_methodology_context
from knowledge.training_data import extract_training_pairs
from pipeline.defaults import DEFAULT_PROJECT_ID, DEFAULT_PROJECT_NAME
from processors.bc3_parser import merge_bc3_catalogs, parse_bc3
from processors.json_processor import process_autodesk_json

logger = logging.getLogger("dupla.pipeline.project")


@dataclass(frozen=True)
class ApsOptions:
    translation_views: tuple[str, ...] = ("2d",)
    translation_timeout_seconds: int = 3600
    poll_interval_seconds: int = 10
    max_property_wait_seconds: int = 3600
    failed_manifest_grace_polls: int = 3
    failed_manifest_grace_sleep_seconds: int = 20
    auto_unique_object_name: bool = True
    upload_object_name: str | None = None
    bucket_name: str | None = None


def lib_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir_default() -> Path:
    return lib_root().parent / "data"


def resolve_office_methodology(path: Path | None = None) -> str:
    p = path or (lib_root() / "knowledge" / "office_methodology.md")
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def pdf_pages_cache_dir(outputs_dir: Path, pdf_path: Path) -> Path:
    key = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return outputs_dir / "rendered_pages" / f"p_{key}"


def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    paths: list[Path] = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = output_dir / f"page_{i + 1:04d}.png"
        pix.save(str(img))
        paths.append(img)
    return paths


def load_shared_resources(
    api_data: Path,
    *,
    pres_relative: str = "PRES.xlsx",
) -> dict[str, Any]:
    """Load BC3 catalog, embeddings, training, auto_methodology — same semantics as GEBSA main()."""
    bc3_files = sorted(api_data.glob("*.bc3"))
    if not bc3_files:
        raise FileNotFoundError(f"No .bc3 files in {api_data}")
    catalogs = [parse_bc3(str(p)) for p in bc3_files]
    for p, cat in zip(bc3_files, catalogs, strict=True):
        logger.info("BC3 loaded: %s (%d items)", p.name, len(cat.get("items", [])))
    bc3_catalog = merge_bc3_catalogs(*catalogs) if len(catalogs) > 1 else catalogs[0]

    embedding_index = None
    if bc3_catalog.get("items"):
        logger.info("Building embeddings (may take a minute on first run)...")
        embedding_index = load_or_build_embeddings(bc3_catalog)
        logger.info("Embeddings ready: %d vectors", len(embedding_index.metadata))

    training_pairs: list = []
    xlsx = (api_data / pres_relative).resolve()
    if xlsx.is_file():
        training_pairs = extract_training_pairs(xlsx)
        logger.info("Training pairs: %d from %s", len(training_pairs), xlsx.name)
    else:
        logger.info("PRES not found at %s — no training pairs", xlsx)

    auto_methodology = generate_methodology_context(
        training_pairs=training_pairs or None,
        bc3_catalog=bc3_catalog or None,
    )
    bc3_path_value = str(bc3_catalog.get("path") or bc3_files[0].resolve())

    return {
        "bc3_catalog": bc3_catalog,
        "bc3_path_value": bc3_path_value,
        "embedding_index": embedding_index,
        "training_pairs": training_pairs,
        "xlsx_path": str(xlsx) if xlsx.is_file() else None,
        "auto_methodology": auto_methodology,
    }


def process_discipline(
    disc_id: str,
    files: dict[str, str],
    run_dir: RunOutputDir,
    shared: dict[str, Any],
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    project_name: str = DEFAULT_PROJECT_NAME,
    aps: ApsOptions | None = None,
    vision_max_workers: int | None = None,
    pages_dir_override: Path | None = None,
) -> dict[str, Any]:
    """
    files: { "dwg": path str optional, "pdf": path str required for rendering }
    """
    t0 = time.time()
    aps = aps or ApsOptions()
    disc_dir = run_dir.discipline_dir(disc_id)
    bucket_name = aps.bucket_name or APS_BUCKET_NAME

    get_engine(disc_id)
    rules = load_domain_rules_for_discipline(disc_id)
    logger.info("=" * 60)
    logger.info("DISCIPLINE: %s", disc_id.upper())
    logger.info("=" * 60)

    raw_json_path = disc_dir / "autodesk_raw.json"
    normalized_json_path = disc_dir / "cad_facts.json"
    cad_facts: dict = {}
    dwg_path_str = files.get("dwg")
    if dwg_path_str and Path(dwg_path_str).is_file():
        try:
            logger.info("[%s] APS extraction: %s", disc_id, Path(dwg_path_str).name)
            token = get_aps_token()
            create_bucket(token, bucket_name)
            unique_suffix: str | None = None
            if aps.auto_unique_object_name:
                unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            uploaded = upload_file_to_bucket(
                token, bucket_name, dwg_path_str, object_name=aps.upload_object_name, unique_suffix=unique_suffix
            ) or ""
            if uploaded:
                logger.info("[%s] DWG uploaded as '%s'", disc_id, uploaded)
                raw_data = extract_dwg_data(
                    token,
                    bucket_name,
                    uploaded,
                    views=aps.translation_views,
                    translation_timeout_seconds=aps.translation_timeout_seconds,
                    poll_interval_seconds=aps.poll_interval_seconds,
                    max_property_wait_seconds=aps.max_property_wait_seconds,
                    failed_manifest_grace_polls=aps.failed_manifest_grace_polls,
                    failed_manifest_grace_sleep_seconds=aps.failed_manifest_grace_sleep_seconds,
                )
                raw_json_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                cad_facts = process_autodesk_json(str(raw_json_path))
                normalized_json_path.write_text(
                    json.dumps(cad_facts, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info("[%s] CAD facts: %d keys", disc_id, len(cad_facts))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] APS extraction failed, continuing with PDF only: %s", disc_id, exc)
            cad_facts = {}
    else:
        logger.info("[%s] No DWG provided, using PDF only", disc_id)

    pdf_path = Path(files["pdf"])
    if pages_dir_override is not None and pages_dir_override.is_dir():
        pages_dir = pages_dir_override.resolve()
        image_paths = sorted(
            p
            for p in pages_dir.iterdir()
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        logger.info("[%s] Using pre-rendered pages: %d images", disc_id, len(image_paths))
    else:
        pages_dir = pdf_pages_cache_dir(disc_dir, pdf_path)
        image_paths = render_pdf_to_images(pdf_path, pages_dir)
        logger.info("[%s] Rendered %d PDF pages", disc_id, len(image_paths))

    manual_meth = resolve_office_methodology()
    auto_meth = shared.get("auto_methodology") or ""
    parts = [p for p in [auto_meth, manual_meth] if p and str(p).strip()]
    methodology = "\n\n---\n\n".join(parts) if parts else None

    logger.info("[%s] Running Vision AI on %d pages...", disc_id, len(image_paths))
    vision_results = run_full_vision_analysis(
        str(pages_dir),
        cad_facts,
        office_methodology=methodology,
        upload_discipline_id=disc_id,
        max_workers=vision_max_workers,
    )
    run_dir.discipline_vision_json(disc_id).write_text(
        json.dumps(vision_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    vision_ok = sum(1 for r in vision_results if isinstance(r, dict) and "error" not in r)
    vision_err = len(vision_results) - vision_ok
    logger.info("[%s] Vision: %d pages OK, %d errors", disc_id, vision_ok, vision_err)

    if rules:
        validation = validate_vision_output(vision_results, rules, project_name)
        unclass_path = write_unclassified_report(validation, run_dir.unclassified_elements)
        missing_path = write_missing_attributes_report(validation, run_dir.discipline_missing_attrs(disc_id))
        if unclass_path:
            logger.warning(
                "[%s] %d unclassified element types. See: %s", disc_id, len(validation.unclassified), unclass_path
            )
        if missing_path:
            logger.info(
                "[%s] %d missing attributes. See: %s", disc_id, len(validation.missing_attributes), missing_path
            )

    allowed_types = sorted(rules.budget_item_types) if rules else None
    page_paths_str = sorted(
        str(p)
        for p in pages_dir.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    context = ProjectContext(
        project_id=project_id,
        project_name=project_name,
        source_json_path=str(raw_json_path) if raw_json_path.exists() else None,
        plan_image_paths=page_paths_str,
        bc3_path=shared.get("bc3_path_value"),
        metadata={
            "discipline_id": disc_id,
            "allowed_item_types": allowed_types,
            "xlsx_path": shared.get("xlsx_path"),
            "pres_template_takeoffs": False,
            "enable_semantic_layer": True,
        },
    )
    logger.info("[%s] Building budget...", disc_id)
    budget = build_budget_from_sources(
        context,
        cad_facts,
        vision_results,
        shared["bc3_catalog"],
        embedding_index=shared.get("embedding_index"),
        training_pairs=shared.get("training_pairs"),
    )
    budget_lines = len(budget.get("lines", []))
    budget_chapters = len(budget.get("chapters", []))
    logger.info("[%s] Budget: %d chapters, %d lines", disc_id, budget_chapters, budget_lines)

    excel_path = export_budget_workbook(
        context,
        budget["rows"],
        run_dir.discipline_excel(disc_id),
        sheet_name=disc_id.upper(),
        quality_report=budget.get("quality_report"),
    )
    logger.info("[%s] Excel: %s", disc_id, excel_path)
    out_bc3 = export_budget_bc3(
        context, budget["rows"], run_dir.discipline_bc3(disc_id), bc3_catalog=shared["bc3_catalog"]
    )
    logger.info("[%s] BC3: %s", disc_id, out_bc3)
    run_dir.discipline_budget_json(disc_id).write_text(
        json.dumps(budget, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    if budget.get("quality_report"):
        write_quality_report_json(budget["quality_report"], run_dir.discipline_quality_json(disc_id))
        write_input_gaps_markdown(budget["quality_report"], run_dir.discipline_input_gaps_md(disc_id))
        logger.info("[%s] Quality report + INPUT_GAPS written", disc_id)

    elapsed = time.time() - t0
    logger.info("[%s] Completed in %.1fs", disc_id, elapsed)
    return {
        "status": "success",
        "duration_s": round(elapsed, 1),
        "vision_pages": len(image_paths),
        "vision_errors": vision_err,
        "budget_lines": budget_lines,
        "budget_chapters": budget_chapters,
        "excel": str(excel_path),
        "bc3": str(out_bc3),
    }
