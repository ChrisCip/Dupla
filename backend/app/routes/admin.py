from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_elevated_access, require_gerencia
from app.models.user import User
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminImportUsersRequest,
    AdminImportUsersResponse,
    AdminUpdateUserRequest,
)
from app.schemas.auth import UserResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Listar usuarios",
    description="Gerencia o Líder de equipo. Incluye módulos asignados.",
)
async def list_users_admin(
    _: Annotated[User, Depends(require_elevated_access)],
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
    description="Crea credenciales y asigna módulos. Solo Gerencia.",
)
async def create_user_admin(
    body: AdminCreateUserRequest,
    _: Annotated[User, Depends(require_gerencia)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    svc = AdminService(session)
    user = await svc.create_user(body)
    await session.commit()
    return UserResponse.from_user(user)


@router.post(
    "/users/import",
    response_model=AdminImportUsersResponse,
    summary="Importar usuarios",
    description="Crea usuarios en lote con contraseña temporal generada. Solo Gerencia.",
)
async def import_users_admin(
    body: AdminImportUsersRequest,
    _: Annotated[User, Depends(require_gerencia)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminImportUsersResponse:
    svc = AdminService(session)
    result = await svc.import_users(body.users)
    await session.commit()
    return result


@router.patch(
    "/users/{user_uuid}",
    response_model=UserResponse,
    summary="Actualizar usuario",
    description="Correo, rol, módulos y opcionalmente contraseña. Gerencia o Líder de equipo.",
)
async def update_user_admin(
    user_uuid: UUID,
    body: AdminUpdateUserRequest,
    actor: Annotated[User, Depends(require_elevated_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    svc = AdminService(session)
    user = await svc.update_user(actor, user_uuid, body)
    await session.commit()
    return UserResponse.from_user(user)


@router.delete(
    "/users/{user_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Elimina credenciales y datos asociados en cascada. Gerencia o Líder de equipo.",
    responses={
        400: {"description": "No se puede eliminar (cuenta propia o último Gerencia)"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def delete_user_admin(
    user_uuid: UUID,
    actor: Annotated[User, Depends(require_elevated_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    svc = AdminService(session)
    await svc.delete_user(actor.id, user_uuid)
    await session.commit()
