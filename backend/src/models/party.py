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
    from .user_party_binding import UserPartyBinding


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PartyType(StrEnum):
    LEGAL_ENTITY = "legal_entity"
    INDIVIDUAL = "individual"


class PartyReviewStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Party(Base):
    """Canonical legal/business party."""

    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("code", name="uq_parties_code"),
        CheckConstraint(
            "party_type IN ('legal_entity', 'individual')",
            name="ck_parties_party_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_parties_status",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_parties_metadata_object",
        ),
        CheckConstraint(
            "(party_type = 'legal_entity' AND code ~ '^LE-[0-9]{6}$') OR "
            "(party_type = 'individual' AND code ~ '^NP-[0-9]{6}$')",
            name="ck_parties_code_format",
        ),
        CheckConstraint(
            "(identifier_type IS NULL AND identifier_value IS NULL) OR "
            "(identifier_type IS NOT NULL AND identifier_value IS NOT NULL)",
            name="ck_parties_identifier_pair",
        ),
        CheckConstraint(
            "identifier_type IS NULL OR "
            "(party_type = 'legal_entity' AND identifier_type IN "
            "('unified_social_credit_code', 'legal_registration_number', "
            "'foreign_registration_number')) OR "
            "(party_type = 'individual' AND identifier_type IN "
            "('national_id', 'passport'))",
            name="ck_parties_identifier_type",
        ),
        CheckConstraint(
            "(identifier_type IS NULL AND identifier_fingerprint IS NULL) OR "
            "(identifier_type IS NOT NULL AND party_type = 'legal_entity' AND "
            "identifier_fingerprint IS NULL) OR "
            "(identifier_type IS NOT NULL AND party_type = 'individual' AND "
            "identifier_fingerprint IS NOT NULL)",
            name="ck_parties_identifier_fingerprint",
        ),
        Index(
            "uq_parties_legal_identifier",
            "identifier_type",
            "identifier_value",
            unique=True,
            postgresql_where=text(
                "party_type = 'legal_entity' AND identifier_type IS NOT NULL"
            ),
        ),
        Index(
            "uq_parties_individual_identifier_fingerprint",
            "identifier_type",
            "identifier_fingerprint",
            unique=True,
            postgresql_where=text(
                "party_type = 'individual' AND identifier_type IS NOT NULL"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    party_type: Mapped[PartyType] = mapped_column(
        String(50), nullable=False, comment="主体类型"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="主体名称")
    code: Mapped[str] = mapped_column(String(100), nullable=False, comment="主体编码")
    identifier_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="正式标识类型"
    )
    identifier_value: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="规范化或加密后的正式标识值"
    )
    identifier_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="自然人正式标识指纹"
    )
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
    user_bindings: Mapped[list["UserPartyBinding"]] = relationship(
        "UserPartyBinding", back_populates="party", cascade="all, delete-orphan"
    )
    review_logs: Mapped[list["PartyReviewLog"]] = relationship(
        "PartyReviewLog", back_populates="party", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Party(id={self.id}, code={self.code}, type={self.party_type})>"


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
    "PartyContact",
]
