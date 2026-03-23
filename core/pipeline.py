"""
Pipeline helpers for the active APS/JSON-first architecture.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from agents.classifier_agent import match_takeoffs_to_bc3
from agents.quantifier_agent import quantify_inventory
from core.inventory_builder import build_level_inventory
from core.schemas import (
    BudgetCandidate,
    LevelInventory,
    ProjectContext,
    QuantityTakeoff,
    level_inventory_from_dict,
)
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


def build_expanded_takeoffs_from_inventory(
    levels: list[LevelInventory],
    rules_engine: RulesEngine | None = None,
) -> tuple[list[QuantityTakeoff], list[QuantityTakeoff]]:
    """
    Quantify inventory deterministically, then expand base takeoffs through the
    configured rule engine.
    """
    engine = rules_engine or default_rules_engine()
    base_takeoffs = quantify_inventory(levels)
    expanded_takeoffs = engine.apply(base_takeoffs)
    return base_takeoffs, expanded_takeoffs


def _coerce_vision_payloads(
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
) -> list[LevelInventory | Mapping[str, Any]]:
    if vision_payloads is None:
        return []
    if isinstance(vision_payloads, LevelInventory):
        return [vision_payloads]
    if isinstance(vision_payloads, Mapping):
        return [vision_payloads]
    return list(vision_payloads)


def build_hybrid_inventory(
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
) -> list[LevelInventory]:
    """
    Build merged hybrid inventories from normalized CAD facts and vision payloads.

    Each vision payload is normalized to a `LevelInventory`, then merged with the
    CAD-derived inventory via `build_level_inventory(...)`.
    """
    coerced_payloads = _coerce_vision_payloads(vision_payloads)
    if not coerced_payloads:
        fallback_name = str(cad_facts.get("project") or "level_01")
        return [
            build_level_inventory(
                cad_facts,
                None,
                level_id="level_01",
                level_name=fallback_name,
            )
        ]

    hybrid_levels: list[LevelInventory] = []
    for index, payload in enumerate(coerced_payloads, start=1):
        if isinstance(payload, LevelInventory):
            vision_level = payload
        else:
            payload_dict = dict(payload)
            payload_dict.setdefault("level_id", f"level_{index:02d}")
            payload_dict.setdefault("level_name", payload_dict["level_id"])
            vision_level = level_inventory_from_dict(payload_dict, default_source="vision")

        hybrid_levels.append(
            build_level_inventory(
                cad_facts,
                vision_level,
                level_id=vision_level.level_id,
                level_name=vision_level.level_name,
            )
        )

    return hybrid_levels


def build_takeoffs_from_sources(
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
) -> tuple[list[LevelInventory], list[QuantityTakeoff]]:
    """
    Official hybrid Stage 2/3 path:
        normalized CAD facts + vision inventory -> hybrid inventory -> quantity takeoffs
    """
    hybrid_inventory = build_hybrid_inventory(cad_facts, vision_payloads)
    return hybrid_inventory, quantify_inventory(hybrid_inventory)


def build_expanded_takeoffs_from_sources(
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
    rules_engine: RulesEngine | None = None,
) -> tuple[list[LevelInventory], list[QuantityTakeoff], list[QuantityTakeoff]]:
    hybrid_inventory = build_hybrid_inventory(cad_facts, vision_payloads)
    base_takeoffs, expanded_takeoffs = build_expanded_takeoffs_from_inventory(
        hybrid_inventory,
        rules_engine=rules_engine,
    )
    return hybrid_inventory, base_takeoffs, expanded_takeoffs


def build_budget_from_sources(
    context: ProjectContext,
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
    bc3_catalog: dict[str, Any],
    rules_engine: RulesEngine | None = None,
) -> dict[str, Any]:
    hybrid_inventory, base_takeoffs, expanded_takeoffs = build_expanded_takeoffs_from_sources(
        cad_facts,
        vision_payloads,
        rules_engine=rules_engine,
    )
    candidates = match_takeoffs_to_bc3(expanded_takeoffs, bc3_catalog)
    budget = build_final_budget(context, expanded_takeoffs, candidates)
    budget["hybrid_inventory"] = [level.to_dict() for level in hybrid_inventory]
    budget["base_takeoffs"] = [takeoff.to_dict() for takeoff in base_takeoffs]
    return budget


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
