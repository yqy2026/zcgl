"""
资产相关的Pydantic模型

注意：枚举字段已统一使用 str 类型，枚举值由数据库动态管理
验证由 EnumValidationService 统一处理
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from ..constants.validation_constants import FieldLengthLimits
from .ownership import OwnershipResponse
from .project import ProjectResponse

LEGACY_ASSET_FIELD_REPLACEMENTS = {
    "wuyang_project_name": "project_name",
    "description": "notes",
}


def _reject_legacy_asset_fields(data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    legacy_fields = [
        key for key in LEGACY_ASSET_FIELD_REPLACEMENTS.keys() if key in data
    ]
    if not legacy_fields:
        return data

    replacement_mapping = "、".join(
        f"{field}->{LEGACY_ASSET_FIELD_REPLACEMENTS[field]}" for field in legacy_fields
    )
    raise PydanticCustomError(
        "legacy_asset_field_not_supported",
        f"检测到已废弃字段，请改用: {replacement_mapping}",
        {"legacy_fields": legacy_fields},
    )


class AssetBase(BaseModel):
    """资产基础模型"""

    # 基本信息 - 按照权属方、权属类别、资产编码、资产名称、分类、地址顺序
    organization_id: str | None = Field(None, description="所属组织ID（DEPRECATED）")
    ownership_id: str | None = Field(None, description="权属方ID（DEPRECATED）")
    manager_party_id: str | None = Field(None, description="经营管理方主体ID")
    owner_party_id: str | None = Field(None, description="产权方主体ID")
    ownership_category: str | None = Field(
        None, max_length=FieldLengthLimits.CODE_MAX, description="权属类别"
    )
    project_name: str | None = Field(
        None,
        max_length=FieldLengthLimits.SHORT_TEXT_MAX,
        description="项目名称",
    )
    asset_code: str | None = Field(
        None, max_length=50, description="资产编码（系统生成，新建时可留空）"
    )
    asset_name: str = Field(
        ...,
        min_length=1,
        max_length=FieldLengthLimits.SHORT_TEXT_MAX,
        description="资产名称",
    )
    asset_form: str | None = Field(
        None, description="资产形态：land/building/structure/parking/warehouse/other"
    )
    spatial_level: str | None = Field(
        None, description="空间层级：plot/campus/building/floor/room/shop"
    )
    business_usage: str | None = Field(
        None, description="经营用途：commercial/office/warehouse/industrial/mixed/other"
    )
    # 半结构化地址子字段（所有三级行政区上线前可暂时为 null）
    province_code: str | None = Field(None, max_length=20, description="省级行政区代码")
    city_code: str | None = Field(None, max_length=20, description="市级行政区代码")
    district_code: str | None = Field(None, max_length=20, description="区县行政区代码")
    address_detail: str | None = Field(
        None, max_length=200, description="详细地址（trim 后长度 5-200）"
    )
    # address 不对外开放直写，由 Service 层自动拼接，必须保留在 schema 中才能通过 CRUD 传入 ORM
    address: str | None = Field(
        None, description="物业地址（系统拼接只读，不接受外部直写）"
    )
    ownership_status: str = Field(..., description="确权状态")
    property_nature: str = Field(..., description="物业性质")
    usage_status: str = Field(..., description="使用状态")
    management_entity: str | None = Field(
        None, max_length=200, description="经营管理单位"
    )
    business_category: str | None = Field(None, max_length=100, description="业态类别")
    is_litigated: bool = Field(False, description="是否涉诉")
    notes: str | None = Field(None, description="备注")

    # 面积相关字段
    land_area: Decimal | None = Field(None, ge=0, description="土地面积（平方米）")
    actual_property_area: Decimal | None = Field(
        None, ge=0, description="实际房产面积（平方米）"
    )
    rentable_area: Decimal | None = Field(
        None, ge=0, description="可出租面积（平方米）"
    )
    rented_area: Decimal | None = Field(None, ge=0, description="已出租面积（平方米）")
    non_commercial_area: Decimal | None = Field(
        None, ge=0, description="非经营物业面积（平方米）"
    )
    include_in_occupancy_rate: bool = Field(
        True,
        description="是否计入出租率统计",
    )

    # 用途相关字段
    certificated_usage: str | None = Field(None, max_length=100, description="证载用途")
    actual_usage: str | None = Field(None, max_length=100, description="实际用途")

    # 承租方相关字段
    tenant_type: str | None = Field(None, description="承租方类型")
    is_sublease: bool = Field(False, description="是否分租/转租")
    sublease_notes: str | None = Field(None, description="分租/转租备注")

    # 管理相关字段
    manager_name: str | None = Field(
        None, max_length=100, description="管理责任人（网格员）"
    )
    revenue_mode: str | None = Field(None, description="经营模式（承租/代理）")
    operation_status: str | None = Field(None, description="经营状态")

    # 财务相关字段已移除
    # annual_income, annual_expense, net_income 字段已移除

    # 接收相关字段
    operation_agreement_start_date: date | None = Field(
        None, description="接收协议开始日期"
    )
    operation_agreement_end_date: date | None = Field(
        None, description="接收协议结束日期"
    )
    operation_agreement_attachments: str | None = Field(
        None, description="接收协议文件"
    )
    terminal_contract_files: str | None = Field(None, description="终端合同文件")

    # 项目相关字段

    # 系统字段
    data_status: str = Field("正常", description="数据状态")
    created_by: str | None = Field(None, max_length=100, description="创建人")
    updated_by: str | None = Field(None, max_length=100, description="更新人")
    version: int = Field(1, description="版本号")
    tags: str | None = Field(None, description="标签")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: str | None = Field(None, description="审核备注")

    @field_validator("address_detail")
    @classmethod
    def validate_address_detail(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if len(stripped) < 5:
            raise PydanticCustomError(
                "address_detail_too_short", "详细地址 trim 后不得少于 5 个字符", {}
            )
        if len(stripped) > 200:
            raise PydanticCustomError(
                "address_detail_too_long", "详细地址 trim 后不得超过 200 个字符", {}
            )
        return stripped

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_fields(cls, data: Any) -> Any:
        return _reject_legacy_asset_fields(data)

    @field_validator(
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "non_commercial_area",
    )
    @classmethod
    def validate_area(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "negative_value", "数值不能为负数", {}
            )  # pragma: no cover
        return v  # pragma: no cover

    # occupancy_rate 验证器已移除，因为现在是计算字段

    @field_validator("is_litigated")
    @classmethod
    def validate_is_litigated(cls, v: bool) -> bool:
        if v is not None and not isinstance(v, bool):  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "invalid_boolean", "是否涉诉必须是布尔值", {}
            )  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("operation_agreement_end_date")
    @classmethod
    def validate_agreement_dates(
        cls, v: date | None, info: ValidationInfo
    ) -> date | None:
        if (
            v  # pragma: no cover
            and info.data.get("operation_agreement_start_date")  # pragma: no cover
            and v < info.data["operation_agreement_start_date"]  # pragma: no cover
        ):
            raise PydanticCustomError(  # pragma: no cover
                "invalid_date_range", "接收协议结束日期不能早于开始日期", {}
            )  # pragma: no cover
        return v  # pragma: no cover

    @model_validator(mode="after")
    def validate_ownership_required(self) -> "AssetBase":
        if not self.owner_party_id and not self.ownership_id:
            raise PydanticCustomError(
                "missing_owner_reference",
                "owner_party_id 或 ownership_id 至少提供一个",
                {"field": "owner_party_id"},
            )
        return self


class AssetCreate(AssetBase):
    """创建资产模型"""

    pass


class AssetUpdate(BaseModel):
    """更新资产模型"""

    # 基本信息 - 按照权属方、权属类别、资产编码、资产名称、分类、地址顺序
    organization_id: str | None = Field(None, description="所属组织ID（DEPRECATED）")
    ownership_id: str | None = Field(None, description="权属方ID（DEPRECATED）")
    manager_party_id: str | None = Field(None, description="经营管理方主体ID")
    owner_party_id: str | None = Field(None, description="产权方主体ID")
    ownership_category: str | None = Field(None, max_length=100, description="权属类别")
    project_name: str | None = Field(
        None,
        max_length=200,
        description="项目名称",
    )
    asset_code: str | None = Field(None, max_length=50, description="资产编码")
    asset_name: str | None = Field(
        None, min_length=1, max_length=200, description="资产名称"
    )
    asset_form: str | None = Field(None, description="资产形态")
    spatial_level: str | None = Field(None, description="空间层级")
    business_usage: str | None = Field(None, description="经营用途")
    province_code: str | None = Field(None, max_length=20, description="省级行政区代码")
    city_code: str | None = Field(None, max_length=20, description="市级行政区代码")
    district_code: str | None = Field(None, max_length=20, description="区县行政区代码")
    address_detail: str | None = Field(None, max_length=200, description="详细地址")
    # address 不对外开放直写
    address: str | None = Field(
        None, description="物业地址（系统拼接，不接受外部直写）"
    )
    ownership_status: str | None = Field(None, description="确权状态")
    property_nature: str | None = Field(None, description="物业性质")
    usage_status: str | None = Field(None, description="使用状态")
    management_entity: str | None = Field(
        None, max_length=200, description="经营管理单位"
    )
    business_category: str | None = Field(None, max_length=100, description="业态类别")
    is_litigated: bool | None = Field(None, description="是否涉诉")
    notes: str | None = Field(None, description="备注")

    # 面积相关字段
    land_area: Decimal | None = Field(None, ge=0, description="土地面积（平方米）")
    actual_property_area: Decimal | None = Field(
        None, ge=0, description="实际房产面积（平方米）"
    )
    rentable_area: Decimal | None = Field(
        None, ge=0, description="可出租面积（平方米）"
    )
    rented_area: Decimal | None = Field(None, ge=0, description="已出租面积（平方米）")
    # unrented_area 已移除，改为计算字段
    non_commercial_area: Decimal | None = Field(
        None, ge=0, description="非经营物业面积（平方米）"
    )
    # occupancy_rate 已移除，改为计算字段
    include_in_occupancy_rate: bool | None = Field(
        None,
        description="是否计入出租率统计",
    )

    # 用途相关字段
    certificated_usage: str | None = Field(None, max_length=100, description="证载用途")
    actual_usage: str | None = Field(None, max_length=100, description="实际用途")

    # 承租方相关字段
    tenant_type: str | None = Field(None, description="承租方类型")
    is_sublease: bool | None = Field(None, description="是否分租/转租")
    sublease_notes: str | None = Field(None, description="分租/转租备注")

    # 管理相关字段
    manager_name: str | None = Field(
        None, max_length=100, description="管理责任人（网格员）"
    )
    revenue_mode: str | None = Field(None, description="经营模式（承租/代理）")
    operation_status: str | None = Field(None, description="经营状态")

    # 财务相关字段已移除
    # annual_income, annual_expense, net_income 字段已移除

    # 接收相关字段
    operation_agreement_start_date: date | None = Field(
        None, description="接收协议开始日期"
    )
    operation_agreement_end_date: date | None = Field(
        None, description="接收协议结束日期"
    )
    operation_agreement_attachments: str | None = Field(
        None, description="接收协议文件"
    )
    terminal_contract_files: str | None = Field(None, description="终端合同文件")

    # 项目相关字段

    # 系统字段
    data_status: str | None = Field(None, description="数据状态")
    updated_by: str | None = Field(None, max_length=100, description="更新人")
    version: int | None = Field(None, ge=1, description="版本号(乐观锁)")
    tags: str | None = Field(None, description="标签")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: str | None = Field(None, description="审核备注")

    @field_validator("address_detail")
    @classmethod
    def validate_address_detail_update(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if len(stripped) < 5:
            raise PydanticCustomError(
                "address_detail_too_short", "详细地址 trim 后不得少于 5 个字符", {}
            )
        if len(stripped) > 200:
            raise PydanticCustomError(
                "address_detail_too_long", "详细地址 trim 后不得超过 200 个字符", {}
            )
        return stripped

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_fields_update(cls, data: Any) -> Any:
        return _reject_legacy_asset_fields(data)

    @field_validator(
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "non_commercial_area",
    )
    @classmethod
    def validate_area(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "negative_value", "数值不能为负数", {}
            )  # pragma: no cover
        return v  # pragma: no cover

    # occupancy_rate 验证器已移除，因为现在是计算字段

    @field_validator("is_litigated")
    @classmethod
    def validate_is_litigated(cls, v: bool | None) -> bool | None:
        if v is not None and not isinstance(v, bool):  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "invalid_boolean", "是否涉诉必须是布尔值", {}
            )  # pragma: no cover
        return v  # pragma: no cover


class AssetReviewRejectRequest(BaseModel):
    """资产驳回/反审核请求。"""

    reason: str = Field(..., min_length=1, max_length=500, description="原因（必填）")


class AssetReviewLogResponse(BaseModel):
    """资产审核日志响应。"""

    id: str = Field(..., description="日志ID")
    asset_id: str = Field(..., description="资产ID")
    action: str = Field(..., description="动作")
    from_status: str = Field(..., description="变更前状态")
    to_status: str = Field(..., description="变更后状态")
    operator: str | None = Field(None, description="操作人")
    reason: str | None = Field(None, description="原因")
    context: dict[str, Any] | None = Field(None, description="附加上下文")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class AssetResponseBase(BaseModel):
    """
    资产响应基础模型 - 使用宽松的str类型

    该模型用于从数据库读取数据时的响应，使用str类型代替Enum类型，
    以支持数据库中可能存在的遗留枚举值。
    """

    # 基本信息
    ownership_entity: str | None = Field(None, description="权属方名称（动态获取）")
    ownership_category: str | None = Field(None, description="权属类别")
    project_name: str | None = Field(None, description="项目名称")
    asset_code: str | None = Field(None, description="资产编码")
    asset_name: str = Field(..., description="资产名称")
    asset_form: str | None = Field(None, description="资产形态")
    spatial_level: str | None = Field(None, description="空间层级")
    business_usage: str | None = Field(None, description="经营用途")
    province_code: str | None = Field(None, description="省级行政区代码")
    city_code: str | None = Field(None, description="市级行政区代码")
    district_code: str | None = Field(None, description="区县行政区代码")
    address_detail: str | None = Field(None, description="详细地址")
    address: str = Field(..., description="物业地址（系统拼接只读）")

    # 枚举字段 - 使用str类型以兼容遗留数据
    ownership_status: str = Field(..., description="确权状态")
    property_nature: str = Field(..., description="物业性质")
    usage_status: str = Field(..., description="使用状态")
    management_entity: str | None = Field(
        None, max_length=200, description="经营管理单位"
    )

    business_category: str | None = Field(None, description="业态类别")
    is_litigated: bool = Field(False, description="是否涉诉")
    notes: str | None = Field(None, description="备注")

    # 面积相关字段
    land_area: Decimal | None = Field(None, description="土地面积（平方米）")
    actual_property_area: Decimal | None = Field(
        None, description="实际房产面积（平方米）"
    )
    rentable_area: Decimal | None = Field(None, description="可出租面积（平方米）")
    rented_area: Decimal | None = Field(None, description="已出租面积（平方米）")
    non_commercial_area: Decimal | None = Field(
        None, description="非经营物业面积（平方米）"
    )
    include_in_occupancy_rate: bool = Field(
        True,
        description="是否计入出租率统计",
    )

    # 用途相关字段
    certificated_usage: str | None = Field(None, description="证载用途")
    actual_usage: str | None = Field(None, description="实际用途")

    # 承租方相关字段
    tenant_name: str | None = Field(None, description="承租方名称")
    tenant_type: str | None = Field(None, description="承租方类型")

    # 合同相关字段
    lease_contract_number: str | None = Field(None, description="租赁合同编号")
    contract_start_date: date | None = Field(None, description="合同开始日期")
    contract_end_date: date | None = Field(None, description="合同结束日期")
    monthly_rent: Decimal | None = Field(None, description="月租金（元）")
    deposit: Decimal | None = Field(None, description="押金（元）")
    is_sublease: bool = Field(False, description="是否分租/转租")
    sublease_notes: str | None = Field(None, description="分租/转租备注")

    # 管理相关字段
    manager_name: str | None = Field(None, description="管理责任人（网格员）")
    revenue_mode: str | None = Field(None, description="经营模式（承租/代理）")
    operation_status: str | None = Field(None, description="经营状态")

    # 接收相关字段
    operation_agreement_start_date: date | None = Field(
        None, description="接收协议开始日期"
    )
    operation_agreement_end_date: date | None = Field(
        None, description="接收协议结束日期"
    )
    operation_agreement_attachments: str | None = Field(
        None, description="接收协议文件"
    )
    terminal_contract_files: str | None = Field(None, description="终端合同文件")

    # 系统字段
    data_status: str = Field("正常", description="数据状态")
    created_by: str | None = Field(None, description="创建人")
    updated_by: str | None = Field(None, description="更新人")
    version: int = Field(1, description="版本号")
    tags: str | None = Field(None, description="标签")

    # 审核字段
    review_status: str = Field(
        "draft", description="审核状态：draft/pending/approved/reversed"
    )
    review_by: str | None = Field(None, description="审核人")
    reviewed_at: datetime | None = Field(None, description="审核时间")
    review_reason: str | None = Field(None, description="审核原因")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: str | None = Field(None, description="审核备注")


class AssetResponse(AssetResponseBase):
    """资产响应模型"""

    id: str = Field(..., description="资产ID")
    organization_id: str | None = Field(None, description="所属组织ID（DEPRECATED）")
    project_id: str | None = Field(None, description="项目ID")  # 对齐Model
    ownership_id: str | None = Field(
        None, description="权属ID（DEPRECATED）"
    )  # 对齐Model
    manager_party_id: str | None = Field(None, description="经营管理方主体ID")
    owner_party_id: str | None = Field(None, description="产权方主体ID")
    project: ProjectResponse | None = Field(None, description="关联项目")
    ownership: OwnershipResponse | None = Field(None, description="关联权属方")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class AssetListItemResponse(AssetResponseBase):
    """资产列表响应模型（轻量，无深层关联字段）"""

    id: str = Field(..., description="资产ID")
    organization_id: str | None = Field(None, description="所属组织ID（DEPRECATED）")
    project_id: str | None = Field(None, description="项目ID")
    ownership_id: str | None = Field(None, description="权属ID（DEPRECATED）")
    manager_party_id: str | None = Field(None, description="经营管理方主体ID")
    owner_party_id: str | None = Field(None, description="产权方主体ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class ContractTypeSummary(BaseModel):
    group_relation_type: str = Field(..., description="合同角色")
    label: str = Field(..., description="展示标签")
    contract_count: int = Field(..., description="合同数量")
    total_area: float = Field(..., description="面积汇总（MVP 固定 0）")
    monthly_amount: float = Field(..., description="月度金额汇总")


class ContractPartyItem(BaseModel):
    party_id: str | None = Field(None, description="承租方主体 ID")
    party_name: str = Field(..., description="承租方名称")
    group_relation_type: str = Field(..., description="合同角色")
    contract_count: int = Field(..., description="合同数量")


class AssetLeaseSummaryResponse(BaseModel):
    asset_id: str = Field(..., description="资产 ID")
    period_start: date = Field(..., description="展示周期开始")
    period_end: date = Field(..., description="展示周期结束")
    total_contracts: int = Field(..., description="合同总数")
    total_rented_area: float = Field(..., description="已出租/管理面积")
    rentable_area: float = Field(..., description="可出租面积")
    occupancy_rate: float = Field(..., description="出租率")
    by_type: list[ContractTypeSummary] = Field(..., description="按合同角色汇总")
    customer_summary: list[ContractPartyItem] = Field(..., description="客户摘要")


class AssetListResponse(BaseModel):
    """资产列表响应模型"""

    items: list[AssetResponse] = Field(..., description="资产列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    pages: int = Field(..., description="总页数")


class AssetHistoryResponse(BaseModel):
    """资产历史响应模型"""

    id: str = Field(..., description="历史记录ID")
    asset_id: str = Field(..., description="资产ID")
    operation_type: str = Field(..., description="操作类型")
    field_name: str | None = Field(None, description="字段名称")
    old_value: str | None = Field(None, description="原值")
    new_value: str | None = Field(None, description="新值")
    operator: str | None = Field(None, description="操作人")
    operation_time: datetime = Field(..., description="操作时间")
    description: str | None = Field(None, description="操作描述")
    # 审计字段 - 对齐Model
    change_reason: str | None = Field(None, description="变更原因")
    ip_address: str | None = Field(None, description="IP地址")
    user_agent: str | None = Field(None, description="用户代理")
    session_id: str | None = Field(None, description="会话ID")

    model_config = ConfigDict(from_attributes=True)


class AssetDocumentResponse(BaseModel):
    """资产文档响应模型"""

    id: str = Field(..., description="文档ID")
    asset_id: str = Field(..., description="资产ID")
    document_name: str = Field(..., description="文档名称")
    document_type: str = Field(..., description="文档类型")
    file_path: str | None = Field(None, description="文件路径")
    file_size: int | None = Field(None, description="文件大小(字节)")
    mime_type: str | None = Field(None, description="文件MIME类型")
    upload_time: datetime = Field(..., description="上传时间")
    uploader: str | None = Field(None, description="上传人")
    description: str | None = Field(None, description="文档描述")

    model_config = ConfigDict(from_attributes=True)


class SystemDictionaryCreate(BaseModel):
    """系统数据字典创建模型"""

    dict_type: str = Field(..., description="字典类型")
    dict_code: str = Field(..., description="字典编码")
    dict_label: str = Field(..., description="字典标签")
    dict_value: str = Field(..., description="字典值")
    sort_order: int = Field(0, description="排序")
    is_active: bool = Field(True, description="是否启用")


class SystemDictionaryUpdate(BaseModel):
    """系统数据字典更新模型"""

    dict_type: str | None = Field(None, description="字典类型")
    dict_code: str | None = Field(None, description="字典编码")
    dict_label: str | None = Field(None, description="字典标签")
    dict_value: str | None = Field(None, description="字典值")
    sort_order: int | None = Field(None, description="排序")
    is_active: bool | None = Field(None, description="是否启用")


class SystemDictionaryResponse(BaseModel):
    """系统数据字典响应模型"""

    id: str = Field(..., description="字典项ID")
    dict_type: str = Field(..., description="字典类型")
    dict_code: str = Field(..., description="字典编码")
    dict_label: str = Field(..., description="字典标签")
    dict_value: str = Field(..., description="字典值")
    sort_order: int = Field(..., description="排序")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class AssetCustomFieldCreate(BaseModel):
    """资产自定义字段创建模型"""

    field_name: str = Field(..., description="字段名称")
    display_name: str = Field(..., description="显示名称")
    field_type: str = Field(..., description="字段类型")
    is_required: bool = Field(False, description="是否必填")
    is_active: bool = Field(True, description="是否启用")
    sort_order: int = Field(0, description="排序")
    default_value: str | None = Field(None, description="默认值")
    field_options: str | None = Field(None, description="字段选项(JSON)")
    validation_rules: str | None = Field(None, description="验证规则(JSON)")
    help_text: str | None = Field(None, description="帮助文本")
    description: str | None = Field(None, description="描述")


class AssetCustomFieldUpdate(BaseModel):
    """资产自定义字段更新模型"""

    field_name: str | None = Field(None, description="字段名称")
    display_name: str | None = Field(None, description="显示名称")
    field_type: str | None = Field(None, description="字段类型")
    is_required: bool | None = Field(None, description="是否必填")
    is_active: bool | None = Field(None, description="是否启用")
    sort_order: int | None = Field(None, description="排序")
    default_value: str | None = Field(None, description="默认值")
    field_options: str | None = Field(None, description="字段选项(JSON)")
    validation_rules: str | None = Field(None, description="验证规则(JSON)")
    help_text: str | None = Field(None, description="帮助文本")
    description: str | None = Field(None, description="描述")


class CustomFieldValueItem(BaseModel):
    """自定义字段值项"""

    field_name: str = Field(..., description="字段名称")
    value: str | int | float | bool | None = Field(None, description="字段值")


class CustomFieldValueUpdate(BaseModel):
    """自定义字段值更新模型"""

    values: list[CustomFieldValueItem] = Field(..., description="字段值列表")


class AssetCustomFieldResponse(BaseModel):
    """资产自定义字段响应模型"""

    id: str = Field(..., description="自定义字段ID")
    field_name: str = Field(..., description="字段名称")
    display_name: str = Field(..., description="显示名称")
    field_type: str = Field(..., description="字段类型")
    is_required: bool = Field(..., description="是否必填")
    is_active: bool = Field(..., description="是否启用")
    sort_order: int = Field(..., description="排序")
    default_value: str | None = Field(None, description="默认值")
    field_options: str | None = Field(None, description="字段选项(JSON)")
    validation_rules: str | None = Field(None, description="验证规则(JSON)")
    help_text: str | None = Field(None, description="帮助文本")
    description: str | None = Field(None, description="描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


# ===== 批量操作相关模型 =====


class BatchProcessingError(BaseModel):
    """批量处理错误详情"""

    id: str | None = Field(None, description="对象ID")
    row_index: int | None = Field(None, description="行号")
    field: str | None = Field(None, description="字段名")
    message: str = Field(..., description="错误信息")
    code: str | None = Field(None, description="错误代码")


class ValidationWarning(BaseModel):
    """验证警告详情"""

    field: str | None = Field(None, description="字段名")
    message: str = Field(..., description="警告信息")
    code: str | None = Field(None, description="警告代码")


class AssetBatchUpdateRequest(BaseModel):
    """资产批量更新请求模型"""

    asset_ids: list[str] = Field(..., description="资产ID列表")
    updates: AssetUpdate = Field(..., description="更新数据")
    should_update_all: bool = Field(False, description="是否更新所有资产")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetBatchUpdateResponse(BaseModel):
    """资产批量更新响应模型"""

    success_count: int = Field(..., description="成功更新数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[BatchProcessingError] = Field(
        default_factory=list, description="错误信息列表"
    )
    updated_assets: list[str] = Field(
        default_factory=list, description="成功更新的资产ID"
    )

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetValidationRequest(BaseModel):
    """资产数据验证请求模型"""

    data: dict[str, Any] = Field(..., description="待验证的资产数据")
    validate_rules: list[str] | None = Field(None, description="验证规则列表")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetValidationResponse(BaseModel):
    """资产数据验证响应模型"""

    is_valid: bool = Field(..., description="是否通过验证")
    errors: list[BatchProcessingError] = Field(
        default_factory=list, description="错误信息列表"
    )
    warnings: list[ValidationWarning] = Field(
        default_factory=list, description="警告信息列表"
    )
    validated_fields: list[str] = Field(default_factory=list, description="已验证字段")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetImportRequest(BaseModel):
    """资产导入请求模型"""

    data: list[dict[str, Any]] = Field(..., description="待导入的资产数据列表")
    import_mode: str = Field("create", description="导入模式：create/merge/update")
    should_skip_errors: bool = Field(False, description="是否跳过错误数据")
    is_dry_run: bool = Field(False, description="是否仅验证不实际导入")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetImportResponse(BaseModel):
    """资产导入响应模型"""

    success_count: int = Field(..., description="成功导入数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[BatchProcessingError] = Field(
        default_factory=list, description="错误信息列表"
    )
    imported_assets: list[str] = Field(
        default_factory=list, description="成功导入的资产ID"
    )
    import_id: str | None = Field(None, description="导入任务ID")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class BatchCustomFieldUpdateRequest(BaseModel):
    """批量自定义字段更新请求模型"""

    asset_ids: list[str] = Field(..., description="资产ID列表")
    field_values: dict[str, str | int | float | bool | None] = Field(
        ..., description="自定义字段值"
    )

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class BatchCustomFieldUpdateResponse(BaseModel):
    """批量自定义字段更新响应模型"""

    success_count: int = Field(..., description="成功更新数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[BatchProcessingError] = Field(
        default_factory=list, description="错误信息列表"
    )

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetCustomFieldAssignment(BaseModel):
    """资产自定义字段分配模型"""

    asset_id: str = Field(..., description="关联资产ID")
    field_name: str = Field(..., min_length=1, max_length=100, description="字段名称")
    field_type: str = Field(..., description="字段类型：text/number/date/boolean")
    field_value: str | None = Field(None, description="字段值")

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        if v not in ["text", "number", "date", "boolean"]:  # pragma: no cover
            raise PydanticCustomError(
                "invalid_field_type",
                "字段类型必须是text、number、date或boolean之一",
                {},
            )  # pragma: no cover
        return v  # pragma: no cover
