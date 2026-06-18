"""Coordination package diagnostics and alignment readiness checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from coordination.selection.coordinate_audit import SourceAudit
from coordination.selection.fast_compare import AlignmentOverride, CohortManifest
from coordination.selection.source_selection import normalize_source_text


def alignment_gaps_for_scheduled_pairs(
    *,
    scheduled_pairs: list[Any],
    audit_by_rel: dict[str, SourceAudit],
    alignment_overrides: dict[str, AlignmentOverride] | None,
) -> list[dict[str, object]]:
    """Files that need manifest alignment before clash comparison."""
    overrides = alignment_overrides or {}
    gaps: list[dict[str, object]] = []
    seen: set[str] = set()

    for pair in scheduled_pairs:
        alignment_required = str(getattr(pair, "alignment_status", "") or "") == "required"
        band_mismatch = bool(getattr(pair, "scheduled", False)) and not bool(
            getattr(pair, "coordinate_compatible", True)
        )
        if not alignment_required and not band_mismatch:
            continue

        pair_paths = (getattr(pair, "file_a", ""), getattr(pair, "file_b", ""))
        if band_mismatch:
            if any(normalize_source_text(str(rel)) in overrides for rel in pair_paths if rel):
                continue

        for rel_path in pair_paths:
            key = normalize_source_text(str(rel_path))
            if not key or key in seen:
                continue
            audit = audit_by_rel.get(rel_path) or audit_by_rel.get(key)
            if audit is None:
                continue
            if not band_mismatch and audit.audit_status != "needs_alignment":
                continue
            if key in overrides:
                continue
            seen.add(key)
            gaps.append(
                {
                    "rel_path": audit.rel_path,
                    "file_name": audit.file_name,
                    "discipline": audit.discipline,
                    "level_id": audit.level_id,
                    "coordinate_band": audit.coordinate_band,
                    "audit_status": audit.audit_status,
                    "pair_file_a": getattr(pair, "file_a", None),
                    "pair_file_b": getattr(pair, "file_b", None),
                    "reason": "coordinate_band_mismatch" if band_mismatch else "needs_alignment",
                }
            )
    return gaps


def build_coordination_package_diagnostics(
    *,
    project_name: str,
    nasas_root: Path,
    cohort_manifest: CohortManifest | None,
    alignment_overrides: dict[str, AlignmentOverride] | None,
    selected_candidates: list[Any],
    candidate_audits: list[SourceAudit],
    scheduled_pairs: list[Any],
    primary_incident_count: int,
    status: str,
    alignment_gaps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    audit_by_rel = {audit.rel_path: audit for audit in candidate_audits}
    override_keys = set((alignment_overrides or {}).keys())
    files: list[dict[str, object]] = []

    for candidate in selected_candidates:
        rel = str(getattr(candidate, "rel_path", ""))
        audit = audit_by_rel.get(rel)
        alignment_required = False
        alignment_applied = normalize_source_text(rel) in override_keys
        if audit is not None:
            alignment_required = audit.audit_status == "needs_alignment"
        for pair in scheduled_pairs:
            if rel not in (getattr(pair, "file_a", ""), getattr(pair, "file_b", "")):
                continue
            if str(getattr(pair, "alignment_status", "")) == "required":
                alignment_required = True
            break

        discipline = getattr(candidate, "discipline", "")
        discipline_label = discipline.value if hasattr(discipline, "value") else str(discipline)
        files.append(
            {
                "rel_path": rel,
                "file_name": Path(rel).name,
                "discipline": discipline_label,
                "level_id": str(getattr(candidate, "level_id", "")),
                "coordinate_band": audit.coordinate_band if audit else None,
                "audit_status": audit.audit_status if audit else None,
                "alignment_required": alignment_required,
                "alignment_applied": alignment_applied,
                "scheduled_for_clash": any(
                    rel in (getattr(pair, "file_a", ""), getattr(pair, "file_b", ""))
                    and bool(getattr(pair, "scheduled", False))
                    for pair in scheduled_pairs
                ),
            }
        )

    scheduled_count = sum(1 for pair in scheduled_pairs if bool(getattr(pair, "scheduled", False)))
    gaps = alignment_gaps or alignment_gaps_for_scheduled_pairs(
        scheduled_pairs=scheduled_pairs,
        audit_by_rel=audit_by_rel,
        alignment_overrides=alignment_overrides,
    )

    return {
        "project_name": project_name,
        "nasas_root": str(nasas_root),
        "package_mode": "cohort_manifest" if cohort_manifest else "preferred_selection",
        "cohort_name": cohort_manifest.cohort_name if cohort_manifest else None,
        "cohort_file_count": len(cohort_manifest.source_files) if cohort_manifest else None,
        "selected_file_count": len(selected_candidates),
        "scheduled_pair_count": scheduled_count,
        "primary_incident_count": primary_incident_count,
        "alignment_override_count": len(alignment_overrides or {}),
        "alignment_gaps": gaps,
        "alignment_blocking": bool(gaps),
        "status": status,
        "files": files,
    }


def render_coordination_package_markdown(payload: dict[str, object]) -> str:
    lines = [
        f"# Coordination Package Diagnostics - {payload.get('project_name') or 'Proyecto'}",
        "",
        f"- Root: `{payload.get('nasas_root')}`",
        f"- Package mode: `{payload.get('package_mode')}`",
        f"- Cohort: `{payload.get('cohort_name') or 'n/a'}` ({payload.get('cohort_file_count') or 0} files in manifest)",
        f"- Selected files: {payload.get('selected_file_count')}",
        f"- Scheduled pairs: {payload.get('scheduled_pair_count')}",
        f"- Primary incidents: {payload.get('primary_incident_count')}",
        f"- Alignment overrides: {payload.get('alignment_override_count')}",
        f"- Status: `{payload.get('status')}`",
        "",
    ]
    gaps = payload.get("alignment_gaps") or []
    if gaps:
        lines.extend(
            [
                "## Alignment blocking",
                "Scheduled pairs require alignment, but these files have no `alignment_manifest` entry:",
                "",
                "| File | Discipline | Level | Band | Audit status |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            lines.append(
                "| "
                f"`{gap.get('file_name')}` | "
                f"{gap.get('discipline')} | "
                f"`{gap.get('level_id')}` | "
                f"`{gap.get('coordinate_band') or 'none'}` | "
                f"`{gap.get('audit_status')}` |"
            )
        lines.append("")
    else:
        lines.append("## Alignment blocking")
        lines.append("- None. All required alignment overrides are present or not required.")
        lines.append("")

    lines.extend(
        [
            "## Package files",
            "| File | Discipline | Level | Band | Audit | Alignment required | Alignment applied | Scheduled |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload.get("files") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            f"`{row.get('file_name')}` | "
            f"{row.get('discipline')} | "
            f"`{row.get('level_id')}` | "
            f"`{row.get('coordinate_band') or 'none'}` | "
            f"`{row.get('audit_status') or 'n/a'}` | "
            f"{'yes' if row.get('alignment_required') else 'no'} | "
            f"{'yes' if row.get('alignment_applied') else 'no'} | "
            f"{'yes' if row.get('scheduled_for_clash') else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)
