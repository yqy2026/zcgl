"""User to party relationship bindings."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..utils.time import utcnow_naive

if TYPE_CHECKING:
    from .party import Party


class RelationType(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    HEADQUARTERS = "headquarters"


class UserPartyBinding(Base):
    """Binding of a user to party with a perspective (owner/manager/headquarters)."""

    __tablename__ = "user_party_bindings"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_user_party_bindings_valid_range",
        ),
        Index(
            "uq_user_party_bindings_primary_per_relation",
            "user_id",
            "relation_type",
            unique=True,
            postgresql_where=text("is_primary = true"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="主体ID",
    )
    relation_type: Mapped[RelationType] = mapped_column(
        String(50), nullable=False, comment="关系类型"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否主关系"
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, comment="生效时间"
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, comment="失效时间")
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

    party: Mapped["Party"] = relationship("Party", back_populates="user_bindings")

    def __repr__(self) -> str:
        return f"<UserPartyBinding(user_id={self.user_id}, party_id={self.party_id}, relation={self.relation_type})>"


__all__ = [
    "RelationType",
    "UserPartyBinding",
]
