from __future__ import annotations

import importlib
import json
from io import BytesIO
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


def test_health(app_client: TestClient) -> None:
    r = app_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_project_returns_202_and_enqueues(
    app_client: TestClient,
    mock_queue: MagicMock,
    tmp_path: Path,
) -> None:
    buf = BytesIO(b"stub dwg content")
    r = app_client.post(
        "/api/v1/projects",
        files={"dwg": ("test.dwg", buf, "application/acad")},
    )
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert "/api/v1/projects/" in body["status_url"]
    mock_queue.enqueue.assert_called_once()
    job_id = body["job_id"]
    inputs = tmp_path / "data" / "jobs" / job_id / "inputs"
    assert inputs.is_dir()
    dwg_files = list(inputs.glob("*.dwg"))
    assert len(dwg_files) == 1


def test_create_project_rejects_non_dwg(app_client: TestClient, mock_queue: MagicMock) -> None:
    buf = BytesIO(b"x")
    r = app_client.post(
        "/api/v1/projects",
        files={"dwg": ("bad.txt", buf, "text/plain")},
    )
    assert r.status_code == 400
    mock_queue.enqueue.assert_not_called()


def test_get_results_404(app_client: TestClient) -> None:
    r = app_client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/results")
    assert r.status_code == 404


def test_get_results_succeeded_reads_normalized_json(
    app_client: TestClient,
    tmp_path: Path,
) -> None:
    job_id = "11111111-1111-1111-1111-111111111111"
    job_root = tmp_path / "data" / "jobs" / job_id
    outputs = job_root / "outputs"
    outputs.mkdir(parents=True)
    norm = {"a": 1, "b": {"c": 2}}
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

    r = app_client.get(f"/api/v1/projects/{job_id}/results")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "succeeded"
    assert data["cad_facts"] == norm
    assert data["cad_fact_keys"] == 2
