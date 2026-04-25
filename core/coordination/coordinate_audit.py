"""Coordinate and eligibility audit helpers for staged clash runs."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.coordination.fast_compare import primary_geometry_role
from core.coordination.models_25d import Element25D

AuditStatus = Literal["eligible", "needs_alignment", "annotation_noise", "bbox_only", "extract_failed"]


class SourceAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rel_path: str
    file_name: str
    suffix: str
    issue_key: str
    cohort_id: str
    discipline: str
    level_id: str
    level_source: str
    coordinate_band_key: tuple[int, int] | None = None
    coordinate_band: str | None = None
    centroid_mm: tuple[float, float] | None = None
    bounds_mm: tuple[float, float, float, float] | None = None
    units_to_mm_factor: float | None = None
    raw_entity_count: int = 0
    raw_primary_candidate_count: int = 0
    raw_annotation_count: int = 0
    raw_bbox_only_count: int = 0
    selected_total_count: int = 0
    selected_primary_count: int = 0
    dominant_entity_types: list[str] = Field(default_factory=list)
    audit_status: AuditStatus = "extract_failed"
    notes: list[str] = Field(default_factory=list)


class PairScheduleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    file_a: str
    file_b: str
    coordinate_band: str | None = None
    level_ids: tuple[str, str]
    scheduled: bool
    block_reason: str | None = None


def build_source_audit(
    candidate: Any,
    *,
    elements: list[Element25D] | None = None,
    accore_profile: dict[str, Any] | None = None,
    coordinate_band_cell_mm: float = 500_000.0,
    min_primary_elements: int = 20,
    max_annotation_ratio: float = 0.60,
) -> SourceAudit:
    elements = list(elements or [])
    selected_total = len(elements)
    selected_primary = sum(1 for element in elements if primary_geometry_role(element))
    bbox_like = sum(
        1 for element in elements if "bbox" in str(element.metadata.get("geometry_source") or "").lower()
    )
    bounds_mm, centroid_mm = _elements_bounds_and_centroid(elements)
    dominant_entity_types = _dominant_entity_types(elements)

    raw_entity_count = int(accore_profile.get("raw_entity_count") or 0) if accore_profile else 0
    raw_primary_candidate_count = (
        int(accore_profile.get("raw_primary_candidate_count") or 0) if accore_profile else selected_primary
    )
    raw_annotation_count = int(accore_profile.get("raw_annotation_count") or 0) if accore_profile else 0
    raw_bbox_only_count = int(accore_profile.get("raw_bbox_only_count") or 0) if accore_profile else bbox_like
    units_to_mm_factor = (
        float(accore_profile.get("units_to_mm_factor"))
        if accore_profile and accore_profile.get("units_to_mm_factor") is not None
        else None
    )
    if not dominant_entity_types and accore_profile:
        dominant_entity_types = [str(item) for item in accore_profile.get("dominant_entity_types") or []]

    if (
        (bounds_mm is None or centroid_mm is None)
        and accore_profile
        and accore_profile.get("dominant_cluster_bounds_mm")
        and accore_profile.get("dominant_cluster_centroid_mm")
    ):
        cluster_bounds = accore_profile["dominant_cluster_bounds_mm"]
        bounds_mm = (
            float(cluster_bounds[0]),
            float(cluster_bounds[1]),
            float(cluster_bounds[2]),
            float(cluster_bounds[3]),
        )
        cluster_centroid = accore_profile["dominant_cluster_centroid_mm"]
        centroid_mm = (float(cluster_centroid[0]), float(cluster_centroid[1]))

    if (
        (bounds_mm is None or centroid_mm is None)
        and accore_profile
        and accore_profile.get("bounds_mm")
        and accore_profile.get("centroid_mm")
    ):
        raw_bounds = accore_profile["bounds_mm"]
        bounds_mm = (float(raw_bounds[0]), float(raw_bounds[1]), float(raw_bounds[2]), float(raw_bounds[3]))
        raw_centroid = accore_profile["centroid_mm"]
        centroid_mm = (float(raw_centroid[0]), float(raw_centroid[1]))
    coordinate_band_key, coordinate_band = _coordinate_band(centroid_mm, cell_size_mm=coordinate_band_cell_mm)

    notes: list[str] = []
    if accore_profile and raw_entity_count > 0:
        annotation_ratio = (raw_annotation_count / raw_entity_count) if raw_entity_count > 0 else 0.0
        if annotation_ratio > max_annotation_ratio:
            status: AuditStatus = "annotation_noise"
            notes.append(f"annotation_ratio={annotation_ratio:.2f}")
        elif raw_primary_candidate_count == 0:
            status = "bbox_only"
            notes.append("sin geometria primaria util")
        else:
            status = "eligible"
            if raw_primary_candidate_count < min_primary_elements:
                notes.append(f"low_primary_count={raw_primary_candidate_count}")
    elif selected_total == 0:
        status = "extract_failed"
        notes.append("sin perfil ligero ni elementos extraidos")
    else:
        annotation_ratio = (raw_annotation_count / raw_entity_count) if raw_entity_count > 0 else 0.0
        if annotation_ratio > max_annotation_ratio:
            status = "annotation_noise"
            notes.append(f"annotation_ratio={annotation_ratio:.2f}")
        elif selected_primary == 0 or raw_primary_candidate_count == 0:
            status = "bbox_only"
            notes.append("sin geometria primaria util")
        else:
            status = "eligible"
            if selected_primary < min_primary_elements:
                notes.append(f"low_primary_count={selected_primary}")

    return SourceAudit(
        rel_path=str(candidate.rel_path),
        file_name=Path(str(candidate.rel_path)).name,
        suffix=str(candidate.suffix),
        issue_key=str(candidate.issue_key),
        cohort_id=str(candidate.cohort_id or candidate.issue_key),
        discipline=str(candidate.discipline.value),
        level_id=str(candidate.level_id),
        level_source=str(candidate.level_source),
        coordinate_band_key=coordinate_band_key,
        coordinate_band=coordinate_band,
        centroid_mm=centroid_mm,
        bounds_mm=bounds_mm,
        units_to_mm_factor=units_to_mm_factor,
        raw_entity_count=raw_entity_count,
        raw_primary_candidate_count=raw_primary_candidate_count,
        raw_annotation_count=raw_annotation_count,
        raw_bbox_only_count=raw_bbox_only_count,
        selected_total_count=selected_total,
        selected_primary_count=selected_primary,
        dominant_entity_types=dominant_entity_types,
        audit_status=status,
        notes=notes,
    )


def apply_coordinate_band_gating(
    audits: list[SourceAudit],
    *,
    required_disciplines: tuple[Any, ...],
) -> list[SourceAudit]:
    required_values = {
        discipline.value if hasattr(discipline, "value") else str(discipline)
        for discipline in required_disciplines
    }
    band_counts: Counter[tuple[int, int]] = Counter(
        audit.coordinate_band_key
        for audit in audits
        if audit.audit_status == "eligible"
        and audit.coordinate_band_key is not None
        and audit.discipline in required_values
    )
    if not band_counts:
        return audits
    dominant_band = band_counts.most_common(1)[0][0]

    gated: list[SourceAudit] = []
    for audit in audits:
        if (
            audit.audit_status == "eligible"
            and audit.coordinate_band_key is not None
            and audit.coordinate_band_key != dominant_band
        ):
            notes = list(audit.notes)
            notes.append("fuera de la banda dominante")
            gated.append(audit.model_copy(update={"audit_status": "needs_alignment", "notes": notes}))
        else:
            gated.append(audit)
    return gated


def build_pair_schedule(
    audits: list[SourceAudit],
    *,
    required_disciplines: tuple[Any, ...],
) -> list[PairScheduleItem]:
    required_values = {
        discipline.value if hasattr(discipline, "value") else str(discipline)
        for discipline in required_disciplines
    }
    schedule: list[PairScheduleItem] = []
    ordered = sorted(audits, key=lambda item: (item.cohort_id, item.rel_path))
    for index, left in enumerate(ordered):
        if left.discipline not in required_values:
            continue
        for right in ordered[index + 1 :]:
            if right.cohort_id != left.cohort_id:
                continue
            if right.discipline not in required_values or right.discipline == left.discipline:
                continue
            block_reason = None
            scheduled = True
            if left.audit_status != "eligible":
                scheduled = False
                block_reason = f"{left.file_name}:{left.audit_status}"
            elif right.audit_status != "eligible":
                scheduled = False
                block_reason = f"{right.file_name}:{right.audit_status}"
            elif left.coordinate_band_key != right.coordinate_band_key:
                scheduled = False
                block_reason = "coordinate_band_mismatch"
            elif left.level_id != right.level_id:
                scheduled = False
                block_reason = "level_mismatch"

            schedule.append(
                PairScheduleItem(
                    cohort_id=left.cohort_id,
                    file_a=left.rel_path,
                    file_b=right.rel_path,
                    coordinate_band=left.coordinate_band if left.coordinate_band == right.coordinate_band else None,
                    level_ids=(left.level_id, right.level_id),
                    scheduled=scheduled,
                    block_reason=block_reason,
                )
            )
    return schedule


def render_coordinate_audit_markdown(
    audits: list[SourceAudit],
    *,
    project_name: str,
    root: Path,
) -> str:
    lines = [
        f"# Coordinate Audit - {project_name}",
        "",
        f"- Root: `{root.as_posix()}`",
        f"- Files audited: {len(audits)}",
        "",
        "## Sources",
    ]
    for audit in audits:
        lines.append(
            "- "
            f"`{audit.file_name}` [{audit.discipline} / {audit.level_id}] "
            f"status `{audit.audit_status}`; band `{audit.coordinate_band or 'none'}`; "
            f"raw primary {audit.raw_primary_candidate_count}; "
            f"selected primary {audit.selected_primary_count}/{audit.selected_total_count}; "
            f"raw entities {audit.raw_entity_count}; raw annotation {audit.raw_annotation_count}"
        )
    lines.append("")
    return "\n".join(lines)


def render_hotspot_markdown(
    incidents: list[Any],
    *,
    project_name: str,
    root: Path,
) -> str:
    lines = [
        f"# Hotspot Incidents - {project_name}",
        "",
        f"- Root: `{root.as_posix()}`",
        f"- Incident count: {len(incidents)}",
        "",
        "## Hotspots",
    ]
    for incident in incidents:
        representative = incident.representative_conflict
        x, y = incident.plan_centroid_mm
        lines.append(
            "- "
            f"`{Path(incident.file_pair[0]).name}` vs `{Path(incident.file_pair[1]).name}`: "
            f"{incident.member_count} miembros, "
            f"centro ({round(x):,}, {round(y):,}) mm, "
            f"geometrias {' / '.join(incident.geometry_sources)}, "
            f"niveles {' / '.join(representative.level_ids)}"
        )
    lines.append("")
    return "\n".join(lines)


def _coordinate_band(
    centroid_mm: tuple[float, float] | None,
    *,
    cell_size_mm: float,
) -> tuple[tuple[int, int] | None, str | None]:
    if centroid_mm is None:
        return (None, None)
    key = (
        int(math.floor(centroid_mm[0] / cell_size_mm)),
        int(math.floor(centroid_mm[1] / cell_size_mm)),
    )
    label = f"X~{centroid_mm[0] / 1_000_000.0:.2f}M, Y~{centroid_mm[1] / 1_000_000.0:.2f}M"
    return (key, label)


def _elements_bounds_and_centroid(
    elements: list[Element25D],
) -> tuple[tuple[float, float, float, float] | None, tuple[float, float] | None]:
    if not elements:
        return (None, None)
    primary_elements = [element for element in elements if primary_geometry_role(element)]
    points_source = primary_elements or elements
    xs: list[float] = []
    ys: list[float] = []
    for element in points_source:
        for x, y in element.footprint_coords_mm:
            xs.append(float(x))
            ys.append(float(y))
    if not xs or not ys:
        return (None, None)
    bounds = (min(xs), min(ys), max(xs), max(ys))
    centroid = ((bounds[0] + bounds[2]) / 2.0, (bounds[1] + bounds[3]) / 2.0)
    return (bounds, centroid)


def _dominant_entity_types(elements: list[Element25D]) -> list[str]:
    counts: Counter[str] = Counter()
    for element in elements:
        parts = str(element.source_ref).split("|")
        if len(parts) >= 3:
            counts[parts[2]] += 1
    return [entity_type for entity_type, _count in counts.most_common(5)]
