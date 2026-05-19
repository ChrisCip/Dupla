"""Generate human-readable memory digests from clash feedback."""

from __future__ import annotations

from pathlib import Path
import re

from coordination.learning.feedback_store import load_all, load_for_project
from coordination.learning.pattern_learner import PatternStats, load_patterns


def build_patterns_catalog(feedback_path: Path, out_path: Path) -> None:
    """Build a markdown catalog with learned pattern statistics."""
    patterns = load_patterns(feedback_path)
    rows = sorted(patterns.values(), key=lambda item: (-item.total, -item.fp_rate, item.layer_pair))
    lines = [
        "# Catalogo de Patrones de Clashes",
        "",
        "| layer_pair | discipline_pair | project_type | total | real | false_positive | marginal | fp_rate | learned_confidence |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in rows:
        lines.append(
            "| "
            f"{item.layer_pair} | "
            f"{item.discipline_pair} | "
            f"{item.project_type} | "
            f"{item.total} | "
            f"{item.real_clash_count} | "
            f"{item.false_positive_count} | "
            f"{item.marginal_count} | "
            f"{item.fp_rate:.3f} | "
            f"{item.learned_confidence} |"
        )
    if not rows:
        lines.append("| - | - | - | 0 | 0 | 0 | 0 | 0.000 | medium |")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_project_profile(feedback_path: Path, project_name: str, out_path: Path) -> None:
    """Build one project-specific markdown memory profile."""
    project_feedback = load_for_project(feedback_path, project_name)
    grouped: dict[tuple[str, str], PatternStats] = {}
    for feedback in project_feedback:
        key = (feedback.layer_pair, feedback.discipline_pair)
        stats = grouped.get(key)
        if stats is None:
            stats = PatternStats(
                layer_pair=feedback.layer_pair,
                discipline_pair=feedback.discipline_pair,
                project_type=(feedback.project_type or "generic"),
            )
            grouped[key] = stats
        stats.total += 1
        if feedback.human_label == "REAL_CLASH":
            stats.real_clash_count += 1
        elif feedback.human_label == "FALSE_POSITIVE":
            stats.false_positive_count += 1
        elif feedback.human_label == "MARGINAL":
            stats.marginal_count += 1

    runs = sorted({item.run_label for item in project_feedback})
    lines = [
        f"# Perfil de Memoria - {project_name}",
        "",
        f"- feedback_total: {len(project_feedback)}",
        f"- runs_observados: {', '.join(runs) if runs else 'ninguno'}",
        "",
        "## Patrones por layer y disciplina",
        "| layer_pair | discipline_pair | total | real | false_positive | marginal | fp_rate | confidence |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    ordered = sorted(grouped.values(), key=lambda item: (-item.total, item.layer_pair, item.discipline_pair))
    for item in ordered:
        lines.append(
            "| "
            f"{item.layer_pair} | "
            f"{item.discipline_pair} | "
            f"{item.total} | "
            f"{item.real_clash_count} | "
            f"{item.false_positive_count} | "
            f"{item.marginal_count} | "
            f"{item.fp_rate:.3f} | "
            f"{item.learned_confidence} |"
        )
    if not ordered:
        lines.append("| - | - | 0 | 0 | 0 | 0 | 0.000 | medium |")

    lines.extend(["", "## Lectura rapida", "- Ruido historico:"])
    noisy = [item for item in ordered if item.fp_rate >= 0.7]
    if noisy:
        for item in noisy[:8]:
            lines.append(f"- `{item.layer_pair}` ({item.discipline_pair}) -> {item.fp_rate:.0%} false_positive")
    else:
        lines.append("- Sin patrones de ruido dominante aun.")

    lines.append("- Patrones confiables:")
    strong = [item for item in ordered if item.fp_rate <= 0.3 and item.total >= 1]
    if strong:
        for item in strong[:8]:
            lines.append(f"- `{item.layer_pair}` ({item.discipline_pair}) -> {item.real_clash_count}/{item.total} reales")
    else:
        lines.append("- Aun no hay patrones fuertes.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_all_project_profiles(feedback_path: Path, output_dir: Path) -> list[Path]:
    """Build profiles for every project present in feedback log."""
    records = load_all(feedback_path)
    projects = sorted({record.project_name for record in records if record.project_name.strip()})
    written: list[Path] = []
    for project in projects:
        target = output_dir / f"{slugify(project)}.md"
        build_project_profile(feedback_path, project, target)
        written.append(target)
    return written


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "project"

