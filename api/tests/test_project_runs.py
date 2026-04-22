from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


def _body():
    return {
        "project_id": "gebsa_iv",
        "project_name": "Residencial GEBSA IV",
        "disciplines": [
            {"id": "arquitectura", "dwg_url": "https://x/a.dwg", "pdf_url": "https://x/a.pdf"},
        ],
    }


@patch("app.queue.get_task_queue")
def test_create_project_run_202(mock_q, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("CLIENT_ID", "x")
    monkeypatch.setenv("CLIENT_SECRET", "x")
    mock_q.return_value.enqueue = MagicMock()
    settings = Settings(job_data_dir=tmp_path, api_data_dir=tmp_path, artifact_cache_dir=tmp_path / "c")
    monkeypatch.setattr("app.routers.project_runs.get_settings", lambda: settings)
    import importlib

    importlib.import_module("app.routers.project_runs")
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/v1/project-runs", json=_body())
    assert r.status_code == 202
    data = r.json()
    assert "run_id" in data
    assert data["status"] == "pending"
    mock_q.return_value.enqueue.assert_called_once()


def test_create_requires_pdf():
    from app.models.schemas import ProjectRunCreate

    with pytest.raises(ValueError):
        ProjectRunCreate(
            disciplines=[{"id": "arquitectura", "dwg_url": "https://a/b", "pdf_url": ""}],
        )


def test_get_not_found(tmp_path, monkeypatch):
    from app.main import app

    monkeypatch.setattr(
        "app.routers.project_runs.get_settings",
        lambda: Settings(job_data_dir=tmp_path, api_data_dir=tmp_path, artifact_cache_dir=tmp_path / "c"),
    )
    c = TestClient(app)
    r = c.get("/api/v1/project-runs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
