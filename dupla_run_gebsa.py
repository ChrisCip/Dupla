"""
Dupla multi-discipline runner for the GEBSA IV project.

Processes 4 disciplines sequentially (arquitectura, estructura, electrico,
sanitario), each generating an Excel + BC3 presupuesto parcial, plus
domain validation reports.

Usage:
    python dupla_run_gebsa.py
    python dupla_run_gebsa.py --only arquitectura
    python dupla_run_gebsa.py --resume
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ========= CONFIG =========
PROJECT_NAME = "Residencial GEBSA IV"
PROJECT_ID = "gebsa_iv"

DISCIPLINES: dict[str, dict[str, str]] = {
    "arquitectura": {
        "pdf": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\TERMINACIONES GEBSA PDF\prueba dupla full.pdf",
        "dwg": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\DISEÑOS GEBSA DWG\2- PLANTAS ARQUITECTONICAS.dwg",
    },
    "estructura": {
        "pdf": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\ESTRUCTURAL GEBSA PDF\full gebsa estructural.pdf",
        "dwg": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\DISEÑOS GEBSA DWG\ESTRUCTURA GEBSA IV.dwg",
    },
    "electrico": {
        "pdf": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\ELECTRICOS GEBSA PDF\electrico gebsa full.pdf",
        "dwg": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\DISEÑOS GEBSA DWG\GEBSA IV- EL01 definitivos1 FINAL.dwg",
    },
    "sanitario": {
        "pdf": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\SANITARIOS GEBSA PDF\sanitario full pdf gebsa.pdf",
        "dwg": r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\DISEÑOS GEBSA DWG\SANITARIAS FINAL ODELIN.dwg",
    },
}

DISCIPLINE_ORDER = ["arquitectura", "estructura", "sanitario", "electrico"]

BC3_PATH = r"data\GIV00001 (1).bc3"
XLSX_TRAINING_PATH = r"data\PRES.xlsx"
OFFICE_METHODOLOGY_PATH = r"knowledge\office_methodology.md"

OUTPUTS_DIR = r"C:\Users\chris\Downloads\dupla1"

TRANSLATION_VIEWS = ("2d",)
TRANSLATION_TIMEOUT_SECONDS = 3600
POLL_INTERVAL_SECONDS = 10
MAX_PROPERTY_WAIT_SECONDS = 3600
FAILED_MANIFEST_GRACE_POLLS = 3
FAILED_MANIFEST_GRACE_SLEEP_SECONDS = 20
AUTO_UNIQUE_OBJECT_NAME = True
BUCKET_NAME = None
# ========= END CONFIG =========

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

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
from analysis.day1_prep import build_day1_artifacts
from analysis.day2_prep import build_day2_dataset_artifacts
from processors.bc3_parser import merge_bc3_catalogs, parse_bc3
from processors.json_processor import process_autodesk_json

logger = logging.getLogger("dupla.gebsa")


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

def run_preflight(disciplines: dict[str, dict[str, str]], bc3_path: str) -> list[str]:
    """Return list of errors. Empty means all checks passed."""
    errors: list[str] = []

    for disc_id, files in disciplines.items():
        pdf = Path(files["pdf"])
        if not pdf.exists():
            errors.append(f"[{disc_id}] PDF not found: {pdf}")
        dwg_path = files.get("dwg")
        if dwg_path:
            dwg = Path(dwg_path)
            if not dwg.exists():
                errors.append(f"[{disc_id}] DWG not found: {dwg}")

    data_bc3_files = list((REPO_ROOT / "data").glob("*.bc3"))
    if not data_bc3_files:
        bc3_full = (REPO_ROOT / bc3_path).resolve()
        if not bc3_full.exists():
            errors.append(f"No BC3 files in data/*.bc3 and BC3_PATH not found: {bc3_full}")

    if not os.getenv("CLIENT_ID") or not os.getenv("CLIENT_SECRET"):
        errors.append("APS credentials missing: CLIENT_ID or CLIENT_SECRET not in .env")

    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OpenAI API key missing: OPENAI_API_KEY not in .env")

    try:
        import yaml  # noqa: F401
    except ImportError:
        errors.append("pyyaml not installed: pip install pyyaml")

    try:
        import fitz  # noqa: F401
    except ImportError:
        errors.append("PyMuPDF not installed: pip install pymupdf")

    for disc_id in disciplines:
        rules_path = REPO_ROOT / "disciplines" / disc_id / "domain_rules.yaml"
        if not rules_path.exists():
            errors.append(f"[{disc_id}] domain_rules.yaml not found: {rules_path}")
        prompt_path = REPO_ROOT / "knowledge" / "prompts" / disc_id / "user_prompt.md"
        if not prompt_path.exists():
            errors.append(f"[{disc_id}] user_prompt.md not found: {prompt_path}")

    return errors


# ---------------------------------------------------------------------------
# Run state persistence (for resume)
# ---------------------------------------------------------------------------

def _state_path(run_dir: RunOutputDir) -> Path:
    return run_dir.root / "run_state.json"


def load_run_state(run_dir: RunOutputDir) -> dict[str, dict[str, Any]]:
    sp = _state_path(run_dir)
    if sp.exists():
        return json.loads(sp.read_text(encoding="utf-8"))
    return {d: {"status": "pending"} for d in DISCIPLINE_ORDER}


def save_run_state(run_dir: RunOutputDir, state: dict) -> None:
    sp = _state_path(run_dir)
    sp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pdf_pages_cache_dir(outputs_dir: Path, pdf_path: Path) -> Path:
    key = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return outputs_dir / "rendered_pages" / f"p_{key}"


def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    import fitz
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


def _load_office_methodology() -> str:
    path = (REPO_ROOT / OFFICE_METHODOLOGY_PATH).resolve()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _is_likely_valid_code(code: str) -> bool:
    value = (code or "").strip()
    if not value or " " in value:
        return False
    return len(value) <= 32


def _is_likely_valid_unit(unit: str) -> bool:
    value = (unit or "").strip()
    if not value:
        return False
    if len(value) > 16:
        return False
    if value.count(" ") > 1:
        return False
    return True


def _source_quality_score(pairs: list[Any]) -> float:
    if not pairs:
        return 0.0
    valid = 0
    for pair in pairs:
        if (
            _is_likely_valid_code(getattr(pair, "output_bc3_code", ""))
            and _is_likely_valid_unit(getattr(pair, "output_unit", ""))
            and bool(str(getattr(pair, "output_description", "")).strip())
        ):
            valid += 1
    return valid / len(pairs)


def _load_training_pairs_from_sources(
    pres_sources: list[str],
    *,
    min_source_quality: float,
) -> tuple[list[Any], dict[str, int], dict[str, float], dict[str, str]]:
    training_pairs: list[Any] = []
    source_pair_counts: dict[str, int] = {}
    source_quality_scores: dict[str, float] = {}
    excluded_sources: dict[str, str] = {}

    for source in pres_sources:
        source_path = Path(source).resolve()
        if not source_path.exists():
            logger.warning("Training source not found, skipping: %s", source_path)
            continue

        extracted = extract_training_pairs(source_path)
        quality = _source_quality_score(extracted)
        source_quality_scores[str(source_path)] = round(quality, 4)
        if extracted and quality < min_source_quality:
            excluded_sources[str(source_path)] = (
                f"quality {quality:.2f} below threshold {min_source_quality:.2f}"
            )
            continue

        for pair in extracted:
            pair.source = source_path.name
        source_pair_counts[str(source_path)] = len(extracted)
        training_pairs.extend(extracted)

    return training_pairs, source_pair_counts, source_quality_scores, excluded_sources


# ---------------------------------------------------------------------------
# Per-discipline processing
# ---------------------------------------------------------------------------

def process_discipline(
    disc_id: str,
    files: dict[str, str],
    run_dir: RunOutputDir,
    shared: dict[str, Any],
    *,
    day1_prep_enabled: bool = False,
    day1_pres_path: str | None = None,
    day1_holdout_limit: int = 40,
    day2_prep_enabled: bool = False,
    day2_pres_paths: list[str] | None = None,
    day2_validation_limit: int = 40,
    day2_min_source_quality: float = 0.75,
) -> dict[str, Any]:
    """Process a single discipline end-to-end. Returns summary dict."""
    t0 = time.time()
    disc_dir = run_dir.discipline_dir(disc_id)
    bucket_name = BUCKET_NAME or APS_BUCKET_NAME

    engine = get_engine(disc_id)
    rules = load_domain_rules_for_discipline(disc_id)
    logger.info("=" * 60)
    logger.info("DISCIPLINE: %s", disc_id.upper())
    logger.info("=" * 60)

    # --- APS extraction (optional) ---
    cad_facts: dict = {}
    uploaded_object_name = ""
    raw_json_path = disc_dir / "autodesk_raw.json"
    normalized_json_path = disc_dir / "cad_facts.json"

    dwg_path_str = files.get("dwg")
    if dwg_path_str and Path(dwg_path_str).exists():
        try:
            logger.info("[%s] APS extraction: %s", disc_id, Path(dwg_path_str).name)
            token = get_aps_token()
            create_bucket(token, bucket_name)

            unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            uploaded_object_name = upload_file_to_bucket(
                token, bucket_name, dwg_path_str,
                unique_suffix=unique_suffix,
            ) or ""

            if uploaded_object_name:
                logger.info("[%s] DWG uploaded as '%s'", disc_id, uploaded_object_name)
                raw_data = extract_dwg_data(
                    token, bucket_name, uploaded_object_name,
                    views=TRANSLATION_VIEWS,
                    translation_timeout_seconds=TRANSLATION_TIMEOUT_SECONDS,
                    poll_interval_seconds=POLL_INTERVAL_SECONDS,
                    max_property_wait_seconds=MAX_PROPERTY_WAIT_SECONDS,
                    failed_manifest_grace_polls=FAILED_MANIFEST_GRACE_POLLS,
                    failed_manifest_grace_sleep_seconds=FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
                )
                raw_json_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                cad_facts = process_autodesk_json(str(raw_json_path))
                normalized_json_path.write_text(
                    json.dumps(cad_facts, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info("[%s] CAD facts: %d keys", disc_id, len(cad_facts))
        except Exception as exc:
            logger.warning("[%s] APS extraction failed, continuing with PDF only: %s", disc_id, exc)
            cad_facts = {}
    else:
        logger.info("[%s] No DWG provided, using PDF only", disc_id)

    # --- PDF rendering ---
    pdf_path = Path(files["pdf"])
    pages_dir = _pdf_pages_cache_dir(disc_dir, pdf_path)
    image_paths = render_pdf_to_images(pdf_path, pages_dir)
    logger.info("[%s] Rendered %d PDF pages", disc_id, len(image_paths))

    # --- Vision analysis ---
    manual_meth = _load_office_methodology()
    auto_meth = shared.get("auto_methodology") or ""
    parts = [p for p in [auto_meth, manual_meth] if p.strip()]
    methodology = "\n\n---\n\n".join(parts) if parts else None

    logger.info("[%s] Running Vision AI on %d pages...", disc_id, len(image_paths))
    vision_results = run_full_vision_analysis(
        str(pages_dir),
        cad_facts,
        office_methodology=methodology,
        upload_discipline_id=disc_id,
    )

    vision_json = run_dir.discipline_vision_json(disc_id)
    vision_json.write_text(json.dumps(vision_results, indent=2, ensure_ascii=False), encoding="utf-8")

    vision_ok = sum(1 for r in vision_results if isinstance(r, dict) and "error" not in r)
    vision_err = len(vision_results) - vision_ok
    logger.info("[%s] Vision: %d pages OK, %d errors", disc_id, vision_ok, vision_err)

    # --- Domain validation (R1.b + R3) ---
    if rules:
        validation = validate_vision_output(vision_results, rules, PROJECT_NAME)
        unclass_path = write_unclassified_report(validation, run_dir.unclassified_elements)
        missing_path = write_missing_attributes_report(
            validation, run_dir.discipline_missing_attrs(disc_id)
        )
        if unclass_path:
            logger.warning(
                "[%s] %d unclassified element types. See: %s",
                disc_id, len(validation.unclassified), unclass_path,
            )
        if missing_path:
            logger.info(
                "[%s] %d missing attributes. See: %s",
                disc_id, len(validation.missing_attributes), missing_path,
            )

    # --- Budget pipeline ---
    allowed_types = sorted(rules.budget_item_types) if rules else None
    page_paths_str = sorted(
        str(p) for p in pages_dir.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )

    context = ProjectContext(
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
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

    apu_matcher = shared.get("apu_matcher")
    pricing_store = shared.get("pricing_store")
    if apu_matcher is not None:
        logger.info(
            "[%s] Building budget with constructor APU matcher (apus=%d)",
            disc_id, len(pricing_store.apus) if pricing_store is not None else -1,
        )
    else:
        logger.info("[%s] Building budget (BC3 catalog only, no --pricing-excel)", disc_id)
    budget = build_budget_from_sources(
        context, cad_facts, vision_results,
        shared["bc3_catalog"],
        embedding_index=shared.get("embedding_index"),
        training_pairs=shared.get("training_pairs"),
        pricing_store=pricing_store,
        apu_matcher=apu_matcher,
    )

    budget_lines = len(budget.get("lines", []))
    budget_chapters = len(budget.get("chapters", []))
    logger.info("[%s] Budget: %d chapters, %d lines", disc_id, budget_chapters, budget_lines)

    # --- Export Excel + BC3 ---
    excel_path = export_budget_workbook(
        context, budget["rows"],
        run_dir.discipline_excel(disc_id),
        sheet_name=disc_id.upper(),
        quality_report=budget.get("quality_report"),
    )
    logger.info("[%s] Excel: %s", disc_id, excel_path)

    bc3_path = export_budget_bc3(
        context, budget["rows"], run_dir.discipline_bc3(disc_id),
        bc3_catalog=shared["bc3_catalog"],
    )
    logger.info("[%s] BC3: %s", disc_id, bc3_path)

    day1_prep: dict[str, Any] | None = None
    if day1_prep_enabled and day1_pres_path:
        try:
            day1_prep = build_day1_artifacts(
                day1_pres_path,
                run_dir.day1_prep_dir(disc_id),
                generated_path=excel_path,
                holdout_limit=day1_holdout_limit,
            )
            logger.info("[%s] Day 1 prep written: %s", disc_id, day1_prep.get("report_path", ""))
        except Exception as exc:
            logger.warning("[%s] Day 1 prep failed, continuing: %s", disc_id, exc, exc_info=True)

    day2_prep: dict[str, Any] | None = None
    if day2_prep_enabled and day2_pres_paths:
        try:
            day2_prep = build_day2_dataset_artifacts(
                day2_pres_paths,
                run_dir.day2_prep_dir(disc_id),
                validation_limit=day2_validation_limit,
                min_source_quality=day2_min_source_quality,
            )
            logger.info("[%s] Day 2 dataset written: %s", disc_id, day2_prep.get("report_path", ""))
        except Exception as exc:
            logger.warning("[%s] Day 2 dataset failed, continuing: %s", disc_id, exc, exc_info=True)

    # --- Save budget JSON ---
    budget_json_path = run_dir.discipline_budget_json(disc_id)
    budget_json_path.write_text(
        json.dumps(budget, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # --- Quality report artifacts ---
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
        "bc3": str(bc3_path),
        "day1_prep": day1_prep,
        "day2_prep": day2_prep,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dupla GEBSA multi-discipline runner")
    parser.add_argument("--only", type=str, help="Run only this discipline")
    parser.add_argument("--resume", action="store_true", help="Resume from run_state.json")
    parser.add_argument("--skip-aps", action="store_true", help="Skip APS extraction, PDF only")
    parser.add_argument("--day1-prep", action="store_true", help="Write Day 1 prep artifacts per discipline")
    parser.add_argument(
        "--day1-pres",
        default=str(REPO_ROOT / "data" / "PRES.xlsx"),
        help="PRES.xlsx source used for Day 1 prep artifacts",
    )
    parser.add_argument(
        "--day1-holdout-limit",
        type=int,
        default=40,
        help="Maximum Day 1 holdout examples sampled from PRES",
    )
    parser.add_argument("--day2-prep", action="store_true", help="Write Day 2 dataset artifacts per discipline")
    parser.add_argument(
        "--day2-pres",
        action="append",
        default=None,
        help="PRES.xlsx source used for Day 2 dataset artifacts (repeat to add multiple)",
    )
    parser.add_argument(
        "--day2-validation-limit",
        type=int,
        default=40,
        help="Maximum Day 2 validation examples sampled from PRES",
    )
    parser.add_argument(
        "--day2-min-source-quality",
        type=float,
        default=0.75,
        help="Minimum source quality score required for each Day 2 PRES source",
    )
    parser.add_argument(
        "--training-pres",
        action="append",
        default=None,
        help="PRES source workbook for pipeline few-shot/context training (repeat to add multiple)",
    )
    parser.add_argument(
        "--training-min-source-quality",
        type=float,
        default=0.75,
        help="Minimum source quality score required for each pipeline training source",
    )
    parser.add_argument(
        "--pricing-excel",
        type=str,
        default=None,
        help="Path to the constructor pricing Excel (materials + labor + APUs). "
             "When given, build_budget uses APU prices and components over BC3 catalog fallback.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Dupla pipeline starting - project: %s", PROJECT_NAME)

    # --- Determine which disciplines to run ---
    if args.only:
        if args.only not in DISCIPLINES:
            logger.error("Unknown discipline: %s. Available: %s", args.only, list(DISCIPLINES.keys()))
            sys.exit(1)
        active = [args.only]
    else:
        active = list(DISCIPLINE_ORDER)

    # --- Preflight ---
    active_disciplines = {d: DISCIPLINES[d] for d in active}
    if args.skip_aps:
        for d in active_disciplines.values():
            d.pop("dwg", None)

    errors = run_preflight(active_disciplines, BC3_PATH)
    if errors:
        logger.error("Preflight checks FAILED:")
        for e in errors:
            logger.error("  %s", e)
        sys.exit(1)
    logger.info("Preflight checks passed (%d disciplines)", len(active))

    # --- Output directory ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RunOutputDir(OUTPUTS_DIR, PROJECT_NAME, timestamp=ts)
    logger.info("Output directory: %s", run_dir.root)

    log_file = run_dir.debug_log
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(fh)
    logger.info("Debug log: %s", log_file)

    # --- Load shared resources (once) ---
    logger.info("Loading shared resources...")
    bc3_files = sorted((REPO_ROOT / "data").glob("*.bc3"))
    if not bc3_files:
        logger.error("No .bc3 files found in %s", REPO_ROOT / "data")
        sys.exit(1)
    catalogs = [parse_bc3(str(p)) for p in bc3_files]
    for p, cat in zip(bc3_files, catalogs, strict=True):
        logger.info("BC3 loaded: %s (%d items)", p.name, len(cat.get("items", [])))
    bc3_catalog = merge_bc3_catalogs(*catalogs) if len(catalogs) > 1 else catalogs[0]
    logger.info(
        "BC3 combined catalog: %d items from %d file(s)",
        len(bc3_catalog.get("items", [])),
        len(catalogs),
    )
    bc3_full = (REPO_ROOT / BC3_PATH).resolve()
    if not bc3_full.exists():
        logger.warning("Configured BC3_PATH does not exist: %s (merge still uses data/*.bc3)", bc3_full)

    embedding_index = None
    if bc3_catalog.get("items"):
        logger.info("Building embeddings (may take a minute on first run)...")
        embedding_index = load_or_build_embeddings(bc3_catalog)
        logger.info("Embeddings ready: %d vectors", len(embedding_index.metadata))

    training_pres_sources = args.training_pres or [str((REPO_ROOT / XLSX_TRAINING_PATH).resolve())]
    training_pairs, source_pair_counts, source_quality_scores, excluded_sources = _load_training_pairs_from_sources(
        training_pres_sources,
        min_source_quality=args.training_min_source_quality,
    )
    if training_pairs:
        logger.info("Training pairs loaded: %d", len(training_pairs))
    else:
        logger.warning("No training pairs loaded from configured sources")
    for source, count in source_pair_counts.items():
        logger.info("Training source included: %s (%d pairs)", source, count)
    for source, score in source_quality_scores.items():
        logger.info("Training source quality: %s (%.2f)", source, score)
    for source, reason in excluded_sources.items():
        logger.warning("Training source excluded: %s (%s)", source, reason)

    xlsx_path_resolved = Path(training_pres_sources[0]).resolve() if training_pres_sources else None

    auto_methodology = generate_methodology_context(
        training_pairs=training_pairs or None,
        bc3_catalog=bc3_catalog or None,
    )

    pricing_store = None
    apu_matcher = None
    if args.pricing_excel:
        pricing_excel_path = Path(args.pricing_excel).resolve()
        if not pricing_excel_path.exists():
            logger.error("Pricing Excel not found: %s", pricing_excel_path)
            sys.exit(1)
        from pricing.excel_price_loader import load_or_cache_constructor_pricing
        from pricing.apu_matcher import APUMatcher

        pricing_store = load_or_cache_constructor_pricing(
            pricing_excel_path,
            project_id=PROJECT_ID,
        )
        logger.info(
            "Constructor PricingStore loaded from %s (materials=%d, labor=%d, apus=%d)",
            pricing_excel_path,
            len(pricing_store.materials),
            len(pricing_store.labor),
            len(pricing_store.apus),
        )
        apu_matcher = APUMatcher(pricing_store)
        logger.info("APUMatcher initialised (shared across all disciplines this run)")

    shared = {
        "bc3_catalog": bc3_catalog,
        "bc3_path_value": str(bc3_catalog.get("path") or bc3_full),
        "embedding_index": embedding_index,
        "training_pairs": training_pairs,
        "xlsx_path": str(xlsx_path_resolved) if xlsx_path_resolved and xlsx_path_resolved.exists() else None,
        "training_sources": training_pres_sources,
        "training_source_pair_counts": source_pair_counts,
        "training_source_quality_scores": source_quality_scores,
        "training_excluded_sources": excluded_sources,
        "auto_methodology": auto_methodology,
        "pricing_store": pricing_store,
        "apu_matcher": apu_matcher,
    }
    logger.info("Shared resources loaded")

    # --- Load/create run state ---
    state = load_run_state(run_dir) if args.resume else {
        d: {"status": "pending"} for d in DISCIPLINE_ORDER
    }

    # --- Process disciplines ---
    t_total = time.time()
    for disc_id in active:
        if state.get(disc_id, {}).get("status") == "success":
            logger.info("Skipping %s (already completed)", disc_id)
            continue

        state[disc_id] = {"status": "running", "started_at": datetime.now().isoformat()}
        save_run_state(run_dir, state)

        try:
            result = process_discipline(
                disc_id,
                DISCIPLINES[disc_id],
                run_dir,
                shared,
                day1_prep_enabled=args.day1_prep,
                day1_pres_path=args.day1_pres,
                day1_holdout_limit=args.day1_holdout_limit,
                day2_prep_enabled=args.day2_prep,
                day2_pres_paths=(args.day2_pres or [str(REPO_ROOT / "data" / "PRES.xlsx")]),
                day2_validation_limit=args.day2_validation_limit,
                day2_min_source_quality=args.day2_min_source_quality,
            )
            state[disc_id] = result
        except Exception as exc:
            logger.error("DISCIPLINE %s FAILED: %s", disc_id.upper(), exc, exc_info=True)
            state[disc_id] = {
                "status": "error",
                "error": str(exc),
                "duration_s": round(time.time() - time.time(), 1),
            }

        save_run_state(run_dir, state)

    total_elapsed = time.time() - t_total

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE - %s", PROJECT_NAME)
    logger.info("Total duration: %.1fs", total_elapsed)
    logger.info("=" * 60)

    for disc_id in active:
        s = state.get(disc_id, {})
        status = s.get("status", "unknown")
        duration = s.get("duration_s", 0)
        lines = s.get("budget_lines", 0)
        if status == "success":
            logger.info("  [OK]   %-15s %6.1fs  %d lines  %s", disc_id, duration, lines, s.get("excel", ""))
        elif status == "error":
            logger.info("  [FAIL] %-15s  %s", disc_id, s.get("error", "")[:80])
        else:
            logger.info("  [%-4s] %-15s", status.upper(), disc_id)

    logger.info("Output: %s", run_dir.root)

    summary = {
        "project": PROJECT_NAME,
        "timestamp": ts,
        "total_duration_s": round(total_elapsed, 1),
        "disciplines": state,
        "output_dir": str(run_dir.root),
    }
    run_dir.run_summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
