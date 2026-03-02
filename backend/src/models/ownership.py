"""
权属方模型
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .project_relations import ProjectOwnershipRelation


class Ownership(Base):
    """权属方模型"""

    __tablename__ = "ownerships"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="权属方全称")
    code: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="权属方编码"
    )
    short_name: Mapped[str | None] = mapped_column(String(100), comment="权属方简称")
    # 以下字段已删除: contact_person, contact_phone, contact_email, registration_number, legal_representative, business_scope, established_date, registered_capital
    address: Mapped[str | None] = mapped_column(String(500), comment="地址")
    management_entity: Mapped[str | None] = mapped_column(
        String(200), comment="管理单位"
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 系统字段
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="状态"
    )
    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态"
    )

    # 时间戳
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

    # 关联关系
    ownership_relations: Mapped[list["ProjectOwnershipRelation"]] = relationship(
        "ProjectOwnershipRelation",
        back_populates="ownership",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Ownership(id={self.id}, name={self.name}, code={self.code})>"


__all__ = ["Ownership"]
