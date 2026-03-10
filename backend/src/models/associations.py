"""跨聚合多对多关联表定义。"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table

from ..database import Base

# ---- 合同组-资产（REQ-RNT-001 五层合同体系）----

contract_group_assets = Table(
    "contract_group_assets",
    Base.metadata,
    Column(
        "contract_group_id",
        String,
        ForeignKey("contract_groups.contract_group_id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="关联创建时间",
    ),
    comment="合同组-资产多对多关联",
)

contract_assets = Table(
    "contract_assets",
    Base.metadata,
    Column(
        "contract_id",
        String,
        ForeignKey("contracts.contract_id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="关联创建时间",
    ),
    comment="合同-资产多对多关联（ContractGroup.asset_ids 的子集）",
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


__all__ = [
    "contract_group_assets",
    "contract_assets",
    "property_cert_assets",
]
