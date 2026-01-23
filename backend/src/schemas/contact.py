"""
联系人相关的 Pydantic 模型
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class ContactType(str, Enum):
    """联系人类型枚举"""

    PRIMARY = "primary"
    FINANCE = "finance"
    OPERATIONS = "operations"
    LEGAL = "legal"
    GENERAL = "general"


class ContactBase(BaseModel):
    """联系人基础模型"""

    name: str = Field(..., description="联系人姓名", max_length=100)
    title: str | None = Field(None, description="职位/头衔", max_length=100)
    department: str | None = Field(None, description="部门", max_length=100)
    phone: str | None = Field(None, description="手机号码", max_length=20)
    office_phone: str | None = Field(None, description="办公电话", max_length=20)
    email: EmailStr | None = Field(None, description="电子邮箱")
    wechat: str | None = Field(None, description="微信号", max_length=100)
    address: str | None = Field(None, description="地址", max_length=500)
    contact_type: ContactType = Field(
        default=ContactType.GENERAL, description="联系人类型"
    )
    is_primary: bool = Field(default=False, description="是否主要联系人")
    notes: str | None = Field(None, description="备注")
    preferred_contact_time: str | None = Field(
        None, description="偏好联系时间", max_length=100
    )
    preferred_contact_method: str | None = Field(
        None, description="偏好联系方式", max_length=50
    )


class ContactCreate(ContactBase):
    """创建联系人模型"""

    entity_type: str = Field(..., description="关联实体类型: ownership/project/tenant")
    entity_id: str = Field(..., description="关联实体ID")


class ContactUpdate(BaseModel):
    """更新联系人模型"""

    name: str | None = Field(None, max_length=100)
    title: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    office_phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = Field(None)
    wechat: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=500)
    contact_type: ContactType | None = None
    is_primary: bool | None = None
    notes: str | None = None
    preferred_contact_time: str | None = Field(None, max_length=100)
    preferred_contact_method: str | None = Field(None, max_length=50)


class ContactResponse(ContactBase):
    """联系人响应模型"""

    id: str
    entity_type: str
    entity_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """联系人列表响应模型"""

    items: list[ContactResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PrimaryContactResponse(BaseModel):
    """主要联系人响应模型"""

    id: str
    name: str
    title: str | None
    phone: str | None
    email: str | None
    wechat: str | None
    preferred_contact_method: str | None

    class Config:
        from_attributes = True
