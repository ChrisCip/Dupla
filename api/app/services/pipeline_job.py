from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import app.bootstrap_path  # noqa: F401

load_dotenv()

from aps_integration.aps_auth import get_aps_token
from aps_integration.model_derivative import extract_dwg_data
from aps_integration.oss_manager import APS_BUCKET_NAME, create_bucket, upload_file_to_bucket
from core.logging_config import setup_logging
from processors.json_processor import process_autodesk_json

from app.config import get_settings
from app.services.job_store import JobStore

logger = logging.getLogger("dupla.api.pipeline_job")


def process_dwg_job(job_id: str) -> None:
    """
    RQ worker entrypoint: APS extraction + ``process_autodesk_json`` for one job.

    Expected layout (created by HTTP handler):
    ``{job_data_dir}/jobs/{job_id}/inputs/<file>.dwg``
    """
    settings = get_settings()
    store = JobStore(settings.job_data_dir)
    record = store.get(job_id)
    if record is None:
        logger.error("Job not found: %s", job_id)
        return

    inputs_dir = store.inputs_dir(job_id)
    outputs_dir = store.outputs_dir(job_id)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    dwg_name = record.dwg_filename or "upload.dwg"
    dwg_path = inputs_dir / dwg_name
    if not dwg_path.is_file():
        store.update(job_id, status="failed", error=f"DWG not found at {dwg_path}")
        return

    log_path = outputs_dir / "dupla_debug.log"
    setup_logging(console_level=logging.INFO, log_file=log_path)
    store.update(job_id, status="running")

    try:
        result = run_aps_extraction_sync(dwg_path, outputs_dir, settings)
        rel_raw = result["raw_json_path"].name
        rel_norm = result["normalized_json_path"].name
        store.update(
            job_id,
            status="succeeded",
            outputs={
                "raw_json": rel_raw,
                "normalized_json": rel_norm,
                "log": log_path.name,
            },
            cad_fact_keys=len(result["cad_facts"]),
            uploaded_object_name=result["uploaded_object_name"],
        )
    except Exception as exc:
        logger.exception("APS pipeline failed for job %s", job_id)
        store.update(job_id, status="failed", error=str(exc))


def run_aps_extraction_sync(dwg_path: Path, outputs_dir: Path, settings) -> dict:
    """
    Upload DWG, extract Model Derivative JSON, normalize CAD facts (same as
    ``stage_aps_extraction`` in ``dupla_run_full_analysis_local.py``).
    """
    bucket_name = settings.aps_bucket_name or APS_BUCKET_NAME
    token = get_aps_token()
    create_bucket(token, bucket_name)

    unique_suffix = None
    if settings.auto_unique_object_name:
        unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.debug("Auto-unique upload suffix: %s", unique_suffix)

    object_name = upload_file_to_bucket(
        token,
        bucket_name,
        str(dwg_path),
        object_name=settings.upload_object_name,
        unique_suffix=unique_suffix,
    )
    if not object_name:
        raise RuntimeError("DWG upload to Autodesk failed.")
    logger.info("DWG uploaded as %r to bucket %r", object_name, bucket_name)

    raw_data = extract_dwg_data(
        token,
        bucket_name,
        object_name,
        views=tuple(settings.translation_views),
        translation_timeout_seconds=settings.translation_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
        max_property_wait_seconds=settings.max_property_wait_seconds,
        failed_manifest_grace_polls=settings.failed_manifest_grace_polls,
        failed_manifest_grace_sleep_seconds=settings.failed_manifest_grace_sleep_seconds,
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
