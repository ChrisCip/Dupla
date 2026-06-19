"""Canonical clash severity (internal English enum values)."""

from __future__ import annotations

from typing import Any

from app.domain.clash_workflow_enums import Severity

_SEVERITY_ALIASES: dict[str, str] = {
    "critical": Severity.CRITICAL.value,
    "critica": Severity.CRITICAL.value,
    "crítica": Severity.CRITICAL.value,
    "critico": Severity.CRITICAL.value,
    "crítico": Severity.CRITICAL.value,
    "high": Severity.HIGH.value,
    "alta": Severity.HIGH.value,
    "alto": Severity.HIGH.value,
    "major": Severity.HIGH.value,
    "medium": Severity.MEDIUM.value,
    "media": Severity.MEDIUM.value,
    "medio": Severity.MEDIUM.value,
    "minor": Severity.MEDIUM.value,
    "low": Severity.LOW.value,
    "baja": Severity.LOW.value,
    "bajo": Severity.LOW.value,
    "noise": Severity.LOW.value,
}

_SEVERITY_LABEL_ES: dict[str, str] = {
    Severity.CRITICAL.value: "crítica",
    Severity.HIGH.value: "alta",
    Severity.MEDIUM.value: "media",
    Severity.LOW.value: "baja",
}


def score_to_severity(
    *,
    member_count: int = 1,
    area_mm2: float = 0.0,
    overlap_depth_mm: float = 0.0,
    report_confidence: str = "medium",
) -> str:
    """Match coordination/reporting.py::_severity scoring (4 internal levels)."""
    score = 0.0
    if member_count >= 12:
        score += 2.0
    elif member_count >= 6:
        score += 1.0
    elif member_count >= 3:
        score += 0.5
    if area_mm2 >= 2_000_000.0:
        score += 2.0
    elif area_mm2 >= 750_000.0:
        score += 1.0
    elif area_mm2 >= 200_000.0:
        score += 0.5
    if overlap_depth_mm >= 250.0:
        score += 1.0
    elif overlap_depth_mm >= 100.0:
        score += 0.5
    conf = str(report_confidence or "medium").strip().lower()
    if conf == "high":
        score += 1.0
    elif conf == "low":
        score -= 1.0
    if score >= 4.5 and conf == "high":
        return Severity.CRITICAL.value
    if score >= 3.0:
        return Severity.HIGH.value
    if score >= 1.5:
        return Severity.MEDIUM.value
    return Severity.LOW.value


def normalize_severity(value: Any, *, default: str = Severity.LOW.value) -> str | None:
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    try:
        return Severity(key).value
    except ValueError:
        return None


def severity_label_es(severity: str) -> str:
    normalized = normalize_severity(severity) or Severity.LOW.value
    return _SEVERITY_LABEL_ES.get(normalized, normalized)


def resolve_incident_severity(
    incident: dict[str, Any],
    *,
    enriched: dict[str, Any] | None = None,
) -> str:
    """Prefer motor/enriched severity; fall back to score_to_severity."""
    rep = incident.get("representative_conflict") or {}
    candidates: list[Any] = []
    if enriched:
        candidates.append(enriched.get("severity"))
    candidates.extend(
        [
            incident.get("severity"),
            rep.get("severity"),
        ]
    )
    for raw in candidates:
        normalized = normalize_severity(raw)
        if normalized is not None:
            return normalized

    member_count = int(incident.get("member_count") or (enriched or {}).get("member_count") or 1)
    area_mm2 = float(rep.get("plan_intersection_area_mm2") or (enriched or {}).get("area_mm2") or 0.0)
    overlap_depth_mm = float(
        rep.get("overlap_depth_z_mm") or (enriched or {}).get("overlap_depth_mm") or 0.0
    )
    report_confidence = str(
        incident.get("confidence")
        or rep.get("confidence")
        or (enriched or {}).get("report_confidence")
        or "medium"
    ).lower()
    return score_to_severity(
        member_count=member_count,
        area_mm2=area_mm2,
        overlap_depth_mm=overlap_depth_mm,
        report_confidence=report_confidence,
    )
