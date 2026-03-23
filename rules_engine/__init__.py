"""
Deterministic rule engine for derived construction takeoffs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.schemas import QuantityTakeoff
from .registry import RuleDefinition, RuleMatchCriteria, RuleRegistry, load_rule_registry


class RulesEngine:
    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self.registry = registry or RuleRegistry()

    def register_rule(self, rule: RuleDefinition) -> None:
        self.registry.rules.append(rule)

    def apply(self, takeoffs: Iterable[QuantityTakeoff]) -> list[QuantityTakeoff]:
        expanded: list[QuantityTakeoff] = []
        seen_keys: set[str] = set()

        for takeoff in takeoffs:
            if takeoff.item_key not in seen_keys:
                expanded.append(takeoff)
                seen_keys.add(takeoff.item_key)

            for derived in self.registry.derive_takeoffs(takeoff):
                if derived.item_key in seen_keys:
                    continue
                expanded.append(derived)
                seen_keys.add(derived.item_key)

        return expanded


def default_rules_engine(config_path: str | Path | None = None) -> RulesEngine:
    return RulesEngine(load_rule_registry(config_path))


__all__ = [
    "RuleDefinition",
    "RuleMatchCriteria",
    "RuleRegistry",
    "RulesEngine",
    "default_rules_engine",
    "load_rule_registry",
]
