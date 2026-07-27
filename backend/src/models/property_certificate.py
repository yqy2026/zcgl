"""Property certificate models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .associations import property_cert_assets

if TYPE_CHECKING:
    from .asset import Asset
    from .certificate_party_relation import CertificatePartyRelation


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CertificateType(str, Enum):
    """Supported property certificate types."""

    REAL_ESTATE = "real_estate"
    HOUSE_OWNERSHIP = "house_ownership"
    LAND_USE = "land_use"
    OTHER = "other"


class PropertyCertificate(Base):
    """Property certificate master record."""

    __tablename__ = "property_certificates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    certificate_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Certificate number",
    )
    certificate_type: Mapped[CertificateType] = mapped_column(
        SQLEnum(CertificateType), nullable=False, index=True, comment="Certificate type"
    )
    registration_date: Mapped[date | None] = mapped_column(
        Date, comment="Registration date"
    )
    property_address: Mapped[str | None] = mapped_column(
        String(500), comment="Property address"
    )
    property_type: Mapped[str | None] = mapped_column(
        String(50), comment="Property usage type"
    )
    building_area: Mapped[str | None] = mapped_column(
        String(50), comment="Building area"
    )
    floor_info: Mapped[str | None] = mapped_column(String(100), comment="Floor info")
    land_area: Mapped[str | None] = mapped_column(String(50), comment="Land area")
    land_use_type: Mapped[str | None] = mapped_column(
        String(50), comment="Land use right type"
    )
    land_use_term_start: Mapped[date | None] = mapped_column(
        Date, comment="Land use term start"
    )
    land_use_term_end: Mapped[date | None] = mapped_column(
        Date, comment="Land use term end"
    )
    co_ownership: Mapped[str | None] = mapped_column(
        String(200), comment="Co-ownership"
    )
    restrictions: Mapped[str | None] = mapped_column(Text, comment="Restrictions")
    remarks: Mapped[str | None] = mapped_column(Text, comment="Remarks")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, comment="Created at"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, comment="Updated at"
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="Creator ID")

    assets: Mapped[list[Asset]] = relationship(
        "Asset", secondary=property_cert_assets, back_populates="certificates"
    )
    party_relations: Mapped[list[CertificatePartyRelation]] = relationship(
        "CertificatePartyRelation", cascade="all, delete-orphan", passive_deletes=True
    )
