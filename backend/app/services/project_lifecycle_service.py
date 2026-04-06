from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.domain.workflow_phase import LINEAR_NEXT, WorkflowPhase
from app.models.architecture_revision import ArchitectureRevision, ArchitectureRevisionDecision
from app.models.project import Project
from app.models.project_event import ProjectEvent
from app.models.project_file import ProjectFile
from app.models.subcontract_quote import SubcontractQuote, SubcontractQuoteLine
from app.models.user import User, UserRole
from app.models.user_notification import UserNotification
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.project_service import ProjectService


class ProjectLifecycleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectRepository(session)
        self._users = UserRepository(session)
        self._project_svc = ProjectService(session)
        self._settings = get_settings()

    async def _load_project_full(self, project_uuid: UUID) -> Optional[Project]:
        result = await self._session.execute(
            select(Project)
            .options(
                selectinload(Project.architecture_data),
                selectinload(Project.subcontract_quotes).selectinload(SubcontractQuote.lines),
            )
            .where(Project.id == project_uuid)
        )
        return result.scalar_one_or_none()

    async def _sync_subcontracts_flag(self, project: Project) -> None:
        meta = dict(project.workflow_meta or {})
        bp = _budget_pipeline(meta)
        has = False
        for q in project.subcontract_quotes:
            if len(q.lines) > 0:
                has = True
                break
        bp["subcontracts_done"] = has
        _set_budget_pipeline(meta, bp)
        project.workflow_meta = meta

    def _bootstrap_required_ok(self, project: Project) -> bool:
        criteria = project.project_bootstrap_criteria or []
        if not isinstance(criteria, list):
            return False
        for item in criteria:
            if not isinstance(item, dict):
                continue
            if item.get("required") and not item.get("done"):
                return False
        return len(criteria) > 0

    async def _latest_revision(self, project_id: UUID) -> Optional[ArchitectureRevision]:
        q = (
            select(ArchitectureRevision)
            .where(ArchitectureRevision.project_id == project_id)
            .order_by(ArchitectureRevision.version.desc())
            .limit(1)
        )
        return (await self._session.execute(q)).scalar_one_or_none()

    async def _next_revision_version(self, project_id: UUID) -> int:
        q = select(func.coalesce(func.max(ArchitectureRevision.version), 0)).where(
            ArchitectureRevision.project_id == project_id
        )
        v = (await self._session.execute(q)).scalar_one()
        return int(v) + 1

    async def _assert_transition_guards(
        self,
        user: User,
        project: Project,
        target: WorkflowPhase,
    ) -> None:
        current = WorkflowPhase(project.workflow_phase)
        if current == WorkflowPhase.BOOTSTRAPPING and target == WorkflowPhase.AWAITING_FILES:
            if not self._bootstrap_required_ok(project):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Completa el checklist de documentos requeridos antes de continuar",
                )
        if current == WorkflowPhase.AWAITING_FILES and target == WorkflowPhase.FILES_INGESTED:
            n = await self._projects.count_project_files(project.id)
            if n < 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Sube al menos un archivo de plano antes de continuar",
                )
        if current == WorkflowPhase.ARCHITECTURE_REVIEW and target == WorkflowPhase.SPECIFICATIONS:
            rev = await self._latest_revision(project.id)
            if rev is None or rev.decision != ArchitectureRevisionDecision.APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Se requiere una revisión de arquitectura aprobada",
                )
        if current == WorkflowPhase.SPECIFICATIONS and target == WorkflowPhase.BUDGETING_PIPELINE:
            spec = project.specifications_document or {}
            summary = (spec.get("summary") or "").strip() if isinstance(spec, dict) else ""
            if len(summary) < 10:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Completa el pliego de condiciones (resumen mínimo 10 caracteres) antes de presupuesto",
                )
        if current == WorkflowPhase.BUDGETING_PIPELINE and target == WorkflowPhase.BUDGET_APPROVED:
            if user.role != UserRole.MASTER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo MASTER puede marcar presupuesto aprobado por el cliente",
                )
            await self._sync_subcontracts_flag(project)
            meta = dict(project.workflow_meta or {})
            bp = _budget_pipeline(meta)
            if not (
                bp.get("subcontracts_done")
                and bp.get("volumetry_done")
                and bp.get("cost_analysis_done")
                and bp.get("budget_marked_complete")
                and (bp.get("client_approved_version_label") or "").strip()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Completa el pipeline de presupuesto y la versión aprobada por el cliente",
                )

    async def transition_phase(
        self,
        user: User,
        project_uuid: UUID,
        target_phase: WorkflowPhase,
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        current = WorkflowPhase(project.workflow_phase)
        expected = LINEAR_NEXT.get(current)
        if expected is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El proyecto ya está en la fase final",
            )
        if expected != target_phase:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transición inválida: la siguiente fase es {expected.value}",
            )
        await self._assert_transition_guards(user, project, target_phase)
        prev = project.workflow_phase
        project.workflow_phase = target_phase.value
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="WORKFLOW_TRANSITION",
            payload={"from_phase": prev, "to_phase": target_phase.value},
        )
        if target_phase == WorkflowPhase.SPECIFICATIONS:
            await self._notify_architecture_complete(project)
        if target_phase == WorkflowPhase.BUDGET_APPROVED:
            await self._notify_budget_approved(project)
        await self._session.flush()
        return project

    async def _notify_architecture_complete(self, project: Project) -> None:
        mids = await self._users.list_ids_by_module_and_roles(
            self._settings.architecture_module_id,
            [UserRole.MASTER, UserRole.COORDINATOR],
        )
        title = "Fase de arquitectura completada"
        body = f"El proyecto «{project.name}» completó la definición arquitectónica."
        for uid in mids:
            self._session.add(
                UserNotification(
                    user_id=uid,
                    project_id=project.id,
                    kind="ARCHITECTURE_PHASE_COMPLETE",
                    title=title,
                    body=body,
                    created_at=datetime.now(timezone.utc),
                )
            )
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=None,
            event_type="NOTIFICATION_ARCHITECTURE_COMPLETE",
            payload={"recipient_count": len(mids)},
        )

    async def _notify_budget_approved(self, project: Project) -> None:
        mids = await self._users.list_ids_by_module_and_roles(
            self._settings.architecture_module_id,
            [UserRole.MASTER],
        )
        title = "Presupuesto aprobado por el cliente"
        body = f"El proyecto «{project.name}» tiene una versión de presupuesto aprobada."
        for uid in mids:
            self._session.add(
                UserNotification(
                    user_id=uid,
                    project_id=project.id,
                    kind="BUDGET_APPROVED",
                    title=title,
                    body=body,
                    created_at=datetime.now(timezone.utc),
                )
            )
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=None,
            event_type="NOTIFICATION_BUDGET_APPROVED",
            payload={"recipient_count": len(mids)},
        )

    async def update_project_meta(
        self,
        user: User,
        project_uuid: UUID,
        *,
        name: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        if name is not None:
            project.name = name.strip()
        if client_name is not None:
            project.client_name = client_name.strip() or None
        await self._session.flush()
        return project

    async def put_bootstrap_criteria(
        self,
        user: User,
        project_uuid: UUID,
        criteria: list[dict[str, Any]],
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        if WorkflowPhase(project.workflow_phase) != WorkflowPhase.BOOTSTRAPPING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El checklist solo es editable en fase BOOTSTRAPPING",
            )
        project.project_bootstrap_criteria = criteria
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="BOOTSTRAP_UPDATED",
            payload={"items": len(criteria)},
        )
        await self._session.flush()
        return project

    async def put_specifications(
        self,
        user: User,
        project_uuid: UUID,
        document: dict[str, Any],
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        wf = WorkflowPhase(project.workflow_phase)
        allowed = {
            WorkflowPhase.ARCHITECTURE_REVIEW,
            WorkflowPhase.SPECIFICATIONS,
            WorkflowPhase.BUDGETING_PIPELINE,
            WorkflowPhase.BUDGET_APPROVED,
        }
        if wf not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El pliego de condiciones no es editable en esta fase",
            )
        project.specifications_document = document
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="SPECIFICATIONS_UPDATED",
            payload={},
        )
        await self._session.flush()
        return project

    async def patch_workflow_meta(
        self,
        user: User,
        project_uuid: UUID,
        patch: dict[str, Any],
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        meta = dict(project.workflow_meta or {})
        if "budget_pipeline" in patch and isinstance(patch["budget_pipeline"], dict):
            bp = _budget_pipeline(meta)
            bp.update(patch["budget_pipeline"])
            _set_budget_pipeline(meta, bp)
        project.workflow_meta = meta
        p = await self._load_project_full(project_uuid)
        if p is not None:
            await self._sync_subcontracts_flag(p)
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="WORKFLOW_META_PATCHED",
            payload={"keys": list(patch.keys())},
        )
        await self._session.flush()
        return await self._project_svc.get_project(user, project_uuid)

    async def list_events(self, user: User, project_uuid: UUID) -> list[ProjectEvent]:
        project = await self._project_svc.get_project(user, project_uuid)
        q = (
            select(ProjectEvent)
            .where(ProjectEvent.project_id == project.id)
            .order_by(ProjectEvent.created_at.desc())
            .limit(200)
        )
        return list((await self._session.execute(q)).scalars().all())

    async def create_architecture_revision(
        self,
        user: User,
        project_uuid: UUID,
        *,
        decision: ArchitectureRevisionDecision,
        notes: Optional[str],
        checklist: dict[str, Any],
    ) -> ArchitectureRevision:
        project = await self._project_svc.get_project(user, project_uuid)
        if WorkflowPhase(project.workflow_phase) != WorkflowPhase.ARCHITECTURE_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Revisiones solo en fase ARCHITECTURE_REVIEW",
            )
        ver = await self._next_revision_version(project.id)
        rev = ArchitectureRevision(
            id=uuid.uuid4(),
            project_id=project.id,
            version=ver,
            decision=decision,
            notes=notes,
            checklist=checklist or {},
            checked_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(rev)
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="ARCHITECTURE_REVISION",
            payload={"version": ver, "decision": decision.value},
        )
        await self._session.flush()
        await self._session.refresh(rev)
        return rev

    async def list_architecture_revisions(self, user: User, project_uuid: UUID) -> list[ArchitectureRevision]:
        project = await self._project_svc.get_project(user, project_uuid)
        q = (
            select(ArchitectureRevision)
            .where(ArchitectureRevision.project_id == project.id)
            .order_by(ArchitectureRevision.version.asc())
        )
        return list((await self._session.execute(q)).scalars().all())

    async def upload_file(
        self,
        user: User,
        project_uuid: UUID,
        upload: UploadFile,
        category: Optional[str],
    ) -> ProjectFile:
        project = await self._project_svc.get_project(user, project_uuid)
        wf = WorkflowPhase(project.workflow_phase)
        if wf not in (
            WorkflowPhase.AWAITING_FILES,
            WorkflowPhase.FILES_INGESTED,
            WorkflowPhase.ARCHITECTURE_REVIEW,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se aceptan archivos en esta fase",
            )
        raw = await upload.read()
        if len(raw) > 50 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Archivo demasiado grande")
        fid = uuid.uuid4()
        root = Path(self._settings.upload_root)
        dest_dir = root / str(project.id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(upload.filename or "file").name.replace("..", "_")
        storage_key = str(dest_dir / f"{fid}_{safe_name}")
        Path(storage_key).write_bytes(raw)
        pf = ProjectFile(
            id=fid,
            project_id=project.id,
            storage_key=storage_key,
            original_name=upload.filename or "file",
            mime=upload.content_type,
            category=category,
            created_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(pf)
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="FILE_UPLOADED",
            payload={"file_uuid": str(fid), "name": pf.original_name},
        )
        await self._session.flush()
        await self._session.refresh(pf)
        return pf

    async def list_files(self, user: User, project_uuid: UUID) -> list[ProjectFile]:
        project = await self._project_svc.get_project(user, project_uuid)
        q = (
            select(ProjectFile)
            .where(ProjectFile.project_id == project.id)
            .order_by(ProjectFile.created_at.desc())
        )
        return list((await self._session.execute(q)).scalars().all())

    async def get_file_path(self, user: User, project_uuid: UUID, file_uuid: UUID) -> tuple[ProjectFile, Path]:
        project = await self._project_svc.get_project(user, project_uuid)
        pf = await self._session.get(ProjectFile, file_uuid)
        if pf is None or pf.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
        return pf, Path(pf.storage_key)

    async def list_subcontract_quotes(self, user: User, project_uuid: UUID) -> list[SubcontractQuote]:
        project = await self._project_svc.get_project(user, project_uuid)
        q = (
            select(SubcontractQuote)
            .options(selectinload(SubcontractQuote.lines))
            .where(SubcontractQuote.project_id == project.id)
            .order_by(SubcontractQuote.created_at.desc())
        )
        return list((await self._session.execute(q)).scalars().all())

    async def create_subcontract_quote(
        self,
        user: User,
        project_uuid: UUID,
        title: Optional[str],
    ) -> SubcontractQuote:
        project = await self._project_svc.get_project(user, project_uuid)
        q = SubcontractQuote(
            id=uuid.uuid4(),
            project_id=project.id,
            title=title,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(q)
        await self._session.flush()
        await self._session.refresh(q, ["lines"])
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)
        return q

    async def add_subcontract_line(
        self,
        user: User,
        project_uuid: UUID,
        quote_uuid: UUID,
        *,
        item_label: str,
        provider: Optional[str],
        price: Decimal,
        currency: str,
        external_ref: Optional[str],
    ) -> SubcontractQuoteLine:
        project = await self._project_svc.get_project(user, project_uuid)
        quote = await self._session.get(SubcontractQuote, quote_uuid)
        if quote is None or quote.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotización no encontrada")
        line = SubcontractQuoteLine(
            id=uuid.uuid4(),
            quote_id=quote.id,
            item_label=item_label.strip(),
            provider=provider,
            price=price,
            currency=currency or "MXN",
            external_ref=external_ref,
        )
        self._session.add(line)
        await self._session.flush()
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)
        return line

    async def get_subcontract_quote_with_lines(
        self,
        user: User,
        project_uuid: UUID,
        quote_uuid: UUID,
    ) -> SubcontractQuote:
        project = await self._project_svc.get_project(user, project_uuid)
        q = await self._session.execute(
            select(SubcontractQuote)
            .options(selectinload(SubcontractQuote.lines))
            .where(
                SubcontractQuote.id == quote_uuid,
                SubcontractQuote.project_id == project.id,
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotización no encontrada")
        return row

    async def delete_subcontract_quote(self, user: User, project_uuid: UUID, quote_uuid: UUID) -> None:
        project = await self._project_svc.get_project(user, project_uuid)
        quote = await self._session.get(SubcontractQuote, quote_uuid)
        if quote is None or quote.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotización no encontrada")
        await self._session.delete(quote)
        await self._session.flush()
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)

    async def list_my_notifications(self, user: User, *, unread_only: bool) -> list[UserNotification]:
        q = select(UserNotification).where(UserNotification.user_id == user.id)
        if unread_only:
            q = q.where(UserNotification.read_at.is_(None))
        q = q.order_by(UserNotification.created_at.desc()).limit(100)
        return list((await self._session.execute(q)).scalars().all())

    async def mark_notification_read(self, user: User, notification_uuid: UUID) -> None:
        n = await self._session.get(UserNotification, notification_uuid)
        if n is None or n.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
        n.read_at = datetime.now(timezone.utc)
        await self._session.flush()


def _budget_pipeline_defaults() -> dict[str, Any]:
    return {
        "subcontracts_done": False,
        "volumetry_done": False,
        "cost_analysis_done": False,
        "budget_marked_complete": False,
        "client_approved_version_label": None,
        "volumetry": {},
        "cost_analysis": {},
        "budget_versions": [],
    }


def _budget_pipeline(meta: dict[str, Any]) -> dict[str, Any]:
    raw = meta.get("budget_pipeline")
    base = _budget_pipeline_defaults()
    if not isinstance(raw, dict):
        return dict(base)
    merged = dict(base)
    merged.update(raw)
    return merged


def _set_budget_pipeline(meta: dict[str, Any], bp: dict[str, Any]) -> None:
    meta["budget_pipeline"] = bp
