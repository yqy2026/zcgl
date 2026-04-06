"""
资产分析API路由 (简化版)

重构说明:
- 业务逻辑已迁移到 AnalyticsService
- API层只负责参数解析和服务调用
- 保持了原有的API签名和响应格式，确保向后兼容
"""

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError
from ....core.response_handler import ResponseHandler, get_request_id
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
from ....models.auth import User
from ....security.route_guards import debug_only, require_localhost
from ....services.analytics.analytics_export_service import AnalyticsExportService
from ....services.analytics.analytics_service import AnalyticsService
from ....services.party_scope import build_party_filter_from_scope_context

logger = logging.getLogger(__name__)

router = APIRouter()
_ANALYTICS_UPDATE_UNSCOPED_PARTY_ID = "__unscoped__:analytics:update"
_ANALYTICS_UPDATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
}


@router.get("/comprehensive", summary="获取综合统计分析数据")
async def get_comprehensive_analytics(
    request: Request,
    should_include_deleted: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    should_use_cache: bool = True,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> JSONResponse:
    """
    获取综合统计分析数据

    整合了多种统计维度:
    - 资产总数
    - 面积统计
    - 出租率统计
    - 财务数据
    - 分布数据

    权限要求: 需要登录
    """

    filters: dict[str, Any] = {
        "include_deleted": should_include_deleted,
    }

    if date_from is not None:
        filters["date_from"] = date_from
    if date_to is not None:
        filters["date_to"] = date_to

    try:
        service = AnalyticsService(db)
        result = await service.get_comprehensive_analytics(
            filters=filters,
            should_use_cache=should_use_cache,
            current_user=current_user,
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )

        success_response: JSONResponse = ResponseHandler.success(
            data=result,
            message="统计分析数据获取成功",
            request_id=get_request_id(request),
        )
        return success_response

    except Exception as e:
        logger.error(f"获取综合分析数据失败: {str(e)}", exc_info=True)
        try:
            fallback_service = AnalyticsService(db)
            fallback_result = await fallback_service.get_comprehensive_analytics(
                filters=filters,
                should_use_cache=False,
                current_user=current_user,
                party_filter=build_party_filter_from_scope_context(_scope_ctx),
            )
            return ResponseHandler.success(
                data=fallback_result,
                message="统计分析数据获取成功",
                request_id=get_request_id(request),
            )
        except Exception as fallback_error:
            logger.error(
                f"获取综合分析数据降级失败: {str(fallback_error)}",
                exc_info=True,
            )
            error_response: JSONResponse = ResponseHandler.error(
                message=f"获取分析数据失败: {str(e)}",
                request_id=get_request_id(request),
            )
            return error_response


@router.get("/cache/stats", summary="获取缓存统计信息")
async def get_cache_stats(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> JSONResponse:
    """
    获取分析缓存的统计信息

    返回缓存命中率、键数量等信息
    """

    try:
        service = AnalyticsService(db)
        stats = await service.get_cache_stats()

        success_response: JSONResponse = ResponseHandler.success(
            data=stats,
            message="缓存统计信息获取成功",
            request_id=get_request_id(request),
        )
        return success_response

    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        error_response: JSONResponse = ResponseHandler.error(
            message=f"获取缓存统计失败: {str(e)}",
            request_id=get_request_id(request),
        )
        return error_response


@router.post("/cache/clear", summary="清除分析缓存")
async def clear_cache(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="analytics",
            resource_context=_ANALYTICS_UPDATE_RESOURCE_CONTEXT,
        )
    ),
) -> JSONResponse:
    """
    清除所有分析相关的缓存

    权限要求: 需要登录
    """

    try:
        service = AnalyticsService(db)
        result = await service.clear_cache()

        success_response: JSONResponse = ResponseHandler.success(
            data=result,
            message="缓存清除成功",
            request_id=get_request_id(request),
        )
        return success_response

    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        error_response: JSONResponse = ResponseHandler.error(
            message=f"清除缓存失败: {str(e)}",
            request_id=get_request_id(request),
        )
        return error_response


@router.get(
    "/debug/cache",
    summary="调试缓存状态",
    dependencies=[Depends(require_localhost)],
)
@debug_only
async def debug_cache_status(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    调试端点：获取详细的缓存状态

    仅在调试模式下可用
    """

    try:
        service = AnalyticsService(db)
        stats = await service.get_cache_stats()

        debug_info = {
            **stats,
            "debug_mode": True,
            "request_path": str(request.url),
        }

        success_response: JSONResponse = ResponseHandler.success(
            data=debug_info,
            message="缓存调试信息获取成功",
            request_id=get_request_id(request),
        )
        return success_response

    except Exception as e:
        logger.error(f"获取缓存调试信息失败: {str(e)}")
        error_response: JSONResponse = ResponseHandler.error(
            message=f"获取调试信息失败: {str(e)}",
            request_id=get_request_id(request),
        )
        return error_response


@router.get("/trend", summary="获取趋势数据")
async def get_trend_data(
    request: Request,
    trend_type: str = Query(..., description="趋势类型: occupancy, area, financial"),
    time_dimension: str = Query(
        "monthly", description="时间维度: daily, weekly, monthly, quarterly, yearly"
    ),
    should_include_deleted: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> JSONResponse:
    """
    获取指定类型的趋势数据

    Args:
        trend_type: 趋势类型 (occupancy, area, financial)
        time_dimension: 时间维度
        should_include_deleted: 是否包含已删除数据
    """

    try:
        filters = {"include_deleted": should_include_deleted}

        service = AnalyticsService(db)
        trend_data = await service.calculate_trend(
            trend_type=trend_type,
            time_dimension=time_dimension,
            filters=filters,
        )

        success_response: JSONResponse = ResponseHandler.success(
            data={
                "trend_type": trend_type,
                "time_dimension": time_dimension,
                "data": trend_data,
            },
            message="趋势数据获取成功",
            request_id=get_request_id(request),
        )
        return success_response

    except Exception as e:
        logger.error(f"获取趋势数据失败: {str(e)}")
        error_response: JSONResponse = ResponseHandler.error(
            message=f"获取趋势数据失败: {str(e)}",
            request_id=get_request_id(request),
        )
        return error_response


@router.get("/distribution", summary="获取分布数据")
async def get_distribution_data(
    request: Request,
    distribution_type: str = Query(
        ..., description="分布类型: property_nature, business_category, usage_status"
    ),
    should_include_deleted: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> JSONResponse:
    """
    获取指定类型的分布数据

    Args:
        distribution_type: 分布类型 (property_nature, business_category, usage_status)
        should_include_deleted: 是否包含已删除数据
    """

    try:
        filters = {"include_deleted": should_include_deleted}

        service = AnalyticsService(db)
        distribution = await service.calculate_distribution(
            distribution_type=distribution_type,
            filters=filters,
        )

        success_response: JSONResponse = ResponseHandler.success(
            data=distribution,
            message="分布数据获取成功",
            request_id=get_request_id(request),
        )
        return success_response

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(f"获取分布数据失败: {str(e)}")
        error_response: JSONResponse = ResponseHandler.error(
            message=f"获取分布数据失败: {str(e)}",
            request_id=get_request_id(request),
        )
        return error_response


@router.post("/export", summary="导出分析数据")
async def export_analytics(
    request: Request,
    export_format: str = Query("excel", description="导出格式: excel, csv, pdf"),
    should_include_deleted: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> Any:
    """
    导出综合分析数据

    支持导出为 Excel、CSV 或 PDF 格式
    权限要求: 需要登录
    """

    try:
        filters: dict[str, Any] = {
            "include_deleted": should_include_deleted,
        }

        if date_from is not None:
            filters["date_from"] = date_from
        if date_to is not None:
            filters["date_to"] = date_to

        if export_format == "pdf":
            return ResponseHandler.error(
                message="PDF 导出功能尚未实现，请使用 Excel 或 CSV 格式",
                error_code="EXPORT_NOT_IMPLEMENTED",
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                request_id=get_request_id(request),
            )

        if export_format not in {"csv", "excel"}:
            return ResponseHandler.error(
                message=f"不支持的导出格式: {export_format}",
                error_code="INVALID_EXPORT_FORMAT",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=get_request_id(request),
            )

        service = AnalyticsService(db)
        result = await service.get_comprehensive_analytics(
            filters=filters,
            should_use_cache=False,
            current_user=current_user,
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        export_service = AnalyticsExportService()
        export_rows = export_service.build_export_rows(result)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == "csv":
            csv_content = export_service.render_csv(export_rows)

            async def csv_generator() -> AsyncIterator[bytes]:
                yield csv_content.encode("utf-8")

            return StreamingResponse(
                csv_generator(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics_{timestamp}.csv"
                },
            )

        if export_format == "excel":
            from ....services.excel import ExcelExportService

            excel_service = ExcelExportService(None)
            buffer = excel_service.export_analytics_to_excel(export_rows)

            async def excel_generator() -> AsyncIterator[bytes]:
                data = buffer.getvalue()
                yield data
                buffer.close()

            return StreamingResponse(
                excel_generator(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics_{timestamp}.xlsx"
                },
            )

    except Exception as e:
        logger.error(f"导出分析数据失败: {str(e)}")
        return ResponseHandler.error(
            message=f"导出失败: {str(e)}",
            request_id=get_request_id(request),
        )
