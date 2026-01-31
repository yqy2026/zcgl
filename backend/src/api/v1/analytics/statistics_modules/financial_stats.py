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

from src.crud.asset import asset_crud
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import FinancialSummaryResponse
from src.utils.cache_manager import cache_statistics
from src.constants.cache_constants import CACHE_TTL_MEDIUM_SECONDS
from src.utils.numeric import to_float

logger = logging.getLogger(__name__)

# 创建财务统计路由器
router = APIRouter()


@cache_statistics(expire=CACHE_TTL_MEDIUM_SECONDS)  # 30分钟缓存  # type: ignore[misc]
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

    assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,  # 获取所有资产
        filters=filters,
    )

    # 计算财务汇总
    summary = {
        "total_assets": len(assets),
        "total_annual_income": 0.0,
        "total_annual_expense": 0.0,
        "total_net_income": 0.0,
        "total_monthly_rent": 0.0,
        "total_deposit": 0.0,
        "total_rentable_area": 0.0,
        "assets_with_income_data": 0,
        "assets_with_rent_data": 0,
    }

    for asset in assets:
        # 累计可出租面积
        if getattr(asset, "rentable_area", None):
            summary["total_rentable_area"] += to_float(getattr(asset, "rentable_area"))

        # 累计年收入
        if getattr(asset, "annual_income", None):
            summary["total_annual_income"] += to_float(getattr(asset, "annual_income"))
            summary["assets_with_income_data"] += 1

        # 累计年支出
        if getattr(asset, "annual_expense", None):
            summary["total_annual_expense"] += to_float(
                getattr(asset, "annual_expense")
            )

        # 累计净收入
        if getattr(asset, "net_income", None):
            summary["total_net_income"] += to_float(getattr(asset, "net_income"))

        # 累计月租金
        if getattr(asset, "monthly_rent", None):
            summary["total_monthly_rent"] += to_float(getattr(asset, "monthly_rent"))
            summary["assets_with_rent_data"] += 1

        # 累计押金
        if getattr(asset, "deposit", None):
            summary["total_deposit"] += to_float(getattr(asset, "deposit"))

    # 格式化数据，保留2位小数
    for key in [
        "total_annual_income",
        "total_annual_expense",
        "total_net_income",
        "total_monthly_rent",
        "total_deposit",
        "total_rentable_area",
    ]:
        if summary[key] is not None:
            summary[key] = round(summary[key], 2)
        else:
            summary[key] = 0.0

    # 计算每平方米收入和支出
    total_rentable_area = summary.get("total_rentable_area", 0)
    income_per_sqm = (
        summary["total_annual_income"] / total_rentable_area
        if total_rentable_area > 0
        else 0.0
    )
    expense_per_sqm = (
        summary["total_annual_expense"] / total_rentable_area
        if total_rentable_area > 0
        else 0.0
    )

    return FinancialSummaryResponse(
        total_assets=int(summary["total_assets"]),
        total_annual_income=summary["total_annual_income"],
        total_annual_expense=summary["total_annual_expense"],
        net_annual_income=summary["total_net_income"],
        income_per_sqm=round(income_per_sqm, 2),
        expense_per_sqm=round(expense_per_sqm, 2),
    )
