from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.project import Project
from app.models.task_board import TaskCard, TaskList
from app.models.user import User, UserModule
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task_board import (
    TaskAssigneeOption,
    TaskBoardResponse,
    TaskCardCreateRequest,
    TaskCardPatchRequest,
    TaskCardResponse,
    TaskListResponse,
)


class TaskBoardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._projects = ProjectRepository(session)

    async def _require_project_access_for_card(self, actor: User, project_id: Optional[uuid.UUID]) -> None:
        if project_id is None:
            return
        project = await self._session.get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proyecto no encontrado",
            )
        if not await self._projects.user_has_access_to_project(actor, project):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin acceso a este proyecto",
            )

    async def list_assignees(self) -> list[TaskAssigneeOption]:
        settings = get_settings()
        mid = settings.architecture_module_id
        q = (
            select(User)
            .join(UserModule, UserModule.user_id == User.id)
            .where(UserModule.module_id == mid)
            .order_by(User.email)
        )
        rows = list((await self._session.execute(q)).scalars().all())
        return [TaskAssigneeOption(uuid=u.id, email=u.email) for u in rows]

    async def _validate_assignee(self, assignee_uuid: Optional[uuid.UUID]) -> None:
        if assignee_uuid is None:
            return
        user = await self._session.get(User, assignee_uuid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario asignado no existe",
            )
        settings = get_settings()
        if not await self._users.has_module(assignee_uuid, settings.architecture_module_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El asignado debe tener acceso al módulo Arquitectura",
            )

    async def get_board(
        self,
        *,
        viewer: User,
        include_archived: bool,
        mine: bool,
        filter_assignee: Optional[uuid.UUID],
        filter_project: Optional[uuid.UUID] = None,
    ) -> TaskBoardResponse:
        result = await self._session.execute(
            select(TaskList)
            .options(
                selectinload(TaskList.cards).selectinload(TaskCard.creator),
                selectinload(TaskList.cards).selectinload(TaskCard.assignee),
            )
            .order_by(TaskList.position)
        )
        lists = list(result.scalars().all())

        assignee_target: Optional[uuid.UUID] = None
        if mine:
            assignee_target = viewer.id
        elif filter_assignee is not None:
            assignee_target = filter_assignee

        list_responses: list[TaskListResponse] = []
        for tl in lists:
            active = [c for c in tl.cards if not c.archived]
            if assignee_target is not None:
                active = [c for c in active if c.assignee_id == assignee_target]
            if filter_project is not None:
                active = [c for c in active if c.project_id == filter_project]
            list_responses.append(TaskListResponse.from_list(tl, active))

        archived_cards: list[TaskCardResponse] = []
        if include_archived:
            q = (
                select(TaskCard)
                .where(TaskCard.archived.is_(True))
                .options(selectinload(TaskCard.creator), selectinload(TaskCard.assignee))
                .order_by(TaskCard.archived_at.desc(), TaskCard.created_at.desc())
            )
            arch_rows = list((await self._session.execute(q)).scalars().all())
            filtered = arch_rows
            if assignee_target is not None:
                filtered = [c for c in arch_rows if c.assignee_id == assignee_target]
            if filter_project is not None:
                filtered = [c for c in filtered if c.project_id == filter_project]
            archived_cards = [TaskCardResponse.from_card(c) for c in filtered]

        return TaskBoardResponse(lists=list_responses, archived_cards=archived_cards)

    async def create_card(self, actor: User, body: TaskCardCreateRequest) -> TaskCard:
        await self._validate_assignee(body.assignee_uuid)
        await self._require_project_access_for_card(actor, body.project_uuid)

        lst = await self._session.get(TaskList, body.list_uuid)
        if lst is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista no encontrada")

        q = select(TaskCard).where(TaskCard.list_id == body.list_uuid, TaskCard.archived.is_(False))
        existing = list((await self._session.execute(q)).scalars().all())
        position = max((c.position for c in existing), default=-1) + 1

        card = TaskCard(
            id=uuid.uuid4(),
            list_id=body.list_uuid,
            title=body.title.strip(),
            description=body.description.strip() if body.description else None,
            position=position,
            created_by=actor.id,
            assignee_id=body.assignee_uuid,
            archived=False,
            archived_at=None,
            created_at=datetime.now(timezone.utc),
            project_id=body.project_uuid,
        )
        self._session.add(card)
        await self._session.flush()
        await self._session.refresh(card, attribute_names=["creator", "assignee"])
        return card

    async def patch_card(self, actor: User, card_uuid: uuid.UUID, body: TaskCardPatchRequest) -> TaskCard:
        card = await self._session.get(TaskCard, card_uuid)
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")

        await self._require_project_access_for_card(actor, card.project_id)

        updates = body.model_dump(exclude_unset=True)

        if "assignee_uuid" in updates:
            await self._validate_assignee(updates["assignee_uuid"])
            card.assignee_id = updates["assignee_uuid"]

        if "project_uuid" in updates:
            await self._require_project_access_for_card(actor, updates["project_uuid"])
            card.project_id = updates["project_uuid"]

        if "title" in updates and updates["title"] is not None:
            card.title = updates["title"].strip()
        if "description" in updates:
            card.description = (
                updates["description"].strip() if updates["description"] else None
            )

        if "archived" in updates:
            card.archived = bool(updates["archived"])
            if card.archived:
                card.archived_at = datetime.now(timezone.utc)
            else:
                card.archived_at = None

        has_list = "list_uuid" in updates and updates["list_uuid"] is not None
        has_position = "position" in updates
        if has_list or has_position:
            if card.archived:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Desarchiva la tarea antes de moverla de columna",
                )
            if has_list:
                if not has_position:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="position es obligatoria al mover de lista",
                    )
                await self._move_card(card, updates["list_uuid"], updates["position"])
            else:
                await self._move_card(card, card.list_id, updates["position"])

        await self._session.flush()
        await self._session.refresh(card, attribute_names=["creator", "assignee"])
        return card

    async def _ordered_ids(self, list_id: uuid.UUID) -> list[uuid.UUID]:
        q = (
            select(TaskCard)
            .where(TaskCard.list_id == list_id, TaskCard.archived.is_(False))
            .order_by(TaskCard.position.asc(), TaskCard.id.asc())
        )
        cards = list((await self._session.execute(q)).scalars().all())
        return [c.id for c in cards]

    async def _apply_order(self, list_id: uuid.UUID, ordered_ids: list[uuid.UUID]) -> None:
        for i, cid in enumerate(ordered_ids):
            c = await self._session.get(TaskCard, cid)
            if c is None:
                continue
            c.list_id = list_id
            c.position = i

    async def _move_card(self, card: TaskCard, new_list_uuid: uuid.UUID, position: int) -> None:
        new_list = await self._session.get(TaskList, new_list_uuid)
        if new_list is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista destino no encontrada")

        old_id = card.list_id
        if old_id == new_list_uuid:
            ids = await self._ordered_ids(old_id)
            ids = [i for i in ids if i != card.id]
            pos = min(max(0, position), len(ids))
            ids.insert(pos, card.id)
            await self._apply_order(old_id, ids)
            return

        old_ids = await self._ordered_ids(old_id)
        old_ids = [i for i in old_ids if i != card.id]
        await self._apply_order(old_id, old_ids)

        new_ids = await self._ordered_ids(new_list_uuid)
        pos = min(max(0, position), len(new_ids))
        new_ids.insert(pos, card.id)
        await self._apply_order(new_list_uuid, new_ids)
