"""
Excel配置管理模块
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.exception_handler import not_found, validation_error
from src.database import get_db
from src.enums.task import ExcelConfigType, TaskType
from src.middleware.auth import require_permission
from src.models.auth import User
from src.models.task import ExcelTaskConfig
from src.schemas.excel_advanced import ExcelConfigCreate

router = APIRouter()


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
def create_excel_config(
    config_in: ExcelConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> dict[str, Any]:
    """
    创建Excel导入导出配置

    - **config_in**: 配置信息
    """
    from src.crud.task import excel_task_config_crud

    config_data = config_in.model_dump()
    config_data["task_type"] = _resolve_task_type(config_data["config_type"])

    format_config = _build_format_config(config_data)
    if format_config:
        config_data["format_config"] = format_config

    if config_data.get("is_default") is True:
        db.query(ExcelTaskConfig).filter(
            ExcelTaskConfig.config_type == config_data["config_type"],
            ExcelTaskConfig.task_type == config_data["task_type"],
            ExcelTaskConfig.is_default.is_(True),
        ).update({"is_default": False})

    config = excel_task_config_crud.create(db=db, obj_in=config_data)
    return {
        "message": "配置创建成功",
        "config_id": config.id,
        "config_name": config.config_name,
    }


@router.get("/configs", summary="获取Excel配置列表")
def get_excel_configs(
    config_type: str | None = Query(None, description="配置类型"),
    task_type: str | None = Query(None, description="任务类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> dict[str, Any]:
    """
    获取Excel配置列表

    - **config_type**: 按配置类型筛选
    - **task_type**: 按任务类型筛选
    """
    from src.crud.task import excel_task_config_crud

    configs = excel_task_config_crud.get_multi(
        db=db, limit=50, config_type=config_type, task_type=task_type
    )
    return {"items": configs, "total": len(configs)}


@router.get("/configs/default", summary="获取默认Excel配置")
def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> Any:
    """
    获取默认的Excel配置

    - **config_type**: 配置类型
    - **task_type**: 任务类型
    """
    from src.crud.task import excel_task_config_crud

    config = excel_task_config_crud.get_default(
        db=db, config_type=config_type, task_type=task_type
    )
    if not config:
        raise not_found(
            "未找到默认配置",
            resource_type="excel_config",
            resource_id=f"{config_type}_{task_type}",
        )
    return config


@router.get("/configs/{config_id}", summary="获取Excel配置详情")
def get_excel_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> Any:
    """
    获取单个Excel配置的详细信息

    - **config_id**: 配置ID
    """
    from src.crud.task import excel_task_config_crud

    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )
    return config


@router.put("/configs/{config_id}", summary="更新Excel配置")
def update_excel_config(
    config_id: str,
    config_in: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> dict[str, Any]:
    """
    更新Excel配置

    - **config_id**: 配置ID
    - **config_in**: 更新数据
    """
    from src.crud.task import excel_task_config_crud

    config = excel_task_config_crud.get(db=db, id=config_id)
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

    if config_data.get("is_default") is True:
        target_config_type = config_data.get("config_type", config.config_type)
        target_task_type = config_data.get("task_type", config.task_type)
        db.query(ExcelTaskConfig).filter(
            ExcelTaskConfig.config_type == target_config_type,
            ExcelTaskConfig.task_type == target_task_type,
            ExcelTaskConfig.is_default.is_(True),
            ExcelTaskConfig.id != config.id,
        ).update({"is_default": False})

    updated_config = excel_task_config_crud.update(
        db=db, db_obj=config, obj_in=config_data
    )
    return {"message": "配置更新成功", "config_id": updated_config.id}


@router.delete("/configs/{config_id}", summary="删除Excel配置")
def delete_excel_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> dict[str, str]:
    """
    删除Excel配置

    - **config_id**: 配置ID
    """
    from src.crud.task import excel_task_config_crud

    excel_task_config_crud.remove(db=db, id=config_id)
    return {"message": "配置删除成功"}
