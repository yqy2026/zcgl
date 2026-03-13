"""资产审核审计日志模型。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .asset import Asset


class AssetReviewLog(Base):
    """资产审核状态流转日志。"""

    __tablename__ = "asset_review_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    asset_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
        comment="关联资产 ID",
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="动作：submit/approve/reject/reverse/resubmit",
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
        comment="驳回/反审核原因",
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="附加上下文信息",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="创建时间",
    )

    asset: Mapped[Asset] = relationship(
        "Asset",
        back_populates="review_logs",
    )
