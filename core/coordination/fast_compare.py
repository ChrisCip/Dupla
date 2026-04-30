"""Helpers for fast, low-noise clash comparison runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from core.coordination.level_inference import LevelResolution, infer_level_from_view_name
from core.coordination.models_25d import Discipline, Element25D
from core.coordination.nasas_paths import coordination_issue_key, discipline_from_nasas_relative_path
from core.coordination.registry import ProjectLevelRegistryDocument
from core.coordination.source_selection import normalize_source_text, relative_posix

FAST_COMPARE_ANALYSIS_PROFILE = "fast_compare"
FAST_COMPARE_DISCIPLINES = (Discipline.ARCH, Discipline.STRUC)
FAST_COMPARE_LEVEL_THICKNESS_MM = {
    "CIMENTACION": 800.0,
    "SOTANO": 400.0,
    "NPT_P1": 300.0,
    "NPT_P2": 300.0,
    "TECHO": 400.0,
}
FAST_COMPARE_DEFAULT_THICKNESS_MM = 300.0
FAST_COMPARE_Z_CLAMP_MM = 2000.0
CAD_SUFFIXES = {".dwg", ".dxf"}


@dataclass(frozen=True)
class SourceCandidate:
    path: Path
    rel_path: str
    issue_key: str
    discipline: Discipline
    suffix: str
    level_id: str
    level_source: str
    cohort_id: str | None = None


@dataclass(frozen=True)
class CohortManifest:
    cohort_name: str
    source_files: frozenset[str]


@dataclass(frozen=True)
class AlignmentOverride:
    source_file: str
    translate_mm: tuple[float, float]
    level_id: str | None = None
    level_source: str | None = None
    note: str | None = None


def parse_include_disciplines(raw: str | None) -> tuple[Discipline, ...]:
    if not raw or not raw.strip():
        return FAST_COMPARE_DISCIPLINES
    out: list[Discipline] = []
    for token in raw.split(","):
        value = token.strip().upper()
        if not value:
            continue
        matched = next(
            (
                discipline
                for discipline in Discipline
                if value in {discipline.name.upper(), discipline.value.upper()}
            ),
            None,
        )
        if matched is None:
            raise ValueError(f"Disciplina no soportada en --include-disciplines: {token!r}")
        if matched not in out:
            out.append(matched)
    if not out:
        raise ValueError("--include-disciplines no produjo disciplinas validas")
    return tuple(out)


def build_source_candidates(
    media: Iterable[Path],
    *,
    root: Path,
    doc: ProjectLevelRegistryDocument,
    default_level_id: str,
) -> list[SourceCandidate]:
    candidates: list[SourceCandidate] = []
    for path in media:
        rel = relative_posix(path, root)
        view_text = "\n".join(part for part in (path.stem, path.name, rel, path.parent.name) if part)
        level_resolution = infer_level_from_view_name(
            view_text,
            doc=doc,
            default_level_id=default_level_id,
        )
        candidates.append(
            SourceCandidate(
                path=path,
                rel_path=rel,
                issue_key=coordination_issue_key(path, root),
                discipline=discipline_from_nasas_relative_path(rel.lower()),
                suffix=path.suffix.lower(),
                level_id=level_resolution.level_id,
                level_source=level_resolution.source,
            )
        )
    return candidates


def load_cohort_manifest(path: Path, *, root: Path) -> CohortManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    source_files = payload.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        raise ValueError("cohort manifest requiere source_files no vacio")
    normalized: set[str] = set()
    for raw in source_files:
        if not isinstance(raw, str) or not raw.strip():
            continue
        file_path = Path(raw)
        rel = relative_posix(file_path if file_path.is_absolute() else root / file_path, root)
        normalized.add(normalize_source_text(rel))
    if not normalized:
        raise ValueError("cohort manifest no contiene source_files validos")
    cohort_name = str(payload.get("cohort_name") or payload.get("name") or path.stem)
    return CohortManifest(cohort_name=cohort_name, source_files=frozenset(normalized))


def load_alignment_manifest(path: Path, *, root: Path) -> dict[str, AlignmentOverride]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("alignment manifest requiere entries no vacio")

    overrides: dict[str, AlignmentOverride] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_source = entry.get("source_file")
        translate_mm = entry.get("translate_mm")
        level_id = entry.get("level_id")
        level_source = entry.get("level_source")
        if not isinstance(raw_source, str) or not raw_source.strip():
            continue
        if (
            not isinstance(translate_mm, list)
            or len(translate_mm) != 2
            or any(not isinstance(value, (int, float)) for value in translate_mm)
        ):
            raise ValueError("alignment manifest requiere translate_mm=[dx,dy] por entry")
        file_path = Path(raw_source)
        rel = relative_posix(file_path if file_path.is_absolute() else root / file_path, root)
        key = normalize_source_text(rel)
        overrides[key] = AlignmentOverride(
            source_file=rel,
            translate_mm=(float(translate_mm[0]), float(translate_mm[1])),
            level_id=str(level_id).strip() if isinstance(level_id, str) and level_id.strip() else None,
            level_source=(
                str(level_source).strip()
                if isinstance(level_source, str) and level_source.strip()
                else (
                    f"manual_manifest:{str(level_id).strip()}"
                    if isinstance(level_id, str) and level_id.strip()
                    else None
                )
            ),
            note=str(entry.get("note")) if entry.get("note") else None,
        )
    if not overrides:
        raise ValueError("alignment manifest no contiene entries validos")
    return overrides


def apply_manifest_selection(
    candidates: Iterable[SourceCandidate],
    *,
    manifest: CohortManifest,
) -> list[SourceCandidate]:
    selected: list[SourceCandidate] = []
    for candidate in candidates:
        if normalize_source_text(candidate.rel_path) not in manifest.source_files:
            continue
        selected.append(
            SourceCandidate(
                path=candidate.path,
                rel_path=candidate.rel_path,
                issue_key=candidate.issue_key,
                discipline=candidate.discipline,
                suffix=candidate.suffix,
                level_id=candidate.level_id,
                level_source=candidate.level_source,
                cohort_id=manifest.cohort_name,
            )
        )
    return selected


def compute_readiness_payload(
    candidates: Iterable[SourceCandidate],
    *,
    required_disciplines: tuple[Discipline, ...],
) -> dict[str, object]:
    candidates = list(candidates)
    groups: dict[str, list[SourceCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.issue_key, []).append(candidate)

    cohorts: list[dict[str, object]] = []
    comparable_issue_keys: list[str] = []
    availability = _discipline_issue_availability(groups)
    for issue_key, group in sorted(groups.items()):
        files_by_discipline: dict[str, list[str]] = {}
        levels_by_discipline: dict[str, list[str]] = {}
        for discipline in required_disciplines:
            members = [candidate for candidate in group if candidate.discipline == discipline]
            if members:
                files_by_discipline[discipline.value] = sorted(candidate.rel_path for candidate in members)
                levels_by_discipline[discipline.value] = sorted({candidate.level_id for candidate in members})
        missing = [discipline.value for discipline in required_disciplines if discipline.value not in files_by_discipline]
        shared_levels = _shared_levels(levels_by_discipline, required_disciplines)
        comparable = not missing and bool(shared_levels)
        if comparable:
            comparable_issue_keys.append(issue_key)
        nearest_candidates = {
            discipline: _nearest_issue_candidate(issue_key, availability.get(discipline, []))
            for discipline in missing
        }
        cohorts.append(
            {
                "issue_key": issue_key,
                "available_disciplines": sorted(files_by_discipline),
                "missing_disciplines": missing,
                "files_by_discipline": files_by_discipline,
                "levels_by_discipline": levels_by_discipline,
                "shared_levels": shared_levels,
                "is_comparable": comparable,
                "nearest_candidates": nearest_candidates,
            }
        )

    return {
        "required_disciplines": [discipline.value for discipline in required_disciplines],
        "candidate_count": len(candidates),
        "comparable_issue_keys": comparable_issue_keys,
        "cohorts": cohorts,
    }


def select_comparable_candidates(
    candidates: Iterable[SourceCandidate],
    *,
    comparable_issue_keys: Iterable[str],
) -> list[SourceCandidate]:
    allowed = set(comparable_issue_keys)
    out: list[SourceCandidate] = []
    for candidate in candidates:
        if candidate.issue_key not in allowed:
            continue
        out.append(
            SourceCandidate(
                path=candidate.path,
                rel_path=candidate.rel_path,
                issue_key=candidate.issue_key,
                discipline=candidate.discipline,
                suffix=candidate.suffix,
                level_id=candidate.level_id,
                level_source=candidate.level_source,
                cohort_id=candidate.issue_key,
            )
        )
    return out


def suppress_visual_backups(candidates: Iterable[SourceCandidate]) -> list[SourceCandidate]:
    cad_keys = {
        (candidate.cohort_id or candidate.issue_key, candidate.discipline, candidate.level_id)
        for candidate in candidates
        if candidate.suffix in CAD_SUFFIXES
    }
    selected: list[SourceCandidate] = []
    for candidate in candidates:
        if candidate.suffix == ".pdf" and (
            candidate.cohort_id or candidate.issue_key,
            candidate.discipline,
            candidate.level_id,
        ) in cad_keys:
            continue
        selected.append(candidate)
    return selected


def normalize_fast_compare_element(
    element: Element25D,
    *,
    file_level_id: str,
    cohort_id: str,
    level_source: str,
) -> Element25D:
    metadata = dict(element.metadata)
    metadata["file_level_id"] = file_level_id
    metadata["cohort_id"] = cohort_id
    metadata.setdefault("geometry_role", "primary")
    if metadata["geometry_role"] != "primary":
        metadata.setdefault("suppression_reason", "non_primary_geometry")

    z_data = element.z_data
    clamp = abs(z_data.z_ref_raw_mm) > FAST_COMPARE_Z_CLAMP_MM or z_data.thickness_mm > FAST_COMPARE_Z_CLAMP_MM
    if clamp:
        z_data = z_data.model_copy(
            update={
                "level_id": file_level_id,
                "z_ref_raw_mm": 0.0,
                "thickness_mm": FAST_COMPARE_LEVEL_THICKNESS_MM.get(
                    file_level_id,
                    FAST_COMPARE_DEFAULT_THICKNESS_MM,
                ),
                "reference_point": "bottom",
            }
        )
        metadata["level_assignment_source"] = "clamped_2d_default"
    else:
        metadata["level_assignment_source"] = level_source

    return element.model_copy(update={"z_data": z_data, "metadata": metadata})


def render_readiness_markdown(
    payload: dict[str, object],
    *,
    project_name: str,
    root: Path,
) -> str:
    lines = [
        f"# Comparison Readiness Report - {project_name or 'Proyecto'}",
        "",
        f"- Root: `{root.as_posix()}`",
        f"- Required disciplines: {', '.join(payload['required_disciplines'])}",
        f"- Candidate files: {payload['candidate_count']}",
        f"- Comparable issue keys: {len(payload['comparable_issue_keys'])}",
        "",
        "## Cohorts",
    ]
    for cohort in payload["cohorts"]:
        issue_key = cohort["issue_key"]
        comparable = "yes" if cohort["is_comparable"] else "no"
        lines.append(f"- `{issue_key}` comparable: {comparable}")
        lines.append(f"  disciplines: {', '.join(cohort['available_disciplines']) or 'none'}")
        lines.append(f"  shared levels: {', '.join(cohort['shared_levels']) or 'none'}")
        if cohort["missing_disciplines"]:
            lines.append(f"  missing: {', '.join(cohort['missing_disciplines'])}")
        nearest = cohort["nearest_candidates"]
        for discipline, candidate in sorted(nearest.items()):
            if candidate:
                lines.append(f"  nearest {discipline}: {candidate}")
    lines.append("")
    return "\n".join(lines)


def primary_geometry_role(element: Element25D) -> bool:
    return str(element.metadata.get("geometry_role") or "primary") == "primary"


def _shared_levels(
    levels_by_discipline: dict[str, list[str]],
    required_disciplines: tuple[Discipline, ...],
) -> list[str]:
    shared: set[str] | None = None
    for discipline in required_disciplines:
        levels = set(levels_by_discipline.get(discipline.value, []))
        if not levels:
            return []
        shared = levels if shared is None else shared & levels
    return sorted(shared or [])


def _discipline_issue_availability(
    groups: dict[str, list[SourceCandidate]],
) -> dict[str, list[tuple[str, date | None]]]:
    availability: dict[str, list[tuple[str, date | None]]] = {}
    for issue_key, group in groups.items():
        issue_date = _parse_issue_date(issue_key)
        for discipline in {candidate.discipline.value for candidate in group}:
            availability.setdefault(discipline, []).append((issue_key, issue_date))
    return availability


def _nearest_issue_candidate(
    current_issue_key: str,
    options: list[tuple[str, date | None]],
) -> str | None:
    if not options:
        return None
    current_date = _parse_issue_date(current_issue_key)
    if current_date is not None:
        dated = [item for item in options if item[1] is not None]
        if dated:
            best = min(dated, key=lambda item: (abs((item[1] - current_date).days), item[0]))
            return best[0]
    return sorted(item[0] for item in options)[0]


def _parse_issue_date(issue_key: str) -> date | None:
    if not issue_key.startswith("d:") or len(issue_key) != 10:
        return None
    try:
        return date(
            int(issue_key[2:6]),
            int(issue_key[6:8]),
            int(issue_key[8:10]),
        )
    except ValueError:
        return None
