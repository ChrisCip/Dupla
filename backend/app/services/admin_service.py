from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserModule, UserRole
from app.repositories.module_repository import ModuleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminImportCreatedUser,
    AdminImportErrorRow,
    AdminImportSkippedUser,
    AdminImportUserRow,
    AdminImportUsersResponse,
    AdminUpdateUserRequest,
)
from app.security.password import hash_password
from app.security.temporary_password import generate_temporary_password


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
            first_name=body.first_name,
            last_name=body.last_name,
            password_hash=hash_password(body.password),
            role=body.role,
        )
        self._users.add(user)
        for mid in body.module_ids:
            self._users.add_module_link(UserModule(user_id=uid, module_id=mid))
        await self._session.flush()
        await self._session.refresh(user, attribute_names=["modules"])
        return user

    async def import_users(self, rows: list[AdminImportUserRow]) -> AdminImportUsersResponse:
        created: list[AdminImportCreatedUser] = []
        skipped: list[AdminImportSkippedUser] = []
        errors: list[AdminImportErrorRow] = []
        seen_emails: set[str] = set()

        for row in rows:
            email_key = row.email.lower()
            if email_key in seen_emails:
                errors.append(
                    AdminImportErrorRow(
                        email=row.email,
                        detail="Correo duplicado en la importación",
                    )
                )
                continue
            seen_emails.add(email_key)

            existing = await self._users.get_by_email(row.email)
            if existing is not None:
                skipped.append(
                    AdminImportSkippedUser(
                        email=row.email,
                        reason="Ya existe un usuario con este correo",
                    )
                )
                continue

            password = generate_temporary_password()
            try:
                user = await self.create_user(
                    AdminCreateUserRequest(
                        email=row.email,
                        first_name=row.first_name,
                        last_name=row.last_name,
                        password=password,
                        role=row.role,
                        module_ids=row.module_ids,
                    )
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else "No se pudo crear el usuario"
                errors.append(AdminImportErrorRow(email=row.email, detail=detail))
                continue

            created.append(
                AdminImportCreatedUser(
                    uuid=str(user.id),
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=user.role,
                    password=password,
                )
            )

        return AdminImportUsersResponse(created=created, skipped=skipped, errors=errors)

    async def update_user(self, user_uuid: uuid.UUID, body: AdminUpdateUserRequest) -> User:
        user = await self._users.get_by_uuid(user_uuid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        if body.email != user.email:
            existing = await self._users.get_by_email(body.email)
            if existing is not None and existing.id != user.id:
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

        user.email = body.email
        user.first_name = body.first_name
        user.last_name = body.last_name
        user.role = body.role
        if body.password:
            user.password_hash = hash_password(body.password)

        await self._users.delete_module_links_for_user(user.id)
        for mid in body.module_ids:
            self._users.add_module_link(UserModule(user_id=user.id, module_id=mid))
        await self._session.flush()
        await self._session.refresh(user, attribute_names=["modules"])
        return user

    async def delete_user(self, actor_uuid: uuid.UUID, user_uuid: uuid.UUID) -> None:
        if actor_uuid == user_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes eliminar tu propia cuenta",
            )

        user = await self._users.get_by_uuid(user_uuid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.role == UserRole.GERENCIA:
            gerencia_count = await self._users.count_by_role(UserRole.GERENCIA)
            if gerencia_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar el último usuario con rol Gerencia",
                )

        await self._users.clear_blocking_references(user.id)
        await self._users.delete(user)
        await self._session.flush()
