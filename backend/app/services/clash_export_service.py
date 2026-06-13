"""PDF export for clash analysis reports (technical + human/architect)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_clash_job import ProjectClashJob
from app.models.user import User
from app.services.clash_excel_export import build_corrida_technical_excel, build_final_technical_excel
from app.services.clash_reports.data import build_report_bundle
from app.services.clash_reports.final_pdf import build_final_human_pdf, build_final_technical_pdf
from app.services.clash_reports.human_pdf import build_human_pdf
from app.services.clash_reports.technical_pdf import build_technical_pdf
from app.services.clash_service import ClashService, extract_clash_artifacts
from app.services.clash_workflow_service import ClashWorkflowService
from app.services.project_service import ProjectService

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
    if kind == "technical_excel":
        return (
            f"Reporte Tecnico de Clashes de la {folder} del {project} "
            f"con {date_str} por el {user} numero {number}.xlsx"
        )
    if kind == "final_technical":
        return (
            f"Informe Tecnico Final de la {folder} del {project} "
            f"con {date_str} por el {user} numero {number}.pdf"
        )
    if kind == "final_technical_excel":
        return (
            f"Informe Tecnico Final de la {folder} del {project} "
            f"con {date_str} por el {user} numero {number}.xlsx"
        )
    if kind == "final_human":
        return (
            f"Informe Final de la {folder} del {project} "
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

    async def export_human_pdf(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        job = await self._clash_svc.get_job_for_export(user, project_uuid, job_id=job_id)
        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        meta = await self._export_meta(user, project, job)
        pdf_bytes = self.build_clash_human_pdf(meta=meta, artifacts=artifacts)
        filename = build_export_filename("human", meta)
        return pdf_bytes, filename

    async def export_technical_excel(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        job = await self._clash_svc.get_job_for_export(user, project_uuid, job_id=job_id)
        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        meta = await self._export_meta(user, project, job)
        bundle = build_report_bundle(meta=meta, artifacts=artifacts)
        xlsx = build_corrida_technical_excel(bundle)
        filename = build_export_filename("technical_excel", meta)
        return xlsx, filename

    async def export_final_technical_pdf(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        workflow = ClashWorkflowService(self._session)
        job, items = await workflow.list_workflow_rows_for_export(user, project_uuid, job_id=job_id)
        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        meta = await self._export_meta(user, project, job)
        bundle = build_report_bundle(meta=meta, artifacts=artifacts)
        pdf_bytes = build_final_technical_pdf(bundle, items)
        filename = build_export_filename("final_technical", meta)
        return pdf_bytes, filename

    async def export_final_technical_excel(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        workflow = ClashWorkflowService(self._session)
        job, items = await workflow.list_workflow_rows_for_export(user, project_uuid, job_id=job_id)
        meta = await self._export_meta(user, project, job)
        xlsx = build_final_technical_excel(meta=meta, items=items)
        filename = build_export_filename("final_technical_excel", meta)
        return xlsx, filename

    async def export_final_human_pdf(
        self,
        user: User,
        project_uuid: UUID,
        job_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        project = await self._project_svc.get_project(user, project_uuid)
        workflow = ClashWorkflowService(self._session)
        job, items = await workflow.list_workflow_rows_for_export(user, project_uuid, job_id=job_id)
        artifacts = extract_clash_artifacts(job.result if isinstance(job.result, dict) else None)
        meta = await self._export_meta(user, project, job)
        bundle = build_report_bundle(meta=meta, artifacts=artifacts)
        pdf_bytes = build_final_human_pdf(bundle, items)
        filename = build_export_filename("final_human", meta)
        return pdf_bytes, filename
