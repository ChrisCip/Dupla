"""Tests for BC3 (FIEBDC-3) export — focusing on correctness and duplicate-free output."""

from pathlib import Path

from budget.export_bc3 import export_budget_bc3
from core.schemas import ProjectContext


def _make_context(project_id: str = "test_proj") -> ProjectContext:
    return ProjectContext(project_id=project_id, project_name="Test Project")


def _chapter_row(**kwargs):
    base = {
        "row_type": "chapter",
        "code": "CAP01",
        "nat": "cap",
        "unit": "",
        "summary": "Capítulo 1",
        "quantity": None,
        "unit_price": None,
        "amount": None,
        "chapter_id": "CAP01",
        "parent_chapter_id": None,
        "level": 1,
        "takeoff_key": None,
        "source_refs": [],
        "assumptions": [],
        "metadata": {},
        "excel_row": None,
    }
    base.update(kwargs)
    return base


def _line_row(**kwargs):
    base = {
        "row_type": "line",
        "code": "P0303130",
        "nat": "partida",
        "unit": "m3",
        "summary": "Zapata Z1",
        "quantity": 7.56,
        "unit_price": 399.4,
        "amount": 3019.46,
        "chapter_id": "CAP01",
        "parent_chapter_id": None,
        "level": 2,
        "takeoff_key": "level_01:footing",
        "source_refs": [],
        "assumptions": [],
        "metadata": {},
        "excel_row": None,
    }
    base.update(kwargs)
    return base


def test_bc3_export_produces_valid_file(tmp_path: Path) -> None:
    context = _make_context()
    rows = [
        _chapter_row(),
        _line_row(),
    ]
    out_path = tmp_path / "test.bc3"
    result = export_budget_bc3(context, rows, out_path)

    assert result.exists()
    content = result.read_text(encoding="latin-1")
    assert "~V|" in content
    assert "~C|" in content
    assert "~D|" in content
    assert "P0303130" in content


def test_bc3_export_no_duplicate_c_records(tmp_path: Path) -> None:
    """Multiple rows with the same BC3 code must produce exactly one ~C record."""
    context = _make_context()
    rows = [
        _chapter_row(code="CAP01", chapter_id="CAP01"),
        _line_row(code="P0303130", chapter_id="CAP01", quantity=7.56),
        _line_row(code="P0303130", chapter_id="CAP01", quantity=3.21),  # duplicate code
    ]
    out_path = tmp_path / "dedup.bc3"
    export_budget_bc3(context, rows, out_path)

    content = out_path.read_text(encoding="latin-1")
    # Count occurrences of the ~C record for P0303130
    c_records_for_code = [
        line for line in content.splitlines()
        if line.startswith("~C|P0303130|")
    ]
    assert len(c_records_for_code) == 1, (
        f"Expected 1 ~C record for P0303130, got {len(c_records_for_code)}"
    )


def test_bc3_export_no_duplicate_m_records(tmp_path: Path) -> None:
    """Only the first measurement for each code should be emitted."""
    context = _make_context()
    rows = [
        _chapter_row(code="CAP01", chapter_id="CAP01"),
        _line_row(code="P0501101", chapter_id="CAP01", quantity=100.0),
        _line_row(code="P0501101", chapter_id="CAP01", quantity=50.0),
    ]
    out_path = tmp_path / "dedup_m.bc3"
    export_budget_bc3(context, rows, out_path)

    content = out_path.read_text(encoding="latin-1")
    m_records_for_code = [
        line for line in content.splitlines()
        if line.startswith("~M|P0501101#|")
    ]
    assert len(m_records_for_code) == 1, (
        f"Expected 1 ~M record for P0501101, got {len(m_records_for_code)}"
    )


def test_bc3_export_unique_children_in_d_record(tmp_path: Path) -> None:
    """~D decomposition records must not list the same child code twice."""
    context = _make_context()
    rows = [
        _chapter_row(code="CAP02", summary="Capítulo 2", chapter_id="CAP02"),
        _line_row(code="PX001", chapter_id="CAP02", quantity=5.0),
        _line_row(code="PX001", chapter_id="CAP02", quantity=2.0),
    ]
    out_path = tmp_path / "dedup_d.bc3"
    export_budget_bc3(context, rows, out_path)

    content = out_path.read_text(encoding="latin-1")
    d_line = next(
        (line for line in content.splitlines() if line.startswith("~D|CAP02#|")),
        None,
    )
    assert d_line is not None, "~D record for CAP02 not found"
    # Count how many times PX001 appears in the ~D line
    occurrences = d_line.count("PX001")
    assert occurrences == 1, (
        f"PX001 appears {occurrences} times in ~D record, expected 1: {d_line}"
    )


def test_bc3_export_multiple_chapters(tmp_path: Path) -> None:
    """Two different chapters with different lines should both appear correctly."""
    context = _make_context()
    rows = [
        _chapter_row(code="CAP01", summary="MOVIMIENTO DE TIERRAS", chapter_id="CAP01"),
        _chapter_row(code="CAP02", summary="HORMIGON ARMADO", chapter_id="CAP02"),
        _line_row(code="P0101001", chapter_id="CAP01", summary="Excavacion manual", quantity=10.0),
        _line_row(code="P0202001", chapter_id="CAP02", summary="Columna HA", quantity=5.0),
    ]
    out_path = tmp_path / "multi_ch.bc3"
    export_budget_bc3(context, rows, out_path)

    content = out_path.read_text(encoding="latin-1")
    assert "CAP01" in content
    assert "CAP02" in content
    assert "P0101001" in content
    assert "P0202001" in content
