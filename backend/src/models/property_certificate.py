"""Property certificate models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, String, Text
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
    """产权证类型。"""

    REAL_ESTATE = "real_estate"
    HOUSE_OWNERSHIP = "house_ownership"
    LAND_USE = "land_use"
    OTHER = "other"


class OwnerType(str, Enum):
    """兼容保留：历史权利人类型。"""

    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    JOINT = "joint"


class PropertyCertificate(Base):
    """产权证主表（Phase4 仅保留主证与 party 关系）。"""

    __tablename__ = "property_certificates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    certificate_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="证书编号"
    )
    certificate_type: Mapped[CertificateType] = mapped_column(
        SQLEnum(CertificateType), nullable=False, index=True, comment="证书类型"
    )

    extraction_confidence: Mapped[float | None] = mapped_column(
        default=None, comment="LLM提取置信度 (0-1)"
    )
    extraction_source: Mapped[str] = mapped_column(
        String(20), default="manual", comment="数据来源：llm/manual"
    )
    is_verified: Mapped[bool] = mapped_column(
        "verified", Boolean, default=False, comment="是否人工审核"
    )

    registration_date: Mapped[date | None] = mapped_column(Date, comment="登记日期")
    property_address: Mapped[str | None] = mapped_column(
        String(500), comment="坐落地址"
    )
    property_type: Mapped[str | None] = mapped_column(
        String(50), comment="用途（住宅/商业/工业/办公）"
    )
    building_area: Mapped[str | None] = mapped_column(
        String(50), comment="建筑面积（平方米）"
    )
    floor_info: Mapped[str | None] = mapped_column(String(100), comment="楼层信息")
    land_area: Mapped[str | None] = mapped_column(
        String(50), comment="土地使用面积（平方米）"
    )
    land_use_type: Mapped[str | None] = mapped_column(
        String(50), comment="土地使用权类型（出让/划拨）"
    )
    land_use_term_start: Mapped[date | None] = mapped_column(
        Date, comment="土地使用期限起"
    )
    land_use_term_end: Mapped[date | None] = mapped_column(
        Date, comment="土地使用期限止"
    )
    co_ownership: Mapped[str | None] = mapped_column(String(200), comment="共有情况")
    restrictions: Mapped[str | None] = mapped_column(Text, comment="权利限制情况")
    remarks: Mapped[str | None] = mapped_column(Text, comment="备注")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人ID")

    assets: Mapped[list[Asset]] = relationship(
        "Asset",
        secondary=property_cert_assets,
        back_populates="certificates",
    )
    party_relations: Mapped[list[CertificatePartyRelation]] = relationship(
        "CertificatePartyRelation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
