from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_gerencia
from app.domain.task_board_constants import TASK_LIST_DONE_UUID
from app.domain.workflow_phase import WorkflowPhase
from app.models.project import Project
from app.models.task_board import TaskCard
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardSummaryResponse(BaseModel):
    projects_by_phase: dict[str, int]
    pending_task_cards: int
    projects_past_deadline: int


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    current: Annotated[User, Depends(require_gerencia)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardSummaryResponse:
    del current
    q_ph = select(Project.workflow_phase, func.count()).group_by(Project.workflow_phase)
    phase_rows = (await session.execute(q_ph)).all()
    projects_by_phase = {str(r[0]): int(r[1]) for r in phase_rows}

    q_tasks = select(func.count()).select_from(TaskCard).where(
        TaskCard.archived.is_(False),
        TaskCard.list_id != TASK_LIST_DONE_UUID,
    )
    pending_task_cards = int((await session.execute(q_tasks)).scalar_one() or 0)

    today = date.today()
    q_late = select(func.count()).select_from(Project).where(
        Project.deadline.isnot(None),
        Project.deadline < today,
        Project.workflow_phase != WorkflowPhase.COMPLETE.value,
    )
    projects_past_deadline = int((await session.execute(q_late)).scalar_one() or 0)

    return DashboardSummaryResponse(
        projects_by_phase=projects_by_phase,
        pending_task_cards=pending_task_cards,
        projects_past_deadline=projects_past_deadline,
    )
