"""
统计和报表相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class StatisticsRequest(BaseModel):
    """统计请求模型"""

    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="筛选条件",
        example={
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "ownership_entity": "国资集团"
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filters": {
                    "ownership_status": "已确权",
                    "property_nature": "经营性",
                    "ownership_entity": "国资集团"
                }
            }
        }


class BasicStatisticsResponse(BaseModel):
    """基础统计数据响应模型"""

    total_assets: int = Field(..., description="总资产数")
    ownership_status: Dict[str, int] = Field(..., description="按确权状态统计")
    property_nature: Dict[str, int] = Field(..., description="按物业性质统计")
    usage_status: Dict[str, int] = Field(..., description="按使用状态统计")
    generated_at: datetime = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的筛选条件")

    class Config:
        json_schema_extra = {
            "example": {
                "total_assets": 100,
                "ownership_status": {
                    "confirmed": 80,
                    "unconfirmed": 15,
                    "partial": 5
                },
                "property_nature": {
                    "commercial": 70,
                    "non_commercial": 30
                },
                "usage_status": {
                    "rented": 60,
                    "available": 30,
                    "maintenance": 10
                },
                "generated_at": "2025-01-20T10:30:00",
                "filters_applied": {}
            }
        }


class DetailedStatisticsResponse(BaseModel):
    """详细统计数据响应模型"""

    summary: BasicStatisticsResponse = Field(..., description="基础统计摘要")
    area_analysis: Dict[str, Any] = Field(..., description="面积分析")
    financial_analysis: Dict[str, Any] = Field(..., description="财务分析")
    occupancy_analysis: Dict[str, Any] = Field(..., description="出租率分析")
    contract_analysis: Dict[str, Any] = Field(..., description="合同分析")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的筛选条件")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": {
                    "total_assets": 100,
                    "ownership_status": {"confirmed": 80, "unconfirmed": 15, "partial": 5},
                    "property_nature": {"commercial": 70, "non_commercial": 30},
                    "usage_status": {"rented": 60, "available": 30, "maintenance": 10},
                    "generated_at": "2025-01-20T10:30:00",
                    "filters_applied": {}
                },
                "area_analysis": {
                    "total_area": 10000.0,
                    "rentable_area": 8500.0,
                    "rented_area": 6800.0,
                    "occupancy_rate": 80.0
                },
                "financial_analysis": {
                    "total_annual_income": 1000000.0,
                    "total_annual_expense": 200000.0,
                    "net_income": 800000.0
                },
                "occupancy_analysis": {
                    "by_area": {"rented": 6800.0, "available": 1700.0},
                    "by_count": {"rented": 60, "available": 30}
                },
                "contract_analysis": {
                    "active_contracts": 60,
                    "expiring_soon": 5,
                    "expired": 2
                },
                "filters_applied": {}
            }
        }


class TimeSeriesDataPoint(BaseModel):
    """时间序列数据点"""

    date: datetime = Field(..., description="日期")
    value: float = Field(..., description="数值")
    label: Optional[str] = Field(None, description="标签")


class TimeSeriesStatisticsResponse(BaseModel):
    """时间序列统计数据响应模型"""

    metric_name: str = Field(..., description="指标名称")
    data_points: List[TimeSeriesDataPoint] = Field(..., description="数据点列表")
    period_start: datetime = Field(..., description="统计开始时间")
    period_end: datetime = Field(..., description="统计结束时间")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的筛选条件")


class OccupancyRateStatsResponse(BaseModel):
    """出租率统计响应模型"""
    overall_occupancy_rate: float = Field(..., description="总体出租率")
    total_rentable_area: float = Field(..., description="总可租面积")
    total_rented_area: float = Field(..., description="总已租面积")
    calculated_at: datetime = Field(..., description="计算时间")


class CategoryOccupancyRateResponse(BaseModel):
    """分类出租率响应模型"""
    category: str = Field(..., description="分类名称")
    occupancy_rate: float = Field(..., description="出租率")
    rentable_area: float = Field(..., description="可租面积")
    rented_area: float = Field(..., description="已租面积")
    asset_count: int = Field(..., description="资产数量")


class AreaSummaryResponse(BaseModel):
    """面积汇总响应模型"""
    total_area: float = Field(..., description="总面积")
    rentable_area: float = Field(..., description="可租面积")
    rented_area: float = Field(..., description="已租面积")
    unrented_area: float = Field(..., description="未租面积")
    occupancy_rate: float = Field(..., description="出租率")


class FinancialSummaryResponse(BaseModel):
    """财务汇总响应模型"""
    total_annual_income: float = Field(..., description="年总收入")
    total_annual_expense: float = Field(..., description="年总支出")
    net_annual_income: float = Field(..., description="年净收入")
    income_per_sqm: float = Field(..., description="每平方米年收入")
    expense_per_sqm: float = Field(..., description="每平方米年支出")