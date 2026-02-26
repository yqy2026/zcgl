"""Asset management-party history model."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .asset import Asset
    from .party import Party


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AssetManagementHistory(Base):
    """经营方历史记录。"""

    __tablename__ = "asset_management_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="资产ID",
    )
    manager_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="经营管理主体ID",
    )
    start_date: Mapped[date | None] = mapped_column(Date, comment="生效日期")
    end_date: Mapped[date | None] = mapped_column(Date, comment="结束日期")
    agreement: Mapped[str | None] = mapped_column(String(500), comment="协议文件/编号")
    change_reason: Mapped[str | None] = mapped_column(String(500), comment="变更原因")
    changed_by: Mapped[str | None] = mapped_column(String(100), comment="变更人")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
        comment="更新时间",
    )

    asset: Mapped["Asset"] = relationship("Asset")
    manager_party: Mapped["Party"] = relationship("Party")

    def __repr__(self) -> str:
        return (
            f"<AssetManagementHistory(asset_id={self.asset_id}, "
            f"manager_party_id={self.manager_party_id})>"
        )


__all__ = ["AssetManagementHistory"]
