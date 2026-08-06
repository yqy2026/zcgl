"""
组织架构相关数据库模型
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, relationship

from ..database import Base

if TYPE_CHECKING:
    from .party import Party


class RepresentedPartyPerspective(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"


class Organization(Base):
    """组织架构模型"""

    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("code", name="uq_organizations_code"),
        CheckConstraint(
            "(represented_party_id IS NULL AND "
            "represented_party_perspective IS NULL) OR "
            "(represented_party_id IS NOT NULL AND "
            "represented_party_perspective IS NOT NULL)",
            name="ck_organizations_represented_party_pair",
        ),
        CheckConstraint(
            "represented_party_perspective IS NULL OR "
            "represented_party_perspective IN ('owner', 'manager')",
            name="ck_organizations_represented_party_perspective",
        ),
        Index("ix_organizations_represented_party_id", "represented_party_id"),
    )

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
    represented_party_id = Column(
        String,
        ForeignKey("parties.id", ondelete="RESTRICT"),
        nullable=True,
        comment="直接代表的法人主体",
    )
    represented_party_perspective = Column(
        String(20), nullable=True, comment="默认产权方或运营方视角"
    )

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
    represented_party: Mapped["Party | None"] = relationship("Party")

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


class OrganizationPartyScopeCommit(Base):
    """Durable receipt for an Organization represented-Party scope commit."""

    __tablename__ = "organization_party_scope_commits"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "actor_id",
            "idempotency_key",
            name="uq_organization_party_scope_commit_request",
        ),
        Index(
            "ix_organization_party_scope_commits_organization_id",
            "organization_id",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="目标组织ID",
    )
    actor_id = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="提交人ID",
    )
    idempotency_key = Column(String(128), nullable=False, comment="幂等键")
    reason = Column(String(500), nullable=False, comment="变更原因")
    proposal = Column(JSON, nullable=False, comment="提交的主体范围提案")
    before_scope = Column(JSON, nullable=False, comment="提交前范围快照")
    after_scope = Column(JSON, nullable=False, comment="提交后范围快照")
    impact_summary = Column(JSON, nullable=False, comment="影响摘要")
    result_data = Column(JSON, nullable=False, comment="幂等返回结果快照")
    committed_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="提交时间"
    )

    organization: Mapped["Organization"] = relationship("Organization")

    def __repr__(self) -> str:
        return (
            "<OrganizationPartyScopeCommit("
            f"id={self.id}, organization_id={self.organization_id})>"
        )  # pragma: no cover


class OrganizationPartyScopeBatchCommit(Base):
    """Durable all-or-nothing receipt for Organization Party scope batches."""

    __tablename__ = "organization_party_scope_batch_commits"
    __table_args__ = (
        UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_organization_party_scope_batch_commit_request",
        ),
        Index(
            "ix_organization_party_scope_batch_commits_actor_id",
            "actor_id",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="提交人ID",
    )
    idempotency_key = Column(String(128), nullable=False, comment="幂等键")
    reason = Column(String(500), nullable=False, comment="变更原因")
    proposal = Column(JSON, nullable=False, comment="批量主体范围提案")
    before_scope = Column(JSON, nullable=False, comment="批量提交前范围快照")
    after_scope = Column(JSON, nullable=False, comment="批量提交后范围快照")
    impact_summary = Column(JSON, nullable=False, comment="批量影响摘要")
    result_data = Column(JSON, nullable=False, comment="幂等返回结果快照")
    committed_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="提交时间"
    )

    def __repr__(self) -> str:
        return f"<OrganizationPartyScopeBatchCommit(id={self.id})>"  # pragma: no cover


__all__ = [
    "Organization",
    "OrganizationHistory",
    "OrganizationPartyScopeBatchCommit",
    "OrganizationPartyScopeCommit",
    "RepresentedPartyPerspective",
]
