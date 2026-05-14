from __future__ import annotations

from pathlib import Path

import fitz

from coordination.extraction.from_pdf_vector import extract_elements_from_pdf
from coordination.core.models_25d import Discipline, ProjectLevel
from coordination.core.registry import ProjectLevelRegistryDocument, ViewLevelPattern


def _registry_doc() -> ProjectLevelRegistryDocument:
    return ProjectLevelRegistryDocument(
        levels=[ProjectLevel(id="P1", name="Primer", offset_to_project_zero_mm=0.0)],
        view_level_patterns=[ViewLevelPattern(pattern="primer nivel", level_id="P1")],
    )


def test_extract_elements_from_pdf_clusters_multiple_regions(tmp_path: Path) -> None:
    pdf_path = tmp_path / "plano.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_text((60, 24), "Primer nivel")
    page.draw_rect(fitz.Rect(0, 0, 600, 400), color=(0, 0, 0), width=1)
    page.draw_rect(fitz.Rect(50, 60, 180, 180), color=(0, 0, 0), width=2)
    page.draw_rect(fitz.Rect(320, 80, 520, 240), color=(0, 0, 0), width=2)
    doc.save(pdf_path)
    doc.close()

    elements = extract_elements_from_pdf(
        pdf_path,
        Discipline.ARCH,
        level_id="P1",
        level_doc=_registry_doc(),
    )
    assert len(elements) == 2
    assert all(element.category == "pdf_vector_cluster" for element in elements)
    assert all(element.metadata["geometry_quality"] == "medium" for element in elements)
    assert all(element.z_data.level_id == "P1" for element in elements)


def test_extract_elements_from_pdf_without_fallback_returns_empty(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page(width=300, height=200)
    doc.save(pdf_path)
    doc.close()

    assert extract_elements_from_pdf(pdf_path, Discipline.ARCH, level_id="P1", allow_page_fallback=False) == []
