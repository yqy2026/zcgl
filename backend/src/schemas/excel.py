"""
Excel导入导出相关的Pydantic数据模型
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ImportStatus(str, Enum):
    """导入状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExcelImportResponse(BaseModel):
    """Excel导入响应模型"""

    success: int = Field(..., description="成功导入的记录数")
    failed: int = Field(..., description="导入失败的记录数")
    total: int = Field(..., description="总记录数")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    message: str = Field(..., description="导入结果消息")


class ExcelImportStatus(BaseModel):
    """Excel导入状态模型（用于异步导入）"""

    task_id: str = Field(..., description="任务ID")
    status: ImportStatus = Field(..., description="导入状态")
    progress: float = Field(0.0, description="导入进度(0-100)")
    success: int = Field(0, description="成功导入的记录数")
    failed: int = Field(0, description="导入失败的记录数")
    total: int = Field(0, description="总记录数")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    started_at: str | None = Field(None, description="开始时间")
    completed_at: str | None = Field(None, description="完成时间")
    message: str = Field("", description="状态消息")


class ExcelValidationResponse(BaseModel):
    """Excel验证响应模型"""

    valid: bool = Field(..., description="文件是否有效")
    total_rows: int = Field(..., description="总行数")
    total_columns: int = Field(..., description="总列数")
    errors: list[str] = Field(default_factory=list, description="验证错误列表")
    columns: list[str] = Field(default_factory=list, description="列名列表")
    message: str = Field(..., description="验证结果消息")


class ExcelExportRequest(BaseModel):
    """Excel导出请求模型"""

    filters: dict | None = Field(None, description="筛选条件")
    columns: list[str] | None = Field(None, description="要导出的列")
    format: str = Field("xlsx", description="导出格式", pattern="^(xlsx|xls|csv)$")
    include_headers: bool = Field(True, description="是否包含表头")


class ExcelExportResponse(BaseModel):
    """Excel导出响应模型"""

    file_url: str = Field(..., description="下载链接")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    total_records: int = Field(..., description="导出记录数")
    created_at: str = Field(..., description="创建时间")
    expires_at: str = Field(..., description="过期时间")


class ImportTemplateInfo(BaseModel):
    """导入模板信息模型"""

    template_name: str = Field(..., description="模板名称")
    version: str = Field(..., description="模板版本")
    description: str = Field(..., description="模板描述")
    required_columns: list[str] = Field(..., description="必填列")
    optional_columns: list[str] = Field(..., description="可选列")
    sample_data: list[dict] = Field(default_factory=list, description="示例数据")
    instructions: list[str] = Field(default_factory=list, description="使用说明")


class DataMappingRule(BaseModel):
    """数据映射规则模型"""

    excel_column: str = Field(..., description="Excel列名")
    database_field: str = Field(..., description="数据库字段名")
    data_type: str = Field(..., description="数据类型")
    required: bool = Field(False, description="是否必填")
    default_value: str | None = Field(None, description="默认值")
    validation_rules: list[str] = Field(default_factory=list, description="验证规则")
    transformation: str | None = Field(None, description="数据转换规则")


class ImportConfiguration(BaseModel):
    """导入配置模型"""

    sheet_name: str = Field("土地物业资产数据", description="工作表名称")
    start_row: int = Field(1, description="开始行号（从1开始）")
    header_row: int = Field(1, description="表头行号")
    skip_empty_rows: bool = Field(True, description="是否跳过空行")
    max_errors: int = Field(100, description="最大错误数")
    batch_size: int = Field(1000, description="批处理大小")
    mapping_rules: list[DataMappingRule] = Field(
        default_factory=list, description="字段映射规则"
    )
    validation_enabled: bool = Field(True, description="是否启用数据验证")
    duplicate_handling: str = Field(
        "skip", description="重复数据处理方式", pattern="^(skip|update|error)$"
    )


class ImportPreviewResponse(BaseModel):
    """导入预览响应模型"""

    total_rows: int = Field(..., description="总行数")
    preview_data: list[dict] = Field(..., description="预览数据（前10行）")
    column_mapping: dict[str, Any] = Field(..., description="列映射关系")
    validation_summary: dict[str, Any] = Field(..., description="验证摘要")
    estimated_import_time: int = Field(..., description="预估导入时间（秒）")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    recommendations: list[str] = Field(default_factory=list, description="建议信息")
