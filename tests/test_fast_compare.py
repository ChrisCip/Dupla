from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import scripts.run_nasas09_project_coordination as runner
from core.coordination.clash import ClashConflict, group_conflicts_into_incidents
from core.coordination.fast_compare import (
    PreMatchCandidate,
    SourceCandidate,
    build_pre_match_candidates,
    compute_readiness_payload,
    load_alignment_manifest,
    normalize_fast_compare_element,
    select_preferred_candidates,
)
from core.coordination.models_25d import Discipline, Element25D, ProjectLevel, ZInterval
from core.coordination.registry import ProjectLevelRegistryDocument
from scripts.run_nasas09_project_coordination import _build_fast_compare_primary_conflicts


def _registry():
    doc = ProjectLevelRegistryDocument(
        project_name="Test",
        levels=[
            ProjectLevel(id="NPT_P1", name="P1", offset_to_project_zero_mm=0.0),
            ProjectLevel(id="NPT_P2", name="P2", offset_to_project_zero_mm=3000.0),
            ProjectLevel(id="CIMENTACION", name="Cimientos", offset_to_project_zero_mm=-1500.0),
        ],
    )
    return doc.to_registry()


def test_compute_readiness_payload_requires_coherent_issue() -> None:
    candidates = [
        SourceCandidate(
            path=Path("a.dwg"),
            rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg",
            issue_key="d:20240601",
            discipline=Discipline.ARCH,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="pattern:nivel_1",
        ),
        SourceCandidate(
            path=Path("b.dwg"),
            rel_path="PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/B.dwg",
            issue_key="d:20240115",
            discipline=Discipline.STRUC,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="pattern:nivel_1",
        ),
    ]

    payload = compute_readiness_payload(
        candidates,
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert payload["comparable_issue_keys"] == []
    assert len(payload["cohorts"]) == 2
    assert payload["cohorts"][0]["is_comparable"] is False
    assert payload["decision_summary"]["auto_comparable_count"] == 0


def test_build_pre_match_candidates_scores_cross_cohort_npt_p1_pair() -> None:
    candidates = [
        SourceCandidate(
            path=Path("Serena 18 -PLANTA PISOS 10-10-2022.dwg"),
            rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/06. JUNIO 2024/Serena 18 -PLANTA PISOS 10-10-2022.dwg",
            issue_key="dir:planos recibidos/arquitectonicos/06. junio 2024",
            discipline=Discipline.ARCH,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="default_level",
            drawing_type="floor_plan",
        ),
        SourceCandidate(
            path=Path("EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg"),
            rel_path="PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/01. ENERO 2023/EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg",
            issue_key="dir:planos recibidos/tecnicos/estructural/01. enero 2023",
            discipline=Discipline.STRUC,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="default_level",
            drawing_type="formwork",
        ),
    ]

    pair_candidates = build_pre_match_candidates(
        candidates,
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert len(pair_candidates) == 1
    assert pair_candidates[0].decision == "auto_comparable"
    assert pair_candidates[0].documentary_cohort_relation == "cross_cohort"
    assert pair_candidates[0].score >= 0.75


def test_select_preferred_candidates_keeps_best_architecture_anchor() -> None:
    candidates = [
        SourceCandidate(
            path=Path("Serena 18 -PLANTA PISOS 10-10-2022.dwg"),
            rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/06. JUNIO 2024/Serena 18 -PLANTA PISOS 10-10-2022.dwg",
            issue_key="dir:planos recibidos/arquitectonicos/06. junio 2024",
            discipline=Discipline.ARCH,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="default_level",
            drawing_type="floor_plan",
        ),
        SourceCandidate(
            path=Path("2208-Serena18-ID-Base.dwg"),
            rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/06. JUNIO 2024/2208-Serena18-ID-Base.dwg",
            issue_key="dir:planos recibidos/arquitectonicos/06. junio 2024",
            discipline=Discipline.ARCH,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="default_level",
            drawing_type="base_plan",
        ),
        SourceCandidate(
            path=Path("EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg"),
            rel_path="PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/01. ENERO 2023/EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg",
            issue_key="dir:planos recibidos/tecnicos/estructural/01. enero 2023",
            discipline=Discipline.STRUC,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="default_level",
            drawing_type="formwork",
        ),
        SourceCandidate(
            path=Path("EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg"),
            rel_path="PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/01. ENERO 2023/EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg",
            issue_key="dir:planos recibidos/tecnicos/estructural/01. enero 2023",
            discipline=Discipline.STRUC,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="pattern:nivel_1",
            drawing_type="ground_slab",
        ),
    ]

    selected = select_preferred_candidates(
        candidates,
        pair_candidates=build_pre_match_candidates(candidates, required_disciplines=(Discipline.ARCH, Discipline.STRUC)),
    )

    selected_names = {Path(candidate.rel_path).name for candidate in selected}
    assert "Serena 18 -PLANTA PISOS 10-10-2022.dwg" in selected_names
    assert "2208-Serena18-ID-Base.dwg" not in selected_names
    assert len(selected) == 3


def test_normalize_fast_compare_element_clamps_large_z() -> None:
    element = Element25D(
        id="x",
        source_ref="a|layer|BlockReference|1",
        discipline=Discipline.ARCH,
        footprint_coords_mm=[(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=5500.0, thickness_mm=4200.0),
        metadata={"geometry_source": "dwg_accore_bbox", "geometry_role": "suppressed"},
    )

    normalized = normalize_fast_compare_element(
        element,
        file_level_id="NPT_P1",
        cohort_id="d:20240601",
        level_source="pattern:nivel_1",
    )

    assert normalized.metadata["file_level_id"] == "NPT_P1"
    assert normalized.metadata["cohort_id"] == "d:20240601"
    assert normalized.metadata["level_assignment_source"] == "clamped_2d_default"
    assert normalized.z_data.z_ref_raw_mm == 0.0
    assert normalized.z_data.thickness_mm == 300.0


def test_group_conflicts_into_incidents_merges_same_cell() -> None:
    conflict_a = ClashConflict(
        element_id_a="a1",
        element_id_b="b1",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=100.0,
        z_overlap_range_project_mm=(0.0, 100.0),
        plan_intersection_area_mm2=5000.0,
        plan_intersection_centroid_mm=(1500.0, 1500.0),
        plan_intersection_bounds_mm=(1000.0, 1000.0, 2000.0, 2000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        source_refs=("C:/a.dwg|A|Polyline|1", "C:/b.dwg|B|Polyline|2"),
        geometry_sources=("dwg_accore_polyline", "dwg_accore_polyline"),
        level_assignment_sources=("pattern:nivel_1", "pattern:nivel_1"),
    )
    conflict_b = conflict_a.model_copy(
        update={
            "element_id_a": "a2",
            "element_id_b": "b2",
            "plan_intersection_centroid_mm": (1800.0, 1800.0),
        }
    )

    incidents = group_conflicts_into_incidents([conflict_a, conflict_b], cell_size_mm=2000.0)

    assert len(incidents) == 1
    assert incidents[0].member_count == 2
    assert incidents[0].level_id == "NPT_P1"


def test_build_fast_compare_primary_conflicts_skips_suppressed_and_cross_level() -> None:
    registry = _registry()
    footprint = [(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)]
    arch = Element25D(
        id="arch_p1",
        source_ref="C:/arch.dwg|A|Polyline|1",
        discipline=Discipline.ARCH,
        footprint_coords_mm=footprint,
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=300.0),
        metadata={
            "cohort_id": "d:20240601",
            "file_level_id": "NPT_P1",
            "geometry_role": "primary",
            "geometry_source": "dwg_accore_polyline",
            "level_assignment_source": "pattern:nivel_1",
        },
    )
    struc_primary = Element25D(
        id="struc_p1",
        source_ref="C:/struc.dwg|S|Polyline|2",
        discipline=Discipline.STRUC,
        footprint_coords_mm=footprint,
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=400.0),
        metadata={
            "cohort_id": "d:20240601",
            "file_level_id": "NPT_P1",
            "geometry_role": "primary",
            "geometry_source": "dwg_accore_polyline",
            "level_assignment_source": "pattern:nivel_1",
        },
    )
    struc_suppressed = struc_primary.model_copy(
        update={
            "id": "struc_bbox",
            "metadata": {
                "cohort_id": "d:20240601",
                "file_level_id": "NPT_P1",
                "geometry_role": "suppressed",
                "geometry_source": "dwg_accore_bbox",
                "level_assignment_source": "clamped_2d_default",
            },
        }
    )
    arch_p2 = arch.model_copy(
        update={
            "id": "arch_p2",
            "z_data": ZInterval(level_id="NPT_P2", z_ref_raw_mm=0.0, thickness_mm=300.0),
            "metadata": {
                "cohort_id": "d:20240601",
                "file_level_id": "NPT_P2",
                "geometry_role": "primary",
                "geometry_source": "dwg_accore_polyline",
                "level_assignment_source": "pattern:nivel_2",
            },
        }
    )

    conflicts = _build_fast_compare_primary_conflicts(
        all_elements=[arch, struc_primary, struc_suppressed, arch_p2],
        registry=registry,
        strict_levels=True,
        required_disciplines=(Discipline.ARCH, Discipline.STRUC),
    )

    assert len(conflicts) == 1
    assert conflicts[0].level_ids == ("NPT_P1", "NPT_P1")


def test_run_fast_compare_skips_extraction_when_no_pairs_scheduled(tmp_path, monkeypatch) -> None:
    doc = ProjectLevelRegistryDocument(
        project_name="SERENA 18",
        levels=[ProjectLevel(id="NPT_P1", name="P1", offset_to_project_zero_mm=0.0)],
    )
    registry = doc.to_registry()
    candidates = [
        SourceCandidate(
            path=tmp_path / "PLANOS RECIBIDOS" / "ARQUITECTONICOS" / "A.dwg",
            rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg",
            issue_key="manual:serena18",
            cohort_id="analysis_03_manual",
            discipline=Discipline.ARCH,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="pattern:test",
            drawing_type="floor_plan",
        ),
        SourceCandidate(
            path=tmp_path / "PLANOS RECIBIDOS" / "TECNICOS" / "ESTRUCTURAL" / "B.dwg",
            rel_path="PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/B.dwg",
            issue_key="manual:serena18",
            cohort_id="analysis_03_manual",
            discipline=Discipline.STRUC,
            suffix=".dwg",
            level_id="NPT_P1",
            level_source="pattern:test",
            drawing_type="formwork",
        ),
    ]

    monkeypatch.setattr(runner, "build_source_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(
        runner,
        "_profile_fast_compare_candidates",
        lambda **kwargs: (
            {
                candidates[0].rel_path: {
                    "profile": {
                        "raw_entity_count": 100,
                        "raw_primary_candidate_count": 25,
                        "raw_annotation_count": 10,
                        "raw_bbox_only_count": 5,
                        "bounds_mm": (0.0, 0.0, 10_000.0, 10_000.0, 0.0, 0.0),
                        "centroid_mm": (5_000.0, 5_000.0, 0.0),
                        "dominant_entity_types": ["Polyline"],
                    }
                },
                candidates[1].rel_path: {
                    "profile": {
                        "raw_entity_count": 100,
                        "raw_primary_candidate_count": 25,
                        "raw_annotation_count": 10,
                        "raw_bbox_only_count": 5,
                        "bounds_mm": (900_000.0, 0.0, 910_000.0, 10_000.0, 0.0, 0.0),
                        "centroid_mm": (905_000.0, 5_000.0, 0.0),
                        "dominant_entity_types": ["Polyline"],
                    }
                },
            },
            {"profiled_file_count": 2, "accore_cache_hits": 0, "accore_cache_misses": 2},
        ),
    )

    def _fail_extract(**kwargs):
        raise AssertionError("scheduled extraction should not run when pair_schedule is empty")

    monkeypatch.setattr(runner, "_extract_fast_compare_scheduled_elements", _fail_extract)

    args = Namespace(
        include_disciplines=None,
        skip_dwg=False,
        skip_pdf=False,
        cohort_manifest=None,
        alignment_manifest=None,
        output=tmp_path / "summary.json",
        stage="full",
        coordinate_band_cell_mm=500_000.0,
        accore_timeout_seconds=30,
        max_workers=1,
        shared_site_origin=True,
        strict_levels=True,
        primary_min_plan_area_mm2=10_000.0,
    )

    result = runner._run_fast_compare(
        args=args,
        doc=doc,
        registry=registry,
        default_level_id="NPT_P1",
        media=[],
        scan_skips={},
        nasas_root=tmp_path,
        cache_root=tmp_path / "cache",
    )

    summary = json.loads(args.output.read_text(encoding="utf-8"))
    assert result == 0
    assert summary["status"] == "no_scheduled_pairs"
    assert summary["element_count"] == 0
    assert summary["scheduled_pair_count"] == 0
    assert summary["scheduled_file_count"] == 0


def test_load_alignment_manifest_normalizes_paths(tmp_path) -> None:
    root = tmp_path / "SERENA 18"
    root.mkdir()
    manifest = tmp_path / "alignment.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_file": "PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg",
                        "translate_mm": [-1000.0, 2500.0],
                        "note": "manual",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    overrides = load_alignment_manifest(manifest, root=root)

    assert "planos recibidos/arquitectonicos/a.dwg" in overrides
    assert overrides["planos recibidos/arquitectonicos/a.dwg"].translate_mm == (-1000.0, 2500.0)


def test_load_alignment_manifest_reads_level_override(tmp_path) -> None:
    root = tmp_path / "SERENA 18"
    root.mkdir()
    manifest = tmp_path / "alignment.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_file": "PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg",
                        "translate_mm": [100.0, 200.0],
                        "level_id": "TECHO",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    overrides = load_alignment_manifest(manifest, root=root)

    override = overrides["planos recibidos/arquitectonicos/a.dwg"]
    assert override.level_id == "TECHO"
    assert override.level_source == "manual_manifest:TECHO"


def test_apply_alignment_override_to_candidate_updates_level() -> None:
    candidate = SourceCandidate(
        path=Path("a.dwg"),
        rel_path="PLANOS RECIBIDOS/ARQUITECTONICOS/A.dwg",
        issue_key="d:20240601",
        discipline=Discipline.ARCH,
        suffix=".dwg",
        level_id="NPT_P1",
        level_source="pattern:nivel_1",
        cohort_id="manual",
    )
    overrides = {
        "planos recibidos/arquitectonicos/a.dwg": type(
            "Override",
            (),
            {
                "translate_mm": (100.0, 200.0),
                "level_id": "TECHO",
                "level_source": "manual_manifest:TECHO",
            },
        )()
    }

    updated = runner._apply_alignment_override_to_candidate(
        candidate=candidate,
        alignment_overrides=overrides,
    )

    assert updated.level_id == "TECHO"
    assert updated.level_source == "manual_manifest:TECHO"
    assert updated.rel_path == candidate.rel_path


def test_apply_translation_to_profile_shifts_dominant_cluster() -> None:
    profile = {
        "bounds_mm": (100.0, 200.0, 300.0, 400.0, 0.0, 0.0),
        "centroid_mm": (200.0, 300.0, 0.0),
        "dominant_cluster_bounds_mm": (110.0, 210.0, 290.0, 390.0, 0.0, 0.0),
        "dominant_cluster_centroid_mm": (200.0, 300.0, 0.0),
    }

    shifted = runner._apply_translation_to_profile(profile, translation_mm=(1000.0, -500.0))

    assert shifted["centroid_mm"][:2] == (1200.0, -200.0)
    assert shifted["dominant_cluster_centroid_mm"][:2] == (1200.0, -200.0)
    assert shifted["dominant_cluster_bounds_mm"][:4] == (1110.0, -290.0, 1290.0, -110.0)
