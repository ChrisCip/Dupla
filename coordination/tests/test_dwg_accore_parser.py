from pathlib import Path

from coordination.extraction.from_dwg_accore import extract_elements_from_accore_payload, profile_accore_payload
from coordination.core.models_25d import Discipline


def test_accore_payload_generates_polyline_and_bbox_elements() -> None:
    payload = {
        "UnitsToMmFactor": 1000.0,
        "Entities": [
            {
                "Handle": "10",
                    "Layer": "MUROS",
                "Type": "Polyline",
                "Closed": True,
                "Vertices": [
                    {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    {"X": 3.0, "Y": 0.0, "Z": 0.0},
                    {"X": 3.0, "Y": 4.0, "Z": 0.0},
                    {"X": 0.0, "Y": 4.0, "Z": 0.0},
                ],
                "Bounds": {
                    "Min": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "Max": {"X": 3.0, "Y": 4.0, "Z": 0.0},
                },
            },
            {
                "Handle": "20",
                "Layer": "E-BLOCKS",
                "Type": "BlockReference",
                "Bounds": {
                    "Min": {"X": 10.0, "Y": 10.0, "Z": 0.0},
                    "Max": {"X": 12.0, "Y": 11.0, "Z": 0.5},
                },
            },
            {
                "Handle": "30",
                "Layer": "A-ANNO-TEXT",
                "Type": "DBText",
                "Bounds": {
                    "Min": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                    "Max": {"X": 100.0, "Y": 20.0, "Z": 0.0},
                },
            },
        ],
    }

    elements = extract_elements_from_accore_payload(
        payload,
        path=Path("sample.dwg"),
        discipline=Discipline.STRUC,
        level_id="NPT_P1",
        translation_mm=(10.0, -20.0),
        min_area_mm2=1000.0,
        max_entities=10,
        z_thickness_mm=250.0,
        z_ref_mm=None,
    )

    assert len(elements) == 2
    assert elements[0].metadata["geometry_source"] == "dwg_accore_polyline"
    assert elements[0].metadata["geometry_quality"] == "high"
    assert elements[0].metadata["geometry_role"] == "primary"
    assert elements[0].metadata["source_file"] == "sample.dwg"
    assert elements[0].metadata["cad_handle"] == "10"
    assert elements[0].metadata["entity_type"] == "Polyline"
    assert elements[0].metadata["block_name"] is None
    assert elements[0].metadata["geometry_confidence"] == "high"
    assert elements[0].metadata["bbox_mm"] == (10.0, -20.0, 3010.0, 3980.0)
    assert elements[0].metadata["centroid_mm"] == (1510.0, 1980.0)
    assert elements[0].footprint_coords_mm[0] == (10.0, -20.0)
    assert elements[1].metadata["geometry_source"] == "dwg_accore_bbox"
    assert elements[1].metadata["geometry_quality"] == "medium"
    assert elements[1].metadata["geometry_role"] == "suppressed"
    assert elements[1].metadata["suppression_reason"] == "container_bbox"
    assert elements[1].metadata["source_file"] == "sample.dwg"
    assert elements[1].metadata["cad_handle"] == "20"
    assert elements[1].metadata["entity_type"] == "BlockReference"
    assert elements[1].metadata["geometry_confidence"] == "medium"
    assert elements[1].z_data.thickness_mm == 500.0


def test_profile_accore_payload_prefers_dominant_primary_cluster_over_global_extents() -> None:
    payload = {
        "UnitsToMmFactor": 1.0,
        "Entities": [
            {
                "Type": "Polyline",
                "Layer": "A-WALL",
                "Bounds": {"Min": {"X": 500000.0, "Y": 2000000.0, "Z": 0.0}, "Max": {"X": 510000.0, "Y": 2010000.0, "Z": 0.0}},
            },
            {
                "Type": "Polyline",
                "Layer": "A-WALL",
                "Bounds": {"Min": {"X": 520000.0, "Y": 2020000.0, "Z": 0.0}, "Max": {"X": 530000.0, "Y": 2030000.0, "Z": 0.0}},
            },
            {
                "Type": "Line",
                "Layer": "A-WALL",
                "Bounds": {"Min": {"X": 535000.0, "Y": 2040000.0, "Z": 0.0}, "Max": {"X": 536000.0, "Y": 2041000.0, "Z": 0.0}},
            },
            {
                "Type": "Polyline",
                "Layer": "A-XREF",
                "Bounds": {"Min": {"X": -500000000.0, "Y": -500000000.0, "Z": 0.0}, "Max": {"X": 500000000.0, "Y": 500000000.0, "Z": 0.0}},
            },
        ],
    }

    profile = profile_accore_payload(payload)

    assert profile["dominant_cluster_key"] == (1, 4)
    assert profile["dominant_cluster_entity_count"] == 3
    assert profile["dominant_cluster_centroid_mm"][0] > 500000.0
    assert profile["dominant_cluster_centroid_mm"][1] > 2000000.0
