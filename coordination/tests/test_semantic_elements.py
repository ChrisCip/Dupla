from __future__ import annotations

from pathlib import Path

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.semantic.semantic_elements import (
    build_semantic_elements_from_accore_payload,
    export_elements_by_dwg_json,
)


def test_build_semantic_elements_from_accore_payload_preserves_traceability() -> None:
    raw = Element25D(
        id="arch_001",
        source_ref="C:/repo/ARQ-P1.dwg|A-WALL|Polyline|10",
        discipline=Discipline.ARCH,
        category="Polyline:A-WALL",
        footprint_coords_mm=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 1000.0), (0.0, 1000.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0),
        metadata={
            "source_file": "C:/repo/ARQ-P1.dwg",
            "source_rel_path": "PLANOS/ARQ/ARQ-P1.dwg",
            "file": "ARQ-P1.dwg",
            "layer": "A-WALL",
            "cad_handle": "10",
            "entity_type": "Polyline",
            "geometry_source": "dwg_accore_polyline",
            "geometry_role": "primary",
            "geometry_confidence": "high",
            "file_level_id": "NPT_P1",
        },
    )

    items = build_semantic_elements_from_accore_payload(
        raw_elements=[raw],
        source_file=Path("C:/repo/ARQ-P1.dwg"),
        source_rel_path="PLANOS/ARQ/ARQ-P1.dwg",
        payload={"Entities": [{"Handle": "10", "Type": "Polyline", "Layer": "A-WALL"}]},
    )

    assert len(items) == 1
    item = items[0]
    assert item.source_file == "C:/repo/ARQ-P1.dwg"
    assert item.source_rel_path == "PLANOS/ARQ/ARQ-P1.dwg"
    assert item.level_id == "NPT_P1"
    assert item.layer == "A-WALL"
    assert item.cad_handle == "10"
    assert item.entity_type == "Polyline"
    assert item.element_type == "wall_masonry"
    assert item.semantic_type_confidence == "medium"
    assert item.semantic_type_reason == "layer_token_match"
    assert item.element_name is None
    assert item.bbox_mm == (0.0, 0.0, 2000.0, 1000.0)
    assert item.centroid_mm == (1000.0, 500.0)
    assert item.geometry_confidence == "high"


def test_export_elements_by_dwg_json_summarizes_unknown_types() -> None:
    raw = Element25D(
        id="struc_001",
        source_ref="C:/repo/EST-P1.dwg|S-BEAM|Polyline|20",
        discipline=Discipline.STRUC,
        category="Polyline:S-BEAM",
        footprint_coords_mm=[(10.0, 10.0), (1010.0, 10.0), (1010.0, 510.0), (10.0, 510.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=400.0),
        metadata={
            "source_file": "C:/repo/EST-P1.dwg",
            "file": "EST-P1.dwg",
            "layer": "S-BEAM",
            "cad_handle": "20",
            "entity_type": "Polyline",
            "geometry_confidence": "medium",
            "file_level_id": "NPT_P1",
        },
    )
    semantic = build_semantic_elements_from_accore_payload(
        raw_elements=[raw],
        source_file=Path("C:/repo/EST-P1.dwg"),
        payload=None,
    )

    payload = export_elements_by_dwg_json(
        generated_at="2026-05-03T00:00:00+00:00",
        project_name="SERENA 18",
        run_label="analysis_06",
        semantic_elements=semantic,
    )

    assert payload["file_count"] == 1
    assert payload["element_count"] == 1
    assert payload["element_type_mix"]["beam"] == 1
    assert payload["semantic_type_confidence_mix"]["medium"] == 1
    assert payload["files"][0]["discipline"] == "ESTRUCTURA"


def test_build_semantic_elements_keeps_ambiguous_layers_as_unknown() -> None:
    raw = Element25D(
        id="arch_002",
        source_ref="C:/repo/ARQ-P1.dwg|MARCO|Polyline|11",
        discipline=Discipline.ARCH,
        category="Polyline:MARCO",
        footprint_coords_mm=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 1000.0), (0.0, 1000.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0),
        metadata={
            "source_file": "C:/repo/ARQ-P1.dwg",
            "file": "ARQ-P1.dwg",
            "layer": "MARCO",
            "cad_handle": "11",
            "entity_type": "Polyline",
            "geometry_confidence": "high",
            "file_level_id": "NPT_P1",
        },
    )

    items = build_semantic_elements_from_accore_payload(
        raw_elements=[raw],
        source_file=Path("C:/repo/ARQ-P1.dwg"),
        payload=None,
    )

    assert items[0].element_type == "unknown_architecture"
    assert items[0].semantic_type_confidence == "unknown"


def test_build_semantic_elements_does_not_classify_from_filename_tokens() -> None:
    raw = Element25D(
        id="arch_003",
        source_ref="C:/repo/Serena 18 -PLANTA PISOS 10-10-2022.dwg|MARCO|Polyline|12",
        discipline=Discipline.ARCH,
        category="Polyline:MARCO",
        footprint_coords_mm=[(0.0, 0.0), (2000.0, 0.0), (2000.0, 1000.0), (0.0, 1000.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0),
        metadata={
            "source_file": "C:/repo/Serena 18 -PLANTA PISOS 10-10-2022.dwg",
            "file": "Serena 18 -PLANTA PISOS 10-10-2022.dwg",
            "layer": "MARCO",
            "cad_handle": "12",
            "entity_type": "Polyline",
            "geometry_confidence": "high",
            "file_level_id": "NPT_P1",
        },
    )

    items = build_semantic_elements_from_accore_payload(
        raw_elements=[raw],
        source_file=Path("C:/repo/Serena 18 -PLANTA PISOS 10-10-2022.dwg"),
        payload=None,
    )

    assert items[0].element_type == "unknown_architecture"
    assert items[0].semantic_type_confidence == "unknown"
