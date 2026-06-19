"""Workflow incident contract: titles, labels, base-plan rule, confirmed-clash gate.

Broad/narrow architecture (motor coordination/core/clash.py):
  AABB/STRtree overlap = candidate_pair (broad phase, not ingested here).
  exact XY intersection + Z overlap = confirmed_clash (narrow phase).
  Only confirmed_clash rows in primary_incidents become INC-xxx workflow items.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domain.clash_severity import resolve_incident_severity, severity_label_es
from app.services.clash_reports.formatting import FilenameAliasRegistry, layers_from_incident

SHORT_LABEL_MAX_LEN = 90

_ARCH_MARKERS = ("ARQUITECTURA", "ARCH", "ARQ")
_STRUCT_MARKERS = ("ESTRUCTURA", "STRUC", "EST")
_PLUMB_MARKERS = ("FONTANERIA", "PLOMERIA", "SANITARIO", "HID", "SAN")


@dataclass
class IncidentContractFields:
    title_semantic: str
    short_label: str
    table_comment: str
    base_plan_number: str
    compared_plan_number: str
    severity: str
    workflow_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanAliasState:
    registry: FilenameAliasRegistry = field(default_factory=FilenameAliasRegistry)
    seq_by_prefix: dict[str, int] = field(default_factory=dict)

    def plan_number_for(self, filename: str, *, discipline: str | None) -> tuple[str, list[str]]:
        warnings: list[str] = []
        stem = Path(str(filename or "")).name
        if not stem:
            return "PLAN-00", ["missing_plan_filename"]
        alias = self.registry.alias_for(stem, discipline=discipline)
        prefix = alias.split("_", 1)[0].upper()
        self.seq_by_prefix[prefix] = self.seq_by_prefix.get(prefix, 0) + 1
        code = f"{prefix}-{self.seq_by_prefix[prefix]:02d}"
        if len(stem) > 48:
            warnings.append(f"plan_alias_fallback:{stem[:48]}")
        return code, warnings


def normalize_incident_code(incident_id: str) -> str:
    text = str(incident_id or "").strip()
    match = re.search(r"(\d+)", text)
    if match:
        return f"INC-{int(match.group(1)):03d}"
    if text.upper().startswith("INC-"):
        return text.upper()
    return "INC-000"


def is_confirmed_workflow_incident(incident: dict[str, Any]) -> bool:
    """Reject broad-phase / candidate-only payloads; require narrow-phase evidence."""
    if incident.get("candidate_only") is True:
        return False
    phase = str(incident.get("phase") or incident.get("detection_phase") or "").strip().lower()
    if phase in {"broad", "candidate", "candidate_pair", "aabb"}:
        return False
    if incident.get("confirmed") is False:
        return False

    rep = incident.get("representative_conflict")
    if not isinstance(rep, dict) or not rep:
        return False

    try:
        area = float(rep.get("plan_intersection_area_mm2") or 0.0)
    except (TypeError, ValueError):
        area = 0.0
    z_raw = rep.get("overlap_depth_z_mm")
    clash_type = rep.get("clash_type")
    has_z = z_raw is not None
    if area <= 0.0 and not has_z and not clash_type:
        return False
    return True


def _discipline_marker(discipline: str | None, markers: tuple[str, ...]) -> bool:
    text = str(discipline or "").strip().upper()
    return any(text.startswith(m) or m in text for m in markers)


def resolve_base_compared(
    *,
    discipline_a: str | None,
    discipline_b: str | None,
    user_base_index: int | None = None,
) -> tuple[int, int, str, list[str]]:
    """Return (base_idx, compared_idx, base_rule, warnings) for file_pair indices."""
    warnings: list[str] = []
    if user_base_index in (0, 1):
        compared = 1 - user_base_index
        return user_base_index, compared, "user_selected_base", warnings

    if _discipline_marker(discipline_a, _ARCH_MARKERS):
        return 0, 1, "architecture_base", warnings
    if _discipline_marker(discipline_b, _ARCH_MARKERS):
        return 1, 0, "architecture_base", warnings
    if _discipline_marker(discipline_a, _STRUCT_MARKERS):
        return 0, 1, "structure_base", warnings
    if _discipline_marker(discipline_b, _STRUCT_MARKERS):
        return 1, 0, "structure_base", warnings

    warnings.append("base_plan_rule_fallback_dwg_a")
    return 0, 1, "fallback_dwg_a", warnings


def _element_label_from_layer(layer: str | None) -> str:
    if not layer:
        return "elemento"
    text = str(layer).strip().upper()
    mapping = {
        "MURO": "muro",
        "COLUMN": "columna",
        "COLUM": "columna",
        "VIGA": "viga",
        "LOSA": "losa",
        "TUB": "tubería",
        "SAN": "bajante sanitaria",
        "BAJ": "bajante",
        "DUCT": "ducto",
        "MANIF": "manifold",
    }
    for key, label in mapping.items():
        if key in text:
            return label
    token = text.split("_")[-1].lower()
    return token if token else "elemento"


def _problem_phrase(layer_a: str | None, layer_b: str | None, clash_type: str | None) -> str:
    la = _element_label_from_layer(layer_a)
    lb = _element_label_from_layer(layer_b)
    if clash_type == "SOFT":
        return f"{la} no respeta holgura con {lb}"
    if la != "elemento" and lb != "elemento":
        return f"{la} interfiere con {lb}"
    return "solape constructivo entre capas"


def _action_phrase(clash_type: str | None) -> str:
    if clash_type == "SOFT":
        return "Ajustar separación."
    return "Coordinar en planta."


def build_table_comment(
    *,
    level_id: str | None,
    discipline_a: str | None,
    discipline_b: str | None,
    layer_a: str | None,
    layer_b: str | None,
    clash_type: str | None,
    base_plan: str,
    compared_plan: str,
) -> str:
    layers = " / ".join(x for x in (layer_a, layer_b) if x) or "capas no identificadas"
    discs = " / ".join(x for x in (discipline_a, discipline_b) if x) or "disciplinas mixtas"
    level = level_id or "nivel no indicado"
    problem = _problem_phrase(layer_a, layer_b, clash_type)
    return (
        f"En {level}, {problem} entre {discs} ({layers}) al comparar "
        f"{base_plan}_BASE con {compared_plan}. Revisar trazado y resolver en el DWG base."
    )


def build_short_label(
    incident_code: str,
    *,
    layer_a: str | None,
    layer_b: str | None,
    clash_type: str | None,
    max_len: int = SHORT_LABEL_MAX_LEN,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    problem = _problem_phrase(layer_a, layer_b, clash_type)
    action = _action_phrase(clash_type).rstrip(".")
    label = f"{incident_code}: {problem.capitalize()}. {action}."
    if len(label) <= max_len:
        return label, warnings
    trimmed = label[: max_len - 1].rstrip() + "…"
    warnings.append("short_label_truncated")
    return trimmed, warnings


def build_title_semantic(
    *,
    base_plan_number: str,
    incident_code: str,
    compared_plan_number: str,
    severity: str,
) -> str:
    sev_es = severity_label_es(severity)
    return (
        f"{base_plan_number}_BASE / {incident_code} / "
        f"Contra {compared_plan_number} / Severidad {sev_es}"
    )


def build_incident_contract(
    incident: dict[str, Any],
    *,
    plan_state: PlanAliasState,
    enriched: dict[str, Any] | None = None,
    user_base_index: int | None = None,
) -> IncidentContractFields:
    pair = incident.get("file_pair") or ("", "")
    paths = list(pair) if isinstance(pair, (list, tuple)) else ["", ""]
    while len(paths) < 2:
        paths.append("")

    rep = incident.get("representative_conflict") or {}
    discipline_a = str(rep.get("discipline_a") or (enriched or {}).get("discipline_a") or "") or None
    discipline_b = str(rep.get("discipline_b") or (enriched or {}).get("discipline_b") or "") or None
    layer_a, layer_b = layers_from_incident(incident)
    clash_type = str(rep.get("clash_type") or "") or None
    level_id = str(incident.get("level_id") or "") or None

    base_idx, compared_idx, base_rule, rule_warnings = resolve_base_compared(
        discipline_a=discipline_a,
        discipline_b=discipline_b,
        user_base_index=user_base_index,
    )

    base_path, compared_path = paths[base_idx], paths[compared_idx]
    base_disc = discipline_a if base_idx == 0 else discipline_b
    compared_disc = discipline_b if compared_idx == 1 else discipline_a

    base_plan, base_warn = plan_state.plan_number_for(base_path, discipline=base_disc)
    compared_plan, compared_warn = plan_state.plan_number_for(compared_path, discipline=compared_disc)

    incident_code = normalize_incident_code(str(incident.get("incident_id") or "unknown"))
    severity = resolve_incident_severity(incident, enriched=enriched)

    short_label, short_warn = build_short_label(
        incident_code,
        layer_a=layer_a,
        layer_b=layer_b,
        clash_type=clash_type,
    )
    table_comment = build_table_comment(
        level_id=level_id,
        discipline_a=discipline_a,
        discipline_b=discipline_b,
        layer_a=layer_a,
        layer_b=layer_b,
        clash_type=clash_type,
        base_plan=base_plan,
        compared_plan=compared_plan,
    )
    title_semantic = build_title_semantic(
        base_plan_number=base_plan,
        incident_code=incident_code,
        compared_plan_number=compared_plan,
        severity=severity,
    )

    warnings = [*rule_warnings, *base_warn, *compared_warn, *short_warn]
    metadata: dict[str, Any] = {
        "base_rule": base_rule,
        "base_file_index": base_idx,
        "compared_file_index": compared_idx,
        "incident_code": incident_code,
        "confirmed_clash": True,
        "warnings": warnings,
        "has_real_visual": False,
        "visual_provenance": "pending_pr3_renderer",
        "broad_narrow_note": (
            "AABB/STRtree overlap = candidate_pair; "
            "exact XY intersection + Z overlap = confirmed_clash; "
            "only confirmed_clash creates INC-xxx."
        ),
    }

    return IncidentContractFields(
        title_semantic=title_semantic,
        short_label=short_label,
        table_comment=table_comment,
        base_plan_number=base_plan,
        compared_plan_number=compared_plan,
        severity=severity,
        workflow_metadata=metadata,
    )
