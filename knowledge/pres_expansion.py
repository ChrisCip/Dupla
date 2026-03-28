"""
Expand quantity takeoffs using real budget lines from PRES.xlsx (training pairs).

Each hybrid level (e.g. vision page) is matched to PRES chapter levels; matching
training pairs become synthetic takeoffs with deterministic BC3 candidates (no GPT).
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.schemas import BudgetCandidate, LevelInventory, QuantityTakeoff, QuantityTrace

from .training_data import TrainingPair


def _level_index_from_string(text: str) -> int | None:
    lowered = text.lower()
    match = re.search(r"nivel\s*(\d+)", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"page_(\d+)", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"_(\d{3})(?:\.[^.]+)?$", lowered)
    if match:
        return int(match.group(1))
    return None


def _pres_level_matches_hybrid(ctx_level: str, level_name: str, level_id: str) -> bool:
    cl = ctx_level.strip().lower()
    hn = (level_name or "").lower()
    hid = (level_id or "").lower()
    blob = f"{hn} {hid}"

    if "semisotano" in cl or "semisótano" in cl:
        return "semisotano" in blob or "sotano" in blob or "sótano" in blob
    if "techo" in cl and "nivel" not in cl:
        return "techo" in blob
    if "miscelaneo" in cl or "misceláneo" in cl:
        return "misc" in blob
    if "equipo" in cl and "electric" in cl:
        return "electric" in blob and ("equipo" in blob or "equip" in blob)

    idx_c = _level_index_from_string(cl)
    idx_h = _level_index_from_string(hn) or _level_index_from_string(hid)
    if idx_c is not None and idx_h is not None and idx_c == idx_h:
        return True

    if len(cl) > 8 and cl in blob:
        return True
    return False


def _split_context(input_context: str) -> tuple[str, str]:
    parts = input_context.split("|", 1)
    level = parts[0].strip() if parts else ""
    discipline = parts[1].strip() if len(parts) > 1 else ""
    return level, discipline


def synthetic_takeoffs_from_pres(
    levels: list[LevelInventory],
    training_pairs: list[TrainingPair],
    *,
    max_per_level: int = 250,
) -> list[QuantityTakeoff]:
    if not levels or not training_pairs:
        return []

    extra: list[QuantityTakeoff] = []
    for inv in levels:
        level_pairs: list[TrainingPair] = []
        for pair in training_pairs:
            ctx_level, _disc = _split_context(pair.input_context)
            if _pres_level_matches_hybrid(ctx_level, inv.level_name, inv.level_id):
                level_pairs.append(pair)

        level_pairs.sort(key=lambda p: (p.output_bc3_code, p.output_description))
        for idx, pair in enumerate(level_pairs[:max_per_level]):
            ctx_level, disc = _split_context(pair.input_context)
            code = pair.output_bc3_code.strip()
            if not code:
                continue
            item_key = f"{inv.level_id}:pres:{code}:{idx}"
            extra.append(
                QuantityTakeoff(
                    item_key=item_key,
                    item_type="pres_reference_line",
                    level_id=inv.level_id,
                    unit=pair.output_unit or "",
                    quantity=float(pair.output_quantity),
                    formula="pres.xlsx plantilla (referencia)",
                    inputs={
                        "pres_bc3_code": code,
                        "pres_summary": pair.output_description,
                        "pres_context": pair.input_context,
                        "pres_discipline": disc,
                    },
                    assumptions=[
                        f"Linea de referencia desde presupuesto real ({pair.source}) para calibracion."
                    ],
                    source_refs=[pair.source],
                    trace=QuantityTrace(
                        evidence=[pair.output_description],
                        metadata={
                            "pres_expansion": True,
                            "pres_level": ctx_level,
                            "pres_discipline": disc,
                            "pres_unit_price": float(pair.output_price),
                        },
                    ),
                )
            )
    return extra


def inject_pres_reference_candidates(
    takeoffs: list[QuantityTakeoff],
    candidates_by_takeoff: dict[str, list[BudgetCandidate]],
    bc3_catalog: dict[str, Any],
) -> None:
    concepts = bc3_catalog.get("concepts_by_code", {})
    for takeoff in takeoffs:
        if takeoff.item_type != "pres_reference_line":
            continue
        code = str(takeoff.inputs.get("pres_bc3_code", "")).strip()
        if not code:
            continue
        summary = str(takeoff.inputs.get("pres_summary", "") or code)
        concept = concepts.get(code, {}) if isinstance(concepts, dict) else {}
        price = float(concept.get("price") or 0)
        if price == 0.0:
            for item in bc3_catalog.get("items", []):
                if str(item.get("code", "")).strip() == code:
                    price = float(item.get("price") or 0)
                    break
        if price == 0.0:
            price = float(takeoff.trace.metadata.get("pres_unit_price") or 0)

        rationale = json.dumps(
            {
                "unit_price": price,
                "match_type": "exacto",
                "source": "pres_reference",
            },
            ensure_ascii=False,
        )
        candidates_by_takeoff[takeoff.item_key] = [
            BudgetCandidate(
                takeoff_key=takeoff.item_key,
                bc3_code=code,
                summary=summary[:200],
                unit=takeoff.unit,
                score=0.99,
                rationale=rationale,
                source="pres_reference",
            )
        ]
