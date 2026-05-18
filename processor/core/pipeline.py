"""
Pipeline helpers for the active APS/JSON-first architecture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from agents.classifier_agent import match_takeoffs_to_bc3
from agents.quantifier_agent import quantify_inventory
from budget.composer import compose_budget
from core.inventory_builder import build_level_inventory
from core.quality_engine import evaluate_semantic_quality
from core.schemas import (
    BudgetCandidate,
    LevelInventory,
    ProjectContext,
    QuantityTakeoff,
    QuantityTrace,
    level_inventory_from_dict,
)
def infer_source_discipline(takeoff: QuantityTakeoff, context: ProjectContext | None) -> str:
    if context and context.metadata:
        return str(context.metadata.get("discipline_id") or "architectural")
    return "architectural"
from core.semantic_adapter import adapt_semantic_to_inventory
from core.semantic_enrichment import enrich_semantics
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.pres_expansion import synthetic_takeoffs_from_pres
from knowledge.training_data import extract_training_pairs
try:
    from pricing.construcosto_loader import load_construcosto_snapshot
except ImportError:
    def load_construcosto_snapshot() -> Any:
        class DummySnapshot:
            count = 0
        return DummySnapshot()
from processors.bc3_parser import parse_bc3
from processors.json_processor import process_autodesk_json
from rules_engine import RulesEngine, default_rules_engine

logger = logging.getLogger("dupla.pipeline")


def _runner_discipline_canonical(context: ProjectContext | None) -> str | None:
    """Disciplina de corrida (arquitectonica|estructural|electrica|sanitaria) desde metadata, o None."""
    if context is None or not context.metadata:
        return None
    if not str(context.metadata.get("discipline_id") or "").strip():
        return None
    probe = QuantityTakeoff(
        item_key="__discipline_probe__",
        item_type="wall_net_area",
        unit="m2",
        quantity=0.0,
        formula="",
        trace=QuantityTrace(),
    )
    return infer_source_discipline(probe, context)


def _stamp_takeoffs_source_discipline(
    takeoffs: Iterable[QuantityTakeoff],
    label: str | None,
) -> None:
    if not label:
        return
    for takeoff in takeoffs:
        takeoff.trace.metadata["source_discipline"] = label


def merge_pres_template_takeoffs(
    levels: list[LevelInventory],
    takeoffs: list[QuantityTakeoff],
    training_pairs: list[Any] | None,
    *,
    pres_template_takeoffs: bool = False,
    max_per_level: int = 250,
    fallback_unmatched: bool = True,
) -> list[QuantityTakeoff]:
    if not pres_template_takeoffs or not training_pairs:
        return takeoffs
    extra = synthetic_takeoffs_from_pres(
        levels,
        training_pairs,
        max_per_level=max_per_level,
        fallback_unmatched=fallback_unmatched,
    )
    seen = {t.item_key for t in takeoffs}
    merged = list(takeoffs)
    for item in extra:
        if item.item_key not in seen:
            merged.append(item)
            seen.add(item.item_key)
    return merged


async def _match_or_generate(
    expanded_takeoffs: list[QuantityTakeoff],
    bc3_catalog: dict[str, Any],
    *,
    embedding_index: Any | None = None,
    training_pairs: list[Any] | None = None,
    project_discipline_id: str | None = None,
) -> tuple[dict[str, list[BudgetCandidate]], dict[str, Any]]:
    """
    Try PartidaGenerator (GPT-4o generates project-specific partidas), fall back to
    legacy match_takeoffs_to_bc3 on any failure.

    Returns (candidates_dict, bc3_catalog_to_use). On the generator path the catalog
    is an extended copy with synthetic partida codes so _guard_budget_candidate passes.
    On the fallback path the original bc3_catalog is returned unchanged.
    """
    import os as _os  # local import — avoids shadowing the module-level namespace

    api_key = _os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from agents.partida_generator import PartidaGenerator
            from agents.partida_adapter import adapt_generated_to_legacy_format

            generator = PartidaGenerator()
            generated = await generator.generate(
                expanded_takeoffs,
                training_pairs=training_pairs,
                bc3_catalog=bc3_catalog,
            )
            if not generated:
                raise ValueError("PartidaGenerator returned empty result — using BC3 fallback")

            candidates, extended_catalog = adapt_generated_to_legacy_format(
                generated, expanded_takeoffs, bc3_catalog
            )
            logger.info("PartidaGenerator path: %d partidas generated", len(generated))
            return candidates, extended_catalog

        except Exception:
            logger.warning(
                "PartidaGenerator failed — falling back to BC3 matching", exc_info=True
            )
    else:
        logger.info("No OPENAI_API_KEY — skipping PartidaGenerator, using BC3 matching")

    candidates = await match_takeoffs_to_bc3(
        expanded_takeoffs,
        bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
        project_discipline_id=project_discipline_id,
    )
    return candidates, bc3_catalog


def _load_construcosto_if_available() -> Any:
    try:
        snapshot = load_construcosto_snapshot()
        if snapshot.count > 0:
            logger.info("ConstruCosto snapshot: %d entries loaded", snapshot.count)
            return snapshot
    except Exception:
        logger.debug("ConstruCosto snapshot not available", exc_info=True)
    return None


def build_final_budget(
    context: ProjectContext,
    takeoffs: Iterable[QuantityTakeoff],
    candidates_by_takeoff: dict[str, list[BudgetCandidate]],
    *,
    bc3_catalog: dict[str, Any] | None = None,
    construcosto_snapshot: Any | None = None,
) -> dict[str, Any]:
    takeoff_list = list(takeoffs)
    lines = []

    for takeoff in takeoff_list:
        candidates = candidates_by_takeoff.get(takeoff.item_key, [])
        lines.append(
            {
                "takeoff": takeoff.to_dict(),
                "candidates": [candidate.to_dict() for candidate in candidates],
            }
        )

    composed = compose_budget(
        context, takeoff_list, candidates_by_takeoff,
        bc3_catalog=bc3_catalog,
        construcosto_snapshot=construcosto_snapshot,
    )
    composed["budget_lines"] = lines
    composed["takeoffs"] = [takeoff.to_dict() for takeoff in takeoff_list]
    composed["candidates_by_takeoff"] = {
        key: [candidate.to_dict() for candidate in value]
        for key, value in candidates_by_takeoff.items()
    }
    return composed


async def build_budget_from_inventory(
    context: ProjectContext,
    levels: list[LevelInventory],
    bc3_catalog: dict[str, Any],
    rules_engine: RulesEngine | None = None,
    *,
    embedding_index: Any | None = None,
    training_pairs: list[Any] | None = None,
) -> dict[str, Any]:
    engine = rules_engine or default_rules_engine()
    project_discipline = _runner_discipline_canonical(context)
    base_takeoffs = quantify_inventory(levels, runner_source_discipline=project_discipline)
    expanded_takeoffs = engine.apply(base_takeoffs)
    expanded_takeoffs = merge_pres_template_takeoffs(
        levels,
        expanded_takeoffs,
        training_pairs,
        pres_template_takeoffs=bool(context.metadata.get("pres_template_takeoffs", False)),
        max_per_level=int(context.metadata.get("pres_max_per_level", 250)),
        fallback_unmatched=bool(context.metadata.get("pres_fallback_unmatched", True)),
    )
    _stamp_takeoffs_source_discipline(expanded_takeoffs, project_discipline)
    candidates, bc3_catalog_for_budget = await _match_or_generate(
        expanded_takeoffs,
        bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
        project_discipline_id=project_discipline,
    )
    snapshot = _load_construcosto_if_available()
    return build_final_budget(
        context, expanded_takeoffs, candidates,
        bc3_catalog=bc3_catalog_for_budget,
        construcosto_snapshot=snapshot,
    )


def build_expanded_takeoffs_from_inventory(
    levels: list[LevelInventory],
    rules_engine: RulesEngine | None = None,
    *,
    runner_source_discipline: str | None = None,
) -> tuple[list[QuantityTakeoff], list[QuantityTakeoff]]:
    """
    Quantify inventory deterministically, then expand base takeoffs through the
    configured rule engine.
    """
    engine = rules_engine or default_rules_engine()
    base_takeoffs = quantify_inventory(levels, runner_source_discipline=runner_source_discipline)
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


def _extract_level_markers(cad_facts: dict[str, Any]) -> list[str]:
    """Pull unique level names from inventory_hints.level_markers."""
    markers = cad_facts.get("inventory_hints", {}).get("level_markers", [])
    seen: set[str] = set()
    unique: list[str] = []
    for marker in markers:
        text = str(marker.get("content", "") if isinstance(marker, Mapping) else marker).strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    return unique


def _build_cad_only_levels(cad_facts: dict[str, Any]) -> list[LevelInventory]:
    """Build one LevelInventory per detected level marker, or a single fallback."""
    markers = _extract_level_markers(cad_facts)
    if not markers:
        fallback_name = str(cad_facts.get("project") or "level_01")
        return [
            build_level_inventory(cad_facts, None, level_id="level_01", level_name=fallback_name)
        ]
    levels: list[LevelInventory] = []
    for idx, name in enumerate(markers, start=1):
        level_id = f"level_{idx:02d}"
        levels.append(build_level_inventory(cad_facts, None, level_id=level_id, level_name=name))
    return levels


def build_hybrid_inventory(
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
) -> list[LevelInventory]:
    """
    Build merged hybrid inventories from normalized CAD facts and vision payloads.

    Each vision payload is normalized to a `LevelInventory`, then merged with the
    CAD-derived inventory via `build_level_inventory(...)`.
    Falls back to CAD-only when vision payloads are absent or ALL contain errors.
    """
    coerced_payloads = _coerce_vision_payloads(vision_payloads)
    if not coerced_payloads:
        logger.info("No vision payloads — building CAD-only inventory")
        return _build_cad_only_levels(cad_facts)

    error_count = 0
    hybrid_levels: list[LevelInventory] = []
    for index, payload in enumerate(coerced_payloads, start=1):
        if isinstance(payload, LevelInventory):
            vision_level = payload
        elif isinstance(payload, Mapping) and "error" in payload:
            error_count += 1
            logger.warning(
                "Vision payload %d contains error, skipping: %s",
                index, payload.get("error"),
            )
            continue
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

    if not hybrid_levels and cad_facts:
        logger.warning(
            "All %d vision payloads failed — falling back to CAD-only inventory",
            error_count,
        )
        return _build_cad_only_levels(cad_facts)

    logger.info(
        "Hybrid inventory built: %d levels (%d vision errors skipped)",
        len(hybrid_levels), error_count,
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


async def build_budget_from_sources(
    context: ProjectContext,
    cad_facts: dict[str, Any],
    vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | LevelInventory | Mapping[str, Any] | None,
    bc3_catalog: dict[str, Any],
    rules_engine: RulesEngine | None = None,
    *,
    embedding_index: Any | None = None,
    training_pairs: list[Any] | None = None,
) -> dict[str, Any]:
    logger.info("build_budget_from_sources: starting hybrid inventory + takeoffs")
    hybrid_inventory = build_hybrid_inventory(cad_facts, vision_payloads)

    # --- Semantic layer + quality ---
    semantic_building_dict: dict[str, Any] | None = None
    quality_report_obj = None
    disc_id = (context.metadata or {}).get("discipline_id", "")
    enable_semantic = bool((context.metadata or {}).get("enable_semantic_layer", False))

    if enable_semantic and disc_id:
        logger.info("[semantic] Enriching %s semantics (%d levels)...", disc_id, len(hybrid_inventory))
        sem_building = enrich_semantics(
            project_id=context.project_id,
            project_name=context.project_name,
            discipline=disc_id,
            levels=hybrid_inventory,
        )
        semantic_building_dict = sem_building.to_dict()
        logger.info(
            "[semantic] Building: %d elements, avg confidence %.3f",
            len(sem_building.elements),
            sem_building.confidence_score,
        )

        quality_report_obj = evaluate_semantic_quality(sem_building)
        logger.info(
            "[quality] OK=%d WARNING=%d BLOCKED=%d",
            quality_report_obj.ok_count,
            quality_report_obj.warning_count,
            quality_report_obj.blocked_count,
        )

        if quality_report_obj.blocked_count > 0:
            hybrid_inventory = adapt_semantic_to_inventory(
                sem_building, quality_report_obj, hybrid_inventory,
            )
            logger.info(
                "[semantic] Adapted inventory: %d BLOCKED entities filtered out",
                quality_report_obj.blocked_count,
            )

    project_discipline = _runner_discipline_canonical(context)
    base_takeoffs, expanded_takeoffs = build_expanded_takeoffs_from_inventory(
        hybrid_inventory,
        rules_engine=rules_engine,
        runner_source_discipline=project_discipline,
    )
    logger.info(
        "Takeoffs: %d base -> %d expanded (rules applied)",
        len(base_takeoffs), len(expanded_takeoffs),
    )

    expanded_takeoffs = merge_pres_template_takeoffs(
        hybrid_inventory,
        expanded_takeoffs,
        training_pairs,
        pres_template_takeoffs=bool(context.metadata.get("pres_template_takeoffs", False)),
        max_per_level=int(context.metadata.get("pres_max_per_level", 250)),
        fallback_unmatched=bool(context.metadata.get("pres_fallback_unmatched", True)),
    )
    logger.info("After PRES merge: %d takeoffs", len(expanded_takeoffs))

    _stamp_takeoffs_source_discipline(expanded_takeoffs, project_discipline)

    logger.info("Resolving candidates for %d takeoffs", len(expanded_takeoffs))
    candidates, bc3_catalog_for_budget = await _match_or_generate(
        expanded_takeoffs,
        bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
        project_discipline_id=project_discipline,
    )
    logger.info("Candidates resolved for %d takeoff keys", len(candidates))

    snapshot = _load_construcosto_if_available()
    budget = build_final_budget(
        context, expanded_takeoffs, candidates,
        bc3_catalog=bc3_catalog_for_budget,
        construcosto_snapshot=snapshot,
    )
    budget["hybrid_inventory"] = [level.to_dict() for level in hybrid_inventory]
    budget["base_takeoffs"] = [takeoff.to_dict() for takeoff in base_takeoffs]
    if semantic_building_dict is not None:
        budget["semantic_building"] = semantic_building_dict
    if quality_report_obj is not None:
        budget["quality_report"] = quality_report_obj.to_dict()

    logger.info(
        "Budget built: %d chapters, %d lines, %d rows",
        len(budget.get("chapters", [])),
        len(budget.get("lines", [])),
        len(budget.get("rows", [])),
    )
    return budget


def bootstrap_pipeline_inputs(context: ProjectContext) -> dict[str, Any]:
    """
    Load the reusable non-LLM inputs for the active pipeline.

    Vision/image analysis is intentionally kept outside this helper so it can be
    run independently or mocked in tests.
    """
    cad_facts = process_autodesk_json(context.source_json_path) if context.source_json_path else {}
    logger.info("CAD facts loaded: %d keys", len(cad_facts))

    bc3_catalog = parse_bc3(context.bc3_path) if context.bc3_path else {}
    logger.info("BC3 catalog: %d items", len(bc3_catalog.get("items", [])))

    embeddings = None
    if bc3_catalog.get("items"):
        try:
            embeddings = load_or_build_embeddings(bc3_catalog)
            logger.info("Embeddings built: %d vectors", len(getattr(embeddings, "metadata", [])))
        except Exception:
            logger.warning("Failed to build BC3 embeddings, continuing without them", exc_info=True)
            embeddings = None

    xlsx_path = context.metadata.get("xlsx_path") if context.metadata else None
    if not xlsx_path:
        default_xlsx = Path(__file__).resolve().parent.parent / "data" / "PRES.xlsx"
        if default_xlsx.exists():
            xlsx_path = str(default_xlsx)
    training_pairs: list[Any] = []
    if xlsx_path:
        try:
            training_pairs = extract_training_pairs(xlsx_path)
            logger.info("Training pairs loaded: %d from %s", len(training_pairs), xlsx_path)
        except Exception:
            logger.warning("Failed to load training pairs from %s", xlsx_path, exc_info=True)
            training_pairs = []

    construcosto = _load_construcosto_if_available()

    return {
        "project_context": context.to_dict(),
        "cad_facts": cad_facts,
        "bc3_catalog": bc3_catalog,
        "bc3_embeddings": embeddings,
        "training_pairs": training_pairs,
        "construcosto_snapshot": construcosto,
    }
