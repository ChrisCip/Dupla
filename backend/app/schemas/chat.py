from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.chat_message import ChatMessage
from app.models.user import User


class ChatAuthorResponse(BaseModel):
    uuid: UUID
    email: EmailStr


class ChatMessageResponse(BaseModel):
    uuid: UUID
    body: str
    created_at: datetime
    author: ChatAuthorResponse

    @classmethod
    def from_row(cls, msg: ChatMessage, author: User) -> ChatMessageResponse:
        return cls(
            uuid=msg.id,
            body=msg.body,
            created_at=msg.created_at,
            author=ChatAuthorResponse(uuid=author.id, email=author.email),
        )


class ChatPostRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
