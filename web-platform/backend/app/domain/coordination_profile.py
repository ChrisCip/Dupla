"""Coordination profile slug inference (tortuga_c40, serena18, nasas09)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.project import Project

VALID_PROFILES = frozenset({"tortuga_c40", "serena18", "nasas09"})

PROFILE_ALIASES: dict[str, str] = {
    "tortuga_c40": "tortuga_c40",
    "tortuga-c40": "tortuga_c40",
    "tortuga": "tortuga_c40",
    "serena_18": "serena18",
    "serena18": "serena18",
    "serena": "serena18",
    "nasas_09": "nasas09",
    "nasas09": "nasas09",
    "nasas": "nasas09",
}

PROFILE_LABELS: dict[str, str] = {
    "tortuga_c40": "TORTUGA C40",
    "serena18": "SERENA 18",
    "nasas09": "NASAS 09",
}

# Whole-word match in project name / code only (not filenames or fuzzy substrings).
_PROFILE_KEYWORD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\btortuga\b", re.IGNORECASE), "tortuga_c40"),
    (re.compile(r"\bserena\b", re.IGNORECASE), "serena18"),
    (re.compile(r"\bnasas\b", re.IGNORECASE), "nasas09"),
)


def normalize_profile_slug(raw: str | None) -> str | None:
    """Normalize an explicit profile slug (form/API), not free-form project titles."""
    if not raw or not str(raw).strip():
        return None
    key = re.sub(r"[^a-z0-9]+", "_", str(raw).strip().lower()).strip("_")
    key = key.replace("_c_40", "_c40")
    if key in PROFILE_ALIASES:
        return PROFILE_ALIASES[key]
    if key in VALID_PROFILES:
        return key
    return None


def infer_profile_from_project_fields(
    *,
    name: str | None = None,
    project_code: str | None = None,
) -> str | None:
    """Infer profile only when name or project_code contains TORTUGA, SERENA or NASAS."""
    for candidate in (project_code, name):
        if not candidate or not str(candidate).strip():
            continue
        text = str(candidate)
        for pattern, slug in _PROFILE_KEYWORD_PATTERNS:
            if pattern.search(text):
                return slug
    return None


def get_configured_coordination_profile(project: Project) -> str | None:
    """Profile stored on the project (manual selection in Detalles)."""
    return normalize_profile_slug(getattr(project, "coordination_profile", None))


def resolve_coordination_profile(project: Project) -> str | None:
    """Effective profile for running jobs: configured value, else keyword in name/code."""
    explicit = get_configured_coordination_profile(project)
    if explicit:
        return explicit
    return infer_profile_from_project_fields(
        name=project.name,
        project_code=project.project_code,
    )


def apply_inferred_profile_if_empty(project: Project) -> bool:
    """Set coordination_profile from name/code when empty. Returns True if changed."""
    if project.coordination_profile:
        return False
    slug = infer_profile_from_project_fields(name=project.name, project_code=project.project_code)
    if not slug:
        return False
    project.coordination_profile = slug
    return True
