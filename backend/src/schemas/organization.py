"""
组织架构相关数据验证模式
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class OrganizationBase(BaseModel):
    """组织架构基础模式"""
    name: str = Field(..., min_length=1, max_length=200, description="组织名称")
    code: str = Field(..., min_length=1, max_length=50, description="组织编码")
    level: int = Field(default=1, ge=1, le=10, description="组织层级")
    sort_order: int = Field(default=0, ge=0, description="排序")
    parent_id: Optional[str] = Field(None, description="上级组织ID")

    # 组织基本信息
    type: str = Field(..., description="组织类型")
    status: str = Field(..., description="状态")

    # 联系信息
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=200, description="地址")

    # 负责人信息
    leader_name: Optional[str] = Field(None, max_length=50, description="负责人姓名")
    leader_phone: Optional[str] = Field(None, max_length=20, description="负责人电话")
    leader_email: Optional[str] = Field(None, max_length=100, description="负责人邮箱")

    # 其他信息
    description: Optional[str] = Field(None, max_length=1000, description="组织描述")
    functions: Optional[str] = Field(None, max_length=1000, description="主要职能")

    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['company', 'department', 'group', 'division', 'team', 'branch', 'office']
        if v not in allowed_types:
            raise ValueError(f'type must be one of {allowed_types}')
        return v

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'suspended']
        if v not in allowed_statuses:
            raise ValueError(f'status must be one of {allowed_statuses}')
        return v




class OrganizationCreate(OrganizationBase):
    """创建组织架构模式"""
    created_by: Optional[str] = Field(None, max_length=100, description="创建人")


class OrganizationUpdate(BaseModel):
    """更新组织架构模式"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="组织名称")
    code: Optional[str] = Field(None, min_length=1, max_length=50, description="组织编码")
    level: Optional[int] = Field(None, ge=1, le=10, description="组织层级")
    sort_order: Optional[int] = Field(None, ge=0, description="排序")
    parent_id: Optional[str] = Field(None, description="上级组织ID")

    # 组织基本信息
    type: Optional[str] = Field(None, description="组织类型")
    status: Optional[str] = Field(None, description="状态")

    # 联系信息
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=200, description="地址")

    # 负责人信息
    leader_name: Optional[str] = Field(None, max_length=50, description="负责人姓名")
    leader_phone: Optional[str] = Field(None, max_length=20, description="负责人电话")
    leader_email: Optional[str] = Field(None, max_length=100, description="负责人邮箱")

    # 其他信息
    description: Optional[str] = Field(None, max_length=1000, description="组织描述")
    functions: Optional[str] = Field(None, max_length=1000, description="主要职能")

    updated_by: Optional[str] = Field(None, max_length=100, description="更新人")

    @validator('type')
    def validate_type(cls, v):
        if v is None:
            return v
        allowed_types = ['company', 'department', 'group', 'division', 'team', 'branch', 'office']
        if v not in allowed_types:
            raise ValueError(f'type must be one of {allowed_types}')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        allowed_statuses = ['active', 'inactive', 'suspended']
        if v not in allowed_statuses:
            raise ValueError(f'status must be one of {allowed_statuses}')
        return v




class OrganizationResponse(OrganizationBase):
    """组织架构响应模式"""
    id: str
    path: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    # 子组织列表
    children: Optional[List['OrganizationResponse']] = []
    
    class Config:
        from_attributes = True


class OrganizationTree(BaseModel):
    """组织架构树形结构"""
    id: str
    name: str
    level: int
    sort_order: int
    children: List['OrganizationTree'] = []
    
    class Config:
        from_attributes = True


class OrganizationHistoryResponse(BaseModel):
    """组织架构历史响应模式"""
    id: str
    organization_id: str
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_reason: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationStatistics(BaseModel):
    """组织架构统计信息"""
    total: int = Field(..., description="总数")
    active: int = Field(..., description="活跃数量")
    inactive: int = Field(..., description="非活跃数量")
    by_type: dict = Field(..., description="按类型统计")
    by_level: dict = Field(..., description="按层级统计")


class OrganizationMoveRequest(BaseModel):
    """组织移动请求"""
    target_parent_id: Optional[str] = Field(None, description="目标上级组织ID")
    sort_order: Optional[int] = Field(None, ge=0, description="新排序位置")
    updated_by: Optional[str] = Field(None, max_length=100, description="操作人")


class OrganizationBatchRequest(BaseModel):
    """批量操作请求"""
    organization_ids: List[str] = Field(..., description="组织ID列表")
    action: str = Field(..., description="操作类型")
    updated_by: Optional[str] = Field(None, max_length=100, description="操作人")

    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['delete', 'move']
        if v not in allowed_actions:
            raise ValueError(f'action must be one of {allowed_actions}')
        return v


class OrganizationSearchRequest(BaseModel):
    """组织搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    level: Optional[int] = Field(None, ge=1, le=10, description="层级")
    parent_id: Optional[str] = Field(None, description="上级组织ID")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(100, ge=1, le=1000, description="限制数量")


# 更新前向引用
OrganizationResponse.model_rebuild()
OrganizationTree.model_rebuild()