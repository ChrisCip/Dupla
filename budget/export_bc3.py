"""
BC3 (FIEBDC-3) writer for Presto-compatible budget export.

Generates a valid BC3 file from Dupla budget output that can be imported
directly into Presto, Arquímedes, or any FIEBDC-compatible tool.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from core.schemas import BudgetRow, ProjectContext

logger = logging.getLogger("dupla.export_bc3")

_FIEBDC_HEADER = "FIEBDC-3/2016"
_GENERATOR = "DUPLA"


def _escape_bc3(text: str) -> str:
    return text.replace("|", "/").replace("\\", "/").replace("~", "-").replace("\n", " ").strip()


def _format_price(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _coerce_row(row: BudgetRow | Mapping[str, object]) -> BudgetRow:
    if isinstance(row, BudgetRow):
        return row
    payload = dict(row)
    return BudgetRow(
        row_type=str(payload.get("row_type", "line")),
        code=str(payload.get("code", "")),
        nat=str(payload.get("nat", "")),
        unit=str(payload.get("unit", "")),
        summary=str(payload.get("summary", "")),
        quantity=payload.get("quantity"),
        unit_price=payload.get("unit_price"),
        amount=payload.get("amount"),
        chapter_id=payload.get("chapter_id"),
        parent_chapter_id=payload.get("parent_chapter_id"),
        level=int(payload.get("level", 0) or 0),
        takeoff_key=payload.get("takeoff_key"),
        source_refs=list(payload.get("source_refs", [])),
        assumptions=list(payload.get("assumptions", [])),
        metadata=dict(payload.get("metadata", {})),
        excel_row=payload.get("excel_row"),
    )


def _sanitize_code(code: str) -> str:
    """BC3 codes must not contain # or | characters."""
    return code.replace("#", "").replace("|", "").strip()


def export_budget_bc3(
    context: ProjectContext,
    rows: list[BudgetRow | Mapping[str, object]],
    output_path: str | Path,
) -> Path:
    """
    Export a Dupla budget to BC3 (FIEBDC-3) format.

    The generated file contains:
    - ~V record: version header
    - ~K record: regional settings (RD$ currency)
    - ~C records: concept definitions for root, chapters, and line items
    - ~D records: decomposition (hierarchy) linking chapters to lines
    - ~T records: long text descriptions
    - ~M records: measurement lines
    """
    coerced_rows = [_coerce_row(r) for r in rows]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    project_name = _escape_bc3(context.project_name or context.project_id or "DUPLA")
    today = datetime.now().strftime("%d%m%Y")

    chapters: list[BudgetRow] = []
    lines_by_chapter: dict[str, list[BudgetRow]] = {}
    all_line_codes: set[str] = set()

    for row in coerced_rows:
        if row.row_type == "chapter":
            chapters.append(row)
            chapter_id = row.chapter_id or row.code
            lines_by_chapter.setdefault(chapter_id, [])
        elif row.row_type == "line":
            chapter_id = row.chapter_id or "ROOT"
            lines_by_chapter.setdefault(chapter_id, []).append(row)
            all_line_codes.add(_sanitize_code(row.code))

    records: list[str] = []

    records.append(f"~V|{_FIEBDC_HEADER}|{_GENERATOR}|{today}|")

    records.append(
        "~K|\\2\\2\\2\\2\\2\\2\\EUR\\|"
        "0|0|0|0|0|0|0|0|"
    )

    root_code = _sanitize_code(project_name[:20])
    records.append(
        f"~C|{root_code}#||{_escape_bc3(project_name)}|||0|"
    )

    chapter_codes: list[str] = []
    for chapter in chapters:
        ch_code = _sanitize_code(chapter.code)
        ch_summary = _escape_bc3(chapter.summary)
        records.append(
            f"~C|{ch_code}#||{ch_summary}|||0|"
        )
        chapter_codes.append(ch_code)

    emitted_line_codes: set[str] = set()
    for row in coerced_rows:
        if row.row_type != "line":
            continue
        code = _sanitize_code(row.code)
        if code in emitted_line_codes:
            continue
        emitted_line_codes.add(code)
        unit = _escape_bc3(row.unit or "")
        summary = _escape_bc3(row.summary or "")

        price_value = row.unit_price
        if isinstance(price_value, str) and price_value.startswith("="):
            price_value = None
        price_str = _format_price(price_value)

        records.append(
            f"~C|{code}|{unit}|{summary}|{price_str}|{today}||"
        )

    if chapter_codes:
        children_tokens = "\\".join(
            f"{ch_code}\\1.000\\1.000" for ch_code in chapter_codes
        )
        records.append(f"~D|{root_code}#|{children_tokens}\\|")

    for chapter in chapters:
        ch_code = _sanitize_code(chapter.code)
        chapter_id = chapter.chapter_id or chapter.code
        child_lines = lines_by_chapter.get(chapter_id, [])
        if not child_lines:
            continue

        seen_child_codes: set[str] = set()
        unique_child_tokens: list[str] = []
        for line in child_lines:
            line_code = _sanitize_code(line.code)
            if line_code not in seen_child_codes:
                seen_child_codes.add(line_code)
                unique_child_tokens.append(f"{line_code}\\1.000\\1.000")

        if not unique_child_tokens:
            continue
        children_tokens = "\\".join(unique_child_tokens)
        records.append(f"~D|{ch_code}#|{children_tokens}\\|")

    emitted_measurement_codes: set[str] = set()
    for row in coerced_rows:
        if row.row_type != "line":
            continue
        code = _sanitize_code(row.code)
        if code in emitted_measurement_codes:
            continue

        qty = row.quantity
        if isinstance(qty, str) and qty.startswith("="):
            continue
        if qty is None:
            continue

        try:
            qty_float = float(qty)
        except (TypeError, ValueError):
            continue

        emitted_measurement_codes.add(code)
        takeoff_key = row.takeoff_key or ""
        summary_line = _escape_bc3(takeoff_key[:60]) if takeoff_key else _escape_bc3(row.summary[:60])

        records.append(
            f"~M|{code}#|1|{summary_line}\\1\\{qty_float:.3f}\\0.000\\0.000\\0.000\\|"
        )

    for chapter in chapters:
        ch_code = _sanitize_code(chapter.code)
        path_info = chapter.metadata.get("path", [])
        if path_info:
            long_text = " > ".join(str(p) for p in path_info)
            records.append(f"~T|{ch_code}#|{_escape_bc3(long_text)}|")

    bc3_content = "\n".join(records) + "\n"
    output.write_text(bc3_content, encoding="latin-1", errors="replace")
    logger.info(
        "BC3 exported: %s (%d records, %d chapters, %d lines)",
        output, len(records), len(chapters), len(all_line_codes),
    )
    return output
