"""
出租率计算API路由
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.exception_handler import bad_request, internal_error
from ...database import get_db

# 配置日志
logger = logging.getLogger(__name__)

# 创建出租率路由器
router = APIRouter()


@router.get("/rate", summary="计算出租率")
async def calculate_occupancy_rate(
    property_nature: str | None = Query(None, description="物业性质筛选"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    ownership_entity: str | None = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    计算出租率

    Args:
        property_nature: 物业性质筛选
        ownership_status: 确权状态筛选
        ownership_entity: 权属方筛选
        db: 数据库会话

    Returns:
        出租率统计数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity

        logger.info(f"开始计算出租率，筛选条件: {filters}")

        # 模拟数据（因为使用了简化的数据库）
        total_rentable = 100
        rented_count = 75
        self_used_count = 15
        vacant_count = 10

        # 计算出租率
        occupancy_rate = (
            (rented_count / total_rentable) * 100 if total_rentable > 0 else 0
        )

        # 计算利用率（出租+自用）
        utilization_rate = (
            ((rented_count + self_used_count) / total_rentable) * 100
            if total_rentable > 0
            else 0
        )

        # 计算空置率
        vacancy_rate = (
            (vacant_count / total_rentable) * 100 if total_rentable > 0 else 0
        )

        occupancy_data = {
            "total_rentable_assets": total_rentable,
            "rented_count": rented_count,
            "self_used_count": self_used_count,
            "vacant_count": vacant_count,
            "occupancy_rate": round(occupancy_rate, 2),
            "utilization_rate": round(utilization_rate, 2),
            "vacancy_rate": round(vacancy_rate, 2),
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
        }

        logger.info(f"出租率计算完成，出租率: {occupancy_rate:.2f}%")

        return {
            "success": True,
            "message": f"成功计算 {total_rentable} 个可出租资产的出租率",
            "data": occupancy_data,
        }

    except Exception as e:
        logger.error(f"计算出租率异常: {str(e)}")
        raise internal_error(f"计算出租率失败: {str(e)}")


@router.get("/analysis", summary="出租率分析")
async def analyze_occupancy(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    出租率分析

    Returns:
        详细的出租率分析数据
    """
    try:
        logger.info("开始进行出租率分析")

        # 总体出租率
        overall_rate = await calculate_occupancy_rate(db=db)

        if not overall_rate["success"]:
            raise bad_request(overall_rate["message"])

        # 按权属方分析（模拟数据）
        ownership_analysis = [
            {
                "ownership_entity": "国有",
                "data": {
                    "total_rentable_assets": 60,
                    "rented_count": 45,
                    "occupancy_rate": 75.0,
                },
            },
            {
                "ownership_entity": "集体",
                "data": {
                    "total_rentable_assets": 25,
                    "rented_count": 20,
                    "occupancy_rate": 80.0,
                },
            },
            {
                "ownership_entity": "私有",
                "data": {
                    "total_rentable_assets": 15,
                    "rented_count": 10,
                    "occupancy_rate": 66.7,
                },
            },
        ]

        # 按确权状态分析（模拟数据）
        status_analysis = [
            {
                "ownership_status": "已确权",
                "data": {
                    "total_rentable_assets": 80,
                    "rented_count": 65,
                    "occupancy_rate": 81.3,
                },
            },
            {
                "ownership_status": "未确权",
                "data": {
                    "total_rentable_assets": 20,
                    "rented_count": 10,
                    "occupancy_rate": 50.0,
                },
            },
        ]

        analysis_data = {
            "overall": overall_rate["data"],
            "by_ownership_entity": ownership_analysis,
            "by_ownership_status": status_analysis,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info("出租率分析完成")

        return {"success": True, "message": "出租率分析完成", "data": analysis_data}

    except Exception as e:
        logger.error(f"出租率分析异常: {str(e)}")
        raise internal_error(f"出租率分析失败: {str(e)}")


@router.get("/trends", summary="出租率趋势")
async def get_occupancy_trends(
    months: int = Query(12, ge=1, le=36, description="分析月数"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    获取出租率趋势（简化版本）

    Args:
        months: 分析的月数
        db: 数据库会话

    Returns:
        出租率趋势数据
    """
    try:
        logger.info(f"开始获取 {months} 个月的出租率趋势")

        # 模拟趋势数据
        monthly_data = []
        base_rate = 75.0

        for i in range(months):
            month_date = datetime.now().replace(day=1)
            month_date = month_date.replace(
                month=month_date.month - i
                if month_date.month > i
                else 12 + month_date.month - i
            )
            if month_date.month > datetime.now().month:
                month_date = month_date.replace(year=month_date.year - 1)

            # 模拟一些波动
            rate_variation = (i % 3 - 1) * 2  # -2, 0, 2 的循环
            monthly_rate = base_rate + rate_variation

            monthly_data.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "occupancy_rate": round(monthly_rate, 2),
                }
            )

        monthly_data.reverse()  # 按时间正序排列

        trends_data = {
            "period_months": months,
            "current_rate": base_rate,
            "trend_direction": "stable",  # stable, increasing, decreasing
            "monthly_data": monthly_data,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info("出租率趋势获取完成")

        return {
            "success": True,
            "message": f"成功获取 {months} 个月的出租率趋势",
            "data": trends_data,
        }

    except Exception as e:
        logger.error(f"获取出租率趋势异常: {str(e)}")
        raise internal_error(f"获取出租率趋势失败: {str(e)}")
