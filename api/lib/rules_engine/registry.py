"""
Config-backed rule registry for deterministic takeoff expansion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from core.schemas import QuantityTakeoff, QuantityTrace

DEFAULT_RULES_PATH = Path(__file__).with_name("default_rules.json")
SUPPORTED_STRATEGIES = {
    "surface_multiplier",
    "identity",
    "count_multiplier",
    "conditional_faces",
}


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
    return {tag.lower() for tag in tags if tag}


def _inherited_context_tags(takeoff: QuantityTakeoff) -> list[str]:
    return _dedupe(
        [
            *_coerce_tags(takeoff.inputs.get("context_tags")),
            *_coerce_tags(takeoff.trace.metadata.get("context_tags")),
        ]
    )


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _strategy_payload(
    takeoff: QuantityTakeoff,
    rule: "RuleDefinition",
    derivative: "DerivedTakeoffRule",
) -> tuple[float, str, dict[str, Any], dict[str, Any], list[str]]:
    strategy = rule.strategy
    factor = derivative.factor
    assumptions: list[str] = []
    metadata: dict[str, Any] = {}
    inputs: dict[str, Any] = {}

    if strategy == "identity":
        quantity = takeoff.quantity * factor
        formula = (
            f"{takeoff.item_key}.quantity"
            if factor == 1.0
            else f"{takeoff.item_key}.quantity * {factor:g}"
        )
        return quantity, formula, metadata, inputs, assumptions

    if strategy in {"surface_multiplier", "count_multiplier"}:
        quantity = takeoff.quantity * factor
        formula = f"{takeoff.item_key}.quantity * {factor:g}"
        return quantity, formula, metadata, inputs, assumptions

    if strategy == "conditional_faces":
        derivative_inputs = derivative.inputs or {}
        default_faces = _coerce_int(derivative_inputs.get("default_faces"), default=1)
        faces_by_tag_payload = derivative_inputs.get("faces_by_tag", {})
        faces_by_tag: dict[str, int] = {}
        if isinstance(faces_by_tag_payload, Mapping):
            faces_by_tag = {
                str(tag).lower(): _coerce_int(value, default=default_faces)
                for tag, value in faces_by_tag_payload.items()
            }

        takeoff_tags = _takeoff_context_tags(takeoff)
        selector_tag: str | None = None
        resolved_faces = default_faces
        for tag, faces in faces_by_tag.items():
            if tag in takeoff_tags:
                selector_tag = tag
                resolved_faces = faces
                break

        if selector_tag is None:
            assumptions.append(
                f"Rule {rule.rule_id} used default_faces={default_faces} because no matching face-selection tag was present."
            )

        quantity = takeoff.quantity * factor * resolved_faces
        formula = f"{takeoff.item_key}.quantity * {factor:g} * faces({resolved_faces})"
        metadata = {
            "resolved_faces": resolved_faces,
            "default_faces": default_faces,
            "faces_by_tag": faces_by_tag,
            "face_selector_tag": selector_tag,
        }
        inputs = {
            "resolved_faces": resolved_faces,
            "face_selector_tag": selector_tag,
        }
        return quantity, formula, metadata, inputs, assumptions

    raise ValueError(f"Unsupported rule strategy '{strategy}'.")


@dataclass(frozen=True)
class RuleMatchCriteria:
    item_types: tuple[str, ...]
    material_hints: tuple[str, ...] = ()
    context_tags: tuple[str, ...] = ()
    exclude_tags: tuple[str, ...] = ()

    def matches(self, takeoff: QuantityTakeoff) -> bool:
        if self.item_types and takeoff.item_type not in self.item_types:
            return False

        material_hint = _takeoff_material_hint(takeoff)
        if self.material_hints and material_hint not in self.material_hints:
            return False

        takeoff_tags = _takeoff_context_tags(takeoff)
        if self.context_tags and not set(self.context_tags).issubset(takeoff_tags):
            return False

        if self.exclude_tags and set(self.exclude_tags).intersection(takeoff_tags):
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
    priority: int = 0
    override_rule_ids: tuple[str, ...] = ()
    strategy: str = "surface_multiplier"

    def __post_init__(self) -> None:
        if self.strategy not in SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported rule strategy '{self.strategy}'. Expected one of: {', '.join(sorted(SUPPORTED_STRATEGIES))}."
            )


class RuleRegistry:
    def __init__(self, rules: Iterable[RuleDefinition] | None = None) -> None:
        self.rules = list(rules or [])

    def matching_rules(self, takeoff: QuantityTakeoff) -> list[RuleDefinition]:
        matched = [rule for rule in self.rules if rule.match.matches(takeoff)]
        return sorted(matched, key=lambda rule: (-rule.priority, rule.rule_id))

    def resolved_rules(self, takeoff: QuantityTakeoff) -> list[RuleDefinition]:
        matched = self.matching_rules(takeoff)
        suppressed_rule_ids = {
            override_rule_id
            for rule in matched
            for override_rule_id in rule.override_rule_ids
            if override_rule_id
        }
        return [rule for rule in matched if rule.rule_id not in suppressed_rule_ids]

    def derive_takeoffs(self, takeoff: QuantityTakeoff) -> list[QuantityTakeoff]:
        derived: list[QuantityTakeoff] = []
        seen_signatures: set[tuple[str, str, str]] = set()
        for rule in self.resolved_rules(takeoff):
            for derivative in rule.derive:
                candidate = _build_derived_takeoff(takeoff, rule, derivative)
                signature = (takeoff.item_key, candidate.item_type, candidate.unit)
                if signature in seen_signatures:
                    continue
                derived.append(candidate)
                seen_signatures.add(signature)
        return derived


def _build_derived_takeoff(
    takeoff: QuantityTakeoff,
    rule: RuleDefinition,
    derivative: DerivedTakeoffRule,
) -> QuantityTakeoff:
    inherited_context_tags = _inherited_context_tags(takeoff)
    context_tags = _dedupe([*inherited_context_tags, *derivative.context_tags])
    quantity, formula, strategy_metadata, strategy_inputs, strategy_assumptions = _strategy_payload(
        takeoff,
        rule,
        derivative,
    )
    assumptions = _dedupe(
        [
            *takeoff.assumptions,
            *derivative.assumptions,
            *strategy_assumptions,
        ]
    )
    trace = QuantityTrace(
        source_entity_ids=list(takeoff.trace.source_entity_ids),
        source_entity_sources=list(takeoff.trace.source_entity_sources),
        steps=[
            *takeoff.trace.steps,
            f"Expanded via rule {rule.rule_id}:{derivative.suffix} using strategy {rule.strategy}.",
        ],
        evidence=list(takeoff.trace.evidence),
        conflict_notes=list(takeoff.trace.conflict_notes),
        metadata={
            **takeoff.trace.metadata,
            "derived_from": takeoff.item_key,
            "derivation_rule_id": rule.rule_id,
            "derivation_strategy": rule.strategy,
            "derivation_suffix": derivative.suffix,
            "derivation_factor": derivative.factor,
            "derivation_formula": formula,
            "priority": rule.priority,
            "override_rule_ids": list(rule.override_rule_ids),
            "inherited_context_tags": inherited_context_tags,
            "context_tags": context_tags,
            **strategy_metadata,
        },
    )
    return QuantityTakeoff(
        item_key=f"{takeoff.item_key}:{rule.rule_id}:{derivative.suffix}",
        item_type=derivative.item_type,
        level_id=takeoff.level_id,
        unit=derivative.unit,
        quantity=quantity,
        formula=formula,
        inputs={
            **takeoff.inputs,
            **derivative.inputs,
            **strategy_inputs,
            "base_quantity": takeoff.quantity,
            "base_unit": takeoff.unit,
            "base_item_type": takeoff.item_type,
            "derived_from": takeoff.item_key,
            "derivation_rule_id": rule.rule_id,
            "derivation_strategy": rule.strategy,
            "derivation_factor": derivative.factor,
            "priority": rule.priority,
            "inherited_context_tags": inherited_context_tags,
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
                priority=_coerce_int(rule_payload.get("priority"), default=0),
                override_rule_ids=tuple(
                    str(item) for item in rule_payload.get("override_rule_ids", [])
                ),
                strategy=str(rule_payload.get("strategy", "surface_multiplier")),
                match=RuleMatchCriteria(
                    item_types=tuple(str(item) for item in match_payload.get("item_types", [])),
                    material_hints=tuple(
                        str(item).lower() for item in match_payload.get("material_hints", [])
                    ),
                    context_tags=tuple(
                        str(item).lower() for item in match_payload.get("context_tags", [])
                    ),
                    exclude_tags=tuple(
                        str(item).lower() for item in match_payload.get("exclude_tags", [])
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
