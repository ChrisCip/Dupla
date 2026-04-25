"""Tests for the 2.5D coordination core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.coordination import (
    Discipline,
    Element25D,
    ElevationMode,
    ProjectLevelRegistry,
    ProjectLevelRegistryDocument,
    ZInterval,
    clash_pairs,
    element_from_inventory_meters,
    to_mm,
)
from core.coordination.models_25d import ProjectLevel
from core.coordination.nasas_paths import COORDINATION_ISSUE_METADATA_KEY, coordination_issue_key


def test_to_mm() -> None:
    assert to_mm(1.0, "m") == 1000.0
    assert to_mm(100.0, "cm") == 1000.0


def test_compute_envelope_center() -> None:
    z = ZInterval(
        level_id="L1",
        z_ref_raw_mm=2500.0,
        thickness_mm=200.0,
        reference_point="center",
    )
    assert z.compute_envelope_relative_mm() == (2400.0, 2600.0)


def test_get_absolute_interval_relative() -> None:
    reg = ProjectLevelRegistry.from_llm_rows(
        [{"id": "L1", "name": "N1", "offset_to_project_zero_mm": 3000.0}],
        provisional=False,
    )
    el = Element25D(
        id="e1",
        source_ref="t1",
        discipline=Discipline.STRUC,
        footprint_coords_mm=[(0, 0), (1000, 0), (1000, 500), (0, 500)],
        z_data=ZInterval(
            level_id="L1",
            mode=ElevationMode.RELATIVE_TO_LEVEL,
            z_ref_raw_mm=0.0,
            thickness_mm=400.0,
            reference_point="bottom",
            measurement_uncertainty_mm=0.0,
            clearance_required_mm=0.0,
        ),
    )
    z0, z1 = el.get_absolute_interval_mm(reg.offsets_map(), strict_levels=True)
    assert z0 == 3000.0
    assert z1 == 3400.0


def test_clash_pairs_overlap() -> None:
    reg = ProjectLevelRegistry.from_llm_rows(
        [{"id": "L1", "name": "N1", "offset_to_project_zero_mm": 0.0}],
        provisional=False,
    )
    foot = [(0, 0), (2000, 0), (2000, 2000), (0, 2000)]
    duct = Element25D(
        id="duct_1",
        source_ref="v1",
        discipline=Discipline.MEP_HVAC,
        category="duct",
        footprint_coords_mm=foot,
        z_data=ZInterval(
            level_id="L1",
            z_ref_raw_mm=2500.0,
            thickness_mm=400.0,
            reference_point="bottom",
        ),
    )
    beam = Element25D(
        id="beam_1",
        source_ref="v2",
        discipline=Discipline.STRUC,
        category="beam",
        footprint_coords_mm=foot,
        z_data=ZInterval(
            level_id="L1",
            z_ref_raw_mm=2600.0,
            thickness_mm=500.0,
            reference_point="bottom",
        ),
    )
    conflicts = clash_pairs([duct, beam], reg, strict_levels=True)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.overlap_depth_z_mm > 0
    assert conflict.plan_intersection_area_mm2 > 0
    assert conflict.confidence == "medium"


def test_coordination_issue_key_date_in_name(tmp_path: Path) -> None:
    path = tmp_path / "11.03.2026 LAGOS PLANOS ESTRUCTURALES.pdf"
    path.write_bytes(b"%PDF-1.4")
    assert coordination_issue_key(path, tmp_path) == "d:20260311"


def test_coordination_issue_key_compact_date(tmp_path: Path) -> None:
    path = tmp_path / "LAS NASAS 09 PLANOS ARQ. 20251121.pdf"
    path.write_bytes(b"%PDF-1.4")
    assert coordination_issue_key(path, tmp_path) == "d:20251121"


def test_clash_pairs_skips_different_issue_keys() -> None:
    reg = ProjectLevelRegistry.from_llm_rows(
        [{"id": "L1", "name": "N1", "offset_to_project_zero_mm": 0.0}],
        provisional=False,
    )
    foot = [(0, 0), (2000, 0), (2000, 2000), (0, 2000)]
    a = Element25D(
        id="a",
        source_ref="v1",
        discipline=Discipline.MEP_HVAC,
        footprint_coords_mm=foot,
        z_data=ZInterval(level_id="L1", z_ref_raw_mm=2500.0, thickness_mm=400.0),
        metadata={COORDINATION_ISSUE_METADATA_KEY: "d:20250101"},
    )
    b = Element25D(
        id="b",
        source_ref="v2",
        discipline=Discipline.STRUC,
        footprint_coords_mm=foot,
        z_data=ZInterval(level_id="L1", z_ref_raw_mm=2600.0, thickness_mm=500.0),
        metadata={COORDINATION_ISSUE_METADATA_KEY: "d:20250201"},
    )
    assert (
        clash_pairs(
            [a, b],
            reg,
            strict_levels=True,
            require_same_metadata_key=COORDINATION_ISSUE_METADATA_KEY,
        )
        == []
    )
    assert len(clash_pairs([a, b], reg, strict_levels=True)) == 1


def test_no_clash_same_discipline() -> None:
    reg = ProjectLevelRegistry.from_llm_rows(
        [{"id": "L1", "name": "N1", "offset_to_project_zero_mm": 0.0}],
        provisional=False,
    )
    foot = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    a = Element25D(
        id="a1",
        source_ref="s",
        discipline=Discipline.MEP_HVAC,
        footprint_coords_mm=foot,
        z_data=ZInterval(level_id="L1", z_ref_raw_mm=0.0, thickness_mm=500.0),
    )
    b = Element25D(
        id="a2",
        source_ref="s",
        discipline=Discipline.MEP_HVAC,
        footprint_coords_mm=foot,
        z_data=ZInterval(level_id="L1", z_ref_raw_mm=100.0, thickness_mm=500.0),
    )
    assert clash_pairs([a, b], reg) == []


def test_element_from_inventory_meters() -> None:
    el = element_from_inventory_meters(
        id="x",
        source_ref="y",
        discipline=Discipline.ARCH,
        category="wall",
        footprint_xy_m=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
        z_interval=ZInterval(level_id="L1", z_ref_raw_mm=0.0, thickness_mm=100.0),
    )
    assert el.footprint_coords_mm[0] == (0.0, 0.0)
    assert el.footprint_coords_mm[1] == (1000.0, 0.0)


def test_load_nasas_sample_registry_json() -> None:
    repo = Path(__file__).resolve().parent.parent
    path = repo / "aps_integration" / "NASAS 09" / "coordination" / "sample_project_levels.json"
    if not path.is_file():
        pytest.skip("sample NASAS coordination JSON not present")
    doc = ProjectLevelRegistryDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))
    reg = doc.to_registry()
    assert len(doc.levels) >= 12
    assert "NASAS_Z_m1450" in reg.root
    assert reg.offset_mm("NASAS_Z_m1450") == -1450.0
    assert reg.offset_mm("NASAS_Z_4000") == 4000.0
    assert "NPT_P1" in reg.root
    assert reg.offset_mm("NPT_P1") == 0.0
    assert "L00" in reg.root
    assert reg.offset_mm("L00") == 0.0
    assert len(doc.view_level_patterns) >= 3
    assert len(doc.source_exclude_patterns) >= 2


def test_registry_document_alias_requires_canonical() -> None:
    doc = ProjectLevelRegistryDocument(
        levels=[ProjectLevel(id="A", name="a", offset_to_project_zero_mm=0.0)],
        level_aliases={"B": "missing"},
    )
    with pytest.raises(ValueError, match="canonico inexistente"):
        doc.to_registry()
