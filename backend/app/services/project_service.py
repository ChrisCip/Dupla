from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
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
        is_master = user.role == UserRole.MASTER
        return await self._projects.list_for_user(user.id, is_master=is_master)

    async def create_project(self, user: User, body: ProjectCreateRequest) -> Project:
        await self.ensure_architecture_access(user)
        return await self._projects.create_with_architecture(
            name=body.name,
            client_name=body.client_name,
            created_by=user.id,
        )

    async def get_project(self, user: User, project_uuid: UUID) -> Project:
        await self.ensure_architecture_access(user)
        project = await self._projects.get_by_uuid(project_uuid)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    async def get_architecture(self, user: User, project_uuid: UUID) -> Tuple[dict, Optional[datetime]]:
        await self.ensure_architecture_access(user)
        project = await self._projects.get_by_uuid(project_uuid)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
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
        await self.ensure_architecture_access(user)
        project = await self._projects.get_by_uuid(project_uuid)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
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
