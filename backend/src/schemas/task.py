from typing import Any
"""
任务管理相关的Pydantic模型
"""

from datetime import datetime


from pydantic import BaseModel, ConfigDict, Field

from ..enums.task import TaskStatus, TaskType


class TaskCreate(BaseModel):
    """创建任务请求模型"""

    task_type: TaskType = Field(..., description="任务类型")
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str | None = Field(None, description="任务描述")
    parameters: dict[str, Any] | None = Field(
        default_factory=dict, description="任务参数"
    )
    config: dict[str, Any] | None = Field(default_factory=dict, description="任务配置")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )


class TaskUpdate(BaseModel):
    """更新任务请求模型"""

    status: TaskStatus | None = Field(None, description="任务状态")
    progress: int | None = Field(None, ge=0, le=100, description="进度百分比")
    processed_items: int | None = Field(None, ge=0, description="已处理项目数")
    failed_items: int | None = Field(None, ge=0, description="失败项目数")
    error_message: str | None = Field(None, description="错误信息")
    result_data: dict[str, Any] | None = Field(None, description="结果数据")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )


class TaskResponse(BaseModel):
    """任务响应模型"""

    id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    title: str = Field(..., description="任务标题")
    description: str | None = Field(None, description="任务描述")

    created_at: datetime = Field(..., description="创建时间")
    started_at: datetime | None = Field(None, description="开始时间")
    completed_at: datetime | None = Field(None, description="完成时间")

    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    total_items: int | None = Field(None, description="总项目数")
    processed_items: int = Field(..., ge=0, description="已处理项目数")
    failed_items: int = Field(..., ge=0, description="失败项目数")

    result_data: dict[str, Any] | None = Field(None, description="结果数据")
    error_message: str | None = Field(None, description="错误信息")
    parameters: dict[str, Any] | None = Field(None, description="任务参数")

    success_rate: float = Field(..., description="成功率")
    duration_seconds: float = Field(..., description="持续时间（秒）")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"description": "任务响应示例"}},
    )


class TaskListResponse(BaseModel):
    """任务列表响应模型"""

    items: list[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    limit: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )


class TaskHistoryResponse(BaseModel):
    """任务历史响应模型"""

    id: str = Field(..., description="历史记录ID")
    task_id: str = Field(..., description="任务ID")
    action: str = Field(..., description="操作类型")
    message: str = Field(..., description="消息内容")
    details: dict[str, Any] | None = Field(None, description="详细信息")
    created_at: datetime = Field(..., description="创建时间")
    user_id: str | None = Field(None, description="用户ID")

    model_config = ConfigDict(from_attributes=True)


class TaskStatistics(BaseModel):
    """任务统计模型"""

    total_tasks: int = Field(..., description="总任务数")
    running_tasks: int = Field(..., description="运行中任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")

    by_type: dict[str, int] = Field(..., description="按类型统计")
    by_status: dict[str, int] = Field(..., description="按状态统计")
    avg_duration: float | None = Field(None, description="平均持续时间（秒）")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )


class ExcelTaskConfigCreate(BaseModel):
    """Excel任务配置创建模型"""

    config_name: str = Field(..., min_length=1, max_length=200, description="配置名称")
    config_type: str = Field(..., description="配置类型")
    task_type: TaskType = Field(..., description="任务类型")
    field_mapping: dict[str, Any] | None = Field(
        default_factory=dict, description="字段映射配置"
    )
    validation_rules: dict[str, Any] | None = Field(
        default_factory=dict, description="验证规则配置"
    )
    format_config: dict[str, Any] | None = Field(
        default_factory=dict, description="格式配置"
    )
    is_default: bool = Field(False, description="是否默认配置")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )


class ExcelTaskConfigResponse(BaseModel):
    """Excel任务配置响应模型"""

    id: str = Field(..., description="配置ID")
    config_name: str = Field(..., description="配置名称")
    config_type: str = Field(..., description="配置类型")
    task_type: str = Field(..., description="任务类型")
    field_mapping: dict[str, Any] | None = Field(None, description="字段映射配置")
    validation_rules: dict[str, Any] | None = Field(None, description="验证规则配置")
    format_config: dict[str, Any] | None = Field(None, description="格式配置")
    is_default: bool = Field(..., description="是否默认配置")
    is_active: bool = Field(..., description="是否启用")
    created_by: str | None = Field(None, description="创建者")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class TaskCancelRequest(BaseModel):
    """任务取消请求模型"""

    reason: str | None = Field(None, description="取消原因")

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "任务创建示例"}}
    )
