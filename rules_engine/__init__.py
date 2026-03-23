"""
Minimal rules engine scaffold.

The engine can expand a deterministic takeoff into derived items when explicit
rules exist. The default registry is intentionally conservative.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable

from core.schemas import QuantityTakeoff

RuleHandler = Callable[[QuantityTakeoff], list[QuantityTakeoff]]


class RulesEngine:
    def __init__(self, handlers: Iterable[RuleHandler] | None = None) -> None:
        self._handlers = list(handlers or [])

    def register(self, handler: RuleHandler) -> None:
        self._handlers.append(handler)

    def apply(self, takeoffs: Iterable[QuantityTakeoff]) -> list[QuantityTakeoff]:
        expanded: list[QuantityTakeoff] = []
        for takeoff in takeoffs:
            expanded.append(takeoff)
            for handler in self._handlers:
                expanded.extend(handler(takeoff))
        return expanded


def explicit_derivation_rule(takeoff: QuantityTakeoff) -> list[QuantityTakeoff]:
    """
    Expand a takeoff only when explicit derivation metadata is present.

    Example:
        takeoff.trace["derive"] = [
            {"suffix": "finish", "factor": 2.0, "unit": "m2", "label": "wall_finish"}
        ]

    TODO: Replace this metadata-driven scaffold with first-class domain rules
    once finish systems, openings and assembly logic are formally modeled.
    """
    derivations = takeoff.trace.metadata.get("derive", [])
    if not isinstance(derivations, list):
        return []

    expanded: list[QuantityTakeoff] = []
    for derivation in derivations:
        factor = float(derivation.get("factor", 1.0))
        suffix = str(derivation.get("suffix", "derived"))
        unit = str(derivation.get("unit", takeoff.unit))
        label = str(derivation.get("label", suffix))
        expanded.append(
            replace(
                takeoff,
                item_key=f"{takeoff.item_key}:{suffix}",
                quantity=takeoff.quantity * factor,
                unit=unit,
                formula=f"{takeoff.formula} * {factor}".strip(),
                trace=replace(
                    takeoff.trace,
                    metadata={
                        **takeoff.trace.metadata,
                        "derived_from": takeoff.item_key,
                        "derived_label": label,
                    },
                ),
            )
        )
    return expanded


def default_rules_engine() -> RulesEngine:
    return RulesEngine([explicit_derivation_rule])
