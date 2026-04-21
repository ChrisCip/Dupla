"""Tests para sub-PDFs por disciplina (sin llamadas a OpenAI)."""

from __future__ import annotations

from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz", reason="PyMuPDF")


def test_write_split_pdfs_by_discipline_orders_and_groups(tmp_path: Path) -> None:
    from pipeline.pdf_discipline_split import PageDiscipline, write_split_pdfs_by_discipline

    doc = fitz.open()
    for _ in range(4):
        doc.new_page()
    pdf = tmp_path / "combo.pdf"
    doc.save(str(pdf))
    doc.close()

    labels = [
        PageDiscipline(0, "structural", "a"),
        PageDiscipline(1, "electrical", "b"),
        PageDiscipline(2, "structural", "c"),
        PageDiscipline(3, "general", "d"),
    ]
    out_dir = tmp_path / "split_out"
    written = write_split_pdfs_by_discipline(pdf, labels, out_dir)

    assert set(written.keys()) == {"structural", "electrical", "general"}
    sdoc = fitz.open(written["structural"])
    try:
        assert len(sdoc) == 2
    finally:
        sdoc.close()
