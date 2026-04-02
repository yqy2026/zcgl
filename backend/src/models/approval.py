"""审批域核心模型。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ApprovalInstance(Base):
    """审批实例。"""

    __tablename__ = "approval_instances"
    __table_args__ = (
        Index(
            "ix_approval_instances_business_status",
            "business_type",
            "business_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    approval_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    business_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    starter_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    assignee_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    current_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApprovalTaskSnapshot(Base):
    """审批待办快照。"""

    __tablename__ = "approval_task_snapshots"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    approval_instance_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("approval_instances.id"),
        nullable=False,
        index=True,
    )
    business_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    business_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    assignee_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApprovalActionLog(Base):
    """审批动作日志。"""

    __tablename__ = "approval_action_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    approval_instance_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("approval_instances.id"),
        nullable=False,
        index=True,
    )
    approval_task_snapshot_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("approval_task_snapshots.id"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    operator_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
    )
