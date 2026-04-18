from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.project_updated import touch_project_updated_at
from app.models.project import Project
from app.models.user import User, UserRole
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.architecture import ArchitectureDocumentPayload
from app.schemas.project import ProjectCreateRequest

settings = get_settings()


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self._projects = ProjectRepository(session)
        self._users = UserRepository(session)

    async def ensure_architecture_access(self, user: User) -> None:
        ok = await self._users.has_module(user.id, settings.architecture_module_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to the Architecture module",
            )

    async def list_projects(self, user: User) -> list[Project]:
        await self.ensure_architecture_access(user)
        is_master = user.role == UserRole.GERENCIA
        return await self._projects.list_for_user(user.id, is_master=is_master)

    async def create_project(self, user: User, body: ProjectCreateRequest) -> Project:
        await self.ensure_architecture_access(user)
        if user.role != UserRole.GERENCIA:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo Gerencia puede crear proyectos",
            )
        project = await self._projects.create_with_architecture(
            name=body.name,
            client_name=body.client_name,
            created_by=user.id,
        )
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="PROJECT_CREATED",
            payload={"name": project.name, "client_name": project.client_name},
        )
        if body.member_user_uuids is not None:
            await self.set_project_members(user, project.id, body.member_user_uuids)
        return project

    async def get_project(self, user: User, project_uuid: UUID) -> Project:
        await self.ensure_architecture_access(user)
        project = await self._projects.get_by_uuid(project_uuid)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not await self._projects.user_has_access_to_project(user, project):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    async def list_project_members(self, user: User, project_uuid: UUID) -> list[tuple[UUID, str]]:
        project = await self.get_project(user, project_uuid)
        return await self._projects.list_project_members_with_emails(project.id)

    async def set_project_members(self, master: User, project_uuid: UUID, member_user_uuids: list[UUID]) -> None:
        if master.role != UserRole.GERENCIA:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo Gerencia puede configurar quién ve el proyecto",
            )
        project = await self.get_project(master, project_uuid)
        ids = set(member_user_uuids)
        if project.created_by is not None:
            ids.add(project.created_by)
        for uid in ids:
            u = await self._users.get_by_uuid(uid)
            if u is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uno o más usuarios no existen",
                )
            if not await self._users.has_module(uid, settings.architecture_module_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Todos los miembros deben tener acceso al módulo Arquitectura",
                )
        await self._projects.replace_project_members(project.id, ids)
        pairs = await self._projects.list_project_members_with_emails(project.id)
        member_payload: list[dict[str, Any]] = [
            {"user_uuid": str(u), "email": e} for u, e in sorted(pairs, key=lambda x: x[1].lower())
        ]
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=master.id,
            event_type="PROJECT_MEMBERS_UPDATED",
            payload={"member_count": len(member_payload), "members": member_payload},
        )
        touch_project_updated_at(project)

    async def get_architecture(self, user: User, project_uuid: UUID) -> Tuple[dict, Optional[datetime]]:
        project = await self.get_project(user, project_uuid)
        if project.architecture_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Architecture data missing")
        doc = project.architecture_data.document or {}
        if "groups" not in doc:
            doc = {"groups": doc.get("groups", [])}
        materiales = project.architecture_data.materiales or []
        payload = {"groups": doc.get("groups", []), "materiales": materiales}
        return payload, project.architecture_data.updated_at

    async def put_architecture(
        self,
        user: User,
        project_uuid: UUID,
        payload: ArchitectureDocumentPayload,
    ) -> None:
        project = await self.get_project(user, project_uuid)
        groups = [g.model_dump(mode="json") for g in payload.groups]
        materiales = [m.model_dump(mode="json") for m in payload.materiales]
        document = {"groups": groups}
        row = await self._projects.save_architecture(
            project_uuid,
            document=document,
            materiales=materiales,
            user_uuid=user.id,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Architecture data missing")
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="ARCHITECTURE_SAVED",
            payload={"groups_count": len(groups), "materiales_count": len(materiales)},
        )
