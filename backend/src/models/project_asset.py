"""Project-asset relation model for time-bounded bindings."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ProjectAsset(Base):
    """Binding between project and asset with validity window."""

    __tablename__ = "project_assets"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_project_assets_valid_range",
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目ID",
    )
    asset_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="资产ID",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive, comment="生效时间"
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, comment="失效时间")
    bind_reason: Mapped[str | None] = mapped_column(String(500), comment="绑定原因")
    unbind_reason: Mapped[str | None] = mapped_column(
        String(500), comment="解绑原因"
    )
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

    def __repr__(self) -> str:
        return f"<ProjectAsset(project_id={self.project_id}, asset_id={self.asset_id})>"


__all__ = ["ProjectAsset"]
