"""
任务管理相关的Pydantic模型
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..enums.task import TaskStatus, TaskType, ExcelConfigType, TaskPriority


class TaskCreate(BaseModel):
    """创建任务请求模型"""

    task_type: TaskType = Field(..., description="任务类型")
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务参数")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务配置")

    class Config:
        json_schema_extra = {
            "example": {
                "task_type": "excel_export",
                "title": "导出资产数据",
                "description": "导出筛选的资产数据到Excel文件",
                "parameters": {
                    "filters": {"ownership_status": "已确权"},
                    "export_format": "xlsx"
                },
                "config": {
                    "include_headers": True,
                    "sheet_name": "资产数据"
                }
            }
        }


class TaskUpdate(BaseModel):
    """更新任务请求模型"""

    status: Optional[TaskStatus] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度百分比")
    processed_items: Optional[int] = Field(None, ge=0, description="已处理项目数")
    failed_items: Optional[int] = Field(None, ge=0, description="失败项目数")
    error_message: Optional[str] = Field(None, description="错误信息")
    result_data: Optional[Dict[str, Any]] = Field(None, description="结果数据")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "running",
                "progress": 45,
                "processed_items": 450,
                "failed_items": 5
            }
        }


class TaskResponse(BaseModel):
    """任务响应模型"""

    id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")

    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    total_items: Optional[int] = Field(None, description="总项目数")
    processed_items: int = Field(..., ge=0, description="已处理项目数")
    failed_items: int = Field(..., ge=0, description="失败项目数")

    result_data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    parameters: Optional[Dict[str, Any]] = Field(None, description="任务参数")

    success_rate: float = Field(..., description="成功率")
    duration_seconds: float = Field(..., description="持续时间（秒）")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "task_123",
                "task_type": "excel_export",
                "status": "completed",
                "title": "导出资产数据",
                "description": "成功导出1000条资产记录",
                "created_at": "2024-01-01T10:00:00",
                "started_at": "2024-01-01T10:00:05",
                "completed_at": "2024-01-01T10:02:30",
                "progress": 100,
                "total_items": 1000,
                "processed_items": 1000,
                "failed_items": 0,
                "result_data": {
                    "file_path": "/exports/asset_export_20240101.xlsx",
                    "file_size": 1024000
                },
                "success_rate": 100.0,
                "duration_seconds": 145.5
            }
        }


class TaskListResponse(BaseModel):
    """任务列表响应模型"""

    items: List[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    limit: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 10,
                "page": 1,
                "limit": 20,
                "pages": 1
            }
        }


class TaskHistoryResponse(BaseModel):
    """任务历史响应模型"""

    id: str = Field(..., description="历史记录ID")
    task_id: str = Field(..., description="任务ID")
    action: str = Field(..., description="操作类型")
    message: str = Field(..., description="消息内容")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    created_at: datetime = Field(..., description="创建时间")
    user_id: Optional[str] = Field(None, description="用户ID")

    class Config:
        from_attributes = True


class TaskStatistics(BaseModel):
    """任务统计模型"""

    total_tasks: int = Field(..., description="总任务数")
    running_tasks: int = Field(..., description="运行中任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")

    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_status: Dict[str, int] = Field(..., description="按状态统计")
    avg_duration: Optional[float] = Field(None, description="平均持续时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tasks": 100,
                "running_tasks": 5,
                "completed_tasks": 90,
                "failed_tasks": 5,
                "by_type": {
                    "excel_export": 60,
                    "excel_import": 30,
                    "batch_update": 10
                },
                "by_status": {
                    "completed": 90,
                    "failed": 5,
                    "running": 5
                },
                "avg_duration": 120.5
            }
        }


class ExcelTaskConfigCreate(BaseModel):
    """Excel任务配置创建模型"""

    config_name: str = Field(..., min_length=1, max_length=200, description="配置名称")
    config_type: str = Field(..., description="配置类型")
    task_type: TaskType = Field(..., description="任务类型")
    field_mapping: Optional[Dict[str, Any]] = Field(default_factory=dict, description="字段映射配置")
    validation_rules: Optional[Dict[str, Any]] = Field(default_factory=dict, description="验证规则配置")
    format_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="格式配置")
    is_default: bool = Field(False, description="是否默认配置")

    class Config:
        json_schema_extra = {
            "example": {
                "config_name": "标准资产导出配置",
                "config_type": "export",
                "task_type": "excel_export",
                "field_mapping": {
                    "property_name": "物业名称",
                    "address": "地址",
                    "ownership_status": "权属状态"
                },
                "validation_rules": {
                    "required_fields": ["property_name", "address"]
                },
                "format_config": {
                    "include_headers": True,
                    "sheet_name": "资产数据"
                }
            }
        }


class ExcelTaskConfigResponse(BaseModel):
    """Excel任务配置响应模型"""

    id: str = Field(..., description="配置ID")
    config_name: str = Field(..., description="配置名称")
    config_type: str = Field(..., description="配置类型")
    task_type: str = Field(..., description="任务类型")
    field_mapping: Optional[Dict[str, Any]] = Field(None, description="字段映射配置")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则配置")
    format_config: Optional[Dict[str, Any]] = Field(None, description="格式配置")
    is_default: bool = Field(..., description="是否默认配置")
    is_active: bool = Field(..., description="是否启用")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class TaskCancelRequest(BaseModel):
    """任务取消请求模型"""

    reason: Optional[str] = Field(None, description="取消原因")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "用户取消操作"
            }
        }