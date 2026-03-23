"""
Config-backed rule registry for deterministic takeoff expansion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from core.schemas import QuantityTakeoff, QuantityTrace

DEFAULT_RULES_PATH = Path(__file__).with_name("default_rules.json")


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _coerce_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def _takeoff_material_hint(takeoff: QuantityTakeoff) -> str | None:
    material_hint = takeoff.inputs.get("material_hint")
    if material_hint is None:
        material_hint = takeoff.trace.metadata.get("material_hint")
    return str(material_hint).lower() if material_hint else None


def _takeoff_context_tags(takeoff: QuantityTakeoff) -> set[str]:
    tags = set(_coerce_tags(takeoff.inputs.get("context_tags")))
    tags.update(_coerce_tags(takeoff.trace.metadata.get("context_tags")))
    tags.add(takeoff.item_type)
    tags.update(part for part in takeoff.item_type.split("_") if part)
    return {tag.lower() for tag in tags if tag}


@dataclass(frozen=True)
class RuleMatchCriteria:
    item_types: tuple[str, ...]
    material_hints: tuple[str, ...] = ()
    context_tags: tuple[str, ...] = ()

    def matches(self, takeoff: QuantityTakeoff) -> bool:
        if self.item_types and takeoff.item_type not in self.item_types:
            return False

        material_hint = _takeoff_material_hint(takeoff)
        if self.material_hints and material_hint not in self.material_hints:
            return False

        takeoff_tags = _takeoff_context_tags(takeoff)
        if self.context_tags and not set(self.context_tags).issubset(takeoff_tags):
            return False

        return True


@dataclass(frozen=True)
class DerivedTakeoffRule:
    suffix: str
    item_type: str
    unit: str
    factor: float = 1.0
    assumptions: tuple[str, ...] = ()
    context_tags: tuple[str, ...] = ()
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    description: str
    match: RuleMatchCriteria
    derive: tuple[DerivedTakeoffRule, ...]


class RuleRegistry:
    def __init__(self, rules: Iterable[RuleDefinition] | None = None) -> None:
        self.rules = list(rules or [])

    def matching_rules(self, takeoff: QuantityTakeoff) -> list[RuleDefinition]:
        return [rule for rule in self.rules if rule.match.matches(takeoff)]

    def derive_takeoffs(self, takeoff: QuantityTakeoff) -> list[QuantityTakeoff]:
        derived: list[QuantityTakeoff] = []
        for rule in self.matching_rules(takeoff):
            for derivative in rule.derive:
                derived.append(_build_derived_takeoff(takeoff, rule, derivative))
        return derived


def _build_derived_takeoff(
    takeoff: QuantityTakeoff,
    rule: RuleDefinition,
    derivative: DerivedTakeoffRule,
) -> QuantityTakeoff:
    context_tags = _dedupe(
        [
            *_coerce_tags(takeoff.inputs.get("context_tags")),
            *_coerce_tags(takeoff.trace.metadata.get("context_tags")),
            *derivative.context_tags,
        ]
    )
    formula = f"{takeoff.item_key}.quantity * {derivative.factor:g}"
    assumptions = _dedupe([*takeoff.assumptions, *derivative.assumptions])
    trace = QuantityTrace(
        source_entity_ids=list(takeoff.trace.source_entity_ids),
        source_entity_sources=list(takeoff.trace.source_entity_sources),
        steps=[
            *takeoff.trace.steps,
            f"Expanded via rule {rule.rule_id}:{derivative.suffix} using factor {derivative.factor:g}.",
        ],
        evidence=list(takeoff.trace.evidence),
        conflict_notes=list(takeoff.trace.conflict_notes),
        metadata={
            **takeoff.trace.metadata,
            "derived_from": takeoff.item_key,
            "derivation_rule_id": rule.rule_id,
            "derivation_suffix": derivative.suffix,
            "derivation_factor": derivative.factor,
            "derivation_formula": formula,
            "context_tags": context_tags,
        },
    )
    return QuantityTakeoff(
        item_key=f"{takeoff.item_key}:{rule.rule_id}:{derivative.suffix}",
        item_type=derivative.item_type,
        level_id=takeoff.level_id,
        unit=derivative.unit,
        quantity=takeoff.quantity * derivative.factor,
        formula=formula,
        inputs={
            **takeoff.inputs,
            **derivative.inputs,
            "base_quantity": takeoff.quantity,
            "base_unit": takeoff.unit,
            "base_item_type": takeoff.item_type,
            "derived_from": takeoff.item_key,
            "derivation_rule_id": rule.rule_id,
            "derivation_factor": derivative.factor,
            "context_tags": context_tags,
        },
        assumptions=assumptions,
        source_refs=list(takeoff.source_refs),
        trace=trace,
    )


def load_rule_registry(config_path: str | Path | None = None) -> RuleRegistry:
    path = Path(config_path) if config_path else DEFAULT_RULES_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))

    rules: list[RuleDefinition] = []
    for rule_payload in payload.get("rules", []):
        match_payload = rule_payload.get("match", {})
        derive_payload = rule_payload.get("derive", [])
        rules.append(
            RuleDefinition(
                rule_id=str(rule_payload["id"]),
                description=str(rule_payload.get("description", "")),
                match=RuleMatchCriteria(
                    item_types=tuple(str(item) for item in match_payload.get("item_types", [])),
                    material_hints=tuple(
                        str(item).lower() for item in match_payload.get("material_hints", [])
                    ),
                    context_tags=tuple(
                        str(item).lower() for item in match_payload.get("context_tags", [])
                    ),
                ),
                derive=tuple(
                    DerivedTakeoffRule(
                        suffix=str(item["suffix"]),
                        item_type=str(item["item_type"]),
                        unit=str(item["unit"]),
                        factor=float(item.get("factor", 1.0)),
                        assumptions=tuple(str(note) for note in item.get("assumptions", [])),
                        context_tags=tuple(str(tag).lower() for tag in item.get("context_tags", [])),
                        inputs=dict(item.get("inputs", {})),
                    )
                    for item in derive_payload
                ),
            )
        )

    return RuleRegistry(rules)
