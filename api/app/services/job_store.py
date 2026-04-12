from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("dupla.api.job_store")

JobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    dwg_filename: str | None = None
    error: str | None = None
    outputs: dict[str, Any] | None = None
    cad_fact_keys: int | None = None
    uploaded_object_name: str | None = None


class JobStore:
    """Filesystem-backed job metadata under ``{job_data_dir}/jobs/{uuid}/meta.json``."""

    def __init__(self, job_data_dir: Path) -> None:
        self.job_data_dir = Path(job_data_dir).resolve()
        self.jobs_root = self.job_data_dir / "jobs"

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_root / job_id

    def inputs_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "inputs"

    def outputs_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "outputs"

    def meta_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "meta.json"

    def create_pending(self, job_id: str, *, dwg_filename: str) -> JobRecord:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        now = _utc_now_iso()
        record = JobRecord(
            job_id=job_id,
            status="pending",
            created_at=now,
            updated_at=now,
            dwg_filename=dwg_filename,
        )
        self._write(record)
        return record

    def get(self, job_id: str) -> JobRecord | None:
        path = self.meta_path(job_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _record_from_dict(data)

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        error: str | None = None,
        outputs: dict[str, Any] | None = None,
        cad_fact_keys: int | None = None,
        uploaded_object_name: str | None = None,
    ) -> JobRecord:
        current = self.get(job_id)
        if current is None:
            raise KeyError(f"Unknown job_id: {job_id}")
        if status is not None:
            current.status = status
        if error is not None:
            current.error = error
        if outputs is not None:
            current.outputs = outputs
        if cad_fact_keys is not None:
            current.cad_fact_keys = cad_fact_keys
        if uploaded_object_name is not None:
            current.uploaded_object_name = uploaded_object_name
        current.updated_at = _utc_now_iso()
        self._write(current)
        return current

    def _write(self, record: JobRecord) -> None:
        path = self.meta_path(record.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(record)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_from_dict(data: dict[str, Any]) -> JobRecord:
    return JobRecord(
        job_id=data["job_id"],
        status=data["status"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        dwg_filename=data.get("dwg_filename"),
        error=data.get("error"),
        outputs=data.get("outputs"),
        cad_fact_keys=data.get("cad_fact_keys"),
        uploaded_object_name=data.get("uploaded_object_name"),
    )
