"""
Financial summary calculation service.

Provides aggregated financial metrics for assets.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...utils.numeric import to_float

logger = logging.getLogger(__name__)


class FinancialService:
    """财务汇总计算服务"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_summary(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        计算财务汇总数据

        Args:
            filters: 资产筛选条件

        Returns:
            财务汇总统计结果
        """
        assets, _ = asset_crud.get_multi_with_search(
            db=self.db,
            skip=0,
            limit=10000,
            filters=filters,
        )

        total_assets = len(assets)
        total_rentable_area = 0.0
        total_annual_income = 0.0
        total_annual_expense = 0.0
        total_net_income = 0.0

        for asset in assets:
            if getattr(asset, "rentable_area", None):
                total_rentable_area += to_float(getattr(asset, "rentable_area"))

            if getattr(asset, "annual_income", None):
                total_annual_income += to_float(getattr(asset, "annual_income"))

            if getattr(asset, "annual_expense", None):
                total_annual_expense += to_float(getattr(asset, "annual_expense"))

            if getattr(asset, "net_income", None):
                total_net_income += to_float(getattr(asset, "net_income"))

        total_rentable_area = round(total_rentable_area, 2)
        total_annual_income = round(total_annual_income, 2)
        total_annual_expense = round(total_annual_expense, 2)
        total_net_income = round(total_net_income, 2)

        if total_rentable_area > 0:
            income_per_sqm = round(total_annual_income / total_rentable_area, 2)
            expense_per_sqm = round(total_annual_expense / total_rentable_area, 2)
        else:
            income_per_sqm = 0.0
            expense_per_sqm = 0.0

        return {
            "total_assets": total_assets,
            "total_annual_income": total_annual_income,
            "total_annual_expense": total_annual_expense,
            "net_annual_income": total_net_income,
            "income_per_sqm": income_per_sqm,
            "expense_per_sqm": expense_per_sqm,
        }
