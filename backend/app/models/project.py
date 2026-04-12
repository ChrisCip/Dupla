from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.workflow_phase import WorkflowPhase


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    workflow_phase: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=WorkflowPhase.BOOTSTRAPPING.value,
    )
    workflow_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    project_bootstrap_criteria: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    specifications_document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="projects_created",
    )
    architecture_data: Mapped[Optional["ProjectArchitectureData"]] = relationship(
        back_populates="project",
        uselist=False,
    )
    events: Mapped[list["ProjectEvent"]] = relationship(
        "ProjectEvent",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["ProjectFile"]] = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    architecture_revisions: Mapped[list["ArchitectureRevision"]] = relationship(
        "ArchitectureRevision",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    subcontract_quotes: Mapped[list["SubcontractQuote"]] = relationship(
        "SubcontractQuote",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectArchitectureData(Base):
    __tablename__ = "project_architecture_data"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    materiales: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="architecture_data")
