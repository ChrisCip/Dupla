from __future__ import annotations

from types import SimpleNamespace

from coordination.selection.coordinate_audit import (
    PairScheduleItem,
    SourceAudit,
    apply_coordinate_band_gating,
    build_pair_schedule,
    build_source_audit,
)
from coordination.selection.fast_compare import PreMatchCandidate
from coordination.core.models_25d import Discipline, Element25D, ZInterval


def _candidate(rel_path: str, discipline: Discipline, level_id: str = "NPT_P1"):
    return SimpleNamespace(
        rel_path=rel_path,
        suffix=".dwg",
        issue_key="manual:serena18",
        cohort_id="analysis_03_manual",
        discipline=discipline,
        level_id=level_id,
        level_source="pattern:test",
        drawing_type="generic_plan",
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


def test_apply_coordinate_band_gating_uses_per_discipline_dominant_band() -> None:
    fontaneria = SourceAudit(
        rel_path="HID/S-100.dwg",
        file_name="S-100.dwg",
        suffix=".dwg",
        issue_key="d:2025",
        cohort_id="hid",
        discipline="FONTANERIA",
        level_id="NPT_P1",
        level_source="pattern:test",
        coordinate_band_key=(347, 1248),
        coordinate_band="X~173.5M, Y~624.1M",
        audit_status="eligible",
    )
    arq = fontaneria.model_copy(
        update={
            "rel_path": "ARQ/PLANTA.dwg",
            "file_name": "PLANTA.dwg",
            "discipline": "ARQUITECTURA",
            "coordinate_band_key": (337, 1249),
            "coordinate_band": "X~168.8M, Y~624.6M",
        }
    )
    est = arq.model_copy(
        update={
            "rel_path": "EST/E03.dwg",
            "file_name": "E03.dwg",
            "discipline": "ESTRUCTURA",
        }
    )

    gated = apply_coordinate_band_gating(
        [fontaneria, arq, est],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC, Discipline.MEP_PLUMBING),
    )
    by_path = {item.rel_path: item for item in gated}

    assert by_path["ARQ/PLANTA.dwg"].audit_status == "eligible"
    assert by_path["EST/E03.dwg"].audit_status == "eligible"
    assert by_path["HID/S-100.dwg"].audit_status == "eligible"


def test_build_pair_schedule_schedules_site_proximity_cross_band_pair() -> None:
    arch = SourceAudit(
        rel_path="PLANOS/ARQ/PLANTA.dwg",
        file_name="PLANTA.dwg",
        suffix=".dwg",
        issue_key="dir:arq",
        cohort_id="prematch_npt_p1_arch_01",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="default_level",
        drawing_type="floor_plan",
        coordinate_band_key=(347, 1248),
        coordinate_band="X~173.69M, Y~624.14M",
        audit_status="eligible",
        roles_detected=["WALL", "SLAB"],
    )
    struc = arch.model_copy(
        update={
            "rel_path": "PLANOS/EST/E03.dwg",
            "file_name": "E03.dwg",
            "issue_key": "dir:est",
            "discipline": Discipline.STRUC.value,
            "drawing_type": "formwork",
            "coordinate_band_key": (337, 1249),
            "coordinate_band": "X~168.81M, Y~624.65M",
            "audit_status": "needs_alignment",
            "notes": ["fuera de la banda dominante de disciplina"],
            "roles_detected": ["BEAM", "SLAB"],
        }
    )
    pre_match = PreMatchCandidate(
        file_a=arch.rel_path,
        file_b=struc.rel_path,
        file_name_a=arch.file_name,
        file_name_b=struc.file_name,
        issue_key_a="dir:arq",
        issue_key_b="dir:est",
        discipline_a=Discipline.ARCH.value,
        discipline_b=Discipline.STRUC.value,
        level_id="NPT_P1",
        drawing_type_a="floor_plan",
        drawing_type_b="formwork",
        drawing_type_compatibility=1.0,
        revision_proximity=0.4,
        geometry_overlap_hint=1.0,
        anchor_quality=0.9,
        score=0.79,
        decision="auto_comparable",
        reason_codes=("cross_revision_pair_required",),
        documentary_cohort_relation="cross_cohort",
    )

    schedule = build_pair_schedule(
        [arch, struc],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
        pre_match_candidates=[pre_match],
    )

    assert len(schedule) == 1
    assert schedule[0].scheduled is True
    assert schedule[0].alignment_status == "required"
    assert "site_proximity_band" in schedule[0].reason_codes
    assert schedule[0].primary_rejection_rule is None


def test_build_pair_schedule_promotes_cross_cohort_pair_from_audit() -> None:
    arch = SourceAudit(
        rel_path="PLANOS/ARQ/PLANTA.dwg",
        file_name="PLANTA.dwg",
        suffix=".dwg",
        issue_key="dir:arq",
        cohort_id="prematch_npt_p1_arch_01",
        discipline=Discipline.ARCH.value,
        level_id="NPT_P1",
        level_source="default_level",
        drawing_type="floor_plan",
        coordinate_band_key=(337, 1249),
        coordinate_band="X~168.82M, Y~624.64M",
        audit_status="eligible",
    )
    struc = arch.model_copy(
        update={
            "rel_path": "PLANOS/EST/E03.dwg",
            "file_name": "E03.dwg",
            "issue_key": "dir:est",
            "discipline": Discipline.STRUC.value,
            "drawing_type": "formwork",
        }
    )
    pre_match = PreMatchCandidate(
        file_a=arch.rel_path,
        file_b=struc.rel_path,
        file_name_a=arch.file_name,
        file_name_b=struc.file_name,
        issue_key_a="dir:arq",
        issue_key_b="dir:est",
        discipline_a=Discipline.ARCH.value,
        discipline_b=Discipline.STRUC.value,
        level_id="NPT_P1",
        drawing_type_a="floor_plan",
        drawing_type_b="formwork",
        drawing_type_compatibility=1.0,
        revision_proximity=0.4,
        geometry_overlap_hint=1.0,
        anchor_quality=0.9,
        score=0.79,
        decision="auto_comparable",
        reason_codes=("cross_revision_pair_required",),
        documentary_cohort_relation="cross_cohort",
    )

    schedule = build_pair_schedule(
        [arch, struc],
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
        pre_match_candidates=[pre_match],
    )

    assert len(schedule) == 1
    assert schedule[0].scheduled is True
    assert schedule[0].selection_reason == "promoted_from_coordinate_audit"
    assert schedule[0].documentary_cohort_relation == "cross_cohort_promoted"
    assert "audit_promoted" in schedule[0].reason_codes
