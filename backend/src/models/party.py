"""Party-domain models for Party-Role architecture."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .party_review_log import PartyReviewLog
    from .party_role import PartyRoleBinding
    from .user_party_binding import UserPartyBinding


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PartyType(StrEnum):
    ORGANIZATION = "organization"
    LEGAL_ENTITY = "legal_entity"
    INDIVIDUAL = "individual"


class PartyReviewStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REVERSED = "reversed"


class Party(Base):
    """Canonical legal/business party."""

    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("party_type", "code", name="uq_parties_party_type_code"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    party_type: Mapped[PartyType] = mapped_column(
        String(50), nullable=False, comment="主体类型"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="主体名称")
    code: Mapped[str] = mapped_column(String(100), nullable=False, comment="主体编码")
    external_ref: Mapped[str | None] = mapped_column(
        String(200), comment="外部系统引用ID"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", comment="状态"
    )
    review_status: Mapped[PartyReviewStatus] = mapped_column(
        String(50), nullable=False, default=PartyReviewStatus.DRAFT, comment="审核状态"
    )
    review_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="审核人"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="审核时间"
    )
    review_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="审核原因/驳回原因"
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, comment="扩展信息"
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, comment="软删除时间"
    )

    contacts: Mapped[list["PartyContact"]] = relationship(
        "PartyContact", back_populates="party", cascade="all, delete-orphan"
    )
    parent_links: Mapped[list["PartyHierarchy"]] = relationship(
        "PartyHierarchy",
        foreign_keys="PartyHierarchy.parent_party_id",
        back_populates="parent_party",
        cascade="all, delete-orphan",
    )
    child_links: Mapped[list["PartyHierarchy"]] = relationship(
        "PartyHierarchy",
        foreign_keys="PartyHierarchy.child_party_id",
        back_populates="child_party",
        cascade="all, delete-orphan",
    )
    role_bindings: Mapped[list["PartyRoleBinding"]] = relationship(
        "PartyRoleBinding", back_populates="party", cascade="all, delete-orphan"
    )
    user_bindings: Mapped[list["UserPartyBinding"]] = relationship(
        "UserPartyBinding", back_populates="party", cascade="all, delete-orphan"
    )
    review_logs: Mapped[list["PartyReviewLog"]] = relationship(
        "PartyReviewLog", back_populates="party", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Party(id={self.id}, code={self.code}, type={self.party_type})>"


class PartyHierarchy(Base):
    """Parent-child hierarchy between parties."""

    __tablename__ = "party_hierarchy"
    __table_args__ = (
        UniqueConstraint(
            "parent_party_id",
            "child_party_id",
            name="uq_party_hierarchy_parent_child",
        ),
        CheckConstraint(
            "parent_party_id <> child_party_id", name="ck_party_hierarchy_no_self_ref"
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parent_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="父主体ID",
    )
    child_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="子主体ID",
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

    parent_party: Mapped["Party"] = relationship(
        "Party", foreign_keys=[parent_party_id], back_populates="parent_links"
    )
    child_party: Mapped["Party"] = relationship(
        "Party", foreign_keys=[child_party_id], back_populates="child_links"
    )

    def __repr__(self) -> str:
        return f"<PartyHierarchy(parent={self.parent_party_id}, child={self.child_party_id})>"


class PartyContact(Base):
    """Contact information of a party."""

    __tablename__ = "party_contacts"
    __table_args__ = (
        Index(
            "uq_party_contacts_primary_per_party",
            "party_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
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
    contact_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="联系人姓名"
    )
    contact_phone: Mapped[str | None] = mapped_column(String(50), comment="联系电话")
    contact_email: Mapped[str | None] = mapped_column(String(255), comment="联系邮箱")
    position: Mapped[str | None] = mapped_column(String(100), comment="职位")
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否主联系人"
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")
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

    party: Mapped["Party"] = relationship("Party", back_populates="contacts")

    def __repr__(self) -> str:
        return f"<PartyContact(id={self.id}, party_id={self.party_id}, primary={self.is_primary})>"


__all__ = [
    "PartyType",
    "PartyReviewStatus",
    "Party",
    "PartyHierarchy",
    "PartyContact",
]
