from __future__ import annotations

from pathlib import Path

from coordination.reporting.reporting import (
    build_analysis_bot_context,
    build_coordination_report_context,
    render_coordination_human_report_markdown,
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
        "incident_count": 1,
        "incident_conflict_count": 2,
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": ["C:/repo/ARQ-P1.dwg", "C:/repo/EST-P1.dwg"],
                "level_id": "NPT_P1",
                "member_count": 2,
                "plan_centroid_mm": [168_800_000.0, 624_600_000.0],
                "plan_bounds_mm": [168_799_000.0, 624_599_000.0, 168_801_000.0, 624_601_000.0],
                "confidence": "medium",
                "geometry_sources": ["dwg_accore_polyline", "dwg_accore_polyline"],
                "representative_conflict": {
                    "discipline_a": "ARQUITECTURA",
                    "discipline_b": "ESTRUCTURA",
                    "confidence": "medium",
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
            }
        ],
    }


def test_build_analysis_bot_context_exposes_semantic_mapping_summary() -> None:
    context = build_coordination_report_context(
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={"debug_conflict_count": 10, "suppressed_element_count": 4, "suppressed_elements": []},
        coordinate_audit_payload={"audit_count": 0, "audits": []},
        pair_schedule_payload={"pairs": []},
    )

    bot_context = build_analysis_bot_context(
        project_name="SERENA 18",
        nasas_root=Path("C:/repo"),
        run_label="analysis_06",
        summary_payload=_summary_payload(),
        readiness_payload={"candidate_count": 153},
        coordinate_audit_payload={"audits": []},
        pair_schedule_payload={"pairs": []},
        report_context=context,
        semantic_elements_payload={
            "file_count": 2,
            "element_count": 12,
            "element_type_mix": {"unknown_architecture": 7, "unknown_structure": 5},
        },
        clash_element_links_payload={
            "mapped_incidents_count": 1,
            "unmapped_incidents_count": 0,
            "mapping_confidence_mix": {"medium": 1},
            "mapped": [
                {
                    "incident_id": "incident_0001",
                    "mapping_confidence": "medium",
                    "file_a": {"element_type": "wall_masonry", "semantic_type_confidence": "medium"},
                    "file_b": {"element_type": "beam", "semantic_type_confidence": "medium"},
                }
            ],
            "unmapped": [],
        },
    )

    assert bot_context["elements_by_dwg_summary"]["element_count"] == 12
    assert bot_context["clash_element_links_summary"]["mapped_incidents_count"] == 1
    assert bot_context["clash_element_links_summary"]["publishable_semantic_type_count"] == 1
    assert bot_context["mapped_incidents_count"] == 1
    assert "Low-confidence mapping must not be verbalized" in " ".join(bot_context["element_mapping_limitations"])


def test_render_coordination_human_report_markdown_keeps_low_mapping_conservative() -> None:
    context = build_coordination_report_context(
        summary_payload=_summary_payload(),
        primary_payload=_primary_payload(),
        debug_payload={"debug_conflict_count": 10, "suppressed_element_count": 4, "suppressed_elements": []},
        coordinate_audit_payload={"audit_count": 0, "audits": []},
        pair_schedule_payload={"pairs": []},
    )
    markdown = render_coordination_human_report_markdown(
        project_name="SERENA 18",
        run_label="analysis_06",
        summary_payload=_summary_payload(),
        readiness_payload={"promoted_pair_candidates": []},
        coordinate_audit_payload={"audit_count": 0, "audits": []},
        pair_schedule_payload={"pairs": []},
        report_context=context,
        clash_element_links_payload={
            "mapped": [
                {
                    "incident_id": "incident_0001",
                    "mapping_confidence": "low",
                    "file_a": {"element_name": "PUERTA P-03", "name_confidence": "low", "cad_handle": "1", "entity_type": "Polyline", "layer": "I-WALL", "source_element_id": "arch_001"},
                    "file_b": {"element_name": "VIGA V-12", "name_confidence": "low", "cad_handle": "2", "entity_type": "Polyline", "layer": "S-BEAM", "source_element_id": "struc_001"},
                }
            ]
        },
    )

    assert "PUERTA P-03" not in markdown
    assert "`I-WALL / S-BEAM`" in markdown
    assert "1/Polyline/I-WALL/arch_001" in markdown
