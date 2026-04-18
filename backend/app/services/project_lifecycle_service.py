from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.domain.file_discipline import FileIngestStatus, parse_discipline
from app.domain.project_updated import touch_project_updated_at
from app.domain.task_board_constants import TASK_LIST_DONE_UUID
from app.domain.workflow_phase import LINEAR_NEXT, LINEAR_PREV, WorkflowPhase
from app.models.architecture_revision import ArchitectureRevision, ArchitectureRevisionDecision
from app.models.project import Project
from app.models.task_board import TaskCard
from app.models.project_event import ProjectEvent
from app.models.project_file import ProjectFile
from app.models.project_file_folder import ProjectFileFolder
from app.models.subcontract_quote import SubcontractQuote, SubcontractQuoteLine
from app.models.user import User, UserRole
from app.models.user_notification import UserNotification
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.project_file_ai_service import ProjectFileAIService
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
        _user: User,
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
        if current == WorkflowPhase.AWAITING_FILES and target == WorkflowPhase.ARCHITECTURE_REVIEW:
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
        if current == WorkflowPhase.BUDGETING_PIPELINE and target == WorkflowPhase.MANAGEMENT_APPROVAL:
            await self._sync_subcontracts_flag(project)
            meta = dict(project.workflow_meta or {})
            bp = _budget_pipeline(meta)
            if not (
                bp.get("subcontracts_done")
                and bp.get("volumetry_done")
                and bp.get("cost_analysis_done")
                and bp.get("budget_marked_complete")
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Completa el pipeline de presupuesto antes de enviar a gerencia",
                )
        if current == WorkflowPhase.MANAGEMENT_APPROVAL and target == WorkflowPhase.BUDGET_APPROVED:
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

    async def _count_pending_tasks_for_project(self, project_id: UUID) -> int:
        q = (
            select(func.count())
            .select_from(TaskCard)
            .where(
                TaskCard.project_id == project_id,
                TaskCard.archived.is_(False),
                TaskCard.list_id != TASK_LIST_DONE_UUID,
            )
        )
        return int((await self._session.execute(q)).scalar_one())

    async def transition_phase(
        self,
        user: User,
        project_uuid: UUID,
        target_phase: WorkflowPhase,
    ) -> Project:
        project = await self._project_svc.get_project(user, project_uuid)
        current = WorkflowPhase(project.workflow_phase)
        expected_next = LINEAR_NEXT.get(current)
        expected_prev = LINEAR_PREV.get(current)

        is_forward = expected_next == target_phase
        is_backward = expected_prev == target_phase

        if not is_forward and not is_backward:
            hint = expected_next.value if expected_next is not None else None
            prev_hint = expected_prev.value if expected_prev is not None else None
            parts = []
            if hint is not None:
                parts.append(f"siguiente válida: {hint}")
            if prev_hint is not None:
                parts.append(f"anterior válida: {prev_hint}")
            detail = "Transición inválida."
            if parts:
                detail = f"Transición inválida ({'; '.join(parts)})."
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

        if is_forward:
            pending = await self._count_pending_tasks_for_project(project.id)
            if pending > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Hay tareas del proyecto pendientes en el tablero (fuera de «Hecho»). "
                        "Complétalas o archívalas antes de avanzar de fase."
                    ),
                )
            await self._assert_transition_guards(user, project, target_phase)

        prev = project.workflow_phase
        project.workflow_phase = target_phase.value
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="WORKFLOW_TRANSITION",
            payload={
                "from_phase": prev,
                "to_phase": target_phase.value,
                "direction": "forward" if is_forward else "backward",
            },
        )
        if is_forward:
            if target_phase == WorkflowPhase.SPECIFICATIONS:
                await self._notify_architecture_complete(project)
            if target_phase == WorkflowPhase.BUDGET_APPROVED:
                await self._notify_budget_approved(project)
        touch_project_updated_at(project)
        await self._session.flush()
        return project

    async def _notify_architecture_complete(self, project: Project) -> None:
        mids = await self._users.list_ids_by_module_and_roles(
            self._settings.architecture_module_id,
            [UserRole.GERENCIA, UserRole.CONTROL],
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
            [UserRole.GERENCIA],
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
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = {"from": project.name, "to": name.strip()}
            project.name = name.strip()
        if client_name is not None:
            prev = project.client_name
            nxt = client_name.strip() or None
            payload["client_name"] = {"from": prev, "to": nxt}
            project.client_name = nxt
        if payload:
            await self._projects.record_event(
                project_id=project.id,
                actor_user_id=user.id,
                event_type="PROJECT_META_UPDATED",
                payload=payload,
            )
        touch_project_updated_at(project)
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
        touch_project_updated_at(project)
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
            WorkflowPhase.MANAGEMENT_APPROVAL,
            WorkflowPhase.BUDGET_APPROVED,
        }
        if wf not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El pliego de condiciones no es editable en esta fase",
            )
        project.specifications_document = document
        summary = ""
        if isinstance(document, dict):
            summary = str((document.get("summary") or "")).strip()
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="SPECIFICATIONS_UPDATED",
            payload={"summary_chars": len(summary)},
        )
        touch_project_updated_at(project)
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
        if p is not None:
            touch_project_updated_at(p)
        else:
            touch_project_updated_at(project)
        await self._session.flush()
        return await self._project_svc.get_project(user, project_uuid)

    async def list_events_page(
        self,
        user: User,
        project_uuid: UUID,
        *,
        limit: int,
        offset: int,
        event_type: Optional[str],
        q: Optional[str],
    ) -> tuple[list[ProjectEvent], int]:
        project = await self._project_svc.get_project(user, project_uuid)
        conditions = [ProjectEvent.project_id == project.id]
        if event_type and event_type.strip():
            conditions.append(ProjectEvent.event_type == event_type.strip())
        q_clean = (q or "").strip()
        if q_clean:
            pat = f"%{q_clean}%"
            conditions.append(
                or_(
                    cast(ProjectEvent.payload, Text).ilike(pat),
                    User.email.ilike(pat),
                )
            )
        base = and_(*conditions)
        count_stmt = (
            select(func.count())
            .select_from(ProjectEvent)
            .outerjoin(User, User.id == ProjectEvent.actor_user_id)
            .where(base)
        )
        total = int((await self._session.execute(count_stmt)).scalar_one() or 0)
        stmt = (
            select(ProjectEvent)
            .outerjoin(User, User.id == ProjectEvent.actor_user_id)
            .where(base)
            .order_by(ProjectEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(ProjectEvent.actor))
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return rows, total

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
        touch_project_updated_at(project)
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

    async def _require_folder_in_project(self, project_id: UUID, folder_uuid: UUID) -> UUID:
        row = await self._session.get(ProjectFileFolder, folder_uuid)
        if row is None or row.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carpeta no encontrada")
        return row.id

    async def _folder_is_descendant_of(self, folder_id: UUID, ancestor_id: UUID) -> bool:
        cur = await self._session.get(ProjectFileFolder, folder_id)
        while cur is not None:
            if cur.id == ancestor_id:
                return True
            if cur.parent_id is None:
                return False
            cur = await self._session.get(ProjectFileFolder, cur.parent_id)
        return False

    async def upload_file(
        self,
        user: User,
        project_uuid: UUID,
        upload: UploadFile,
        category: Optional[str],
        *,
        folder_uuid: Optional[UUID] = None,
        wizard: bool = False,
    ) -> ProjectFile:
        project = await self._project_svc.get_project(user, project_uuid)
        wf = WorkflowPhase(project.workflow_phase)
        if wf not in (
            WorkflowPhase.AWAITING_FILES,
            WorkflowPhase.ARCHITECTURE_REVIEW,
            WorkflowPhase.SPECIFICATIONS,
            WorkflowPhase.BUDGETING_PIPELINE,
            WorkflowPhase.MANAGEMENT_APPROVAL,
            WorkflowPhase.BUDGET_APPROVED,
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

        resolved_folder_id: Optional[UUID] = None
        if folder_uuid is not None:
            resolved_folder_id = await self._require_folder_in_project(project.id, folder_uuid)

        pf = ProjectFile(
            id=fid,
            project_id=project.id,
            storage_key=storage_key,
            original_name=upload.filename or "file",
            mime=upload.content_type,
            category=category,
            folder_id=resolved_folder_id,
            created_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        if wizard:
            ai = ProjectFileAIService()
            disc, desc, _used = await ai.suggest(pf.original_name, pf.mime)
            pf.discipline = disc.value if disc else None
            pf.description = desc if desc else None
            pf.ingest_status = FileIngestStatus.DRAFT.value
        else:
            pf.ingest_status = FileIngestStatus.PUBLISHED.value

        self._session.add(pf)
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="FILE_UPLOADED",
            payload={"file_uuid": str(fid), "name": pf.original_name},
        )
        touch_project_updated_at(project)
        await self._session.flush()
        await self._session.refresh(pf)
        return pf

    async def list_files(
        self,
        user: User,
        project_uuid: UUID,
        folder_uuid: Optional[UUID] = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProjectFile], int]:
        project = await self._project_svc.get_project(user, project_uuid)
        if folder_uuid is not None:
            await self._require_folder_in_project(project.id, folder_uuid)
        conds = [ProjectFile.project_id == project.id]
        if folder_uuid is None:
            conds.append(ProjectFile.folder_id.is_(None))
        else:
            conds.append(ProjectFile.folder_id == folder_uuid)
        where_clause = and_(*conds)
        count_q = select(func.count()).select_from(ProjectFile).where(where_clause)
        total = int((await self._session.execute(count_q)).scalar_one())
        q = (
            select(ProjectFile)
            .where(where_clause)
            .order_by(ProjectFile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self._session.execute(q)).scalars().all())
        return rows, total

    async def _folder_path_parts(self, project_id: UUID, folder_id: Optional[UUID]) -> list[str]:
        if folder_id is None:
            return []
        parts: list[str] = []
        cur: Optional[UUID] = folder_id
        for _ in range(128):
            if cur is None:
                break
            row = await self._session.get(ProjectFileFolder, cur)
            if row is None or row.project_id != project_id:
                break
            parts.append(row.name)
            cur = row.parent_id
        parts.reverse()
        return parts

    async def search_project_files(
        self,
        user: User,
        project_uuid: UUID,
        q_raw: Optional[str],
        discipline_raw: Optional[str],
    ) -> list[tuple[ProjectFile, str]]:
        project = await self._project_svc.get_project(user, project_uuid)
        has_q = bool(q_raw and q_raw.strip())
        has_d = bool(discipline_raw and discipline_raw.strip())
        if not has_q and not has_d:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Indica al menos un criterio: q (texto) o discipline",
            )
        stmt = select(ProjectFile).where(ProjectFile.project_id == project.id)
        if has_d:
            d = parse_discipline(discipline_raw.strip())
            if d is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="discipline no válida",
                )
            stmt = stmt.where(ProjectFile.discipline == d.value)
        if has_q:
            term = f"%{q_raw.strip()}%"
            stmt = stmt.where(
                or_(
                    ProjectFile.original_name.ilike(term),
                    ProjectFile.description.ilike(term),
                )
            )
        stmt = stmt.order_by(ProjectFile.created_at.desc())
        rows = list((await self._session.execute(stmt)).scalars().all())
        out: list[tuple[ProjectFile, str]] = []
        for pf in rows:
            parts = await self._folder_path_parts(project.id, pf.folder_id)
            path_display = "Raíz" if not parts else "Raíz / " + " / ".join(parts)
            out.append((pf, path_display))
        return out

    async def list_file_folders(
        self,
        user: User,
        project_uuid: UUID,
        parent_uuid: Optional[UUID],
    ) -> list[ProjectFileFolder]:
        project = await self._project_svc.get_project(user, project_uuid)
        q = select(ProjectFileFolder).where(ProjectFileFolder.project_id == project.id)
        if parent_uuid is None:
            q = q.where(ProjectFileFolder.parent_id.is_(None))
        else:
            await self._require_folder_in_project(project.id, parent_uuid)
            q = q.where(ProjectFileFolder.parent_id == parent_uuid)
        q = q.order_by(ProjectFileFolder.name.asc())
        return list((await self._session.execute(q)).scalars().all())

    async def create_file_folder(
        self,
        user: User,
        project_uuid: UUID,
        name: str,
        parent_uuid: Optional[UUID],
    ) -> ProjectFileFolder:
        project = await self._project_svc.get_project(user, project_uuid)
        parent_id: Optional[UUID] = None
        if parent_uuid is not None:
            parent_id = await self._require_folder_in_project(project.id, parent_uuid)
        row = ProjectFileFolder(
            id=uuid.uuid4(),
            project_id=project.id,
            parent_id=parent_id,
            name=name.strip(),
            created_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        touch_project_updated_at(project)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def patch_file_folder(
        self,
        user: User,
        project_uuid: UUID,
        folder_uuid: UUID,
        patch: dict[str, Any],
    ) -> ProjectFileFolder:
        project = await self._project_svc.get_project(user, project_uuid)
        row = await self._session.get(ProjectFileFolder, folder_uuid)
        if row is None or row.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carpeta no encontrada")

        if "parent_uuid" in patch:
            raw_parent = patch["parent_uuid"]
            if raw_parent is None:
                row.parent_id = None
            else:
                if raw_parent == folder_uuid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La carpeta no puede ser padre de sí misma",
                    )
                new_parent = await self._require_folder_in_project(project.id, raw_parent)
                if await self._folder_is_descendant_of(new_parent, folder_uuid):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No se puede mover una carpeta dentro de su propia jerarquía",
                    )
                row.parent_id = new_parent

        if "name" in patch and patch["name"] is not None:
            row.name = str(patch["name"]).strip()

        touch_project_updated_at(project)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete_file_folder(self, user: User, project_uuid: UUID, folder_uuid: UUID) -> None:
        project = await self._project_svc.get_project(user, project_uuid)
        row = await self._session.get(ProjectFileFolder, folder_uuid)
        if row is None or row.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carpeta no encontrada")
        sub = await self._session.execute(
            select(func.count()).select_from(ProjectFileFolder).where(ProjectFileFolder.parent_id == row.id)
        )
        if sub.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La carpeta contiene subcarpetas",
            )
        fc = await self._session.execute(
            select(func.count()).select_from(ProjectFile).where(ProjectFile.folder_id == row.id)
        )
        if fc.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La carpeta contiene archivos",
            )
        await self._session.delete(row)
        touch_project_updated_at(project)

    async def patch_project_file(
        self,
        user: User,
        project_uuid: UUID,
        file_uuid: UUID,
        patch: dict[str, Any],
    ) -> ProjectFile:
        project = await self._project_svc.get_project(user, project_uuid)
        pf = await self._session.get(ProjectFile, file_uuid)
        if pf is None or pf.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")

        if "description" in patch:
            pf.description = patch["description"]

        if "discipline" in patch:
            raw = patch["discipline"]
            if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                pf.discipline = None
            elif isinstance(raw, str):
                d = parse_discipline(raw)
                if d is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="discipline no válida",
                    )
                pf.discipline = d.value

        if "folder_uuid" in patch:
            fu = patch["folder_uuid"]
            if fu is None:
                pf.folder_id = None
            else:
                pf.folder_id = await self._require_folder_in_project(project.id, fu)

        if "ingest_status" in patch and patch["ingest_status"] is not None:
            s = str(patch["ingest_status"]).strip().upper()
            if s not in (FileIngestStatus.DRAFT.value, FileIngestStatus.PUBLISHED.value):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="ingest_status debe ser DRAFT o PUBLISHED",
                )
            pf.ingest_status = s

        touch_project_updated_at(project)
        await self._session.flush()
        await self._session.refresh(pf)
        return pf

    async def delete_project_file(self, user: User, project_uuid: UUID, file_uuid: UUID) -> None:
        project = await self._project_svc.get_project(user, project_uuid)
        pf = await self._session.get(ProjectFile, file_uuid)
        if pf is None or pf.project_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
        path = Path(pf.storage_key)
        await self._session.delete(pf)
        if path.is_file():
            path.unlink()
        touch_project_updated_at(project)

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
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="SUBCONTRACT_QUOTE_CREATED",
            payload={"quote_uuid": str(q.id), "title": q.title},
        )
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)
            touch_project_updated_at(p2)
        else:
            touch_project_updated_at(project)
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
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="SUBCONTRACT_LINE_ADDED",
            payload={
                "quote_uuid": str(quote.id),
                "line_uuid": str(line.id),
                "item_label": line.item_label,
                "price": str(line.price),
                "currency": line.currency,
            },
        )
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)
            touch_project_updated_at(p2)
        else:
            touch_project_updated_at(project)
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
        await self._projects.record_event(
            project_id=project.id,
            actor_user_id=user.id,
            event_type="SUBCONTRACT_QUOTE_DELETED",
            payload={"quote_uuid": str(quote.id), "title": quote.title},
        )
        await self._session.delete(quote)
        await self._session.flush()
        p2 = await self._load_project_full(project_uuid)
        if p2 is not None:
            await self._sync_subcontracts_flag(p2)
            touch_project_updated_at(p2)
        else:
            touch_project_updated_at(project)

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
