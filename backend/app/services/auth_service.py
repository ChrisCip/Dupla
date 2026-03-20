from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.security.jwt_tokens import create_access_token, decode_token_subject
from app.security.password import verify_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> str:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return create_access_token(user.id)

    async def get_user_for_token(self, token: str):
        user_uuid = decode_token_subject(token)
        if user_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self._users.get_by_uuid(user_uuid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
