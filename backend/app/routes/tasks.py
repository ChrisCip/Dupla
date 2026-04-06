from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_task_operator
from app.models.user import User
from app.schemas.task_board import (
    TaskAssigneeOption,
    TaskBoardResponse,
    TaskCardCreateRequest,
    TaskCardPatchRequest,
    TaskCardResponse,
)
from app.services.task_board_service import TaskBoardService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get(
    "/assignees",
    response_model=list[TaskAssigneeOption],
    summary="Usuarios asignables",
    description="Usuarios con acceso al módulo Arquitectura (para asignar tareas).",
)
async def list_task_assignees(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaskAssigneeOption]:
    svc = TaskBoardService(session)
    return await svc.list_assignees()


@router.get(
    "/board",
    response_model=TaskBoardResponse,
    summary="Tablero de tareas",
    description=(
        "Listas activas (sin archivadas). Query `mine=1` filtra por asignado = usuario actual; "
        "`assignee_uuid` filtra por otro usuario. `include_archived=1` añade `archived_cards`."
    ),
)
async def get_task_board(
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    include_archived: Annotated[bool, Query(description="Incluir lista de tarjetas archivadas")] = False,
    mine: Annotated[bool, Query(description="Solo tareas asignadas a mí")] = False,
    assignee_uuid: Annotated[
        Optional[UUID],
        Query(description="Filtrar por usuario asignado (UUID)"),
    ] = None,
    project_uuid: Annotated[
        Optional[UUID],
        Query(description="Filtrar tarjetas vinculadas a un proyecto"),
    ] = None,
) -> TaskBoardResponse:
    svc = TaskBoardService(session)
    return await svc.get_board(
        viewer=current,
        include_archived=include_archived,
        mine=mine,
        filter_assignee=assignee_uuid,
        filter_project=project_uuid,
    )


@router.post(
    "/cards",
    response_model=TaskCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tarjeta",
    description="COORDINATOR y WORKER. MASTER solo lectura.",
)
async def create_task_card(
    body: TaskCardCreateRequest,
    current: Annotated[User, Depends(require_task_operator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskCardResponse:
    svc = TaskBoardService(session)
    card = await svc.create_card(current, body)
    await session.commit()
    return TaskCardResponse.from_card(card)


@router.patch(
    "/cards/{card_uuid}",
    response_model=TaskCardResponse,
    summary="Actualizar, mover, archivar o asignar tarjeta",
    description="COORDINATOR y WORKER. MASTER solo lectura.",
)
async def patch_task_card(
    card_uuid: UUID,
    body: TaskCardPatchRequest,
    _: Annotated[User, Depends(require_task_operator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskCardResponse:
    svc = TaskBoardService(session)
    card = await svc.patch_card(card_uuid, body)
    await session.commit()
    return TaskCardResponse.from_card(card)
