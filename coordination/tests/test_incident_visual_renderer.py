"""Tests for full-plan base SVG + per-incident overlay renderer (PR 3)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.incident_visual_renderer import (
    INCIDENT_SEVERITY_COLORS,
    build_overlay_short_label,
    compose_full_plan_incident_svg,
    compute_dwg_full_extent,
    is_confirmed_incident_visual,
    render_all_incident_visual_artifacts,
    render_base_full_plan_svg,
    render_incident_overlay_svg,
    resolve_base_file_index,
    viewbox_from_bounds,
)
from coordination.reporting.tile_renderer import _cad_to_svg


def _element(
    element_id: str,
    discipline: Discipline,
    footprint: list[tuple[float, float]],
    *,
    source_file: str,
    level_id: str = "P1",
) -> Element25D:
    return Element25D(
        id=element_id,
        source_ref=f"{source_file}|LAYER|LINE|{element_id}",
        discipline=discipline,
        category=f"LINE:{discipline.value}",
        footprint_coords_mm=footprint,
        z_data=ZInterval(
            level_id=level_id,
            z_ref_raw_mm=0.0,
            thickness_mm=3000.0,
            measurement_uncertainty_mm=0.0,
        ),
        metadata={"level_id": level_id, "source_file": source_file},
    )


def _confirmed_incident(**overrides) -> dict:
    base = {
        "incident_id": "incident_0001",
        "file_pair": ["EST-ESTRUCTURA.dwg", "HID-SAN-01.dwg"],
        "level_id": "P1",
        "member_count": 1,
        "plan_bounds_mm": [4800, 4800, 5200, 5200],
        "plan_centroid_mm": [5000, 5000],
        "representative_conflict": {
            "discipline_a": "ESTRUCTURA",
            "discipline_b": "PLOMERIA",
            "clash_type": "HARD",
            "overlap_depth_z_mm": 120.0,
            "plan_intersection_area_mm2": 25_000.0,
            "plan_intersection_bounds_mm": [4900, 4900, 5100, 5100],
            "raw_layers": ["EST_MURO", "HID_TUBERIA"],
        },
    }
    base.update(overrides)
    return base


def _elements_for_interdisciplinary() -> list[Element25D]:
    base_file = "EST-ESTRUCTURA.dwg"
    other_file = "HID-SAN-01.dwg"
    return [
        _element(
            "wall",
            Discipline.STRUC,
            [(0, 0), (10000, 0), (10000, 2000), (0, 2000)],
            source_file=base_file,
        ),
        _element(
            "pipe",
            Discipline.MEP_PLUMBING,
            [(4800, 4800), (5200, 4800), (5200, 5200), (4800, 5200)],
            source_file=other_file,
        ),
    ]


def test_compute_dwg_full_extent_unions_entities() -> None:
    elements = _elements_for_interdisciplinary()
    result = compute_dwg_full_extent(elements, base_file="EST-ESTRUCTURA.dwg", level_id="P1")
    assert result.element_count == 1
    assert result.bounds[0] <= 0.0
    assert result.bounds[2] >= 10000.0


def test_compute_dwg_full_extent_ignores_invalid() -> None:
    elements = [
        _element("bad", Discipline.STRUC, [(0, 0), (100, 0)], source_file="A.dwg"),
        _element("good", Discipline.STRUC, [(0, 0), (100, 0), (100, 100), (0, 100)], source_file="A.dwg"),
    ]
    result = compute_dwg_full_extent(elements, base_file="A.dwg")
    assert result.element_count == 1
    assert "ignored_invalid_element:bad" in result.warnings


def test_compute_dwg_full_extent_fallback_without_geometry() -> None:
    result = compute_dwg_full_extent([], base_file="EMPTY.dwg")
    assert "full_extent_fallback_default" in result.warnings
    assert result.bounds[2] > result.bounds[0]


def test_render_base_full_plan_svg_has_viewbox() -> None:
    elements = _elements_for_interdisciplinary()
    extent = compute_dwg_full_extent(elements, base_file="EST-ESTRUCTURA.dwg", level_id="P1")
    viewbox = viewbox_from_bounds(extent.bounds)
    svg, _, _ = render_base_full_plan_svg(
        base_file="EST-ESTRUCTURA.dwg",
        level_id="P1",
        elements=elements,
        viewbox=viewbox,
        extent=extent,
    )
    assert 'viewBox="0 0' in svg
    assert "base-full-plan" in svg
    assert f'data-cad-bounds="{",".join(f"{v:.3f}" for v in viewbox.cad_bounds)}"' in svg


def test_base_plan_cached_once_per_dwg_level(tmp_path: Path) -> None:
    elements = _elements_for_interdisciplinary()
    manifest = render_all_incident_visual_artifacts(
        [_confirmed_incident(), _confirmed_incident(incident_id="incident_0002", plan_bounds_mm=[4950, 4950, 5050, 5050])],
        all_elements=elements,
        output_dir=tmp_path,
    )
    assert len(manifest["base_plans"]) == 1
    base_files = list((tmp_path / "tiles" / "base_full").glob("*.svg"))
    assert len(base_files) == 1


def test_render_incident_overlay_rejects_candidate_only() -> None:
    viewbox = viewbox_from_bounds((0, 0, 10000, 10000))
    with pytest.raises(ValueError, match="candidate-only"):
        render_incident_overlay_svg({"incident_id": "x", "candidate_only": True}, viewbox=viewbox)


def test_render_incident_overlay_severity_color_and_labels() -> None:
    incident = _confirmed_incident()
    viewbox = viewbox_from_bounds((0, 0, 10000, 10000))
    svg, _ = render_incident_overlay_svg(incident, viewbox=viewbox, severity="critical")
    assert INCIDENT_SEVERITY_COLORS["critical"] in svg
    assert "INC-001" in svg
    assert "Tubería cruza muro estructural" in svg


def test_compose_full_page_contains_base_and_overlay() -> None:
    elements = _elements_for_interdisciplinary()
    extent = compute_dwg_full_extent(elements, base_file="EST-ESTRUCTURA.dwg", level_id="P1")
    viewbox = viewbox_from_bounds(extent.bounds)
    base_svg, _, _ = render_base_full_plan_svg(
        base_file="EST-ESTRUCTURA.dwg",
        level_id="P1",
        elements=elements,
        viewbox=viewbox,
        extent=extent,
    )
    overlay_svg, _ = render_incident_overlay_svg(_confirmed_incident(), viewbox=viewbox)
    composed = compose_full_plan_incident_svg(base_svg, overlay_svg)
    assert "base-full-plan" in composed
    assert "incident-overlay" in composed


def test_interdisciplinary_overlay_on_structure_base(tmp_path: Path) -> None:
    elements = _elements_for_interdisciplinary()
    manifest = render_all_incident_visual_artifacts(
        [_confirmed_incident()],
        all_elements=elements,
        output_dir=tmp_path,
    )
    entry = manifest["incidents"]["incident_0001"]
    assert entry["base_full_plan_tile_path"].startswith("base_full/")
    assert Path(tmp_path / "tiles" / entry["composed_full_page_tile_path"]).is_file()
    assert entry["has_real_visual"] is True
    assert build_overlay_short_label(_confirmed_incident()) == (
        "INC-001: Tubería cruza muro estructural. Coordinar desvío."
    )


def test_candidate_only_skipped_in_manifest(tmp_path: Path) -> None:
    manifest = render_all_incident_visual_artifacts(
        [_confirmed_incident(candidate_only=True), _confirmed_incident(incident_id="incident_0002")],
        all_elements=_elements_for_interdisciplinary(),
        output_dir=tmp_path,
    )
    assert manifest["skipped_candidates"] == 1
    assert "incident_0001" not in manifest["incidents"]
    assert "incident_0002" in manifest["incidents"]


def test_resolve_base_file_index_architecture_wins() -> None:
    assert resolve_base_file_index(discipline_a="ARQUITECTURA", discipline_b="PLOMERIA") == (0, 1)


def test_manifest_written_to_disk(tmp_path: Path) -> None:
    render_all_incident_visual_artifacts(
        [_confirmed_incident()],
        all_elements=_elements_for_interdisciplinary(),
        output_dir=tmp_path,
    )
    manifest_path = tmp_path / "incident_visual_manifest.json"
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["incidents"]["incident_0001"]["composed_full_page_tile_path"].startswith("composed/")


def _extract_viewbox(svg: str) -> str:
    match = re.search(r'viewBox="([^"]+)"', svg)
    assert match is not None
    return match.group(1)


def test_base_overlay_compose_share_identical_viewbox() -> None:
    elements = _elements_for_interdisciplinary()
    extent = compute_dwg_full_extent(elements, base_file="EST-ESTRUCTURA.dwg", level_id="P1")
    viewbox = viewbox_from_bounds(extent.bounds)
    base_svg, _, _ = render_base_full_plan_svg(
        base_file="EST-ESTRUCTURA.dwg",
        level_id="P1",
        elements=elements,
        viewbox=viewbox,
        extent=extent,
    )
    overlay_svg, _ = render_incident_overlay_svg(_confirmed_incident(), viewbox=viewbox)
    composed = compose_full_plan_incident_svg(base_svg, overlay_svg)
    base_vb = _extract_viewbox(base_svg)
    assert _extract_viewbox(overlay_svg) == base_vb
    assert _extract_viewbox(composed) == base_vb


def test_overlay_cloud_uses_same_cad_y_flip_as_base() -> None:
    cad_bounds = (0.0, 0.0, 1000.0, 1000.0)
    viewbox = viewbox_from_bounds(cad_bounds)
    incident = _confirmed_incident()
    incident["representative_conflict"]["plan_intersection_bounds_mm"] = [100.0, 100.0, 200.0, 200.0]
    overlay, _ = render_incident_overlay_svg(incident, viewbox=viewbox)
    _, sy = _cad_to_svg(100.0, 200.0, 0.0, 1000.0, viewbox.scale)
    assert f"{sy:.2f}" in overlay


def test_overlay_escapes_malicious_short_label() -> None:
    viewbox = viewbox_from_bounds((0, 0, 10000, 10000))
    malicious = '<script>alert(1)</script> & "quotes"'
    overlay, _ = render_incident_overlay_svg(
        _confirmed_incident(),
        viewbox=viewbox,
        short_label=malicious,
    )
    assert "<script>" not in overlay
    assert "&lt;script&gt;" in overlay
    assert "&amp;" in overlay
    assert "&quot;" in overlay
