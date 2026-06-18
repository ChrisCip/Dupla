"""Project tolerances for extraction and clash consistency."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOLERANCES_DIR = REPO_ROOT / "config" / "tolerances"


class ClashTolerances(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_size_mm: float = Field(default=1.0, ge=0.0)
    linear_buffer_mm: float = Field(default=25.0, gt=0.0)
    tesselation_chord_error_mm: float = Field(default=5.0, gt=0.0)
    min_plan_area_mm2: float = Field(default=50_000.0, ge=0.0)
    min_overlap_width_mm: float | None = Field(default=None, ge=0.0)
    z_overlap_tolerance_mm: float = Field(default=25.0, ge=0.0)
    clearance_mm: float = Field(default=0.0, ge=0.0)


def load_project_tolerances(
    *,
    project_name: str,
    config_dir: Path | None = None,
) -> ClashTolerances:
    root = config_dir or DEFAULT_TOLERANCES_DIR
    default_path = root / "default.yaml"
    project_path = root / f"{_project_slug(project_name)}.yaml"

    merged: dict[str, Any] = {}
    for path in (default_path, project_path):
        if not path.is_file():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            merged.update(payload)
    return ClashTolerances.model_validate(merged or {})


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
