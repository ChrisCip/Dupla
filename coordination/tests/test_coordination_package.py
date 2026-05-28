from __future__ import annotations

from pathlib import Path

from coordination.selection.coordination_package import (
    alignment_gaps_for_scheduled_pairs,
    build_coordination_package_diagnostics,
)
from coordination.selection.coordinate_audit import PairScheduleItem, SourceAudit
from coordination.selection.fast_compare import load_cohort_manifest
from coordination.core.models_25d import Discipline


def test_load_cohort_manifest_resolves_relative_paths(tmp_path: Path) -> None:
    root = tmp_path / "SERENA 18"
    (root / "PLANOS RECIBIDOS/ARQUITECTONICOS").mkdir(parents=True)
    manifest_path = tmp_path / "cohort_manifest.json"
    manifest_path.write_text(
        '{"cohort_name": "test", "source_files": ["PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg"]}',
        encoding="utf-8",
    )
    loaded = load_cohort_manifest(manifest_path, root=root)
    assert loaded.cohort_name == "test"
    assert "planos recibidos/arquitectonicos/a.dwg" in loaded.source_files


def test_alignment_gaps_detect_missing_override() -> None:
    arq = SourceAudit(
        rel_path="ARQ/A.dwg",
        file_name="A.dwg",
        suffix=".dwg",
        issue_key="manual",
        cohort_id="pkg",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="test",
        coordinate_band_key=(347, 1248),
        coordinate_band="X~173M",
        audit_status="needs_alignment",
    )
    est = arq.model_copy(
        update={
            "rel_path": "EST/B.dwg",
            "file_name": "B.dwg",
            "discipline": Discipline.STRUC.value,
            "coordinate_band_key": (337, 1249),
            "coordinate_band": "X~168M",
            "audit_status": "eligible",
        }
    )
    pair = PairScheduleItem(
        cohort_id="pkg",
        file_a=arq.rel_path,
        file_b=est.rel_path,
        level_ids=("NPT_P1", "NPT_P1"),
        scheduled=True,
        alignment_status="required",
        coordinate_compatible=True,
    )
    gaps = alignment_gaps_for_scheduled_pairs(
        scheduled_pairs=[pair],
        audit_by_rel={arq.rel_path: arq, est.rel_path: est},
        alignment_overrides={},
    )
    assert len(gaps) == 1
    assert gaps[0]["rel_path"] == arq.rel_path
    assert gaps[0]["reason"] == "needs_alignment"

    band_pair = pair.model_copy(update={"coordinate_compatible": False})
    band_gaps = alignment_gaps_for_scheduled_pairs(
        scheduled_pairs=[band_pair],
        audit_by_rel={arq.rel_path: arq, est.rel_path: est},
        alignment_overrides={},
    )
    assert len(band_gaps) == 2


def test_build_coordination_package_diagnostics_lists_files() -> None:
    audit = SourceAudit(
        rel_path="ARQ/A.dwg",
        file_name="A.dwg",
        suffix=".dwg",
        issue_key="manual",
        cohort_id="pkg",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="test",
        audit_status="eligible",
        coordinate_band="X~168M",
    )
    from types import SimpleNamespace

    candidate = SimpleNamespace(
        rel_path=audit.rel_path,
        discipline=Discipline.ARCH,
        level_id="NPT_P1",
    )
    payload = build_coordination_package_diagnostics(
        project_name="Test",
        nasas_root=Path("."),
        cohort_manifest=None,
        alignment_overrides={},
        selected_candidates=[candidate],
        candidate_audits=[audit],
        scheduled_pairs=[],
        primary_incident_count=0,
        status="no_scheduled_pairs",
    )
    assert payload["selected_file_count"] == 1
    assert payload["files"][0]["discipline"] == Discipline.ARCH.value
