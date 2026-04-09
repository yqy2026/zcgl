"""
趋势分析模块

提供趋势分析相关的统计端点:
- 指标趋势 (trend/{metric})

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
from src.models.auth import User
from src.schemas.statistics import TimeSeriesDataPoint, TrendDataResponse
from src.services.analytics.analytics_service import AnalyticsService
from src.services.party_scope import build_party_filter_from_scope_context

logger = logging.getLogger(__name__)

# 创建趋势分析路由器
router = APIRouter()


@router.get("/trend/{metric}", response_model=TrendDataResponse, summary="获取趋势数据")
async def get_trend_data(
    metric: str = Path(..., description="指标名称"),
    period: str = Query(
        "monthly", pattern="^(daily|weekly|monthly|yearly)$", description="时间周期"
    ),
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
) -> TrendDataResponse:
    """
    获取指标趋势数据

    支持多种指标的历史趋势分析，包括占用率、收入、支出等。
    Args:
        metric: 指标名称 (occupancy_rate, income, expense)
        period: 时间周期 (daily, weekly, monthly, yearly)
        db: 数据库会话
        current_user: 当前用户

    Returns:
        趋势数据，包括时间序列和趋势方向

    Note:
        当前实现返回模拟数据，实际项目中应从历史数据表中查询真实趋势
    """

    trend_alias = {
        "occupancy_rate": "occupancy",
        "income": "financial",
    }.get(metric, metric)
    trend_rows = await AnalyticsService(db).calculate_trend(
        trend_type=trend_alias,
        time_dimension=period,
        filters={},
        party_filter=build_party_filter_from_scope_context(_scope_ctx),
    )
    time_series = [
        TimeSeriesDataPoint(
            date=datetime.strptime(str(item.get("period")), "%Y-%m"),
            value=float(
                item.get("occupancy_rate")
                or item.get("total_land_area")
                or item.get("value")
                or 0
            ),
            label=str(item.get("period")),
        )
        for item in trend_rows
    ]

    return TrendDataResponse(
        metric_name=metric,
        time_series=time_series,
        trend_direction="up" if metric == "income" else "stable",
        change_percentage=5.0 if metric == "income" else None,
    )
