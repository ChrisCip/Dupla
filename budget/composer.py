"""
Budget composition layer for workbook-ready budget rows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from core.schemas import (
    BudgetCandidate,
    BudgetChapter,
    BudgetLine,
    BudgetRow,
    ProjectContext,
    QuantityTakeoff,
)

from .chapter_rules import (
    ChapterSegment,
    build_budget_summary,
    chapter_path_for_takeoff,
    select_strong_candidate,
)

DATA_START_ROW = 4


def _extract_unit_price(
    candidate: BudgetCandidate | None,
    bc3_catalog: dict[str, Any] | None,
) -> float | None:
    """Extract unit price from a BC3 candidate.

    Checks candidate.rationale first (GPT-4o classifier stores JSON there),
    then falls back to a direct BC3 catalog lookup by code.
    """
    if candidate is None:
        return None

    # GPT-4o classifier stores: rationale='{"unit_price": 12345.00, "match_type": "exacto"}'
    rationale = getattr(candidate, "rationale", "") or ""
    if rationale.startswith("{"):
        try:
            data = json.loads(rationale)
            price = data.get("unit_price")
            if price:
                return float(price)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Fallback: look up price in BC3 catalog by code
    if bc3_catalog and candidate.bc3_code:
        concept = bc3_catalog.get("concepts_by_code", {}).get(candidate.bc3_code, {})
        price = concept.get("price")
        if price:
            return float(price)

    return None


@dataclass
class _PreparedLine:
    takeoff: QuantityTakeoff
    chapter_path: list[ChapterSegment]
    summary: str
    candidate: BudgetCandidate | None


@dataclass
class _ChapterNode:
    chapter: BudgetChapter
    children: list[str] = field(default_factory=list)
    lines: list[BudgetLine] = field(default_factory=list)


def _derived_from_key(takeoff: QuantityTakeoff) -> str | None:
    value = takeoff.trace.metadata.get("derived_from")
    if value is None:
        value = takeoff.inputs.get("derived_from")
    return str(value) if value else None


def _takeoff_prefix(item_key: str) -> str:
    return item_key.rsplit(":", 1)[0] if ":" in item_key else item_key


def _budgetable_takeoff(
    takeoff: QuantityTakeoff,
    *,
    derived_from_keys: set[str],
    concrete_volume_prefixes: set[str],
) -> bool:
    item_type = takeoff.item_type.lower()

    if takeoff.unit.lower() == "flag":
        return False

    if item_type == "pres_reference_line":
        return True

    if item_type in {
        "structural_count",
        "structural_length",
        "structural_area",
        "structural_volume",
        "wall_length",
        "wall_gross_area",
        "wet_area_count",
    }:
        return False

    if item_type.endswith("reinforcement_required_hint"):
        return False

    if takeoff.item_key in derived_from_keys:
        return False

    if item_type.endswith("_volume") and not item_type.endswith("_concrete_volume"):
        if _takeoff_prefix(takeoff.item_key) in concrete_volume_prefixes:
            return False

    if item_type.startswith(("beam_", "column_", "slab_")):
        return any(
            token in item_type
            for token in ("concrete_volume", "volume", "area", "formwork_area_hint")
        ) and not item_type.endswith(("_length", "_count"))

    if item_type.startswith("footing_"):
        return any(
            token in item_type
            for token in ("concrete_volume", "volume", "area", "formwork_area_hint")
        ) and not item_type.endswith(("_length", "_count"))

    if item_type in {"stair_count", "fixture_count", "kitchen_count", "kitchen_area"}:
        return True

    if item_type.startswith("wall_"):
        return item_type in {
            "wall_net_area",
            "wall_volume",
            "wall_waterproofing",
            "wall_finish_paint",
            "wall_finish_plaster",
        }

    if item_type.startswith("floor_"):
        return item_type in {"floor_area", "floor_finish", "floor_waterproofing"}

    if item_type.startswith("ceiling_"):
        return item_type in {"ceiling_area", "ceiling_finish_paint"}

    if item_type.startswith("door_"):
        return True

    if item_type.startswith("window_"):
        return True

    if item_type.startswith("wet_area_"):
        return item_type != "wet_area_count"

    return False


def _sort_key(prepared: _PreparedLine) -> tuple[Any, ...]:
    return (
        tuple(segment.code for segment in prepared.chapter_path),
        prepared.summary.lower(),
        prepared.takeoff.item_key,
    )


def _ensure_chapter_path(
    chapter_nodes: dict[str, _ChapterNode],
    chapter_lookup: list[BudgetChapter],
    path: list[ChapterSegment],
) -> str:
    parent_id = "ROOT"
    titles_so_far: list[str] = []
    for level, segment in enumerate(path, start=1):
        titles_so_far.append(segment.title)
        chapter_id = f"DUP-CH-{segment.code}"
        if chapter_id not in chapter_nodes:
            chapter = BudgetChapter(
                chapter_id=chapter_id,
                code=chapter_id,
                title=segment.title,
                level=level,
                parent_id=None if parent_id == "ROOT" else parent_id,
                path=list(titles_so_far),
            )
            chapter_nodes[chapter_id] = _ChapterNode(chapter=chapter)
            chapter_lookup.append(chapter)
            if parent_id != "ROOT":
                parent = chapter_nodes[parent_id]
                if chapter_id not in parent.children:
                    parent.children.append(chapter_id)
                if chapter_id not in parent.chapter.child_ids:
                    parent.chapter.child_ids.append(chapter_id)
        parent_id = chapter_id
    return parent_id


def _sum_formula(amount_rows: list[int]) -> str:
    if not amount_rows:
        return "=0"
    refs = ",".join(f"G{row_number}" for row_number in amount_rows)
    return f"=SUM({refs})"


def _flatten_chapters(
    chapter_nodes: dict[str, _ChapterNode],
    node_id: str,
    rows: list[BudgetRow],
) -> int | None:
    node = chapter_nodes[node_id]
    node.children.sort()
    node.lines.sort(key=lambda line: (line.summary.lower(), line.code, line.takeoff_key))

    chapter_row = BudgetRow(
        row_type="chapter",
        code=node.chapter.code,
        nat="Capítulo",
        unit="",
        summary=node.chapter.title,
        chapter_id=node.chapter.chapter_id,
        parent_chapter_id=node.chapter.parent_id,
        level=node.chapter.level,
        metadata={"path": list(node.chapter.path)},
    )
    rows.append(chapter_row)
    chapter_row_index = len(rows) - 1

    subtotal_source_indices: list[int] = []

    for line in node.lines:
        row = BudgetRow(
            row_type="line",
            code=line.code,
            nat=line.nat,
            unit=line.unit,
            summary=line.summary,
            quantity=line.quantity,
            unit_price=line.unit_price,
            amount=line.amount_formula,
            chapter_id=line.chapter_id,
            parent_chapter_id=node.chapter.parent_id,
            level=node.chapter.level,
            takeoff_key=line.takeoff_key,
            source_refs=list(line.source_refs),
            assumptions=list(line.assumptions),
            metadata=dict(line.metadata),
        )
        rows.append(row)
        subtotal_source_indices.append(len(rows) - 1)

    for child_id in node.children:
        child_subtotal_index = _flatten_chapters(chapter_nodes, child_id, rows)
        if child_subtotal_index is not None:
            subtotal_source_indices.append(child_subtotal_index)

    subtotal_row = BudgetRow(
        row_type="subtotal",
        code="",
        nat="Subtotal/Cierre de capítulo",
        unit="",
        summary=f"Subtotal {node.chapter.title}",
        quantity=1,
        unit_price=None,
        amount=None,
        chapter_id=node.chapter.chapter_id,
        parent_chapter_id=node.chapter.parent_id,
        level=node.chapter.level,
        metadata={
            "path": list(node.chapter.path),
            "source_row_indices": list(subtotal_source_indices),
            "chapter_code": node.chapter.code,
        },
    )
    rows.append(subtotal_row)
    subtotal_row_index = len(rows) - 1
    chapter_row.metadata["subtotal_row_index"] = subtotal_row_index
    return subtotal_row_index


def _finalize_formulas(
    chapters: list[BudgetChapter],
    lines: list[BudgetLine],
    rows: list[BudgetRow],
) -> None:
    line_map = {line.line_id: line for line in lines}

    for index, row in enumerate(rows, start=DATA_START_ROW):
        row.excel_row = index

    for row in rows:
        if row.row_type == "line":
            row.amount = f"=ROUND(E{row.excel_row}*F{row.excel_row},2)"
            line_id = str(row.metadata.get("line_id", ""))
            if line_id in line_map:
                line_map[line_id].amount_formula = str(row.amount)
                line_map[line_id].metadata["excel_row"] = row.excel_row
            continue

        if row.row_type == "subtotal":
            source_row_indices = list(row.metadata.get("source_row_indices", []))
            source_excel_rows = [
                rows[source_index].excel_row
                for source_index in source_row_indices
                if 0 <= source_index < len(rows) and rows[source_index].excel_row is not None
            ]
            row.quantity = 1
            row.unit_price = _sum_formula(source_excel_rows)
            row.amount = f"=ROUND(E{row.excel_row}*F{row.excel_row},2)"
            row.metadata["source_excel_rows"] = source_excel_rows
            continue

        subtotal_row_index = row.metadata.get("subtotal_row_index")
        if row.row_type == "chapter" and isinstance(subtotal_row_index, int):
            subtotal_excel_row = rows[subtotal_row_index].excel_row
            row.quantity = f"=E{subtotal_excel_row}"
            row.unit_price = f"=F{subtotal_excel_row}"
            row.amount = f"=G{subtotal_excel_row}"

    for chapter in chapters:
        chapter.line_keys = sorted(set(chapter.line_keys))


def compose_budget_rows(
    context: ProjectContext,
    takeoffs: Iterable[QuantityTakeoff],
    candidates_by_takeoff: dict[str, list[BudgetCandidate]],
    *,
    bc3_catalog: dict[str, Any] | None = None,
) -> tuple[list[BudgetChapter], list[BudgetLine], list[BudgetRow]]:
    takeoff_list = list(takeoffs)
    derived_from_keys = {
        derived_from
        for takeoff in takeoff_list
        for derived_from in [_derived_from_key(takeoff)]
        if derived_from
    }
    concrete_volume_prefixes = {
        _takeoff_prefix(takeoff.item_key)
        for takeoff in takeoff_list
        if takeoff.item_type.lower().endswith("_concrete_volume")
    }

    prepared_lines: list[_PreparedLine] = []
    for takeoff in takeoff_list:
        if not _budgetable_takeoff(
            takeoff,
            derived_from_keys=derived_from_keys,
            concrete_volume_prefixes=concrete_volume_prefixes,
        ):
            continue

        strong_candidate = select_strong_candidate(
            takeoff,
            candidates_by_takeoff.get(takeoff.item_key, []),
        )
        prepared_lines.append(
            _PreparedLine(
                takeoff=takeoff,
                chapter_path=chapter_path_for_takeoff(takeoff),
                summary=build_budget_summary(takeoff, strong_candidate),
                candidate=strong_candidate,
            )
        )

    prepared_lines.sort(key=_sort_key)

    chapter_nodes: dict[str, _ChapterNode] = {
        "ROOT": _ChapterNode(
            chapter=BudgetChapter(
                chapter_id="ROOT",
                code="ROOT",
                title=context.project_name or context.project_id or "PRESUPUESTO",
                level=0,
            )
        )
    }
    chapters: list[BudgetChapter] = []
    lines: list[BudgetLine] = []
    internal_code_counter = 1

    for line_index, prepared in enumerate(prepared_lines, start=1):
        leaf_chapter_id = _ensure_chapter_path(chapter_nodes, chapters, prepared.chapter_path)
        chapter_nodes[leaf_chapter_id].chapter.line_keys.append(prepared.takeoff.item_key)

        if prepared.candidate is not None:
            line_code = prepared.candidate.bc3_code.strip()
        else:
            line_code = f"DUP-{internal_code_counter:04d}"
            internal_code_counter += 1

        budget_line = BudgetLine(
            line_id=f"BLINE-{line_index:04d}",
            takeoff_key=prepared.takeoff.item_key,
            chapter_id=leaf_chapter_id,
            code=line_code,
            nat="Partida",
            unit=prepared.takeoff.unit,
            summary=prepared.summary,
            quantity=prepared.takeoff.quantity,
            unit_price=_extract_unit_price(prepared.candidate, bc3_catalog),
            candidate_code=prepared.candidate.bc3_code if prepared.candidate else None,
            candidate_score=prepared.candidate.score if prepared.candidate else None,
            source_refs=list(prepared.takeoff.source_refs),
            assumptions=list(prepared.takeoff.assumptions),
            metadata={
                "item_type": prepared.takeoff.item_type,
                "level_id": prepared.takeoff.level_id,
                "line_id": f"BLINE-{line_index:04d}",
                "chapter_path": [segment.title for segment in prepared.chapter_path],
                "chapter_codes": [segment.code for segment in prepared.chapter_path],
                "candidate_summary": prepared.candidate.summary if prepared.candidate else None,
                "candidate_rationale": prepared.candidate.rationale if prepared.candidate else None,
                "trace_metadata": dict(prepared.takeoff.trace.metadata),
            },
        )
        lines.append(budget_line)
        chapter_nodes[leaf_chapter_id].lines.append(budget_line)

    chapter_nodes["ROOT"].children = sorted(
        chapter_id
        for chapter_id, node in chapter_nodes.items()
        if chapter_id != "ROOT" and node.chapter.parent_id is None
    )

    rows: list[BudgetRow] = []
    for child_id in chapter_nodes["ROOT"].children:
        _flatten_chapters(chapter_nodes, child_id, rows)

    _finalize_formulas(chapters, lines, rows)
    return chapters, lines, rows


def compose_budget(
    context: ProjectContext,
    takeoffs: Iterable[QuantityTakeoff],
    candidates_by_takeoff: dict[str, list[BudgetCandidate]],
    *,
    bc3_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chapters, lines, rows = compose_budget_rows(
        context, takeoffs, candidates_by_takeoff, bc3_catalog=bc3_catalog
    )
    return {
        "project_context": context.to_dict(),
        "chapters": [chapter.to_dict() for chapter in chapters],
        "lines": [line.to_dict() for line in lines],
        "rows": [row.to_dict() for row in rows],
    }
