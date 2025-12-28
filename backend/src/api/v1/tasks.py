from typing import Any


class BusinessLogicError(Exception):
    """Business logic error"""

    pass


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
任务管理API路由
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...crud.task import excel_task_config_crud, task_crud
from ...database import get_db
from ...enums.task import TaskStatus
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...models.task import AsyncTask
from ...schemas.task import (
    ExcelTaskConfigCreate,
    ExcelTaskConfigResponse,
    TaskCancelRequest,
    TaskCreate,
    TaskHistoryResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatistics,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.post("/", response_model=TaskResponse, summary="创建新任务")
async def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建新的异步任务

    - **task_type**: 任务类型
    - **title**: 任务标题
    - **description**: 任务描述
    - **parameters**: 任务参数
    - **config**: 任务配置
    """
    try:
        task = task_crud.create(db=db, obj_in=task_in)
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/", response_model=TaskListResponse, summary="获取任务列表")
async def get_tasks(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    task_type: str | None = Query(None, description="任务类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    user_id: str | None = Query(None, description="用户ID筛选"),
    created_after: str | None = Query(None, description="创建时间起始筛选"),
    created_before: str | None = Query(None, description="创建时间结束筛选"),
    order_by: str = Query("created_at", description="排序字段"),
    order_dir: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务列表，支持分页和筛选

    - **skip**: 跳过记录数
    - **limit**: 每页记录数
    - **task_type**: 按任务类型筛选
    - **status**: 按状态筛选
    - **user_id**: 按用户ID筛选
    - **created_after**: 创建时间起始
    - **created_before**: 创建时间结束
    - **order_by**: 排序字段
    - **order_dir**: 排序方向
    """
    try:
        # 处理时间筛选
        created_after_dt = None
        created_before_dt = None
        if created_after:
            created_after_dt = datetime.fromisoformat(created_after)
        if created_before:
            created_before_dt = datetime.fromisoformat(created_before)

        tasks = task_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            task_type=task_type,
            status=status,
            user_id=user_id,
            created_after=created_after_dt,
            created_before=created_before_dt,
            order_by=order_by,
            order_dir=order_dir,
        )

        # 计算总数
        total = task_crud.count(db=db, task_type=task_type, status=status)

        return TaskListResponse(
            items=tasks,
            total=total,
            page=skip // limit + 1,
            limit=limit,
            pages=(total + limit - 1) // limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取单个任务的详细信息

    - **task_id**: 任务ID
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
async def update_task(
    task_id: str = Path(..., description="任务ID"),
    task_in: TaskUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新任务信息

    - **task_id**: 任务ID
    - **task_in**: 更新数据
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查任务是否可以更新
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="已完成的任务无法更新")

    try:
        updated_task = task_crud.update(db=db, db_obj=task, obj_in=task_in)
        return updated_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.post("/{task_id}/cancel", response_model=TaskResponse, summary="取消任务")
async def cancel_task(
    task_id: str = Path(..., description="任务ID"),
    cancel_request: TaskCancelRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    取消正在运行的任务

    - **task_id**: 任务ID
    - **reason**: 取消原因
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查任务是否可以取消
    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="任务无法取消")

    try:
        # 更新任务状态为已取消
        update_data = TaskUpdate(
            status=TaskStatus.CANCELLED,
            error_message=f"任务被取消: {cancel_request.reason if cancel_request and cancel_request.reason else '无原因'}",
        )
        updated_task = task_crud.update(db=db, db_obj=task, obj_in=update_data)
        return updated_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除任务（软删除）

    - **task_id**: 任务ID
    """
    try:
        task_crud.delete(db=db, id=task_id)
        return {"message": "任务删除成功"}
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get(
    "/{task_id}/history",
    response_model=list[TaskHistoryResponse],
    summary="获取任务历史",
)
async def get_task_history(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务的历史记录

    - **task_id**: 任务ID
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        history = task_crud.get_history(db=db, task_id=task_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务历史失败: {str(e)}")


@router.get("/statistics", response_model=TaskStatistics, summary="获取任务统计")
async def get_task_statistics(
    user_id: str | None = Query(None, description="用户ID筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务统计信息

    - **user_id**: 按用户ID筛选
    """
    try:
        stats = task_crud.get_statistics(db=db, user_id=user_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")


@router.get("/running", response_model=list[TaskResponse], summary="获取正在运行的任务")
async def get_running_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前正在运行的所有任务
    """
    try:
        tasks = task_crud.get_multi(
            db=db,
            limit=100,
            status=TaskStatus.RUNNING.value,
            order_by="started_at",
            order_dir="asc",
        )
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取运行任务失败: {str(e)}")


@router.get("/recent", response_model=list[TaskResponse], summary="获取最近任务")
async def get_recent_tasks(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取最近的任务

    - **limit**: 返回数量
    """
    try:
        tasks = task_crud.get_multi(
            db=db, limit=limit, order_by="created_at", order_dir="desc"
        )
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最近任务失败: {str(e)}")


# ===== Excel任务配置管理 =====


@router.post(
    "/configs/excel",
    response_model=ExcelTaskConfigResponse,
    summary="创建Excel任务配置",
)
async def create_excel_config(
    config_in: ExcelTaskConfigCreate, db: Session = Depends(get_db)
):
    """
    创建Excel任务配置

    - **config_name**: 配置名称
    - **config_type**: 配置类型
    - **task_type**: 任务类型
    - **field_mapping**: 字段映射配置
    - **validation_rules**: 验证规则配置
    - **format_config**: 格式配置
    - **is_default**: 是否默认配置
    """
    try:
        config = excel_task_config_crud.create(db=db, obj_in=config_in)
        db.commit()  # Commit at API layer, not CRUD layer
        db.refresh(config)
        return config
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel",
    response_model=list[ExcelTaskConfigResponse],
    summary="获取Excel配置列表",
)
async def get_excel_configs(
    config_type: str | None = Query(None, description="配置类型"),
    task_type: str | None = Query(None, description="任务类型"),
    db: Session = Depends(get_db),
):
    """
    获取Excel任务配置列表

    - **config_type**: 按配置类型筛选
    - **task_type**: 按任务类型筛选
    """
    try:
        configs = excel_task_config_crud.get_multi(
            db=db, limit=50, config_type=config_type, task_type=task_type
        )
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel/default",
    response_model=ExcelTaskConfigResponse,
    summary="获取默认Excel配置",
)
async def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: Session = Depends(get_db),
):
    """
    获取默认的Excel任务配置

    - **config_type**: 配置类型
    - **task_type**: 任务类型
    """
    try:
        config = excel_task_config_crud.get_default(
            db=db, config_type=config_type, task_type=task_type
        )
        if not config:
            raise HTTPException(status_code=404, detail="未找到默认配置")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取默认Excel配置失败: {str(e)}")


@router.get(
    "/configs/excel/{config_id}",
    response_model=ExcelTaskConfigResponse,
    summary="获取Excel配置详情",
)
async def get_excel_config(
    config_id: str = Path(..., description="配置ID"), db: Session = Depends(get_db)
):
    """
    获取单个Excel配置的详细信息

    - **config_id**: 配置ID
    """
    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.put(
    "/configs/excel/{config_id}",
    response_model=ExcelTaskConfigResponse,
    summary="更新Excel配置",
)
async def update_excel_config(
    config_id: str = Path(..., description="配置ID"),
    config_in: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    更新Excel任务配置

    - **config_id**: 配置ID
    - **config_in**: 更新数据
    """
    config = excel_task_config_crud.get(db=db, id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    try:
        updated_config = excel_task_config_crud.update(
            db=db, db_obj=config, obj_in=config_in
        )
        return updated_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新Excel配置失败: {str(e)}")


@router.delete("/configs/excel/{config_id}", summary="删除Excel配置")
async def delete_excel_config(
    config_id: str = Path(..., description="配置ID"), db: Session = Depends(get_db)
):
    """
    删除Excel配置（软删除）

    - **config_id**: 配置ID
    """
    try:
        excel_task_config_crud.delete(db=db, id=config_id)
        return {"message": "Excel配置删除成功"}
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除Excel配置失败: {str(e)}")


@router.get("/cleanup", summary="清理过期任务")
async def cleanup_old_tasks(
    days: int = Query(30, ge=1, le=365, description="清理多少天前的任务"),
    dry_run: bool = Query(False, description="是否为试运行"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    清理过期的任务记录

    - **days**: 清理多少天前的任务
    - **dry_run**: 是否为试运行
    """
    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # 查找过期的任务
        old_tasks = (
            db.query(AsyncTask)
            .filter(
                and_(
                    AsyncTask.created_at < cutoff_date,
                    AsyncTask.status.in_(
                        [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                    ),
                    AsyncTask.is_active,
                )
            )
            .all()
        )

        if dry_run:
            return {
                "message": f"试运行模式，发现 {len(old_tasks)} 个可清理的任务",
                "cleanup_date": cutoff_date.isoformat(),
                "task_count": len(old_tasks),
            }
        else:
            # 执行清理
            count = 0
            for task in old_tasks:
                task.is_active = False
                count += 1

            db.commit()

            return {
                "message": f"成功清理 {count} 个过期任务",
                "cleanup_date": cutoff_date.isoformat(),
                "cleaned_count": count,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理任务失败: {str(e)}")
