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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .property_certificate import PropertyCertificate
    from .rent_contract import RentContract


class Asset(Base):
    """资产模型"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
    ownership_entity: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="权属方"
    )
    ownership_category: Mapped[str | None] = mapped_column(
        String(100), comment="权属类别"
    )
    project_name: Mapped[str | None] = mapped_column(
        String(200), index=True, comment="项目名称"
    )
    property_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="物业名称"
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
    # occupancy_rate 字段已移除，改为计算字段
    include_in_occupancy_rate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否计入出租率统计"
    )

    # 用途相关字段
    certificated_usage: Mapped[str | None] = mapped_column(
        String(100), comment="证载用途"
    )
    actual_usage: Mapped[str | None] = mapped_column(String(100), comment="实际用途")

    # 租户相关字段
    tenant_name: Mapped[str | None] = mapped_column(String(200), comment="租户名称")
    tenant_type: Mapped[str | None] = mapped_column(String(20), comment="租户类型")

    # 合同相关字段
    lease_contract_number: Mapped[str | None] = mapped_column(
        String(100), comment="租赁合同编号"
    )
    contract_start_date: Mapped[date | None] = mapped_column(
        Date, comment="合同开始日期"
    )
    contract_end_date: Mapped[date | None] = mapped_column(Date, comment="合同结束日期")
    monthly_rent: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="月租金（元）"
    )
    deposit: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="押金（元）"
    )
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

    # 财务相关字段已移除
    # annual_income, annual_expense, net_income 字段已移除

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

    # 项目相关字段

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

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: Mapped[str | None] = mapped_column(Text, comment="审核备注")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
        kwargs.setdefault("created_at", datetime.now(UTC))
        kwargs.setdefault("updated_at", datetime.now(UTC))
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name={self.property_name})>"

    def clear_cached_properties(self) -> None:
        """清除缓存的计算属性"""
        # 对于cached_property，需要手动处理缓存清除
        self.__dict__.pop("unrented_area", None)
        self.__dict__.pop("occupancy_rate", None)


class AssetHistory(Base):
    """资产变更历史模型"""

    __tablename__ = "asset_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_id: Mapped[str] = mapped_column(
        String, ForeignKey("assets.id"), index=True, nullable=False, comment="资产ID"
    )
    operation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="操作类型"
    )
    field_name: Mapped[str | None] = mapped_column(String(100), comment="字段名称")
    old_value: Mapped[str | None] = mapped_column(Text, comment="原值")
    new_value: Mapped[str | None] = mapped_column(Text, comment="新值")
    operator: Mapped[str | None] = mapped_column(String(100), comment="操作人")
    operation_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="操作时间"
    )
    description: Mapped[str | None] = mapped_column(Text, comment="操作描述")

    # 新增审计字段
    change_reason: Mapped[str | None] = mapped_column(String(200), comment="变更原因")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")
    session_id: Mapped[str | None] = mapped_column(String(100), comment="会话ID")

    # 关联关系
    asset: Mapped["Asset"] = relationship("Asset", back_populates="history_records")

    def __repr__(self) -> str:
        return f"<AssetHistory(id={self.id}, asset_id={self.asset_id}, operation={self.operation_type})>"


class AssetDocument(Base):
    """资产文档模型"""

    __tablename__ = "asset_documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_id: Mapped[str] = mapped_column(
        String, ForeignKey("assets.id"), index=True, nullable=False, comment="资产ID"
    )
    document_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="文档名称"
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="文档类型"
    )
    file_path: Mapped[str | None] = mapped_column(String(500), comment="文件路径")
    file_size: Mapped[int | None] = mapped_column(Integer, comment="文件大小(字节)")
    mime_type: Mapped[str | None] = mapped_column(String(100), comment="文件MIME类型")
    upload_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="上传时间"
    )
    uploader: Mapped[str | None] = mapped_column(String(100), comment="上传人")
    description: Mapped[str | None] = mapped_column(Text, comment="文档描述")

    # 关联关系
    asset: Mapped["Asset"] = relationship("Asset", back_populates="documents")

    def __repr__(self) -> str:
        return f"<AssetDocument(id={self.id}, name={self.document_name})>"


class SystemDictionary(Base):
    """系统数据字典模型"""

    __tablename__ = "system_dictionaries"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dict_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="字典类型"
    )
    dict_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="字典编码"
    )
    dict_label: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="字典标签"
    )
    dict_value: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="字典值"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<SystemDictionary(type={self.dict_type}, code={self.dict_code}, label={self.dict_label})>"


class AssetCustomField(Base):
    """资产自定义字段模型"""

    __tablename__ = "asset_custom_fields"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="字段名称"
    )
    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="显示名称"
    )
    field_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="字段类型"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否必填"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    default_value: Mapped[str | None] = mapped_column(Text, comment="默认值")
    field_options: Mapped[str | None] = mapped_column(Text, comment="字段选项(JSON)")
    validation_rules: Mapped[str | None] = mapped_column(Text, comment="验证规则(JSON)")
    help_text: Mapped[str | None] = mapped_column(Text, comment="帮助文本")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<AssetCustomField(field_name={self.field_name}, display_name={self.display_name})>"


class ProjectOwnershipRelation(Base):
    """项目-权属方多对多关系表（简化版）"""

    __tablename__ = "project_ownership_relations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id"), index=True, nullable=False, comment="项目ID"
    )
    ownership_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ownerships.id"),
        index=True,
        nullable=False,
        comment="权属方ID",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否有效"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关联关系
    project: Mapped["Project"] = relationship(
        "Project", back_populates="ownership_relations"
    )
    ownership: Mapped["Ownership"] = relationship(
        "Ownership", back_populates="ownership_relations"
    )

    def __repr__(self) -> str:
        return f"<ProjectOwnershipRelation(project_id={self.project_id}, ownership_id={self.ownership_id})>"


class Project(Base):
    """项目模型"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    short_name: Mapped[str | None] = mapped_column(String(100), comment="项目简称")
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="项目编码"
    )
    project_type: Mapped[str | None] = mapped_column(String(50), comment="项目类型")
    project_scale: Mapped[str | None] = mapped_column(String(50), comment="项目规模")
    project_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="规划中", comment="项目状态"
    )
    start_date: Mapped[date | None] = mapped_column(Date, comment="开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, comment="结束日期")
    expected_completion_date: Mapped[date | None] = mapped_column(
        Date, comment="预计完成日期"
    )
    actual_completion_date: Mapped[date | None] = mapped_column(
        Date, comment="实际完成日期"
    )

    # 地址信息
    address: Mapped[str | None] = mapped_column(String(500), comment="项目地址")
    city: Mapped[str | None] = mapped_column(String(100), comment="城市")
    district: Mapped[str | None] = mapped_column(String(100), comment="区域")
    province: Mapped[str | None] = mapped_column(String(100), comment="省份")

    # 联系信息
    project_manager: Mapped[str | None] = mapped_column(String(100), comment="项目经理")
    project_phone: Mapped[str | None] = mapped_column(String(50), comment="项目电话")
    project_email: Mapped[str | None] = mapped_column(String(100), comment="项目邮箱")

    # 投资信息
    total_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="总投资"
    )
    planned_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="计划投资"
    )
    actual_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="实际投资"
    )
    project_budget: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="项目预算"
    )

    # 项目描述
    project_description: Mapped[str | None] = mapped_column(Text, comment="项目描述")
    project_objectives: Mapped[str | None] = mapped_column(Text, comment="项目目标")
    project_scope: Mapped[str | None] = mapped_column(Text, comment="项目范围")

    # 相关单位
    management_entity: Mapped[str | None] = mapped_column(
        String(200), comment="管理单位"
    )
    ownership_entity: Mapped[str | None] = mapped_column(
        String(200), comment="权属单位"
    )
    construction_company: Mapped[str | None] = mapped_column(
        String(200), comment="施工单位"
    )
    design_company: Mapped[str | None] = mapped_column(String(200), comment="设计单位")
    supervision_company: Mapped[str | None] = mapped_column(
        String(200), comment="监理单位"
    )

    # 系统字段
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关联关系
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan"
    )
    ownership_relations: Mapped[list["ProjectOwnershipRelation"]] = relationship(
        "ProjectOwnershipRelation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, code={self.code})>"


class Ownership(Base):
    """权属方模型"""

    __tablename__ = "ownerships"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="权属方全称")
    code: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="权属方编码"
    )
    short_name: Mapped[str | None] = mapped_column(String(100), comment="权属方简称")
    # 以下字段已删除: contact_person, contact_phone, contact_email, registration_number, legal_representative, business_scope, established_date, registered_capital
    address: Mapped[str | None] = mapped_column(String(500), comment="地址")
    management_entity: Mapped[str | None] = mapped_column(
        String(200), comment="管理单位"
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 系统字段
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="状态"
    )
    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关联关系
    owned_rent_contracts: Mapped[list["RentContract"]] = relationship(
        "RentContract", back_populates="ownership", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="ownership", passive_deletes=True
    )  # 注意：不使用 cascade="all, delete-orphan"，因为资产不应随权属方删除而自动删除
    ownership_relations: Mapped[list["ProjectOwnershipRelation"]] = relationship(
        "ProjectOwnershipRelation",
        back_populates="ownership",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Ownership(id={self.id}, name={self.name}, code={self.code})>"
