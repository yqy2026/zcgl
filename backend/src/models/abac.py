"""ABAC policy models."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .rbac import Role


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Persist enum values instead of member names for PostgreSQL enum compatibility."""
    return [member.value for member in enum_cls]


class ABACEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class ABACAction(StrEnum):
    CREATE = "create"
    READ = "read"
    LIST = "list"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"


class ABACPolicy(Base):
    """ABAC policy root entity."""

    __tablename__ = "abac_policies"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="策略名称")
    effect: Mapped[ABACEffect] = mapped_column(
        SQLEnum(
            ABACEffect,
            name="abac_effect",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ABACEffect.ALLOW,
        comment="策略效果",
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="优先级"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
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

    rules: Mapped[list["ABACPolicyRule"]] = relationship(
        "ABACPolicyRule", back_populates="policy", cascade="all, delete-orphan"
    )
    role_policies: Mapped[list["ABACRolePolicy"]] = relationship(
        "ABACRolePolicy", back_populates="policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ABACPolicy(id={self.id}, name={self.name}, effect={self.effect})>"


class ABACPolicyRule(Base):
    """Executable rule under an ABAC policy."""

    __tablename__ = "abac_policy_rules"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    policy_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("abac_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="策略ID",
    )
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="资源类型"
    )
    action: Mapped[ABACAction] = mapped_column(
        SQLEnum(
            ABACAction,
            name="abac_action",
            values_callable=_enum_values,
        ),
        nullable=False,
        comment="动作",
    )
    condition_expr: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="JSONLogic 条件表达式"
    )
    field_mask: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, comment="字段掩码"
    )

    policy: Mapped["ABACPolicy"] = relationship("ABACPolicy", back_populates="rules")

    def __repr__(self) -> str:
        return (
            f"<ABACPolicyRule(policy_id={self.policy_id}, resource={self.resource_type}, action={self.action})>"
        )


class ABACRolePolicy(Base):
    """Role to policy binding table."""

    __tablename__ = "abac_role_policies"
    __table_args__ = (
        UniqueConstraint("role_id", "policy_id", name="uq_abac_role_policies_role_policy"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    role_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="角色ID",
    )
    policy_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("abac_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="策略ID",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    priority_override: Mapped[int | None] = mapped_column(
        Integer, comment="优先级覆盖"
    )
    params_override: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, comment="参数覆盖"
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

    policy: Mapped["ABACPolicy"] = relationship(
        "ABACPolicy", back_populates="role_policies"
    )
    role: Mapped["Role"] = relationship("Role")

    def __repr__(self) -> str:
        return f"<ABACRolePolicy(role_id={self.role_id}, policy_id={self.policy_id})>"


__all__ = [
    "ABACEffect",
    "ABACAction",
    "ABACPolicy",
    "ABACPolicyRule",
    "ABACRolePolicy",
]
