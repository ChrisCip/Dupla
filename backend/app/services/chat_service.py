from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatPostRequest


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_messages(self, after_uuid: Optional[uuid.UUID], limit: int = 100) -> list[ChatMessageResponse]:
        cap = min(max(limit, 1), 200)
        if after_uuid is None:
            q = (
                select(ChatMessage)
                .options(joinedload(ChatMessage.author))
                .order_by(ChatMessage.created_at.desc())
                .limit(cap)
            )
            rows = list((await self._session.execute(q)).unique().scalars().all())
            rows.reverse()
        else:
            ref = await self._session.get(ChatMessage, after_uuid)
            if ref is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje de referencia no encontrado")
            q = (
                select(ChatMessage)
                .options(joinedload(ChatMessage.author))
                .where(
                    (ChatMessage.created_at > ref.created_at)
                    | ((ChatMessage.created_at == ref.created_at) & (ChatMessage.id > ref.id))
                )
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                .limit(cap)
            )
            rows = list((await self._session.execute(q)).unique().scalars().all())

        out: list[ChatMessageResponse] = []
        for msg in rows:
            author = msg.author
            if author is None:
                continue
            out.append(ChatMessageResponse.from_row(msg, author))
        return out

    async def post_message(self, author: User, body: ChatPostRequest) -> ChatMessageResponse:
        msg = ChatMessage(
            id=uuid.uuid4(),
            author_id=author.id,
            body=body.body.strip(),
            created_at=datetime.utcnow(),
        )
        self._session.add(msg)
        await self._session.flush()
        return ChatMessageResponse.from_row(msg, author)
