"""
操作日志管理API路由
支持日志查询、统计、导出等功能
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import get_current_active_user, require_admin
from ....models.auth import User
from ....services.operation_log.service import (
    OperationLogService,
    get_operation_log_service,
)
from ..utils import handle_api_errors

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
    request_params: str | None = None
    request_body: str | None = None
    response_status: int | None = None
    response_time: int | None = None
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationLogListResponse(BaseModel):
    """操作日志列表响应"""

    items: list[OperationLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OperationLogStatisticsResponse(BaseModel):
    """操作日志统计响应"""

    success: bool
    data: dict[str, Any]
    message: str = "统计成功"


def _resolve_service(service: OperationLogService | Any) -> OperationLogService | Any:
    if isinstance(service, DependsParam):
        return get_operation_log_service()
    return service


# ==================== 日志查询端点 ====================


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OperationLogResponse]],
    summary="获取操作日志列表",
)
@handle_api_errors
async def get_operation_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str | None = Query(None, description="用户ID"),
    action: str | None = Query(None, description="操作类型"),
    module: str | None = Query(None, description="操作模块"),
    resource_type: str | None = Query(None, description="资源类型"),
    response_status: str | None = Query(None, description="响应状态筛选"),
    search: str | None = Query(None, description="搜索关键词"),
    start_date: str | None = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> JSONResponse:
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

    _ = current_user
    resolved_service = _resolve_service(service)
    logs, total = await resolved_service.get_operation_logs(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        module=module,
        resource_type=resource_type,
        response_status=response_status,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )

    return ResponseHandler.paginated(
        data=[OperationLogResponse.model_validate(log) for log in logs],
        page=page,
        page_size=page_size,
        total=total,
        message="获取操作日志列表成功",
    )


@router.get("/{log_id}", response_model=OperationLogResponse, summary="获取日志详情")
@handle_api_errors
async def get_operation_log(
    log_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> OperationLogResponse:
    """获取单条操作日志详情"""
    _ = current_user
    resolved_service = _resolve_service(service)
    log = await resolved_service.get_operation_log(db, log_id=log_id)
    return OperationLogResponse.model_validate(log)


# ==================== 统计端点 ====================


@router.get(
    "/statistics/user",
    response_model=OperationLogStatisticsResponse,
    summary="获取用户操作统计",
)
@handle_api_errors
async def get_user_operation_statistics(
    user_id: str = Query(..., description="用户ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> OperationLogStatisticsResponse:
    """获取指定用户的操作统计"""
    _ = current_user
    resolved_service = _resolve_service(service)
    stats = await resolved_service.get_user_operation_statistics(
        db,
        user_id=user_id,
        days=days,
    )

    return OperationLogStatisticsResponse(
        success=True,
        data=stats,
    )


@router.get(
    "/statistics/module",
    response_model=OperationLogStatisticsResponse,
    summary="获取模块操作统计",
)
@handle_api_errors
async def get_module_operation_statistics(
    module: str = Query(..., description="模块名称"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> OperationLogStatisticsResponse:
    """获取指定模块的操作统计"""
    _ = current_user
    resolved_service = _resolve_service(service)
    stats = await resolved_service.get_module_operation_statistics(
        db,
        module=module,
        days=days,
    )

    return OperationLogStatisticsResponse(
        success=True,
        data=stats,
    )


@router.get(
    "/statistics/daily",
    response_model=OperationLogStatisticsResponse,
    summary="获取每日操作统计",
)
@handle_api_errors
async def get_daily_operation_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> OperationLogStatisticsResponse:
    """获取每日操作统计"""
    _ = current_user
    resolved_service = _resolve_service(service)
    stats = await resolved_service.get_daily_operation_statistics(db, days=days)

    return OperationLogStatisticsResponse(
        success=True,
        data=stats,
    )


@router.get(
    "/statistics/errors",
    response_model=OperationLogStatisticsResponse,
    summary="获取错误操作统计",
)
@handle_api_errors
async def get_error_operation_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: OperationLogService = Depends(get_operation_log_service),
) -> OperationLogStatisticsResponse:
    """获取错误操作统计（仅管理员）"""
    _ = current_user
    resolved_service = _resolve_service(service)
    stats = await resolved_service.get_error_operation_statistics(db, days=days)

    return OperationLogStatisticsResponse(
        success=True,
        data=stats,
    )


@router.get(
    "/statistics/summary", response_model=dict[str, Any], summary="获取日志汇总统计"
)
@handle_api_errors
async def get_operation_log_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: OperationLogService = Depends(get_operation_log_service),
) -> dict[str, Any]:
    """获取操作日志汇总统计"""
    _ = current_user
    resolved_service = _resolve_service(service)
    summary = await resolved_service.get_operation_log_summary(db, days=days)

    return {
        "success": True,
        "data": summary,
    }


# ==================== 导出端点 ====================


@router.post("/export", summary="导出操作日志")
@handle_api_errors
async def export_operation_logs(
    filters: dict[str, Any] | None = None,
    format: str = Query("excel", description="导出格式: excel 或 csv"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: OperationLogService = Depends(get_operation_log_service),
) -> dict[str, Any]:
    """
    导出操作日志为Excel或CSV格式

    - **format**: excel 或 csv
    """

    _ = current_user
    resolved_filters = filters or {}
    resolved_service = _resolve_service(service)
    logs = await resolved_service.export_operation_logs(db=db, filters=resolved_filters)

    if format.lower() == "csv":
        return {
            "success": True,
            "message": f"已导出 {len(logs)} 条日志",
            "count": len(logs),
            "format": "csv",
        }
    return {
        "success": True,
        "message": f"已导出 {len(logs)} 条日志",
        "count": len(logs),
        "format": "excel",
    }


@router.post("/cleanup", summary="清理过期日志")
@handle_api_errors
async def cleanup_old_logs(
    days: int = Query(90, ge=1, le=365, description="保留天数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: OperationLogService = Depends(get_operation_log_service),
) -> dict[str, Any]:
    """
    删除指定天数前的日志（仅管理员）

    - **days**: 保留最近N天的日志，更早的日志将被删除
    """

    _ = current_user
    resolved_service = _resolve_service(service)
    deleted_count = await resolved_service.cleanup_old_logs(db=db, days=days)

    return {
        "success": True,
        "message": f"已删除 {deleted_count} 条过期日志",
        "deleted_count": deleted_count,
        "days": days,
    }
