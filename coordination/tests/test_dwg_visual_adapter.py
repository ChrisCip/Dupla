"""Tests for DWG visual source adapter."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from coordination.core.clash import ClashConflict, ClashIncident
from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.dwg_visual_adapter import (
    COORD_TRANSFORM_UNAVAILABLE,
    RUN_NO_VISUAL_WARNING,
    LocalizationStatus,
    VisualSourceKind,
    build_incident_comparison_panels,
    build_placeholder_panel,
    build_visual_panel,
    crop_visual_to_bounds,
    get_visual_source_for_dwg,
    project_dwg_bounds_to_image_coords,
)


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


def _make_incident() -> ClashIncident:
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
    return ClashIncident(
        incident_id="incident_0001",
        file_pair=("a.dwg", "b.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=conflict,
        plan_centroid_mm=(750.0, 750.0),
        plan_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
    )


def test_get_visual_source_none_for_missing_file() -> None:
    source = get_visual_source_for_dwg("missing.dwg")
    assert source.kind == VisualSourceKind.NONE


def test_get_visual_source_finds_sidecar_png(tmp_path: Path) -> None:
    dwg = tmp_path / "plan_a.dwg"
    dwg.write_text("stub", encoding="utf-8")
    png = tmp_path / "plan_a.png"
    doc = fitz.open()
    page = doc.new_page(width=1000, height=800)
    page.draw_rect(fitz.Rect(0, 0, 1000, 800), color=(0.8, 0.8, 0.8), fill=(0.9, 0.9, 0.9))
    doc.save(png)
    doc.close()

    source = get_visual_source_for_dwg(str(dwg))
    assert source.kind == VisualSourceKind.SIDECAR_RASTER
    assert source.image_path == png.resolve()
    assert source.localization == LocalizationStatus.FULL_IMAGE_ONLY
    assert COORD_TRANSFORM_UNAVAILABLE in (source.note or "")


def test_project_dwg_bounds_to_image_coords() -> None:
    pixel_bounds = project_dwg_bounds_to_image_coords(
        (250.0, 250.0, 750.0, 750.0),
        image_cad_bounds=(0.0, 0.0, 1000.0, 1000.0),
        image_width_px=1000,
        image_height_px=500,
    )
    assert pixel_bounds == (250, 125, 750, 375)


def test_crop_visual_to_bounds(tmp_path: Path) -> None:
    png_path = tmp_path / "full.png"
    doc = fitz.open()
    page = doc.new_page(width=1000, height=1000)
    page.draw_rect(fitz.Rect(0, 0, 1000, 1000), fill=(1, 1, 1))
    page.draw_rect(fitz.Rect(400, 400, 600, 600), fill=(1, 0, 0))
    doc.save(png_path)
    doc.close()
    png_bytes = png_path.read_bytes()

    cropped = crop_visual_to_bounds(
        png_bytes,
        image_cad_bounds=(0.0, 0.0, 1000.0, 1000.0),
        crop_cad_bounds=(400.0, 400.0, 600.0, 600.0),
        padding_mm=0.0,
    )
    assert cropped is not None
    out_bytes, out_w, out_h = cropped
    assert out_w == 200
    assert out_h == 200
    assert len(out_bytes) > 100


def test_build_placeholder_panel() -> None:
    panel = build_placeholder_panel(
        panel_id="p1",
        file_label="Plano A",
        file_path="missing.dwg",
    )
    assert panel.source_kind == VisualSourceKind.NONE
    assert panel.has_geometry is False
    assert "no disponible" in panel.svg_content.lower()


def test_build_visual_panel_raster_without_mapping_shows_full_image_no_marker(tmp_path: Path) -> None:
    dwg = tmp_path / "plan.dwg"
    dwg.write_text("stub", encoding="utf-8")
    png = tmp_path / "plan.png"
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.draw_rect(fitz.Rect(0, 0, 400, 300), fill=(0.85, 0.85, 0.85))
    doc.save(png)
    doc.close()

    source = get_visual_source_for_dwg(str(dwg))
    panel = build_visual_panel(
        panel_id="p1",
        file_path=str(dwg),
        file_label="Plano A",
        visual_source=source,
        clash_bounds_mm=(100.0, 100.0, 200.0, 200.0),
        marker_code="T-A1",
    )
    assert panel.has_geometry is True
    assert panel.localization == LocalizationStatus.FULL_IMAGE_ONLY
    assert COORD_TRANSFORM_UNAVAILABLE in (panel.warning or "")
    assert "clash-marker" not in panel.svg_content
    assert "data:image/png;base64," in panel.svg_content


def test_build_visual_panel_raster_with_mapping_draws_marker(tmp_path: Path) -> None:
    dwg = tmp_path / "plan.dwg"
    dwg.write_text("stub", encoding="utf-8")
    png = tmp_path / "plan.png"
    doc = fitz.open()
    page = doc.new_page(width=1000, height=1000)
    page.draw_rect(fitz.Rect(0, 0, 1000, 1000), fill=(0.9, 0.9, 0.9))
    doc.save(png)
    doc.close()

    source = get_visual_source_for_dwg(
        str(dwg),
        file_cad_bounds_mm={str(dwg): (0.0, 0.0, 1000.0, 1000.0)},
    )
    panel = build_visual_panel(
        panel_id="p1",
        file_path=str(dwg),
        file_label="Plano A",
        visual_source=source,
        clash_bounds_mm=(400.0, 400.0, 600.0, 600.0),
        marker_code="T-A1",
    )
    assert panel.localization == LocalizationStatus.EXACT
    assert "clash-marker" in panel.svg_content


def test_build_incident_comparison_panels_footprint_fallback() -> None:
    incident = _make_incident()
    elements = [
        _make_element("a", "a.dwg", Discipline.ARCH),
        _make_element("b", "b.dwg", Discipline.STRUC),
    ]
    left, right, has_visual, warnings = build_incident_comparison_panels(
        incident,
        elements,
        marker_code="N-A1",
    )
    assert has_visual
    assert left.source_kind == VisualSourceKind.FOOTPRINT_GEOMETRY
    assert right.source_kind == VisualSourceKind.FOOTPRINT_GEOMETRY
    assert left.svg_content.startswith("<svg")
    assert "clash-marker" in left.svg_content


def test_build_incident_comparison_panels_no_elements_uses_placeholder() -> None:
    incident = _make_incident()
    left, right, has_visual, warnings = build_incident_comparison_panels(
        incident,
        None,
        marker_code="N-A1",
    )
    assert has_visual is False
    assert left.source_kind == VisualSourceKind.NONE
    assert RUN_NO_VISUAL_WARNING in warnings
