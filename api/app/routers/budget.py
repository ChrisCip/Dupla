from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.services.budget_service import BudgetBuildError, compute_budget_for_job

logger = logging.getLogger("dupla.api.budget")

router = APIRouter(prefix="/projects", tags=["budget"])


def _map_budget_error(exc: BudgetBuildError) -> HTTPException:
    code = exc.code
    if code == "not_found":
        return HTTPException(status_code=404, detail=exc.message)
    if code == "job_not_ready":
        return HTTPException(status_code=409, detail=exc.message)
    if code == "bc3_missing":
        return HTTPException(status_code=500, detail=exc.message)
    if code in ("no_normalized_json", "normalized_missing", "invalid_normalized_json"):
        return HTTPException(status_code=500, detail=exc.message)
    return HTTPException(status_code=500, detail=exc.message)


@router.post("/{job_id}/budget")
def post_project_budget(job_id: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return compute_budget_for_job(
            job_id,
            job_data_dir=settings.job_data_dir,
            bc3_catalog_path=settings.bc3_catalog_path,
            pres_xlsx_path=settings.pres_xlsx_path,
        )
    except BudgetBuildError as exc:
        raise _map_budget_error(exc) from exc
    except Exception:
        logger.exception("Budget build failed for job %s", job_id)
        raise HTTPException(status_code=500, detail="Budget computation failed") from None
