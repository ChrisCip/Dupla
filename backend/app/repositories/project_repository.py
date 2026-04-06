from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.bootstrap_defaults import default_bootstrap_criteria
from app.domain.workflow_phase import WorkflowPhase
from app.models.project import Project, ProjectArchitectureData
from app.models.project_event import ProjectEvent
from app.models.project_file import ProjectFile


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
            stmt = stmt.where(Project.created_by == user_uuid)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

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
