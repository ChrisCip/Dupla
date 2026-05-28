"""Tests for elements_by_dwg.json loading into Element25D."""

from __future__ import annotations

from coordination.reporting.element_loaders import (
    semantic_element_from_export_dict,
    semantic_to_element25d,
)


def test_semantic_element_from_export_dict_tolerates_extra_keys() -> None:
    raw = {
        "semantic_element_id": "semantic_test",
        "source_element_id": "src_test",
        "element_id": "legacy_id",
        "source_file": r"C:\repo\plan.dwg",
        "file_name": "plan.dwg",
        "discipline": "ARQUITECTURA",
        "level_id": "NPT_P1",
        "layer": "MUROS",
        "cad_handle": "ABC",
        "entity_type": "Polyline",
        "element_type": "wall_masonry",
        "bbox": [0.0, 0.0, 1000.0, 1000.0],
        "centroid": [500.0, 500.0],
        "geometry_kind": "polyline",
        "evidence": {"note": "legacy"},
    }
    semantic = semantic_element_from_export_dict(raw)
    assert semantic is not None
    element = semantic_to_element25d(semantic)
    assert element.source_ref.startswith(r"C:\repo\plan.dwg")
    assert len(element.footprint_coords_mm) >= 3
