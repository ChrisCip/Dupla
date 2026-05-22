"""Canonical CAD layer role mapping for coordination defensibility."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from coordination.core.models_25d import Discipline

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES_DIR = REPO_ROOT / "config" / "layer_rules"


class CanonicalRole(str, Enum):
    WALL = "WALL"
    SLAB = "SLAB"
    COLUMN = "COLUMN"
    BEAM = "BEAM"
    OPENING = "OPENING"
    STAIR = "STAIR"
    FURNITURE = "FURNITURE"
    ANNOTATION = "ANNOTATION"
    AXIS = "AXIS"
    TERRAIN = "TERRAIN"
    DETAIL = "DETAIL"
    UNKNOWN = "UNKNOWN"


class LayerRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discipline: str = "*"
    pattern: str
    role: CanonicalRole
    priority: int = 0
    confidence: str = "medium"
    reason: str = "rule_match"


class LayerRoleResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_layer: str
    normalized_layer: str
    canonical_role: CanonicalRole
    rule_confidence: str
    rule_reason: str
    matched_pattern: str | None = None


def normalize_layer_name(layer: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", str(layer or "").strip().upper())
    return re.sub(r"\s+", " ", cleaned).strip() or "0"


def resolve_layer_role(
    layer: str,
    discipline: Discipline,
    *,
    rules: list[LayerRule] | None = None,
) -> LayerRoleResolution:
    normalized = normalize_layer_name(layer)
    discipline_name = discipline.value.upper()
    candidate_rules = sorted(rules or [], key=lambda item: item.priority, reverse=True)
    for rule in candidate_rules:
        if not _discipline_matches(rule.discipline, discipline_name):
            continue
        if re.search(rule.pattern, normalized, flags=re.IGNORECASE):
            return LayerRoleResolution(
                raw_layer=str(layer or "0"),
                normalized_layer=normalized,
                canonical_role=rule.role,
                rule_confidence=rule.confidence,
                rule_reason=rule.reason,
                matched_pattern=rule.pattern,
            )
    return LayerRoleResolution(
        raw_layer=str(layer or "0"),
        normalized_layer=normalized,
        canonical_role=CanonicalRole.UNKNOWN,
        rule_confidence="low",
        rule_reason="no_rule_match",
    )


def load_project_layer_rules(
    *,
    project_name: str,
    config_dir: Path | None = None,
) -> list[LayerRule]:
    root = config_dir or DEFAULT_RULES_DIR
    default_path = root / "default.yaml"
    project_path = root / f"{_project_slug(project_name)}.yaml"

    rules: list[LayerRule] = []
    for path in (default_path, project_path):
        if not path.is_file():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = payload.get("rules") if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            rules.append(LayerRule.model_validate(entry))
    return sorted(rules, key=lambda item: item.priority, reverse=True)


def is_suppressed_role(role: CanonicalRole, *, confidence: str) -> bool:
    if role in {
        CanonicalRole.ANNOTATION,
        CanonicalRole.AXIS,
        CanonicalRole.FURNITURE,
        CanonicalRole.DETAIL,
    }:
        return True
    return role == CanonicalRole.UNKNOWN and str(confidence).lower() == "low"


def role_pair_allowed(
    role_a: str,
    role_b: str,
    *,
    role_matrix: dict[tuple[str, str], bool] | None,
    allow_same_role: bool,
) -> bool:
    if not allow_same_role and role_a == role_b:
        return False
    if role_matrix is None:
        return True
    key = (str(role_a).upper(), str(role_b).upper())
    rev = (key[1], key[0])
    return bool(role_matrix.get(key) or role_matrix.get(rev))


def load_role_matrix(
    *,
    project_name: str,
    config_dir: Path | None = None,
) -> tuple[dict[tuple[str, str], bool], set[str]]:
    root = config_dir or (REPO_ROOT / "config" / "clash_role_matrix")
    default_path = root / "default.yaml"
    project_path = root / f"{_project_slug(project_name)}.yaml"
    merged: dict[str, Any] = {"role_pairs": [], "suppress_roles": []}
    for path in (default_path, project_path):
        if not path.is_file():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("role_pairs"), list):
            merged["role_pairs"].extend(payload["role_pairs"])
        if isinstance(payload.get("suppress_roles"), list):
            merged["suppress_roles"] = payload["suppress_roles"]
    role_matrix: dict[tuple[str, str], bool] = {}
    for item in merged["role_pairs"]:
        if not isinstance(item, dict):
            continue
        left = str(item.get("left") or "").upper().strip()
        right = str(item.get("right") or "").upper().strip()
        enabled = bool(item.get("enabled", True))
        if left and right:
            role_matrix[(left, right)] = enabled
    suppress_roles = {str(item).upper().strip() for item in merged["suppress_roles"] if str(item).strip()}
    return role_matrix, suppress_roles


def _discipline_matches(rule_discipline: str, discipline_name: str) -> bool:
    value = str(rule_discipline or "*").strip().upper()
    if value in {"*", "ANY", "ALL"}:
        return True
    return value in {discipline_name, _discipline_alias(discipline_name)}


def _discipline_alias(discipline_name: str) -> str:
    return {
        "ARQUITECTURA": "ARCH",
        "ESTRUCTURA": "STRUC",
        "FONTANERIA": "PLUMBING",
        "CLIMATIZACION": "HVAC",
        "ELECTRICIDAD": "ELEC",
    }.get(discipline_name, discipline_name)


def _project_slug(project_name: str) -> str:
    lowered = str(project_name or "").strip().lower()
    if "serena" in lowered:
        return "serena18"
    if "nasas" in lowered:
        return "nasas09"
    if "tortuga" in lowered:
        return "tortuga_c40"
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return cleaned or "default"
