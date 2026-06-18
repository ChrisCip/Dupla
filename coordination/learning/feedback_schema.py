"""Schemas for human-in-the-loop clash feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClashFeedback(BaseModel):
    """Canonical feedback record for one reviewed clash incident."""

    model_config = ConfigDict(extra="forbid")

    run_label: str
    incident_id: str
    project_name: str
    discipline_pair: str
    level_id: str
    layer_pair: str
    geometry_metrics: dict[str, float | int | str] = Field(default_factory=dict)
    human_label: Literal["REAL_CLASH", "FALSE_POSITIVE", "MARGINAL"]
    human_reason: str
    reviewer: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    project_type: str | None = None
    notes: str | None = None

