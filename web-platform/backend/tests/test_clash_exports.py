"""Tests for clash export metadata and PDF generation."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

from app.models.project_file import ProjectFile
from app.services.clash_export_service import ClashExportService, build_export_filename
from app.services.clash_reports.data import build_report_bundle
from app.services.clash_reports.formatting import make_zoom_command
from app.services.clash_service import compute_cad_fingerprint, resolve_run_sequence


def _sample_artifacts() -> dict:
    primary = {
        "project_name": "Obra demo",
        "incident_count": 1,
        "incident_conflict_count": 1,
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
                    "source_refs": [
                        "ARQ-PLANTA.dwg|ARQ_MURO|Polyline|AAA",
                        "EST-LOSAS.dwg|EST_LOSA|Polyline|BBB",
                    ],
                },
                "confidence": "high",
            }
        ],
    }
    context = {
        "counts": {
            "scheduled_pairs": 1,
            "scheduled_files": 2,
            "primary_incidents": 1,
            "primary_members": 1,
        },
        "pair_rollups": [],
    }
    pair_schedule = {
        "pairs": [
            {
                "file_a": "ARQ-PLANTA.dwg",
                "file_b": "EST-LOSAS.dwg",
                "scheduled": True,
                "discipline_a": "ARQUITECTURA",
                "discipline_b": "ESTRUCTURA",
            }
        ]
    }
    return {
        "primary_incidents": json.dumps(primary),
        "coordination_context": json.dumps(context),
        "pair_schedule": json.dumps(pair_schedule),
        "analyzed_documents": [
            {"original_name": "ARQ-PLANTA.dwg", "discipline_bucket": "arquitectura"},
            {"original_name": "EST-LOSAS.dwg", "discipline_bucket": "estructura"},
        ],
    }


def _make_cad_file(project_id: uuid.UUID, name: str, discipline: str, file_id: uuid.UUID | None = None) -> ProjectFile:
    return ProjectFile(
        id=file_id or uuid.uuid4(),
        project_id=project_id,
        original_name=name,
        discipline=discipline,
        storage_key=f"/tmp/{name}",
        mime="application/octet-stream",
    )


def test_cad_fingerprint_stable_and_changes_with_inventory():
    project_id = uuid.uuid4()
    f1 = _make_cad_file(project_id, "a.dwg", "ARQ", uuid.UUID("11111111-1111-4111-8111-111111111111"))
    f2 = _make_cad_file(project_id, "b.dwg", "EST", uuid.UUID("22222222-2222-4222-8222-222222222222"))
    assert compute_cad_fingerprint([f1, f2]) == compute_cad_fingerprint([f2, f1])
    f3 = _make_cad_file(project_id, "c.dwg", "ELC", uuid.UUID("33333333-3333-4333-8333-333333333333"))
    assert compute_cad_fingerprint([f1, f2, f3]) != compute_cad_fingerprint([f1, f2])


def test_run_sequence_reused_and_incremented():
    fp_same = "abc123"
    fp_new = "def456"
    prior = [(fp_same, 1)]
    assert resolve_run_sequence(prior, fp_same) == 1
    assert resolve_run_sequence(prior, fp_new) == 2
    assert resolve_run_sequence([(fp_new, 2), (fp_same, 1)], fp_same) == 1


def test_build_export_filename_format():
    meta = {
        "folder_name": "TEST_01",
        "project_name": "Tutorial · Workspace Dupla",
        "user_display": "Carlos Ruiz",
        "run_date": "2026-05-22",
        "run_sequence": 1,
    }
    assert "numero 01.pdf" in build_export_filename("technical", meta)
    assert "numero 01.pdf" in build_export_filename("human", meta)


def test_clash_pdf_builders_return_pdf_bytes():
    svc = ClashExportService(session=MagicMock())
    meta = {
        "project_name": "Tutorial · Workspace Dupla",
        "folder_name": "TEST_01",
        "user_display": "Carlos Ruiz",
        "run_date": "2026-05-22",
        "run_sequence": 1,
    }
    artifacts = _sample_artifacts()
    technical = svc.build_clash_technical_pdf(meta=meta, artifacts=artifacts)
    human = svc.build_clash_human_pdf(meta=meta, artifacts=artifacts)
    assert technical[:4] == b"%PDF"
    assert human[:4] == b"%PDF"
    assert len(technical) > 2000
    assert len(human) > 2000
    assert b"Inventario analizado" not in technical


def test_technical_pdf_index_many_incidents():
    svc = ClashExportService(session=MagicMock())
    meta = {
        "project_name": "Tutorial · Workspace Dupla",
        "folder_name": "TEST_01",
        "user_display": "Carlos Ruiz",
        "run_date": "2026-05-22",
        "run_sequence": 1,
    }
    base = _incident_dict()
    incidents = []
    for i in range(24):
        row = dict(base)
        row["incident_id"] = f"incident_{i:04d}"
        row["plan_centroid_mm"] = [148000 + i * 1000, -163000 - i * 500]
        row["plan_bounds_mm"] = [
            148000 + i * 1000,
            -163000 - i * 500,
            158000 + i * 1000,
            -154000 - i * 500,
        ]
        incidents.append(row)
    artifacts = _sample_artifacts()
    primary = json.loads(artifacts["primary_incidents"])
    primary["incidents"] = incidents
    primary["incident_count"] = len(incidents)
    artifacts["primary_incidents"] = json.dumps(primary)
    pdf = svc.build_clash_technical_pdf(meta=meta, artifacts=artifacts)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000


def test_report_bundle_includes_zoom_command_not_bare_ze():
    meta = {"project_name": "Demo", "folder_name": "TEST_01", "run_sequence": 1}
    bundle = build_report_bundle(meta=meta, artifacts=_sample_artifacts())
    assert len(bundle.incidents) == 1
    inc = bundle.incidents[0]
    assert inc.zoom_command is not None
    assert inc.zoom_command.startswith("Z W")
    assert inc.layer_a == "ARQ_MURO"
    assert "?" not in inc.center_text


def test_zoom_command_never_returns_bare_ze():
    cmd, fb = make_zoom_command(None, center=None)
    assert cmd != "Z E"
    assert fb is not None
