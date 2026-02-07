"""
Property Certificate Schema
产权证/不动产权证字段定义

用于从产权证图像中提取结构化数据
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PropertyCertificateFields(BaseModel):
    """产权证提取字段"""

    # 证书基本信息
    certificate_number: str | None = Field(
        default=None, description="不动产权证号/房产证号"
    )
    registration_date: date | None = Field(default=None, description="登记日期")

    # 权利人信息
    owner_name: str | None = Field(default=None, description="权利人名称")
    owner_id_type: str | None = Field(default=None, description="证件类型")
    owner_id_number: str | None = Field(default=None, description="证件号码")

    # 不动产信息
    property_address: str | None = Field(default=None, description="坐落地址")
    property_type: str | None = Field(default=None, description="用途 (住宅/商业/工业)")
    building_area: str | None = Field(
        default=None, description="建筑面积 (㎡)"
    )  # 对齐Model: String类型
    land_area: str | None = Field(
        default=None, description="土地使用面积 (㎡)"
    )  # 对齐Model: String类型
    floor_info: str | None = Field(default=None, description="楼层信息")

    # 土地信息
    land_use_type: str | None = Field(
        default=None, description="土地使用权类型 (出让/划拨)"
    )
    land_use_term_start: date | None = Field(default=None, description="土地使用期限起")
    land_use_term_end: date | None = Field(default=None, description="土地使用期限止")

    # 共有情况
    co_ownership: str | None = Field(default=None, description="共有情况")

    # 其他
    restrictions: str | None = Field(default=None, description="权利限制情况")
    remarks: str | None = Field(default=None, description="备注")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，过滤空值"""
        result = {}
        for field_name, field_value in self.model_dump().items():
            if field_value is not None:
                if isinstance(field_value, (date, Decimal)):
                    result[field_name] = str(field_value)
                else:
                    result[field_name] = field_value
        return result


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


class PropertyCertificateUploadResponse(BaseModel):
    """产权证上传响应"""

    session_id: str = Field(description="会话ID")
    asset_ids: list[str] = []
    certificate_type: str = Field(default="property_cert", description="证书类型")
    extracted_data: dict[str, Any] = Field(
        default_factory=dict, description="提取的字段数据"
    )
    confidence_score: float = Field(ge=0.0, le=1.0, description="置信度分数")
    asset_matches: list[dict[str, Any]] = Field(
        default_factory=list, description="匹配的资产列表"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="验证错误列表"
    )
    warnings: list[str] = Field(default_factory=list, description="警告列表")

    class Config:
        from_attributes = True


class CertificateImportConfirm(BaseModel):
    """产权证导入确认"""

    session_id: str = Field(description="会话ID")
    asset_ids: list[str] = Field(default_factory=list, description="关联资产ID列表")
    extracted_data: dict[str, Any] = Field(description="提取的字段数据")
    asset_link_id: str | None = Field(default=None, description="关联的资产ID")
    should_create_new_asset: bool = Field(default=False, description="是否创建新资产")
    owners: list[dict[str, Any]] = Field(default_factory=list, description="权利人列表")

    class Config:
        from_attributes = True


# CRUD Schemas
class PropertyCertificateBase(BaseModel):
    """产权证基础字段"""

    certificate_number: str = Field(description="证书编号")
    certificate_type: str = Field(description="证书类型")
    registration_date: date | None = Field(default=None, description="登记日期")
    property_address: str | None = Field(default=None, description="坐落地址")
    property_type: str | None = Field(
        default=None, description="用途（住宅/商业/工业/办公）"
    )
    building_area: str | None = Field(default=None, description="建筑面积（平方米）")
    floor_info: str | None = Field(default=None, description="楼层信息")
    land_area: str | None = Field(default=None, description="土地使用面积（平方米）")
    land_use_type: str | None = Field(
        default=None, description="土地使用权类型（出让/划拨）"
    )
    land_use_term_start: date | None = Field(default=None, description="土地使用期限起")
    land_use_term_end: date | None = Field(default=None, description="土地使用期限止")
    co_ownership: str | None = Field(default=None, description="共有情况")
    restrictions: str | None = Field(default=None, description="权利限制情况")
    remarks: str | None = Field(default=None, description="备注")


class PropertyCertificateCreate(PropertyCertificateBase):
    """创建产权证"""

    extraction_confidence: float | None = Field(
        default=None, description="LLM提取置信度"
    )
    extraction_source: str = Field(default="manual", description="数据来源")
    is_verified: bool = Field(default=False, description="是否人工审核")


class PropertyCertificateUpdate(BaseModel):
    """更新产权证"""

    certificate_number: str | None = Field(default=None, description="证书编号")
    certificate_type: str | None = Field(default=None, description="证书类型")
    registration_date: date | None = Field(default=None, description="登记日期")
    property_address: str | None = Field(default=None, description="坐落地址")
    property_type: str | None = Field(default=None, description="用途")
    building_area: str | None = Field(default=None, description="建筑面积")
    floor_info: str | None = Field(default=None, description="楼层信息")
    land_area: str | None = Field(default=None, description="土地使用面积")
    land_use_type: str | None = Field(default=None, description="土地使用权类型")
    land_use_term_start: date | None = Field(default=None, description="土地使用期限起")
    land_use_term_end: date | None = Field(default=None, description="土地使用期限止")
    co_ownership: str | None = Field(default=None, description="共有情况")
    restrictions: str | None = Field(default=None, description="权利限制情况")
    remarks: str | None = Field(default=None, description="备注")
    extraction_confidence: float | None = Field(
        default=None, description="LLM提取置信度"
    )
    extraction_source: str | None = Field(default=None, description="数据来源")
    is_verified: bool | None = Field(default=None, description="是否人工审核")


class PropertyCertificateResponse(PropertyCertificateBase):
    """产权证响应"""

    id: str = Field(description="证书ID")
    asset_ids: list[str] = []
    extraction_confidence: float | None = Field(
        default=None, description="LLM提取置信度"
    )
    extraction_source: str = Field(description="数据来源")
    is_verified: bool = Field(description="是否人工审核")

    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    created_by: str | None = Field(default=None, description="创建人ID")

    class Config:
        from_attributes = True


# PropertyOwner Schemas
class PropertyOwnerBase(BaseModel):
    """权利人基础字段"""

    owner_type: str = Field(default="个人", description="权利人类型（个人/单位）")
    name: str = Field(description="权利人姓名/单位名称")
    id_type: str | None = Field(default=None, description="证件类型")
    id_number: str | None = Field(default=None, description="证件号码（加密存储）")
    phone: str | None = Field(default=None, description="联系电话（加密存储）")
    address: str | None = Field(default=None, description="地址")
    organization_id: str | None = Field(default=None, description="关联单位ID")
    asset_ids: list[str] = []


class PropertyOwnerCreate(PropertyOwnerBase):
    """创建权利人"""

    pass


class PropertyOwnerUpdate(BaseModel):
    """更新权利人"""

    owner_type: str | None = Field(default=None, description="权利人类型")
    name: str | None = Field(default=None, description="权利人姓名/单位名称")
    id_type: str | None = Field(default=None, description="证件类型")
    id_number: str | None = Field(default=None, description="证件号码")
    phone: str | None = Field(default=None, description="联系电话")
    address: str | None = Field(default=None, description="地址")
    organization_id: str | None = Field(default=None, description="关联单位ID")
    asset_ids: list[str] = []


class PropertyOwnerResponse(PropertyOwnerBase):
    """权利人响应"""

    id: str = Field(description="权利人ID")
    asset_ids: list[str] = []
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    class Config:
        from_attributes = True
