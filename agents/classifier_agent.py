"""
Deterministic BC3 candidate matching.

This is intentionally lightweight: it ranks BC3 concepts against takeoff
descriptions using token overlap and unit compatibility, without introducing a
project-specific ontology into the active path.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from core.schemas import BudgetCandidate, QuantityTakeoff


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", text.lower())
        if token and len(token) > 2
    }


def _query_text(takeoff: QuantityTakeoff) -> str:
    trace_values = " ".join(str(value) for value in takeoff.trace.values() if value)
    return f"{takeoff.item_key} {takeoff.source_element_type} {trace_values}"


def rank_budget_candidates(
    takeoff: QuantityTakeoff,
    bc3_catalog: dict[str, Any],
    top_k: int = 5,
) -> list[BudgetCandidate]:
    query_tokens = _tokenize(_query_text(takeoff))
    candidates: list[BudgetCandidate] = []

    for concept in bc3_catalog.get("items", []):
        summary = str(concept.get("summary", ""))
        long_text = str(concept.get("long_text", ""))
        candidate_tokens = _tokenize(f"{summary} {long_text}")
        if not candidate_tokens:
            continue

        overlap = query_tokens & candidate_tokens
        if not overlap:
            continue

        token_score = len(overlap) / max(len(query_tokens), 1)
        unit_bonus = 0.25 if str(concept.get("unit", "")).lower() == takeoff.unit.lower() else 0.0
        score = round(token_score + unit_bonus, 4)

        candidates.append(
            BudgetCandidate(
                takeoff_key=takeoff.item_key,
                bc3_code=str(concept.get("code", "")),
                summary=summary,
                unit=str(concept.get("unit", "")),
                score=score,
                rationale=f"Shared tokens: {', '.join(sorted(overlap))}",
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_k]


def match_takeoffs_to_bc3(
    takeoffs: Iterable[QuantityTakeoff],
    bc3_catalog: dict[str, Any],
    top_k: int = 3,
) -> dict[str, list[BudgetCandidate]]:
    """
    Rank candidate BC3 items for each takeoff.

    TODO: Add synonym dictionaries and language-specific stemming once the
    catalog coverage is broader than keyword overlap.
    """
    return {
        takeoff.item_key: rank_budget_candidates(takeoff, bc3_catalog, top_k=top_k)
        for takeoff in takeoffs
    }
