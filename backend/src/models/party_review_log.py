"""主体审核审计日志模型。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .party import Party


class PartyReviewLog(Base):
    """主体审核状态流转日志。"""

    __tablename__ = "party_review_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="关联主体 ID",
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="动作：submit/approve/reject",
    )
    from_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="变更前审核状态",
    )
    to_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="变更后审核状态",
    )
    operator: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="操作人",
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="驳回原因",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="创建时间",
    )

    party: Mapped[Party] = relationship(
        "Party",
        back_populates="review_logs",
    )
