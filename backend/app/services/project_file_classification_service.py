"""Clasificación ligera de archivos de proyecto (extensión + cabecera) en segundo plano."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal
from app.models.project import Project
from app.models.project_file import ProjectFile

_classify_sem = asyncio.Semaphore(5)

FILE_CAT_PDF = "PDF_DOCUMENT"
FILE_CAT_CAD = "CAD_DRAWING"
FILE_CAT_BIM = "BIM_MODEL"
FILE_CAT_LEGAL = "LEGAL_TECHNICAL"

SUGGESTIONS_KEY = "file_classification_suggestions"


def _category_from_path(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return FILE_CAT_PDF
    if ext in (".dwg", ".dxf"):
        return FILE_CAT_CAD
    if ext == ".ifc":
        return FILE_CAT_BIM
    if ext == ".docx":
        return FILE_CAT_LEGAL
    return None


async def _classify_and_merge_pliego_hint(session: AsyncSession, pf: ProjectFile) -> None:
    path = Path(pf.storage_key)
    if not path.is_file():
        return
    kind = _category_from_path(path)
    if kind is None:
        return
    if pf.category and str(pf.category).strip():
        return
    pf.category = kind

    result = await session.execute(select(Project).where(Project.id == pf.project_id))
    project = result.scalar_one_or_none()
    if project is None:
        return
    spec: dict = dict(project.specifications_document) if isinstance(project.specifications_document, dict) else {}
    hints: list = list(spec.get(SUGGESTIONS_KEY) or [])
    fid = str(pf.id)
    hints = [h for h in hints if isinstance(h, dict) and str(h.get("file_uuid")) != fid]
    hints.append(
        {
            "file_uuid": fid,
            "category": kind,
            "name": pf.original_name,
        }
    )
    spec[SUGGESTIONS_KEY] = hints[-80:]
    project.specifications_document = spec
    flag_modified(project, "specifications_document")


async def run_file_classification_task(file_id: UUID) -> None:
    """BackgroundTasks: clasificación paralela (máx. 5 simultáneas por proceso)."""
    async with _classify_sem:
        async with AsyncSessionLocal() as session:
            try:
                pf = await session.get(ProjectFile, file_id)
                if pf is None:
                    return
                await _classify_and_merge_pliego_hint(session, pf)
                await session.commit()
            except Exception:
                await session.rollback()
