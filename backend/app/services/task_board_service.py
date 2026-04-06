from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_board import TaskCard, TaskList
from app.models.user import User
from app.schemas.task_board import (
    TaskBoardResponse,
    TaskCardCreateRequest,
    TaskCardPatchRequest,
    TaskListResponse,
)


class TaskBoardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_board(self) -> TaskBoardResponse:
        result = await self._session.execute(
            select(TaskList).options(selectinload(TaskList.cards)).order_by(TaskList.position)
        )
        lists = list(result.scalars().all())
        return TaskBoardResponse(lists=[TaskListResponse.from_list(tl) for tl in lists])

    async def create_card(self, actor: User, body: TaskCardCreateRequest) -> TaskCard:
        lst = await self._session.get(TaskList, body.list_uuid)
        if lst is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista no encontrada")

        q = select(TaskCard).where(TaskCard.list_id == body.list_uuid)
        existing = list((await self._session.execute(q)).scalars().all())
        position = max((c.position for c in existing), default=-1) + 1

        card = TaskCard(
            id=uuid.uuid4(),
            list_id=body.list_uuid,
            title=body.title.strip(),
            description=body.description.strip() if body.description else None,
            position=position,
            created_by=actor.id,
            created_at=datetime.utcnow(),
        )
        self._session.add(card)
        await self._session.flush()
        return card

    async def patch_card(self, card_uuid: uuid.UUID, body: TaskCardPatchRequest) -> TaskCard:
        card = await self._session.get(TaskCard, card_uuid)
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")

        if body.title is not None:
            card.title = body.title.strip()
        if body.description is not None:
            card.description = body.description.strip() if body.description else None

        if body.list_uuid is not None:
            if body.position is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="position es obligatoria al mover de lista",
                )
            await self._move_card(card, body.list_uuid, body.position)
        elif body.position is not None:
            await self._move_card(card, card.list_id, body.position)

        await self._session.flush()
        return card

    async def _ordered_ids(self, list_id: uuid.UUID) -> list[uuid.UUID]:
        q = (
            select(TaskCard)
            .where(TaskCard.list_id == list_id)
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
