"""
数据统计和报表服务
使用Polars进行高性能数据分析和统计
"""

import polars as pl
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from src.models.asset import Asset
from src.crud.asset import CRUDAsset
from src.database import get_db

logger = logging.getLogger(__name__)


class StatisticsError(Exception):
    """统计分析异常"""
    pass


class AssetStatisticsAnalyzer:
    """资产数据统计分析器"""
    
    @staticmethod
    def calculate_basic_statistics(assets: List[Asset]) -> Dict[str, Any]:
        """计算基础统计信息"""
        try:
            if not assets:
                return {
                    "total_count": 0,
                    "total_area": 0.0,
                    "avg_area": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "overall_occupancy_rate": 0.0
                }
            
            # 转换为DataFrame进行分析
            data = []
            for asset in assets:
                data.append({
                    "actual_property_area": asset.actual_property_area or 0.0,
                    "rentable_area": asset.rentable_area or 0.0,
                    "rented_area": asset.rented_area or 0.0,
                    "unrented_area": asset.unrented_area or 0.0,
                    "non_commercial_area": asset.non_commercial_area or 0.0
                })
            
            df = pl.DataFrame(data)
            
            # 计算统计指标
            stats = df.select([
                pl.len().alias("total_count"),
                pl.col("actual_property_area").sum().alias("total_area"),
                pl.col("actual_property_area").mean().alias("avg_area"),
                pl.col("rentable_area").sum().alias("total_rentable_area"),
                pl.col("rented_area").sum().alias("total_rented_area"),
                pl.col("unrented_area").sum().alias("total_unrented_area"),
                pl.col("non_commercial_area").sum().alias("total_non_commercial_area")
            ]).to_dicts()[0]
            
            # 计算整体出租率
            total_rentable = stats["total_rentable_area"] or 0.0
            total_rented = stats["total_rented_area"] or 0.0
            overall_occupancy_rate = (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            
            stats["overall_occupancy_rate"] = round(overall_occupancy_rate, 2)
            
            # 格式化数值
            for key in ["total_area", "avg_area", "total_rentable_area", "total_rented_area", "total_unrented_area", "total_non_commercial_area"]:
                if stats[key] is not None:
                    stats[key] = round(stats[key], 2)
                else:
                    stats[key] = 0.0
            
            logger.info(f"计算基础统计完成，共 {stats['total_count']} 条资产")
            return stats
            
        except Exception as e:
            logger.error(f"计算基础统计失败: {str(e)}")
            raise StatisticsError(f"计算基础统计失败: {str(e)}")
    
    @staticmethod
    def analyze_ownership_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """分析权属分布"""
        try:
            if not assets:
                return {"distribution": {}, "chart_data": []}
            
            # 统计确权状态分布
            ownership_counts = {}
            for asset in assets:
                status = asset.ownership_status or "未知"
                ownership_counts[status] = ownership_counts.get(status, 0) + 1
            
            # 计算百分比
            total = len(assets)
            distribution = {}
            chart_data = []
            
            for status, count in ownership_counts.items():
                percentage = round(count / total * 100, 2)
                distribution[status] = {
                    "count": count,
                    "percentage": percentage
                }
                chart_data.append({
                    "name": status,
                    "value": count,
                    "percentage": percentage
                })
            
            logger.info(f"权属分布分析完成，{len(distribution)} 种状态")
            return {
                "distribution": distribution,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"权属分布分析失败: {str(e)}")
            raise StatisticsError(f"权属分布分析失败: {str(e)}")
    
    @staticmethod
    def analyze_property_nature_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """分析物业性质分布"""
        try:
            if not assets:
                return {"distribution": {}, "chart_data": []}
            
            # 统计物业性质分布
            nature_counts = {}
            nature_areas = {}
            
            for asset in assets:
                nature = asset.property_nature or "未知"
                area = asset.actual_property_area or 0.0
                
                nature_counts[nature] = nature_counts.get(nature, 0) + 1
                nature_areas[nature] = nature_areas.get(nature, 0.0) + area
            
            # 计算统计信息
            total_count = len(assets)
            total_area = sum(nature_areas.values())
            
            distribution = {}
            chart_data = []
            
            for nature in nature_counts.keys():
                count = nature_counts[nature]
                area = nature_areas[nature]
                count_percentage = round(count / total_count * 100, 2)
                area_percentage = round(area / total_area * 100, 2) if total_area > 0 else 0.0
                
                distribution[nature] = {
                    "count": count,
                    "count_percentage": count_percentage,
                    "total_area": round(area, 2),
                    "area_percentage": area_percentage,
                    "avg_area": round(area / count, 2) if count > 0 else 0.0
                }
                
                chart_data.append({
                    "name": nature,
                    "count": count,
                    "area": round(area, 2),
                    "count_percentage": count_percentage,
                    "area_percentage": area_percentage
                })
            
            logger.info(f"物业性质分布分析完成，{len(distribution)} 种性质")
            return {
                "distribution": distribution,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"物业性质分布分析失败: {str(e)}")
            raise StatisticsError(f"物业性质分布分析失败: {str(e)}")
    
    @staticmethod
    def analyze_usage_status_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """分析使用状态分布"""
        try:
            if not assets:
                return {"distribution": {}, "chart_data": []}
            
            # 统计使用状态分布
            status_counts = {}
            status_areas = {}
            
            for asset in assets:
                status = asset.usage_status or "未知"
                area = asset.actual_property_area or 0.0
                
                status_counts[status] = status_counts.get(status, 0) + 1
                status_areas[status] = status_areas.get(status, 0.0) + area
            
            # 计算统计信息
            total_count = len(assets)
            total_area = sum(status_areas.values())
            
            distribution = {}
            chart_data = []
            
            for status in status_counts.keys():
                count = status_counts[status]
                area = status_areas[status]
                count_percentage = round(count / total_count * 100, 2)
                area_percentage = round(area / total_area * 100, 2) if total_area > 0 else 0.0
                
                distribution[status] = {
                    "count": count,
                    "count_percentage": count_percentage,
                    "total_area": round(area, 2),
                    "area_percentage": area_percentage,
                    "avg_area": round(area / count, 2) if count > 0 else 0.0
                }
                
                chart_data.append({
                    "name": status,
                    "count": count,
                    "area": round(area, 2),
                    "count_percentage": count_percentage,
                    "area_percentage": area_percentage
                })
            
            logger.info(f"使用状态分布分析完成，{len(distribution)} 种状态")
            return {
                "distribution": distribution,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"使用状态分布分析失败: {str(e)}")
            raise StatisticsError(f"使用状态分布分析失败: {str(e)}")
    
    @staticmethod
    def analyze_ownership_entity_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """分析权属方分布"""
        try:
            if not assets:
                return {"distribution": {}, "chart_data": []}
            
            # 统计权属方分布
            entity_counts = {}
            entity_areas = {}
            
            for asset in assets:
                entity = asset.ownership_entity or "未知"
                area = asset.actual_property_area or 0.0
                
                entity_counts[entity] = entity_counts.get(entity, 0) + 1
                entity_areas[entity] = entity_areas.get(entity, 0.0) + area
            
            # 计算统计信息
            total_count = len(assets)
            total_area = sum(entity_areas.values())
            
            distribution = {}
            chart_data = []
            
            for entity in entity_counts.keys():
                count = entity_counts[entity]
                area = entity_areas[entity]
                count_percentage = round(count / total_count * 100, 2)
                area_percentage = round(area / total_area * 100, 2) if total_area > 0 else 0.0
                
                distribution[entity] = {
                    "count": count,
                    "count_percentage": count_percentage,
                    "total_area": round(area, 2),
                    "area_percentage": area_percentage,
                    "avg_area": round(area / count, 2) if count > 0 else 0.0
                }
                
                chart_data.append({
                    "name": entity,
                    "count": count,
                    "area": round(area, 2),
                    "count_percentage": count_percentage,
                    "area_percentage": area_percentage
                })
            
            # 按面积排序
            chart_data.sort(key=lambda x: x["area"], reverse=True)
            
            logger.info(f"权属方分布分析完成，{len(distribution)} 个权属方")
            return {
                "distribution": distribution,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"权属方分布分析失败: {str(e)}")
            raise StatisticsError(f"权属方分布分析失败: {str(e)}")
    
    @staticmethod
    def analyze_area_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """分析面积分布"""
        try:
            if not assets:
                return {
                    "area_ranges": {},
                    "chart_data": [],
                    "statistics": {}
                }
            
            # 提取面积数据
            areas = [asset.actual_property_area or 0.0 for asset in assets if asset.actual_property_area]
            
            if not areas:
                return {
                    "area_ranges": {},
                    "chart_data": [],
                    "statistics": {}
                }
            
            df = pl.DataFrame({"area": areas})
            
            # 计算面积统计
            area_stats = df.select([
                pl.col("area").min().alias("min_area"),
                pl.col("area").max().alias("max_area"),
                pl.col("area").mean().alias("avg_area"),
                pl.col("area").median().alias("median_area"),
                pl.col("area").std().alias("std_area"),
                pl.col("area").sum().alias("total_area")
            ]).to_dicts()[0]
            
            # 定义面积区间
            ranges = [
                (0, 500, "小型（0-500㎡）"),
                (500, 1000, "中小型（500-1000㎡）"),
                (1000, 2000, "中型（1000-2000㎡）"),
                (2000, 5000, "大型（2000-5000㎡）"),
                (5000, float('inf'), "超大型（5000㎡以上）")
            ]
            
            # 统计各区间分布
            area_ranges = {}
            chart_data = []
            
            for min_area, max_area, label in ranges:
                if max_area == float('inf'):
                    count = len([a for a in areas if a >= min_area])
                    total_area = sum([a for a in areas if a >= min_area])
                else:
                    count = len([a for a in areas if min_area <= a < max_area])
                    total_area = sum([a for a in areas if min_area <= a < max_area])
                
                if count > 0:
                    percentage = round(count / len(areas) * 100, 2)
                    area_percentage = round(total_area / sum(areas) * 100, 2)
                    avg_area = round(total_area / count, 2)
                    
                    area_ranges[label] = {
                        "count": count,
                        "percentage": percentage,
                        "total_area": round(total_area, 2),
                        "area_percentage": area_percentage,
                        "avg_area": avg_area
                    }
                    
                    chart_data.append({
                        "name": label,
                        "count": count,
                        "percentage": percentage,
                        "total_area": round(total_area, 2),
                        "area_percentage": area_percentage
                    })
            
            # 格式化统计数据
            statistics = {
                "min_area": round(area_stats["min_area"], 2),
                "max_area": round(area_stats["max_area"], 2),
                "avg_area": round(area_stats["avg_area"], 2),
                "median_area": round(area_stats["median_area"], 2),
                "std_area": round(area_stats["std_area"], 2),
                "total_area": round(area_stats["total_area"], 2),
                "total_count": len(areas)
            }
            
            logger.info(f"面积分布分析完成，{len(chart_data)} 个区间")
            return {
                "area_ranges": area_ranges,
                "chart_data": chart_data,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"面积分布分析失败: {str(e)}")
            raise StatisticsError(f"面积分布分析失败: {str(e)}")
    
    @staticmethod
    def generate_occupancy_analysis(assets: List[Asset]) -> Dict[str, Any]:
        """生成出租率分析"""
        try:
            if not assets:
                return {
                    "overall_occupancy": 0.0,
                    "by_property_nature": {},
                    "by_ownership_entity": {},
                    "occupancy_ranges": {},
                    "chart_data": []
                }
            
            # 计算整体出租率
            total_rentable = sum([asset.rentable_area or 0.0 for asset in assets])
            total_rented = sum([asset.rented_area or 0.0 for asset in assets])
            overall_occupancy = (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            
            # 按物业性质分析出租率
            by_nature = {}
            nature_groups = {}
            for asset in assets:
                nature = asset.property_nature or "未知"
                if nature not in nature_groups:
                    nature_groups[nature] = []
                nature_groups[nature].append(asset)
            
            for nature, group_assets in nature_groups.items():
                group_rentable = sum([asset.rentable_area or 0.0 for asset in group_assets])
                group_rented = sum([asset.rented_area or 0.0 for asset in group_assets])
                occupancy = (group_rented / group_rentable * 100) if group_rentable > 0 else 0.0
                
                by_nature[nature] = {
                    "count": len(group_assets),
                    "total_rentable_area": round(group_rentable, 2),
                    "total_rented_area": round(group_rented, 2),
                    "occupancy_rate": round(occupancy, 2)
                }
            
            # 按权属方分析出租率
            by_entity = {}
            entity_groups = {}
            for asset in assets:
                entity = asset.ownership_entity or "未知"
                if entity not in entity_groups:
                    entity_groups[entity] = []
                entity_groups[entity].append(asset)
            
            for entity, group_assets in entity_groups.items():
                group_rentable = sum([asset.rentable_area or 0.0 for asset in group_assets])
                group_rented = sum([asset.rented_area or 0.0 for asset in group_assets])
                occupancy = (group_rented / group_rentable * 100) if group_rentable > 0 else 0.0
                
                by_entity[entity] = {
                    "count": len(group_assets),
                    "total_rentable_area": round(group_rentable, 2),
                    "total_rented_area": round(group_rented, 2),
                    "occupancy_rate": round(occupancy, 2)
                }
            
            # 出租率区间分析
            occupancy_ranges = {
                "高出租率（80%以上）": 0,
                "中等出租率（50%-80%）": 0,
                "低出租率（20%-50%）": 0,
                "极低出租率（20%以下）": 0,
                "未出租（0%）": 0
            }
            
            for asset in assets:
                rentable = asset.rentable_area or 0.0
                rented = asset.rented_area or 0.0
                if rentable > 0:
                    occupancy = rented / rentable * 100
                    if occupancy >= 80:
                        occupancy_ranges["高出租率（80%以上）"] += 1
                    elif occupancy >= 50:
                        occupancy_ranges["中等出租率（50%-80%）"] += 1
                    elif occupancy >= 20:
                        occupancy_ranges["低出租率（20%-50%）"] += 1
                    elif occupancy > 0:
                        occupancy_ranges["极低出租率（20%以下）"] += 1
                    else:
                        occupancy_ranges["未出租（0%）"] += 1
                else:
                    occupancy_ranges["未出租（0%）"] += 1
            
            # 生成图表数据
            chart_data = []
            for range_name, count in occupancy_ranges.items():
                if count > 0:
                    percentage = round(count / len(assets) * 100, 2)
                    chart_data.append({
                        "name": range_name,
                        "count": count,
                        "percentage": percentage
                    })
            
            logger.info(f"出租率分析完成，整体出租率 {overall_occupancy:.2f}%")
            return {
                "overall_occupancy": round(overall_occupancy, 2),
                "by_property_nature": by_nature,
                "by_ownership_entity": by_entity,
                "occupancy_ranges": occupancy_ranges,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"出租率分析失败: {str(e)}")
            raise StatisticsError(f"出租率分析失败: {str(e)}")


class ReportService:
    """报表服务"""
    
    def __init__(self):
        self.analyzer = AssetStatisticsAnalyzer()
        self.asset_crud = CRUDAsset(Asset)
    
    def generate_comprehensive_report(
        self,
        filters: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """生成综合报表"""
        try:
            if db is None:
                db = next(get_db())
            
            # 获取资产数据
            assets = self._get_filtered_assets(filters, db)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有找到符合条件的资产数据",
                    "data": None
                }
            
            # 生成各种分析
            basic_stats = self.analyzer.calculate_basic_statistics(assets)
            ownership_dist = self.analyzer.analyze_ownership_distribution(assets)
            nature_dist = self.analyzer.analyze_property_nature_distribution(assets)
            usage_dist = self.analyzer.analyze_usage_status_distribution(assets)
            entity_dist = self.analyzer.analyze_ownership_entity_distribution(assets)
            area_dist = self.analyzer.analyze_area_distribution(assets)
            occupancy_analysis = self.analyzer.generate_occupancy_analysis(assets)
            
            # 组装报表数据
            report_data = {
                "basic_statistics": basic_stats,
                "ownership_distribution": ownership_dist,
                "property_nature_distribution": nature_dist,
                "usage_status_distribution": usage_dist,
                "ownership_entity_distribution": entity_dist,
                "area_distribution": area_dist,
                "occupancy_analysis": occupancy_analysis,
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters or {},
                "data_count": len(assets)
            }
            
            logger.info(f"综合报表生成完成，包含 {len(assets)} 条资产数据")
            return {
                "success": True,
                "message": f"成功生成包含 {len(assets)} 条资产的综合报表",
                "data": report_data
            }
            
        except Exception as e:
            logger.error(f"生成综合报表失败: {str(e)}")
            return {
                "success": False,
                "message": f"生成报表失败: {str(e)}",
                "data": None
            }
    
    def generate_dashboard_data(
        self,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """生成仪表板数据"""
        try:
            if db is None:
                db = next(get_db())
            
            # 获取所有资产数据
            assets = self.asset_crud.get_multi(db, limit=10000)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有资产数据",
                    "data": None
                }
            
            # 生成关键指标
            basic_stats = self.analyzer.calculate_basic_statistics(assets)
            occupancy_analysis = self.analyzer.generate_occupancy_analysis(assets)
            
            # 生成简化的分布数据（用于图表）
            ownership_chart = self.analyzer.analyze_ownership_distribution(assets)["chart_data"]
            nature_chart = self.analyzer.analyze_property_nature_distribution(assets)["chart_data"]
            usage_chart = self.analyzer.analyze_usage_status_distribution(assets)["chart_data"]
            
            # 组装仪表板数据
            dashboard_data = {
                "key_metrics": {
                    "total_assets": basic_stats["total_count"],
                    "total_area": basic_stats["total_area"],
                    "total_rentable_area": basic_stats["total_rentable_area"],
                    "overall_occupancy_rate": occupancy_analysis["overall_occupancy"],
                    "total_rented_area": basic_stats["total_rented_area"],
                    "total_unrented_area": basic_stats["total_unrented_area"]
                },
                "charts": {
                    "ownership_distribution": ownership_chart,
                    "property_nature_distribution": nature_chart,
                    "usage_status_distribution": usage_chart,
                    "occupancy_ranges": occupancy_analysis["chart_data"]
                },
                "generated_at": datetime.now().isoformat(),
                "data_count": len(assets)
            }
            
            logger.info(f"仪表板数据生成完成，包含 {len(assets)} 条资产数据")
            return {
                "success": True,
                "message": f"成功生成仪表板数据",
                "data": dashboard_data
            }
            
        except Exception as e:
            logger.error(f"生成仪表板数据失败: {str(e)}")
            return {
                "success": False,
                "message": f"生成仪表板数据失败: {str(e)}",
                "data": None
            }
    
    def _get_filtered_assets(
        self, 
        filters: Optional[Dict[str, Any]], 
        db: Session
    ) -> List[Asset]:
        """根据筛选条件获取资产数据"""
        try:
            if not filters:
                # 获取所有资产
                return self.asset_crud.get_multi(db, limit=10000)
            
            # 构建筛选条件
            filter_dict = {}
            for key, value in filters.items():
                if value is not None and value != "":
                    filter_dict[key] = value
            
            # 使用现有的搜索功能
            assets = self.asset_crud.get_multi_with_search(
                db=db,
                search=filters.get("search"),
                filters=filter_dict if filter_dict else None,
                skip=0,
                limit=10000
            )
            
            return assets
            
        except Exception as e:
            logger.error(f"获取筛选资产数据失败: {str(e)}")
            raise StatisticsError(f"获取筛选资产数据失败: {str(e)}")