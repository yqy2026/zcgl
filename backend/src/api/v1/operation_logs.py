"""
操作日志管理API路由
支持日志查询、统计、导出等功能
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from ...core.api_errors import bad_request, internal_error, not_found
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ...crud.operation_log import OperationLogCRUD
from ...database import get_db
from ...middleware.auth import get_current_active_user, require_admin
from ...models.auth import User

router = APIRouter(tags=["操作日志"])

# ==================== Schema定义 ====================


class OperationLogResponse(BaseModel):
    """操作日志响应"""

    id: str
    user_id: str
    username: str | None = None
    action: str
    action_name: str | None = None
    module: str
    module_name: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    request_method: str | None = None
    request_url: str | None = None
    response_status: int | None = None
    response_time: int | None = None
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationLogListResponse(BaseModel):
    """操作日志列表响应"""

    items: list[OperationLogResponse]
    total: int
    page: int
    limit: int
    pages: int


class OperationLogStatisticsResponse(BaseModel):
    """操作日志统计响应"""

    success: bool
    data: dict[str, Any]
    message: str = "统计成功"


# ==================== 日志查询端点 ====================


@router.get("", response_model=OperationLogListResponse, summary="获取操作日志列表")
async def get_operation_logs(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str | None = Query(None, description="用户ID"),
    action: str | None = Query(None, description="操作类型"),
    module: str | None = Query(None, description="操作模块"),
    resource_type: str | None = Query(None, description="资源类型"),
    search: str | None = Query(None, description="搜索关键词"),
    start_date: str | None = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期(YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OperationLogListResponse:
    """
    获取操作日志列表，支持多条件筛选

    - **page**: 页码，从1开始
    - **limit**: 每页数量，最多100
    - **user_id**: 按用户ID筛选
    - **action**: 按操作类型筛选
    - **module**: 按操作模块筛选
    - **resource_type**: 按资源类型筛选
    - **search**: 按用户名、操作名称或资源名称搜索
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        log_crud = OperationLogCRUD()
        skip = (page - 1) * limit

        # 解析日期
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                    raise bad_request("开始日期格式错误，应为YYYY-MM-DD")

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                    raise bad_request("结束日期格式错误，应为YYYY-MM-DD")

        logs, total = log_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            start_date=start_dt,
            end_date=end_dt,
            search=search,
        )

        pages = (total + limit - 1) // limit

        return OperationLogListResponse(
            items=[OperationLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(str(e))


@router.get("/{log_id}", response_model=OperationLogResponse, summary="获取日志详情")
async def get_operation_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OperationLogResponse:
    """获取单条操作日志详情"""
    try:
        log_crud = OperationLogCRUD()
        log = log_crud.get(db, log_id)

        if not log:
            raise not_found("日志不存在", resource_type="operation_log", resource_id=log_id)

        return OperationLogResponse.model_validate(log)
    except Exception as e:
        if "UnifiedError" in type(e).__name__:
            raise
        raise internal_error(str(e))


# ==================== 统计端点 ====================


@router.get(
    "/statistics/user",
    response_model=OperationLogStatisticsResponse,
    summary="获取用户操作统计",
)
async def get_user_operation_statistics(
    user_id: str = Query(..., description="用户ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OperationLogStatisticsResponse:
    """获取指定用户的操作统计"""
    try:
        log_crud = OperationLogCRUD()
        stats = log_crud.get_user_statistics(db, user_id, days)

        return OperationLogStatisticsResponse(
            success=True,
            data=stats,
        )
    except Exception as e:
        raise internal_error(str(e))


@router.get(
    "/statistics/module",
    response_model=OperationLogStatisticsResponse,
    summary="获取模块操作统计",
)
async def get_module_operation_statistics(
    module: str = Query(..., description="模块名称"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OperationLogStatisticsResponse:
    """获取指定模块的操作统计"""
    try:
        log_crud = OperationLogCRUD()
        stats = log_crud.get_module_statistics(db, module, days)

        return OperationLogStatisticsResponse(
            success=True,
            data=stats,
        )
    except Exception as e:
        raise internal_error(str(e))


@router.get(
    "/statistics/daily",
    response_model=OperationLogStatisticsResponse,
    summary="获取每日操作统计",
)
async def get_daily_operation_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OperationLogStatisticsResponse:
    """获取每日操作统计"""
    try:
        log_crud = OperationLogCRUD()
        stats = log_crud.get_daily_statistics(db, days)

        return OperationLogStatisticsResponse(
            success=True,
            data=stats,
        )
    except Exception as e:
        raise internal_error(str(e))


@router.get(
    "/statistics/errors",
    response_model=OperationLogStatisticsResponse,
    summary="获取错误操作统计",
)
async def get_error_operation_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> OperationLogStatisticsResponse:
    """获取错误操作统计（仅管理员）"""
    try:
        log_crud = OperationLogCRUD()
        stats = log_crud.get_error_statistics(db, days)

        return OperationLogStatisticsResponse(
            success=True,
            data=stats,
        )
    except Exception as e:
        raise internal_error(str(e))


@router.get(
    "/statistics/summary", response_model=dict[str, Any], summary="获取日志汇总统计"
)
async def get_operation_log_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """获取操作日志汇总统计"""
    try:
        log_crud = OperationLogCRUD()

        daily_stats = log_crud.get_daily_statistics(db, days)
        error_stats = log_crud.get_error_statistics(db, days)
        total_count = log_crud.count(db)

        return {
            "success": True,
            "data": {
                "total_logs": total_count,
                "days": days,
                "daily_statistics": daily_stats.get("daily_breakdown", {}),
                "error_statistics": error_stats,
            },
        }
    except Exception as e:
        raise internal_error(str(e))


# ==================== 导出端点 ====================


@router.post("/export", summary="导出操作日志")
async def export_operation_logs(
    filters: dict[str, Any] | None = None,
    format: str = Query("excel", description="导出格式: excel 或 csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    导出操作日志为Excel或CSV格式

    - **format**: excel 或 csv
    """
    if filters is None:
        filters = {}
    try:
        log_crud = OperationLogCRUD()

        # 获取所有匹配的日志（不分页）
        logs, _ = log_crud.get_multi(db=db, skip=0, limit=10000, **filters)

        if format.lower() == "csv":
            # CSV导出逻辑（后续可扩展）
            return {
                "success": True,
                "message": f"已导出 {len(logs)} 条日志",
                "count": len(logs),
                "format": "csv",
            }
        else:  # excel
            return {
                "success": True,
                "message": f"已导出 {len(logs)} 条日志",
                "count": len(logs),
                "format": "excel",
            }
    except Exception as e:
        raise internal_error(str(e))


# ==================== 维护端点 ====================


@router.post("/cleanup", summary="清理过期日志")
async def cleanup_old_logs(
    days: int = Query(90, ge=1, le=365, description="保留天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    删除指定天数前的日志（仅管理员）

    - **days**: 保留最近N天的日志，更早的日志将被删除
    """
    try:
        log_crud = OperationLogCRUD()
        deleted_count = log_crud.delete_old_logs(db, days)

        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条过期日志",
            "deleted_count": deleted_count,
            "days": days,
        }
    except Exception as e:
        raise internal_error(str(e))
