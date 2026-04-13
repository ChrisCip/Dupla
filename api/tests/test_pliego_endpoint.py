from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("JOB_DATA_DIR", str(tmp_path / "data"))
    import app.main

    importlib.reload(app.main)
    from app.main import app

    return TestClient(app)


def test_pliego_fill_404(app_client: TestClient) -> None:
    r = app_client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/pliego-fill")
    assert r.status_code == 404


def test_pliego_fill_409_pending(app_client: TestClient, tmp_path: Path) -> None:
    job_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    root = tmp_path / "data" / "jobs" / job_id
    root.mkdir(parents=True)
    meta = {
        "job_id": job_id,
        "status": "pending",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:01+00:00",
        "dwg_filename": "x.dwg",
        "error": None,
        "outputs": None,
        "cad_fact_keys": None,
        "uploaded_object_name": None,
    }
    (root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    r = app_client.get(f"/api/v1/projects/{job_id}/pliego-fill")
    assert r.status_code == 409


def test_pliego_fill_200_structure(app_client: TestClient, tmp_path: Path) -> None:
    job_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    root = tmp_path / "data" / "jobs" / job_id
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    norm = {
        "project": "test.normalized.json",
        "total_objects": 10,
        "cad_facts": {
            "layers": {"WALL": {"object_count": 2, "entity_types": {}, "sample_names": [], "handles": []}},
            "texts": [{"layer": "0", "entity_type": "text", "handle": "1", "content": "Calle Falsa 123"}],
            "hatches": [{"layer": "A", "area": 12.5, "entity_type": "hatch"}],
            "dimensions": [],
            "blocks": [],
            "geometry_hints": [],
        },
        "inventory_hints": {"level_markers": [], "block_frequency": []},
    }
    (outputs / "file.normalized.json").write_text(json.dumps(norm), encoding="utf-8")
    meta = {
        "job_id": job_id,
        "status": "succeeded",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:01+00:00",
        "dwg_filename": "proyecto_pliego.dwg",
        "error": None,
        "outputs": {"normalized_json": "file.normalized.json", "raw_json": "x.json"},
        "cad_fact_keys": 3,
        "uploaded_object_name": "x",
    }
    (root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    r = app_client.get(f"/api/v1/projects/{job_id}/pliego-fill")
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert "template_reference" in data
    assert data["resumen_fields"]["proyecto"]["suggested_value"] == "proyecto_pliego"
    assert data["resumen_fields"]["m2_construccion"]["suggested_value"] == 12.5
    assert "Calle Falsa" in (data["resumen_fields"]["ubicacion_del_proyecto"]["suggested_value"] or "")
