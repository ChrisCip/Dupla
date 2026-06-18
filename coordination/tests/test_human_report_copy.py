"""Tests for architectural human report copy."""

from __future__ import annotations

from coordination.reporting.human_report_copy import (
    CORRECTION_LIFECYCLE,
    DWG_TO_CORRECT_PENDING,
    build_architectural_observation,
    corrected_delivery_section_lines,
    filter_human_warnings,
    format_clash_type,
    format_correction_status,
    format_dwg_to_correct,
    format_upload_status,
    format_ubicacion_zw,
    format_ubicacion_zw_lines,
    humanize_discipline_label,
)


def test_format_correction_status_defaults_to_detected() -> None:
    assert format_correction_status("") == "Detectado"
    assert format_correction_status("correction_required") == "Corrección requerida"
    assert format_correction_status("false_positive") == "Falso positivo"
    assert format_correction_status("reviewed") == "Revisado"


def test_format_upload_status_defaults_to_pending() -> None:
    assert format_upload_status("") == "Pendiente de carga"
    assert format_upload_status("uploaded") == "Cargado en Dupla"


def test_corrected_delivery_mentions_no_overwrite() -> None:
    text = " ".join(corrected_delivery_section_lines()).lower()
    assert "dwg a vs dwg b" in text or "dwg a vs dwg b" in text.replace("vs", "vs")
    assert "no sobrescriba" in text
    assert "revisión" in text
    assert CORRECTION_LIFECYCLE.startswith("Detectado")


def test_build_architectural_observation_uses_layers() -> None:
    text = build_architectural_observation(
        layer_a="PLAFON",
        layer_b="SOLAR",
        nivel="NPT_P1",
        disciplina_a="Arquitectura",
        disciplina_b="Estructura",
        plano_a="arq.dwg",
        plano_b="est.dwg",
    )
    assert "PLAFON" in text
    assert "SOLAR" in text
    assert "NPT_P1" in text
    assert "source_ref" not in text.lower()


def test_filter_human_warnings_removes_debug_messages() -> None:
    warnings = [
        "S-A1: capas no disponibles tras revisar todas las fuentes",
        "No DWG visual preview available for this run.",
    ]
    filtered = filter_human_warnings(warnings)
    assert len(filtered) == 1
    assert "visual preview" in filtered[0]


def test_format_clash_type_architectural() -> None:
    assert format_clash_type("HARD") == "Solapamiento constructivo"
    assert format_clash_type("") == "Interferencia geométrica"


def test_humanize_discipline_label_strips_enum_repr() -> None:
    assert humanize_discipline_label("Discipline.ARCH") == "Arquitectura"
    assert humanize_discipline_label("Discipline.Struc") == "Estructura"
    assert humanize_discipline_label("ARQUITECTURA") == "Arquitectura"


def test_format_dwg_to_correct_pending_without_enum() -> None:
    text = format_dwg_to_correct(
        "",
        plano_a="ARQ_REV1",
        plano_b="EST_REV1",
        disciplina_a="Discipline.Arch",
        disciplina_b="Discipline.Struc",
    )
    assert text == DWG_TO_CORRECT_PENDING
    assert "Discipline" not in text


def test_format_ubicacion_zw_uses_newlines_not_html() -> None:
    text = format_ubicacion_zw(center_text="NPT_P1; (1, 2) mm", zoom_command="Z W 0,0 100,100")
    assert "<br" not in text
    lines = format_ubicacion_zw_lines(center_text="NPT_P1; (1, 2) mm", zoom_command="Z W 0,0 100,100")
    assert len(lines) == 2
    assert lines[1].startswith("Z W")
