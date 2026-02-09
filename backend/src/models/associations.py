"""跨聚合多对多关联表定义。"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table

from ..database import Base

rent_contract_assets = Table(
    "rent_contract_assets",
    Base.metadata,
    Column("contract_id", String, ForeignKey("rent_contracts.id"), primary_key=True),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="关联创建时间",
    ),
)


property_cert_assets = Table(
    "property_cert_assets",
    Base.metadata,
    Column(
        "certificate_id",
        String,
        ForeignKey("property_certificates.id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column("link_type", String(50), comment="关联类型（primary/secondary/partial）"),
    Column("notes", String(500), comment="关联备注"),
    comment="产权证资产关联表",
)


__all__ = ["rent_contract_assets", "property_cert_assets"]
