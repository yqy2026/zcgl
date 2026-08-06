"""Durable receipts for sensitive Party lifecycle commits."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class PartyLifecycleCommit(Base):
    """One idempotent, auditable Party activation-state change."""

    __tablename__ = "party_lifecycle_commits"
    __table_args__ = (
        UniqueConstraint(
            "party_id",
            "actor_id",
            "idempotency_key",
            name="uq_party_lifecycle_commit_request",
        ),
        Index("ix_party_lifecycle_commits_party_id", "party_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Target Party ID",
    )
    actor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Commit actor ID",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Idempotency key"
    )
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="deactivate or reactivate"
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False, comment="Reason")
    before_state: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Pre-commit state snapshot"
    )
    after_state: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Post-commit state snapshot"
    )
    impact_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Impact summary"
    )
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Idempotent response snapshot"
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="Commit timestamp"
    )


__all__ = ["PartyLifecycleCommit"]
