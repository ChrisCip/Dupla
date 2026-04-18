from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.project import Project


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    client_name: Optional[str]
    project_kind: str
    status: str
    workflow_phase: str
    workflow_meta: dict[str, Any]
    project_bootstrap_criteria: list[Any]
    specifications_document: dict[str, Any]
    created_by_user_uuid: Optional[UUID] = None
    updated_at: datetime

    @classmethod
    def from_project(cls, project: Project) -> ProjectResponse:
        return cls(
            uuid=project.id,
            name=project.name,
            client_name=project.client_name,
            project_kind=project.project_kind,
            status=project.status,
            workflow_phase=project.workflow_phase,
            workflow_meta=project.workflow_meta or {},
            project_bootstrap_criteria=project.project_bootstrap_criteria or [],
            specifications_document=project.specifications_document or {},
            created_by_user_uuid=project.created_by,
            updated_at=project.updated_at,
        )


class ProjectMemberEntry(BaseModel):
    uuid: UUID
    email: EmailStr
    first_name: str
    last_name: str


class ProjectMembersPutRequest(BaseModel):
    member_user_uuids: list[UUID] = Field(default_factory=list)
