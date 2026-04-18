from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, intersect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.chat_conversation import (
    GENERAL_CONVERSATION_UUID,
    ChatConversation,
    ChatConversationKind,
    ChatConversationMember,
)
from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.models.user import User
from app.services.project_service import ProjectService
from app.schemas.chat import (
    ChatConversationResponse,
    ChatMessageResponse,
    ChatPostRequest,
    ChatUserDirectoryItem,
)


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_general_conversation(self) -> ChatConversation:
        conv = await self._session.get(ChatConversation, GENERAL_CONVERSATION_UUID)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Canal general no configurado",
            )
        return conv

    async def _get_conversation(self, conversation_uuid: uuid.UUID) -> ChatConversation:
        conv = await self._session.get(ChatConversation, conversation_uuid)
        if conv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
        return conv

    async def _assert_can_access(self, user: User, conv: ChatConversation) -> None:
        if conv.kind == ChatConversationKind.GENERAL:
            return
        if conv.kind == ChatConversationKind.PROJECT:
            stmt = select(ChatConversationMember).where(
                ChatConversationMember.conversation_id == conv.id,
                ChatConversationMember.user_id == user.id,
            )
            row = (await self._session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
            return
        stmt = select(ChatConversationMember).where(
            ChatConversationMember.conversation_id == conv.id,
            ChatConversationMember.user_id == user.id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")

    async def _ensure_general_membership(self, user: User) -> None:
        stmt = select(ChatConversationMember).where(
            ChatConversationMember.conversation_id == GENERAL_CONVERSATION_UUID,
            ChatConversationMember.user_id == user.id,
        )
        if (await self._session.execute(stmt)).scalar_one_or_none() is None:
            self._session.add(
                ChatConversationMember(
                    conversation_id=GENERAL_CONVERSATION_UUID,
                    user_id=user.id,
                )
            )
            await self._session.flush()

    async def _ensure_member(self, user: User, conv: ChatConversation) -> ChatConversationMember:
        stmt = select(ChatConversationMember).where(
            ChatConversationMember.conversation_id == conv.id,
            ChatConversationMember.user_id == user.id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            return row
        m = ChatConversationMember(conversation_id=conv.id, user_id=user.id)
        self._session.add(m)
        await self._session.flush()
        return m

    async def _last_message_preview(self, conversation_id: uuid.UUID) -> Optional[str]:
        q = (
            select(ChatMessage.body)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        raw = (await self._session.execute(q)).scalar_one_or_none()
        if raw is None:
            return None
        text = " ".join(raw.strip().split())
        if len(text) <= 140:
            return text
        return text[:137] + "…"

    async def _participant_count(self, conversation_id: uuid.UUID) -> int:
        q = select(func.count()).select_from(ChatConversationMember).where(
            ChatConversationMember.conversation_id == conversation_id
        )
        return int((await self._session.execute(q)).scalar_one() or 0)

    async def _unread_count(self, user: User, conv: ChatConversation) -> int:
        await self._ensure_member(user, conv)
        stmt = select(ChatConversationMember).where(
            ChatConversationMember.conversation_id == conv.id,
            ChatConversationMember.user_id == user.id,
        )
        mem = (await self._session.execute(stmt)).scalar_one_or_none()
        if mem is None:
            return 0
        threshold = mem.last_read_at
        if threshold is None:
            threshold = datetime(1970, 1, 1, tzinfo=timezone.utc)
        q = (
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.conversation_id == conv.id,
                ChatMessage.author_id != user.id,
                ChatMessage.created_at > threshold,
            )
        )
        return int((await self._session.execute(q)).scalar_one() or 0)

    async def _mark_conversation_read(self, user: User, conv: ChatConversation) -> None:
        mem = await self._ensure_member(user, conv)
        sub = select(func.max(ChatMessage.created_at)).where(ChatMessage.conversation_id == conv.id)
        mx = (await self._session.execute(sub)).scalar_one_or_none()
        if mx is not None:
            mem.last_read_at = mx

    async def _conversation_to_response(
        self,
        conv: ChatConversation,
        user: User,
        *,
        last_message_preview: Optional[str] = None,
        unread_count: int = 0,
        participant_count: Optional[int] = None,
    ) -> ChatConversationResponse:
        if conv.kind == ChatConversationKind.GENERAL:
            return ChatConversationResponse(
                uuid=conv.id,
                kind=conv.kind.value,
                display_title="Avisos generales",
                last_message_at=conv.last_message_at,
                last_message_preview=last_message_preview,
                unread_count=unread_count,
                participant_count=participant_count,
            )
        if conv.kind == ChatConversationKind.GROUP:
            return ChatConversationResponse(
                uuid=conv.id,
                kind=conv.kind.value,
                display_title=(conv.title or "Grupo").strip() or "Grupo",
                last_message_at=conv.last_message_at,
                last_message_preview=last_message_preview,
                unread_count=unread_count,
                participant_count=participant_count,
            )
        if conv.kind == ChatConversationKind.PROJECT:
            title = "Proyecto"
            if conv.project_id is not None:
                proj = await self._session.get(Project, conv.project_id)
                if proj is not None:
                    title = proj.name
            return ChatConversationResponse(
                uuid=conv.id,
                kind=conv.kind.value,
                display_title=f"Chat · {title}",
                last_message_at=conv.last_message_at,
                last_message_preview=last_message_preview,
                unread_count=unread_count,
                participant_count=participant_count,
            )
        stmt = (
            select(User)
            .join(ChatConversationMember, ChatConversationMember.user_id == User.id)
            .where(
                ChatConversationMember.conversation_id == conv.id,
                User.id != user.id,
            )
        )
        other = (await self._session.execute(stmt)).scalar_one_or_none()
        label = other.email if other is not None else "Chat directo"
        return ChatConversationResponse(
            uuid=conv.id,
            kind=conv.kind.value,
            display_title=label,
            last_message_at=conv.last_message_at,
            last_message_preview=last_message_preview,
            unread_count=unread_count,
            participant_count=participant_count,
        )

    async def list_conversations(self, user: User) -> list[ChatConversationResponse]:
        await self._ensure_general_membership(user)
        member_subq = select(ChatConversationMember.conversation_id).where(
            ChatConversationMember.user_id == user.id
        )
        q = select(ChatConversation).where(
            (ChatConversation.kind == ChatConversationKind.GENERAL)
            | (ChatConversation.id.in_(member_subq))
        )
        rows = list((await self._session.execute(q)).scalars().all())

        def sort_key(c: ChatConversation) -> tuple[int, float]:
            ts = (c.last_message_at or c.created_at).timestamp()
            primary = 0 if c.kind == ChatConversationKind.GENERAL else 1
            return (primary, -ts)

        rows.sort(key=sort_key)
        out: list[ChatConversationResponse] = []
        for conv in rows:
            preview = await self._last_message_preview(conv.id)
            unread = await self._unread_count(user, conv)
            pcount = await self._participant_count(conv.id)
            out.append(
                await self._conversation_to_response(
                    conv,
                    user,
                    last_message_preview=preview,
                    unread_count=unread,
                    participant_count=pcount,
                )
            )
        return out

    async def list_directory(self, user: User) -> list[ChatUserDirectoryItem]:
        q = select(User).where(User.id != user.id).order_by(User.email.asc())
        users = list((await self._session.execute(q)).scalars().all())
        return [ChatUserDirectoryItem(uuid=u.id, email=u.email) for u in users]

    async def get_or_create_direct(self, user: User, other_uuid: uuid.UUID) -> ChatConversationResponse:
        if other_uuid == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes abrir un chat contigo mismo",
            )
        other = await self._session.get(User, other_uuid)
        if other is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        inter_q = intersect(
            select(ChatConversationMember.conversation_id).where(ChatConversationMember.user_id == user.id),
            select(ChatConversationMember.conversation_id).where(ChatConversationMember.user_id == other.id),
        )
        stmt = select(ChatConversation).where(
            ChatConversation.kind == ChatConversationKind.DIRECT,
            ChatConversation.id.in_(inter_q),
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return await self._conversation_to_response(existing, user)

        now = datetime.now(timezone.utc)
        conv = ChatConversation(
            id=uuid.uuid4(),
            kind=ChatConversationKind.DIRECT,
            title=None,
            created_at=now,
            last_message_at=None,
        )
        self._session.add(conv)
        self._session.add(ChatConversationMember(conversation_id=conv.id, user_id=user.id))
        self._session.add(ChatConversationMember(conversation_id=conv.id, user_id=other.id))
        await self._session.flush()
        return await self._conversation_to_response(conv, user)

    async def create_group(self, user: User, title: str, member_uuids: list[uuid.UUID]) -> ChatConversationResponse:
        ids_set: set[uuid.UUID] = {user.id}
        for uid in member_uuids:
            ids_set.add(uid)
        if len(ids_set) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un grupo necesita al menos dos personas distintas",
            )

        for uid in ids_set:
            u = await self._session.get(User, uid)
            if u is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario no encontrado: {uid}",
                )

        now = datetime.now(timezone.utc)
        conv = ChatConversation(
            id=uuid.uuid4(),
            kind=ChatConversationKind.GROUP,
            title=title.strip(),
            created_at=now,
            last_message_at=None,
        )
        self._session.add(conv)
        for uid in ids_set:
            self._session.add(ChatConversationMember(conversation_id=conv.id, user_id=uid))
        await self._session.flush()
        return await self._conversation_to_response(conv, user)

    async def list_conversation_messages(
        self,
        user: User,
        conversation_uuid: uuid.UUID,
        after_uuid: Optional[uuid.UUID],
        limit: int,
    ) -> list[ChatMessageResponse]:
        conv = await self._get_conversation(conversation_uuid)
        await self._assert_can_access(user, conv)
        cap = min(max(limit, 1), 200)
        if after_uuid is None:
            q = (
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conv.id)
                .options(joinedload(ChatMessage.author))
                .order_by(ChatMessage.created_at.desc())
                .limit(cap)
            )
            rows = list((await self._session.execute(q)).unique().scalars().all())
            rows.reverse()
        else:
            ref = await self._session.get(ChatMessage, after_uuid)
            if ref is None or ref.conversation_id != conv.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Mensaje de referencia no encontrado",
                )
            q = (
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conv.id)
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
        await self._mark_conversation_read(user, conv)
        await self._session.flush()
        return out

    async def post_conversation_message(
        self,
        user: User,
        conversation_uuid: uuid.UUID,
        body: ChatPostRequest,
    ) -> ChatMessageResponse:
        conv = await self._get_conversation(conversation_uuid)
        await self._assert_can_access(user, conv)
        now = datetime.now(timezone.utc)
        msg = ChatMessage(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            author_id=user.id,
            body=body.body.strip(),
            created_at=now,
        )
        self._session.add(msg)
        conv.last_message_at = now
        await self._session.flush()
        return ChatMessageResponse.from_row(msg, user)

    async def list_messages(self, user: User, after_uuid: Optional[uuid.UUID], limit: int) -> list[ChatMessageResponse]:
        general = await self._get_general_conversation()
        return await self.list_conversation_messages(user, general.id, after_uuid, limit)

    async def post_message(self, author: User, body: ChatPostRequest) -> ChatMessageResponse:
        general = await self._get_general_conversation()
        return await self.post_conversation_message(author, general.id, body)

    async def get_or_create_project_conversation(
        self,
        user: User,
        project_uuid: uuid.UUID,
    ) -> ChatConversationResponse:
        ps = ProjectService(self._session)
        project = await ps.get_project(user, project_uuid)
        stmt = select(ChatConversation).where(
            ChatConversation.kind == ChatConversationKind.PROJECT,
            ChatConversation.project_id == project.id,
        )
        conv = (await self._session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if conv is None:
            conv = ChatConversation(
                id=uuid.uuid4(),
                kind=ChatConversationKind.PROJECT,
                title=None,
                created_at=now,
                last_message_at=None,
                project_id=project.id,
            )
            self._session.add(conv)
            self._session.add(ChatConversationMember(conversation_id=conv.id, user_id=user.id))
            await self._session.flush()
        else:
            m_stmt = select(ChatConversationMember).where(
                ChatConversationMember.conversation_id == conv.id,
                ChatConversationMember.user_id == user.id,
            )
            existing_m = (await self._session.execute(m_stmt)).scalar_one_or_none()
            if existing_m is None:
                self._session.add(ChatConversationMember(conversation_id=conv.id, user_id=user.id))
                await self._session.flush()
        return await self._conversation_to_response(conv, user)
