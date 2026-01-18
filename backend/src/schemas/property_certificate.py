"""
Property Certificate Schema
产权证/不动产权证字段定义

用于从产权证图像中提取结构化数据
"""

from datetime import date
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
    building_area: Decimal | None = Field(default=None, description="建筑面积 (㎡)")
    land_area: Decimal | None = Field(default=None, description="土地使用面积 (㎡)")
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
    certificate_type: str = Field(default="property_cert", description="证书类型")
    extracted_data: dict[str, Any] = Field(default_factory=dict, description="提取的字段数据")
    confidence_score: float = Field(ge=0.0, le=1.0, description="置信度分数")
    asset_matches: list[dict[str, Any]] = Field(default_factory=list, description="匹配的资产列表")
    validation_errors: list[str] = Field(default_factory=list, description="验证错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")

    class Config:
        from_attributes = True


class CertificateImportConfirm(BaseModel):
    """产权证导入确认"""

    session_id: str = Field(description="会话ID")
    extracted_data: dict[str, Any] = Field(description="提取的字段数据")
    asset_link_id: str | None = Field(default=None, description="关联的资产ID")
    create_new_asset: bool = Field(default=False, description="是否创建新资产")
    owners: list[dict[str, Any]] = Field(default_factory=list, description="权利人列表")

    class Config:
        from_attributes = True
