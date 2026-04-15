"""
Auto-generate vision methodology context from PRES training pairs + BC3 catalog.

The output is a compact Spanish text block injected into the OpenAI vision prompt
so the model knows what level of detail and what disciplines/partidas are expected
*before* it looks at any plan image.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from knowledge.training_data import TrainingPair


def _discipline_summary(pairs: list[TrainingPair]) -> dict[str, list[TrainingPair]]:
    by_disc: dict[str, list[TrainingPair]] = defaultdict(list)
    for p in pairs:
        _, _, disc = p.input_context.partition("|")
        by_disc[disc.strip() or "General"].append(p)
    return dict(by_disc)


def _bc3_chapter_summary(bc3_catalog: dict[str, Any]) -> list[str]:
    chapters = bc3_catalog.get("chapters") or []
    lines: list[str] = []
    for ch in chapters[:30]:
        code = ch.get("code", "")
        summary = ch.get("summary", "")
        if summary:
            lines.append(f"  - {code}: {summary}")
    return lines


def _bc3_unit_distribution(bc3_catalog: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in bc3_catalog.get("items") or []:
        u = str(item.get("unit") or "").strip().lower()
        if u:
            counts[u] += 1
    return dict(counts.most_common(15))


def _pres_detail_examples(
    disc_pairs: dict[str, list[TrainingPair]],
    max_per_disc: int = 6,
) -> list[str]:
    lines: list[str] = []
    for disc, pairs in sorted(disc_pairs.items()):
        sample = pairs[:max_per_disc]
        descs = [p.output_description for p in sample]
        units = sorted({p.output_unit for p in sample if p.output_unit})
        lines.append(
            f"  {disc} ({len(pairs)} partidas, unidades: {', '.join(units) or '?'}):"
        )
        for d in descs:
            lines.append(f"    · {d}")
    return lines


def _level_names(pairs: list[TrainingPair]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for p in pairs:
        level, _, _ = p.input_context.partition("|")
        level = level.strip()
        if level and level not in seen:
            seen.add(level)
            names.append(level)
    return names[:20]


def generate_methodology_context(
    training_pairs: list[TrainingPair] | None = None,
    bc3_catalog: dict[str, Any] | None = None,
    *,
    max_chars: int = 10000,
) -> str:
    """
    Build a compact Spanish methodology block from existing project data.

    Returns empty string when no data is available.
    """
    sections: list[str] = []

    has_pres = bool(training_pairs)
    has_bc3 = bool(bc3_catalog and bc3_catalog.get("items"))

    if not has_pres and not has_bc3:
        return ""

    sections.append(
        "CONTEXTO AUTOMÁTICO (generado del PRES y BC3 del proyecto de referencia).\n"
        "Úsalo para entender el NIVEL DE DETALLE y las DISCIPLINAS que el presupuestista espera.\n"
        "NO copies cantidades de aquí — solo el criterio de desglose."
    )

    if has_pres and training_pairs:
        disc_map = _discipline_summary(training_pairs)
        levels = _level_names(training_pairs)

        type_counts: Counter[str] = Counter()
        unit_counts: Counter[str] = Counter()
        for p in training_pairs:
            type_counts[p.input_item_type] += 1
            if p.output_unit:
                unit_counts[p.output_unit.lower()] += 1

        sections.append(
            f"\n## PRESUPUESTO DE REFERENCIA (PRES) — {len(training_pairs)} partidas"
        )

        if levels:
            sections.append(f"Niveles: {', '.join(levels)}")

        sections.append(
            f"Disciplinas encontradas: {', '.join(sorted(disc_map.keys()))}"
        )

        sections.append(
            f"Tipos de partida: {', '.join(f'{t} ({c})' for t, c in type_counts.most_common(12))}"
        )

        sections.append(
            f"Unidades usadas: {', '.join(f'{u} ({c})' for u, c in unit_counts.most_common(10))}"
        )

        detail_lines = _pres_detail_examples(disc_map, max_per_disc=5)
        if detail_lines:
            sections.append("\nDesglose por disciplina (ejemplos reales de partidas):")
            sections.extend(detail_lines)

        sections.append(
            "\nREGLA: el nivel de desglose de arriba es lo MÍNIMO que debes extraer del plano. "
            "Si ves algo adicional (eléctrico, sanitario, escaleras, exteriores, etc.) también extráelo."
        )

    if has_bc3 and bc3_catalog:
        item_count = len(bc3_catalog.get("items") or [])
        chapter_lines = _bc3_chapter_summary(bc3_catalog)
        unit_dist = _bc3_unit_distribution(bc3_catalog)

        sections.append(
            f"\n## CATÁLOGO BC3 — {item_count} partidas disponibles"
        )

        if chapter_lines:
            sections.append("Capítulos del catálogo:")
            sections.extend(chapter_lines)

        if unit_dist:
            sections.append(
                f"Unidades en catálogo: {', '.join(f'{u} ({c})' for u, c in unit_dist.items())}"
            )

        sections.append(
            "REGLA: el catálogo cubre estas disciplinas. "
            "Extrae elementos que encajen en ellas para que el presupuesto pueda asignar códigos."
        )

    text = "\n".join(sections)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... contexto truncado por límite ...]"
    return text
