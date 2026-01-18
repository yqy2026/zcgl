"""Property Certificate Models - 产权证管理数据模型"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


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


class PropertyOwner(Base):  # type: ignore[valid-type, misc]
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
    phone: Mapped[str | None] = mapped_column(String(20), comment="联系电话（加密存储）")
    address: Mapped[str | None] = mapped_column(String(500), comment="地址")

    # Optional organization linkage
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), comment="关联组织ID"
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # Relationships
    organization = relationship("Organization", back_populates="property_owners")

