from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserModule, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_uuid(self, user_uuid: UUID) -> Optional[User]:
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

    async def list_all_ordered(self) -> Sequence[User]:
        result = await self._session.execute(select(User).order_by(User.email))
        return result.scalars().all()

    def add(self, user: User) -> None:
        self._session.add(user)

    def add_module_link(self, link: UserModule) -> None:
        self._session.add(link)

    async def list_ids_by_module_and_roles(
        self,
        module_id: int,
        roles: list[UserRole],
    ) -> list[UUID]:
        if not roles:
            return []
        q = (
            select(User.id)
            .join(UserModule, UserModule.user_id == User.id)
            .where(UserModule.module_id == module_id, User.role.in_(roles))
        )
        rows = (await self._session.execute(q)).scalars().all()
        return list(rows)
