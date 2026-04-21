"""
Canonical discipline keys ↔ chapter codes (Dupla composer) ↔ heurísticas de comparación.

Las claves coinciden con `discipline` en `inputs/projects/*.yaml`.
Los prefijos de capítulo alinean con `budget.chapter_rules.chapter_path_for_takeoff`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Claves estables para YAML, visión y few-shot
STRUCTURAL: Final = "structural"
ELECTRICAL: Final = "electrical"
FINISHES_ARCH: Final = "finishes_architectural"
SANITARY: Final = "sanitary"
GENERAL: Final = "general"

DISCIPLINE_KEYS: Final[tuple[str, ...]] = (
    STRUCTURAL,
    ELECTRICAL,
    FINISHES_ARCH,
    SANITARY,
    GENERAL,
)


@dataclass(frozen=True)
class SuccessMetricThresholds:
    """Umbrales orientativos para decidir si especializar visión/prompts."""

    min_code_coverage_pct: float = 35.0
    min_qty_accuracy_pct: float = 50.0
    max_total_amount_rel_error: float = 0.35


@dataclass(frozen=True)
class DisciplineChapterMap:
    """Prefijos de código de capítulo (segment.code) por disciplina de negocio."""

    chapter_code_prefixes: tuple[str, ...]
    compare_heuristic_tags: tuple[str, ...]


# Prefijos "01", "01.01"… son los `ChapterSegment.code` del composer.
MAPPING: Final[dict[str, DisciplineChapterMap]] = {
    STRUCTURAL: DisciplineChapterMap(
        chapter_code_prefixes=("01", "01.01", "01.02", "01.03", "01.04", "02", "02.01"),
        compare_heuristic_tags=(
            "hormigon_armado",
            "acero_refuerzo",
            "muros_divisiones",
            "movimiento_tierra",
            "preliminares",
        ),
    ),
    ELECTRICAL: DisciplineChapterMap(
        chapter_code_prefixes=("08", "08.01"),
        compare_heuristic_tags=("electrico", "equipos_electricos"),
    ),
    SANITARY: DisciplineChapterMap(
        chapter_code_prefixes=("08", "08.02", "04", "04.01"),
        compare_heuristic_tags=("sanitario", "impermeabilizacion"),
    ),
    FINISHES_ARCH: DisciplineChapterMap(
        chapter_code_prefixes=(
            "05",
            "05.01",
            "05.02",
            "05.03",
            "05.04",
            "05.05",
            "05.06",
            "06",
            "06.01",
            "06.02",
            "03",
        ),
        compare_heuristic_tags=(
            "panete_revestimiento",
            "pisos",
            "escaleras",
            "puertas",
            "ventanas",
            "ebanisteria",
            "pintura",
            "techos_cubierta",
            "acabados",
            "herreria",
            "miscelaneos",
        ),
    ),
    GENERAL: DisciplineChapterMap(
        chapter_code_prefixes=("07", "07.01", "09", "99", "99.01"),
        compare_heuristic_tags=("gastos_generales", "miscelaneos", "preliminares"),
    ),
}


def normalize_discipline_key(value: str | None) -> str:
    if not value:
        return GENERAL
    v = value.strip().lower().replace("-", "_")
    aliases = {
        "terminaciones": FINISHES_ARCH,
        "arquitectonico": FINISHES_ARCH,
        "arquitectónico": FINISHES_ARCH,
        "terminaciones_arquitectonico": FINISHES_ARCH,
        "estructura": STRUCTURAL,
        "estructural": STRUCTURAL,
        "electrica": ELECTRICAL,
        "electric": ELECTRICAL,
        "sanitarias": SANITARY,
        "plomeria": SANITARY,
    }
    if v in DISCIPLINE_KEYS:
        return v
    return aliases.get(v, GENERAL)


def chapter_prefixes_for(discipline_key: str) -> tuple[str, ...]:
    key = normalize_discipline_key(discipline_key)
    return MAPPING.get(key, MAPPING[GENERAL]).chapter_code_prefixes


def compare_tags_for(discipline_key: str) -> tuple[str, ...]:
    key = normalize_discipline_key(discipline_key)
    return MAPPING.get(key, MAPPING[GENERAL]).compare_heuristic_tags


def canonical_discipline_for_summary(summary: str) -> str:
    """
    Clasificación liviana por texto del resumen (partida PRES / generado).
    Prioridad: estructura → instalaciones (eléctrico antes que sanitario por keywords) → terminaciones.
    """
    n = (summary or "").lower()
    if any(
        x in n
        for x in (
            "hormigon",
            "hormigón",
            "viga",
            "columna",
            "losa",
            "zapata",
            "platea",
            "encofrad",
            "acero",
            "refuerzo",
        )
    ):
        return STRUCTURAL
    if any(x in n for x in ("electrico", "eléctrico", "luminaria", "tomacorr", "interruptor", "panel")):
        return ELECTRICAL
    if any(x in n for x in ("sanitario", "inodoro", "lavamanos", "plomer", "drenaje", "desague", "desagüe")):
        return SANITARY
    if any(
        x in n
        for x in (
            "pañete",
            "panete",
            "porcelanato",
            "ceramica",
            "cerámica",
            "piso",
            "puerta",
            "ventana",
            "pintura",
            "techo",
            "cielo",
            "terminacion",
            "terminación",
            "acabado",
            "closet",
            "ebanister",
        )
    ):
        return FINISHES_ARCH
    return GENERAL
