from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.architecture import ArchitectureDataResponse, ArchitectureDocumentPayload
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.services.export_service import ExportService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects",
    description="MASTER sees all projects; others see projects they created.",
)
async def list_projects(
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProjectResponse]:
    svc = ProjectService(session)
    rows = await svc.list_projects(current)
    return [ProjectResponse.from_project(p) for p in rows]


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Creates a project and empty architecture document. Requires Architecture module access.",
)
async def create_project(
    body: ProjectCreateRequest,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    svc = ProjectService(session)
    project = await svc.create_project(current, body)
    await session.commit()
    return ProjectResponse.from_project(project)


@router.get(
    "/{project_uuid}",
    response_model=ProjectResponse,
    summary="Get project",
    description="Returns project metadata by UUID. Requires Architecture module access.",
    responses={404: {"description": "Project not found"}, 403: {"description": "No module access"}},
)
async def get_project(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    svc = ProjectService(session)
    project = await svc.get_project(current, project_uuid)
    return ProjectResponse.from_project(project)


@router.get(
    "/{project_uuid}/architecture",
    response_model=ArchitectureDataResponse,
    summary="Get architecture workspace data",
    description="Returns groups/items and materiales JSON for the project.",
    responses={404: {"description": "Project not found"}, 403: {"description": "No module access"}},
)
async def get_architecture(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ArchitectureDataResponse:
    svc = ProjectService(session)
    raw, updated = await svc.get_architecture(current, project_uuid)
    doc = ArchitectureDocumentPayload.model_validate(raw)
    updated_str = updated.isoformat() if isinstance(updated, datetime) else None
    return ArchitectureDataResponse(
        project_uuid=project_uuid,
        document=doc,
        updated_at=updated_str,
    )


@router.put(
    "/{project_uuid}/architecture",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Replace architecture workspace data",
    description="Full document replace for groups and materiales.",
    responses={404: {"description": "Project not found"}, 403: {"description": "No module access"}},
)
async def put_architecture(
    project_uuid: UUID,
    body: ArchitectureDocumentPayload,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ProjectService(session)
    await svc.put_architecture(current, project_uuid, body)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_uuid}/exports/pliego.xlsx",
    summary="Export Pliego (Excel)",
    description="Pliego GA-FO-01: usa plantilla en app/templates/ si existe; nombre de archivo sugerido en Content-Disposition.",
    responses={404: {"description": "Project not found"}},
)
async def export_pliego_xlsx(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ExportService(session)
    data, filename = await svc.export_pliego_xlsx(current, project_uuid)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{project_uuid}/exports/control-planos.xlsx",
    summary="Export Control Entrega Planos (Excel)",
    description="Downloads control de planos as XLSX.",
    responses={404: {"description": "Project not found"}},
)
async def export_control_xlsx(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ExportService(session)
    data = await svc.export_control_xlsx(current, project_uuid)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="control-planos-{project_uuid}.xlsx"'},
    )


@router.get(
    "/{project_uuid}/exports/pliego.pdf",
    summary="Export Pliego (PDF)",
)
async def export_pliego_pdf(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ExportService(session)
    data = await svc.export_pliego_pdf(current, project_uuid)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="pliego-{project_uuid}.pdf"'},
    )


@router.get(
    "/{project_uuid}/exports/control-planos.pdf",
    summary="Export Control Planos (PDF)",
)
async def export_control_pdf(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ExportService(session)
    data = await svc.export_control_pdf(current, project_uuid)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="control-planos-{project_uuid}.pdf"'},
    )
