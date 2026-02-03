from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import (
    BaseBusinessError,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.task import excel_task_config_crud, task_crud
from ....database import get_db
from ....enums.task import TaskStatus
from ....middleware.auth import (
    get_current_active_user,
    require_admin,
    require_permission,
)
from ....models.auth import User
from ....schemas.task import (
    ExcelTaskConfigCreate,
    ExcelTaskConfigResponse,
    TaskCancelRequest,
    TaskCreate,
    TaskHistoryResponse,
    TaskResponse,
    TaskStatistics,
    TaskUpdate,
)
from ....services.task import task_service
from ....services.task.access import ensure_task_access, resolve_task_user_filter


class BusinessLogicError(Exception):
    pass


router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.post("/", response_model=TaskResponse, summary="创建新任务")
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    创建新的异步任务
    """
    try:
        task = task_service.create_task(db=db, obj_in=task_in, user_id=current_user.id)
        return TaskResponse.model_validate(task)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建任务失败: {str(e)}")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[TaskResponse]],
    summary="获取任务列表",
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[TaskResponse]],
    summary="获取任务列表",
)
def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    task_type: str | None = Query(None, description="任务类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    user_id: str | None = Query(None, description="用户ID筛选"),
    created_after: str | None = Query(None, description="创建时间起始筛选"),
    created_before: str | None = Query(None, description="创建时间结束筛选"),
    order_by: str = Query("created_at", description="排序字段"),
    order_dir: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    获取任务列表，支持分页和筛选
    """
    try:
        # 处理时间筛选
        created_after_dt = None
        created_before_dt = None
        if created_after:
            created_after_dt = datetime.fromisoformat(created_after)
        if created_before:
            created_before_dt = datetime.fromisoformat(created_before)

        skip = (page - 1) * page_size
        effective_user_id = resolve_task_user_filter(user_id, current_user)
        tasks = task_crud.get_multi(
            db=db,
            skip=skip,
            limit=page_size,
            task_type=task_type,
            status=status,
            user_id=effective_user_id,
            created_after=created_after_dt,
            created_before=created_before_dt,
            order_by=order_by,
            order_dir=order_dir,
        )

        # 计算总数
        total = task_crud.count(
            db=db,
            task_type=task_type,
            status=status,
            user_id=effective_user_id,
            created_after=created_after_dt,
            created_before=created_before_dt,
        )

        # Convert AsyncTask models to TaskResponse schemas
        task_responses = [TaskResponse.model_validate(task) for task in tasks]

        return ResponseHandler.paginated(
            data=task_responses,
            page=page,
            page_size=page_size,
            total=total,
            message="获取任务列表成功",
        )
    except Exception as e:
        raise internal_error(f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
def get_task(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    获取单个任务的详细信息
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    ensure_task_access(task, current_user)
    result: TaskResponse = TaskResponse.model_validate(task)
    return result


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
def update_task(
    task_id: str = Path(..., description="任务ID"),
    task_in: TaskUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    更新任务信息
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    ensure_task_access(task, current_user)
    try:
        updated_task = task_service.update_task(db=db, task_id=task_id, obj_in=task_in)
        return TaskResponse.model_validate(updated_task)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新任务失败: {str(e)}")


@router.post("/{task_id}/cancel", response_model=TaskResponse, summary="取消任务")
def cancel_task(
    task_id: str = Path(..., description="任务ID"),
    cancel_request: TaskCancelRequest | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    取消正在运行的任务
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    ensure_task_access(task, current_user)
    try:
        updated_task = task_service.cancel_task(
            db=db,
            task_id=task_id,
            reason=cancel_request.reason if cancel_request else None,
        )
        return TaskResponse.model_validate(updated_task)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"取消任务失败: {str(e)}")


@router.delete("/{task_id}", summary="删除任务")
def delete_task(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    删除任务（软删除）
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    ensure_task_access(task, current_user)
    try:
        task_service.delete_task(db=db, task_id=task_id)
        return {"message": "任务删除成功"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除任务失败: {str(e)}")


@router.get(
    "/{task_id}/history",
    response_model=list[TaskHistoryResponse],
    summary="获取任务历史",
)
def get_task_history(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TaskHistoryResponse]:
    """
    获取任务的历史记录
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    ensure_task_access(task, current_user)

    try:
        history = task_crud.get_history(db=db, task_id=task_id)
        # Convert TaskHistory models to TaskHistoryResponse schemas
        result: list[TaskHistoryResponse] = [
            TaskHistoryResponse.model_validate(h) for h in history
        ]
        return result
    except Exception as e:
        raise internal_error(f"获取任务历史失败: {str(e)}")


@router.get("/statistics", response_model=TaskStatistics, summary="获取任务统计")
def get_task_statistics(
    user_id: str | None = Query(None, description="用户ID筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskStatistics:
    """
    获取任务统计信息
    """
    try:
        effective_user_id = resolve_task_user_filter(user_id, current_user)
        stats = task_service.get_statistics(db=db, user_id=effective_user_id)
        return TaskStatistics.model_validate(stats)
    except Exception as e:
        raise internal_error(f"获取任务统计失败: {str(e)}")


@router.get("/running", response_model=list[TaskResponse], summary="获取正在运行的任务")
def get_running_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TaskResponse]:
    """
    获取当前正在运行的所有任务
    """
    try:
        effective_user_id = resolve_task_user_filter(None, current_user)
        tasks = task_crud.get_multi(
            db=db,
            limit=100,
            status=TaskStatus.RUNNING.value,
            user_id=effective_user_id,
            order_by="started_at",
            order_dir="asc",
        )
        return [TaskResponse.model_validate(task) for task in tasks]
    except Exception as e:
        raise internal_error(f"获取运行任务失败: {str(e)}")


@router.get("/recent", response_model=list[TaskResponse], summary="获取最近任务")
def get_recent_tasks(
    page_size: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TaskResponse]:
    """
    获取最近的任务
    """
    try:
        tasks = task_crud.get_multi(
            db=db,
            limit=page_size,
            user_id=resolve_task_user_filter(None, current_user),
            order_by="created_at",
            order_dir="desc",
        )
        return [TaskResponse.model_validate(task) for task in tasks]
    except Exception as e:
        raise internal_error(f"获取最近任务失败: {str(e)}")


# ===== Excel任务配置管理 =====


@router.post(
    "/configs/excel",
    response_model=ExcelTaskConfigResponse,
    summary="创建Excel任务配置",
)
def create_excel_config(
    config_in: ExcelTaskConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> ExcelTaskConfigResponse:
    """
    创建Excel任务配置
    """
    try:
        config = task_service.create_excel_config(
            db=db, obj_in=config_in, user_id=current_user.id
        )
        return ExcelTaskConfigResponse.model_validate(config)
    except Exception as e:
        raise internal_error(f"创建Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel",
    response_model=list[ExcelTaskConfigResponse],
    summary="获取Excel配置列表",
)
def get_excel_configs(
    config_type: str | None = Query(None, description="配置类型"),
    task_type: str | None = Query(None, description="任务类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> list[ExcelTaskConfigResponse]:
    """
    获取Excel任务配置列表
    """
    try:
        configs = excel_task_config_crud.get_multi(
            db=db, limit=50, config_type=config_type, task_type=task_type
        )
        return [ExcelTaskConfigResponse.model_validate(cfg) for cfg in configs]
    except Exception as e:
        raise internal_error(f"获取Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel/default",
    response_model=ExcelTaskConfigResponse,
    summary="获取默认Excel配置",
)
def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> ExcelTaskConfigResponse:
    """
    获取默认的Excel任务配置
    """
    try:
        config = excel_task_config_crud.get_default(
            db=db, config_type=config_type, task_type=task_type
        )
        if not config:
            raise not_found("未找到默认配置", resource_type="excel_config")
        return ExcelTaskConfigResponse.model_validate(config)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取默认Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel/{config_id}",
    response_model=ExcelTaskConfigResponse,
    summary="获取Excel配置详情",
)
def get_excel_config(
    config_id: str = Path(..., description="配置ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "read")),
) -> ExcelTaskConfigResponse:
    """
    获取单个Excel配置的详细信息
    """
    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )
    result: ExcelTaskConfigResponse = ExcelTaskConfigResponse.model_validate(config)
    return result


@router.put(
    "/configs/excel/{config_id}",
    response_model=ExcelTaskConfigResponse,
    summary="更新Excel配置",
)
def update_excel_config(
    config_id: str = Path(..., description="配置ID"),
    config_in: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> ExcelTaskConfigResponse:
    """
    更新Excel任务配置
    """
    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise not_found(
            "配置不存在", resource_type="excel_config", resource_id=config_id
        )

    try:
        updated_config = excel_task_config_crud.update(
            db=db, db_obj=config, obj_in=config_in
        )
        result: ExcelTaskConfigResponse = ExcelTaskConfigResponse.model_validate(
            updated_config
        )
        return result
    except Exception as e:
        raise internal_error(f"更新Excel配置失败: {str(e)}")


@router.delete("/configs/excel/{config_id}", summary="删除Excel配置")
def delete_excel_config(
    config_id: str = Path(..., description="配置ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("excel_config", "write")),
) -> dict[str, str]:
    """
    删除Excel配置（软删除）
    """
    try:
        # Use soft deletion by setting is_active=False
        config = excel_task_config_crud.get(db=db, id=config_id)
        if not config:
            raise not_found(
                "配置不存在", resource_type="excel_config", resource_id=config_id
            )

        excel_task_config_crud.update(db=db, db_obj=config, obj_in={"is_active": False})
        return {"message": "Excel配置删除成功"}
    except Exception as e:
        raise internal_error(f"删除Excel配置失败: {str(e)}")


@router.get("/cleanup", summary="清理过期任务")
def cleanup_old_tasks(
    days: int = Query(30, ge=1, le=365, description="清理多少天前的任务"),
    is_dry_run: bool = Query(False, description="是否为试运行"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    清理过期的任务记录
    """
    try:
        return task_service.cleanup_old_tasks(db=db, days=days, dry_run=is_dry_run)
    except Exception as e:
        raise internal_error(f"清理任务失败: {str(e)}")
