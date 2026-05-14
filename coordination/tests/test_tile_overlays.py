"""Tests for annotated clash tiles and human report image embedding."""

from __future__ import annotations

from coordination.reporting.reporting import (
    render_coordination_human_report_html,
    render_coordination_human_report_markdown,
)
from coordination.reporting.tile_renderer import RenderedTile, render_annotated_tile
from coordination.semantic.vision_validator import (
    VisionClashAssessment,
    VisionElementResult,
    VisionTileResult,
)


def _base_tile() -> RenderedTile:
    return RenderedTile(
        tile_id="incident_0001",
        svg_content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" width="800" height="400"><rect width="100%" height="100%" fill="#fff"/></svg>',
        bbox_cad_mm=(0.0, 0.0, 2000.0, 1000.0),
        width_px=800,
        height_px=400,
        scale_mm_per_px=2.5,
        elements_in_tile=["e1"],
        texts_in_tile=[],
        incident_id="incident_0001",
    )


def _vision_result(appears_real: bool = True) -> VisionTileResult:
    return VisionTileResult(
        tile_id="incident_0001",
        incident_id="incident_0001",
        elements_identified=[
            VisionElementResult(
                element_id="e1",
                semantic_type="puerta",
                name="P-01",
                confidence="high",
                evidence="texto cercano",
            )
        ],
        clash_assessment=VisionClashAssessment(
            appears_real=appears_real,
            reason="intersección visible",
            severity_visual="major",
        ),
        model_used="test-model",
        raw_response="{}",
        success=True,
    )


def _report_context() -> dict:
    return {
        "counts": {"scheduled_pairs": 1, "scheduled_files": 2, "debug_conflicts": 0, "suppressed_elements": 0},
        "defendable_incidents": [
            {
                "incident_id": "incident_0001",
                "priority": "P1",
                "severity": "critical",
                "report_confidence": "high",
                "level_id": "NPT_P1",
                "discipline_pair": "ARQUITECTURA / ESTRUCTURA",
                "location_short": "NPT_P1; (100, 100) mm",
                "layer_pair": "A-WALL / S-COL",
                "recommended_action": "Coordinar ajuste",
            }
        ],
        "validation_incidents": [],
        "reader_sections": {},
        "noise_summary": {},
    }


def test_render_annotated_tile_with_vision() -> None:
    tile = render_annotated_tile(_base_tile(), _vision_result(), severity="major")

    assert "MAJOR" in tile.svg_content
    assert "CLASH REAL" in tile.svg_content


def test_render_annotated_tile_without_vision() -> None:
    tile = render_annotated_tile(_base_tile(), None, severity="minor")

    assert "MINOR" in tile.svg_content
    assert "CLASH REAL" not in tile.svg_content


def test_render_annotated_tile_severity_colors() -> None:
    assert "#DC2626" in render_annotated_tile(_base_tile(), severity="critical").svg_content
    assert "#D97706" in render_annotated_tile(_base_tile(), severity="major").svg_content
    assert "#2563EB" in render_annotated_tile(_base_tile(), severity="minor").svg_content
    assert "#6B7280" in render_annotated_tile(_base_tile(), severity="noise").svg_content


def test_render_annotated_tile_element_labels() -> None:
    tile = render_annotated_tile(_base_tile(), _vision_result(), severity="major")

    assert "e1 · puerta: P-01" in tile.svg_content
    assert "#16A34A" in tile.svg_content


def test_render_annotated_tile_border() -> None:
    tile = render_annotated_tile(_base_tile(), severity="critical")

    assert 'stroke="#DC2626"' in tile.svg_content
    assert 'stroke-width="3"' in tile.svg_content


def test_html_report_contains_tiles() -> None:
    markdown = "- `incident_0001` | `P1` | `critical` | `high`\n![Visualización del clash](tiles/incident_0001_annotated.svg)"

    html = render_coordination_human_report_html(project_name="Proyecto", run_label="run", markdown=markdown)

    assert "tile-container" in html
    assert "<img" in html
    assert "incident_0001_annotated.svg" in html


def test_html_report_traffic_light() -> None:
    markdown = "\n".join(
        [
            "# Report",
            "- `i1` | `P1` | `critical` | `high`",
            "- `i2` | `P1` | `critical` | `high`",
            "- `i3` | `P1` | `critical` | `high`",
            "- `i4` | `P3` | `minor` | `medium`",
            "- `i5` | `P3` | `minor` | `medium`",
        ]
    )

    html = render_coordination_human_report_html(project_name="Proyecto", run_label="run", markdown=markdown)

    assert "3 críticos" in html
    assert "2 menores" in html


def test_markdown_report_contains_tile_ref() -> None:
    markdown = render_coordination_human_report_markdown(
        project_name="Proyecto",
        run_label="run",
        summary_payload={},
        readiness_payload={},
        coordinate_audit_payload={},
        pair_schedule_payload={},
        report_context=_report_context(),
    )

    assert "![Visualización del clash](tiles/incident_0001_annotated.svg)" in markdown
