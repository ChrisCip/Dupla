from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import Project


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: str | None = Field(default=None, max_length=255)


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    client_name: str | None
    status: str

    @classmethod
    def from_project(cls, project: Project) -> ProjectResponse:
        return cls(
            uuid=project.id,
            name=project.name,
            client_name=project.client_name,
            status=project.status,
        )
