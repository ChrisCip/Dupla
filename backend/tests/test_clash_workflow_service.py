"""Tests for clash workflow tenancy, ingest visibility, and service wiring."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.routing import APIRoute

from app.models.project_clash_job import ProjectClashJob
from app.routes import clash_workflow as clash_workflow_routes
from app.services.clash_service import ClashService
from app.services.clash_export_service import ClashExportService
from app.services.clash_workflow_service import (
    WORKFLOW_INGEST_RESULT_KEY,
    ClashWorkflowService,
    apply_workflow_ingest_result,
    workflow_ingest_result,
)


def _sample_primary_artifacts() -> dict:
    primary = {
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": ["ARQ-PLANTA.dwg", "EST-LOSAS.dwg"],
                "level_id": "P1",
                "member_count": 1,
                "plan_bounds_mm": [148000, -163000, 158000, -154000],
                "plan_centroid_mm": [153000, -158500],
                "representative_conflict": {
                    "discipline_a": "ARQUITECTURA",
                    "discipline_b": "ESTRUCTURA",
                    "clash_type": "HARD",
                    "overlap_depth_z_mm": 180.0,
                    "plan_intersection_area_mm2": 50_000.0,
                    "raw_layers": ["ARQ_MURO", "EST_LOSA"],
                },
                "confidence": "high",
            }
        ]
    }
    return {
        "primary_incidents": json.dumps(primary),
    }


def test_clash_workflow_service_requires_workspace_id():
    session = MagicMock()
    workspace_id = uuid.uuid4()
    svc = ClashWorkflowService(session, workspace_id)
    assert svc._workspace_id == workspace_id
    assert svc._clash_svc._workspace_id == workspace_id
    assert svc._project_svc._workspace_id == workspace_id


def test_clash_workflow_service_rejects_missing_workspace_id():
    with pytest.raises(TypeError):
        ClashWorkflowService(MagicMock())  # type: ignore[call-arg]


def test_apply_workflow_ingest_result_ok():
    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="rq-1",
        status="completed",
        result={"report": {"ok": True}},
    )
    apply_workflow_ingest_result(job, status="ok", stats={"created": 2, "updated": 0, "total": 2})
    stored = workflow_ingest_result(job)
    assert stored is not None
    assert stored["status"] == "ok"
    assert stored["stats"] == {"created": 2, "updated": 0, "total": 2}
    assert job.result[WORKFLOW_INGEST_RESULT_KEY]["status"] == "ok"
    assert job.result["report"] == {"ok": True}


def test_apply_workflow_ingest_result_failed():
    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="rq-2",
        status="completed",
        result=None,
    )
    apply_workflow_ingest_result(job, status="failed", error="boom")
    stored = workflow_ingest_result(job)
    assert stored is not None
    assert stored["status"] == "failed"
    assert stored["error"] == "boom"


@pytest.mark.asyncio
async def test_ensure_ingested_creates_project_clash_items():
    workspace_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = ProjectClashJob(
        id=job_id,
        project_id=uuid.uuid4(),
        job_id="coord-run-1",
        status="completed",
        result={
            "report": {},
            "artifacts": _sample_primary_artifacts(),
        },
    )

    session = AsyncMock()
    existing_result = MagicMock()
    existing_result.all.return_value = []
    item_result = MagicMock()
    item_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[existing_result, item_result])
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = ClashWorkflowService(session, workspace_id)
    stats = await svc.ensure_ingested(job, actor="system")

    assert stats["created"] == 1
    assert stats["total"] == 1
    assert session.add.call_count >= 2


@pytest.mark.asyncio
async def test_ingest_after_job_complete_records_failure_not_silent():
    workspace_id = uuid.uuid4()
    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="coord-run-fail",
        status="completed",
        result={"report": {}, "artifacts": {}},
    )
    clash_svc = ClashService(AsyncMock(), workspace_id)

    with patch.object(
        ClashWorkflowService,
        "ensure_ingested",
        new_callable=AsyncMock,
        side_effect=RuntimeError("ingest exploded"),
    ):
        await clash_svc._ingest_workflow_after_job_complete(job)

    stored = workflow_ingest_result(job)
    assert stored is not None
    assert stored["status"] == "failed"
    assert "ingest exploded" in stored["error"]


@pytest.mark.asyncio
async def test_ingest_after_job_complete_records_success():
    workspace_id = uuid.uuid4()
    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="coord-run-ok",
        status="completed",
        result={"report": {}, "artifacts": {}},
    )
    clash_svc = ClashService(AsyncMock(), workspace_id)

    with patch.object(
        ClashWorkflowService,
        "ensure_ingested",
        new_callable=AsyncMock,
        return_value={"created": 1, "updated": 0, "total": 1},
    ):
        await clash_svc._ingest_workflow_after_job_complete(job)

    stored = workflow_ingest_result(job)
    assert stored is not None
    assert stored["status"] == "ok"
    assert stored["stats"]["total"] == 1


@pytest.mark.parametrize(
    "route",
    [r for r in clash_workflow_routes.router.routes if isinstance(r, APIRoute)],
    ids=lambda r: r.path,
)
def test_clash_workflow_routes_declare_workspace_context(route: APIRoute):
    dep_names = {dep.call.__name__ for dep in route.dependant.dependencies if dep.call}
    assert "get_workspace_context" in dep_names


def test_clash_export_service_requires_workspace_id():
    session = MagicMock()
    workspace_id = uuid.uuid4()
    svc = ClashExportService(session, workspace_id)
    assert svc._workspace_id == workspace_id
    assert svc._clash_svc._workspace_id == workspace_id
    assert svc._project_svc._workspace_id == workspace_id
