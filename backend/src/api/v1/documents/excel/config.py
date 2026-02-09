"""
Excel配置管理模块
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import not_found, validation_error
from src.database import get_async_db
from src.enums.task import ExcelConfigType, TaskType
from src.middleware.auth import require_permission
from src.models.auth import User
from src.schemas.excel_advanced import ExcelConfigCreate
from src.services.excel.excel_config_service import (
    ExcelConfigService,
    get_excel_config_service,
)

router = APIRouter()


def _resolve_service(service: ExcelConfigService | Any) -> ExcelConfigService | Any:
    if isinstance(service, DependsParam):
        return get_excel_config_service()
    return service


def _resolve_task_type(config_type: str) -> TaskType:
    mapping = {
        ExcelConfigType.IMPORT.value: TaskType.EXCEL_IMPORT,
        ExcelConfigType.EXPORT.value: TaskType.EXCEL_EXPORT,
        ExcelConfigType.VALIDATION.value: TaskType.DATA_VALIDATION,
        ExcelConfigType.FIELD_MAPPING.value: TaskType.EXCEL_IMPORT,
    }
    key = config_type.strip().lower()
    if key not in mapping:
        raise validation_error(f"未知配置类型: {config_type}")
    return mapping[key]


def _build_format_config(config_data: dict[str, Any]) -> dict[str, Any] | None:
    default_values = config_data.pop("default_values", None)
    description = config_data.pop("description", None)
    format_config: dict[str, Any] = {}
    if default_values:
        format_config["default_values"] = default_values
    if description:
        format_config["description"] = description
    return format_config or None


@router.post("/configs", summary="创建Excel配置")
async def create_excel_config(
    config_in: ExcelConfigCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> dict[str, Any]:
    """
    创建Excel导入导出配置

    - **config_in**: 配置信息
    """
    _ = current_user
    config_data = config_in.model_dump()
    config_data["task_type"] = _resolve_task_type(config_data["config_type"])

    format_config = _build_format_config(config_data)
    if format_config:
        config_data["format_config"] = format_config

    resolved_service = _resolve_service(service)
    config = await resolved_service.create_config(db=db, config_data=config_data)
    return {
        "message": "配置创建成功",
        "config_id": config.id,
        "config_name": config.config_name,
    }


@router.get("/configs", summary="获取Excel配置列表")
async def get_excel_configs(
    config_type: str | None = Query(None, description="配置类型"),
    task_type: str | None = Query(None, description="任务类型"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> dict[str, Any]:
    """
    获取Excel配置列表

    - **config_type**: 按配置类型筛选
    - **task_type**: 按任务类型筛选
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    configs = await resolved_service.get_configs(
        db=db,
        limit=50,
        config_type=config_type,
        task_type=task_type,
    )
    return {"items": configs, "total": len(configs)}


@router.get("/configs/default", summary="获取默认Excel配置")
async def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> Any:
    """
    获取默认的Excel配置

    - **config_type**: 配置类型
    - **task_type**: 任务类型
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    config = await resolved_service.get_default_config(
        db=db,
        config_type=config_type,
        task_type=task_type,
    )
    if not config:
        raise not_found(
            "未找到默认配置",
            resource_type="excel_config",
            resource_id=f"{config_type}_{task_type}",
        )
    return config


@router.get("/configs/{config_id}", summary="获取Excel配置详情")
async def get_excel_config(
    config_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> Any:
    """
    获取单个Excel配置的详细信息

    - **config_id**: 配置ID
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    config = await resolved_service.get_config(db=db, config_id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )
    return config


@router.put("/configs/{config_id}", summary="更新Excel配置")
async def update_excel_config(
    config_id: str,
    config_in: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> dict[str, Any]:
    """
    更新Excel配置

    - **config_id**: 配置ID
    - **config_in**: 更新数据
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    config = await resolved_service.get_config(db=db, config_id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )

    config_data = dict(config_in)
    if "config_type" in config_data and "task_type" not in config_data:
        config_data["task_type"] = _resolve_task_type(str(config_data["config_type"]))

    format_config = _build_format_config(config_data)
    if format_config:
        current_format = config.format_config if config.format_config else {}
        format_config = {**current_format, **format_config}
        config_data["format_config"] = format_config

    updated_config = await resolved_service.update_config(
        db=db,
        config=config,
        config_data=config_data,
    )
    return {"message": "配置更新成功", "config_id": updated_config.id}


@router.delete("/configs/{config_id}", summary="删除Excel配置")
async def delete_excel_config(
    config_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
    service: ExcelConfigService = Depends(get_excel_config_service),
) -> dict[str, str]:
    """
    删除Excel配置

    - **config_id**: 配置ID
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    await resolved_service.delete_config(db=db, config_id=config_id)
    return {"message": "配置删除成功"}
