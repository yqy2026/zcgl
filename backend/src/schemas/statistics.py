from typing import Any

"""
统计和报表相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StatisticsRequest(BaseModel):
    """统计请求模型"""

    filters: dict[str, Any] | None = Field(
        None,
        description="筛选条件",
        json_schema_extra={
            "example": {
                "ownership_status": "已确权",
                "property_nature": "经营性",
                "ownership_entity": "国资集团",
            }
        },
    )

    model_config = ConfigDict(json_schema_extra={})


class BasicStatisticsResponse(BaseModel):
    """基础统计数据响应模型"""

    total_assets: int = Field(..., description="总资产数")
    ownership_status: dict[str, int] = Field(..., description="按确权状态统计")
    property_nature: dict[str, int] = Field(..., description="按物业性质统计")
    usage_status: dict[str, int] = Field(..., description="按使用状态统计")
    generated_at: datetime = Field(..., description="生成时间")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="应用的筛选条件"
    )

    model_config = ConfigDict(json_schema_extra={})


class DetailedStatisticsResponse(BaseModel):
    """详细统计数据响应模型"""

    summary: BasicStatisticsResponse = Field(..., description="基础统计摘要")
    area_analysis: dict[str, Any] = Field(..., description="面积分析")
    financial_analysis: dict[str, Any] = Field(..., description="财务分析")
    occupancy_analysis: dict[str, Any] = Field(..., description="出租率分析")
    contract_analysis: dict[str, Any] = Field(..., description="合同分析")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="应用的筛选条件"
    )

    model_config = ConfigDict(json_schema_extra={})


class TimeSeriesDataPoint(BaseModel):
    """时间序列数据点"""

    date: datetime = Field(..., description="日期")
    value: float = Field(..., description="数值")
    label: str | None = Field(None, description="标签")


class TimeSeriesStatisticsResponse(BaseModel):
    """时间序列统计数据响应模型"""

    metric_name: str = Field(..., description="指标名称")
    data_points: list[TimeSeriesDataPoint] = Field(..., description="数据点列表")
    period_start: datetime = Field(..., description="统计开始时间")
    period_end: datetime = Field(..., description="统计结束时间")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="应用的筛选条件"
    )


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

    total_assets: int = Field(..., description="总资产数量")
    total_annual_income: float = Field(..., description="年总收入")
    total_annual_expense: float = Field(..., description="年总支出")
    net_annual_income: float = Field(..., description="年净收入")
    income_per_sqm: float = Field(..., description="每平方米年收入")
    expense_per_sqm: float = Field(..., description="每平方米年支出")


class DashboardDataResponse(BaseModel):
    """仪表板数据响应模型"""

    basic_stats: BasicStatisticsResponse = Field(..., description="基础统计数据")
    area_summary: AreaSummaryResponse = Field(..., description="面积汇总")
    financial_summary: FinancialSummaryResponse = Field(..., description="财务汇总")
    occupancy_stats: OccupancyRateStatsResponse = Field(..., description="出租率统计")
    category_occupancy: list[CategoryOccupancyRateResponse] = Field(
        ..., description="分类出租率"
    )
    generated_at: datetime = Field(..., description="生成时间")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="应用的筛选条件"
    )


class ChartDataItem(BaseModel):
    """图表数据项"""

    name: str = Field(..., description="名称")
    value: float = Field(..., description="数值")
    percentage: float | None = Field(None, description="百分比")


class DistributionResponse(BaseModel):
    """分布数据响应模型"""

    total: int = Field(..., description="总数")
    categories: list[ChartDataItem] = Field(..., description="分类数据")
    chart_type: str = Field(default="pie", description="图表类型")


class TrendDataResponse(BaseModel):
    """趋势数据响应模型"""

    metric_name: str = Field(..., description="指标名称")
    time_series: list[TimeSeriesDataPoint] = Field(..., description="时间序列数据")
    trend_direction: str | None = Field(None, description="趋势方向")
    change_percentage: float | None = Field(None, description="变化百分比")
