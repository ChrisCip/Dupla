"""Backend tests for PR 3 visual manifest ingest and tile paths."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.clash_incident_contract import PlanAliasState
from app.models.project_clash_job import ProjectClashJob
from app.services.clash_workflow_service import (
    ClashWorkflowService,
    _incident_to_fields,
    _load_visual_manifest,
)


def _confirmed_incident(incident_id: str = "incident_0001") -> dict:
    return {
        "incident_id": incident_id,
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


def test_load_visual_manifest_from_artifacts_json_string(tmp_path: Path) -> None:
    manifest = {"incidents": {"incident_0001": {"has_real_visual": True}}}
    artifacts = {"incident_visual_manifest": json.dumps(manifest)}
    loaded = _load_visual_manifest(artifacts, str(tmp_path))
    assert loaded["incidents"]["incident_0001"]["has_real_visual"] is True


def test_load_visual_manifest_from_output_dir_file(tmp_path: Path) -> None:
    manifest = {"incidents": {"incident_0001": {"zoom_tile_path": "zoom/incident_0001_zoom.svg"}}}
    (tmp_path / "incident_visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    loaded = _load_visual_manifest({}, str(tmp_path))
    assert loaded["incidents"]["incident_0001"]["zoom_tile_path"] == "zoom/incident_0001_zoom.svg"


def test_incident_to_fields_persists_visual_paths() -> None:
    visual_entry = {
        "base_full_plan_tile_path": "base_full/ARQ_P1.svg",
        "zoom_tile_path": "zoom/incident_0001_zoom.svg",
        "incident_overlay_tile_path": "overlays/incident_0001_overlay.svg",
        "composed_full_page_tile_path": "composed/incident_0001_full_page.svg",
        "has_real_visual": True,
        "visual_provenance": "coordination_incident_visual_renderer",
        "visual_warnings": [],
        "cad_viewbox": [0, 0, 1000, 1000],
    }
    fields = _incident_to_fields(
        _confirmed_incident(),
        plan_state=PlanAliasState(),
        visual_entry=visual_entry,
    )
    assert fields["base_full_plan_tile_path"] == "base_full/ARQ_P1.svg"
    assert fields["zoom_tile_path"] == "zoom/incident_0001_zoom.svg"
    assert fields["raw_json"]["_workflow_contract"]["has_real_visual"] is True
    assert fields["raw_json"]["_workflow_contract"]["composed_full_page_tile_path"] == (
        "composed/incident_0001_full_page.svg"
    )


def test_incident_to_fields_without_visual_marks_fallback() -> None:
    fields = _incident_to_fields(_confirmed_incident(), plan_state=PlanAliasState())
    contract = fields["raw_json"]["_workflow_contract"]
    assert contract["has_real_visual"] is False
    assert "no_incident_visual_manifest_entry" in contract["visual_warnings"]


@pytest.mark.asyncio
async def test_ensure_ingested_persists_visual_paths_from_manifest(tmp_path: Path) -> None:
    workspace_id = uuid.uuid4()
    manifest = {
        "incidents": {
            "incident_0001": {
                "base_full_plan_tile_path": "base_full/ARQ_P1.svg",
                "zoom_tile_path": "zoom/incident_0001_zoom.svg",
                "has_real_visual": True,
                "visual_provenance": "coordination_incident_visual_renderer",
                "visual_warnings": [],
            }
        }
    }
    tiles_dir = tmp_path / "tiles" / "base_full"
    tiles_dir.mkdir(parents=True)
    (tiles_dir / "ARQ_P1.svg").write_text("<svg></svg>", encoding="utf-8")

    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="coord-visual",
        status="completed",
        output_dir=str(tmp_path),
        result={
            "report": {},
            "artifacts": {
                "primary_incidents": json.dumps({"incidents": [_confirmed_incident()]}),
                "incident_visual_manifest": json.dumps(manifest),
                "output_dir": str(tmp_path),
            },
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
    await svc.ensure_ingested(job, actor="system")

    added_items = [call.args[0] for call in session.add.call_args_list if call.args[0].__class__.__name__ == "ProjectClashItem"]
    assert len(added_items) == 1
    added_item = added_items[0]
    assert added_item.base_full_plan_tile_path == "base_full/ARQ_P1.svg"
    assert added_item.zoom_tile_path == "zoom/incident_0001_zoom.svg"


def test_item_ui_payload_backward_compatible_without_visual_paths() -> None:
    from app.models.project_clash_item import ProjectClashItem

    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="legacy",
        status="completed",
        result={},
    )
    item = ProjectClashItem(
        id=uuid.uuid4(),
        job_id=job.id,
        clash_code="incident_0001",
        priority="P2",
        severity="medium",
        report_confidence="medium",
        status="detected",
        centroid_x_mm=100.0,
        centroid_y_mm=200.0,
    )
    svc = ClashWorkflowService(MagicMock(), uuid.uuid4())
    payload = svc.item_ui_payload(item, job)
    assert payload["base_full_plan_tile_path"] is None
    assert payload["zoom_tile_path"] is None


def test_tile_file_rejects_path_traversal(tmp_path: Path, monkeypatch) -> None:
    from app.config import get_settings
    from app.models.project_clash_job import ProjectClashJob

    job_id = uuid.uuid4()
    tiles_dir = tmp_path / "tiles" / "composed"
    tiles_dir.mkdir(parents=True)
    (tiles_dir / "incident_0001_full_page.svg").write_text("<svg></svg>", encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("nope", encoding="utf-8")

    monkeypatch.setattr(get_settings(), "upload_root", str(tmp_path / "uploads"))
    job = ProjectClashJob(
        id=job_id,
        project_id=uuid.uuid4(),
        job_id="tile-security",
        status="completed",
        output_dir=str(tmp_path),
        result={},
    )
    svc = ClashWorkflowService(MagicMock(), uuid.uuid4())

    assert svc._tile_file(job, "../secret.txt") is None
    assert svc._tile_file(job, "../../secret.txt") is None
    assert svc._tile_file(job, "/etc/passwd.svg") is None
    assert svc._tile_file(job, "composed/../secret.txt") is None
    assert svc._tile_file(job, "secret.txt") is None
    assert svc._tile_file(job, "composed/evil.py") is None
    assert svc._tile_file(job, "composed/incident_0001_full_page.svg") is not None


def test_tile_file_rejects_disallowed_prefix(tmp_path: Path) -> None:
    from app.models.project_clash_job import ProjectClashJob

    tiles_dir = tmp_path / "tiles" / "private"
    tiles_dir.mkdir(parents=True)
    (tiles_dir / "leak.svg").write_text("<svg></svg>", encoding="utf-8")

    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="tile-prefix",
        status="completed",
        output_dir=str(tmp_path),
        result={},
    )
    svc = ClashWorkflowService(MagicMock(), uuid.uuid4())
    assert svc._tile_file(job, "private/leak.svg") is None
