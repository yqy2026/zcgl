"""Durable receipts for sensitive explicit user Party-scope batch commits."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserPartyScopeBatchCommit(Base):
    """Durable all-or-nothing receipt for user Party-scope batches."""

    __tablename__ = "user_party_scope_batch_commits"
    __table_args__ = (
        UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_user_party_scope_batch_commit_request",
        ),
        Index("ix_user_party_scope_batch_commits_actor_id", "actor_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    actor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="提交人ID",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="幂等键"
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False, comment="变更原因")
    proposal: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="批量用户主体范围提案"
    )
    before_scope: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="批量提交前范围快照"
    )
    after_scope: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="批量提交后范围快照"
    )
    impact_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="批量影响摘要"
    )
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="幂等返回结果快照"
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="提交时间"
    )


__all__ = ["UserPartyScopeBatchCommit"]
