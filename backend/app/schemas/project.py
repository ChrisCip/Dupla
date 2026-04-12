from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.project import Project


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: Optional[str] = Field(default=None, max_length=255)


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    client_name: Optional[str]
    status: str
    workflow_phase: str
    workflow_meta: dict[str, Any]
    project_bootstrap_criteria: list[Any]
    specifications_document: dict[str, Any]
    created_by_user_uuid: Optional[UUID] = None

    @classmethod
    def from_project(cls, project: Project) -> ProjectResponse:
        return cls(
            uuid=project.id,
            name=project.name,
            client_name=project.client_name,
            status=project.status,
            workflow_phase=project.workflow_phase,
            workflow_meta=project.workflow_meta or {},
            project_bootstrap_criteria=project.project_bootstrap_criteria or [],
            specifications_document=project.specifications_document or {},
            created_by_user_uuid=project.created_by,
        )


class ProjectMemberEntry(BaseModel):
    uuid: UUID
    email: EmailStr


class ProjectMembersPutRequest(BaseModel):
    member_user_uuids: list[UUID] = Field(default_factory=list)
