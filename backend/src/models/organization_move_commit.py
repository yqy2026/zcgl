"""Durable receipts for sensitive Organization hierarchy moves."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class OrganizationMoveCommit(Base):
    """One idempotent, auditable Organization hierarchy move."""

    __tablename__ = "organization_move_commits"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "actor_id",
            "idempotency_key",
            name="uq_organization_move_commit_request",
        ),
        Index("ix_organization_move_commits_organization_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Moved organization ID",
    )
    target_parent_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Target parent organization ID, or null for a root move",
    )
    actor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Submitting actor ID",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Idempotency key"
    )
    reason: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Move reason"
    )
    proposal: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Normalized move proposal"
    )
    before_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Scope before the move"
    )
    after_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Scope after the move"
    )
    impact_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Move impact summary"
    )
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="First commit response snapshot"
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="Committed at"
    )


__all__ = ["OrganizationMoveCommit"]
