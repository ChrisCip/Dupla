from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatPostRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get(
    "/messages",
    response_model=list[ChatMessageResponse],
    summary="Mensajes del chat interno",
    description="Sin `after_uuid`, devuelve los últimos mensajes. Con `after_uuid`, los posteriores para sondeo.",
)
async def list_chat_messages(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    after_uuid: Annotated[Optional[UUID], Query(description="UUID del último mensaje conocido")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ChatMessageResponse]:
    svc = ChatService(session)
    return await svc.list_messages(after_uuid, limit)


@router.post(
    "/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje",
)
async def post_chat_message(
    body: ChatPostRequest,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ChatMessageResponse:
    svc = ChatService(session)
    msg = await svc.post_message(current, body)
    await session.commit()
    return msg
