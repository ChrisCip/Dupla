from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_queue(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    q = MagicMock()
    monkeypatch.setattr("app.routers.projects.get_task_queue", lambda: q)
    return q


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("JOB_DATA_DIR", str(tmp_path / "data"))
    import app.main

    importlib.reload(app.main)
    from app.main import app

    return TestClient(app)


def test_post_budget_404(app_client: TestClient) -> None:
    r = app_client.post("/api/v1/projects/00000000-0000-0000-0000-000000000000/budget")
    assert r.status_code == 404


def test_post_budget_409_when_not_succeeded(app_client: TestClient, tmp_path: Path) -> None:
    job_id = "22222222-2222-2222-2222-222222222222"
    job_root = tmp_path / "data" / "jobs" / job_id
    job_root.mkdir(parents=True)
    meta = {
        "job_id": job_id,
        "status": "running",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:01+00:00",
        "dwg_filename": "file.dwg",
        "error": None,
        "outputs": None,
        "cad_fact_keys": None,
        "uploaded_object_name": None,
    }
    (job_root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    r = app_client.post(f"/api/v1/projects/{job_id}/budget")
    assert r.status_code == 409


def test_post_budget_200_with_mocked_pipeline(
    app_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "44444444-4444-4444-4444-444444444444"
    job_root = tmp_path / "data" / "jobs" / job_id
    outputs = job_root / "outputs"
    outputs.mkdir(parents=True)
    norm = {"project": "Test", "levels": []}
    (outputs / "file.normalized.json").write_text(
        json.dumps(norm, ensure_ascii=False),
        encoding="utf-8",
    )
    meta = {
        "job_id": job_id,
        "status": "succeeded",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:01+00:00",
        "dwg_filename": "file.dwg",
        "error": None,
        "outputs": {"normalized_json": "file.normalized.json", "raw_json": "x.json"},
        "cad_fact_keys": 2,
        "uploaded_object_name": "obj.dwg",
    }
    (job_root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    monkeypatch.setattr(
        "app.routers.budget.compute_budget_for_job",
        lambda *a, **k: {"budget": "ok"},
    )

    r = app_client.post(f"/api/v1/projects/{job_id}/budget")
    assert r.status_code == 200
    assert r.json() == {"budget": "ok"}
