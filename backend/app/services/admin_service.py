from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserModule
from app.repositories.module_repository import ModuleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AdminCreateUserRequest
from app.security.password import hash_password


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._modules = ModuleRepository(session)

    async def list_users(self) -> list[User]:
        return list(await self._users.list_all_ordered())

    async def create_user(self, body: AdminCreateUserRequest) -> User:
        existing = await self._users.get_by_email(body.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con este correo",
            )
        seen: set[int] = set()
        for mid in body.module_ids:
            if mid in seen:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="module_ids no debe repetirse",
                )
            seen.add(mid)
            mod = await self._modules.get_by_id(mid)
            if mod is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Módulo {mid} no existe",
                )

        uid = uuid.uuid4()
        user = User(
            id=uid,
            email=body.email,
            password_hash=hash_password(body.password),
            role=body.role,
        )
        self._users.add(user)
        for mid in body.module_ids:
            self._users.add_module_link(UserModule(user_id=uid, module_id=mid))
        await self._session.flush()
        return user
