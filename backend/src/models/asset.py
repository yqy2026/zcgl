"""
资产相关数据库模型
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..database import Base


class Asset(Base):
    """资产信息表"""
    
    __tablename__ = "assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 权属信息
    ownership_entity = Column(String, nullable=False, comment="权属方")
    management_entity = Column(String, comment="经营管理方")
    ownership_category = Column(String, comment="权属类别")
    
    # 基本信息
    property_name = Column(String, nullable=False, comment="物业名称")
    address = Column(String, nullable=False, comment="所在地址")
    
    # 面积信息（平方米）
    land_area = Column(Float, comment="土地面积")
    actual_property_area = Column(Float, nullable=False, comment="实际房产面积")
    rentable_area = Column(Float, nullable=False, comment="经营性物业可出租面积")
    rented_area = Column(Float, nullable=False, comment="经营性物业已出租面积")
    unrented_area = Column(Float, nullable=False, comment="经营性物业未出租面积")
    non_commercial_area = Column(Float, nullable=False, comment="非经营物业面积")
    
    # 确权和用途信息
    ownership_status = Column(String, nullable=False, comment="是否确权（已确权、未确权、部分确权）")
    certificated_usage = Column(String, comment="证载用途")
    actual_usage = Column(String, nullable=False, comment="实际用途")
    business_category = Column(String, comment="业态类别")
    
    # 使用状态
    usage_status = Column(String, nullable=False, comment="物业使用状态（出租、闲置、自用、公房、其他）")
    is_litigated = Column(String, nullable=False, comment="是否涉诉")
    property_nature = Column(String, nullable=False, comment="物业性质（经营类、非经营类）")
    
    # 经营信息
    business_model = Column(String, comment="经营模式")
    include_in_occupancy_rate = Column(String, comment="是否计入出租率")
    occupancy_rate = Column(String, nullable=False, comment="出租率")
    
    # 合同信息
    lease_contract = Column(String, comment="承租合同/代理协议")
    current_contract_start_date = Column(DateTime, comment="现合同开始日期")
    current_contract_end_date = Column(DateTime, comment="现合同结束日期")
    tenant_name = Column(String, comment="租户名称")
    current_lease_contract = Column(String, comment="现租赁合同")
    current_terminal_contract = Column(String, comment="现终端出租合同")
    
    # 项目信息
    wuyang_project_name = Column(String, comment="五羊运营项目名称")
    agreement_start_date = Column(DateTime, comment="协议开始日期")
    agreement_end_date = Column(DateTime, comment="协议结束日期")
    
    # 备注和说明
    description = Column(Text, comment="说明")
    notes = Column(Text, comment="其他备注")
    
    # 系统字段
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关联关系
    history = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")
    documents = relationship("AssetDocument", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name={self.property_name})>"


class AssetHistory(Base):
    """资产变更历史表"""
    
    __tablename__ = "asset_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    change_type = Column(String, nullable=False, comment="变更类型（create/update/delete）")
    changed_fields = Column(JSON, comment="变更字段列表")
    old_values = Column(JSON, comment="变更前的值")
    new_values = Column(JSON, comment="变更后的值")
    changed_by = Column(String, default="system", comment="变更人")
    changed_at = Column(DateTime, default=datetime.utcnow, comment="变更时间")
    reason = Column(String, comment="变更原因")
    
    # 关联关系
    asset = relationship("Asset", back_populates="history")

    def __repr__(self) -> str:
        return f"<AssetHistory(id={self.id}, asset_id={self.asset_id}, type={self.change_type})>"


class AssetDocument(Base):
    """资产文档表"""
    
    __tablename__ = "asset_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    file_name = Column(String, nullable=False, comment="文件名")
    file_path = Column(String, nullable=False, comment="文件路径")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    mime_type = Column(String, nullable=False, comment="文件类型")
    uploaded_at = Column(DateTime, default=datetime.utcnow, comment="上传时间")
    
    # 关联关系
    asset = relationship("Asset", back_populates="documents")

    def __repr__(self) -> str:
        return f"<AssetDocument(id={self.id}, name={self.file_name})>"