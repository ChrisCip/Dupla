"""PDF export for clash analysis reports (technical + human/architect)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import Project
from app.models.project_clash_job import ProjectClashJob
from app.models.user import User
from app.services.clash_reports.data import build_report_bundle
from app.services.clash_reports.human_pdf import build_human_pdf
from app.services.clash_reports.technical_pdf import build_technical_pdf
from app.services.clash_service import ClashService, extract_clash_artifacts
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)
_settings = get_settings()

_INVALID_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def _sanitize_filename_part(value: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("-", (value or "").strip())
    return cleaned or "sin-nombre"


def _user_display(user: User | None) -> str:
    if user is None:
        return "usuario"
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.email


def build_export_filename(kind: str, meta: dict[str, Any]) -> str:
    folder = _sanitize_filename_part(str(meta.get("folder_name") or "carpeta"))
    project = _sanitize_filename_part(str(meta.get("project_name") or "proyecto"))
    user = _sanitize_filename_part(str(meta.get("user_display") or "usuario"))
    date_str = str(meta.get("run_date") or datetime.now(timezone.utc).date().isoformat())
    sequence = int(meta.get("run_sequence") or 1)
    number = f"{sequence:02d}"
    if kind == "technical":
        return (
            f"Reporte Tecnico de Clashes de la {folder} del {project} "
            f"con {date_str} por el {user} numero {number}.pdf"
        )
    return f"Reporte de la {folder} del {project} con {date_str} por el {user} numero {number}.pdf"


def content_disposition_header(filename: str) -> dict[str, str]:
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "clash-report.pdf"
    encoded = quote(filename)
    return {
        "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"
    }


class ClashExportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clash_svc = ClashService(session)
        self._project_svc = ProjectService(session)

    async def _export_meta(
        self,
        user: User,
        project: Project,
        job: ProjectClashJob,
    ) -> dict[str, Any]:
        triggered_by: User | None = None
        if job.triggered_by_user_id:
            triggered_by = await self._session.get(User, job.triggered_by_user_id)
        run_date = job.updated_at or job.created_at or datetime.now(timezone.utc)
        return {
            "project_name": project.name,
            "folder_name": job.folder_name or "carpeta",
            "user_display": _user_display(triggered_by or user),
            "run_date": run_date.date().isoformat(),
            "run_sequence": job.run_sequence or 1,
        }

    def build_clash_technical_pdf(
        self,
        *,
        meta: dict[str, Any],
        artifacts: dict[str, Any],
    ) -> bytes:
        bundle = build_report_bundle(meta=meta, artifacts=artifacts)
        return build_technical_pdf(bundle)

    def build_clash_human_pdf(
        self,
        *,
        meta: dict[str, Any],
        artifacts: dict[str, Any],
    ) -> bytes:
        bundle = build_report_bundle(meta=meta, artifacts=artifacts)
        return build_human_pdf(bundle)

    async def export_technical_pdf(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        job = await self._clash_svc.get_job_for_export(user, project_uuid, job_id=job_id)
        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        meta = await self._export_meta(user, project, job)
        pdf_bytes = self.build_clash_technical_pdf(meta=meta, artifacts=artifacts)
        filename = build_export_filename("technical", meta)
        return pdf_bytes, filename

    async def _try_fetch_rich_human_pdf(self, coordination_job_id: str) -> bytes | None:
        """Pull the rich coordination_report_human.pdf rendered by coordination-service."""
        base = (_settings.coordination_url or "").rstrip("/")
        if not base or not coordination_job_id:
            return None
        url = f"{base}/jobs/{coordination_job_id}/exports/human.pdf"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url)
        except Exception as exc:
            logger.warning("Could not reach coordination-service for rich human PDF: %s", exc)
            return None
        if resp.status_code != 200:
            logger.info(
                "Rich human PDF not available (job=%s status=%s)",
                coordination_job_id,
                resp.status_code,
            )
            return None
        body = resp.content or b""
        if not body.startswith(b"%PDF"):
            logger.warning("Rich human PDF response was not a PDF (first bytes=%r)", body[:8])
            return None
        return body

    async def export_human_pdf(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        job = await self._clash_svc.get_job_for_export(user, project_uuid, job_id=job_id)
        meta = await self._export_meta(user, project, job)
        filename = build_export_filename("human", meta)

        rich = await self._try_fetch_rich_human_pdf(job.job_id)
        if rich is not None:
            return rich, filename

        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        pdf_bytes = self.build_clash_human_pdf(meta=meta, artifacts=artifacts)
        return pdf_bytes, filename
