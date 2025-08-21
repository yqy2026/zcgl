"""
资产相关的Pydantic数据验证模型
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OwnershipStatus(str, Enum):
    """确权状态枚举"""
    CONFIRMED = "已确权"
    UNCONFIRMED = "未确权"
    PARTIAL = "部分确权"


class UsageStatus(str, Enum):
    """使用状态枚举"""
    RENTED = "出租"
    VACANT = "闲置"
    SELF_USE = "自用"
    PUBLIC = "公房"
    OTHER = "其他"


class PropertyNature(str, Enum):
    """物业性质枚举"""
    COMMERCIAL = "经营类"
    NON_COMMERCIAL = "非经营类"


class AssetBase(BaseModel):
    """资产基础模型"""
    
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    # 权属信息
    ownership_entity: str = Field(..., description="权属方", min_length=1, max_length=100)
    management_entity: Optional[str] = Field(None, description="经营管理方", max_length=100)
    ownership_category: Optional[str] = Field(None, description="权属类别", max_length=50)
    
    # 基本信息
    property_name: str = Field(..., description="物业名称", min_length=1, max_length=200)
    address: str = Field(..., description="所在地址", min_length=1, max_length=500)
    
    # 面积信息（平方米）
    land_area: Optional[float] = Field(None, description="土地面积", ge=0)
    actual_property_area: float = Field(..., description="实际房产面积", gt=0)
    rentable_area: float = Field(..., description="经营性物业可出租面积", ge=0)
    rented_area: float = Field(..., description="经营性物业已出租面积", ge=0)
    unrented_area: float = Field(..., description="经营性物业未出租面积", ge=0)
    non_commercial_area: float = Field(..., description="非经营物业面积", ge=0)
    
    # 确权和用途信息
    ownership_status: OwnershipStatus = Field(..., description="是否确权")
    certificated_usage: Optional[str] = Field(None, description="证载用途", max_length=100)
    actual_usage: str = Field(..., description="实际用途", min_length=1, max_length=100)
    business_category: Optional[str] = Field(None, description="业态类别", max_length=100)
    
    # 使用状态
    usage_status: UsageStatus = Field(..., description="物业使用状态")
    is_litigated: str = Field(..., description="是否涉诉", pattern="^(是|否)$")
    property_nature: PropertyNature = Field(..., description="物业性质")
    
    # 经营信息
    business_model: Optional[str] = Field(None, description="经营模式", max_length=100)
    include_in_occupancy_rate: Optional[str] = Field(None, description="是否计入出租率", max_length=50)
    occupancy_rate: str = Field(..., description="出租率", max_length=20)
    
    # 合同信息
    lease_contract: Optional[str] = Field(None, description="承租合同/代理协议", max_length=500)
    current_contract_start_date: Optional[datetime] = Field(None, description="现合同开始日期")
    current_contract_end_date: Optional[datetime] = Field(None, description="现合同结束日期")
    tenant_name: Optional[str] = Field(None, description="租户名称", max_length=200)
    current_lease_contract: Optional[str] = Field(None, description="现租赁合同", max_length=500)
    current_terminal_contract: Optional[str] = Field(None, description="现终端出租合同", max_length=500)
    
    # 项目信息
    wuyang_project_name: Optional[str] = Field(None, description="五羊运营项目名称", max_length=200)
    agreement_start_date: Optional[datetime] = Field(None, description="协议开始日期")
    agreement_end_date: Optional[datetime] = Field(None, description="协议结束日期")
    
    # 备注和说明
    description: Optional[str] = Field(None, description="说明", max_length=1000)
    notes: Optional[str] = Field(None, description="其他备注", max_length=1000)

    @field_validator('rented_area')
    @classmethod
    def validate_rented_area(cls, v, info):
        """验证已出租面积不能超过可出租面积"""
        if info.data and 'rentable_area' in info.data and v > info.data['rentable_area']:
            raise ValueError('已出租面积不能超过可出租面积')
        return v

    @field_validator('unrented_area')
    @classmethod
    def validate_unrented_area(cls, v, info):
        """验证未出租面积相关的业务规则"""
        if info.data and 'rentable_area' in info.data:
            # 验证未出租面积不能超过可出租面积
            if v > info.data['rentable_area']:
                raise ValueError('未出租面积不能超过可出租面积')
            
            # 验证已出租面积和未出租面积之和不能超过可出租面积
            if ('rented_area' in info.data and 
                info.data['rented_area'] is not None):
                total_used = info.data['rented_area'] + v
                if total_used > info.data['rentable_area']:
                    raise ValueError('已出租面积和未出租面积之和不能超过可出租面积')
        return v

    @field_validator('current_contract_end_date')
    @classmethod
    def validate_contract_dates(cls, v, info):
        """验证合同结束日期必须晚于开始日期"""
        if v and info.data and 'current_contract_start_date' in info.data and info.data['current_contract_start_date']:
            if v <= info.data['current_contract_start_date']:
                raise ValueError('合同结束日期必须晚于开始日期')
        return v

    @field_validator('agreement_end_date')
    @classmethod
    def validate_agreement_dates(cls, v, info):
        """验证协议结束日期必须晚于开始日期"""
        if v and info.data and 'agreement_start_date' in info.data and info.data['agreement_start_date']:
            if v <= info.data['agreement_start_date']:
                raise ValueError('协议结束日期必须晚于开始日期')
        return v


class AssetCreate(AssetBase):
    """创建资产的数据模型"""
    pass


class AssetUpdate(BaseModel):
    """更新资产的数据模型"""
    
    # 所有字段都是可选的，用于部分更新
    ownership_entity: Optional[str] = Field(None, min_length=1, max_length=100)
    management_entity: Optional[str] = Field(None, max_length=100)
    ownership_category: Optional[str] = Field(None, max_length=50)
    
    property_name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    
    land_area: Optional[float] = Field(None, ge=0)
    actual_property_area: Optional[float] = Field(None, gt=0)
    rentable_area: Optional[float] = Field(None, ge=0)
    rented_area: Optional[float] = Field(None, ge=0)
    unrented_area: Optional[float] = Field(None, ge=0)
    non_commercial_area: Optional[float] = Field(None, ge=0)
    
    ownership_status: Optional[OwnershipStatus] = None
    certificated_usage: Optional[str] = Field(None, max_length=100)
    actual_usage: Optional[str] = Field(None, min_length=1, max_length=100)
    business_category: Optional[str] = Field(None, max_length=100)
    
    usage_status: Optional[UsageStatus] = None
    is_litigated: Optional[str] = Field(None, pattern="^(是|否)$")
    property_nature: Optional[PropertyNature] = None
    
    business_model: Optional[str] = Field(None, max_length=100)
    include_in_occupancy_rate: Optional[str] = Field(None, max_length=50)
    occupancy_rate: Optional[str] = Field(None, max_length=20)
    
    lease_contract: Optional[str] = Field(None, max_length=500)
    current_contract_start_date: Optional[datetime] = None
    current_contract_end_date: Optional[datetime] = None
    tenant_name: Optional[str] = Field(None, max_length=200)
    current_lease_contract: Optional[str] = Field(None, max_length=500)
    current_terminal_contract: Optional[str] = Field(None, max_length=500)
    
    wuyang_project_name: Optional[str] = Field(None, max_length=200)
    agreement_start_date: Optional[datetime] = None
    agreement_end_date: Optional[datetime] = None
    
    description: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )


class AssetResponse(AssetBase):
    """资产响应数据模型"""
    
    id: str = Field(..., description="资产ID")
    version: int = Field(..., description="版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )


class AssetHistoryResponse(BaseModel):
    """资产变更历史响应模型"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="历史记录ID")
    asset_id: str = Field(..., description="资产ID")
    change_type: str = Field(..., description="变更类型")
    changed_fields: List[str] = Field(..., description="变更字段列表")
    old_values: Dict[str, Any] = Field(..., description="变更前的值")
    new_values: Dict[str, Any] = Field(..., description="变更后的值")
    changed_by: str = Field(..., description="变更人")
    changed_at: datetime = Field(..., description="变更时间")
    reason: Optional[str] = Field(None, description="变更原因")


class AssetDocumentResponse(BaseModel):
    """资产文档响应模型"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="文档ID")
    asset_id: str = Field(..., description="资产ID")
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    mime_type: str = Field(..., description="文件类型")
    uploaded_at: datetime = Field(..., description="上传时间")


class AssetListResponse(BaseModel):
    """资产列表响应模型"""
    
    data: List[AssetResponse] = Field(..., description="资产列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页记录数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class AssetSearchParams(BaseModel):
    """资产搜索参数模型"""
    
    page: int = Field(1, description="页码", ge=1)
    limit: int = Field(20, description="每页记录数", ge=1, le=100)
    search: Optional[str] = Field(None, description="搜索关键词", max_length=100)
    
    # 筛选条件
    ownership_status: Optional[OwnershipStatus] = Field(None, description="确权状态筛选")
    property_nature: Optional[PropertyNature] = Field(None, description="物业性质筛选")
    usage_status: Optional[UsageStatus] = Field(None, description="使用状态筛选")
    ownership_entity: Optional[str] = Field(None, description="权属方筛选", max_length=100)
    
    # 排序
    sort_field: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向", pattern="^(asc|desc)$")

    model_config = ConfigDict(use_enum_values=True)