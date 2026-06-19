"""Tests for architectural checklist PDF (PR 4)."""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from app.models.project_clash_item import ProjectClashItem
from app.services.clash_reports.incident_pages_pdf import (
    SVG_EMBED_FAILED_SUFFIX,
    VISUAL_UNAVAILABLE_MSG,
    _pdf_eligible,
    _sort_checklist_items,
    build_incident_checklist_pdf,
)


def _pdf_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join((page.extract_text() or "") for page in PdfReader(BytesIO(pdf_bytes)).pages)


def _item(
    *,
    clash_code: str = "incident_0001",
    title_semantic: str | None = None,
    table_comment: str | None = None,
    short_label: str | None = None,
    recommended_action: str | None = None,
    severity: str = "critical",
    has_real_visual: bool = False,
    composed_rel: str | None = None,
    zoom_rel: str | None = None,
    candidate_only: bool = False,
    raw_extra: dict | None = None,
) -> ProjectClashItem:
    contract: dict = {
        "has_real_visual": has_real_visual,
        "composed_full_page_tile_path": composed_rel,
        "visual_warnings": [],
    }
    raw: dict = {
        "incident_id": clash_code,
        "representative_conflict": {
            "plan_intersection_area_mm2": 50_000.0,
            "overlap_depth_z_mm": 100.0,
            "source_refs": [
                "A.dwg|ARQ_MURO|Polyline|HNDL_A",
                "B.dwg|EST_VIGA|Line|HNDL_B",
            ],
        },
        "_workflow_contract": contract,
    }
    if candidate_only:
        raw["candidate_only"] = True
    if raw_extra:
        raw.update(raw_extra)
    return ProjectClashItem(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        clash_code=clash_code,
        priority="P2",
        severity=severity,
        report_confidence="high",
        status="detected",
        dwg_a="ARQ-01.dwg",
        dwg_b="HID-SAN-01.dwg",
        level_id="P1",
        discipline_a="ARQUITECTURA",
        discipline_b="PLOMERIA",
        layer_a="ARQ_MURO",
        layer_b="HID_TUB",
        title_semantic=title_semantic,
        table_comment=table_comment,
        short_label=short_label,
        base_plan_number="ARQ-01",
        compared_plan_number="HID-SAN-01",
        recommended_action=recommended_action or "Coordinar desvío.",
        centroid_x_mm=153000.0,
        centroid_y_mm=-158500.0,
        bounds_minx_mm=148000.0,
        bounds_miny_mm=-163000.0,
        bounds_maxx_mm=158000.0,
        bounds_maxy_mm=-154000.0,
        zoom_tile_path=zoom_rel,
        raw_json=raw,
    )


def _meta() -> dict:
    return {
        "project_name": "Proyecto Demo",
        "folder_name": "NASAS09",
        "user_display": "Revisor",
        "run_date": "2026-06-18",
        "run_sequence": 1,
    }


def test_pdf_contains_main_checklist_table() -> None:
    pdf = build_incident_checklist_pdf(meta=_meta(), items=[_item(table_comment="Obs larga para tabla.")])
    text = _pdf_text(pdf)
    assert "Tabla principal" in text
    assert "Obs larga para tabla." in text


def test_pdf_contains_title_semantic() -> None:
    title = "ARQ-01_BASE / INC-001 / Contra HID-SAN-01 / Severidad crítica"
    pdf = build_incident_checklist_pdf(
        meta=_meta(),
        items=[_item(title_semantic=title, table_comment="x")],
    )
    assert title in _pdf_text(pdf)


def test_pdf_contains_table_comment_not_only_short_label() -> None:
    pdf = build_incident_checklist_pdf(
        meta=_meta(),
        items=[
            _item(
                table_comment="COMENTARIO_TABLA_PR4_UNIQUE",
                short_label="INC-001: Breve.",
            )
        ],
    )
    text = _pdf_text(pdf)
    assert "COMENTARIO_TABLA_PR4_UNIQUE" in text or "COMENTARIO_TABLA_PR4" in text


def test_pdf_uses_composed_visual_when_real(tmp_path: Path) -> None:
    composed_dir = tmp_path / "tiles" / "composed"
    composed_dir.mkdir(parents=True)
    svg_path = composed_dir / "incident_0001_full_page.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="red"/></svg>',
        encoding="utf-8",
    )
    item = _item(
        has_real_visual=True,
        composed_rel="composed/incident_0001_full_page.svg",
        table_comment="Con visual",
    )

    def resolver(it: ProjectClashItem, kind: str) -> Path | None:
        if kind == "composed":
            return svg_path
        return None

    pdf = build_incident_checklist_pdf(meta=_meta(), items=[item], tile_resolver=resolver)
    text = _pdf_text(pdf)
    assert VISUAL_UNAVAILABLE_MSG not in text


def test_pdf_shows_warning_when_no_real_visual() -> None:
    pdf = build_incident_checklist_pdf(
        meta=_meta(),
        items=[_item(has_real_visual=False, table_comment="Sin visual")],
    )
    assert VISUAL_UNAVAILABLE_MSG in _pdf_text(pdf)


def test_pdf_does_not_use_legacy_placeholder_as_real(tmp_path: Path) -> None:
    legacy = tmp_path / "tiles" / "incident_0001_annotated.svg"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>', encoding="utf-8")

    item = _item(has_real_visual=False, table_comment="Legacy exists but not real")

    def resolver(it: ProjectClashItem, kind: str) -> Path | None:
        if kind == "composed":
            return legacy  # should not be called when has_real_visual false
        return None

    pdf = build_incident_checklist_pdf(meta=_meta(), items=[item], tile_resolver=resolver)
    assert VISUAL_UNAVAILABLE_MSG in _pdf_text(pdf)


def test_pdf_one_page_per_incident_minimum() -> None:
    items = [
        _item(clash_code="incident_0001", table_comment="A"),
        _item(clash_code="incident_0002", table_comment="B"),
    ]
    pdf = build_incident_checklist_pdf(meta=_meta(), items=items)
    from pypdf import PdfReader

    pages = len(PdfReader(BytesIO(pdf)).pages)
    assert pages >= 2 + len(items)


def test_pdf_severity_summary_four_levels() -> None:
    items = [
        _item(clash_code="incident_0001", table_comment="a"),
        ProjectClashItem(
            id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            clash_code="incident_0002",
            priority="P3",
            severity="low",
            report_confidence="low",
            status="detected",
            table_comment="b",
            raw_json={"representative_conflict": {"plan_intersection_area_mm2": 1.0}},
        ),
    ]
    text = _pdf_text(build_incident_checklist_pdf(meta=_meta(), items=items))
    assert "Crítica" in text
    assert "Baja" in text


def test_pdf_technical_annex_includes_layers_and_handles() -> None:
    pdf = build_incident_checklist_pdf(meta=_meta(), items=[_item(table_comment="Anexo")])
    text = _pdf_text(pdf)
    assert "Anexo técnico" in text
    assert "HNDL_A" in text
    assert "ARQ_MURO" in text


def test_backward_compat_items_without_visual_paths() -> None:
    item = ProjectClashItem(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        clash_code="legacy_001",
        priority="P3",
        severity="medium",
        report_confidence="medium",
        status="detected",
        table_comment="Item legacy sin campos visuales",
        centroid_x_mm=100.0,
        centroid_y_mm=200.0,
    )
    pdf = build_incident_checklist_pdf(meta=_meta(), items=[item])
    assert pdf[:4] == b"%PDF"
    assert VISUAL_UNAVAILABLE_MSG in _pdf_text(pdf)


def test_candidate_only_excluded_from_pdf() -> None:
    assert _pdf_eligible(_item(candidate_only=True)) is False
    pdf = build_incident_checklist_pdf(
        meta=_meta(),
        items=[_item(candidate_only=True, table_comment="skip"), _item(table_comment="keep")],
    )
    text = _pdf_text(pdf)
    assert "keep" in text
    assert "skip" not in text


def test_pdf_is_valid_binary() -> None:
    pdf = build_incident_checklist_pdf(meta=_meta(), items=[_item(table_comment="ok")])
    assert pdf.startswith(b"%PDF")


def test_pdf_escapes_dangerous_user_text() -> None:
    item = _item(
        title_semantic='ARQ<script>alert(1)</script>_BASE / INC-001 / Contra X / Severidad alta',
        table_comment='A&B "comillas" \'simple\' Muro <estructural>',
        short_label='<b>no interpretar</b>',
        recommended_action="Revisar <layer>",
    )
    item.layer_a = 'LAYER<A>'
    item.layer_b = "LAYER'B\""
    item.dwg_a = 'Plan "A".dwg'
    pdf = build_incident_checklist_pdf(meta=_meta(), items=[item])
    assert pdf.startswith(b"%PDF")
    text = _pdf_text(pdf)
    assert "A&B" in text or "A&amp;B" in text
    assert "Muro" in text
    assert "estructural" in text


def test_pdf_invalid_svg_does_not_break_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "bad.svg"
    bad.write_text("<<<not valid svg>>>", encoding="utf-8")
    item = _item(has_real_visual=True, composed_rel="composed/x.svg", table_comment="bad svg")

    def resolver(_it: ProjectClashItem, kind: str) -> Path | None:
        return bad if kind == "composed" else None

    pdf = build_incident_checklist_pdf(meta=_meta(), items=[item], tile_resolver=resolver)
    assert pdf.startswith(b"%PDF")
    assert VISUAL_UNAVAILABLE_MSG in _pdf_text(pdf)
    assert SVG_EMBED_FAILED_SUFFIX.strip() in _pdf_text(pdf) or "SVG compuesto" in _pdf_text(pdf)


def test_pdf_zoom_only_as_inset_not_main(tmp_path: Path) -> None:
    composed = tmp_path / "composed.svg"
    zoom = tmp_path / "zoom.svg"
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><rect width="50" height="50"/></svg>'
    composed.write_text(svg, encoding="utf-8")
    zoom.write_text(svg, encoding="utf-8")
    item = _item(has_real_visual=True, table_comment="both visuals")

    def resolver(_it: ProjectClashItem, kind: str) -> Path | None:
        if kind == "composed":
            return composed
        if kind == "zoom":
            return zoom
        return None

    text = _pdf_text(build_incident_checklist_pdf(meta=_meta(), items=[item], tile_resolver=resolver))
    assert "Zoom (inset secundario)" in text
    assert VISUAL_UNAVAILABLE_MSG not in text


def test_pdf_order_by_severity_then_incident_code() -> None:
    low = _item(clash_code="incident_0003", table_comment="low", severity="low")
    high = _item(clash_code="incident_0001", table_comment="high", severity="high")
    crit = _item(clash_code="incident_0002", table_comment="crit", severity="critical")
    ordered = _sort_checklist_items([low, high, crit])
    assert [i.clash_code for i in ordered] == ["incident_0002", "incident_0001", "incident_0003"]


def test_resolver_not_called_when_has_real_visual_false() -> None:
    calls: list[str] = []

    def resolver(_it: ProjectClashItem, kind: str) -> Path | None:
        calls.append(kind)
        return None

    build_incident_checklist_pdf(
        meta=_meta(),
        items=[_item(has_real_visual=False, table_comment="no tile lookup")],
        tile_resolver=resolver,
    )
    assert calls == []


def test_export_human_pdf_still_uses_coordination_builder(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    from app.services.clash_export_service import ClashExportService

    called = {"coordination": 0, "checklist": 0}

    def fake_coordination(**kwargs):
        called["coordination"] += 1
        return b"%PDF-coord"

    def fake_checklist(**kwargs):
        called["checklist"] += 1
        return b"%PDF-checklist"

    monkeypatch.setattr(
        "app.services.clash_export_service.build_coordination_report_pdf",
        fake_coordination,
    )
    monkeypatch.setattr(
        "app.services.clash_export_service.build_incident_checklist_pdf",
        fake_checklist,
    )

    svc = ClashExportService(session=MagicMock(), workspace_id=uuid.uuid4())
    svc._project_svc = MagicMock()
    svc._project_svc.get_project = AsyncMock(return_value=MagicMock(name="proj"))
    workflow = MagicMock()
    workflow.list_workflow_rows_for_export = AsyncMock(
        return_value=(MagicMock(job_id="j1", folder_name="f", run_sequence=1), [])
    )
    workflow.resolve_tiles_root = MagicMock(return_value=None)
    workflow._tile_file = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.services.clash_export_service.ClashWorkflowService",
        lambda *_a, **_k: workflow,
    )
    svc._export_meta = AsyncMock(
        return_value={
            "project_name": "P",
            "folder_name": "F",
            "user_display": "U",
            "run_date": "2026-06-18",
            "run_sequence": 1,
        }
    )

    import asyncio

    asyncio.run(svc.export_human_pdf(MagicMock(), uuid.uuid4()))
    assert called["coordination"] == 1
    assert called["checklist"] == 0


def test_generate_checklist_pdf_fixture(tmp_path: Path) -> None:
    out = tmp_path / "checklist_fixture.pdf"
    pdf = build_incident_checklist_pdf(
        meta=_meta(),
        items=[_item(table_comment="fixture", title_semantic="ARQ-01_BASE / INC-001 / Contra HID / Severidad crítica")],
    )
    out.write_bytes(pdf)
    assert out.stat().st_size > 500
