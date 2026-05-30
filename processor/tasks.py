import tempfile
import os
import json
import shutil
from pathlib import Path
from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import create_bucket, upload_file_to_bucket, APS_BUCKET_NAME
from aps_integration.model_derivative import extract_dwg_data
from agents.vision_agent import run_full_vision_analysis
from processors.json_processor import process_autodesk_json
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.methodology_generator import generate_methodology_context
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import merge_bc3_catalogs, parse_bc3
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from disciplines import get_engine

# --- Phase 1 port: full-engine modules (vision/exports wired in later phases) ---
from budget.export_bc3 import export_budget_bc3
from budget.export_excel import export_budget_workbook
from core.output_structure import RunOutputDir
from core.location_parser import parse_location_from_filename
from core.quality_engine import write_input_gaps_markdown, write_quality_report_json
from disciplines.domain_rules import load_domain_rules_for_discipline
from disciplines.domain_validator import (
    validate_vision_output,
    write_missing_attributes_report,
    write_unclassified_report,
)
from analysis.day1_prep import build_day1_artifacts
from analysis.day2_prep import build_day2_dataset_artifacts
from pricing.excel_price_loader import load_or_cache_constructor_pricing
from pricing.apu_matcher import APUMatcher

import logging

logger = logging.getLogger(__name__)

def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    import fitz
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    image_paths = []
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = output_dir / f"page_{page_index + 1:04d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)
    return image_paths

def _merge_cad_facts(base: dict, new: dict) -> None:
    """Merge CAD facts from multiple DWGs into a single unified dict.

    Ported verbatim from dupla_run_nasas.py: accumulates total_objects,
    extends cad_facts collections, merges layers by name and inventory_hints.
    """
    if not base:
        base.update(new)
        return
    base["total_objects"] = base.get("total_objects", 0) + new.get("total_objects", 0)
    if "cad_facts" in new:
        if "cad_facts" not in base:
            base["cad_facts"] = {}
        for key in ["texts", "dimensions", "hatches", "blocks", "geometry_hints"]:
            base["cad_facts"].setdefault(key, []).extend(new["cad_facts"].get(key, []))
        base_layers = base["cad_facts"].setdefault("layers", {})
        for layer, metrics in new["cad_facts"].get("layers", {}).items():
            if layer not in base_layers:
                base_layers[layer] = metrics
            else:
                base_layers[layer]["object_count"] += metrics.get("object_count", 0)
                for et, count in metrics.get("entity_types", {}).items():
                    base_layers[layer]["entity_types"][et] = base_layers[layer]["entity_types"].get(et, 0) + count
                base_layers[layer]["sample_names"] = list(set(base_layers[layer].get("sample_names", []) + metrics.get("sample_names", [])))[:5]
                base_layers[layer]["handles"] = list(set(base_layers[layer].get("handles", []) + metrics.get("handles", [])))[:5]
    if "inventory_hints" in new:
        if "inventory_hints" not in base:
            base["inventory_hints"] = {}
        for key in ["level_markers", "scale_dimensions"]:
            base["inventory_hints"].setdefault(key, []).extend(new["inventory_hints"].get(key, []))
        bf1 = {x["block_name"]: x["count"] for x in base["inventory_hints"].get("block_frequency", [])}
        for x in new["inventory_hints"].get("block_frequency", []):
            bf1[x["block_name"]] = bf1.get(x["block_name"], 0) + x["count"]
        base["inventory_hints"]["block_frequency"] = [{"block_name": k, "count": v} for k, v in sorted(bf1.items(), key=lambda i: i[1], reverse=True)][:25]
        base["inventory_hints"]["layer_names"] = sorted(list(set(base["inventory_hints"].get("layer_names", []) + new["inventory_hints"].get("layer_names", []))))


# Discipline inference: ordered (filename keyword tuple) -> canonical discipline id.
# Canonical ids match disciplines/<id>/ folders, domain_rules paths, and the
# vision agent's _UPLOAD_DISCIPLINE_PROMPT keys.
_DISCIPLINE_FILENAME_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("electric", "electr"), "electrico"),
    (("sanitar", "plomer", "hidrosanit", "agua potable", "aguas negras", "drenaje"), "sanitario"),
    (("estructur", "encofrado", "cimiento"), "estructura"),
    (("arquitect", "arq.", "arq-", "arq "), "arquitectura"),
]
_DEFAULT_DISCIPLINE = "arquitectura"


def _infer_discipline_from_filenames(filenames: list[str]) -> str:
    """Infer the canonical discipline id from uploaded file names.

    Names are checked in order (PDF first when the caller passes it first);
    the first file matching any keyword group wins. Falls back to
    'arquitectura' when nothing matches.
    """
    for name in filenames:
        low = (name or "").lower()
        for keywords, discipline in _DISCIPLINE_FILENAME_HINTS:
            if any(kw in low for kw in keywords):
                return discipline
    return _DEFAULT_DISCIPLINE


def run_dupla_pipeline(
    dwg_files: list[tuple[str, bytes]],
    pdf_content: bytes | None = None,
    pdf_filename: str | None = None,
    discipline_id: str | None = None,
    correlation_id: str = "unknown",
) -> dict:
    """Runs the core budget processing pipeline.

    Args:
        dwg_files: list of (filename, content) tuples. Each DWG is extracted
            via APS independently and merged into a single unified cad_facts.
        pdf_content / pdf_filename: optional PDF for vision analysis.
        discipline_id: canonical discipline (arquitectura | estructura |
            electrico | sanitario). When None, inferred from the file names.
        correlation_id: request correlation id, propagated for log tracing.
    """
    logger.info(f"Starting pipeline with correlation ID: {correlation_id}")
    if not dwg_files:
        raise RuntimeError("No DWG files provided")

    # Resolve the discipline: an explicit request value wins, otherwise infer
    # from the file names (PDF first, then DWGs).
    if discipline_id:
        discipline_id = discipline_id.strip().lower()
    else:
        candidate_names = ([pdf_filename] if pdf_filename else []) + [fn for fn, _ in dwg_files]
        discipline_id = _infer_discipline_from_filenames(candidate_names)
    logger.info("Discipline resolved: %s", discipline_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        outputs_dir = base_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        # 1. APS Extraction (multi-DWG -> merged cad_facts)
        bucket_name = os.getenv("APS_BUCKET_NAME", "dupla_processing_bucket")
        token = get_aps_token()
        create_bucket(token, bucket_name)

        cad_facts: dict = {}
        all_raw_data: list[dict] = []
        for idx, (filename, content) in enumerate(dwg_files):
            dwg_path = base_dir / (filename or f"upload_{idx}.dwg")
            dwg_path.write_bytes(content)
            logger.info("APS extraction (%d/%d): %s", idx + 1, len(dwg_files), dwg_path.name)

            object_name = upload_file_to_bucket(
                token, bucket_name, str(dwg_path), unique_suffix=f"api_job_{idx}"
            )
            if not object_name:
                raise RuntimeError(f"DWG upload to Autodesk failed: {dwg_path.name}")

            raw_data = extract_dwg_data(
                token, bucket_name, object_name,
                views=("2d",),
                translation_timeout_seconds=3600,
                poll_interval_seconds=10,
                max_property_wait_seconds=3600,
                failed_manifest_grace_polls=3,
                failed_manifest_grace_sleep_seconds=20,
            )
            all_raw_data.append({"dwg": dwg_path.name, "data": raw_data})

            temp_raw_json = outputs_dir / f"raw_{idx}.json"
            temp_raw_json.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
            partial_facts = process_autodesk_json(str(temp_raw_json))
            _merge_cad_facts(cad_facts, partial_facts)

        raw_json_path = outputs_dir / "raw.json"
        raw_json_path.write_text(json.dumps(all_raw_data, indent=2, ensure_ascii=False), encoding="utf-8")

        normalized = cad_facts
        normalized_json_path = outputs_dir / "normalized.json"
        normalized_json_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Merged cad_facts: %d layers", len(normalized.get("cad_facts", {}).get("layers", {})))

        # 2. Vision Pages
        pages_dir = base_dir / "rendered_pages"
        pages_dir.mkdir(exist_ok=True)
        if pdf_content:
            pdf_path = base_dir / (pdf_filename or "upload.pdf")
            pdf_path.write_bytes(pdf_content)
            page_paths = render_pdf_to_images(pdf_path, pages_dir)
        else:
            page_paths = []

        # 3. Knowledge
        bc3_path = Path("/app/data/GIV00001.bc3")
        bc3_catalog = parse_bc3(str(bc3_path)) if bc3_path.exists() else {}
        embedding_index = load_or_build_embeddings(bc3_catalog) if bc3_catalog.get("items") else None

        # Training pairs from the reference PRES.xlsx (few-shot context for BC3 matching).
        pres_path = Path("/app/data/PRES.xlsx")
        training_pairs: list = []
        if pres_path.exists():
            try:
                training_pairs = extract_training_pairs(str(pres_path))
                logger.info("Training pairs loaded: %d from %s", len(training_pairs), pres_path.name)
            except Exception as exc:
                logger.warning("Failed to load training pairs from %s: %s", pres_path, exc)
        else:
            logger.warning("PRES.xlsx not found at %s — training pairs empty", pres_path)

        # Auto methodology context for the vision prompt (office criteria from PRES + BC3).
        methodology = generate_methodology_context(
            training_pairs=training_pairs or None,
            bc3_catalog=bc3_catalog or None,
            discipline=discipline_id,
        ) or None
        if methodology:
            logger.info("Methodology context generated: %d chars", len(methodology))

        # 4. Vision Analysis
        vision_results = []
        if page_paths:
            vision_results = run_full_vision_analysis(
                str(pages_dir),
                normalized,
                office_methodology=methodology,
                upload_discipline_id=discipline_id,
            )

        # 4b. Domain validation against the resolved discipline's rules.
        domain_rules = load_domain_rules_for_discipline(discipline_id)
        domain_validation_summary: dict | None = None
        validation = None
        if domain_rules and vision_results:
            validation = validate_vision_output(vision_results, domain_rules, "Dupla API Job")
            domain_validation_summary = {
                "discipline_id": domain_rules.discipline_id,
                "classified": len(validation.classified),
                "belongs": len(validation.belongs),
                "not_belongs": len(validation.not_belongs),
                "unclassified": len(validation.unclassified),
                "missing_attributes": len(validation.missing_attributes),
            }
            logger.info(
                "Domain validation [%s]: %d belongs, %d not_belongs, %d unclassified, %d missing attrs",
                domain_rules.discipline_id,
                len(validation.belongs), len(validation.not_belongs),
                len(validation.unclassified), len(validation.missing_attributes),
            )
        elif not domain_rules:
            logger.warning(
                "No domain_rules.yaml for discipline '%s' — skipping domain validation",
                discipline_id,
            )

        # 5. Build Budget
        context = ProjectContext(
            project_id="api_job",
            project_name="Dupla API Job",
            source_json_path=str(raw_json_path),
            plan_image_paths=[str(p) for p in page_paths],
            bc3_path=str(bc3_path) if bc3_path.exists() else None,
            metadata={
                "discipline_id": discipline_id,
                "enable_semantic_layer": True,
            },
        )

        import asyncio
        budget = asyncio.run(build_budget_from_sources(
            context=context,
            cad_facts=normalized,
            vision_payloads=vision_results,
            bc3_catalog=bc3_catalog,
            embedding_index=embedding_index,
            training_pairs=training_pairs,
        ))

        if domain_validation_summary is not None:
            budget["domain_validation"] = domain_validation_summary

        # 6. Persist deliverables to a non-ephemeral run directory.
        # The output base is a shared volume (docker-compose: dupla_outputs)
        # so the processor API container can serve what the worker produced.
        output_base = os.getenv("DUPLA_OUTPUT_DIR", "/app/output")
        run_dir = RunOutputDir(output_base, "Dupla API Job")
        artifacts: dict[str, str] = {}

        budget_json_path = run_dir.discipline_budget_json(discipline_id)
        budget_json_path.write_text(
            json.dumps(budget, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        artifacts["budget_json"] = str(budget_json_path)

        vision_json_path = run_dir.discipline_vision_json(discipline_id)
        vision_json_path.write_text(
            json.dumps(vision_results, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        artifacts["vision_json"] = str(vision_json_path)

        # Final deliverables: Excel + BC3.
        excel_path = None
        try:
            excel_path = export_budget_workbook(
                context, budget["rows"], run_dir.discipline_excel(discipline_id),
                sheet_name=discipline_id.upper(),
                quality_report=budget.get("quality_report"),
            )
            artifacts["excel"] = str(excel_path)
            logger.info("Excel deliverable: %s", excel_path)
        except Exception as exc:
            logger.error("Excel export failed: %s", exc, exc_info=True)

        try:
            bc3_export_path = export_budget_bc3(
                context, budget["rows"], run_dir.discipline_bc3(discipline_id),
                bc3_catalog=bc3_catalog,
            )
            artifacts["bc3"] = str(bc3_export_path)
            logger.info("BC3 deliverable: %s", bc3_export_path)
        except Exception as exc:
            logger.error("BC3 export failed: %s", exc, exc_info=True)

        # Quality report + INPUT_GAPS markdown.
        quality_report = budget.get("quality_report")
        if quality_report:
            try:
                qpath = write_quality_report_json(
                    quality_report, run_dir.discipline_quality_json(discipline_id)
                )
                gpath = write_input_gaps_markdown(
                    quality_report, run_dir.discipline_input_gaps_md(discipline_id)
                )
                artifacts["quality_report"] = str(qpath)
                artifacts["input_gaps"] = str(gpath)
            except Exception as exc:
                logger.warning("Quality report write failed: %s", exc, exc_info=True)

        # Domain validation reports (persisted to disk).
        if validation is not None:
            unclass = write_unclassified_report(validation, run_dir.unclassified_elements)
            missing = write_missing_attributes_report(
                validation, run_dir.discipline_missing_attrs(discipline_id)
            )
            if unclass:
                artifacts["unclassified_report"] = str(unclass)
            if missing:
                artifacts["missing_attributes_report"] = str(missing)

        # Day 1 / Day 2 dataset artifacts (best-effort; non-critical).
        if pres_path.exists() and excel_path is not None:
            day1_dir = run_dir.discipline_dir(discipline_id) / "day1_prep"
            day1_dir.mkdir(parents=True, exist_ok=True)
            try:
                build_day1_artifacts(str(pres_path), day1_dir, generated_path=str(excel_path))
                artifacts["day1_prep"] = str(day1_dir)
            except Exception as exc:
                logger.warning("Day 1 prep failed, continuing: %s", exc, exc_info=True)
        if pres_path.exists():
            day2_dir = run_dir.discipline_dir(discipline_id) / "day2_prep"
            day2_dir.mkdir(parents=True, exist_ok=True)
            try:
                build_day2_dataset_artifacts(str(pres_path), day2_dir)
                artifacts["day2_prep"] = str(day2_dir)
            except Exception as exc:
                logger.warning("Day 2 dataset failed, continuing: %s", exc, exc_info=True)

        # Package all deliverables into a single downloadable archive.
        archive_path = shutil.make_archive(str(run_dir.root), "zip", root_dir=str(run_dir.root))

        budget["output"] = {
            "run_dir": str(run_dir.root),
            "discipline_id": discipline_id,
            "archive": archive_path,
            "artifacts": artifacts,
        }
        logger.info("Run artifacts persisted: %s (archive: %s)", run_dir.root, archive_path)

        return budget
