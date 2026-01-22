from typing import Any

"""
资产相关的Pydantic模型

注意：枚举字段已统一使用 str 类型，枚举值由数据库动态管理
验证由 EnumValidationService 统一处理
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..constants.validation_constants import FieldLengthLimits


class AssetBase(BaseModel):
    """资产基础模型"""

    # 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
    ownership_entity: str = Field(
        ...,
        min_length=1,
        max_length=FieldLengthLimits.SHORT_TEXT_MAX,
        description="权属方",
    )
    ownership_category: str | None = Field(
        None, max_length=FieldLengthLimits.CODE_MAX, description="权属类别"
    )
    project_name: str | None = Field(
        None, max_length=FieldLengthLimits.SHORT_TEXT_MAX, description="项目名称"
    )
    property_name: str = Field(
        ...,
        min_length=1,
        max_length=FieldLengthLimits.SHORT_TEXT_MAX,
        description="物业名称",
    )
    address: str = Field(
        ...,
        min_length=1,
        max_length=FieldLengthLimits.MEDIUM_TEXT_MAX,
        description="物业地址",
    )
    ownership_status: str = Field(..., description="确权状态")
    property_nature: str = Field(..., description="物业性质")
    usage_status: str = Field(..., description="使用状态")
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
    # unrented_area 已移除，改为计算字段
    non_commercial_area: Decimal | None = Field(
        None, ge=0, description="非经营物业面积（平方米）"
    )
    # occupancy_rate 已移除，改为计算字段
    include_in_occupancy_rate: bool = Field(True, description="是否计入出租率统计")

    # 用途相关字段
    certificated_usage: str | None = Field(None, max_length=100, description="证载用途")
    actual_usage: str | None = Field(None, max_length=100, description="实际用途")

    # 租户相关字段
    tenant_name: str | None = Field(
        None, max_length=FieldLengthLimits.SHORT_TEXT_MAX, description="租户名称"
    )
    tenant_type: str | None = Field(None, description="租户类型")

    # 合同相关字段
    lease_contract_number: str | None = Field(
        None, max_length=FieldLengthLimits.MEDIUM_TEXT_MAX, description="租赁合同编号"
    )
    contract_start_date: date | None = Field(None, description="合同开始日期")
    contract_end_date: date | None = Field(None, description="合同结束日期")
    monthly_rent: Decimal | None = Field(None, ge=0, description="月租金（元）")
    deposit: Decimal | None = Field(None, ge=0, description="押金（元）")
    is_sublease: bool = Field(False, description="是否分租/转租")
    sublease_notes: str | None = Field(None, description="分租/转租备注")

    # 管理相关字段
    manager_name: str | None = Field(
        None, max_length=100, description="管理责任人（网格员）"
    )
    business_model: str | None = Field(None, description="接收模式")
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

    # 多租户支持
    tenant_id: str | None = Field(None, max_length=50, description="租户ID")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: str | None = Field(None, description="审核备注")

    @field_validator(
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "non_commercial_area",
        "monthly_rent",
        "deposit",
    )
    @classmethod
    def validate_area(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:  # pragma: no cover
            raise ValueError("数值不能为负数")  # pragma: no cover
        return v  # pragma: no cover

    # occupancy_rate 验证器已移除，因为现在是计算字段

    @field_validator("is_litigated")
    @classmethod
    def validate_is_litigated(cls, v: bool) -> bool:
        if v is not None and not isinstance(v, bool):  # pragma: no cover
            raise ValueError("是否涉诉必须是布尔值")  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("contract_end_date")
    @classmethod
    def validate_contract_dates(cls, v: date | None, info: Any) -> date | None:
        if (
            v  # pragma: no cover
            and info.data.get("contract_start_date")  # pragma: no cover
            and v < info.data["contract_start_date"]  # pragma: no cover
        ):
            raise ValueError("合同结束日期不能早于开始日期")  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("operation_agreement_end_date")
    @classmethod
    def validate_agreement_dates(cls, v: date | None, info: Any) -> date | None:
        if (
            v  # pragma: no cover
            and info.data.get("operation_agreement_start_date")  # pragma: no cover
            and v < info.data["operation_agreement_start_date"]  # pragma: no cover
        ):
            raise ValueError("接收协议结束日期不能早于开始日期")  # pragma: no cover
        return v  # pragma: no cover


class AssetCreate(AssetBase):
    """创建资产模型"""

    pass


class AssetUpdate(BaseModel):
    """更新资产模型"""

    # 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
    ownership_entity: str | None = Field(
        None, min_length=1, max_length=200, description="权属方"
    )
    ownership_category: str | None = Field(None, max_length=100, description="权属类别")
    project_name: str | None = Field(None, max_length=200, description="项目名称")
    property_name: str | None = Field(
        None, min_length=1, max_length=200, description="物业名称"
    )
    address: str | None = Field(
        None, min_length=1, max_length=500, description="物业地址"
    )
    ownership_status: str | None = Field(None, description="确权状态")
    property_nature: str | None = Field(None, description="物业性质")
    usage_status: str | None = Field(None, description="使用状态")
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
        None, description="是否计入出租率统计"
    )

    # 用途相关字段
    certificated_usage: str | None = Field(None, max_length=100, description="证载用途")
    actual_usage: str | None = Field(None, max_length=100, description="实际用途")

    # 租户相关字段
    tenant_name: str | None = Field(
        None, max_length=FieldLengthLimits.SHORT_TEXT_MAX, description="租户名称"
    )
    tenant_type: str | None = Field(None, description="租户类型")

    # 合同相关字段
    lease_contract_number: str | None = Field(
        None, max_length=FieldLengthLimits.MEDIUM_TEXT_MAX, description="租赁合同编号"
    )
    contract_start_date: date | None = Field(None, description="合同开始日期")
    contract_end_date: date | None = Field(None, description="合同结束日期")
    monthly_rent: Decimal | None = Field(None, ge=0, description="月租金（元）")
    deposit: Decimal | None = Field(None, ge=0, description="押金（元）")
    is_sublease: bool | None = Field(None, description="是否分租/转租")
    sublease_notes: str | None = Field(None, description="分租/转租备注")

    # 管理相关字段
    manager_name: str | None = Field(
        None, max_length=100, description="管理责任人（网格员）"
    )
    business_model: str | None = Field(None, description="接收模式")
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
    tags: str | None = Field(None, description="标签")

    # 审核相关字段已简化
    # last_audit_date, audit_status, auditor 字段已移除
    audit_notes: str | None = Field(None, description="审核备注")

    @field_validator(
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "non_commercial_area",
        "monthly_rent",
        "deposit",
    )
    @classmethod
    def validate_area(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:  # pragma: no cover
            raise ValueError("数值不能为负数")  # pragma: no cover
        return v  # pragma: no cover

    # occupancy_rate 验证器已移除，因为现在是计算字段

    @field_validator("is_litigated")
    @classmethod
    def validate_is_litigated(cls, v: bool | None) -> bool | None:
        if v is not None and not isinstance(v, bool):  # pragma: no cover
            raise ValueError("是否涉诉必须是布尔值")  # pragma: no cover
        return v  # pragma: no cover


class AssetResponseBase(BaseModel):
    """
    资产响应基础模型 - 使用宽松的str类型

    该模型用于从数据库读取数据时的响应，使用str类型代替Enum类型，
    以支持数据库中可能存在的遗留枚举值。
    """

    # 基本信息
    ownership_entity: str = Field(..., description="权属方")
    ownership_category: str | None = Field(None, description="权属类别")
    project_name: str | None = Field(None, description="项目名称")
    property_name: str = Field(..., description="物业名称")
    address: str = Field(..., description="物业地址")

    # 枚举字段 - 使用str类型以兼容遗留数据
    ownership_status: str = Field(..., description="确权状态")
    property_nature: str = Field(..., description="物业性质")
    usage_status: str = Field(..., description="使用状态")

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
    include_in_occupancy_rate: bool = Field(True, description="是否计入出租率统计")

    # 用途相关字段
    certificated_usage: str | None = Field(None, description="证载用途")
    actual_usage: str | None = Field(None, description="实际用途")

    # 租户相关字段
    tenant_name: str | None = Field(None, description="租户名称")
    tenant_type: str | None = Field(None, description="租户类型")

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
    business_model: str | None = Field(None, description="接收模式")
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

    # 多租户支持
    tenant_id: str | None = Field(None, description="租户ID")

    # 审核相关字段
    audit_notes: str | None = Field(None, description="审核备注")


class AssetResponse(AssetResponseBase):
    """资产响应模型"""

    id: str = Field(..., description="资产ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """资产列表响应模型"""

    items: list[AssetResponse] = Field(..., description="资产列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页记录数")
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


class CustomFieldValueUpdate(BaseModel):
    """自定义字段值更新模型"""

    values: list[dict[str, Any]] = Field(..., description="字段值列表")


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


class AssetBatchUpdateRequest(BaseModel):
    """资产批量更新请求模型"""

    asset_ids: list[str] = Field(..., description="资产ID列表")
    updates: dict[str, Any] = Field(..., description="更新数据")
    update_all: bool = Field(False, description="是否更新所有资产")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetBatchUpdateResponse(BaseModel):
    """资产批量更新响应模型"""

    success_count: int = Field(..., description="成功更新数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[dict[str, Any]] = Field(
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
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="错误信息列表"
    )
    warnings: list[dict[str, Any]] = Field(
        default_factory=list, description="警告信息列表"
    )
    validated_fields: list[str] = Field(default_factory=list, description="已验证字段")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetImportRequest(BaseModel):
    """资产导入请求模型"""

    data: list[dict[str, Any]] = Field(..., description="待导入的资产数据列表")
    import_mode: str = Field("create", description="导入模式：create/merge/update")
    skip_errors: bool = Field(False, description="是否跳过错误数据")
    dry_run: bool = Field(False, description="是否仅验证不实际导入")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class AssetImportResponse(BaseModel):
    """资产导入响应模型"""

    success_count: int = Field(..., description="成功导入数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[dict[str, Any]] = Field(
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
    field_values: dict[str, Any] = Field(..., description="自定义字段值")

    model_config = ConfigDict(json_schema_extra={"example": {"description": "示例"}})


class BatchCustomFieldUpdateResponse(BaseModel):
    """批量自定义字段更新响应模型"""

    success_count: int = Field(..., description="成功更新数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    errors: list[dict[str, Any]] = Field(
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
            raise ValueError(
                "字段类型必须是text、number、date或boolean之一"
            )  # pragma: no cover
        return v  # pragma: no cover
