from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# --- Project pipeline (GEBSA IV reference) ---


class DisciplineIn(BaseModel):
    id: str = Field(..., min_length=1, description="Discipline key, e.g. arquitectura")
    dwg_url: str = ""
    pdf_url: str = Field(..., min_length=4, description="HTTPS URL to PDF for vision")


# GEBSA IV reference; keep in sync with pipeline.defaults.DISCIPLINE_ORDER
_GEBSA_DISCIPLINES: tuple[str, ...] = ("arquitectura", "estructura", "sanitario", "electrico")
_GEBSA_FROZEN: frozenset[str] = frozenset(_GEBSA_DISCIPLINES)


class ProjectRunCreate(BaseModel):
    project_id: str = "gebsa_iv"
    project_name: str = "Residencial GEBSA IV"
    """Ordered list; defaults to GEBSA IV order if empty."""
    discipline_order: list[str] = Field(default_factory=list)
    disciplines: list[DisciplineIn] = Field(..., min_length=1)
    skip_aps: bool = False
    max_vision_workers: int | None = Field(default=None, ge=1, le=32)
    max_discipline_workers: int | None = Field(
        default=None,
        ge=1,
        le=4,
        description="Parallel discipline runs (or override server default).",
    )

    @field_validator("disciplines")
    @classmethod
    def _https(cls, v: list[DisciplineIn]) -> list[DisciplineIn]:
        for d in v:
            if not (d.pdf_url or "").strip():
                raise ValueError(f"discipline {d.id}: pdf_url is required")
        return v

    @model_validator(mode="after")
    def _order_and_ids(self) -> "ProjectRunCreate":
        ids_in = {d.id for d in self.disciplines}
        if self.discipline_order:
            order = [x for x in self.discipline_order if x in ids_in and x in _GEBSA_FROZEN]
        else:
            order = [x for x in _GEBSA_DISCIPLINES if x in ids_in]
        if not order:
            raise ValueError("No valid disciplines in order (check ids vs GEBSA template).")
        for d in self.disciplines:
            if d.id not in _GEBSA_FROZEN:
                raise ValueError(f"Unknown discipline id: {d.id!r}")
            if d.id not in order:
                raise ValueError(f"Discipline {d.id} not in resolved run order {order!r}")
        if not self.skip_aps:
            for d in self.disciplines:
                if not (d.dwg_url or "").strip():
                    raise ValueError(f"discipline {d.id}: dwg_url required when skip_aps is false")
        return self


class ProjectRunCreateResponse(BaseModel):
    run_id: str
    status: Literal["pending"] = "pending"
    status_url: str


class ProjectRunGetResponse(BaseModel):
    run_id: str
    project_id: str
    project_name: str
    status: Literal["pending", "running", "succeeded", "failed"]
    created_at: str | None = None
    updated_at: str | None = None
    error: str | None = None
    skip_aps: bool = False
    disciplines: dict[str, Any] = Field(default_factory=dict)
    run_summary: dict[str, Any] | None = None
    work_subdir: str | None = None
