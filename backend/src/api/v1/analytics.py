"""
资产分析API路由 (简化版)
Version: 2026-01-04 - Service层重构版

重构说明:
- 业务逻辑已迁移到 AnalyticsService
- API层只负责参数解析和服务调用
- 保持了原有的API签名和响应格式，确保向后兼容
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.response_handler import ResponseHandler, get_request_id
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...services.analytics.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/comprehensive", summary="获取综合统计分析数据")
async def get_comprehensive_analytics(
    request: Request,
    include_deleted: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    use_cache: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    try:
        # 构建筛选条件
        filters = {
            "include_deleted": include_deleted,
        }

        if date_from is not None:
            filters["date_from"] = date_from
        if date_to is not None:
            filters["date_to"] = date_to

        # 调用服务层
        service = AnalyticsService(db)
        result = service.get_comprehensive_analytics(
            filters=filters,
            use_cache=use_cache,
            current_user=current_user,
        )

        return ResponseHandler.success(
            data=result,
            message="统计分析数据获取成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"获取综合分析数据失败: {str(e)}")
        return ResponseHandler.error(
            message=f"获取分析数据失败: {str(e)}",
            request_id=get_request_id(request),
        )


@router.get("/cache/stats", summary="获取缓存统计信息")
async def get_cache_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    获取分析缓存的统计信息

    返回缓存命中率、键数量等信息
    """
    try:
        service = AnalyticsService(db)
        stats = service.get_cache_stats()

        return ResponseHandler.success(
            data=stats,
            message="缓存统计信息获取成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        return ResponseHandler.error(
            message=f"获取缓存统计失败: {str(e)}",
            request_id=get_request_id(request),
        )


@router.post("/cache/clear", summary="清除分析缓存")
async def clear_cache(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    清除所有分析相关的缓存

    权限要求: 需要登录
    """
    try:
        service = AnalyticsService(db)
        result = service.clear_cache()

        return ResponseHandler.success(
            data=result,
            message="缓存清除成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return ResponseHandler.error(
            message=f"清除缓存失败: {str(e)}",
            request_id=get_request_id(request),
        )


@router.get("/debug/cache", summary="调试缓存状态")
async def debug_cache_status(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    调试端点：获取详细的缓存状态

    仅在调试模式下可用
    """
    try:
        service = AnalyticsService(db)
        stats = service.get_cache_stats()

        # 添加调试信息
        debug_info = {
            **stats,
            "debug_mode": True,
            "request_path": str(request.url),
        }

        return ResponseHandler.success(
            data=debug_info,
            message="缓存调试信息获取成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"获取缓存调试信息失败: {str(e)}")
        return ResponseHandler.error(
            message=f"获取调试信息失败: {str(e)}",
            request_id=get_request_id(request),
        )


@router.get("/trend", summary="获取趋势数据")
async def get_trend_data(
    request: Request,
    trend_type: str = Query(..., description="趋势类型: occupancy, area, financial"),
    time_dimension: str = Query(
        "monthly", description="时间维度: daily, weekly, monthly, quarterly, yearly"
    ),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    获取指定类型的趋势数据

    Args:
        trend_type: 趋势类型 (occupancy, area, financial)
        time_dimension: 时间维度
        include_deleted: 是否包含已删除数据
    """
    try:
        filters = {"include_deleted": include_deleted}

        service = AnalyticsService(db)
        trend_data = service.calculate_trend(
            trend_type=trend_type,
            time_dimension=time_dimension,
            filters=filters,
        )

        return ResponseHandler.success(
            data={
                "trend_type": trend_type,
                "time_dimension": time_dimension,
                "data": trend_data,
            },
            message="趋势数据获取成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"获取趋势数据失败: {str(e)}")
        return ResponseHandler.error(
            message=f"获取趋势数据失败: {str(e)}",
            request_id=get_request_id(request),
        )


@router.get("/distribution", summary="获取分布数据")
async def get_distribution_data(
    request: Request,
    distribution_type: str = Query(
        ..., description="分布类型: property_nature, business_category, usage_status"
    ),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    获取指定类型的分布数据

    Args:
        distribution_type: 分布类型 (property_nature, business_category, usage_status)
        include_deleted: 是否包含已删除数据
    """
    try:
        filters = {"include_deleted": include_deleted}

        service = AnalyticsService(db)
        distribution = service.calculate_distribution(
            distribution_type=distribution_type,
            filters=filters,
        )

        return ResponseHandler.success(
            data=distribution,
            message="分布数据获取成功",
            request_id=get_request_id(request),
        )

    except Exception as e:
        logger.error(f"获取分布数据失败: {str(e)}")
        return ResponseHandler.error(
            message=f"获取分布数据失败: {str(e)}",
            request_id=get_request_id(request),
        )
