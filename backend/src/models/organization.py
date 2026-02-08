"""
组织架构相关数据库模型
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship

from ..database import Base


class Organization(Base):
    """组织架构模型"""

    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(200), nullable=False, comment="组织名称")
    code = Column(String(50), nullable=False, comment="组织编码")
    level = Column(Integer, nullable=False, default=1, comment="组织层级")
    sort_order = Column(Integer, default=0, comment="排序")

    # 组织基本信息
    type = Column(String(20), nullable=False, comment="组织类型")
    status = Column(String(20), nullable=False, default="active", comment="状态")

    # 层级关系
    parent_id = Column(String, ForeignKey("organizations.id"), comment="上级组织ID")
    path = Column(String(1000), comment="组织路径，用/分隔")

    # 描述信息
    description = Column(Text, comment="组织描述")

    # 系统信息
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")

    # 时间信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")

    # 关系定义
    parent: Mapped["Organization | None"] = relationship(
        "Organization", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"  # pragma: no cover


class OrganizationHistory(Base):
    """组织架构变更历史"""

    __tablename__ = "organization_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=False, comment="组织ID"
    )

    # 变更信息
    action = Column(
        String(20), nullable=False, comment="操作类型(create/update/delete)"
    )
    field_name = Column(String(100), comment="变更字段")
    old_value = Column(Text, comment="原值")
    new_value = Column(Text, comment="新值")
    change_reason = Column(String(500), comment="变更原因")

    # 操作信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="操作时间"
    )
    created_by = Column(String(100), comment="操作人")

    # 关系
    organization: Mapped["Organization"] = relationship("Organization")

    def __repr__(self) -> str:
        return f"<OrganizationHistory(id={self.id}, action={self.action})>"  # pragma: no cover
