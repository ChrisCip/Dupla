"""Budget orchestration service.

Bridges the main platform to the processor microservice:
- enqueue_budget_job: forwards file bytes to processor, stores RQ job_id.
- sync_job_status: polls processor for current job state, persists result.
- get_latest_job: returns most recent ProjectBudgetJob for a project.
- get_budget_result: returns the completed budget JSONB.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project_budget_job import ProjectBudgetJob
from app.models.project_file import ProjectFile
from app.models.user import User
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)
settings = get_settings()


class BudgetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._project_svc = ProjectService(session)

    async def _get_project_file(self, project_id: UUID, file_uuid: UUID) -> Optional[ProjectFile]:
        result = await self._session.execute(
            select(ProjectFile).where(
                ProjectFile.id == file_uuid,
                ProjectFile.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def enqueue_budget_job(
        self,
        user: User,
        project_uuid: UUID,
        dwg_file_uuid: UUID,
        pdf_file_uuid: Optional[UUID] = None,
        discipline: Optional[str] = None,
    ) -> ProjectBudgetJob:
        project = await self._project_svc.get_project(user, project_uuid)

        dwg_file = await self._get_project_file(project.id, dwg_file_uuid)
        if dwg_file is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DWG file not found in project")

        upload_root = Path(settings.upload_root)
        dwg_path = upload_root / dwg_file.storage_key
        if not dwg_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DWG file not found on disk")

        dwg_bytes = dwg_path.read_bytes()

        pdf_bytes: Optional[bytes] = None
        pdf_filename: Optional[str] = None
        if pdf_file_uuid is not None:
            pdf_file = await self._get_project_file(project.id, pdf_file_uuid)
            if pdf_file is not None:
                pdf_path = upload_root / pdf_file.storage_key
                if pdf_path.exists():
                    pdf_bytes = pdf_path.read_bytes()
                    pdf_filename = pdf_file.original_name

        processor_url = settings.processor_url
        files: dict[str, Any] = {
            "dwg_file": (dwg_file.original_name, dwg_bytes, "application/octet-stream"),
        }
        if pdf_bytes is not None and pdf_filename is not None:
            files["pdf_file"] = (pdf_filename, pdf_bytes, "application/pdf")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{processor_url}/jobs/process", files=files)
        except Exception as exc:
            logger.error("Failed to reach processor service: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Processor service unavailable",
            ) from exc

        if resp.status_code not in (200, 201, 202):
            logger.error("Processor returned %s: %s", resp.status_code, resp.text[:500])
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Processor rejected the request")

        data = resp.json()
        job_id = data.get("job_id")
        if not job_id:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Processor returned no job_id")

        job = ProjectBudgetJob(
            project_id=project.id,
            job_id=str(job_id),
            status="queued",
            discipline=discipline,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_latest_job(self, user: User, project_uuid: UUID) -> Optional[ProjectBudgetJob]:
        project = await self._project_svc.get_project(user, project_uuid)
        result = await self._session.execute(
            select(ProjectBudgetJob)
            .where(ProjectBudgetJob.project_id == project.id)
            .order_by(ProjectBudgetJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def sync_job_status(self, job: ProjectBudgetJob) -> ProjectBudgetJob:
        """Refresh job status from processor. Mutates job in-place; caller must commit."""
        if job.status in ("completed", "failed"):
            return job

        processor_url = settings.processor_url
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{processor_url}/jobs/{job.job_id}")
        except Exception as exc:
            logger.warning("Processor status poll failed: %s", exc)
            return job

        if resp.status_code == 404:
            job.status = "failed"
            job.error = "Job not found on processor"
            return job

        if resp.status_code != 200:
            return job

        data = resp.json()
        remote_status = data.get("status", "")

        if remote_status == "completed":
            job.status = "completed"
            job.result = data.get("result")
        elif remote_status == "failed":
            job.status = "failed"
            job.error = str(data.get("error") or "Unknown error")
        elif remote_status in ("queued", "started", "deferred", "scheduled"):
            job.status = "processing" if remote_status == "started" else "queued"

        return job

    async def get_budget_result(self, user: User, project_uuid: UUID) -> dict[str, Any]:
        job = await self.get_latest_job(user, project_uuid)
        if job is None or job.status != "completed" or job.result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No completed budget found")
        return job.result
