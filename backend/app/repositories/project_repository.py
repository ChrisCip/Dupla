from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectArchitectureData


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_uuid: UUID, *, is_master: bool) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc())
        if not is_master:
            stmt = stmt.where(Project.created_by == user_uuid)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_uuid(self, project_uuid: UUID) -> Project | None:
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
        client_name: str | None,
        created_by: UUID,
    ) -> Project:
        project = Project(
            name=name,
            client_name=client_name,
            created_by=created_by,
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
        await self._session.refresh(project, ["architecture_data"])
        return project

    async def save_architecture(
        self,
        project_uuid: UUID,
        document: dict,
        materiales: list,
        user_uuid: UUID,
    ) -> ProjectArchitectureData | None:
        result = await self._session.execute(
            select(ProjectArchitectureData).where(ProjectArchitectureData.project_id == project_uuid)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.document = document
        row.materiales = materiales
        row.last_updated_by = user_uuid
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return row
