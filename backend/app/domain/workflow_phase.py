from __future__ import annotations

from enum import StrEnum


class WorkflowPhase(StrEnum):
    BOOTSTRAPPING = "BOOTSTRAPPING"
    AWAITING_FILES = "AWAITING_FILES"
    FILES_INGESTED = "FILES_INGESTED"
    ARCHITECTURE_REVIEW = "ARCHITECTURE_REVIEW"
    SPECIFICATIONS = "SPECIFICATIONS"
    BUDGETING_PIPELINE = "BUDGETING_PIPELINE"
    MANAGEMENT_APPROVAL = "MANAGEMENT_APPROVAL"
    BUDGET_APPROVED = "BUDGET_APPROVED"


# Linear primary path (valid single-step transitions)
LINEAR_NEXT: dict[WorkflowPhase, WorkflowPhase] = {
    WorkflowPhase.BOOTSTRAPPING: WorkflowPhase.AWAITING_FILES,
    WorkflowPhase.AWAITING_FILES: WorkflowPhase.FILES_INGESTED,
    WorkflowPhase.FILES_INGESTED: WorkflowPhase.ARCHITECTURE_REVIEW,
    WorkflowPhase.ARCHITECTURE_REVIEW: WorkflowPhase.SPECIFICATIONS,
    WorkflowPhase.SPECIFICATIONS: WorkflowPhase.BUDGETING_PIPELINE,
    WorkflowPhase.BUDGETING_PIPELINE: WorkflowPhase.MANAGEMENT_APPROVAL,
    WorkflowPhase.MANAGEMENT_APPROVAL: WorkflowPhase.BUDGET_APPROVED,
}

# Paso inverso (una fase atrás); no incluye BOOTSTRAPPING como destino implícito en el mapa de "desde"
LINEAR_PREV: dict[WorkflowPhase, WorkflowPhase] = {v: k for k, v in LINEAR_NEXT.items()}
