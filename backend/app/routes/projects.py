import json
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_gerencia
from app.domain.project_kind import ProjectKind
from app.models.user import User
from app.schemas.architecture import ArchitectureDataResponse, ArchitectureDocumentPayload
from app.schemas.plan_delivery import (
    PlanDeliveryRequestCreate,
    PlanDeliveryRequestPatch,
    PlanDeliveryRequestResponse,
)
from app.schemas.project import (
    ProjectMemberEntry,
    ProjectMembersPutRequest,
    ProjectResponse,
)
from app.services.export_service import ExportService
from app.services.plan_delivery_service import PlanDeliveryService
from app.services.project_lifecycle_service import ProjectLifecycleService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects",
    description="Gerencia ve todos los proyectos; el resto ve los que creó o le compartieron.",
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
    description=(
        "Multipart: name, client_name opcional, project_kind (RESIDENTIAL|TENDER), "
        "member_user_uuids opcional como JSON string de UUIDs, files opcional (múltiples). "
        "Licitación (TENDER): fase inicial revisión de arquitectura y obligatorio al menos un archivo."
    ),
)
async def create_project(
    current: Annotated[User, Depends(require_gerencia)],
    session: Annotated[AsyncSession, Depends(get_db)],
    name: str = Form(...),
    client_name: Optional[str] = Form(None),
    project_kind: str = Form("RESIDENTIAL"),
    member_user_uuids: Optional[str] = Form(
        None,
        description='JSON array de UUIDs, ej. ["uuid1","uuid2"]',
    ),
    files: Annotated[Optional[list[UploadFile]], File()] = None,
) -> ProjectResponse:
    try:
        kind = ProjectKind(project_kind.strip().upper())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="project_kind debe ser RESIDENTIAL o TENDER",
        ) from e
    members: Optional[list[UUID]] = None
    if member_user_uuids is not None and member_user_uuids.strip():
        try:
            raw = json.loads(member_user_uuids)
            if not isinstance(raw, list):
                raise ValueError("not a list")
            members = [UUID(str(x)) for x in raw]
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="member_user_uuids debe ser un JSON array de UUIDs",
            ) from e
    file_list = files if files is not None else []
    svc = ProjectService(session)
    lifecycle = ProjectLifecycleService(session)
    project = await svc.create_project(
        current,
        name=name,
        client_name=client_name,
        project_kind=kind,
        member_user_uuids=members,
        files=file_list,
    )
    for upload in file_list:
        if not getattr(upload, "filename", None):
            continue
        await lifecycle.upload_file(current, project.id, upload, None)
    await session.commit()
    await session.refresh(project)
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
    "/{project_uuid}/members",
    response_model=list[ProjectMemberEntry],
    summary="Miembros con acceso al proyecto",
    description="Usuarios que pueden abrir el proyecto (además del creador). Gerencia y miembros pueden listar.",
)
async def list_project_members(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProjectMemberEntry]:
    svc = ProjectService(session)
    rows = await svc.list_project_members(current, project_uuid)
    return [ProjectMemberEntry(uuid=u, email=e, first_name=fn, last_name=ln) for u, e, fn, ln in rows]


@router.put(
    "/{project_uuid}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Configurar miembros del proyecto",
    description="Solo Gerencia. El creador del proyecto siempre permanece con acceso.",
)
async def put_project_members(
    project_uuid: UUID,
    body: ProjectMembersPutRequest,
    current: Annotated[User, Depends(require_gerencia)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = ProjectService(session)
    await svc.set_project_members(current, project_uuid, body.member_user_uuids)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    "/{project_uuid}/plan-delivery-requests",
    response_model=list[PlanDeliveryRequestResponse],
    summary="Control entrega de planos — listar solicitudes",
)
async def list_plan_delivery_requests(
    project_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlanDeliveryRequestResponse]:
    svc = PlanDeliveryService(session)
    return await svc.list_rows(current, project_uuid)


@router.post(
    "/{project_uuid}/plan-delivery-requests",
    response_model=PlanDeliveryRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Control entrega de planos — nueva solicitud (SDP n+1)",
)
async def create_plan_delivery_request(
    project_uuid: UUID,
    body: PlanDeliveryRequestCreate,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanDeliveryRequestResponse:
    svc = PlanDeliveryService(session)
    return await svc.create_row(current, project_uuid, body)


@router.patch(
    "/{project_uuid}/plan-delivery-requests/{row_uuid}",
    response_model=PlanDeliveryRequestResponse,
    summary="Control entrega de planos — actualizar solicitud",
)
async def patch_plan_delivery_request(
    project_uuid: UUID,
    row_uuid: UUID,
    body: PlanDeliveryRequestPatch,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanDeliveryRequestResponse:
    svc = PlanDeliveryService(session)
    return await svc.patch_row(current, project_uuid, row_uuid, body)


@router.delete(
    "/{project_uuid}/plan-delivery-requests/{row_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Control entrega de planos — eliminar solicitud",
)
async def delete_plan_delivery_request(
    project_uuid: UUID,
    row_uuid: UUID,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = PlanDeliveryService(session)
    await svc.delete_row(current, project_uuid, row_uuid)
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
