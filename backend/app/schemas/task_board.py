from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.inspection import inspect

from app.models.task_board import TaskCard, TaskCardComment, TaskList


class TaskAssigneeOption(BaseModel):
    uuid: UUID
    email: str


class TaskCardResponse(BaseModel):
    uuid: UUID
    title: str
    description: Optional[str]
    position: int
    list_uuid: UUID
    project_uuid: Optional[UUID]
    created_at: datetime
    created_by_uuid: Optional[UUID]
    creator_email: Optional[str]
    assignee_uuid: Optional[UUID]
    assignee_email: Optional[str]
    archived: bool
    archived_at: Optional[datetime]
    created_in_phase: Optional[str]

    @classmethod
    def from_card(cls, card: TaskCard) -> TaskCardResponse:
        st = inspect(card)
        creator = None if "creator" in st.unloaded else card.creator
        assignee = None if "assignee" in st.unloaded else card.assignee
        return cls(
            uuid=card.id,
            title=card.title,
            description=card.description,
            position=card.position,
            list_uuid=card.list_id,
            project_uuid=card.project_id,
            created_at=card.created_at,
            created_by_uuid=card.created_by,
            creator_email=creator.email if creator is not None else None,
            assignee_uuid=card.assignee_id,
            assignee_email=assignee.email if assignee is not None else None,
            archived=card.archived,
            archived_at=card.archived_at,
            created_in_phase=card.created_in_phase,
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
    project_uuid: Optional[UUID] = None


class TaskCardPatchRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    list_uuid: Optional[UUID] = None
    position: Optional[int] = Field(default=None, ge=0)
    assignee_uuid: Optional[UUID] = None
    archived: Optional[bool] = None
    project_uuid: Optional[UUID] = None


class TaskCardCommentResponse(BaseModel):
    uuid: UUID
    body: str
    created_at: datetime
    author_uuid: Optional[UUID]
    author_email: Optional[str]

    @classmethod
    def from_row(cls, row: TaskCardComment) -> TaskCardCommentResponse:
        st = inspect(row)
        author = None if "author" in st.unloaded else row.author
        return cls(
            uuid=row.id,
            body=row.body,
            created_at=row.created_at,
            author_uuid=row.author_id,
            author_email=author.email if author is not None else None,
        )


class TaskCardCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
