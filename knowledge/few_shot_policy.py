"""
Few-shot a partir de PRES: corpus compartido + filtrado por disciplina canónica.

Reutiliza `TrainingPair` y heurísticas de `training_data`; no duplica extracción XLSX.
"""

from __future__ import annotations

from budget.discipline_mapping import (
    ELECTRICAL,
    FINISHES_ARCH,
    GENERAL,
    SANITARY,
    STRUCTURAL,
    canonical_discipline_for_summary,
    normalize_discipline_key,
)
from knowledge.training_data import TrainingPair, generate_few_shot_examples


def training_pairs_for_discipline(
    pairs: list[TrainingPair],
    discipline_key: str | None,
    *,
    max_pairs: int = 400,
) -> list[TrainingPair]:
    """
    Filtra pares cuya descripción o contexto encajan en la disciplina canónica.
    Si `discipline_key` es None o GENERAL, devuelve el corpus completo (acotado).
    """
    key = normalize_discipline_key(discipline_key or GENERAL)
    if key == GENERAL:
        return pairs[:max_pairs]

    out: list[TrainingPair] = []
    for pair in pairs:
        bucket = canonical_discipline_for_summary(pair.output_description + " " + pair.input_context)
        if bucket == key:
            out.append(pair)
        if len(out) >= max_pairs:
            break

    return out if out else pairs[: min(80, len(pairs))]


def few_shot_for_discipline(
    pairs: list[TrainingPair],
    discipline_key: str | None,
    category: str = "muros",
) -> str:
    """Texto few-shot para prompts de matching, usando solo pares de esa disciplina cuando existan."""
    scoped = training_pairs_for_discipline(pairs, discipline_key)
    return generate_few_shot_examples(scoped, category)


def discipline_category_hints(discipline_key: str | None) -> str:
    """Sugerencia de categoría `generate_few_shot_examples` según disciplina."""
    key = normalize_discipline_key(discipline_key or GENERAL)
    return {
        STRUCTURAL: "hormigon",
        ELECTRICAL: "electrico",
        SANITARY: "sanitario",
        FINISHES_ARCH: "muros",
        GENERAL: "muros",
    }.get(key, "muros")
