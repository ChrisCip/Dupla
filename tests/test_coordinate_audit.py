from __future__ import annotations

from types import SimpleNamespace

from core.coordination.coordinate_audit import (
    PairScheduleItem,
    SourceAudit,
    apply_coordinate_band_gating,
    build_pair_schedule,
    build_source_audit,
)
from core.coordination.models_25d import Discipline, Element25D, ZInterval


def _candidate(rel_path: str, discipline: Discipline, level_id: str = "NPT_P1"):
    return SimpleNamespace(
        rel_path=rel_path,
        suffix=".dwg",
        issue_key="manual:serena18",
        cohort_id="analysis_03_manual",
        discipline=discipline,
        level_id=level_id,
        level_source="pattern:test",
    )


def _element(geometry_source: str, geometry_role: str = "primary") -> Element25D:
    return Element25D(
        id=f"el_{geometry_source}_{geometry_role}",
        source_ref=f"C:/x.dwg|A|Polyline|1",
        discipline=Discipline.ARCH,
        footprint_coords_mm=[(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0),
        metadata={"geometry_source": geometry_source, "geometry_role": geometry_role},
    )


def test_build_source_audit_marks_bbox_only() -> None:
    audit = build_source_audit(
        _candidate("PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg", Discipline.ARCH),
        elements=[_element("dwg_accore_bbox", "suppressed")],
    )

    assert audit.audit_status == "bbox_only"
    assert audit.selected_primary_count == 0


def test_build_source_audit_accepts_profile_only() -> None:
    audit = build_source_audit(
        _candidate("PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg", Discipline.ARCH),
        accore_profile={
            "units_to_mm_factor": 1.0,
            "raw_entity_count": 120,
            "raw_primary_candidate_count": 45,
            "raw_annotation_count": 12,
            "raw_bbox_only_count": 10,
            "bounds_mm": (168_000_000.0, 624_000_000.0, 168_100_000.0, 624_100_000.0, 0.0, 0.0),
            "centroid_mm": (168_050_000.0, 624_050_000.0, 0.0),
            "dominant_cluster_bounds_mm": (500_000.0, 2_000_000.0, 530_000.0, 2_030_000.0, 0.0, 0.0),
            "dominant_cluster_centroid_mm": (515_000.0, 2_015_000.0, 0.0),
            "dominant_entity_types": ["Polyline", "Line"],
        },
    )

    assert audit.audit_status == "eligible"
    assert audit.selected_total_count == 0
    assert audit.raw_primary_candidate_count == 45
    assert audit.coordinate_band is not None
    assert audit.coordinate_band_key == (1, 4)


def test_apply_coordinate_band_gating_marks_off_band_as_needs_alignment() -> None:
    left = SourceAudit(
        rel_path="A.dwg",
        file_name="A.dwg",
        suffix=".dwg",
        issue_key="manual",
        cohort_id="manual",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="pattern:test",
        coordinate_band_key=(337, 1249),
        coordinate_band="X~168.5M, Y~624.5M",
        audit_status="eligible",
    )
    right = left.model_copy(
        update={
            "rel_path": "B.dwg",
            "file_name": "B.dwg",
            "discipline": Discipline.STRUC.value,
        }
    )
    off_band = right.model_copy(
        update={
            "rel_path": "C.dwg",
            "file_name": "C.dwg",
            "coordinate_band_key": (0, 0),
            "coordinate_band": "X~0.0M, Y~0.0M",
        }
    )

    gated = apply_coordinate_band_gating(
        [left, right, off_band],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert gated[2].audit_status == "needs_alignment"


def test_build_pair_schedule_blocks_non_eligible_sources() -> None:
    arch = SourceAudit(
        rel_path="A.dwg",
        file_name="A.dwg",
        suffix=".dwg",
        issue_key="manual",
        cohort_id="manual",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="pattern:test",
        coordinate_band_key=(1, 1),
        coordinate_band="X~1.0M, Y~1.0M",
        audit_status="eligible",
    )
    struc = arch.model_copy(
        update={
            "rel_path": "B.dwg",
            "file_name": "B.dwg",
            "discipline": Discipline.STRUC.value,
            "audit_status": "annotation_noise",
        }
    )

    schedule = build_pair_schedule(
        [arch, struc],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert len(schedule) == 1
    assert isinstance(schedule[0], PairScheduleItem)
    assert schedule[0].scheduled is False
    assert schedule[0].block_reason == "B.dwg:annotation_noise"


def test_build_pair_schedule_blocks_level_mismatch_after_band_match() -> None:
    arch = SourceAudit(
        rel_path="A.dwg",
        file_name="A.dwg",
        suffix=".dwg",
        issue_key="manual",
        cohort_id="manual",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="pattern:test",
        coordinate_band_key=(1, 1),
        coordinate_band="X~1.0M, Y~1.0M",
        audit_status="eligible",
    )
    struc = arch.model_copy(
        update={
            "rel_path": "B.dwg",
            "file_name": "B.dwg",
            "discipline": Discipline.STRUC.value,
            "level_id": "NPT_P2",
        }
    )

    schedule = build_pair_schedule(
        [arch, struc],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert len(schedule) == 1
    assert schedule[0].scheduled is False
    assert schedule[0].block_reason == "level_mismatch"
