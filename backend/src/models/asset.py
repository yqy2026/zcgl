"""
资产相关数据库模型
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Text, ForeignKey, JSON, Boolean, Date, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from ..database import Base


class Asset(Base):
    """资产模型"""
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
    ownership_entity = Column(String(200), nullable=False, comment="权属方")
    ownership_category = Column(String(100), comment="权属类别")
    project_name = Column(String(200), comment="项目名称")
    property_name = Column(String(200), nullable=False, comment="物业名称")
    address = Column(String(500), nullable=False, comment="物业地址")
    ownership_status = Column(String(50), nullable=False, comment="确权状态")
    property_nature = Column(String(50), nullable=False, comment="物业性质")
    usage_status = Column(String(50), nullable=False, comment="使用状态")
    business_category = Column(String(100), comment="业态类别")
    is_litigated = Column(Boolean, nullable=False, default=False, comment="是否涉诉")
    notes = Column(Text, comment="备注")
    
    # 面积相关字段
    land_area = Column(DECIMAL(12, 2), comment="土地面积（平方米）")
    actual_property_area = Column(DECIMAL(12, 2), comment="实际房产面积（平方米）")
    rentable_area = Column(DECIMAL(12, 2), comment="可出租面积（平方米）")
    rented_area = Column(DECIMAL(12, 2), comment="已出租面积（平方米）")
    # unrented_area 和 occupancy_rate 改为计算字段，不存储在数据库中
    non_commercial_area = Column(DECIMAL(12, 2), comment="非经营物业面积（平方米）")
    # occupancy_rate 字段已移除，改为计算字段
    include_in_occupancy_rate = Column(Boolean, nullable=False, default=True, comment="是否计入出租率统计")
    
    # 用途相关字段
    certificated_usage = Column(String(100), comment="证载用途")
    actual_usage = Column(String(100), comment="实际用途")
    
    # 租户相关字段
    tenant_name = Column(String(200), comment="租户名称")
    tenant_type = Column(String(20), comment="租户类型")
    
    # 合同相关字段
    lease_contract_number = Column(String(100), comment="租赁合同编号")
    contract_start_date = Column(Date, comment="合同开始日期")
    contract_end_date = Column(Date, comment="合同结束日期")
    monthly_rent = Column(DECIMAL(15, 2), comment="月租金（元）")
    deposit = Column(DECIMAL(15, 2), comment="押金（元）")
    is_sublease = Column(Boolean, nullable=False, default=False, comment="是否分租/转租")
    sublease_notes = Column(Text, comment="分租/转租备注")
    
    # 管理相关字段
    business_model = Column(String(50), comment="接收模式")
    operation_status = Column(String(20), comment="经营状态")
    manager_name = Column(String(100), comment="管理责任人（网格员）")

    # 财务相关字段已移除
    # annual_income, annual_expense, net_income 字段已移除

    # 接收相关字段
    operation_agreement_start_date = Column(Date, comment="接收协议开始日期")
    operation_agreement_end_date = Column(Date, comment="接收协议结束日期")
    operation_agreement_attachments = Column(Text, comment="接收协议文件")

    # 终端合同相关字段
    terminal_contract_files = Column(Text, comment="终端合同文件")
    
    # 项目相关字段
    
    # 系统字段
    data_status = Column(String(20), nullable=False, default="正常", comment="数据状态")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    tags = Column(Text, comment="标签")
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes = Column(Text, comment="审核备注")

   

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 多租户支持
    tenant_id = Column(String(50), nullable=True, comment="租户ID")
    
    # 关联关系
    history_records = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")
    documents = relationship("AssetDocument", back_populates="asset", cascade="all, delete-orphan")
    rent_contracts = relationship("RentContract", back_populates="asset", cascade="all, delete-orphan")
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, comment="项目ID")
    ownership_id = Column(String, ForeignKey("ownerships.id"), nullable=True, comment="权属方ID")

    # 关系定义
    project = relationship("Project", back_populates="assets")
    ownership = relationship("Ownership", back_populates="assets")

    # 计算属性 - 未出租面积（自动计算，不存储）
    @property
    def unrented_area(self) -> Decimal:
        """计算未出租面积"""
        rentable = self.rentable_area or Decimal('0')
        rented = self.rented_area or Decimal('0')
        return max(rentable - rented, Decimal('0'))

    # 计算属性 - 出租率（自动计算，不存储）
    @property
    def occupancy_rate(self) -> Decimal:
        """计算出租率（百分比）"""
        if not self.include_in_occupancy_rate:
            return Decimal('0')

        rentable = self.rentable_area or Decimal('0')
        if rentable == 0:
            return Decimal('0')

        rented = self.rented_area or Decimal('0')
        rate = (rented / rentable) * Decimal('100')
        return round(rate, 2)

    def __repr__(self):
        return f"<Asset(id={self.id}, name={self.property_name})>"


class AssetHistory(Base):
    """资产变更历史模型"""
    __tablename__ = "asset_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    operation_type = Column(String(50), nullable=False, comment="操作类型")
    field_name = Column(String(100), comment="字段名称")
    old_value = Column(Text, comment="原值")
    new_value = Column(Text, comment="新值")
    operator = Column(String(100), comment="操作人")
    operation_time = Column(DateTime, default=datetime.utcnow, comment="操作时间")
    description = Column(Text, comment="操作描述")
    
    # 新增审计字段
    change_reason = Column(String(200), nullable=True, comment="变更原因")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    session_id = Column(String(100), nullable=True, comment="会话ID")
    
    # 关联关系
    asset = relationship("Asset", back_populates="history_records")

    def __repr__(self):
        return f"<AssetHistory(id={self.id}, asset_id={self.asset_id}, operation={self.operation_type})>"


class AssetDocument(Base):
    """资产文档模型"""
    __tablename__ = "asset_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    document_name = Column(String(200), nullable=False, comment="文档名称")
    document_type = Column(String(50), nullable=False, comment="文档类型")
    file_path = Column(String(500), comment="文件路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    mime_type = Column(String(100), comment="文件MIME类型")
    upload_time = Column(DateTime, default=datetime.utcnow, comment="上传时间")
    uploader = Column(String(100), comment="上传人")
    description = Column(Text, comment="文档描述")
    
    # 关联关系
    asset = relationship("Asset", back_populates="documents")

    def __repr__(self):
        return f"<AssetDocument(id={self.id}, name={self.document_name})>"


class SystemDictionary(Base):
    """系统数据字典模型"""
    __tablename__ = "system_dictionaries"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    dict_type = Column(String(50), nullable=False, comment="字典类型")
    dict_code = Column(String(50), nullable=False, comment="字典编码")
    dict_label = Column(String(100), nullable=False, comment="字典标签")
    dict_value = Column(String(100), nullable=False, comment="字典值")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<SystemDictionary(type={self.dict_type}, code={self.dict_code}, label={self.dict_label})>"


class AssetCustomField(Base):
    """资产自定义字段模型"""
    __tablename__ = "asset_custom_fields"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    field_name = Column(String(100), nullable=False, comment="字段名称")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    field_type = Column(String(20), nullable=False, comment="字段类型")
    is_required = Column(Boolean, nullable=False, default=False, comment="是否必填")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序")
    default_value = Column(Text, nullable=True, comment="默认值")
    field_options = Column(Text, nullable=True, comment="字段选项(JSON)")
    validation_rules = Column(Text, nullable=True, comment="验证规则(JSON)")
    help_text = Column(Text, nullable=True, comment="帮助文本")
    description = Column(Text, nullable=True, comment="描述")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<AssetCustomField(field_name={self.field_name}, display_name={self.display_name})>"


class ProjectOwnershipRelation(Base):
    """项目-权属方多对多关系表（简化版）"""
    __tablename__ = "project_ownership_relations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, comment="项目ID")
    ownership_id = Column(String, ForeignKey("ownerships.id"), nullable=False, comment="权属方ID")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否有效")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String(100), nullable=True, comment="创建人")
    updated_by = Column(String(100), nullable=True, comment="更新人")

    # 关联关系
    project = relationship("Project", back_populates="ownership_relations")
    ownership = relationship("Ownership", back_populates="ownership_relations")

    def __repr__(self):
        return f"<ProjectOwnershipRelation(project_id={self.project_id}, ownership_id={self.ownership_id})>"


class Project(Base):
    """项目模型"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(200), nullable=False, comment="项目名称")
    short_name = Column(String(100), nullable=True, comment="项目简称")
    code = Column(String(100), unique=True, nullable=False, comment="项目编码")
    project_type = Column(String(50), nullable=True, comment="项目类型")
    project_scale = Column(String(50), nullable=True, comment="项目规模")
    project_status = Column(String(50), nullable=False, default="规划中", comment="项目状态")
    start_date = Column(Date, nullable=True, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期")
    expected_completion_date = Column(Date, nullable=True, comment="预计完成日期")
    actual_completion_date = Column(Date, nullable=True, comment="实际完成日期")

    # 地址信息
    address = Column(String(500), nullable=True, comment="项目地址")
    city = Column(String(100), nullable=True, comment="城市")
    district = Column(String(100), nullable=True, comment="区域")
    province = Column(String(100), nullable=True, comment="省份")

    # 联系信息
    project_manager = Column(String(100), nullable=True, comment="项目经理")
    project_phone = Column(String(50), nullable=True, comment="项目电话")
    project_email = Column(String(100), nullable=True, comment="项目邮箱")

    # 投资信息
    total_investment = Column(DECIMAL(15, 2), nullable=True, comment="总投资")
    planned_investment = Column(DECIMAL(15, 2), nullable=True, comment="计划投资")
    actual_investment = Column(DECIMAL(15, 2), nullable=True, comment="实际投资")
    project_budget = Column(DECIMAL(15, 2), nullable=True, comment="项目预算")

    # 项目描述
    project_description = Column(Text, nullable=True, comment="项目描述")
    project_objectives = Column(Text, nullable=True, comment="项目目标")
    project_scope = Column(Text, nullable=True, comment="项目范围")

    # 相关单位
    management_entity = Column(String(200), nullable=True, comment="管理单位")
    ownership_entity = Column(String(200), nullable=True, comment="权属单位")
    construction_company = Column(String(200), nullable=True, comment="施工单位")
    design_company = Column(String(200), nullable=True, comment="设计单位")
    supervision_company = Column(String(200), nullable=True, comment="监理单位")

    # 系统字段
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    data_status = Column(String(20), nullable=False, default="正常", comment="数据状态")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String(100), nullable=True, comment="创建人")
    updated_by = Column(String(100), nullable=True, comment="更新人")

    # 关联关系
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    ownership_relations = relationship("ProjectOwnershipRelation", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, code={self.code})>"


class Ownership(Base):
    """权属方模型"""
    __tablename__ = "ownerships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(200), nullable=False, comment="权属方全称")
    code = Column(String(100), nullable=False, comment="权属方编码")
    short_name = Column(String(100), nullable=True, comment="权属方简称")
    # 以下字段已删除: contact_person, contact_phone, contact_email, registration_number, legal_representative, business_scope, established_date, registered_capital
    address = Column(String(500), nullable=True, comment="地址")
    management_entity = Column(String(200), nullable=True, comment="管理单位")
    notes = Column(Text, nullable=True, comment="备注")

    # 系统字段
    is_active = Column(Boolean, nullable=False, default=True, comment="状态")
    data_status = Column(String(20), nullable=False, default="正常", comment="数据状态")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String(100), nullable=True, comment="创建人")
    updated_by = Column(String(100), nullable=True, comment="更新人")

    # 关联关系
    owned_rent_contracts = relationship("RentContract", back_populates="ownership", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="ownership")
    ownership_relations = relationship("ProjectOwnershipRelation", back_populates="ownership", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Ownership(id={self.id}, name={self.name}, code={self.code})>"