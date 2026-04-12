import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.bootstrap_defaults import default_bootstrap_criteria
from app.domain.workflow_phase import WorkflowPhase
from app.models.project import Project, ProjectArchitectureData
from app.models.project_event import ProjectEvent
from app.models.project_file import ProjectFile
from app.models.project_member import ProjectMember
from app.models.user import User, UserRole


def _default_workflow_meta() -> dict[str, Any]:
    return {
        "budget_pipeline": {
            "subcontracts_done": False,
            "volumetry_done": False,
            "cost_analysis_done": False,
            "budget_marked_complete": False,
            "client_approved_version_label": None,
            "volumetry": {},
            "cost_analysis": {},
            "budget_versions": [],
        }
    }


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_uuid: UUID, *, is_master: bool) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc())
        if not is_master:
            member_projects = select(ProjectMember.project_id).where(ProjectMember.user_id == user_uuid)
            stmt = stmt.where(or_(Project.created_by == user_uuid, Project.id.in_(member_projects)))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_project_member(self, project_id: UUID, user_id: UUID) -> bool:
        q = select(ProjectMember.id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        return (await self._session.execute(q)).scalar_one_or_none() is not None

    async def user_has_access_to_project(self, user: User, project: Project) -> bool:
        if user.role == UserRole.MASTER:
            return True
        if project.created_by is not None and project.created_by == user.id:
            return True
        return await self.is_project_member(project.id, user.id)

    async def add_project_member(self, project_id: UUID, user_id: UUID) -> None:
        if await self.is_project_member(project_id, user_id):
            return
        self._session.add(
            ProjectMember(id=uuid.uuid4(), project_id=project_id, user_id=user_id),
        )
        await self._session.flush()

    async def replace_project_members(self, project_id: UUID, user_ids: set[UUID]) -> None:
        await self._session.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))
        for uid in user_ids:
            self._session.add(ProjectMember(id=uuid.uuid4(), project_id=project_id, user_id=uid))
        await self._session.flush()

    async def list_project_members_with_emails(self, project_id: UUID) -> list[tuple[UUID, str]]:
        q = (
            select(User.id, User.email)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.email)
        )
        rows = (await self._session.execute(q)).all()
        return [(r[0], r[1]) for r in rows]

    async def get_by_uuid(self, project_uuid: UUID) -> Optional[Project]:
        result = await self._session.execute(
            select(Project)
            .options(selectinload(Project.architecture_data))
            .where(Project.id == project_uuid)
        )
        return result.scalar_one_or_none()

    async def create_with_architecture(
        self,
        *,
        name: str,
        client_name: Optional[str],
        created_by: UUID,
    ) -> Project:
        project = Project(
            name=name,
            client_name=client_name,
            created_by=created_by,
            workflow_phase=WorkflowPhase.BOOTSTRAPPING.value,
            workflow_meta=_default_workflow_meta(),
            project_bootstrap_criteria=default_bootstrap_criteria(),
            specifications_document={},
        )
        self._session.add(project)
        await self._session.flush()
        arch = ProjectArchitectureData(
            project_id=project.id,
            document={"groups": []},
            materiales=[],
            last_updated_by=created_by,
        )
        self._session.add(arch)
        await self._session.flush()
        await self.add_project_member(project.id, created_by)
        await self._session.refresh(project, ["architecture_data"])
        return project

    async def save_architecture(
        self,
        project_uuid: UUID,
        document: dict,
        materiales: list,
        user_uuid: UUID,
    ) -> Optional[ProjectArchitectureData]:
        result = await self._session.execute(
            select(ProjectArchitectureData).where(ProjectArchitectureData.project_id == project_uuid)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.document = document
        row.materiales = materiales
        row.last_updated_by = user_uuid
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def record_event(
        self,
        *,
        project_id: UUID,
        actor_user_id: Optional[UUID],
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        ev = ProjectEvent(
            project_id=project_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(ev)
        await self._session.flush()

    async def count_project_files(self, project_id: UUID) -> int:
        q = select(func.count()).select_from(ProjectFile).where(ProjectFile.project_id == project_id)
        return int((await self._session.execute(q)).scalar_one())
