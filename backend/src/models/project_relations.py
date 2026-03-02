"""项目与权属方关系模型。"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .ownership import Ownership
    from .project import Project


class ProjectOwnershipRelation(Base):
    """项目-权属方多对多关系表"""

    __tablename__ = "project_" + "ownership_relations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id"), index=True, nullable=False, comment="项目ID"
    )
    ownership_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ownerships.id"),
        index=True,
        nullable=False,
        comment="权属方ID",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否有效"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    project: Mapped["Project"] = relationship("Project")
    ownership: Mapped["Ownership"] = relationship(
        "Ownership", back_populates="ownership_relations"
    )

    def __repr__(self) -> str:
        return f"<ProjectOwnershipRelation(project_id={self.project_id}, ownership_id={self.ownership_id})>"


__all__ = ["ProjectOwnershipRelation"]
