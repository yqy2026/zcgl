"""
资产相关数据库模型
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class Asset(Base):
    """资产模型"""
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_name = Column(String(200), nullable=False, unique=True, comment="物业名称")
    address = Column(String(500), nullable=False, comment="地址")
    ownership_status = Column(String(50), nullable=False, comment="确权状态")
    property_nature = Column(String(50), nullable=False, comment="物业性质")
    usage_status = Column(String(50), nullable=False, comment="使用状态")
    ownership_entity = Column(String(200), nullable=False, comment="权属方")
    management_entity = Column(String(200), comment="经营管理方")
    business_category = Column(String(100), comment="业态类别")
    total_area = Column(Float, comment="总面积(平方米)")
    usable_area = Column(Float, comment="可使用面积(平方米)")
    is_litigated = Column(String(10), default="否", comment="是否涉诉")
    notes = Column(Text, comment="备注")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关联关系
    history_records = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")
    documents = relationship("AssetDocument", back_populates="asset", cascade="all, delete-orphan")

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
    upload_time = Column(DateTime, default=datetime.utcnow, comment="上传时间")
    uploader = Column(String(100), comment="上传人")
    description = Column(Text, comment="文档描述")
    
    # 关联关系
    asset = relationship("Asset", back_populates="documents")

    def __repr__(self):
        return f"<AssetDocument(id={self.id}, name={self.document_name})>"