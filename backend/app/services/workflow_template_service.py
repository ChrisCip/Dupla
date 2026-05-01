from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.workflow_step_behavior import VALID_WORKFLOW_STEP_BEHAVIORS
from app.models.project import Project
from app.models.workflow_template import WorkflowTemplate, WorkflowTemplateStep
from app.repositories.workflow_template_repository import WorkflowTemplateRepository
from app.schemas.workflow_template import WorkflowTemplateStepInput

ALLOWED_WORKFLOW_TEMPLATE_ICON_KEYS = frozenset(
    {
        "GitBranch",
        "Workflow",
        "Layers",
        "Boxes",
        "Kanban",
        "LayoutGrid",
        "CircleDot",
        "ArrowRight",
        "GitFork",
        "Route",
        "Map",
        "Building2",
        "HardHat",
        "DraftingCompass",
        "Ruler",
        "Hammer",
        "ClipboardList",
        "CheckCircle",
        "CirclePlay",
        "Timer",
        "Zap",
    }
)


def _detect_cycle_stable_keys(steps: list[WorkflowTemplateStepInput]) -> None:
    """blocked_by_stable_key forma aristas blocker -> bloqueado; debe ser acíclico."""
    keys = {s.stable_key for s in steps}
    adj: dict[str, set[str]] = {k: set() for k in keys}
    for s in steps:
        if s.blocked_by_stable_key:
            if s.blocked_by_stable_key not in keys:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Paso «{s.stable_key}»: bloqueado por clave inexistente «{s.blocked_by_stable_key}»",
                )
            adj[s.blocked_by_stable_key].add(s.stable_key)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in keys}

    def dfs(u: str) -> bool:
        color[u] = GRAY
        for v in adj.get(u, ()):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for k in keys:
        if color[k] == WHITE:
            if dfs(k):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Las dependencias entre pasos forman un ciclo",
                )


class WorkflowTemplateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkflowTemplateRepository(session)

    async def create_template(self, user_id: UUID, *, name: str, description: str) -> WorkflowTemplate:
        now = datetime.now(timezone.utc)
        row = WorkflowTemplate(
            name=name.strip(),
            description=(description or "").strip(),
            created_by_user_id=user_id,
            archived_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def patch_template(
        self,
        template_uuid: UUID,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        archived: Optional[bool] = None,
        icon_key: Optional[str] = None,
    ) -> WorkflowTemplate:
        t = await self._repo.get_template_by_uuid(template_uuid)
        if t is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
        if name is not None:
            t.name = name.strip()
        if description is not None:
            t.description = description.strip()
        if archived is not None:
            t.archived_at = None if not archived else datetime.now(timezone.utc)
        if icon_key is not None:
            raw = icon_key.strip()
            if raw not in ALLOWED_WORKFLOW_TEMPLATE_ICON_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="icon_key no permitido",
                )
            t.icon_key = raw
        t.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return t

    async def replace_steps(self, template_uuid: UUID, steps: list[WorkflowTemplateStepInput]) -> WorkflowTemplate:
        t = await self._repo.get_template_by_uuid(template_uuid)
        if t is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
        if t.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La plantilla está archivada")

        seen_stable: set[str] = set()
        for s in steps:
            if s.stable_key in seen_stable:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"stable_key duplicado: {s.stable_key}",
                )
            seen_stable.add(s.stable_key)
            if s.behavior_kind not in VALID_WORKFLOW_STEP_BEHAVIORS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"behavior_kind no válido: {s.behavior_kind}",
                )

        _detect_cycle_stable_keys(steps)

        existing_q = select(WorkflowTemplateStep).where(WorkflowTemplateStep.workflow_template_id == t.id)
        existing_rows = list((await self._session.execute(existing_q)).scalars().all())
        existing_by_stable = {r.stable_key: r for r in existing_rows}
        payload_stable = {s.stable_key for s in steps}

        for row in existing_rows:
            if row.stable_key not in payload_stable:
                uq = select(Project.id).where(Project.current_workflow_step_id == row.id).limit(1)
                if (await self._session.execute(uq)).scalar_one_or_none() is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede eliminar el paso «{row.stable_key}»: hay proyectos en ese paso",
                    )

        now = datetime.now(timezone.utc)
        stable_to_row: dict[str, WorkflowTemplateStep] = {}

        for idx, inp in enumerate(steps):
            row = existing_by_stable.get(inp.stable_key)
            actions = inp.on_enter_actions if isinstance(inp.on_enter_actions, list) else []
            if row is None:
                row = WorkflowTemplateStep(
                    workflow_template_id=t.id,
                    sort_index=idx,
                    stable_key=inp.stable_key,
                    title=inp.title.strip(),
                    behavior_kind=inp.behavior_kind.strip(),
                    blocked_by_step_id=None,
                    requires_approval_role=inp.requires_approval_role.strip()
                    if inp.requires_approval_role
                    else None,
                    on_enter_actions=actions,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(row)
                await self._session.flush()
            else:
                row.sort_index = idx
                row.title = inp.title.strip()
                row.behavior_kind = inp.behavior_kind.strip()
                row.requires_approval_role = (
                    inp.requires_approval_role.strip() if inp.requires_approval_role else None
                )
                row.on_enter_actions = actions
                row.updated_at = now
                row.blocked_by_step_id = None
            stable_to_row[inp.stable_key] = row

        await self._session.flush()

        for inp in steps:
            row = stable_to_row[inp.stable_key]
            if inp.blocked_by_stable_key:
                blk = stable_to_row.get(inp.blocked_by_stable_key)
                if blk is None:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="blocked_by inválido")
                row.blocked_by_step_id = blk.id
            else:
                row.blocked_by_step_id = None

        to_delete = [r for r in existing_rows if r.stable_key not in payload_stable]
        for r in to_delete:
            self._session.delete(r)

        t.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

        out = await self._repo.get_template_by_uuid(template_uuid)
        assert out is not None
        await self._session.refresh(out, ["steps"])
        return out

    async def get_detail(self, template_uuid: UUID) -> WorkflowTemplate:
        q = (
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.id == template_uuid)
        )
        t = (await self._session.execute(q)).scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
        return t
