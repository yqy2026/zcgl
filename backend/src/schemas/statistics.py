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
            "property_nature": "经营类",
            "ownership_entity": "国资集团"
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "filters": {
                    "ownership_status": "已确权",
                    "property_nature": "经营类",
                    "ownership_entity": "国资集团"
                }
            }
        }


class StatisticsResponse(BaseModel):
    """统计响应模型"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "成功获取统计数据",
                "data": {
                    "total_count": 100,
                    "total_area": 50000.0,
                    "avg_area": 500.0,
                    "generated_at": "2024-01-01T12:00:00"
                }
            }
        }


class BasicStatistics(BaseModel):
    """基础统计数据模型"""
    
    total_count: int = Field(..., description="资产总数")
    total_area: float = Field(..., description="总面积（平方米）")
    avg_area: float = Field(..., description="平均面积（平方米）")
    total_rentable_area: float = Field(..., description="总可出租面积（平方米）")
    total_rented_area: float = Field(..., description="总已出租面积（平方米）")
    total_unrented_area: float = Field(..., description="总未出租面积（平方米）")
    overall_occupancy_rate: float = Field(..., description="整体出租率（%）")
    generated_at: str = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")
    data_count: int = Field(..., description="数据条数")


class DistributionItem(BaseModel):
    """分布项模型"""
    
    name: str = Field(..., description="项目名称")
    count: int = Field(..., description="数量")
    percentage: float = Field(..., description="百分比")
    total_area: Optional[float] = Field(None, description="总面积")
    area_percentage: Optional[float] = Field(None, description="面积百分比")


class DistributionAnalysis(BaseModel):
    """分布分析模型"""
    
    distribution: Dict[str, Dict[str, Any]] = Field(..., description="分布详情")
    chart_data: List[DistributionItem] = Field(..., description="图表数据")
    generated_at: str = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")
    data_count: int = Field(..., description="数据条数")


class OccupancyAnalysis(BaseModel):
    """出租率分析模型"""
    
    overall_occupancy: float = Field(..., description="整体出租率（%）")
    by_property_nature: Dict[str, Dict[str, Any]] = Field(..., description="按物业性质分析")
    by_ownership_entity: Dict[str, Dict[str, Any]] = Field(..., description="按权属方分析")
    occupancy_ranges: Dict[str, int] = Field(..., description="出租率区间分布")
    chart_data: List[Dict[str, Any]] = Field(..., description="图表数据")
    generated_at: str = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")
    data_count: int = Field(..., description="数据条数")


class AreaDistribution(BaseModel):
    """面积分布模型"""
    
    area_ranges: Dict[str, Dict[str, Any]] = Field(..., description="面积区间分布")
    chart_data: List[Dict[str, Any]] = Field(..., description="图表数据")
    statistics: Dict[str, float] = Field(..., description="面积统计")
    generated_at: str = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")
    data_count: int = Field(..., description="数据条数")


class KeyMetrics(BaseModel):
    """关键指标模型"""
    
    total_assets: int = Field(..., description="资产总数")
    total_area: float = Field(..., description="总面积")
    total_rentable_area: float = Field(..., description="总可出租面积")
    overall_occupancy_rate: float = Field(..., description="整体出租率")
    total_rented_area: float = Field(..., description="总已出租面积")
    total_unrented_area: float = Field(..., description="总未出租面积")


class ChartData(BaseModel):
    """图表数据模型"""
    
    ownership_distribution: List[Dict[str, Any]] = Field(..., description="确权状态分布")
    property_nature_distribution: List[Dict[str, Any]] = Field(..., description="物业性质分布")
    usage_status_distribution: List[Dict[str, Any]] = Field(..., description="使用状态分布")
    occupancy_ranges: List[Dict[str, Any]] = Field(..., description="出租率区间分布")


class DashboardData(BaseModel):
    """仪表板数据模型"""
    
    key_metrics: KeyMetrics = Field(..., description="关键指标")
    charts: ChartData = Field(..., description="图表数据")
    generated_at: str = Field(..., description="生成时间")
    data_count: int = Field(..., description="数据条数")


class DashboardResponse(BaseModel):
    """仪表板响应模型"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[DashboardData] = Field(None, description="仪表板数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "成功生成仪表板数据",
                "data": {
                    "key_metrics": {
                        "total_assets": 100,
                        "total_area": 50000.0,
                        "total_rentable_area": 40000.0,
                        "overall_occupancy_rate": 75.5,
                        "total_rented_area": 30200.0,
                        "total_unrented_area": 9800.0
                    },
                    "charts": {
                        "ownership_distribution": [
                            {"name": "已确权", "value": 80, "percentage": 80.0},
                            {"name": "未确权", "value": 20, "percentage": 20.0}
                        ]
                    },
                    "generated_at": "2024-01-01T12:00:00",
                    "data_count": 100
                }
            }
        }


class ComprehensiveReport(BaseModel):
    """综合报表模型"""
    
    basic_statistics: Dict[str, Any] = Field(..., description="基础统计")
    ownership_distribution: Dict[str, Any] = Field(..., description="确权状态分布")
    property_nature_distribution: Dict[str, Any] = Field(..., description="物业性质分布")
    usage_status_distribution: Dict[str, Any] = Field(..., description="使用状态分布")
    ownership_entity_distribution: Dict[str, Any] = Field(..., description="权属方分布")
    area_distribution: Dict[str, Any] = Field(..., description="面积分布")
    occupancy_analysis: Dict[str, Any] = Field(..., description="出租率分析")
    generated_at: str = Field(..., description="生成时间")
    filters_applied: Dict[str, Any] = Field(..., description="应用的筛选条件")
    data_count: int = Field(..., description="数据条数")


class ReportResponse(BaseModel):
    """报表响应模型"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[ComprehensiveReport] = Field(None, description="综合报表数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "成功生成综合报表",
                "data": {
                    "basic_statistics": {
                        "total_count": 100,
                        "total_area": 50000.0,
                        "avg_area": 500.0,
                        "overall_occupancy_rate": 75.5
                    },
                    "ownership_distribution": {
                        "distribution": {
                            "已确权": {"count": 80, "percentage": 80.0},
                            "未确权": {"count": 20, "percentage": 20.0}
                        }
                    },
                    "generated_at": "2024-01-01T12:00:00",
                    "data_count": 100
                }
            }
        }


# 导出的筛选条件模型
class StatisticsFilters(BaseModel):
    """统计筛选条件模型"""
    
    ownership_status: Optional[str] = Field(None, description="确权状态")
    property_nature: Optional[str] = Field(None, description="物业性质")
    usage_status: Optional[str] = Field(None, description="使用状态")
    ownership_entity: Optional[str] = Field(None, description="权属方")
    search: Optional[str] = Field(None, description="搜索关键词")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ownership_status": "已确权",
                "property_nature": "经营类",
                "usage_status": "出租",
                "ownership_entity": "国资集团",
                "search": "办公楼"
            }
        }


# 统计图表数据点模型
class ChartDataPoint(BaseModel):
    """图表数据点模型"""
    
    name: str = Field(..., description="数据点名称")
    value: float = Field(..., description="数值")
    percentage: Optional[float] = Field(None, description="百分比")
    count: Optional[int] = Field(None, description="数量")
    area: Optional[float] = Field(None, description="面积")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "已确权",
                "value": 80,
                "percentage": 80.0,
                "count": 80,
                "area": 40000.0
            }
        }


# 统计趋势数据模型
class TrendData(BaseModel):
    """趋势数据模型"""
    
    period: str = Field(..., description="时间周期")
    value: float = Field(..., description="数值")
    change: Optional[float] = Field(None, description="变化量")
    change_percentage: Optional[float] = Field(None, description="变化百分比")
    
    class Config:
        json_schema_extra = {
            "example": {
                "period": "2024-01",
                "value": 75.5,
                "change": 2.3,
                "change_percentage": 3.14
            }
        }