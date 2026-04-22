"""Persistence for project pipeline runs (GEBSA IV–style multi-discipline)."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("dupla.api.project_run")

RunStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class DisciplineEntry:
    id: str
    dwg_url: str = ""
    pdf_url: str = ""


@dataclass
class ProjectRunRecord:
    run_id: str
    kind: str
    status: RunStatus
    project_id: str
    project_name: str
    created_at: str
    updated_at: str
    discipline_order: list[str] = field(default_factory=list)
    inputs: list[DisciplineEntry] = field(default_factory=list)
    skip_aps: bool = False
    max_vision_workers: int | None = None
    max_discipline_workers: int | None = None
    error: str | None = None
    disciplines: dict[str, Any] = field(default_factory=dict)
    work_subdir: str | None = None
    run_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["inputs"] = [asdict(x) for x in self.inputs]
        return d

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProjectRunRecord":
        ins = [DisciplineEntry(**x) for x in data.get("inputs", [])]
        return ProjectRunRecord(
            run_id=data["run_id"],
            kind=data.get("kind", "project_pipeline"),
            status=data["status"],
            project_id=data["project_id"],
            project_name=data["project_name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            discipline_order=list(data.get("discipline_order", [])),
            inputs=ins,
            skip_aps=bool(data.get("skip_aps", False)),
            max_vision_workers=data.get("max_vision_workers"),
            max_discipline_workers=data.get("max_discipline_workers"),
            error=data.get("error"),
            disciplines=dict(data.get("disciplines", {})),
            work_subdir=data.get("work_subdir"),
            run_summary=data.get("run_summary"),
        )


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRunStore:
    def __init__(self, job_data_dir: Path) -> None:
        self.base = Path(job_data_dir).resolve() / "project_runs"
        self.base.mkdir(parents=True, exist_ok=True)

    def run_root(self, run_id: str) -> Path:
        return self.base / run_id

    def meta_path(self, run_id: str) -> Path:
        return self.run_root(run_id) / "meta.json"

    def inputs_root(self, run_id: str) -> Path:
        p = self.run_root(run_id) / "inputs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def workspace(self, run_id: str) -> Path:
        p = self.run_root(run_id) / "workspace"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def create_pending(
        self,
        *,
        project_id: str,
        project_name: str,
        inputs: list[DisciplineEntry],
        discipline_order: list[str],
        skip_aps: bool = False,
        max_vision_workers: int | None = None,
        max_discipline_workers: int | None = None,
    ) -> ProjectRunRecord:
        run_id = str(uuid.uuid4())
        now = _utc()
        rec = ProjectRunRecord(
            run_id=run_id,
            kind="project_pipeline",
            status="pending",
            project_id=project_id,
            project_name=project_name,
            created_at=now,
            updated_at=now,
            discipline_order=discipline_order,
            inputs=inputs,
            skip_aps=skip_aps,
            max_vision_workers=max_vision_workers,
            max_discipline_workers=max_discipline_workers,
        )
        self._write(rec)
        return rec

    def get(self, run_id: str) -> ProjectRunRecord | None:
        p = self.meta_path(run_id)
        if not p.is_file():
            return None
        return ProjectRunRecord.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def _write(self, rec: ProjectRunRecord) -> None:
        p = self.meta_path(rec.run_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)

    def update(self, rec: ProjectRunRecord) -> None:
        rec.updated_at = _utc()
        self._write(rec)
