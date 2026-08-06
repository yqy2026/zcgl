"""Durable receipts for sensitive human-user organization transfers."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserOrganizationTransferCommit(Base):
    """One idempotent, auditable human-user organization transfer."""

    __tablename__ = "user_organization_transfer_commits"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "actor_id",
            "idempotency_key",
            name="uq_user_organization_transfer_commit_request",
        ),
        Index("ix_user_organization_transfer_commits_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Target user ID",
    )
    actor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Submitting actor ID",
    )
    target_organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Target organization ID",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Idempotency key"
    )
    reason: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Transfer reason"
    )
    proposal: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Normalized transfer proposal"
    )
    before_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Scope before the transfer"
    )
    after_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Scope after the transfer"
    )
    impact_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Transfer impact summary"
    )
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="First commit response snapshot"
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="Committed at"
    )


__all__ = ["UserOrganizationTransferCommit"]
