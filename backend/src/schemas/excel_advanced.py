"""
Excel高级功能相关的Pydantic模型
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

from .task import TaskType


class ExcelExportRequest(BaseModel):
    """Excel导出请求模型"""

    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="筛选条件")
    fields: Optional[List[str]] = Field(None, description="导出字段列表")
    export_format: str = Field("xlsx", pattern="^(xlsx|xls|csv)$", description="导出格式")
    sheet_name: Optional[str] = Field(None, description="工作表名称")
    include_headers: bool = Field(True, description="是否包含表头")
    date_format: str = Field("%Y-%m-%d", description="日期格式")
    config_id: Optional[str] = Field(None, description="使用配置ID")

    class Config:
        json_schema_extra = {
            "example": {
                "filters": {
                    "ownership_status": "已确权",
                    "property_nature": "经营性"
                },
                "fields": ["property_name", "address", "ownership_status"],
                "export_format": "xlsx",
                "sheet_name": "资产数据",
                "include_headers": True,
                "date_format": "%Y-%m-%d"
            }
        }


class ExcelImportRequest(BaseModel):
    """Excel导入请求模型"""

    config_id: Optional[str] = Field(None, description="使用配置ID")
    validate_data: bool = Field(True, description="是否验证数据")
    create_assets: bool = Field(True, description="是否创建资产")
    update_existing: bool = Field(True, description="是否更新已存在资产")
    skip_errors: bool = Field(False, description="是否跳过错误行")
    batch_size: int = Field(100, ge=1, le=1000, description="批处理大小")

    class Config:
        json_schema_extra = {
            "example": {
                "config_id": "config_123",
                "validate_data": True,
                "create_assets": True,
                "update_existing": True,
                "skip_errors": False,
                "batch_size": 100
            }
        }


class ExcelPreviewRequest(BaseModel):
    """Excel预览请求模型"""

    max_rows: int = Field(10, ge=1, le=100, description="预览最大行数")
    sheet_index: int = Field(0, ge=0, description="工作表索引")

    class Config:
        json_schema_extra = {
            "example": {
                "max_rows": 10,
                "sheet_index": 0
            }
        }


class ExcelFieldMapping(BaseModel):
    """Excel字段映射模型"""

    excel_column: str = Field(..., description="Excel列名")
    system_field: str = Field(..., description="系统字段名")
    data_type: str = Field(..., description="数据类型")
    required: bool = Field(False, description="是否必填")
    default_value: Optional[str] = Field(None, description="默认值")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")

    class Config:
        json_schema_extra = {
            "example": {
                "excel_column": "物业名称",
                "system_field": "property_name",
                "data_type": "string",
                "required": True,
                "default_value": None,
                "validation_rules": {
                    "min_length": 1,
                    "max_length": 200
                }
            }
        }


class ExcelValidationRule(BaseModel):
    """Excel验证规则模型"""

    field_name: str = Field(..., description="字段名")
    rule_type: str = Field(..., description="规则类型")
    rule_value: Union[str, int, float, bool, List, Dict] = Field(..., description="规则值")
    error_message: str = Field(..., description="错误消息")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "ownership_status",
                "rule_type": "enum",
                "rule_value": ["已确权", "未确权", "部分确权"],
                "error_message": "权属状态必须是：已确权、未确权、部分确权之一"
            }
        }


class ExcelImportResult(BaseModel):
    """Excel导入结果模型"""

    total_rows: int = Field(..., description="总行数")
    processed_rows: int = Field(..., description="已处理行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    skipped_rows: int = Field(..., description="跳过行数")
    created_assets: int = Field(..., description="创建的资产数")
    updated_assets: int = Field(..., description="更新的资产数")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误信息列表")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="警告信息列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total_rows": 100,
                "processed_rows": 95,
                "success_rows": 90,
                "failed_rows": 5,
                "skipped_rows": 0,
                "created_assets": 80,
                "updated_assets": 10,
                "errors": [
                    {
                        "row": 15,
                        "column": "物业名称",
                        "error": "此字段为必填",
                        "value": None
                    }
                ],
                "warnings": [
                    {
                        "row": 20,
                        "message": "建议填写土地面积"
                    }
                ]
            }
        }


class ExcelExportResult(BaseModel):
    """Excel导出结果模型"""

    file_path: str = Field(..., description="文件路径")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    record_count: int = Field(..., description="记录数量")
    columns: List[str] = Field(..., description="导出的列名")
    export_time: datetime = Field(..., description="导出时间")
    download_url: str = Field(..., description="下载链接")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/exports/asset_export_20240101_123456.xlsx",
                "file_name": "asset_export_20240101_123456.xlsx",
                "file_size": 1024000,
                "record_count": 1000,
                "columns": ["property_name", "address", "ownership_status"],
                "export_time": "2024-01-01T12:34:56",
                "download_url": "/api/v1/excel/download/asset_export_20240101_123456.xlsx"
            }
        }


class ExcelPreviewResponse(BaseModel):
    """Excel预览响应模型"""

    file_name: str = Field(..., description="文件名")
    sheet_names: List[str] = Field(..., description="工作表名称列表")
    total_rows: int = Field(..., description="总行数")
    columns: List[str] = Field(..., description="列名列表")
    preview_data: List[Dict[str, Any]] = Field(..., description="预览数据")
    detected_field_mapping: Optional[List[ExcelFieldMapping]] = Field(None, description="检测到的字段映射")

    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "asset_data.xlsx",
                "sheet_names": ["资产数据", "Sheet2"],
                "total_rows": 100,
                "columns": ["物业名称", "地址", "权属状态"],
                "preview_data": [
                    {"物业名称": "示例物业1", "地址": "示例地址1", "权属状态": "已确权"},
                    {"物业名称": "示例物业2", "地址": "示例地址2", "权属状态": "未确权"}
                ]
            }
        }


class ExcelFormatInfo(BaseModel):
    """Excel格式信息模型"""

    supported_formats: List[str] = Field(..., description="支持的导出格式")
    max_file_size: int = Field(..., description="最大文件大小（字节）")
    max_rows: int = Field(..., description="最大行数限制")
    supported_encodings: List[str] = Field(..., description="支持的编码格式")
    default_date_formats: List[str] = Field(..., description="默认日期格式")

    class Config:
        json_schema_extra = {
            "example": {
                "supported_formats": ["xlsx", "xls", "csv"],
                "max_file_size": 52428800,  # 50MB
                "max_rows": 10000,
                "supported_encodings": ["utf-8", "gbk", "gb2312"],
                "default_date_formats": ["%Y-%m-%d", "%Y/%m/%d"]
            }
        }


class ExcelConfigCreate(BaseModel):
    """Excel配置创建模型"""

    config_name: str = Field(..., min_length=1, max_length=200, description="配置名称")
    config_type: str = Field(..., description="配置类型")
    field_mapping: List[ExcelFieldMapping] = Field(..., description="字段映射配置")
    validation_rules: List[ExcelValidationRule] = Field(default_factory=list, description="验证规则")
    default_values: Dict[str, Any] = Field(default_factory=dict, description="默认值")
    is_default: bool = Field(False, description="是否默认配置")
    description: Optional[str] = Field(None, description="配置描述")

    class Config:
        json_schema_extra = {
            "example": {
                "config_name": "标准资产导入配置",
                "config_type": "import",
                "field_mapping": [
                    {
                        "excel_column": "物业名称",
                        "system_field": "property_name",
                        "data_type": "string",
                        "required": True
                    }
                ],
                "validation_rules": [
                    {
                        "field_name": "ownership_status",
                        "rule_type": "enum",
                        "rule_value": ["已确权", "未确权", "部分确权"],
                        "error_message": "权属状态无效"
                    }
                ],
                "default_values": {
                    "ownership_status": "未确权"
                },
                "is_default": True
            }
        }


class ExcelConfigResponse(BaseModel):
    """Excel配置响应模型"""

    id: str = Field(..., description="配置ID")
    config_name: str = Field(..., description="配置名称")
    config_type: str = Field(..., description="配置类型")
    field_mapping: List[ExcelFieldMapping] = Field(..., description="字段映射配置")
    validation_rules: List[ExcelValidationRule] = Field(default_factory=list, description="验证规则")
    default_values: Dict[str, Any] = Field(default_factory=dict, description="默认值")
    is_default: bool = Field(..., description="是否默认配置")
    is_active: bool = Field(..., description="是否启用")
    description: Optional[str] = Field(None, description="配置描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ExcelStatusResponse(BaseModel):
    """Excel任务状态响应模型"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., description="进度百分比")
    total_items: Optional[int] = Field(None, description="总项目数")
    processed_items: int = Field(..., description="已处理项目数")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "status": "running",
                "progress": 45,
                "total_items": 1000,
                "processed_items": 450,
                "created_at": "2024-01-01T10:00:00",
                "started_at": "2024-01-01T10:00:05"
            }
        }