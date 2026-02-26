"""Property Certificate Models - 产权证管理数据模型"""

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .associations import property_cert_assets

if TYPE_CHECKING:
    from .asset import Asset
    from .organization import Organization

# Certificate ↔ Owners association table
property_certificate_owners = Table(
    "property_certificate_owners",
    Base.metadata,
    Column(
        "certificate_id",
        String,
        ForeignKey("property_certificates.id"),
        primary_key=True,
    ),
    Column("owner_id", String, ForeignKey("property_owners.id"), primary_key=True),
    Column("ownership_share", Numeric(5, 2), comment="拥有权比例（百分比）"),
    Column(
        "owner_category", String(50), comment="权利人类别（单独所有/共同共有/按份共有）"
    ),
    comment="产权证权利人关联表",
)

class CertificateType(str, Enum):
    """产权证类型"""

    REAL_ESTATE = "real_estate"  # 不动产权证（新版）
    HOUSE_OWNERSHIP = "house_ownership"  # 房屋所有权证（旧版）
    LAND_USE = "land_use"  # 土地使用证
    OTHER = "other"  # 其他权属证明


class OwnerType(str, Enum):
    """权利人类型"""

    INDIVIDUAL = "individual"  # 个人
    ORGANIZATION = "organization"  # 组织/企业
    JOINT = "joint"  # 共有


class PropertyOwner(Base):
    """权利人表 - 支持个人、组织、共有权利人"""

    __tablename__ = "property_owners"

    # Primary fields
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Owner information
    owner_type: Mapped[OwnerType] = mapped_column(
        SQLEnum(OwnerType), nullable=False, index=True, comment="权利人类型"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="权利人姓名/单位名称"
    )
    id_type: Mapped[str | None] = mapped_column(
        String(50), comment="证件类型（身份证/营业执照/其他）"
    )
    id_number: Mapped[str | None] = mapped_column(
        String(100), comment="证件号码（加密存储）"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), comment="联系电话（加密存储）"
    )
    address: Mapped[str | None] = mapped_column(String(500), comment="地址")

    # Optional organization linkage
    organization_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("organizations.id"),
        comment="关联组织ID（DEPRECATED）",
        info={"deprecated": True},
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship("Organization")
    certificates: Mapped[list["PropertyCertificate"]] = relationship(
        "PropertyCertificate",
        secondary="property_certificate_owners",
        back_populates="owners",
    )


class PropertyCertificate(Base):
    """产权证主表"""

    __tablename__ = "property_certificates"

    # Primary fields
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Certificate identification
    certificate_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="证书编号"
    )
    certificate_type: Mapped[CertificateType] = mapped_column(
        SQLEnum(CertificateType), nullable=False, index=True, comment="证书类型"
    )

    # Extraction metadata
    extraction_confidence: Mapped[float | None] = mapped_column(
        default=None, comment="LLM提取置信度 (0-1)"
    )
    extraction_source: Mapped[str] = mapped_column(
        String(20), default="manual", comment="数据来源：llm/manual"
    )
    is_verified: Mapped[bool] = mapped_column(
        "verified", Boolean, default=False, comment="是否人工审核"
    )

    # Basic information
    registration_date: Mapped[date | None] = mapped_column(Date, comment="登记日期")
    property_address: Mapped[str | None] = mapped_column(
        String(500), comment="坐落地址"
    )
    property_type: Mapped[str | None] = mapped_column(
        String(50), comment="用途（住宅/商业/工业/办公）"
    )

    # House information
    building_area: Mapped[str | None] = mapped_column(
        String(50), comment="建筑面积（平方米）"
    )
    floor_info: Mapped[str | None] = mapped_column(String(100), comment="楼层信息")

    # Land information
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

    # Other information
    co_ownership: Mapped[str | None] = mapped_column(String(200), comment="共有情况")
    restrictions: Mapped[str | None] = mapped_column(Text, comment="权利限制情况")
    remarks: Mapped[str | None] = mapped_column(Text, comment="备注")
    organization_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("organizations.id"),
        index=True,
        comment="所属组织ID（DEPRECATED）",
        info={"deprecated": True},
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人ID")

    # Relationships (many-to-many)
    organization: Mapped["Organization | None"] = relationship("Organization")
    owners: Mapped[list["PropertyOwner"]] = relationship(
        "PropertyOwner",
        secondary="property_certificate_owners",
        back_populates="certificates",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=property_cert_assets,
        back_populates="certificates",
    )
