from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_master
from app.models.user import User
from app.schemas.admin import AdminCreateUserRequest
from app.schemas.auth import UserResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Listar usuarios",
    description="Solo rol MASTER. No incluye contraseñas.",
)
async def list_users_admin(
    _: Annotated[User, Depends(require_master)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserResponse]:
    svc = AdminService(session)
    users = await svc.list_users()
    return [UserResponse.from_user(u) for u in users]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea credenciales y asigna módulos. Solo MASTER.",
)
async def create_user_admin(
    body: AdminCreateUserRequest,
    _: Annotated[User, Depends(require_master)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    svc = AdminService(session)
    user = await svc.create_user(body)
    await session.commit()
    return UserResponse.from_user(user)
