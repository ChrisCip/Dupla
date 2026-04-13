from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import JobCreateResponse, JobResultsResponse
from app.queue import get_task_queue
from app.services.job_store import JobStore
from app.services.pliego_fill_service import PliegoFillError, build_pliego_fill_payload

logger = logging.getLogger("dupla.api.projects")

router = APIRouter(prefix="/projects", tags=["projects"])

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    if not base.lower().endswith(".dwg"):
        raise HTTPException(status_code=400, detail="File must have .dwg extension")
    cleaned = _SAFE_NAME.sub("_", base)
    if not cleaned or cleaned == ".dwg":
        cleaned = "upload.dwg"
    return cleaned


@router.post("", status_code=202, response_model=JobCreateResponse)
async def create_project(dwg: UploadFile = File(..., description="Autodesk DWG file")) -> JobCreateResponse:
    settings = get_settings()
    if not dwg.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    safe_name = _sanitize_filename(dwg.filename)
    size_limit = settings.max_upload_mb * 1024 * 1024
    body = await dwg.read()
    if len(body) > size_limit:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max_upload_mb={settings.max_upload_mb}",
        )

    job_id = str(uuid.uuid4())
    store = JobStore(settings.job_data_dir)
    store.create_pending(job_id, dwg_filename=safe_name)

    inputs_dir = store.inputs_dir(job_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dest = inputs_dir / safe_name
    dest.write_bytes(body)

    queue = get_task_queue()
    queue.enqueue(
        "app.services.pipeline_job.process_dwg_job",
        job_id,
        job_timeout=max(7200, settings.translation_timeout_seconds + 600),
    )

    prefix = settings.api_prefix.rstrip("/")
    results_path = f"{prefix}/projects/{job_id}/results"
    return JobCreateResponse(job_id=job_id, status_url=results_path)


@router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_project_results(job_id: str) -> JobResultsResponse:
    settings = get_settings()
    store = JobStore(settings.job_data_dir)
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    cad_facts: dict | None = None
    if record.status == "succeeded" and record.outputs:
        norm_name = record.outputs.get("normalized_json")
        if norm_name:
            norm_path = store.outputs_dir(job_id) / norm_name
            if norm_path.is_file():
                try:
                    cad_facts = json.loads(norm_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    logger.warning("Invalid normalized JSON for job %s: %s", job_id, exc)

    return JobResultsResponse(
        job_id=record.job_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error=record.error,
        outputs=record.outputs,
        cad_facts=cad_facts,
        cad_fact_keys=record.cad_fact_keys,
        uploaded_object_name=record.uploaded_object_name,
    )


def _map_pliego_error(exc: PliegoFillError) -> HTTPException:
    if exc.code == "not_found":
        return HTTPException(status_code=404, detail=exc.message)
    if exc.code == "job_not_ready":
        return HTTPException(status_code=409, detail=exc.message)
    if exc.code in ("no_normalized_json", "normalized_missing", "invalid_normalized_json"):
        return HTTPException(status_code=500, detail=exc.message)
    return HTTPException(status_code=500, detail=exc.message)


@router.get("/{job_id}/pliego-fill")
def get_project_pliego_fill(job_id: str) -> dict[str, object]:
    """
    Sugerencias para rellenar la hoja RESUMEN de ``data/pliego.xlsx`` a partir del CAD normalizado del job.
    """
    settings = get_settings()
    try:
        return build_pliego_fill_payload(job_id, settings.job_data_dir)
    except PliegoFillError as exc:
        raise _map_pliego_error(exc) from exc
