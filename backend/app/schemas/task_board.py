from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task_board import TaskCard, TaskList


class TaskCardResponse(BaseModel):
    uuid: UUID
    title: str
    description: Optional[str]
    position: int
    list_uuid: UUID
    created_at: datetime
    created_by_uuid: Optional[UUID]

    @classmethod
    def from_card(cls, card: TaskCard) -> TaskCardResponse:
        return cls(
            uuid=card.id,
            title=card.title,
            description=card.description,
            position=card.position,
            list_uuid=card.list_id,
            created_at=card.created_at,
            created_by_uuid=card.created_by,
        )


class TaskListResponse(BaseModel):
    uuid: UUID
    title: str
    position: int
    cards: list[TaskCardResponse]

    @classmethod
    def from_list(cls, task_list: TaskList) -> TaskListResponse:
        cards = sorted(task_list.cards, key=lambda c: (c.position, str(c.id)))
        return cls(
            uuid=task_list.id,
            title=task_list.title,
            position=task_list.position,
            cards=[TaskCardResponse.from_card(c) for c in cards],
        )


class TaskBoardResponse(BaseModel):
    lists: list[TaskListResponse]


class TaskCardCreateRequest(BaseModel):
    list_uuid: UUID
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)


class TaskCardPatchRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    list_uuid: Optional[UUID] = None
    position: Optional[int] = Field(default=None, ge=0)
