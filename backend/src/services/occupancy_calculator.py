"""
出租率自动计算服务
提供实时出租率计算、趋势分析和预测功能
"""

import polars as pl
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from src.models.asset import Asset
from src.crud.asset import CRUDAsset
from src.database import get_db

logger = logging.getLogger(__name__)


class OccupancyCalculationError(Exception):
    """出租率计算异常"""
    pass


class OccupancyRateCalculator:
    """出租率计算器"""
    
    @staticmethod
    def calculate_individual_occupancy_rate(
        rentable_area: float, 
        rented_area: float
    ) -> float:
        """
        计算单个资产的出租率
        
        Args:
            rentable_area: 可出租面积
            rented_area: 已出租面积
            
        Returns:
            出租率（百分比）
        """
        if not rentable_area or rentable_area <= 0:
            return 0.0
        
        if not rented_area or rented_area < 0:
            return 0.0
        
        # 确保已出租面积不超过可出租面积
        actual_rented = min(rented_area, rentable_area)
        
        occupancy_rate = (actual_rented / rentable_area) * 100
        return round(occupancy_rate, 2)
    
    @staticmethod
    def calculate_overall_occupancy_rate(assets: List[Asset]) -> Dict[str, Any]:
        """
        计算整体出租率
        
        Args:
            assets: 资产列表
            
        Returns:
            整体出租率统计信息
        """
        try:
            if not assets:
                return {
                    "overall_rate": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "asset_count": 0,
                    "rentable_asset_count": 0
                }
            
            # 筛选出有可出租面积的资产
            rentable_assets = [
                asset for asset in assets 
                if asset.rentable_area and asset.rentable_area > 0
            ]
            
            if not rentable_assets:
                return {
                    "overall_rate": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "asset_count": len(assets),
                    "rentable_asset_count": 0
                }
            
            # 计算总面积
            total_rentable = sum([asset.rentable_area or 0.0 for asset in rentable_assets])
            total_rented = sum([asset.rented_area or 0.0 for asset in rentable_assets])
            total_unrented = total_rentable - total_rented
            
            # 计算整体出租率
            overall_rate = (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            
            return {
                "overall_rate": round(overall_rate, 2),
                "total_rentable_area": round(total_rentable, 2),
                "total_rented_area": round(total_rented, 2),
                "total_unrented_area": round(total_unrented, 2),
                "asset_count": len(assets),
                "rentable_asset_count": len(rentable_assets)
            }
            
        except Exception as e:
            logger.error(f"计算整体出租率失败: {str(e)}")
            raise OccupancyCalculationError(f"计算整体出租率失败: {str(e)}")
    
    @staticmethod
    def calculate_occupancy_by_category(
        assets: List[Asset], 
        category_field: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        按分类计算出租率
        
        Args:
            assets: 资产列表
            category_field: 分类字段名
            
        Returns:
            按分类的出租率统计
        """
        try:
            if not assets:
                return {}
            
            # 按分类分组
            categories = {}
            for asset in assets:
                category_value = getattr(asset, category_field, None) or "未知"
                if category_value not in categories:
                    categories[category_value] = []
                categories[category_value].append(asset)
            
            # 计算每个分类的出租率
            result = {}
            for category, category_assets in categories.items():
                category_stats = OccupancyRateCalculator.calculate_overall_occupancy_rate(category_assets)
                
                # 计算平均单体出租率
                individual_rates = []
                for asset in category_assets:
                    if asset.rentable_area and asset.rentable_area > 0:
                        rate = OccupancyRateCalculator.calculate_individual_occupancy_rate(
                            asset.rentable_area, asset.rented_area or 0.0
                        )
                        individual_rates.append(rate)
                
                avg_individual_rate = sum(individual_rates) / len(individual_rates) if individual_rates else 0.0
                
                result[category] = {
                    **category_stats,
                    "avg_individual_rate": round(avg_individual_rate, 2),
                    "rate_range": {
                        "min": round(min(individual_rates), 2) if individual_rates else 0.0,
                        "max": round(max(individual_rates), 2) if individual_rates else 0.0
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"按分类计算出租率失败: {str(e)}")
            raise OccupancyCalculationError(f"按分类计算出租率失败: {str(e)}")
    
    @staticmethod
    def analyze_occupancy_distribution(assets: List[Asset]) -> Dict[str, Any]:
        """
        分析出租率分布
        
        Args:
            assets: 资产列表
            
        Returns:
            出租率分布分析
        """
        try:
            if not assets:
                return {
                    "distribution": {},
                    "statistics": {},
                    "chart_data": []
                }
            
            # 计算每个资产的出租率
            occupancy_rates = []
            for asset in assets:
                if asset.rentable_area and asset.rentable_area > 0:
                    rate = OccupancyRateCalculator.calculate_individual_occupancy_rate(
                        asset.rentable_area, asset.rented_area or 0.0
                    )
                    occupancy_rates.append(rate)
            
            if not occupancy_rates:
                return {
                    "distribution": {},
                    "statistics": {},
                    "chart_data": []
                }
            
            # 定义出租率区间
            ranges = [
                (0, 20, "极低出租率（0-20%）"),
                (20, 50, "低出租率（20-50%）"),
                (50, 80, "中等出租率（50-80%）"),
                (80, 95, "高出租率（80-95%）"),
                (95, 100, "极高出租率（95-100%）"),
                (100, float('inf'), "满租（100%）")
            ]
            
            # 统计各区间分布
            distribution = {}
            chart_data = []
            
            for min_rate, max_rate, label in ranges:
                if max_rate == float('inf'):
                    count = len([r for r in occupancy_rates if r >= min_rate])
                else:
                    count = len([r for r in occupancy_rates if min_rate <= r < max_rate])
                
                if count > 0:
                    percentage = round(count / len(occupancy_rates) * 100, 2)
                    
                    distribution[label] = {
                        "count": count,
                        "percentage": percentage,
                        "range": f"{min_rate}-{max_rate if max_rate != float('inf') else '100+'}%"
                    }
                    
                    chart_data.append({
                        "name": label,
                        "count": count,
                        "percentage": percentage,
                        "range": f"{min_rate}-{max_rate if max_rate != float('inf') else '100+'}%"
                    })
            
            # 计算统计指标
            df = pl.DataFrame({"rate": occupancy_rates})
            stats = df.select([
                pl.col("rate").min().alias("min_rate"),
                pl.col("rate").max().alias("max_rate"),
                pl.col("rate").mean().alias("avg_rate"),
                pl.col("rate").median().alias("median_rate"),
                pl.col("rate").std().alias("std_rate"),
                pl.col("rate").quantile(0.25).alias("q1_rate"),
                pl.col("rate").quantile(0.75).alias("q3_rate")
            ]).to_dicts()[0]
            
            # 格式化统计数据
            statistics = {
                "min_rate": round(stats["min_rate"], 2),
                "max_rate": round(stats["max_rate"], 2),
                "avg_rate": round(stats["avg_rate"], 2),
                "median_rate": round(stats["median_rate"], 2),
                "std_rate": round(stats["std_rate"], 2),
                "q1_rate": round(stats["q1_rate"], 2),
                "q3_rate": round(stats["q3_rate"], 2),
                "total_assets": len(occupancy_rates)
            }
            
            return {
                "distribution": distribution,
                "statistics": statistics,
                "chart_data": chart_data
            }
            
        except Exception as e:
            logger.error(f"分析出租率分布失败: {str(e)}")
            raise OccupancyCalculationError(f"分析出租率分布失败: {str(e)}")


class OccupancyTrendAnalyzer:
    """出租率趋势分析器"""
    
    @staticmethod
    def calculate_trend_change(
        current_rate: float, 
        previous_rate: float
    ) -> Dict[str, Any]:
        """
        计算趋势变化
        
        Args:
            current_rate: 当前出租率
            previous_rate: 之前出租率
            
        Returns:
            趋势变化信息
        """
        if previous_rate == 0:
            return {
                "change": current_rate,
                "change_percentage": 100.0 if current_rate > 0 else 0.0,
                "trend": "up" if current_rate > 0 else "stable"
            }
        
        change = current_rate - previous_rate
        change_percentage = (change / previous_rate) * 100
        
        if abs(change) < 0.1:  # 变化小于0.1%认为是稳定
            trend = "stable"
        elif change > 0:
            trend = "up"
        else:
            trend = "down"
        
        return {
            "change": round(change, 2),
            "change_percentage": round(change_percentage, 2),
            "trend": trend
        }
    
    @staticmethod
    def analyze_monthly_trend(
        assets: List[Asset], 
        months: int = 12
    ) -> Dict[str, Any]:
        """
        分析月度趋势（模拟数据，实际应该从历史记录获取）
        
        Args:
            assets: 资产列表
            months: 分析月数
            
        Returns:
            月度趋势分析
        """
        try:
            # 当前出租率
            current_stats = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)
            current_rate = current_stats["overall_rate"]
            
            # 模拟历史数据（实际应该从数据库获取）
            monthly_data = []
            base_date = datetime.now().replace(day=1)
            
            for i in range(months):
                month_date = base_date - timedelta(days=30 * i)
                
                # 模拟月度出租率变化（实际应该查询历史数据）
                # 这里简单模拟一个波动
                import random
                random.seed(i)  # 确保结果可重现
                variation = random.uniform(-5, 5)  # ±5%的变化
                simulated_rate = max(0, min(100, current_rate + variation))
                
                monthly_data.append({
                    "month": month_date.strftime("%Y-%m"),
                    "rate": round(simulated_rate, 2),
                    "total_rentable_area": current_stats["total_rentable_area"],
                    "total_rented_area": round(current_stats["total_rentable_area"] * simulated_rate / 100, 2)
                })
            
            # 按时间排序
            monthly_data.sort(key=lambda x: x["month"])
            
            # 计算趋势
            if len(monthly_data) >= 2:
                latest_rate = monthly_data[-1]["rate"]
                previous_rate = monthly_data[-2]["rate"]
                trend_info = OccupancyTrendAnalyzer.calculate_trend_change(latest_rate, previous_rate)
            else:
                trend_info = {"change": 0.0, "change_percentage": 0.0, "trend": "stable"}
            
            # 计算平均增长率
            if len(monthly_data) >= 2:
                first_rate = monthly_data[0]["rate"]
                last_rate = monthly_data[-1]["rate"]
                total_months = len(monthly_data) - 1
                avg_growth_rate = ((last_rate - first_rate) / total_months) if total_months > 0 else 0.0
            else:
                avg_growth_rate = 0.0
            
            return {
                "monthly_data": monthly_data,
                "trend_info": trend_info,
                "avg_growth_rate": round(avg_growth_rate, 2),
                "period": f"{months}个月",
                "data_points": len(monthly_data)
            }
            
        except Exception as e:
            logger.error(f"分析月度趋势失败: {str(e)}")
            raise OccupancyCalculationError(f"分析月度趋势失败: {str(e)}")
    
    @staticmethod
    def predict_future_occupancy(
        monthly_data: List[Dict[str, Any]], 
        months_ahead: int = 3
    ) -> List[Dict[str, Any]]:
        """
        预测未来出租率（简单线性预测）
        
        Args:
            monthly_data: 历史月度数据
            months_ahead: 预测月数
            
        Returns:
            预测数据
        """
        try:
            if len(monthly_data) < 2:
                return []
            
            # 计算趋势斜率（简单线性回归）
            rates = [data["rate"] for data in monthly_data]
            n = len(rates)
            
            # 计算平均增长率
            total_change = rates[-1] - rates[0]
            avg_monthly_change = total_change / (n - 1) if n > 1 else 0
            
            # 生成预测数据
            predictions = []
            last_date = datetime.strptime(monthly_data[-1]["month"], "%Y-%m")
            last_rate = monthly_data[-1]["rate"]
            
            for i in range(1, months_ahead + 1):
                # 计算预测月份
                future_date = last_date + timedelta(days=30 * i)
                
                # 简单线性预测
                predicted_rate = last_rate + (avg_monthly_change * i)
                
                # 限制在合理范围内
                predicted_rate = max(0, min(100, predicted_rate))
                
                predictions.append({
                    "month": future_date.strftime("%Y-%m"),
                    "predicted_rate": round(predicted_rate, 2),
                    "confidence": max(0.5, 1.0 - (i * 0.1))  # 预测越远置信度越低
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测未来出租率失败: {str(e)}")
            return []


class OccupancyService:
    """出租率服务"""
    
    def __init__(self):
        self.calculator = OccupancyRateCalculator()
        self.trend_analyzer = OccupancyTrendAnalyzer()
        self.asset_crud = CRUDAsset(Asset)
    
    async def calculate_comprehensive_occupancy(
        self,
        filters: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        计算综合出租率分析
        
        Args:
            filters: 筛选条件
            db: 数据库会话
            
        Returns:
            综合出租率分析结果
        """
        try:
            if db is None:
                db = next(get_db())
            
            # 获取资产数据
            assets = await self._get_filtered_assets(filters, db)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有找到符合条件的资产数据",
                    "data": None
                }
            
            # 计算整体出租率
            overall_stats = self.calculator.calculate_overall_occupancy_rate(assets)
            
            # 按物业性质分析
            by_nature = self.calculator.calculate_occupancy_by_category(assets, "property_nature")
            
            # 按权属方分析
            by_entity = self.calculator.calculate_occupancy_by_category(assets, "ownership_entity")
            
            # 按使用状态分析
            by_usage = self.calculator.calculate_occupancy_by_category(assets, "usage_status")
            
            # 出租率分布分析
            distribution = self.calculator.analyze_occupancy_distribution(assets)
            
            # 月度趋势分析
            monthly_trend = self.trend_analyzer.analyze_monthly_trend(assets)
            
            # 未来预测
            predictions = self.trend_analyzer.predict_future_occupancy(
                monthly_trend["monthly_data"], 3
            )
            
            # 组装结果
            result_data = {
                "overall_statistics": overall_stats,
                "by_property_nature": by_nature,
                "by_ownership_entity": by_entity,
                "by_usage_status": by_usage,
                "distribution_analysis": distribution,
                "monthly_trend": monthly_trend,
                "future_predictions": predictions,
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters or {},
                "data_count": len(assets)
            }
            
            logger.info(f"综合出租率分析完成，包含 {len(assets)} 条资产数据")
            return {
                "success": True,
                "message": f"成功计算 {len(assets)} 条资产的综合出租率分析",
                "data": result_data
            }
            
        except Exception as e:
            logger.error(f"计算综合出租率分析失败: {str(e)}")
            return {
                "success": False,
                "message": f"计算失败: {str(e)}",
                "data": None
            }
    
    async def update_asset_occupancy_rates(
        self,
        asset_ids: Optional[List[str]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        更新资产出租率字段
        
        Args:
            asset_ids: 要更新的资产ID列表，None表示更新所有
            db: 数据库会话
            
        Returns:
            更新结果
        """
        try:
            if db is None:
                db = next(get_db())
            
            # 获取要更新的资产
            if asset_ids:
                assets = []
                for asset_id in asset_ids:
                    asset = self.asset_crud.get(db, id=asset_id)
                    if asset:
                        assets.append(asset)
            else:
                assets = self.asset_crud.get_multi(db, limit=10000)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有找到要更新的资产",
                    "updated_count": 0
                }
            
            # 更新每个资产的出租率
            updated_count = 0
            for asset in assets:
                if asset.rentable_area and asset.rentable_area > 0:
                    # 计算出租率
                    occupancy_rate = self.calculator.calculate_individual_occupancy_rate(
                        asset.rentable_area, asset.rented_area or 0.0
                    )
                    
                    # 更新资产的出租率字段
                    update_data = {"occupancy_rate": f"{occupancy_rate}%"}
                    self.asset_crud.update(db, db_obj=asset, obj_in=update_data)
                    updated_count += 1
            
            # 提交更改
            db.commit()
            
            logger.info(f"成功更新 {updated_count} 个资产的出租率")
            return {
                "success": True,
                "message": f"成功更新 {updated_count} 个资产的出租率",
                "updated_count": updated_count,
                "total_assets": len(assets)
            }
            
        except Exception as e:
            logger.error(f"更新资产出租率失败: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "updated_count": 0
            }
    
    async def get_occupancy_insights(
        self,
        filters: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        获取出租率洞察分析
        
        Args:
            filters: 筛选条件
            db: 数据库会话
            
        Returns:
            出租率洞察分析
        """
        try:
            if db is None:
                db = next(get_db())
            
            # 获取资产数据
            assets = await self._get_filtered_assets(filters, db)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有找到符合条件的资产数据",
                    "data": None
                }
            
            # 计算基础统计
            overall_stats = self.calculator.calculate_overall_occupancy_rate(assets)
            distribution = self.calculator.analyze_occupancy_distribution(assets)
            
            # 生成洞察
            insights = []
            
            # 整体出租率洞察
            overall_rate = overall_stats["overall_rate"]
            if overall_rate >= 90:
                insights.append({
                    "type": "positive",
                    "title": "出租率表现优秀",
                    "description": f"整体出租率达到 {overall_rate}%，表现优秀",
                    "recommendation": "继续保持现有管理策略，关注租户满意度"
                })
            elif overall_rate >= 70:
                insights.append({
                    "type": "neutral",
                    "title": "出租率表现良好",
                    "description": f"整体出租率为 {overall_rate}%，处于良好水平",
                    "recommendation": "可以通过优化租赁策略进一步提升出租率"
                })
            else:
                insights.append({
                    "type": "warning",
                    "title": "出租率需要改善",
                    "description": f"整体出租率仅为 {overall_rate}%，低于行业平均水平",
                    "recommendation": "建议分析空置原因，制定针对性的招租策略"
                })
            
            # 分布洞察
            stats = distribution["statistics"]
            if stats["std_rate"] > 30:
                insights.append({
                    "type": "info",
                    "title": "出租率差异较大",
                    "description": f"资产间出租率差异较大（标准差 {stats['std_rate']:.1f}%）",
                    "recommendation": "关注低出租率资产，分析其特点并制定改善措施"
                })
            
            # 空置面积洞察
            unrented_area = overall_stats["total_unrented_area"]
            if unrented_area > 1000:
                insights.append({
                    "type": "opportunity",
                    "title": "存在较大空置面积",
                    "description": f"总空置面积达到 {unrented_area:.0f} 平方米",
                    "recommendation": "重点关注空置面积的招租工作，可考虑调整租金策略"
                })
            
            # 按分类分析洞察
            by_nature = self.calculator.calculate_occupancy_by_category(assets, "property_nature")
            if len(by_nature) > 1:
                # 找出表现最好和最差的物业性质
                best_nature = max(by_nature.items(), key=lambda x: x[1]["overall_rate"])
                worst_nature = min(by_nature.items(), key=lambda x: x[1]["overall_rate"])
                
                if best_nature[1]["overall_rate"] - worst_nature[1]["overall_rate"] > 20:
                    insights.append({
                        "type": "comparison",
                        "title": "不同物业性质表现差异明显",
                        "description": f"{best_nature[0]}出租率 {best_nature[1]['overall_rate']:.1f}%，{worst_nature[0]}出租率 {worst_nature[1]['overall_rate']:.1f}%",
                        "recommendation": f"学习{best_nature[0]}的成功经验，改善{worst_nature[0]}的管理策略"
                    })
            
            result_data = {
                "insights": insights,
                "summary": {
                    "total_insights": len(insights),
                    "overall_rate": overall_rate,
                    "total_assets": len(assets),
                    "rentable_assets": overall_stats["rentable_asset_count"]
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"出租率洞察分析完成，生成 {len(insights)} 条洞察")
            return {
                "success": True,
                "message": f"成功生成出租率洞察分析",
                "data": result_data
            }
            
        except Exception as e:
            logger.error(f"获取出租率洞察失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取洞察失败: {str(e)}",
                "data": None
            }
    
    async def _get_filtered_assets(
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
            raise OccupancyCalculationError(f"获取筛选资产数据失败: {str(e)}")