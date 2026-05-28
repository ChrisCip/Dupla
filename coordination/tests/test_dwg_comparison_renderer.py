"""Tests for split DWG comparison panel rendering."""

from __future__ import annotations

from coordination.core.clash import ClashConflict, ClashIncident
from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.element_loaders import load_elements_for_visual_reporting, semantic_to_element25d
from coordination.reporting.tile_renderer import render_dwg_comparison_panels
from coordination.semantic.semantic_elements import SemanticElement25D


def _make_element(element_id: str, file_name: str, discipline: Discipline) -> Element25D:
    return Element25D(
        id=element_id,
        source_ref=f"{file_name}|layer|LINE|{element_id}",
        discipline=discipline,
        category="LINE",
        footprint_coords_mm=[(500, 500), (1000, 500), (1000, 1000), (500, 1000)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=3000.0, measurement_uncertainty_mm=0.0),
        metadata={"level_id": "NPT_P1", "file_level_id": f"{file_name}|NPT_P1"},
    )


def test_render_dwg_comparison_panels_produces_two_svgs() -> None:
    conflict = ClashConflict(
        element_id_a="a",
        element_id_b="b",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=100.0,
        z_overlap_range_project_mm=(0.0, 100.0),
        plan_intersection_area_mm2=250000.0,
        plan_intersection_centroid_mm=(750.0, 750.0),
        plan_intersection_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        source_refs=("a.dwg|layer|LINE|a", "b.dwg|layer|LINE|b"),
    )
    incident = ClashIncident(
        incident_id="incident_0001",
        file_pair=("a.dwg", "b.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=conflict,
        plan_centroid_mm=(750.0, 750.0),
        plan_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
    )
    elements = [
        _make_element("a", "a.dwg", Discipline.ARCH),
        _make_element("b", "b.dwg", Discipline.STRUC),
    ]
    left, right, has_visual = render_dwg_comparison_panels(
        incident,
        elements,
        marker_code="N-A1",
    )
    assert has_visual
    assert left.svg_content.startswith("<svg")
    assert right.svg_content.startswith("<svg")
    assert left.elements_in_tile != right.elements_in_tile


def test_cloud_marker_style() -> None:
    conflict = ClashConflict(
        element_id_a="a",
        element_id_b="b",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=100.0,
        z_overlap_range_project_mm=(0.0, 100.0),
        plan_intersection_area_mm2=250000.0,
        plan_intersection_centroid_mm=(750.0, 750.0),
        plan_intersection_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        source_refs=("a.dwg|layer|LINE|a", "b.dwg|layer|LINE|b"),
    )
    incident = ClashIncident(
        incident_id="incident_0001",
        file_pair=("a.dwg", "b.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=conflict,
        plan_centroid_mm=(750.0, 750.0),
        plan_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
    )
    left, _, _ = render_dwg_comparison_panels(
        incident,
        [_make_element("a", "a.dwg", Discipline.ARCH), _make_element("b", "b.dwg", Discipline.STRUC)],
        marker_code="N-A1",
        marker_style="cloud",
    )
    assert "#EC4899" in left.svg_content


def test_semantic_element_windows_path_matches_incident_basename() -> None:
    full_path = r"C:\repo\Serena 18 -PLANTA PISOS 10-10-2022.dwg"
    semantic = SemanticElement25D(
        semantic_element_id="sem1",
        source_element_id="raw1",
        source_file=full_path,
        file_name="Serena 18 -PLANTA PISOS 10-10-2022.dwg",
        discipline="ARQUITECTURA",
        level_id="NPT_P1",
        layer="MUROS",
        cad_handle="ABC",
        entity_type="Polyline",
        element_type="wall_masonry",
        footprint_coords_mm=[(168800000, 624600000), (168820000, 624600000), (168820000, 624620000), (168800000, 624620000)],
        bbox_mm=(168800000.0, 624600000.0, 168820000.0, 624620000.0),
    )
    element = semantic_to_element25d(semantic)
    conflict = ClashConflict(
        element_id_a="a",
        element_id_b="b",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=100.0,
        z_overlap_range_project_mm=(0.0, 100.0),
        plan_intersection_area_mm2=250000.0,
        plan_intersection_centroid_mm=(168810000.0, 624610000.0),
        plan_intersection_bounds_mm=(168805000.0, 624605000.0, 168815000.0, 624615000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        source_refs=(f"{full_path}|MUROS|Polyline|a", "est.dwg|layer|LINE|b"),
    )
    incident = ClashIncident(
        incident_id="incident_0001",
        file_pair=(full_path, "EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=conflict,
        plan_centroid_mm=(168810000.0, 624610000.0),
        plan_bounds_mm=(168805000.0, 624605000.0, 168815000.0, 624615000.0),
    )
    left, _, has_visual = render_dwg_comparison_panels(incident, [element], marker_code="S-A1")
    assert has_visual
    assert left.elements_in_tile
