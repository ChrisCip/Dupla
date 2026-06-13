"""Live clash workflow: ingest job artifacts, dashboard, reviewer decisions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.clash_coordinates import location_from_mm
from app.domain.clash_workflow_enums import (
    DECISION_TARGET_STATUS,
    PENDING_DECISION_STATUSES,
    ClashStatus,
    EventType,
    Priority,
    ReportConfidence,
    ReviewerDecision,
    Severity,
    can_transition,
    decision_label,
    status_label,
)
from app.models.project_clash_event import ProjectClashEvent
from app.models.project_clash_item import ProjectClashItem
from app.models.project_clash_job import ProjectClashJob
from app.models.user import User
from app.services.clash_service import ClashService, extract_clash_artifacts
from app.services.clash_reports.formatting import compute_severity
from app.services.project_service import ProjectService

class WorkflowError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_json_field(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _safe_enum(value: str, allowed: set[str], default: str) -> str:
    return value if value in allowed else default


def _priority_from_severity(severity: str) -> str:
    if severity == Severity.CRITICAL.value:
        return Priority.P1.value
    if severity in (Severity.HIGH.value, Severity.MEDIUM.value):
        return Priority.P2.value
    return Priority.P3.value


def _incident_to_fields(incident: dict[str, Any]) -> dict[str, Any]:
    rep = incident.get("representative_conflict") or {}
    pair = incident.get("file_pair") or ("", "")
    file_names = [Path(str(p)).name for p in pair] if isinstance(pair, list) else ["", ""]
    while len(file_names) < 2:
        file_names.append("")

    area = float(rep.get("plan_intersection_area_mm2") or 0.0)
    z_depth = rep.get("overlap_depth_z_mm")
    z_val = float(z_depth) if z_depth is not None else None
    severity = compute_severity(area_mm2=area, z_depth_mm=z_val)
    layers = rep.get("raw_layers") or []
    layer_a = str(layers[0]) if len(layers) > 0 and layers[0] else None
    layer_b = str(layers[1]) if len(layers) > 1 and layers[1] else None

    bounds = incident.get("plan_bounds_mm") or rep.get("plan_intersection_bounds_mm")
    if not bounds or len(bounds) != 4:
        bounds = (0.0, 0.0, 0.0, 0.0)
    centroid = incident.get("plan_centroid_mm") or rep.get("plan_intersection_centroid_mm")
    if not centroid or len(centroid) != 2:
        centroid = (0.0, 0.0)

    return {
        "clash_code": str(incident.get("incident_id") or "unknown"),
        "priority": _priority_from_severity(severity),
        "severity": _safe_enum(severity, {s.value for s in Severity}, Severity.LOW.value),
        "report_confidence": _safe_enum(
            str(incident.get("confidence") or rep.get("confidence") or "low").lower(),
            {c.value for c in ReportConfidence},
            ReportConfidence.LOW.value,
        ),
        "status": ClashStatus.DETECTED.value,
        "dwg_a": file_names[0] or None,
        "dwg_b": file_names[1] or None,
        "level_id": str(incident.get("level_id") or "") or None,
        "discipline_a": str(rep.get("discipline_a") or "") or None,
        "discipline_b": str(rep.get("discipline_b") or "") or None,
        "layer_a": layer_a,
        "layer_b": layer_b,
        "observation": None,
        "recommended_action": "Revisar el par directamente en planta.",
        "action_owner": None,
        "centroid_x_mm": float(centroid[0]),
        "centroid_y_mm": float(centroid[1]),
        "bounds_minx_mm": float(bounds[0]),
        "bounds_miny_mm": float(bounds[1]),
        "bounds_maxx_mm": float(bounds[2]),
        "bounds_maxy_mm": float(bounds[3]),
        "area_mm2": area,
        "overlap_depth_mm": z_val,
        "member_count": int(incident.get("member_count") or 0),
        "raw_json": incident,
    }


class ClashWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clash_svc = ClashService(session)
        self._project_svc = ProjectService(session)

    async def _latest_completed_job(self, user: User, project_uuid: UUID) -> ProjectClashJob:
        job = await self._clash_svc.get_latest_job(user, project_uuid)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clash job found")
        if job.status != "completed":
            job = await self._clash_svc.sync_job_status(job)
            await self._session.flush()
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No completed clash analysis for workflow",
            )
        return job

    async def ensure_ingested(self, job: ProjectClashJob, *, actor: str = "system") -> dict[str, int]:
        """Populate workflow rows from job artifacts if not yet ingested."""
        if not isinstance(job.result, dict):
            return {"created": 0, "updated": 0, "total": 0}

        artifacts = extract_clash_artifacts(job.result)
        paths = artifacts.get("paths") if isinstance(artifacts.get("paths"), dict) else {}
        output_dir = paths.get("output_dir")
        if output_dir and not job.output_dir:
            job.output_dir = str(output_dir)

        primary = _parse_json_field(artifacts.get("primary_incidents"))
        incidents = primary.get("incidents") or []
        if not isinstance(incidents, list) or not incidents:
            return {"created": 0, "updated": 0, "total": 0}

        existing = await self._session.execute(
            select(ProjectClashItem.clash_code).where(ProjectClashItem.job_id == job.id)
        )
        existing_codes = {row[0] for row in existing.all()}

        created = 0
        updated = 0
        for inc in incidents:
            if not isinstance(inc, dict):
                continue
            fields = _incident_to_fields(inc)
            code = fields["clash_code"]
            row = await self._session.execute(
                select(ProjectClashItem).where(
                    ProjectClashItem.job_id == job.id,
                    ProjectClashItem.clash_code == code,
                )
            )
            item = row.scalar_one_or_none()
            if item is None:
                item = ProjectClashItem(id=uuid.uuid4(), job_id=job.id, **fields)
                self._session.add(item)
                await self._session.flush()
                self._session.add(
                    ProjectClashEvent(
                        id=uuid.uuid4(),
                        clash_item_id=item.id,
                        event_type=EventType.INGESTED.value,
                        actor=actor,
                        new_status=ClashStatus.DETECTED.value,
                        comment=f"Ingestado desde corrida {job.job_id}",
                        related_run_id=job.job_id,
                        created_at=_now(),
                    )
                )
                created += 1
            else:
                preserved = {"status", "reviewer_decision", "assigned_to", "observation"}
                for key, val in fields.items():
                    if key not in preserved and key != "clash_code":
                        setattr(item, key, val)
                item.updated_at = _now()
                updated += 1

        return {"created": created, "updated": updated, "total": created + updated}

    def _item_location(self, item: ProjectClashItem):
        offset = None
        if item.alignment_dx_mm is not None and item.alignment_dy_mm is not None:
            offset = (item.alignment_dx_mm, item.alignment_dy_mm)
        return location_from_mm(
            centroid_mm=(item.centroid_x_mm or 0.0, item.centroid_y_mm or 0.0),
            bounds_mm=(
                item.bounds_minx_mm or 0.0,
                item.bounds_miny_mm or 0.0,
                item.bounds_maxx_mm or 0.0,
                item.bounds_maxy_mm or 0.0,
            ),
            alignment_offset_mm=offset,
        )

    def _preview_payload(
        self, project_uuid: UUID, job: ProjectClashJob, clash_code: str
    ) -> dict[str, Any]:
        source_dir = job.output_dir
        tiles = Path(source_dir) / "tiles" if source_dir else None
        annotated = tiles / f"{clash_code}_annotated.svg" if tiles else None
        plain = tiles / f"{clash_code}.svg" if tiles else None
        base = f"/api/projects/{project_uuid}/clash-workflow/tiles"
        annotated_url = (
            f"{base}/{clash_code}_annotated.svg"
            if annotated and annotated.is_file()
            else None
        )
        plain_url = (
            f"{base}/{clash_code}.svg"
            if plain and plain.is_file()
            else None
        )
        return {
            "available": bool(annotated_url or plain_url),
            "annotated_url": annotated_url,
            "plain_url": plain_url,
            "default_url": annotated_url or plain_url,
            "format": "svg",
            "description": "Vista de planta con geometría superpuesta de ambos DWG.",
        }

    def item_ui_payload(self, item: ProjectClashItem, job: ProjectClashJob) -> dict[str, Any]:
        try:
            st = ClashStatus(item.status)
        except ValueError:
            st = ClashStatus.DETECTED
        try:
            pr = Priority(item.priority)
        except ValueError:
            pr = Priority.P3
        try:
            sev = Severity(item.severity)
        except ValueError:
            sev = Severity.LOW
        dec = None
        if item.reviewer_decision:
            try:
                dec = ReviewerDecision(item.reviewer_decision)
            except ValueError:
                dec = None

        loc = self._item_location(item)
        layers = " / ".join(x for x in (item.layer_a, item.layer_b) if x)
        return {
            "id": str(item.id),
            "clash_code": item.clash_code,
            "job_id": str(job.id),
            "priority": pr.value,
            "severity": sev.value,
            "report_confidence": item.report_confidence,
            "status": st.value,
            "status_label": status_label(st),
            "reviewer_decision": dec.value if dec else None,
            "decision_label": decision_label(dec) if dec else None,
            "dwg_a": item.dwg_a,
            "dwg_b": item.dwg_b,
            "level_id": item.level_id,
            "discipline_a": item.discipline_a,
            "discipline_b": item.discipline_b,
            "discipline_pair": " / ".join(x for x in (item.discipline_a, item.discipline_b) if x),
            "layer_a": item.layer_a,
            "layer_b": item.layer_b,
            "layers_involved": layers,
            "observation": item.observation,
            "recommended_action": item.recommended_action,
            "action_owner": item.action_owner,
            "assigned_to": item.assigned_to,
            "member_count": item.member_count,
            "area_mm2": item.area_mm2,
            "overlap_depth_mm": item.overlap_depth_mm,
            "location": loc.ui_payload(),
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    async def _query_items(
        self,
        job_id: UUID,
        filters: dict[str, str],
    ) -> list[ProjectClashItem]:
        q = select(ProjectClashItem).where(ProjectClashItem.job_id == job_id)
        result = await self._session.execute(q.order_by(ProjectClashItem.priority, ProjectClashItem.clash_code))
        items = list(result.scalars().all())

        def match(item: ProjectClashItem) -> bool:
            if filters.get("priority") and item.priority != filters["priority"]:
                return False
            if filters.get("severity") and item.severity != filters["severity"]:
                return False
            if filters.get("status") and item.status != filters["status"]:
                return False
            if filters.get("level_id") and item.level_id != filters["level_id"]:
                return False
            if filters.get("discipline"):
                d = filters["discipline"].lower()
                if d not in (item.discipline_a or "").lower() and d not in (item.discipline_b or "").lower():
                    return False
            if filters.get("assigned_to") and item.assigned_to != filters["assigned_to"]:
                return False
            if filters.get("dwg"):
                needle = filters["dwg"].lower()
                if needle not in (item.dwg_a or "").lower() and needle not in (item.dwg_b or "").lower():
                    return False
            return True

        if filters:
            items = [i for i in items if match(i)]
        return items

    async def get_dashboard(
        self,
        user: User,
        project_uuid: UUID,
        filters: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        await self.ensure_ingested(job, actor=user.email)
        items = await self._query_items(job.id, filters or {})

        severity_counts = {s.value: 0 for s in Severity}
        priority_counts = {p.value: 0 for p in Priority}
        status_counts = {s.value: 0 for s in ClashStatus}
        pending_decisions = 0
        correction_uploaded = 0
        pending_reanalysis = 0
        resolved = 0
        false_positives = 0
        still_present = 0

        for item in items:
            severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1
            priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
            try:
                st = ClashStatus(item.status)
            except ValueError:
                st = ClashStatus.DETECTED
            if st in PENDING_DECISION_STATUSES and not item.reviewer_decision:
                pending_decisions += 1
            if st == ClashStatus.CORRECTION_UPLOADED:
                correction_uploaded += 1
            if st == ClashStatus.PENDING_REANALYSIS:
                pending_reanalysis += 1
            if st == ClashStatus.RESOLVED:
                resolved += 1
            if st == ClashStatus.FALSE_POSITIVE:
                false_positives += 1
            if st == ClashStatus.STILL_PRESENT:
                still_present += 1

        return {
            "job_id": str(job.id),
            "total_clashes": len(items),
            "by_severity": {
                "critical": severity_counts.get(Severity.CRITICAL.value, 0),
                "high": severity_counts.get(Severity.HIGH.value, 0),
                "medium": severity_counts.get(Severity.MEDIUM.value, 0),
                "low": severity_counts.get(Severity.LOW.value, 0),
            },
            "by_priority": priority_counts,
            "by_status": status_counts,
            "pending_reviewer_decisions": pending_decisions,
            "correction_uploaded": correction_uploaded,
            "pending_reanalysis": pending_reanalysis,
            "resolved": resolved,
            "false_positives": false_positives,
            "still_present_after_reanalysis": still_present,
        }

    async def list_clashes(
        self,
        user: User,
        project_uuid: UUID,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        job = await self._latest_completed_job(user, project_uuid)
        await self.ensure_ingested(job, actor=user.email)
        items = await self._query_items(job.id, filters or {})
        return [self.item_ui_payload(i, job) for i in items]

    async def get_filters(self, user: User, project_uuid: UUID) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        await self.ensure_ingested(job, actor=user.email)
        result = await self._session.execute(
            select(ProjectClashItem).where(ProjectClashItem.job_id == job.id)
        )
        items = list(result.scalars().all())
        return {
            "priorities": [p.value for p in Priority],
            "statuses": [s.value for s in ClashStatus],
            "severities": [s.value for s in Severity],
            "levels": sorted({i.level_id for i in items if i.level_id}),
            "disciplines": sorted(
                {d for i in items for d in (i.discipline_a, i.discipline_b) if d}
            ),
            "reviewers": sorted({i.assigned_to for i in items if i.assigned_to}),
            "dwgs": sorted({d for i in items for d in (i.dwg_a, i.dwg_b) if d}),
        }

    async def get_clash_detail(self, user: User, project_uuid: UUID, item_id: UUID) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        await self.ensure_ingested(job, actor=user.email)
        result = await self._session.execute(
            select(ProjectClashItem)
            .options(selectinload(ProjectClashItem.events))
            .where(ProjectClashItem.id == item_id, ProjectClashItem.job_id == job.id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clash not found")

        payload = self.item_ui_payload(item, job)
        payload["audit_trail"] = [
            {
                "id": str(ev.id),
                "event_type": ev.event_type,
                "actor": ev.actor,
                "actor_role": ev.actor_role,
                "previous_status": ev.previous_status,
                "new_status": ev.new_status,
                "decision": ev.decision,
                "comment": ev.comment,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in sorted(item.events, key=lambda e: e.created_at or _now())
        ]
        payload["corrections"] = []
        payload["visual_preview"] = self._preview_payload(project_uuid, job, item.clash_code)
        payload["dwg_comparison"] = {
            "dwg_a": {
                "file_name": item.dwg_a,
                "discipline": item.discipline_a,
                "layer": item.layer_a,
            },
            "dwg_b": {
                "file_name": item.dwg_b,
                "discipline": item.discipline_b,
                "layer": item.layer_b,
            },
        }
        return payload

    async def _get_item_for_job(self, job_id: UUID, item_id: UUID) -> ProjectClashItem:
        result = await self._session.execute(
            select(ProjectClashItem).where(
                ProjectClashItem.id == item_id,
                ProjectClashItem.job_id == job_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clash not found")
        return item

    async def _add_event(
        self,
        item: ProjectClashItem,
        *,
        event_type: str,
        actor: str,
        actor_role: str | None = None,
        previous_status: str | None = None,
        new_status: str | None = None,
        decision: str | None = None,
        comment: str | None = None,
    ) -> None:
        self._session.add(
            ProjectClashEvent(
                id=uuid.uuid4(),
                clash_item_id=item.id,
                event_type=event_type,
                actor=actor,
                actor_role=actor_role,
                previous_status=previous_status,
                new_status=new_status,
                decision=decision,
                comment=comment,
                created_at=_now(),
            )
        )

    async def change_status(
        self,
        user: User,
        project_uuid: UUID,
        item_id: UUID,
        new_status: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        item = await self._get_item_for_job(job.id, item_id)
        try:
            current = ClashStatus(item.status)
            target = ClashStatus(new_status)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status") from exc
        if not can_transition(current, target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition: {current.value} -> {target.value}",
            )
        previous = item.status
        if previous != target.value:
            item.status = target.value
            item.updated_at = _now()
        await self._add_event(
            item,
            event_type=EventType.STATUS_CHANGE.value,
            actor=user.email,
            previous_status=previous,
            new_status=target.value,
            comment=comment,
        )
        return self.item_ui_payload(item, job)

    async def record_decision(
        self,
        user: User,
        project_uuid: UUID,
        item_id: UUID,
        decision: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        item = await self._get_item_for_job(job.id, item_id)
        try:
            dec = ReviewerDecision(decision)
            current = ClashStatus(item.status)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid decision") from exc

        target = DECISION_TARGET_STATUS[dec]
        previous = item.status
        item.reviewer_decision = dec.value
        new_status_value: str | None = None
        if target.value != previous and can_transition(current, target):
            item.status = target.value
            new_status_value = target.value
        item.updated_at = _now()
        await self._add_event(
            item,
            event_type=EventType.DECISION.value,
            actor=user.email,
            previous_status=previous,
            new_status=new_status_value,
            decision=dec.value,
            comment=comment,
        )
        return self.item_ui_payload(item, job)

    async def assign(
        self,
        user: User,
        project_uuid: UUID,
        item_id: UUID,
        assigned_to: str,
    ) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        item = await self._get_item_for_job(job.id, item_id)
        item.assigned_to = assigned_to
        item.updated_at = _now()
        await self._add_event(
            item,
            event_type=EventType.ASSIGNMENT.value,
            actor=user.email,
            comment=f"Asignado a {assigned_to}",
        )
        return self.item_ui_payload(item, job)

    async def add_comment(
        self,
        user: User,
        project_uuid: UUID,
        item_id: UUID,
        comment: str,
    ) -> dict[str, Any]:
        job = await self._latest_completed_job(user, project_uuid)
        item = await self._get_item_for_job(job.id, item_id)
        if comment.strip():
            if item.observation:
                item.observation = f"{item.observation}\n{comment.strip()}"
            else:
                item.observation = comment.strip()
        item.updated_at = _now()
        await self._add_event(
            item,
            event_type=EventType.COMMENT.value,
            actor=user.email,
            comment=comment,
        )
        return self.item_ui_payload(item, job)

    def resolve_tile(self, job: ProjectClashJob, filename: str) -> Path | None:
        if not job.output_dir or ".." in filename or "/" in filename or "\\" in filename:
            return None
        if not filename.endswith(".svg"):
            return None
        path = Path(job.output_dir) / "tiles" / filename
        return path if path.is_file() else None

    async def list_workflow_rows_for_export(
        self, user: User, project_uuid: UUID, job_id: UUID | None = None
    ) -> tuple[ProjectClashJob, list[ProjectClashItem]]:
        if job_id:
            job = await self._session.get(ProjectClashJob, job_id)
            project = await self._project_svc.get_project(user, project_uuid)
            if job is None or job.project_id != project.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        else:
            job = await self._latest_completed_job(user, project_uuid)
        await self.ensure_ingested(job, actor=user.email)
        result = await self._session.execute(
            select(ProjectClashItem)
            .where(ProjectClashItem.job_id == job.id)
            .order_by(ProjectClashItem.priority, ProjectClashItem.clash_code)
        )
        return job, list(result.scalars().all())
