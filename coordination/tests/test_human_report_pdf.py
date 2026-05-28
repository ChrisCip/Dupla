"""Tests for human clash PDF report generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from coordination.core.clash import ClashConflict, ClashIncident
from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.human_report_pdf import (
    build_file_alias_map,
    prepare_clash_sheet_rows,
    render_coordination_human_report_pdf,
)
from coordination.reporting.tile_renderer import render_dwg_comparison_panels


def _element(
    element_id: str,
    file_name: str,
    discipline: Discipline,
    footprint: list[tuple[float, float]],
) -> Element25D:
    return Element25D(
        id=element_id,
        source_ref=f"{file_name}|MUROS|LINE|{element_id}",
        discipline=discipline,
        category=f"LINE:{discipline.value}",
        footprint_coords_mm=footprint,
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=3000.0, measurement_uncertainty_mm=0.0),
        metadata={"level_id": "NPT_P1", "file_level_id": f"{file_name}|NPT_P1"},
    )


def _conflict() -> ClashConflict:
    return ClashConflict(
        element_id_a="a1",
        element_id_b="b1",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=120.0,
        z_overlap_range_project_mm=(0.0, 120.0),
        plan_intersection_area_mm2=400000.0,
        plan_intersection_centroid_mm=(750.0, 750.0),
        plan_intersection_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        raw_layers=("MUROS", "EST. MUROS"),
        source_refs=("arq.dwg|MUROS|LINE|a1", "est.dwg|EST. MUROS|LINE|b1"),
    )


def _incident_dict() -> dict:
    incident = ClashIncident(
        incident_id="incident_0001",
        file_pair=("arq.dwg", "est.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=_conflict(),
        plan_centroid_mm=(750.0, 750.0),
        plan_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
    )
    return incident.model_dump()


def _report_context() -> dict:
    return {
        "all_incidents": [
            {
                "incident_id": "incident_0001",
                "severity": "high",
                "priority": "P1",
                "level_id": "NPT_P1",
                "disciplines": ("ARQUITECTURA", "ESTRUCTURA"),
                "layer_pair": "MUROS / EST. MUROS",
                "human_description": "posible traslape de muro con muro estructural",
                "recommended_action": "Verificar reserva estructural con arquitectura.",
                "file_names": ("arq.dwg", "est.dwg"),
            }
        ]
    }


def test_build_file_alias_map_disambiguates_duplicate_names() -> None:
    aliases = build_file_alias_map(
        [
            "/proj/ARQ/plano.dwg",
            "/proj/EST/plano.dwg",
            "/proj/ARQ/unico.dwg",
        ]
    )
    assert aliases["/proj/ARQ/unico.dwg"] == "unico.dwg"
    assert "ARQ/plano.dwg" in aliases["/proj/ARQ/plano.dwg"]
    assert "EST/plano.dwg" in aliases["/proj/EST/plano.dwg"]


def test_build_file_alias_map_tortuga_stable_codes() -> None:
    arq_rev1 = (
        "C:/repo/PLANOS RECIBIDOS/ARQUITECTONICOS/REV. 1/"
        "PLANOS ARQ TORTUGA C-40 NOV 2025.dwg"
    )
    arq_rev2 = (
        "C:/repo/PLANOS RECIBIDOS/ARQUITECTONICOS/REV. 2/"
        "PLANOS ARQ TORTUGA C-40  20260129.dwg"
    )
    est_rev1 = (
        "C:/repo/PLANOS RECIBIDOS/TECNICOS/ESTRUCTURAL/REV. 1/"
        "PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg"
    )
    aliases = build_file_alias_map([arq_rev1, arq_rev2, est_rev1])
    assert aliases[arq_rev1] == "ARQ_REV1"
    assert aliases[arq_rev2] == "ARQ_REV2"
    assert aliases[est_rev1] == "EST_REV1"


def test_render_dwg_comparison_panels_split_by_file() -> None:
    incident = ClashIncident.model_validate(_incident_dict())
    elements = [
        _element("a1", "arq.dwg", Discipline.ARCH, [(400, 400), (1100, 400), (1100, 1100), (400, 1100)]),
        _element("b1", "est.dwg", Discipline.STRUC, [(450, 450), (1050, 450), (1050, 1050), (450, 1050)]),
    ]
    left, right, has_visual = render_dwg_comparison_panels(
        incident,
        elements,
        marker_code="S-A1",
    )
    assert has_visual
    assert left.elements_in_tile == ["a1"]
    assert right.elements_in_tile == ["b1"]
    assert "S-A1" in left.svg_content
    assert "S-A1" in right.svg_content
    assert "#DC2626" in left.svg_content


def test_render_coordination_human_report_pdf_writes_file(tmp_path: Path) -> None:
    reportlab = pytest.importorskip("reportlab")
    pytest.importorskip("svglib")
    assert reportlab is not None

    primary_payload = {
        "incidents": [_incident_dict()],
        "incident_count": 1,
    }
    elements = [
        _element("a1", "arq.dwg", Discipline.ARCH, [(400, 400), (1100, 400), (1100, 1100), (400, 1100)]),
        _element("b1", "est.dwg", Discipline.STRUC, [(450, 450), (1050, 450), (1050, 1050), (450, 1050)]),
    ]
    output = tmp_path / "coordination_report_human.pdf"
    render_coordination_human_report_pdf(
        output_path=output,
        project_name="SERENA 18",
        run_label="test_run",
        generated_at="2026-05-24T12:00:00+00:00",
        report_context=_report_context(),
        primary_payload=primary_payload,
        all_elements=elements,
    )
    assert output.is_file()
    assert output.stat().st_size > 2000
    content = output.read_bytes()
    assert content.startswith(b"%PDF")


def test_severity_bucket_and_layout_fields() -> None:
    rows, _ = prepare_clash_sheet_rows(
        project_name="SERENA 18",
        report_context=_report_context(),
        primary_payload={"incidents": [_incident_dict()]},
        all_elements=[],
    )
    assert rows[0].severity_bucket == "high"
    assert rows[0].layer_a == "MUROS"
    assert rows[0].discipline_pair
    assert rows[0].clash_type == "HARD"


def test_prepare_clash_sheet_rows_codes_and_fields() -> None:
    rows, aliases = prepare_clash_sheet_rows(
        project_name="SERENA 18",
        report_context=_report_context(),
        primary_payload={"incidents": [_incident_dict()]},
        all_elements=[],
    )
    assert len(rows) == 1
    assert rows[0].code.startswith("S-")
    assert rows[0].layer_a == "MUROS"
    assert rows[0].layer_b == "EST. MUROS"
    assert rows[0].center_text != "no disponible"
    assert rows[0].zoom_command.startswith("Z W")
    assert "?" not in rows[0].plano_a
    assert rows[0].tipo == "Solapamiento constructivo"
    assert "Verificar" in rows[0].observacion or "posible traslape" in rows[0].observacion.lower()
    assert rows[0].estado_correccion == "Detectado"
    assert rows[0].estado_carga == "Pendiente de carga"
    assert rows[0].decision_revisor == "Pendiente"
    assert rows[0].incident_id == "incident_0001"
    assert rows[0].dwg_corregir
    assert rows[0].par_dwg_original.startswith("DWG A:")
    assert rows[0].comparacion_dwg == "arq.dwg ↔ est.dwg"
    assert "Discipline." not in rows[0].dwg_corregir
    assert "<br" not in rows[0].ubicacion_comando
    assert "source_ref" not in rows[0].observacion.lower()
    assert all("tras revisar" not in w for w in (rows[0].warnings or []))
