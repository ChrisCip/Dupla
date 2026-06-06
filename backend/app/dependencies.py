from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="JWT",
)

_PASSWORD_CHANGE_ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/me"),
        ("POST", "/api/auth/change-password"),
    }
)


def _allows_password_change_pending(method: str, path: str) -> bool:
    return (method.upper(), path) in _PASSWORD_CHANGE_ALLOWED


async def get_auth_service(session: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(session)


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    auth = AuthService(session)
    user = await auth.get_user_for_token(token)
    if user.must_change_password and not _allows_password_change_pending(request.method, request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña antes de continuar",
        )
    return user


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
