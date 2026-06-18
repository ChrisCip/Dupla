from pathlib import Path

from coordination.core.clash import clash_pairs
from coordination.core.models_25d import Discipline, Element25D, ProjectLevel, ZInterval
from coordination.core.registry import ProjectLevelRegistry
from coordination.core.tolerances import ClashTolerances
from coordination.extraction.from_dwg_accore import extract_elements_from_accore_payload


def _registry() -> ProjectLevelRegistry:
    return ProjectLevelRegistry(
        {
            "NPT_P1": ProjectLevel(
                id="NPT_P1",
                name="NPT_P1",
                offset_to_project_zero_mm=0.0,
            )
        }
    )


def _element(element_id: str, discipline: Discipline, footprint: list[tuple[float, float]]) -> Element25D:
    return Element25D(
        id=element_id,
        source_ref=f"file.dwg|MUROS|Polyline|{element_id}",
        discipline=discipline,
        category="Polyline:MUROS",
        layer_raw="MUROS",
        footprint_coords_mm=footprint,
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0, reference_point="bottom"),
        metadata={
            "canonical_role": "WALL",
            "layer_rule_confidence": "high",
            "raw_layer": "MUROS",
        },
    )


def test_grid_size_collapses_micro_offset() -> None:
    left = _element("a", Discipline.ARCH, [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)])
    right = _element("b", Discipline.STRUC, [(1000.3, 0.0), (2000.3, 0.0), (2000.3, 1000.0), (1000.3, 1000.0)])
    conflicts = clash_pairs(
        [left, right],
        _registry(),
        tolerances=ClashTolerances(
            grid_size_mm=1.0,
            linear_buffer_mm=25.0,
            tesselation_chord_error_mm=5.0,
            min_plan_area_mm2=1.0,
            z_overlap_tolerance_mm=25.0,
            clearance_mm=0.0,
        ),
        min_plan_area_mm2=1.0,
    )
    assert conflicts, "expected snapped overlap with grid_size=1.0"


def test_min_plan_area_filters_micro_overlap() -> None:
    left = _element("a", Discipline.ARCH, [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)])
    right = _element("b", Discipline.STRUC, [(990.0, 0.0), (1990.0, 0.0), (1990.0, 1000.0), (990.0, 1000.0)])
    conflicts = clash_pairs(
        [left, right],
        _registry(),
        tolerances=ClashTolerances(
            min_plan_area_mm2=50_000.0,
            linear_buffer_mm=25.0,
            tesselation_chord_error_mm=5.0,
        ),
        min_plan_area_mm2=50_000.0,
    )
    assert not conflicts


def test_accore_line_buffer_uses_configured_tolerance() -> None:
    payload = {
        "UnitsToMmFactor": 1.0,
        "Entities": [
            {
                "Handle": "11",
                "Layer": "MUROS",
                "Type": "Line",
                "StartPoint": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                "EndPoint": {"X": 1000.0, "Y": 0.0, "Z": 0.0},
                "Bounds": {"Min": {"X": 0.0, "Y": 0.0, "Z": 0.0}, "Max": {"X": 1000.0, "Y": 0.0, "Z": 0.0}},
            }
        ],
    }
    thin = extract_elements_from_accore_payload(
        payload,
        path=Path("line.dwg"),
        discipline=Discipline.ARCH,
        level_id="NPT_P1",
        translation_mm=(0.0, 0.0),
        min_area_mm2=1.0,
        max_entities=20,
        z_thickness_mm=250.0,
        z_ref_mm=None,
        tolerances=ClashTolerances(linear_buffer_mm=10.0, min_plan_area_mm2=1.0),
    )
    thick = extract_elements_from_accore_payload(
        payload,
        path=Path("line.dwg"),
        discipline=Discipline.ARCH,
        level_id="NPT_P1",
        translation_mm=(0.0, 0.0),
        min_area_mm2=1.0,
        max_entities=20,
        z_thickness_mm=250.0,
        z_ref_mm=None,
        tolerances=ClashTolerances(linear_buffer_mm=50.0, min_plan_area_mm2=1.0),
    )
    assert thin and thick
    assert float(thick[0].metadata["area_mm2"]) > float(thin[0].metadata["area_mm2"])
