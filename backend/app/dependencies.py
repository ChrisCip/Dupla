from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="JWT",
)


async def get_auth_service(session: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    auth = AuthService(session)
    return await auth.get_user_for_token(token)


async def require_gerencia(current: Annotated[User, Depends(get_current_user)]) -> User:
    if current.role != UserRole.GERENCIA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol Gerencia",
        )
    return current


async def require_task_creator(current: Annotated[User, Depends(get_current_user)]) -> User:
    if current.role not in (
        UserRole.GERENCIA,
        UserRole.CONTROL,
        UserRole.PRESUPUESTO,
        UserRole.ARQUITECTURA,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )
    return current


async def require_task_operator(current: Annotated[User, Depends(get_current_user)]) -> User:
    if current.role not in (
        UserRole.GERENCIA,
        UserRole.CONTROL,
        UserRole.PRESUPUESTO,
        UserRole.ARQUITECTURA,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )
    return current
