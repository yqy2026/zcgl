"""
Property Certificate Schemas
产权证Pydantic模型定义
"""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


from enum import Enum


# Enums
class CertificateType(str, Enum):
    """产权证类型"""
    REAL_ESTATE = "real_estate"  # 不动产权证（新版）
    HOUSE_OWNERSHIP = "house_ownership"  # 房屋所有权证（旧版）
    LAND_USE = "land_use"  # 土地使用证
    OTHER = "other"  # 其他权属证明


class OwnerType(str, Enum):
    """权利人类型"""
    INDIVIDUAL = "individual"  # 个人
    ORGANIZATION = "organization"  # 组织/企业
    JOINT = "joint"  # 共有


# Base Schemas
class PropertyCertificateBase(BaseModel):
    """产权证基础字段"""
    certificate_number: str = Field(..., description="证书编号")
    certificate_type: CertificateType = Field(..., description="证书类型")
    registration_date: date | None = Field(None, description="登记日期")
    property_address: str | None = Field(None, description="坐落地址")
    property_type: str | None = Field(None, description="用途")
    building_area: str | None = Field(None, description="建筑面积")
    land_area: str | None = Field(None, description="土地面积")
    floor_info: str | None = Field(None, description="楼层信息")
    land_use_type: str | None = Field(None, description="土地使用类型")
    land_use_term_start: date | None = Field(None, description="土地使用期限起")
    land_use_term_end: date | None = Field(None, description="土地使用期限止")
    co_ownership: str | None = Field(None, description="共有情况")
    restrictions: str | None = Field(None, description="权利限制")
    remarks: str | None = Field(None, description="备注")

    model_config = ConfigDict(use_enum_values=True)


class PropertyCertificateCreate(PropertyCertificateBase):
    """创建产权证"""
    asset_ids: list[str] = Field(default_factory=list, description="关联资产ID列表")
    owner_ids: list[str] = Field(default_factory=list, description="关联权利人ID列表")


class PropertyCertificateUpdate(BaseModel):
    """更新产权证"""
    certificate_number: str | None = None
    certificate_type: CertificateType | None = None
    registration_date: date | None = None
    property_address: str | None = None
    property_type: str | None = None
    building_area: str | None = None
    land_area: str | None = None
    floor_info: str | None = None
    land_use_type: str | None = None
    land_use_term_start: date | None = None
    land_use_term_end: date | None = None
    co_ownership: str | None = None
    restrictions: str | None = None
    remarks: str | None = None
    verified: bool | None = None


# Property Owner Schemas
class PropertyOwnerBase(BaseModel):
    """权利人基础字段"""
    owner_type: OwnerType = Field(..., description="权利人类型")
    name: str = Field(..., min_length=1, max_length=200, description="姓名/单位名称")
    id_type: str | None = Field(None, description="证件类型")
    id_number: str | None = Field(None, description="证件号码")
    phone: str | None = Field(None, description="联系电话")
    address: str | None = Field(None, description="地址")
    organization_id: str | None = Field(None, description="关联组织ID")


class PropertyOwnerCreate(PropertyOwnerBase):
    """创建权利人"""
    pass


class PropertyOwnerUpdate(BaseModel):
    """更新权利人"""
    name: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    phone: str | None = None
    address: str | None = None


# Response Schemas
class PropertyOwnerResponse(PropertyOwnerBase):
    """权利人响应"""
    id: str
    created_at: date
    updated_at: date

    model_config = ConfigDict(from_attributes=True)


class PropertyCertificateResponse(PropertyCertificateBase):
    """产权证响应"""
    id: str
    extraction_confidence: float | None
    extraction_source: str
    verified: bool
    created_at: date
    updated_at: date
    owners: list[PropertyOwnerResponse] = []
    asset_ids: list[str] = []

    model_config = ConfigDict(from_attributes=True)


# Extraction Result Schema
class CertificateExtractionResult(BaseModel):
    """证书提取结果"""
    session_id: str
    certificate_type: CertificateType
    extracted_data: dict[str, Any]
    confidence_score: float
    asset_matches: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    warnings: list[str] = []


# Import Confirm Schema
class CertificateImportConfirm(BaseModel):
    """导入确认"""
    session_id: str
    extracted_data: dict[str, Any]
    asset_link_id: str | None = None
    create_new_asset: bool = False
    owners: list[dict[str, Any]] = []
    verified: bool = False


# 产权证提取 Prompt
PROPERTY_CERT_EXTRACTION_PROMPT = """
请从这份不动产权证/房产证图像中提取以下信息，以JSON格式返回：

{
  "certificate_number": "不动产权证号或房产证号",
  "registration_date": "登记日期 (YYYY-MM-DD格式)",
  "owner_name": "权利人姓名或单位名称",
  "owner_id_type": "证件类型 (身份证/营业执照等)",
  "owner_id_number": "证件号码",
  "property_address": "坐落地址 (完整地址)",
  "property_type": "用途 (住宅/商业/工业/办公)",
  "building_area": "建筑面积 (数字，单位㎡)",
  "land_area": "土地使用面积 (数字，单位㎡)",
  "floor_info": "楼层信息",
  "land_use_type": "土地使用权类型 (出让/划拨)",
  "land_use_term_start": "土地使用期限起始日期 (YYYY-MM-DD)",
  "land_use_term_end": "土地使用期限结束日期 (YYYY-MM-DD)",
  "co_ownership": "共有情况",
  "restrictions": "权利限制情况",
  "remarks": "备注"
}

提取规则：
1. 如果某字段无法识别，返回 null
2. 日期统一使用 YYYY-MM-DD 格式
3. 面积只需数字，不需要单位
4. 确保证件号码完整准确
5. 只返回JSON，不要其他说明文字
"""
