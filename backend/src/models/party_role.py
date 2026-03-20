"""Role definition and binding models for party authorization."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..utils.time import utcnow_naive

if TYPE_CHECKING:
    from .party import Party


class PartyRoleDef(Base):
    """Role templates (e.g. OWNER/MANAGER) scoped by resource type."""

    __tablename__ = "party_role_defs"
    __table_args__ = (
        UniqueConstraint(
            "role_code", "scope_type", name="uq_party_role_defs_code_scope"
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    role_code: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="角色编码"
    )
    scope_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="作用域类型"
    )
    description: Mapped[str | None] = mapped_column(String(500), comment="描述")

    bindings: Mapped[list["PartyRoleBinding"]] = relationship(
        "PartyRoleBinding", back_populates="role_def", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PartyRoleDef(id={self.id}, role_code={self.role_code}, scope={self.scope_type})>"


class PartyRoleBinding(Base):
    """Role assignment to party under a specific scope/resource."""

    __tablename__ = "party_role_bindings"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_party_role_bindings_valid_range",
        ),
        CheckConstraint(
            "(scope_type = 'global' AND scope_id IS NULL) OR "
            "(scope_type <> 'global' AND scope_id IS NOT NULL)",
            name="ck_party_role_bindings_scope_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="主体ID",
    )
    role_def_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("party_role_defs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="角色定义ID",
    )
    scope_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="作用域类型"
    )
    scope_id: Mapped[str | None] = mapped_column(String, comment="作用域资源ID")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, comment="生效时间"
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, comment="失效时间")
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="动态属性")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow_naive,
        onupdate=utcnow_naive,
        comment="更新时间",
    )

    party: Mapped["Party"] = relationship("Party", back_populates="role_bindings")
    role_def: Mapped["PartyRoleDef"] = relationship(
        "PartyRoleDef", back_populates="bindings"
    )

    def __repr__(self) -> str:
        return f"<PartyRoleBinding(id={self.id}, party_id={self.party_id}, scope={self.scope_type})>"


__all__ = [
    "PartyRoleDef",
    "PartyRoleBinding",
]
