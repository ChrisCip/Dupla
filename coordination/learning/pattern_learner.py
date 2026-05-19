"""Learning patterns from human clash feedback."""

from __future__ import annotations

from dataclasses import dataclass

from coordination.learning.feedback_store import load_all

_DISCIPLINE_TOKEN_ALIASES: dict[str, str] = {
    "DISCIPLINE.ARCH": "ARQUITECTURA",
    "DISCIPLINE.STRUC": "ESTRUCTURA",
    "ARCH": "ARQUITECTURA",
    "STRUC": "ESTRUCTURA",
    "ARQUITECTURA": "ARQUITECTURA",
    "ESTRUCTURA": "ESTRUCTURA",
}


@dataclass
class PatternStats:
    layer_pair: str
    discipline_pair: str
    project_type: str
    total: int = 0
    real_clash_count: int = 0
    false_positive_count: int = 0
    marginal_count: int = 0

    @property
    def fp_rate(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.false_positive_count / self.total

    @property
    def learned_confidence(self) -> str:
        if self.fp_rate > 0.7:
            return "low"
        if self.fp_rate < 0.3:
            return "high"
        return "medium"

    @property
    def pattern_label(self) -> str:
        fp_percent = round(self.fp_rate * 100)
        if self.learned_confidence == "low":
            return f"falso positivo frecuente ({fp_percent}% fp rate, {self.total} casos previos)"
        if self.learned_confidence == "high":
            return f"clash recurrente confiable ({fp_percent}% fp rate, {self.total} casos previos)"
        return f"patron mixto ({fp_percent}% fp rate, {self.total} casos previos)"


def load_patterns(path) -> dict[str, PatternStats]:
    """Aggregate feedback records into normalized pattern statistics."""
    feedback_rows = load_all(path)
    patterns: dict[str, PatternStats] = {}
    for feedback in feedback_rows:
        layer_pair = _normalize_pair(feedback.layer_pair)
        discipline_pair = _normalize_discipline_pair(feedback.discipline_pair)
        project_type = _normalize_project_type(feedback.project_type)
        key = _pattern_key(layer_pair, discipline_pair, project_type)
        stats = patterns.get(key)
        if stats is None:
            stats = PatternStats(
                layer_pair=layer_pair,
                discipline_pair=discipline_pair,
                project_type=project_type,
            )
            patterns[key] = stats
        stats.total += 1
        if feedback.human_label == "REAL_CLASH":
            stats.real_clash_count += 1
        elif feedback.human_label == "FALSE_POSITIVE":
            stats.false_positive_count += 1
        elif feedback.human_label == "MARGINAL":
            stats.marginal_count += 1
    return patterns


def override_confidence(
    card: dict,
    patterns: dict[str, PatternStats],
    *,
    project_type: str | None = None,
) -> dict:
    """Override card confidence when a known pattern exists."""
    if not patterns:
        card.setdefault("known_pattern_label", None)
        return card

    layer_pair = _normalize_pair(str(card.get("layer_pair") or ""))
    discipline_pair = _normalize_discipline_pair(str(card.get("discipline_pair") or ""))
    project_type_normalized = _normalize_project_type(project_type or card.get("project_type"))
    direct_key = _pattern_key(layer_pair, discipline_pair, project_type_normalized)
    fallback_key = _pattern_key(layer_pair, discipline_pair, "generic")
    stats = patterns.get(direct_key) or patterns.get(fallback_key)
    if stats is None:
        prefix = f"{layer_pair}|{discipline_pair}|"
        matches = [item for key, item in patterns.items() if key.startswith(prefix)]
        if matches:
            stats = max(matches, key=lambda item: item.total)
    if stats is None:
        card.setdefault("known_pattern_label", None)
        return card

    updated = dict(card)
    updated["report_confidence"] = stats.learned_confidence
    updated["known_pattern_label"] = stats.pattern_label
    return updated


def _pattern_key(layer_pair: str, discipline_pair: str, project_type: str) -> str:
    return f"{layer_pair}|{discipline_pair}|{project_type}"


def _normalize_pair(value: str) -> str:
    tokens = [token.strip().upper() for token in value.split("/") if token.strip()]
    return " / ".join(tokens)


def _normalize_discipline_pair(value: str) -> str:
    tokens: list[str] = []
    for token in value.split("/"):
        normalized = token.strip().upper()
        if not normalized:
            continue
        tokens.append(_DISCIPLINE_TOKEN_ALIASES.get(normalized, normalized))
    return " / ".join(tokens)


def _normalize_project_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized or "generic"

