from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.project_lifecycle import UserNotificationResponse
from app.services.project_lifecycle_service import ProjectLifecycleService

router = APIRouter(prefix="/api", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
    description="Returns the authenticated user's public data (UUID, email, role). Requires Bearer JWT.",
)
async def read_me(current: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.from_user(current)


@router.get(
    "/me/notifications",
    response_model=list[UserNotificationResponse],
    summary="Notificaciones del usuario",
)
async def list_my_notifications(
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    unread_only: Annotated[bool, Query()] = False,
) -> list[UserNotificationResponse]:
    svc = ProjectLifecycleService(session)
    rows = await svc.list_my_notifications(current, unread_only=unread_only)
    return [UserNotificationResponse.from_row(r) for r in rows]


@router.patch(
    "/me/notifications/{notification_uuid}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Marcar notificación como leída",
)
async def mark_notification_read(
    notification_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    svc = ProjectLifecycleService(session)
    await svc.mark_notification_read(current, notification_uuid)
    await session.commit()
