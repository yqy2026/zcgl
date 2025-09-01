"""
资产相关的Pydantic模型
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class OwnershipStatus(str, Enum):
    """确权状态枚举"""
    CONFIRMED = "已确权"
    UNCONFIRMED = "未确权"
    PARTIAL = "部分确权"


class PropertyNature(str, Enum):
    """物业性质枚举"""
    COMMERCIAL = "经营性"
    NON_COMMERCIAL = "非经营性"


class UsageStatus(str, Enum):
    """使用状态枚举"""
    RENTED = "出租"
    SELF_USED = "自用"
    VACANT = "空置"


class AssetBase(BaseModel):
    """资产基础模型"""
    property_name: str = Field(..., min_length=1, max_length=200, description="物业名称")
    address: str = Field(..., min_length=1, max_length=500, description="地址")
    ownership_status: OwnershipStatus = Field(..., description="确权状态")
    property_nature: PropertyNature = Field(..., description="物业性质")
    usage_status: UsageStatus = Field(..., description="使用状态")
    ownership_entity: str = Field(..., min_length=1, max_length=200, description="权属方")
    management_entity: Optional[str] = Field(None, max_length=200, description="经营管理方")
    business_category: Optional[str] = Field(None, max_length=100, description="业态类别")
    total_area: Optional[float] = Field(None, ge=0, description="总面积(平方米)")
    usable_area: Optional[float] = Field(None, ge=0, description="可使用面积(平方米)")
    is_litigated: str = Field("否", description="是否涉诉")
    notes: Optional[str] = Field(None, description="备注")

    @validator('total_area', 'usable_area')
    def validate_area(cls, v):
        if v is not None and v < 0:
            raise ValueError('面积不能为负数')
        return v

    @validator('is_litigated')
    def validate_is_litigated(cls, v):
        if v not in ['是', '否']:
            raise ValueError('是否涉诉只能是"是"或"否"')
        return v


class AssetCreate(AssetBase):
    """创建资产模型"""
    pass


class AssetUpdate(BaseModel):
    """更新资产模型"""
    property_name: Optional[str] = Field(None, min_length=1, max_length=200, description="物业名称")
    address: Optional[str] = Field(None, min_length=1, max_length=500, description="地址")
    ownership_status: Optional[OwnershipStatus] = Field(None, description="确权状态")
    property_nature: Optional[PropertyNature] = Field(None, description="物业性质")
    usage_status: Optional[UsageStatus] = Field(None, description="使用状态")
    ownership_entity: Optional[str] = Field(None, min_length=1, max_length=200, description="权属方")
    management_entity: Optional[str] = Field(None, max_length=200, description="经营管理方")
    business_category: Optional[str] = Field(None, max_length=100, description="业态类别")
    total_area: Optional[float] = Field(None, ge=0, description="总面积(平方米)")
    usable_area: Optional[float] = Field(None, ge=0, description="可使用面积(平方米)")
    is_litigated: Optional[str] = Field(None, description="是否涉诉")
    notes: Optional[str] = Field(None, description="备注")

    @validator('total_area', 'usable_area')
    def validate_area(cls, v):
        if v is not None and v < 0:
            raise ValueError('面积不能为负数')
        return v

    @validator('is_litigated')
    def validate_is_litigated(cls, v):
        if v is not None and v not in ['是', '否']:
            raise ValueError('是否涉诉只能是"是"或"否"')
        return v


class AssetResponse(AssetBase):
    """资产响应模型"""
    id: str = Field(..., description="资产ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """资产列表响应模型"""
    items: List[AssetResponse] = Field(..., description="资产列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页记录数")
    pages: int = Field(..., description="总页数")


class AssetHistoryResponse(BaseModel):
    """资产历史响应模型"""
    id: str = Field(..., description="历史记录ID")
    asset_id: str = Field(..., description="资产ID")
    operation_type: str = Field(..., description="操作类型")
    field_name: Optional[str] = Field(None, description="字段名称")
    old_value: Optional[str] = Field(None, description="原值")
    new_value: Optional[str] = Field(None, description="新值")
    operator: Optional[str] = Field(None, description="操作人")
    operation_time: datetime = Field(..., description="操作时间")
    description: Optional[str] = Field(None, description="操作描述")

    class Config:
        from_attributes = True


class AssetDocumentResponse(BaseModel):
    """资产文档响应模型"""
    id: str = Field(..., description="文档ID")
    asset_id: str = Field(..., description="资产ID")
    document_name: str = Field(..., description="文档名称")
    document_type: str = Field(..., description="文档类型")
    file_path: Optional[str] = Field(None, description="文件路径")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    upload_time: datetime = Field(..., description="上传时间")
    uploader: Optional[str] = Field(None, description="上传人")
    description: Optional[str] = Field(None, description="文档描述")

    class Config:
        from_attributes = True