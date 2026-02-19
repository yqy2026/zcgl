"""Certificate-party relation model."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CertificateRelationRole(StrEnum):
    OWNER = "owner"
    CO_OWNER = "co_owner"
    ISSUER = "issuer"
    CUSTODIAN = "custodian"


class CertificatePartyRelation(Base):
    """Ownership/issuer/custodian relationships for certificates."""

    __tablename__ = "certificate_party_relations"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_certificate_party_relations_valid_range",
        ),
        CheckConstraint(
            "share_ratio IS NULL OR (share_ratio > 0 AND share_ratio <= 100)",
            name="ck_certificate_party_relations_share_ratio",
        ),
        Index(
            "uq_certificate_primary_owner_active",
            "certificate_id",
            unique=True,
            postgresql_where=text(
                "relation_role = 'owner' AND is_primary = true AND valid_to IS NULL"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    certificate_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("property_certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="产权证ID",
    )
    party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="主体ID",
    )
    relation_role: Mapped[CertificateRelationRole] = mapped_column(
        SQLEnum(
            CertificateRelationRole,
            name="certificate_relation_role",
        ),
        nullable=False,
        comment="关系角色",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否主角色"
    )
    share_ratio: Mapped[float | None] = mapped_column(
        Numeric(5, 2), comment="占比(%)"
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive, comment="生效时间"
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, comment="失效时间")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, comment="扩展元数据"
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
        return (
            f"<CertificatePartyRelation(certificate_id={self.certificate_id}, party_id={self.party_id}, role={self.relation_role})>"
        )


__all__ = ["CertificateRelationRole", "CertificatePartyRelation"]
