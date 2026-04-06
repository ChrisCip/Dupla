from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_task_operator
from app.models.user import User
from app.schemas.task_board import (
    TaskBoardResponse,
    TaskCardCreateRequest,
    TaskCardPatchRequest,
    TaskCardResponse,
)
from app.services.task_board_service import TaskBoardService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get(
    "/board",
    response_model=TaskBoardResponse,
    summary="Tablero de tareas",
    description="Listas y tarjetas ordenadas. Todos los usuarios autenticados.",
)
async def get_task_board(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskBoardResponse:
    svc = TaskBoardService(session)
    return await svc.get_board()


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
    summary="Actualizar o mover tarjeta",
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
