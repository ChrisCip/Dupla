"""Tests for incident contract, canonical severity, and confirmed-clash gate."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.clash_incident_contract import (
    SHORT_LABEL_MAX_LEN,
    PlanAliasState,
    build_incident_contract,
    build_short_label,
    build_title_semantic,
    is_confirmed_workflow_incident,
    normalize_incident_code,
    resolve_base_compared,
)
from app.domain.clash_severity import (
    normalize_severity,
    resolve_incident_severity,
    score_to_severity,
    severity_label_es,
)
from app.models.project_clash_item import ProjectClashItem
from app.models.project_clash_job import ProjectClashJob
from app.services.clash_reports.formatting import FilenameAliasRegistry, compute_severity
from app.services.clash_workflow_service import ClashWorkflowService, _incident_to_fields


def _confirmed_incident(**overrides) -> dict:
    base = {
        "incident_id": "incident_0001",
        "file_pair": ["ARQ-PLANTA.dwg", "HID-SAN-01.dwg"],
        "level_id": "P1",
        "member_count": 1,
        "plan_bounds_mm": [148000, -163000, 158000, -154000],
        "plan_centroid_mm": [153000, -158500],
        "representative_conflict": {
            "discipline_a": "ARQUITECTURA",
            "discipline_b": "PLOMERIA",
            "clash_type": "HARD",
            "overlap_depth_z_mm": 180.0,
            "plan_intersection_area_mm2": 50_000.0,
            "raw_layers": ["ARQ_BAJANTE", "ARQ_MURO"],
        },
        "confidence": "high",
    }
    base.update(overrides)
    return base


def test_normalize_severity_preserves_canonical_enum():
    assert normalize_severity("critical") == "critical"
    assert normalize_severity("high") == "high"
    assert normalize_severity("medium") == "medium"
    assert normalize_severity("low") == "low"


def test_normalize_severity_maps_spanish_aliases():
    assert normalize_severity("Alta") == "high"
    assert normalize_severity("Media") == "medium"
    assert normalize_severity("Baja") == "low"
    assert normalize_severity("crítica") == "critical"


def test_severity_label_es_presentation_only():
    assert severity_label_es("critical") == "crítica"
    assert severity_label_es("high") == "alta"
    assert severity_label_es("medium") == "media"
    assert severity_label_es("low") == "baja"


def test_resolve_incident_severity_prefers_motor_value():
    incident = _confirmed_incident(severity="high")
    assert resolve_incident_severity(incident) == "high"
    assert resolve_incident_severity(incident, enriched={"severity": "critical"}) == "critical"


def test_resolve_incident_severity_does_not_degrade_to_low_when_scored():
    incident = _confirmed_incident()
    incident.pop("severity", None)
    incident["confidence"] = "medium"
    incident["representative_conflict"]["plan_intersection_area_mm2"] = 2_500_000.0
    incident["representative_conflict"]["overlap_depth_z_mm"] = 10.0
    incident["member_count"] = 8
    assert resolve_incident_severity(incident) == "high"


def test_compute_severity_returns_english_enum():
    assert compute_severity(area_mm2=2_000_000, z_depth_mm=10, member_count=6) == "high"
    assert compute_severity(area_mm2=750_000, z_depth_mm=250) == "medium"
    assert compute_severity(area_mm2=1_000, z_depth_mm=10) == "low"


def test_score_to_severity_critical_with_high_confidence():
    assert (
        score_to_severity(
            member_count=12,
            area_mm2=2_500_000.0,
            overlap_depth_mm=300.0,
            report_confidence="high",
        )
        == "critical"
    )


def test_build_title_semantic_exact_format():
    title = build_title_semantic(
        base_plan_number="ARQ-01",
        incident_code="INC-001",
        compared_plan_number="HID-SAN-01",
        severity="critical",
    )
    assert title == "ARQ-01_BASE / INC-001 / Contra HID-SAN-01 / Severidad crítica"


def test_normalize_incident_code():
    assert normalize_incident_code("incident_0001") == "INC-001"
    assert normalize_incident_code("INC-042") == "INC-042"


def test_short_label_max_ninety_chars():
    label, warnings = build_short_label(
        "INC-001",
        layer_a="ARQ_BAJANTE_SANITARIO_EXTRA_LARGO",
        layer_b="ARQ_MURO_CARGA_ESTRUCTURAL_MUY_LARGO",
        clash_type="HARD",
    )
    assert len(label) <= SHORT_LABEL_MAX_LEN
    assert label.startswith("INC-001:")


def test_short_label_truncation_warns():
    _, warnings = build_short_label(
        "INC-999",
        layer_a="X" * 40,
        layer_b="Y" * 40,
        clash_type="HARD",
        max_len=SHORT_LABEL_MAX_LEN,
    )
    assert "short_label_truncated" in warnings


def test_table_comment_longer_than_short_label():
    incident = _confirmed_incident()
    contract = build_incident_contract(incident, plan_state=PlanAliasState())
    assert len(contract.table_comment) > len(contract.short_label)
    assert "Revisar trazado" in contract.table_comment


def test_resolve_base_compared_architecture_wins():
    base_idx, compared_idx, rule, warnings = resolve_base_compared(
        discipline_a="ARQUITECTURA",
        discipline_b="PLOMERIA",
    )
    assert base_idx == 0
    assert compared_idx == 1
    assert rule == "architecture_base"
    assert not warnings


def test_resolve_base_compared_fallback_dwg_a():
    base_idx, compared_idx, rule, warnings = resolve_base_compared(
        discipline_a="ELECTRICA",
        discipline_b="MECANICA",
    )
    assert base_idx == 0
    assert compared_idx == 1
    assert rule == "fallback_dwg_a"
    assert "base_plan_rule_fallback_dwg_a" in warnings


def test_is_confirmed_rejects_candidate_only():
    candidate = _confirmed_incident(candidate_only=True)
    assert is_confirmed_workflow_incident(candidate) is False

    broad = _confirmed_incident(phase="broad")
    assert is_confirmed_workflow_incident(broad) is False

    no_geom = {"incident_id": "x", "representative_conflict": {}}
    assert is_confirmed_workflow_incident(no_geom) is False


def test_is_confirmed_accepts_narrow_phase_clash():
    assert is_confirmed_workflow_incident(_confirmed_incident()) is True


def test_incident_to_fields_populates_contract_columns():
    fields = _incident_to_fields(_confirmed_incident(), plan_state=PlanAliasState())
    assert fields["title_semantic"]
    assert fields["short_label"]
    assert fields["table_comment"]
    assert fields["base_plan_number"]
    assert fields["compared_plan_number"]
    assert fields["severity"] in {"critical", "high", "medium", "low"}
    assert len(fields["short_label"]) <= SHORT_LABEL_MAX_LEN
    assert fields["raw_json"]["_workflow_contract"]["confirmed_clash"] is True


@pytest.mark.asyncio
async def test_ensure_ingested_skips_candidate_only():
    workspace_id = uuid.uuid4()
    job = ProjectClashJob(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id="coord-run-candidate",
        status="completed",
        result={
            "report": {},
            "artifacts": {
                "primary_incidents": json.dumps(
                    {
                        "incidents": [
                            _confirmed_incident(candidate_only=True, incident_id="cand_1"),
                            _confirmed_incident(incident_id="incident_0002"),
                        ]
                    }
                )
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
    stats = await svc.ensure_ingested(job, actor="system")

    assert stats["created"] == 1
    assert stats["skipped_candidates"] == 1
    assert stats["total"] == 1


def test_item_ui_payload_backward_compatible_without_contract_columns():
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

    assert payload["clash_code"] == "incident_0001"
    assert payload["severity"] == "medium"
    assert payload["severity_label"] == "media"
    assert payload["title_semantic"] is None
    assert payload["short_label"] is None
    assert payload["table_comment"] is None
