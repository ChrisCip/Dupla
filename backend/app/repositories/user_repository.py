from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserModule


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_uuid(self, user_uuid: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_uuid))
        return result.scalar_one_or_none()

    async def has_module(self, user_uuid: UUID, module_id: int) -> bool:
        result = await self._session.execute(
            select(UserModule).where(
                UserModule.user_id == user_uuid,
                UserModule.module_id == module_id,
            )
        )
        return result.scalar_one_or_none() is not None
