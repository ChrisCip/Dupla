from __future__ import annotations

from pathlib import Path

from core.coordination.registry import SourceExcludePattern
from core.coordination.source_selection import collect_coordination_media, should_include_source


def test_should_exclude_pdf_images(tmp_path: Path) -> None:
    root = tmp_path / "NASAS 09"
    path = root / "PLANOS RECIBIDOS" / "ARQUITECTONICOS" / "REV. 1" / "PDF Images" / "planoa1b2c3d4.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"img")
    keep, reason = should_include_source(path, nasas_root=root)
    assert keep is False
    assert reason in {"derived_pdf_image", "excluded_by_pattern:(^|/)pdf images(/|$)"}


def test_collect_coordination_media_skips_review_overlays(tmp_path: Path) -> None:
    root = tmp_path / "NASAS 09"
    keep_pdf = root / "PLANOS RECIBIDOS" / "ARQUITECTONICOS" / "REV. 1" / "plano.pdf"
    skip_pdf = root / "PLANOS RECIBIDOS" / "ARQUITECTONICOS" / "REV. 1" / "SOLAPADO plano.pdf"
    keep_pdf.parent.mkdir(parents=True, exist_ok=True)
    keep_pdf.write_bytes(b"%PDF")
    skip_pdf.write_bytes(b"%PDF")
    selected, skipped = collect_coordination_media(
        root,
        extra_patterns=[SourceExcludePattern(pattern="solapado", reason="overlay")],
    )
    assert keep_pdf in selected
    assert skip_pdf not in selected
    assert skipped["overlay"] == 1


def test_collect_coordination_media_includes_dxf(tmp_path: Path) -> None:
    root = tmp_path / "NASAS 09"
    dxf = root / "PLANOS RECIBIDOS" / "TECNICOS" / "ESTRUCTURAL" / "REV. 1" / "modelo.dxf"
    dxf.parent.mkdir(parents=True, exist_ok=True)
    dxf.write_text("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n", encoding="utf-8")
    selected, skipped = collect_coordination_media(root)
    assert dxf in selected
    assert skipped == {}


def test_collect_coordination_media_prefers_dxf_over_dwg_same_stem(tmp_path: Path) -> None:
    root = tmp_path / "NASAS 09"
    parent = root / "PLANOS RECIBIDOS" / "TECNICOS" / "ESTRUCTURAL" / "REV. 1"
    parent.mkdir(parents=True, exist_ok=True)
    dwg = parent / "modelo.dwg"
    dxf = parent / "modelo.dxf"
    dwg.write_bytes(b"AC1027")
    dxf.write_text("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n", encoding="utf-8")
    selected, skipped = collect_coordination_media(root)
    assert dxf in selected
    assert dwg not in selected
    assert skipped["duplicate_dwg_replaced_by_dxf"] == 1
