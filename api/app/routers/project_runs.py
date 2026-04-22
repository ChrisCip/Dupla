from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

import app.bootstrap_path  # noqa: F401
from app.config import get_settings
from app.models.schemas import (
    ProjectRunCreate,
    ProjectRunCreateResponse,
    ProjectRunGetResponse,
    _GEBSA_DISCIPLINES,
)
from app.queue import get_task_queue
from app.services.project_run_store import DisciplineEntry, ProjectRunStore

router = APIRouter(prefix="/project-runs", tags=["project-runs"])
logger = logging.getLogger("dupla.api.project_runs")


@router.post("", status_code=202, response_model=ProjectRunCreateResponse)
def create_project_run(body: ProjectRunCreate) -> ProjectRunCreateResponse:
    settings = get_settings()
    store = ProjectRunStore(settings.job_data_dir)
    ids = {d.id for d in body.disciplines}
    if body.discipline_order:
        order = [x for x in body.discipline_order if x in ids]
    else:
        order = [x for x in _GEBSA_DISCIPLINES if x in ids]
    entries = [DisciplineEntry(id=d.id, dwg_url=d.dwg_url, pdf_url=d.pdf_url) for d in body.disciplines]
    rec = store.create_pending(
        project_id=body.project_id,
        project_name=body.project_name,
        inputs=entries,
        discipline_order=order,
        skip_aps=body.skip_aps,
        max_vision_workers=body.max_vision_workers,
        max_discipline_workers=body.max_discipline_workers,
    )
    queue = get_task_queue()
    queue.enqueue(
        "app.services.project_pipeline.queue_job.process_project_run",
        rec.run_id,
        job_timeout=7200,
    )
    prefix = settings.api_prefix.rstrip("/")
    return ProjectRunCreateResponse(
        run_id=rec.run_id,
        status="pending",
        status_url=f"{prefix}/project-runs/{rec.run_id}",
    )


@router.get("/{run_id}", response_model=ProjectRunGetResponse)
def get_project_run(run_id: str) -> ProjectRunGetResponse:
    settings = get_settings()
    store = ProjectRunStore(settings.job_data_dir)
    rec = store.get(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return ProjectRunGetResponse(
        run_id=rec.run_id,
        project_id=rec.project_id,
        project_name=rec.project_name,
        status=rec.status,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        error=rec.error,
        skip_aps=rec.skip_aps,
        disciplines=rec.disciplines,
        run_summary=rec.run_summary,
        work_subdir=rec.work_subdir,
    )
