from __future__ import annotations

from core.coordination.level_inference import infer_level_from_pdf_page, infer_level_from_view_name
from core.coordination.models_25d import ProjectLevel
from core.coordination.registry import ProjectLevelRegistryDocument, ViewLevelPattern


def _doc() -> ProjectLevelRegistryDocument:
    return ProjectLevelRegistryDocument(
        levels=[
            ProjectLevel(id="P1", name="Primer", offset_to_project_zero_mm=0.0),
            ProjectLevel(id="P2", name="Segundo", offset_to_project_zero_mm=3000.0),
            ProjectLevel(id="ROOF", name="Techo", offset_to_project_zero_mm=6000.0),
            ProjectLevel(id="FOUND", name="Cimientos", offset_to_project_zero_mm=-1450.0),
        ],
        view_level_patterns=[
            ViewLevelPattern(pattern="primer nivel", level_id="P1"),
            ViewLevelPattern(pattern="segundo nivel", level_id="P2"),
            ViewLevelPattern(pattern="techo", level_id="ROOF"),
            ViewLevelPattern(pattern="cimientos", level_id="FOUND"),
        ],
    )


def test_infer_level_from_pdf_page_text() -> None:
    resolution, z_base = infer_level_from_pdf_page(
        page_text="PLANTA ARQUITECTONICA PRIMER NIVEL",
        page_label="",
        file_name="a.pdf",
        doc=_doc(),
        default_level_id="P1",
        page_index=2,
        page_z_step_mm=3200.0,
    )
    assert resolution.level_id == "P1"
    assert resolution.source.startswith("pattern:")
    assert z_base == 0.0


def test_infer_level_from_pdf_page_falls_back_to_page_index() -> None:
    resolution, z_base = infer_level_from_pdf_page(
        page_text="sin nivel explicito",
        page_label="",
        file_name="a.pdf",
        doc=_doc(),
        default_level_id="P1",
        page_index=3,
        page_z_step_mm=3200.0,
    )
    assert resolution.level_id == "P1"
    assert resolution.source == "page_index_fallback"
    assert z_base == 9600.0


def test_infer_level_from_view_name_for_foundations() -> None:
    resolution = infer_level_from_view_name(
        "PLANTA DE CIMIENTOS",
        doc=_doc(),
        default_level_id="P1",
    )
    assert resolution.level_id == "FOUND"
