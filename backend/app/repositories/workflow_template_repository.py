from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.workflow_template import WorkflowTemplate, WorkflowTemplateStep


class WorkflowTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_templates(self) -> list[WorkflowTemplate]:
        q = (
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.archived_at.is_(None))
            .order_by(WorkflowTemplate.name.asc())
        )
        return list((await self._session.execute(q)).scalars().all())

    async def get_template_by_uuid(self, template_uuid: UUID) -> Optional[WorkflowTemplate]:
        q = (
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.id == template_uuid)
        )
        return (await self._session.execute(q)).scalar_one_or_none()

    async def list_steps_ordered(self, template_id: UUID) -> list[WorkflowTemplateStep]:
        q = (
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.workflow_template_id == template_id)
            .order_by(WorkflowTemplateStep.sort_index.asc())
        )
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_step_by_uuid(self, step_uuid: UUID) -> Optional[WorkflowTemplateStep]:
        q = select(WorkflowTemplateStep).where(WorkflowTemplateStep.id == step_uuid)
        return (await self._session.execute(q)).scalar_one_or_none()

    async def first_step_matching_behavior(
        self,
        template_id: UUID,
        behavior_kind: str,
    ) -> Optional[WorkflowTemplateStep]:
        q = (
            select(WorkflowTemplateStep)
            .where(
                WorkflowTemplateStep.workflow_template_id == template_id,
                WorkflowTemplateStep.behavior_kind == behavior_kind,
            )
            .order_by(WorkflowTemplateStep.sort_index.asc())
            .limit(1)
        )
        return (await self._session.execute(q)).scalar_one_or_none()

    async def search_templates_and_projects(
        self,
        *,
        query: Optional[str],
        preview_project_limit: int = 5,
    ) -> list[tuple[WorkflowTemplate, list[tuple[UUID, str]]]]:
        """Devuelve plantillas con hasta N proyectos (uuid, nombre) para el hub."""
        qtxt = (query or "").strip().lower()
        base = select(WorkflowTemplate).where(WorkflowTemplate.archived_at.is_(None))
        if qtxt:
            sub_proj = (
                select(Project.workflow_template_id)
                .where(func.lower(Project.name).contains(qtxt))
                .distinct()
            )
            base = base.where(
                or_(func.lower(WorkflowTemplate.name).contains(qtxt), WorkflowTemplate.id.in_(sub_proj))
            )
        base = base.order_by(WorkflowTemplate.name.asc())
        templates = list((await self._session.execute(base)).scalars().all())
        out: list[tuple[WorkflowTemplate, list[tuple[UUID, str]]]] = []
        for t in templates:
            pq = (
                select(Project.id, Project.name)
                .where(Project.workflow_template_id == t.id)
                .order_by(Project.updated_at.desc())
                .limit(preview_project_limit)
            )
            rows = (await self._session.execute(pq)).all()
            projects_preview = [(r[0], r[1]) for r in rows]
            out.append((t, projects_preview))
        return out
