"""Normalize clash incident data from all upstream sources for reports and PDFs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coordination.reporting.revision_report import _zoom_command

_NA = "no disponible"
_DEFAULT_CENTER_RADIUS_MM = 5000.0


@dataclass
class FieldProvenance:
    layers_source: str = "unavailable"
    center_source: str = "unavailable"
    bounds_source: str = "unavailable"
    zoom_source: str = "unavailable"
    discipline_source: str = "unavailable"
    level_source: str = "unavailable"


@dataclass
class NormalizedIncident:
    incident_id: str
    human_code: str
    group_code: str
    layer_a: str | None
    layer_b: str | None
    file_a_full: str
    file_b_full: str
    discipline_a: str
    discipline_b: str
    level_id: str
    severity: str
    confidence: str
    area_mm2: float
    member_count: int
    clash_type: str
    center_x: float | None
    center_y: float | None
    center_text: str
    bounds: tuple[float, float, float, float] | None
    bounds_text: str
    zoom_command: str | None
    zoom_fallback: str | None
    handle_a: str | None
    handle_b: str | None
    human_description: str
    recommended_action: str
    priority: str
    action_owner: str
    dwg_to_correct: str
    correction_status: str
    upload_status: str
    reviewer_decision: str
    provenance: FieldProvenance = field(default_factory=FieldProvenance)
    warnings: list[str] = field(default_factory=list)


def merge_enriched_cards(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key in ("all_incidents", "defendable_incidents", "validation_incidents"):
        for card in context.get(key) or []:
            if isinstance(card, dict) and card.get("incident_id"):
                out[str(card["incident_id"])] = card
    return out


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        return not v or v in {"?", "-", "—", "unknown", "null", "None", _NA}
    if isinstance(value, (list, tuple)) and len(value) == 0:
        return True
    return False


def _format_optional(value: Any, suffix: str = "") -> str:
    if _is_missing(value):
        return _NA
    text = str(value).strip()
    return f"{text}{suffix}" if suffix else text


def _format_point(x: float | None, y: float | None) -> str:
    if x is None or y is None:
        return _NA
    if x == 0.0 and y == 0.0:
        return _NA
    return f"X: {int(round(x)):,} mm · Y: {int(round(y)):,} mm".replace(",", ".")


def _format_bounds(bounds: tuple[float, float, float, float] | None) -> str:
    if bounds is None:
        return _NA
    x1, y1, x2, y2 = bounds
    return (
        f"x_min={int(round(x1)):,}; y_min={int(round(y1)):,}; "
        f"x_max={int(round(x2)):,}; y_max={int(round(y2)):,} mm"
    ).replace(",", ".")


def _is_valid_bounds(raw: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        vals = tuple(float(v) for v in raw)
    except (TypeError, ValueError):
        return None
    if vals == (0.0, 0.0, 0.0, 0.0):
        return None
    return vals


def _is_valid_center(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    try:
        x, y = float(raw[0]), float(raw[1])
    except (TypeError, ValueError):
        return None
    if x == 0.0 and y == 0.0:
        return None
    return (x, y)


def _parse_layer_pair_text(text: str) -> tuple[str | None, str | None]:
    if _is_missing(text):
        return None, None
    parts = re.split(r"\s*/\s*", str(text).strip())
    if len(parts) >= 2:
        return parts[0].strip() or None, parts[1].strip() or None
    return str(text).strip() or None, None


def _parse_number_token(raw: str) -> float:
    s = raw.strip().replace(" ", "")
    if not s:
        raise ValueError("empty")
    if s.count(",") >= 2 or ("," in s and "." not in s and len(s.split(",")[-1]) == 3):
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return float(s)


def _parse_center_text(text: str) -> tuple[float, float] | None:
    if not text:
        return None
    mx = re.search(r"X:\s*([-\d.,]+)", text, re.I)
    my = re.search(r"Y:\s*([-\d.,]+)", text, re.I)
    if mx and my:
        try:
            return (_parse_number_token(mx.group(1)), _parse_number_token(my.group(1)))
        except ValueError:
            pass
    m = re.search(r"\(([\d,.\-]+),\s*([\d,.\-]+)\)", text)
    if m:
        try:
            return (_parse_number_token(m.group(1)), _parse_number_token(m.group(2)))
        except ValueError:
            pass
    return None


def _parse_bounds_short(text: str) -> tuple[float, float, float, float] | None:
    if not text:
        return None
    parts = re.split(r",\s+", text.strip())
    if len(parts) >= 4:
        try:
            return tuple(_parse_number_token(p) for p in parts[:4])  # type: ignore[return-value]
        except ValueError:
            return None
    return None


def _layers_from_source_refs(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    rep = raw.get("representative_conflict") or {}
    refs = rep.get("source_refs") or []
    layers: list[str | None] = []
    for ref in refs[:2]:
        if not isinstance(ref, str):
            layers.append(None)
            continue
        parts = ref.split("|")
        layer = parts[1].strip() if len(parts) > 1 else None
        if layer in {None, "", "?", "0"}:
            layers.append(None)
        else:
            layers.append(layer)
    while len(layers) < 2:
        layers.append(None)
    return layers[0], layers[1]


def _layers_from_raw_layers(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    rep = raw.get("representative_conflict") or {}
    raw_layers = rep.get("raw_layers") or raw.get("raw_layers")
    if not isinstance(raw_layers, (list, tuple)) or len(raw_layers) < 2:
        return None, None
    la = str(raw_layers[0]).strip() if raw_layers[0] and str(raw_layers[0]) != "?" else None
    lb = str(raw_layers[1]).strip() if raw_layers[1] and str(raw_layers[1]) != "?" else None
    return la, lb


def _layers_from_enriched(card: dict[str, Any]) -> tuple[str | None, str | None]:
    if card.get("layer_a") or card.get("layer_b"):
        la = str(card.get("layer_a") or "").strip() or None
        lb = str(card.get("layer_b") or "").strip() or None
        if la or lb:
            return la, lb
    lp = card.get("layer_pair")
    if isinstance(lp, str):
        la, lb = _parse_layer_pair_text(lp)
        if la or lb:
            return la, lb
    layers = card.get("layers")
    if isinstance(layers, (list, tuple)) and len(layers) >= 2:
        la = str(layers[0] or "").strip() or None
        lb = str(layers[1] or "").strip() or None
        if la or lb:
            return la, lb
    return None, None


def _disciplines_from_enriched(card: dict[str, Any]) -> tuple[str | None, str | None]:
    d = card.get("disciplines")
    if isinstance(d, (list, tuple)) and len(d) >= 2:
        return str(d[0] or ""), str(d[1] or "")
    dp = card.get("discipline_pair")
    if isinstance(dp, str) and "/" in dp:
        parts = [p.strip() for p in dp.split("/")]
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None, None


def _handles_from_incident(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    rep = raw.get("representative_conflict") or {}
    refs = rep.get("source_refs") or []
    handles: list[str | None] = []
    for ref in refs[:2]:
        if not isinstance(ref, str):
            handles.append(None)
            continue
        parts = ref.split("|")
        handle = parts[-1].strip() if parts else None
        handles.append(handle if handle else None)
    while len(handles) < 2:
        handles.append(None)
    return handles[0], handles[1]


def _expanded_bounds_from_center(center: tuple[float, float], radius: float = _DEFAULT_CENTER_RADIUS_MM) -> tuple[float, float, float, float]:
    cx, cy = center
    r = float(radius)
    return (cx - r, cy - r, cx + r, cy + r)


def _zoom_from_center(center: tuple[float, float], radius: float = _DEFAULT_CENTER_RADIUS_MM) -> str:
    return _zoom_command(list(_expanded_bounds_from_center(center, radius)))


def parse_revision_md_incidents(revision_md: str) -> dict[str, dict[str, Any]]:
    if not revision_md:
        return {}
    out: dict[str, dict[str, Any]] = {}
    chunks = re.split(r"\n###\s+", revision_md)
    for chunk in chunks[1:]:
        header = chunk.split("\n", 1)[0]
        m_id = re.search(r"`(incident_[^`]+)`", header)
        if not m_id:
            continue
        inc_id = m_id.group(1)
        layer_m = re.search(r"\*\*Capas\*\*\s*\|\s*`([^`]+)`[^|]*vs\s*`([^`]+)`", chunk, re.I)
        center_m = re.search(r"\*\*Centro del clash\*\*\s*\|\s*X:\s*([^\n|]+)", chunk, re.I)
        zoom_m = re.search(r"```\s*\n(Z W[^\n`]+)", chunk)
        parsed: dict[str, Any] = {}
        if layer_m:
            parsed["layer_a"] = layer_m.group(1).strip()
            parsed["layer_b"] = layer_m.group(2).strip()
        if center_m:
            parsed["center_text"] = center_m.group(0)
            parsed["center"] = _parse_center_text(center_m.group(0))
        if zoom_m:
            parsed["zoom_command"] = zoom_m.group(1).strip()
        out[inc_id] = parsed
    return out


def normalize_incident_for_reports(
    *,
    raw: dict[str, Any],
    human_code: str,
    group_code: str,
    enriched: dict[str, Any] | None = None,
    revision_parsed: dict[str, Any] | None = None,
    file_discipline_hints: dict[str, str] | None = None,
) -> NormalizedIncident:
    """Merge incident fields using explicit fallback order across sources."""
    enriched = enriched or {}
    revision_parsed = revision_parsed or {}
    file_discipline_hints = file_discipline_hints or {}
    prov = FieldProvenance()
    rep = raw.get("representative_conflict") or {}
    inc_id = str(raw.get("incident_id") or _NA)

    pair = raw.get("file_pair") or enriched.get("file_pair") or enriched.get("file_names") or []
    if isinstance(pair, tuple):
        pair = list(pair)
    file_a_full = str(pair[0]) if len(pair) > 0 and not _is_missing(pair[0]) else _NA
    file_b_full = str(pair[1]) if len(pair) > 1 and not _is_missing(pair[1]) else _NA

    # Layers: incident.layers -> source_refs -> raw_layers -> enriched -> revision -> unavailable
    la: str | None = None
    lb: str | None = None
    incident_layers = raw.get("layers") or enriched.get("layers")
    if isinstance(incident_layers, (list, tuple)) and len(incident_layers) >= 2:
        la = str(incident_layers[0] or "").strip() or None
        lb = str(incident_layers[1] or "").strip() or None
        if la or lb:
            prov.layers_source = "incident.layers"
    if la is None or lb is None:
        sra, srb = _layers_from_source_refs(raw)
        if la is None and sra:
            la, prov.layers_source = sra, "source_refs"
        if lb is None and srb:
            lb, prov.layers_source = srb, "source_refs"
    if la is None or lb is None:
        rla, rlb = _layers_from_raw_layers(raw)
        if la is None and rla:
            la, prov.layers_source = rla, "representative_conflict.raw_layers"
        if lb is None and rlb:
            lb, prov.layers_source = rlb, "representative_conflict.raw_layers"
    if la is None or lb is None:
        ela, elb = _layers_from_enriched(enriched)
        if la is None and ela:
            la, prov.layers_source = ela, "coordination_context.layer_pair"
        if lb is None and elb:
            lb, prov.layers_source = elb, "coordination_context.layer_pair"
    if (la is None or lb is None) and revision_parsed:
        if la is None and revision_parsed.get("layer_a"):
            la = str(revision_parsed["layer_a"])
            prov.layers_source = "revision_md"
        if lb is None and revision_parsed.get("layer_b"):
            lb = str(revision_parsed["layer_b"])
            prov.layers_source = "revision_md"

    # Disciplines
    disc_a = str(rep.get("discipline_a") or "")
    disc_b = str(rep.get("discipline_b") or "")
    if disc_a:
        prov.discipline_source = "representative_conflict"
    eda, edb = _disciplines_from_enriched(enriched)
    if not disc_a and eda:
        disc_a, prov.discipline_source = eda, "coordination_context.disciplines"
    if not disc_b and edb:
        disc_b, prov.discipline_source = edb, "coordination_context.disciplines"
    file_a_key = Path(file_a_full).name if file_a_full != _NA else ""
    file_b_key = Path(file_b_full).name if file_b_full != _NA else ""
    if not disc_a and file_a_key in file_discipline_hints:
        disc_a = file_discipline_hints[file_a_key]
        prov.discipline_source = "file_discipline_hints"
    if not disc_b and file_b_key in file_discipline_hints:
        disc_b = file_discipline_hints[file_b_key]
        prov.discipline_source = "file_discipline_hints"
    disc_a = disc_a or _NA
    disc_b = disc_b or _NA

    # Level
    level = raw.get("level_id") or enriched.get("level_id")
    if raw.get("level_id"):
        prov.level_source = "incident.level_id"
    elif enriched.get("level_id"):
        prov.level_source = "coordination_context.level_id"
    level_id = _format_optional(level)

    # Bounds: incident.bounds -> bbox -> bounds_short -> expanded center -> unavailable
    bounds = _is_valid_bounds(raw.get("plan_bounds_mm") or raw.get("bounds_mm"))
    if bounds:
        prov.bounds_source = "incident.plan_bounds_mm"
    if bounds is None:
        bounds = _is_valid_bounds(enriched.get("bounds_mm"))
        if bounds:
            prov.bounds_source = "coordination_context.bounds_mm"
    if bounds is None:
        bounds = _is_valid_bounds(rep.get("plan_intersection_bounds_mm"))
        if bounds:
            prov.bounds_source = "representative_conflict.plan_intersection_bounds_mm"
    if bounds is None and enriched.get("bounds_short"):
        bounds = _parse_bounds_short(str(enriched["bounds_short"]))
        if bounds:
            prov.bounds_source = "coordination_context.bounds_short"

    # Center: incident.center -> centroid fields -> location_short -> revision -> bbox center -> unavailable
    center = _is_valid_center(raw.get("plan_centroid_mm"))
    if center:
        prov.center_source = "incident.plan_centroid_mm"
    if center is None:
        cx = enriched.get("center_x")
        cy = enriched.get("center_y")
        if cx is not None and cy is not None:
            center = _is_valid_center((cx, cy))
            if center:
                prov.center_source = "coordination_context.center_xy"
    if center is None:
        center = _is_valid_center(rep.get("plan_intersection_centroid_mm"))
        if center:
            prov.center_source = "representative_conflict.plan_intersection_centroid_mm"
    if center is None and enriched.get("location_short"):
        center = _parse_center_text(str(enriched["location_short"]))
        if center:
            prov.center_source = "coordination_context.location_short"
    if center is None and revision_parsed.get("center"):
        center = revision_parsed["center"]
        prov.center_source = "revision_md"
    if center is None and bounds:
        center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
        prov.center_source = "bbox_centroid"

    if bounds is None and center is not None:
        bounds = _expanded_bounds_from_center(center)
        prov.bounds_source = "expanded_center_window"

    # Zoom: explicit -> bounds Z W -> center Z W -> fallback warning (never bare Z E)
    zoom_cmd: str | None = None
    zoom_fb: str | None = None
    explicit = (
        raw.get("zoom_command")
        or enriched.get("zoom_command")
        or revision_parsed.get("zoom_command")
    )
    if explicit and str(explicit).strip().upper().startswith("Z W"):
        zoom_cmd = str(explicit).strip()
        if raw.get("zoom_command"):
            prov.zoom_source = "incident.zoom_command"
        elif enriched.get("zoom_command"):
            prov.zoom_source = "coordination_context.zoom_command"
        else:
            prov.zoom_source = "revision_md"
    elif bounds:
        zoom_cmd = _zoom_command(list(bounds))
        prov.zoom_source = "generated_from_bounds"
    elif center:
        zoom_cmd = _zoom_from_center(center)
        prov.zoom_source = "generated_from_center"
    else:
        zoom_fb = (
            "Limites de zoom no disponibles; use Z E e inspeccione manualmente "
            "el nivel y las capas indicadas."
        )
        prov.zoom_source = "fallback_manual"

    area_mm2 = float(rep.get("plan_intersection_area_mm2") or enriched.get("area_mm2") or 0)
    severity = str(enriched.get("severity") or _NA)
    confidence = _format_optional(
        raw.get("confidence") or rep.get("confidence") or enriched.get("report_confidence")
    )
    ha, hb = _handles_from_incident(raw)
    cx_val = center[0] if center else None
    cy_val = center[1] if center else None

    warnings: list[str] = []
    if la is None or lb is None:
        warnings.append(f"{human_code}: capas no disponibles tras revisar todas las fuentes")
    if center is None:
        warnings.append(f"{human_code}: centro XY no disponible tras revisar todas las fuentes")
    if bounds is None:
        warnings.append(f"{human_code}: limites no disponibles tras revisar todas las fuentes")
    if zoom_cmd is None:
        warnings.append(f"{human_code}: comando Z W no generado (fallback manual)")

    return NormalizedIncident(
        incident_id=inc_id,
        human_code=human_code,
        group_code=group_code,
        layer_a=la,
        layer_b=lb,
        file_a_full=file_a_full,
        file_b_full=file_b_full,
        discipline_a=disc_a,
        discipline_b=disc_b,
        level_id=level_id,
        severity=severity,
        confidence=confidence,
        area_mm2=area_mm2,
        member_count=int(raw.get("member_count") or enriched.get("member_count") or 1),
        clash_type=str(rep.get("clash_type") or _NA),
        center_x=cx_val,
        center_y=cy_val,
        center_text=_format_point(cx_val, cy_val),
        bounds=bounds,
        bounds_text=_format_bounds(bounds),
        zoom_command=zoom_cmd,
        zoom_fallback=zoom_fb,
        handle_a=ha,
        handle_b=hb,
        human_description=str(enriched.get("human_description") or _NA),
        recommended_action=str(enriched.get("recommended_action") or _NA),
        priority=str(enriched.get("priority") or _NA),
        action_owner=str(enriched.get("action_owner") or _NA),
        dwg_to_correct=str(enriched.get("dwg_to_correct") or raw.get("dwg_to_correct") or _NA),
        correction_status=str(enriched.get("correction_status") or raw.get("correction_status") or ""),
        upload_status=str(enriched.get("upload_status") or raw.get("upload_status") or ""),
        reviewer_decision=str(
            enriched.get("reviewer_decision")
            or enriched.get("decision")
            or raw.get("reviewer_decision")
            or raw.get("decision")
            or ""
        ),
        provenance=prov,
        warnings=warnings,
    )


def _project_letter(project_name: str) -> str:
    base = project_name.split("—")[0].split("–")[0].strip()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").upper()
    parts = slug.split("_")
    return parts[0][0] if parts else "X"


def normalize_incidents_for_run(
    *,
    project_name: str,
    primary_payload: dict[str, Any],
    report_context: dict[str, Any] | None = None,
    revision_md: str = "",
    file_discipline_hints: dict[str, str] | None = None,
) -> list[NormalizedIncident]:
    """Normalize all primary incidents with group codes aligned to revision report."""
    from collections import defaultdict

    context = report_context or {}
    enriched_cards = merge_enriched_cards(context)
    revision_parsed = parse_revision_md_incidents(revision_md)
    letter = _project_letter(project_name)
    raw_incidents = [i for i in (primary_payload.get("incidents") or []) if isinstance(i, dict)]

    pre: list[tuple[dict[str, Any], NormalizedIncident]] = []
    for raw in raw_incidents:
        iid = str(raw.get("incident_id") or "")
        norm = normalize_incident_for_reports(
            raw=raw,
            human_code="?",
            group_code="?",
            enriched=enriched_cards.get(iid),
            revision_parsed=revision_parsed.get(iid),
            file_discipline_hints=file_discipline_hints,
        )
        pre.append((raw, norm))

    layer_groups: dict[tuple[str, str], list[tuple[dict[str, Any], NormalizedIncident]]] = defaultdict(list)
    for raw, norm in pre:
        key = (norm.layer_a or _NA, norm.layer_b or _NA)
        layer_groups[key].append((raw, norm))

    sorted_groups = sorted(layer_groups.items(), key=lambda kv: -sum(n.area_mm2 for _, n in kv[1]))
    group_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    results: list[NormalizedIncident] = []

    for g_idx, (_key, items) in enumerate(sorted_groups):
        gl = group_letters[g_idx] if g_idx < len(group_letters) else str(g_idx)
        group_code = f"{letter}-{gl}"
        for i_idx, (raw, _norm) in enumerate(items):
            human_code = f"{group_code}{i_idx + 1}"
            iid = str(raw.get("incident_id") or "")
            final = normalize_incident_for_reports(
                raw=raw,
                human_code=human_code,
                group_code=group_code,
                enriched=enriched_cards.get(iid),
                revision_parsed=revision_parsed.get(iid),
                file_discipline_hints=file_discipline_hints,
            )
            results.append(final)
    return results


def normalized_incident_to_dict(norm: NormalizedIncident) -> dict[str, Any]:
    """Serialize a normalized incident for JSON/report context."""
    return {
        "incident_id": norm.incident_id,
        "human_code": norm.human_code,
        "group_code": norm.group_code,
        "layer_a": norm.layer_a,
        "layer_b": norm.layer_b,
        "file_a_full": norm.file_a_full,
        "file_b_full": norm.file_b_full,
        "discipline_a": norm.discipline_a,
        "discipline_b": norm.discipline_b,
        "level_id": norm.level_id,
        "severity": norm.severity,
        "confidence": norm.confidence,
        "center_x": norm.center_x,
        "center_y": norm.center_y,
        "center_text": norm.center_text,
        "bounds_mm": list(norm.bounds) if norm.bounds else None,
        "bounds_text": norm.bounds_text,
        "zoom_command": norm.zoom_command,
        "zoom_fallback": norm.zoom_fallback,
        "member_count": norm.member_count,
        "correction_status": norm.correction_status,
        "upload_status": norm.upload_status,
        "reviewer_decision": norm.reviewer_decision,
        "dwg_to_correct": norm.dwg_to_correct,
        "provenance": {
            "layers_source": norm.provenance.layers_source,
            "center_source": norm.provenance.center_source,
            "bounds_source": norm.provenance.bounds_source,
            "zoom_source": norm.provenance.zoom_source,
            "discipline_source": norm.provenance.discipline_source,
            "level_source": norm.provenance.level_source,
        },
        "warnings": list(norm.warnings),
    }
