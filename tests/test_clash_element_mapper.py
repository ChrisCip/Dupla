from __future__ import annotations

from core.coordination.clash_element_mapper import map_primary_incidents_to_elements


def _elements_payload(
    left_layer: str = "A-WALL",
    right_layer: str = "S-BEAM",
    *,
    left_geometry_source: str = "dwg_accore_polyline",
    right_geometry_source: str = "dwg_accore_polyline",
    left_geometry_role: str = "primary",
    right_geometry_role: str = "primary",
    left_type: str = "wall_masonry",
    right_type: str = "beam",
    left_type_confidence: str = "medium",
    right_type_confidence: str = "medium",
) -> dict[str, object]:
    return {
        "generated_at": "2026-05-03T00:00:00+00:00",
        "project_name": "SERENA 18",
        "run_label": "analysis_06",
        "files": [
            {
                "source_file": "C:/repo/ARQ-P1.dwg",
                "file_name": "ARQ-P1.dwg",
                "discipline": "ARQUITECTURA",
                "level_id": "NPT_P1",
                "elements": [
                    {
                        "semantic_element_id": "semantic_arch_001",
                        "source_element_id": "arch_001",
                        "source_file": "C:/repo/ARQ-P1.dwg",
                        "source_rel_path": "PLANOS/ARQ/ARQ-P1.dwg",
                        "file_name": "ARQ-P1.dwg",
                        "discipline": "ARQUITECTURA",
                        "level_id": "NPT_P1",
                        "layer": left_layer,
                        "cad_handle": "10",
                        "entity_type": "Polyline",
                        "block_name": None,
                        "element_type": left_type,
                        "element_name": None,
                        "bbox_mm": [0.0, 0.0, 1000.0, 1000.0],
                        "centroid_mm": [500.0, 500.0],
                        "footprint_coords_mm": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 1000.0], [0.0, 1000.0]],
                        "geometry_source": left_geometry_source,
                        "geometry_role": left_geometry_role,
                        "geometry_confidence": "high",
                        "semantic_type_confidence": left_type_confidence,
                        "semantic_type_reason": "layer_token_match",
                        "classification_signals": [f"layer:{left_layer}"],
                        "name_confidence": "low",
                        "metadata": {},
                    }
                ],
            },
            {
                "source_file": "C:/repo/EST-P1.dwg",
                "file_name": "EST-P1.dwg",
                "discipline": "ESTRUCTURA",
                "level_id": "NPT_P1",
                "elements": [
                    {
                        "semantic_element_id": "semantic_struc_001",
                        "source_element_id": "struc_001",
                        "source_file": "C:/repo/EST-P1.dwg",
                        "source_rel_path": "PLANOS/EST/EST-P1.dwg",
                        "file_name": "EST-P1.dwg",
                        "discipline": "ESTRUCTURA",
                        "level_id": "NPT_P1",
                        "layer": right_layer,
                        "cad_handle": "20",
                        "entity_type": "Polyline",
                        "block_name": None,
                        "element_type": right_type,
                        "element_name": None,
                        "bbox_mm": [0.0, 0.0, 1000.0, 1000.0],
                        "centroid_mm": [500.0, 500.0],
                        "footprint_coords_mm": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 1000.0], [0.0, 1000.0]],
                        "geometry_source": right_geometry_source,
                        "geometry_role": right_geometry_role,
                        "geometry_confidence": "high",
                        "semantic_type_confidence": right_type_confidence,
                        "semantic_type_reason": "layer_token_match",
                        "classification_signals": [f"layer:{right_layer}"],
                        "name_confidence": "low",
                        "metadata": {},
                    }
                ],
            },
        ],
    }


def _primary_payload(left_layer: str = "A-WALL", right_layer: str = "S-BEAM") -> dict[str, object]:
    return {
        "generated_at": "2026-05-03T00:00:00+00:00",
        "project_name": "SERENA 18",
        "analysis_profile": "fast_compare",
        "incident_count": 1,
        "incident_conflict_count": 1,
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": ["C:/repo/ARQ-P1.dwg", "C:/repo/EST-P1.dwg"],
                "level_id": "NPT_P1",
                "member_count": 1,
                "plan_centroid_mm": [500.0, 500.0],
                "plan_bounds_mm": [0.0, 0.0, 1000.0, 1000.0],
                "confidence": "medium",
                "representative_conflict": {
                    "source_refs": [
                        f"C:/repo/ARQ-P1.dwg|{left_layer}|Polyline|10",
                        f"C:/repo/EST-P1.dwg|{right_layer}|Polyline|20",
                    ],
                    "plan_intersection_bounds_mm": [0.0, 0.0, 1000.0, 1000.0],
                    "plan_intersection_centroid_mm": [500.0, 500.0],
                },
            }
        ],
    }


def test_map_primary_incidents_to_elements_returns_mapped_case() -> None:
    payload = map_primary_incidents_to_elements(
        generated_at="2026-05-03T00:00:00+00:00",
        project_name="SERENA 18",
        run_label="analysis_06",
        primary_payload=_primary_payload(),
        elements_by_dwg_payload=_elements_payload(),
    )

    assert payload["mapped_incidents_count"] == 1
    assert payload["unmapped_incidents_count"] == 0
    assert payload["mapped"][0]["mapping_confidence"] in {"medium", "high"}
    assert "tipificada como `wall_masonry`" in payload["mapped"][0]["human_sentence"]
    assert "handle_match" in payload["mapped"][0]["mapping_reason_codes"]
    assert payload["mapped"][0]["file_a"]["source_element_id"] == "arch_001"


def test_map_primary_incidents_to_elements_blocks_annotation_layers() -> None:
    payload = map_primary_incidents_to_elements(
        generated_at="2026-05-03T00:00:00+00:00",
        project_name="SERENA 18",
        run_label="analysis_06",
        primary_payload=_primary_payload(left_layer="TITULOS", right_layer="S-BEAM"),
        elements_by_dwg_payload=_elements_payload(left_layer="TITULOS", right_layer="S-BEAM"),
    )

    assert payload["mapped_incidents_count"] == 0
    assert payload["unmapped_incidents_count"] == 1
    assert payload["unmapped"][0]["mapping_confidence"] == "unmapped"
    assert "missing_entity_side" not in payload["unmapped"][0]["mapping_reason_codes"]


def test_map_primary_incidents_to_elements_caps_low_trust_layers() -> None:
    payload = map_primary_incidents_to_elements(
        generated_at="2026-05-03T00:00:00+00:00",
        project_name="SERENA 18",
        run_label="analysis_06",
        primary_payload=_primary_payload(left_layer="MARCO", right_layer="EST_PROYECCION"),
        elements_by_dwg_payload=_elements_payload(left_layer="MARCO", right_layer="EST_PROYECCION"),
    )

    assert payload["mapped_incidents_count"] == 1
    assert payload["mapped"][0]["mapping_confidence"] in {"low", "medium"}
    assert "low_trust_layer_capped" in payload["mapped"][0]["mapping_reason_codes"]


def test_map_primary_incidents_to_elements_caps_proxy_geometry() -> None:
    payload = map_primary_incidents_to_elements(
        generated_at="2026-05-03T00:00:00+00:00",
        project_name="SERENA 18",
        run_label="analysis_06",
        primary_payload=_primary_payload(),
        elements_by_dwg_payload=_elements_payload(
            left_geometry_source="dwg_accore_bbox",
            right_geometry_source="dwg_accore_bbox",
            left_geometry_role="suppressed",
            right_geometry_role="suppressed",
        ),
    )

    assert payload["mapped_incidents_count"] == 1
    assert payload["mapped"][0]["mapping_confidence"] == "low"
    assert "double_proxy_geometry_cap" in payload["mapped"][0]["mapping_reason_codes"]
