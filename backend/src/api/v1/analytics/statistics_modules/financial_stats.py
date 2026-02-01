"""
财务统计模块

提供财务相关的统计端点:
- 财务汇总 (financial-summary)

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.constants.cache_constants import CACHE_TTL_MEDIUM_SECONDS
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import FinancialSummaryResponse
from src.services.analytics import FinancialService
from src.utils.cache_manager import cache_statistics

logger = logging.getLogger(__name__)

# 创建财务统计路由器
router = APIRouter()


@cache_statistics(expire=CACHE_TTL_MEDIUM_SECONDS)  # 30分钟缓存
@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    should_include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinancialSummaryResponse:
    """
    获取财务汇总统计
    计算所有资产的财务汇总数据，包括：
    - 总年收入
    - 总年支出
    - 净年收入
    - 每平方米收入/支出

    Args:
        include_deleted: 是否包含已删除的资产
        db: 数据库会话
    Returns:
        财务汇总统计信息
    """
    # 获取所有资产
    filters: dict[str, Any] = {}
    if not should_include_deleted:
        filters["data_status"] = "正常"

    service = FinancialService(db)
    summary = service.calculate_summary(filters)

    return FinancialSummaryResponse(
        total_assets=int(summary["total_assets"]),
        total_annual_income=summary["total_annual_income"],
        total_annual_expense=summary["total_annual_expense"],
        net_annual_income=summary["net_annual_income"],
        income_per_sqm=summary["income_per_sqm"],
        expense_per_sqm=summary["expense_per_sqm"],
    )
