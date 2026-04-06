from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task_board import TaskCard, TaskList


class TaskAssigneeOption(BaseModel):
    uuid: UUID
    email: str


class TaskCardResponse(BaseModel):
    uuid: UUID
    title: str
    description: Optional[str]
    position: int
    list_uuid: UUID
    created_at: datetime
    created_by_uuid: Optional[UUID]
    creator_email: Optional[str]
    assignee_uuid: Optional[UUID]
    assignee_email: Optional[str]
    archived: bool
    archived_at: Optional[datetime]

    @classmethod
    def from_card(cls, card: TaskCard) -> TaskCardResponse:
        creator = getattr(card, "creator", None)
        assignee = getattr(card, "assignee", None)
        return cls(
            uuid=card.id,
            title=card.title,
            description=card.description,
            position=card.position,
            list_uuid=card.list_id,
            created_at=card.created_at,
            created_by_uuid=card.created_by,
            creator_email=creator.email if creator is not None else None,
            assignee_uuid=card.assignee_id,
            assignee_email=assignee.email if assignee is not None else None,
            archived=card.archived,
            archived_at=card.archived_at,
        )


class TaskListResponse(BaseModel):
    uuid: UUID
    title: str
    position: int
    cards: list[TaskCardResponse]

    @classmethod
    def from_list(cls, task_list: TaskList, cards: list[TaskCard]) -> TaskListResponse:
        ordered = sorted(cards, key=lambda c: (c.position, str(c.id)))
        return cls(
            uuid=task_list.id,
            title=task_list.title,
            position=task_list.position,
            cards=[TaskCardResponse.from_card(c) for c in ordered],
        )


class TaskBoardResponse(BaseModel):
    lists: list[TaskListResponse]
    archived_cards: list[TaskCardResponse] = Field(default_factory=list)


class TaskCardCreateRequest(BaseModel):
    list_uuid: UUID
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    assignee_uuid: Optional[UUID] = None


class TaskCardPatchRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    list_uuid: Optional[UUID] = None
    position: Optional[int] = Field(default=None, ge=0)
    assignee_uuid: Optional[UUID] = None
    archived: Optional[bool] = None
