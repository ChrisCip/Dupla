from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"
    status_url: str = Field(
        ...,
        description="Relative URL template; resolve against API base.",
    )


class JobResultsResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    created_at: str | None = None
    updated_at: str | None = None
    error: str | None = None
    outputs: dict[str, Any] | None = None
    cad_facts: dict[str, Any] | None = Field(
        default=None,
        description="Present when status is succeeded: normalized CAD facts JSON.",
    )
    cad_fact_keys: int | None = None
    uploaded_object_name: str | None = None
