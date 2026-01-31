"""
Excel配置管理模块
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.exception_handler import not_found
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.excel_advanced import ExcelConfigCreate

router = APIRouter()


@router.post("/configs", summary="创建Excel配置")
def create_excel_config(
    config_in: ExcelConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    创建Excel导入导出配置

    - **config_in**: 配置信息
    """
    from src.crud.task import excel_task_config_crud

    config = excel_task_config_crud.create(db=db, obj_in=config_in.model_dump())
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
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取Excel配置列表

    - **config_type**: 按配置类型筛选
    - **task_type**: 按任务类型筛选
    """
    from ....crud.task import excel_task_config_crud

    configs = excel_task_config_crud.get_multi(
        db=db, limit=50, config_type=config_type, task_type=task_type
    )
    return {"items": configs, "total": len(configs)}


@router.get("/configs/default", summary="获取默认Excel配置")
def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: Session = Depends(get_db),
) -> Any:
    """
    获取默认的Excel配置

    - **config_type**: 配置类型
    - **task_type**: 任务类型
    """
    from ....crud.task import excel_task_config_crud

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
def get_excel_config(config_id: str, db: Session = Depends(get_db)) -> Any:
    """
    获取单个Excel配置的详细信息

    - **config_id**: 配置ID
    """
    from ....crud.task import excel_task_config_crud

    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )
    return config


@router.put("/configs/{config_id}", summary="更新Excel配置")
def update_excel_config(
    config_id: str, config_in: dict[str, Any], db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    更新Excel配置

    - **config_id**: 配置ID
    - **config_in**: 更新数据
    """
    from ....crud.task import excel_task_config_crud

    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )

    updated_config = excel_task_config_crud.update(
        db=db, db_obj=config, obj_in=config_in
    )
    return {"message": "配置更新成功", "config_id": updated_config.id}


@router.delete("/configs/{config_id}", summary="删除Excel配置")
def delete_excel_config(
    config_id: str, db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    删除Excel配置

    - **config_id**: 配置ID
    """
    from ....crud.task import excel_task_config_crud

    excel_task_config_crud.remove(db=db, id=config_id)
    return {"message": "配置删除成功"}
