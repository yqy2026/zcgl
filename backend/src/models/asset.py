"""
资产相关数据库模型
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import NO_VALUE

from ..database import Base

if TYPE_CHECKING:
    from .asset_history import AssetDocument, AssetHistory
    from .ownership import Ownership
    from .project import Project
    from .property_certificate import PropertyCertificate
    from .rent_contract import RentContract


def _utcnow_naive() -> datetime:
    """Return UTC now as naive datetime to match current DB column types."""
    return datetime.now(UTC).replace(tzinfo=None)


class Asset(Base):
    """资产模型"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
    # ownership_entity 移除：使用 ownership_id 作为权属唯一来源
    ownership_category: Mapped[str | None] = mapped_column(
        String(100), comment="权属类别"
    )
    project_name: Mapped[str | None] = mapped_column(
        String(200), index=True, comment="项目名称"
    )
    property_name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, comment="物业名称"
    )
    address: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="物业地址"
    )
    ownership_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="确权状态"
    )
    property_nature: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="物业性质"
    )
    usage_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="使用状态"
    )
    management_entity: Mapped[str | None] = mapped_column(
        String(200), comment="经营管理单位"
    )
    business_category: Mapped[str | None] = mapped_column(
        String(100), comment="业态类别"
    )
    is_litigated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否涉诉"
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 面积相关字段
    land_area: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 2), comment="土地面积（平方米）"
    )
    actual_property_area: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 2), comment="实际房产面积（平方米）"
    )
    rentable_area: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 2), comment="可出租面积（平方米）"
    )
    rented_area: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 2), comment="已出租面积（平方米）"
    )
    # unrented_area 和 occupancy_rate 改为计算字段，不存储在数据库中
    non_commercial_area: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 2), comment="非经营物业面积（平方米）"
    )
    include_in_occupancy_rate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否计入出租率统计"
    )

    # 用途相关字段
    certificated_usage: Mapped[str | None] = mapped_column(
        String(100), comment="证载用途"
    )
    actual_usage: Mapped[str | None] = mapped_column(String(100), comment="实际用途")

    # 租户相关字段
    tenant_type: Mapped[str | None] = mapped_column(String(20), comment="租户类型")

    is_sublease: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否分租/转租"
    )
    sublease_notes: Mapped[str | None] = mapped_column(Text, comment="分租/转租备注")

    # 管理相关字段
    business_model: Mapped[str | None] = mapped_column(String(50), comment="接收模式")
    operation_status: Mapped[str | None] = mapped_column(String(20), comment="经营状态")
    manager_name: Mapped[str | None] = mapped_column(
        String(100), comment="管理责任人（网格员）"
    )

    # 接收相关字段
    operation_agreement_start_date: Mapped[date | None] = mapped_column(
        Date, comment="接收协议开始日期"
    )
    operation_agreement_end_date: Mapped[date | None] = mapped_column(
        Date, comment="接收协议结束日期"
    )
    operation_agreement_attachments: Mapped[str | None] = mapped_column(
        Text, comment="接收协议文件"
    )

    # 终端合同相关字段
    terminal_contract_files: Mapped[str | None] = mapped_column(
        Text, comment="终端合同文件"
    )

    # 系统字段
    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="版本号"
    )
    __mapper_args__ = {"version_id_col": version}
    tags: Mapped[str | None] = mapped_column(Text, comment="标签")
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")
    audit_notes: Mapped[str | None] = mapped_column(Text, comment="审核备注")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        comment="更新时间",
    )

    # 关联关系
    history_records: Mapped[list["AssetHistory"]] = relationship(
        "AssetHistory", back_populates="asset", cascade="all, delete-orphan"
    )
    documents: Mapped[list["AssetDocument"]] = relationship(
        "AssetDocument", back_populates="asset", cascade="all, delete-orphan"
    )
    rent_contracts: Mapped[list["RentContract"]] = relationship(
        "RentContract",
        secondary="rent_contract_assets",
        back_populates="assets",
        lazy="selectin",
    )
    certificates: Mapped[list["PropertyCertificate"]] = relationship(
        "PropertyCertificate",
        secondary="property_cert_assets",
        back_populates="assets",
    )
    project_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("projects.id"), index=True, comment="项目ID"
    )
    ownership_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("ownerships.id"), index=True, comment="权属方ID"
    )

    # 关系定义
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    ownership: Mapped["Ownership"] = relationship("Ownership", back_populates="assets")

    @property
    def ownership_entity(self) -> str | None:
        ownership_value = inspect(self).attrs.ownership.loaded_value
        if ownership_value is NO_VALUE:
            return None
        return getattr(ownership_value, "name", None)

    @property
    def active_contract(self) -> "RentContract | None":
        """获取当前有效合同。"""
        from ..core.enums import ContractStatus

        contracts_value = inspect(self).attrs.rent_contracts.loaded_value
        if contracts_value is NO_VALUE:
            return None

        today = date.today()
        active_statuses = {
            ContractStatus.ACTIVE.value,
            ContractStatus.EXPIRING.value,
            "有效",
            "执行中",
            "即将到期",
        }

        active_contracts = [
            contract
            for contract in contracts_value
            if getattr(contract, "contract_status", None) in active_statuses
        ]
        if not active_contracts:
            return None

        effective_contracts = [
            contract
            for contract in active_contracts
            if (contract.start_date is None or contract.start_date <= today)
            and (contract.end_date is None or contract.end_date >= today)
        ]

        candidates = effective_contracts if effective_contracts else active_contracts
        return sorted(
            candidates,
            key=lambda contract: (
                contract.start_date or date.min,
                contract.created_at or datetime.min,
            ),
            reverse=True,
        )[0]

    @property
    def tenant_name(self) -> str | None:
        contract = self.active_contract
        return contract.tenant_name if contract else None

    @property
    def lease_contract_number(self) -> str | None:
        contract = self.active_contract
        return contract.contract_number if contract else None

    @property
    def contract_start_date(self) -> date | None:
        contract = self.active_contract
        return contract.start_date if contract else None

    @property
    def contract_end_date(self) -> date | None:
        contract = self.active_contract
        return contract.end_date if contract else None

    @property
    def monthly_rent(self) -> Decimal | None:
        contract = self.active_contract
        return contract.monthly_rent_base if contract else None

    @property
    def deposit(self) -> Decimal | None:
        contract = self.active_contract
        return contract.total_deposit if contract else None

    # 计算属性 - 未出租面积（自动计算，不存储）
    @cached_property
    def unrented_area(self) -> Decimal:
        """计算未出租面积"""
        rentable = self.rentable_area or Decimal("0")
        rented = self.rented_area or Decimal("0")
        return max(rentable - rented, Decimal("0"))

    # 计算属性 - 出租率（自动计算，不存储）
    @cached_property
    def occupancy_rate(self) -> Decimal:
        """计算出租率（百分比）"""
        if not self.include_in_occupancy_rate:
            return Decimal("0")

        rentable = self.rentable_area or Decimal("0")
        if rentable == 0:
            return Decimal("0")

        rented = self.rented_area or Decimal("0")
        rate = (rented / rentable) * Decimal("100")
        return round(rate, 2)

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", str(uuid.uuid4()))
        kwargs.setdefault("data_status", "正常")
        kwargs.setdefault("version", 1)
        kwargs.setdefault("is_litigated", False)
        kwargs.setdefault("include_in_occupancy_rate", True)
        kwargs.setdefault("is_sublease", False)
        kwargs.setdefault("created_at", _utcnow_naive())
        kwargs.setdefault("updated_at", _utcnow_naive())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name={self.property_name})>"

    def clear_cached_properties(self) -> None:
        """清除缓存的计算属性"""
        self.__dict__.pop("unrented_area", None)
        self.__dict__.pop("occupancy_rate", None)


__all__ = ["Asset"]
