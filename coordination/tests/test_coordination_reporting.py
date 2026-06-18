from __future__ import annotations

from pathlib import Path

from coordination.reporting.reporting import (
    build_analysis_bot_context,
    build_coordination_report_context,
    render_coordination_human_report_markdown,
    render_coordination_report_markdown,
)


def _summary_payload() -> dict[str, object]:
    return {
        "generated_at": "2026-05-02T00:00:00+00:00",
        "project_name": "SERENA 18",
        "analysis_profile": "fast_compare",
        "status": "completed",
        "selected_candidate_count": 3,
        "element_count": 900,
        "scheduled_pair_count": 2,
        "scheduled_file_count": 3,
    }


def _primary_payload() -> dict[str, object]:
    return {
        "generated_at": "2026-05-02T00:00:00+00:00",
        "project_name": "SERENA 18",
        "analysis_profile": "fast_compare",
        "incident_count": 2,
        "incident_conflict_count": 14,
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": [
                    "C:/repo/ARQ-P1.dwg",
                    "C:/repo/EST-P1.dwg",
                ],
                "level_id": "NPT_P1",
                "member_count": 9,
                "plan_centroid_mm": [168_800_000.0, 624_600_000.0],
                "plan_bounds_mm": [168_799_000.0, 624_599_000.0, 168_801_000.0, 624_601_000.0],
                "confidence": "high",
                "geometry_sources": ["dwg_accore_polyline", "dwg_accore_polyline"],
                "representative_conflict": {
                    "discipline_a": "ARQUITECTURA",
                    "discipline_b": "ESTRUCTURA",
                    "confidence": "high",
                    "overlap_depth_z_mm": 290.0,
                    "plan_intersection_area_mm2": 2_500_000.0,
                    "plan_intersection_centroid_mm": [168_800_000.0, 624_600_000.0],
                    "plan_intersection_bounds_mm": [168_799_000.0, 624_599_000.0, 168_801_000.0, 624_601_000.0],
                    "level_ids": ["NPT_P1", "NPT_P1"],
                    "geometry_sources": ["dwg_accore_polyline", "dwg_accore_polyline"],
                    "level_assignment_sources": ["pattern:nivel_1", "pattern:nivel_1"],
                    "source_refs": [
                        "C:/repo/ARQ-P1.dwg|I-WALL|Polyline|1",
                        "C:/repo/EST-P1.dwg|S-BEAM|Polyline|2",
                    ],
                },
            },
            {
                "incident_id": "incident_0002",
                "file_pair": [
                    "C:/repo/ARQ-P1.dwg",
                    "C:/repo/EST-P1.dwg",
                ],
                "level_id": "NPT_P1",
                "member_count": 1,
                "plan_centroid_mm": [168_802_000.0, 624_602_000.0],
                "plan_bounds_mm": [168_801_900.0, 624_601_900.0, 168_802_100.0, 624_602_100.0],
                "confidence": "medium",
                "geometry_sources": ["dwg_accore_polyline", "dwg_accore_line"],
                "representative_conflict": {
                    "discipline_a": "ARQUITECTURA",
                    "discipline_b": "ESTRUCTURA",
                    "confidence": "medium",
                    "overlap_depth_z_mm": 90.0,
                    "plan_intersection_area_mm2": 50_000.0,
                    "plan_intersection_centroid_mm": [168_802_000.0, 624_602_000.0],
                    "plan_intersection_bounds_mm": [168_801_900.0, 624_601_900.0, 168_802_100.0, 624_602_100.0],
                    "level_ids": ["NPT_P1", "NPT_P1"],
                    "geometry_sources": ["dwg_accore_polyline", "dwg_accore_line"],
                    "level_assignment_sources": ["default_level", "default_level"],
                    "source_refs": [
                        "C:/repo/ARQ-P1.dwg|I-WALL|Polyline|3",
                        "C:/repo/EST-P1.dwg|S-GRID|Line|4",
                    ],
                },
            },
        ],
    }


def test_build_coordination_report_context_splits_defendable_from_validation() -> None:
    context = build_coordination_report_context(
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={
            "debug_conflict_count": 10,
            "suppressed_element_count": 4,
            "suppressed_elements": [{"suppression_reason": "bounds_fallback"}],
        },
        coordinate_audit_payload={
            "audit_count": 2,
            "audits": [
                {"discipline": "ARQUITECTURA", "audit_status": "eligible"},
                {"discipline": "ESTRUCTURA", "audit_status": "eligible"},
            ],
        },
        pair_schedule_payload={"pairs": [{"scheduled": True}, {"scheduled": False, "block_reason": "level_mismatch"}]},
    )

    assert len(context["defendable_incidents"]) == 1
    assert context["defendable_incidents"][0]["incident_id"] == "incident_0001"
    assert len(context["validation_incidents"]) == 1
    assert context["validation_incidents"][0]["incident_id"] == "incident_0002"
    assert context["reader_sections"]["arquitectura"]["incidents"]
    assert context["noise_summary"]["blocked_pair_count"] == 1


def test_render_coordination_report_markdown_contains_interdisciplinary_sections() -> None:
    markdown = render_coordination_report_markdown(
        project_name="SERENA 18",
        root=Path("C:/repo"),
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={"debug_conflict_count": 10, "suppressed_element_count": 4, "suppressed_elements": []},
        hotspot_payload={"incident_count": 3},
        coordinate_audit_payload={
            "audit_count": 2,
            "audits": [
                {"discipline": "ARQUITECTURA", "audit_status": "eligible"},
                {"discipline": "ESTRUCTURA", "audit_status": "eligible"},
            ],
        },
        pair_schedule_payload={"pairs": [{"scheduled": True}]},
    )

    assert "## Executive Summary" in markdown
    assert "## Defendable Findings" in markdown
    assert "### Arquitectura" in markdown
    assert "### Electrico" in markdown
    assert "### Sanitario" in markdown
    assert "### Mecanico" in markdown
    assert "incident_0001" in markdown


def test_build_analysis_bot_context_uses_exact_counts() -> None:
    context = build_coordination_report_context(
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={"debug_conflict_count": 10, "suppressed_element_count": 4, "suppressed_elements": []},
        hotspot_payload={"incident_count": 3},
        coordinate_audit_payload={
            "audit_count": 2,
            "audits": [
                {
                    "rel_path": "C:/repo/ARQ-P1.dwg",
                    "file_name": "ARQ-P1.dwg",
                    "discipline": "ARQUITECTURA",
                    "level_id": "NPT_P1",
                    "drawing_type": "floor_plan",
                    "audit_status": "eligible",
                    "coordinate_band": "X~168.80M, Y~624.60M",
                    "coordinate_band_key": [337, 1249],
                    "raw_primary_candidate_count": 100,
                    "raw_annotation_count": 10,
                },
                {
                    "rel_path": "C:/repo/EST-P1.dwg",
                    "file_name": "EST-P1.dwg",
                    "discipline": "ESTRUCTURA",
                    "level_id": "NPT_P1",
                    "drawing_type": "formwork",
                    "audit_status": "eligible",
                    "coordinate_band": "X~168.80M, Y~624.60M",
                    "coordinate_band_key": [337, 1249],
                    "raw_primary_candidate_count": 90,
                    "raw_annotation_count": 8,
                },
            ],
        },
        pair_schedule_payload={
            "pairs": [
                {
                    "scheduled": True,
                    "file_a": "C:/repo/ARQ-P1.dwg",
                    "file_b": "C:/repo/EST-P1.dwg",
                    "level_ids": ["NPT_P1", "NPT_P1"],
                    "selection_reason": "promoted_from_coordinate_audit",
                    "score": 0.84,
                    "reason_codes": ["audit_promoted"],
                    "documentary_cohort_relation": "cross_cohort_promoted",
                }
            ]
        },
    )
    bot_context = build_analysis_bot_context(
        project_name="SERENA 18",
        nasas_root=Path("C:/repo"),
        run_label="analysis_06",
        summary_payload=_summary_payload(),
        readiness_payload={"candidate_count": 153, "auto_pair_candidates": [], "promoted_pair_candidates": [{}]},
        coordinate_audit_payload={
            "audits": [
                {
                    "rel_path": "C:/repo/ARQ-P1.dwg",
                    "file_name": "ARQ-P1.dwg",
                    "discipline": "ARQUITECTURA",
                    "level_id": "NPT_P1",
                    "drawing_type": "floor_plan",
                    "audit_status": "eligible",
                    "coordinate_band": "X~168.80M, Y~624.60M",
                    "coordinate_band_key": [337, 1249],
                    "raw_primary_candidate_count": 100,
                    "raw_annotation_count": 10,
                }
            ]
        },
        pair_schedule_payload={
            "pairs": [
                {
                    "scheduled": True,
                    "file_a": "C:/repo/ARQ-P1.dwg",
                    "file_b": "C:/repo/EST-P1.dwg",
                    "level_ids": ["NPT_P1", "NPT_P1"],
                    "selection_reason": "promoted_from_coordinate_audit",
                    "score": 0.84,
                    "reason_codes": ["audit_promoted"],
                    "documentary_cohort_relation": "cross_cohort_promoted",
                }
            ]
        },
        report_context=context,
    )

    assert bot_context["run_summary"]["candidate_files"] == 153
    assert bot_context["run_summary"]["selected_candidates"] == 3
    assert bot_context["run_summary"]["scheduled_pairs"] == 2
    assert bot_context["coverage"]["arquitectura"] == "direct"
    assert "Element-level semantic clash names are not yet resolved." in bot_context["limitations"]


def test_render_coordination_human_report_markdown_explains_readiness_vs_audit() -> None:
    context = build_coordination_report_context(
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={"debug_conflict_count": 10, "suppressed_element_count": 4, "suppressed_elements": []},
        hotspot_payload={"incident_count": 3},
        coordinate_audit_payload={"audit_count": 2, "audits": []},
        pair_schedule_payload={"pairs": []},
    )
    markdown = render_coordination_human_report_markdown(
        project_name="SERENA 18",
        run_label="analysis_06",
        summary_payload=_summary_payload(),
        readiness_payload={
            "promoted_pair_candidates": [
                {
                    "file_a": "C:/repo/ARQ-P1.dwg",
                    "file_b": "C:/repo/EST-P1.dwg",
                    "selection_reason": "promoted_from_coordinate_audit",
                    "level_ids": ["NPT_P1", "NPT_P1"],
                    "score": 0.84,
                }
            ],
            "audit_promotion_summary": {
                "eligible_files": [
                    {
                        "file": "C:/repo/ARQ-P1.dwg",
                        "discipline": "ARQUITECTURA",
                        "level_id": "NPT_P1",
                        "audit_status": "eligible",
                        "coordinate_band": "X~168.80M, Y~624.60M",
                    }
                ]
            },
        },
        coordinate_audit_payload={"audit_count": 2, "audits": []},
        pair_schedule_payload={"pairs": []},
        report_context=context,
    )

    assert "## Que se comparó y por que si fue comparable" in markdown
    assert "coordinate audit" in markdown.lower()
    assert "promoted_from_coordinate_audit" in markdown
