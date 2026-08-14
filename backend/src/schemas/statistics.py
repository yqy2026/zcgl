from typing import Any

"""
统计和报表相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StatisticsRequest(BaseModel):
    """统计请求模型"""

    filters: dict[str, Any] | None = Field(
        None,
        description="筛选条件",
        json_schema_extra={
            "example": {
                "ownership_status": "已确权",
                "property_nature": "经营性",
                "ownership_id": "ownership-uuid",
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
        default_factory=dict[str, Any], description="应用的筛选条件"
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
        default_factory=dict[str, Any], description="应用的筛选条件"
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
        default_factory=dict[str, Any], description="应用的筛选条件"
    )


class OccupancyRateStatsResponse(BaseModel):
    """出租率统计响应模型"""

    overall_occupancy_rate: float = Field(..., description="总体出租率")
    total_rentable_area: float = Field(..., description="总可租面积")
    total_rented_area: float = Field(..., description="总已租面积")
    calculated_at: datetime = Field(..., description="计算时间")


class CategoryOccupancyRateResponse(BaseModel):
    """分类出租率响应模型 - 单个分类"""

    category: str = Field(..., description="分类名称")
    occupancy_rate: float = Field(..., description="出租率")
    rentable_area: float = Field(..., description="可租面积")
    rented_area: float = Field(..., description="已租面积")
    asset_count: int = Field(..., description="资产数量")


class CategoryOccupancyRateListResponse(BaseModel):
    """分类出租率列表响应模型 - 包含多个分类"""

    category_field: str = Field(..., description="分类字段名")
    categories: list[CategoryOccupancyRateResponse] = Field(
        ..., description="各分类的出租率统计"
    )
    generated_at: datetime = Field(..., description="生成时间")


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
        default_factory=dict[str, Any], description="应用的筛选条件"
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


class ComprehensiveDistributionItem(BaseModel):
    """综合分析分布项公共字段。"""

    model_config = ConfigDict(extra="allow")

    count: int = Field(..., ge=0, description="资产数量")


class ComprehensiveCountDistributionItem(ComprehensiveDistributionItem):
    """综合分析数量分布项。"""

    percentage: float = Field(..., ge=0, le=100, description="数量占比")


class ComprehensiveAreaDistributionItem(ComprehensiveDistributionItem):
    """综合分析可出租面积分布项。"""

    total_area: float = Field(..., ge=0, description="可出租面积合计")
    area_percentage: float = Field(..., ge=0, le=100, description="可出租面积占比")
    average_area: float = Field(..., ge=0, description="平均可出租面积")


class ComprehensiveAnalyticsResponse(BaseModel):
    """综合分析服务契约；既有扩展指标保持透传。"""

    model_config = ConfigDict(extra="allow")

    property_nature_distribution: list[ComprehensiveCountDistributionItem]
    ownership_status_distribution: list[ComprehensiveCountDistributionItem]
    usage_status_distribution: list[ComprehensiveCountDistributionItem]
    business_category_distribution: list[ComprehensiveCountDistributionItem]
    property_nature_area_distribution: list[ComprehensiveAreaDistributionItem]
    ownership_status_area_distribution: list[ComprehensiveAreaDistributionItem]
    usage_status_area_distribution: list[ComprehensiveAreaDistributionItem]
    business_category_area_distribution: list[ComprehensiveAreaDistributionItem]

    @model_validator(mode="after")
    def validate_distribution_labels(self) -> "ComprehensiveAnalyticsResponse":
        label_fields = {
            "property_nature_distribution": "name",
            "ownership_status_distribution": "status",
            "usage_status_distribution": "status",
            "business_category_distribution": "category",
            "property_nature_area_distribution": "name",
            "ownership_status_area_distribution": "status",
            "usage_status_area_distribution": "status",
            "business_category_area_distribution": "category",
        }
        for field_name, label_name in label_fields.items():
            for item in getattr(self, field_name):
                label = item.model_extra.get(label_name) if item.model_extra else None
                if not isinstance(label, str) or label.strip() == "":
                    raise ValueError(f"{field_name} 缺少分类字段 {label_name}")
        return self


class TrendDataResponse(BaseModel):
    """趋势数据响应模型"""

    metric_name: str = Field(..., description="指标名称")
    time_series: list[TimeSeriesDataPoint] = Field(..., description="时间序列数据")
    trend_direction: str | None = Field(None, description="趋势方向")
    change_percentage: float | None = Field(None, description="变化百分比")
