"""
Pipeline helpers for the active APS/JSON-first architecture.
"""

from __future__ import annotations

from typing import Any, Iterable

from agents.classifier_agent import match_takeoffs_to_bc3
from agents.quantifier_agent import quantify_inventory
from core.schemas import BudgetCandidate, LevelInventory, ProjectContext, QuantityTakeoff
from processors.bc3_parser import parse_bc3
from processors.json_processor import process_autodesk_json
from rules_engine import RulesEngine, default_rules_engine


def build_final_budget(
    context: ProjectContext,
    takeoffs: Iterable[QuantityTakeoff],
    candidates_by_takeoff: dict[str, list[BudgetCandidate]],
) -> dict[str, Any]:
    lines = []

    for takeoff in takeoffs:
        candidates = candidates_by_takeoff.get(takeoff.item_key, [])
        lines.append(
            {
                "takeoff": takeoff.to_dict(),
                "candidates": [candidate.to_dict() for candidate in candidates],
            }
        )

    return {
        "project_context": context.to_dict(),
        "budget_lines": lines,
    }


def build_budget_from_inventory(
    context: ProjectContext,
    levels: list[LevelInventory],
    bc3_catalog: dict[str, Any],
    rules_engine: RulesEngine | None = None,
) -> dict[str, Any]:
    engine = rules_engine or default_rules_engine()
    base_takeoffs = quantify_inventory(levels)
    expanded_takeoffs = engine.apply(base_takeoffs)
    candidates = match_takeoffs_to_bc3(expanded_takeoffs, bc3_catalog)
    return build_final_budget(context, expanded_takeoffs, candidates)


def bootstrap_pipeline_inputs(context: ProjectContext) -> dict[str, Any]:
    """
    Load the reusable non-LLM inputs for the active pipeline.

    Vision/image analysis is intentionally kept outside this helper so it can be
    run independently or mocked in tests.
    """
    cad_facts = process_autodesk_json(context.source_json_path) if context.source_json_path else {}
    bc3_catalog = parse_bc3(context.bc3_path) if context.bc3_path else {}
    return {
        "project_context": context.to_dict(),
        "cad_facts": cad_facts,
        "bc3_catalog": bc3_catalog,
    }
