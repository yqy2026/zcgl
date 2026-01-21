"""
租金统计模块
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ....core.exception_handler import BaseBusinessError, internal_error
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import (
    AssetRentStatistics,
    MonthlyRentStatistics,
    OwnershipRentStatistics,
    RentStatisticsQuery,
)
from ....services.rent_contract import rent_contract_service

router = APIRouter()


@router.get("/statistics/overview", summary="获取租金统计概览")
def get_rent_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    ownership_ids: list[str] | None = Query(None, description="权属方ID列表"),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
    contract_status: str | None = Query(None, description="合同状态"),
) -> Any:
    """
    获取租金统计概览信息
    """
    query_params = RentStatisticsQuery(
        start_date=start_date,
        end_date=end_date,
        ownership_ids=ownership_ids,
        asset_ids=asset_ids,
        contract_status=contract_status,
    )

    try:
        statistics = rent_contract_service.get_statistics(
            db=db, query_params=query_params
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取统计信息失败: {str(e)}")


@router.get(
    "/statistics/ownership",
    response_model=list[OwnershipRentStatistics],
    summary="权属方租金统计",
)
def get_ownership_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    ownership_ids: list[str] | None = Query(None, description="权属方ID列表"),
) -> Any:
    """
    按权属方统计租金情况
    """
    try:
        statistics = rent_contract_service.get_ownership_statistics(
            db=db, start_date=start_date, end_date=end_date, ownership_ids=ownership_ids
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取权属方统计失败: {str(e)}")


@router.get(
    "/statistics/asset",
    response_model=list[AssetRentStatistics],
    summary="资产租金统计",
)
def get_asset_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
) -> Any:
    """
    按资产统计租金情况
    """
    try:
        statistics = rent_contract_service.get_asset_statistics(
            db=db, start_date=start_date, end_date=end_date, asset_ids=asset_ids
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取资产统计失败: {str(e)}")


@router.get(
    "/statistics/monthly",
    response_model=list[MonthlyRentStatistics],
    summary="月度租金统计",
)
def get_monthly_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    year: int | None = Query(None, description="年份"),
    start_month: str | None = Query(None, description="开始月份(YYYY-MM)"),
    end_month: str | None = Query(None, description="结束月份(YYYY-MM)"),
) -> Any:
    """
    获取月度租金统计
    """
    try:
        statistics = rent_contract_service.get_monthly_statistics(
            db=db, year=year, start_month=start_month, end_month=end_month
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取月度统计失败: {str(e)}")


@router.get("/statistics/export", summary="导出统计数据")
def export_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    format: str = Query("excel", description="导出格式"),
) -> Any:
    """
    导出统计数据
    """
    try:
        from datetime import datetime

        from ..services.excel_export import export_statistics_report

        overview_stats = rent_contract_service.get_statistics(
            db=db,
            query_params=RentStatisticsQuery(
                start_date=start_date,
                end_date=end_date,
                ownership_ids=None,
                asset_ids=None,
                contract_status=None,
            ),
        )

        ownership_stats = rent_contract_service.get_ownership_statistics(
            db=db, start_date=start_date, end_date=end_date
        )

        asset_stats = rent_contract_service.get_asset_statistics(
            db=db, start_date=start_date, end_date=end_date
        )

        monthly_stats = rent_contract_service.get_monthly_statistics(db=db)

        excel_data = export_statistics_report(
            overview_data=overview_stats,
            ownership_data=ownership_stats,
            asset_data=asset_stats,
            monthly_data=monthly_stats,
            start_date=start_date,
            end_date=end_date,
        )

        filename = f"rent_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"导出统计数据失败: {str(e)}")
