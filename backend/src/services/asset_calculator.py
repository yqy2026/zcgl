"""
资产计算服务
处理出租率、净收益等自动计算逻辑
"""

from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class AssetCalculator:
    """资产计算器"""
    
    @staticmethod
    def calculate_occupancy_rate(rentable_area: Optional[float], rented_area: Optional[float]) -> Optional[float]:
        """
        计算出租率
        
        Args:
            rentable_area: 可出租面积
            rented_area: 已出租面积
            
        Returns:
            出租率（百分比），保留2位小数
        """
        if not rentable_area or rentable_area <= 0:
            return 0.0
            
        if not rented_area or rented_area < 0:
            return 0.0
            
        # 防止已出租面积大于可出租面积
        if rented_area > rentable_area:
            rented_area = rentable_area
            
        rate = (rented_area / rentable_area) * 100
        # 使用Decimal进行精确计算并四舍五入
        return float(Decimal(str(rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def calculate_unrented_area(rentable_area: Optional[float], rented_area: Optional[float]) -> Optional[float]:
        """
        计算未出租面积
        
        Args:
            rentable_area: 可出租面积
            rented_area: 已出租面积
            
        Returns:
            未出租面积
        """
        if not rentable_area or rentable_area <= 0:
            return 0.0
            
        if not rented_area or rented_area < 0:
            return rentable_area
            
        # 防止已出租面积大于可出租面积
        if rented_area > rentable_area:
            return 0.0
            
        return rentable_area - rented_area
    
    @staticmethod
    def calculate_net_income(annual_income: Optional[float], annual_expense: Optional[float]) -> Optional[float]:
        """
        计算净收益
        
        Args:
            annual_income: 年收益
            annual_expense: 年支出
            
        Returns:
            净收益
        """
        if annual_income is None and annual_expense is None:
            return None
            
        income = annual_income or 0.0
        expense = annual_expense or 0.0
        
        return income - expense
    
    @staticmethod
    def validate_area_consistency(data: dict) -> list:
        """
        验证面积数据的一致性
        
        Args:
            data: 包含面积字段的数据字典
            
        Returns:
            验证错误列表
        """
        errors = []
        
        # 获取面积字段
        rentable_area = data.get('rentable_area')
        rented_area = data.get('rented_area')
        actual_property_area = data.get('actual_property_area')
        land_area = data.get('land_area')
        
        # 验证逻辑关系
        if rentable_area and rented_area and rented_area > rentable_area:
            errors.append("已出租面积不能大于可出租面积")
            
            
        return errors
    
    @staticmethod
    def auto_calculate_fields(data: dict) -> dict:
        """
        自动计算相关字段
        
        Args:
            data: 资产数据字典
            
        Returns:
            更新后的数据字典
        """
        # 计算出租率
        if 'rentable_area' in data or 'rented_area' in data:
            rentable_area = data.get('rentable_area')
            rented_area = data.get('rented_area')
            data['occupancy_rate'] = AssetCalculator.calculate_occupancy_rate(rentable_area, rented_area)
            data['unrented_area'] = AssetCalculator.calculate_unrented_area(rentable_area, rented_area)
        
        # 计算净收益
        if 'annual_income' in data or 'annual_expense' in data:
            annual_income = data.get('annual_income')
            annual_expense = data.get('annual_expense')
            data['net_income'] = AssetCalculator.calculate_net_income(annual_income, annual_expense)
        
        return data


class OccupancyRateCalculator:
    """出租率统计计算器"""
    
    @staticmethod
    def calculate_overall_occupancy_rate(assets: list) -> dict:
        """
        计算整体出租率
        
        Args:
            assets: 资产列表
            
        Returns:
            包含统计信息的字典
        """
        total_rentable_area = 0.0
        total_rented_area = 0.0
        included_assets = 0
        
        for asset in assets:
            # 只统计标记为计入出租率的资产
            if not getattr(asset, 'include_in_occupancy_rate', True):
                continue
                
            rentable_area = float(getattr(asset, 'rentable_area', 0) or 0)
            rented_area = float(getattr(asset, 'rented_area', 0) or 0)
            
            if rentable_area > 0:
                total_rentable_area += float(rentable_area)
                total_rented_area += float(min(rented_area, rentable_area))  # 防止超出
                included_assets += 1
        
        overall_rate = 0.0
        if total_rentable_area > 0:
            overall_rate = AssetCalculator.calculate_occupancy_rate(total_rentable_area, total_rented_area)
        
        return {
            'overall_occupancy_rate': overall_rate,
            'total_rentable_area': total_rentable_area,
            'total_rented_area': total_rented_area,
            'total_unrented_area': total_rentable_area - total_rented_area,
            'included_assets_count': included_assets,
            'total_assets_count': len(assets)
        }
    
    @staticmethod
    def calculate_occupancy_by_category(assets: list, category_field: str) -> dict:
        """
        按类别计算出租率
        
        Args:
            assets: 资产列表
            category_field: 分类字段名
            
        Returns:
            按类别的出租率统计
        """
        categories = {}
        
        for asset in assets:
            if not getattr(asset, 'include_in_occupancy_rate', True):
                continue

            category = getattr(asset, category_field, '未分类') or '未分类'

            if category not in categories:
                categories[category] = {
                    'rentable_area': 0.0,
                    'rented_area': 0.0,
                    'asset_count': 0
                }

            rentable_area = float(getattr(asset, 'rentable_area', 0) or 0)
            rented_area = float(getattr(asset, 'rented_area', 0) or 0)

            if rentable_area > 0:
                categories[category]['rentable_area'] += float(rentable_area)
                categories[category]['rented_area'] += float(min(rented_area, rentable_area))
                categories[category]['asset_count'] += 1
        
        # 计算各类别的出租率
        result = {}
        for category, data in categories.items():
            occupancy_rate = AssetCalculator.calculate_occupancy_rate(
                data['rentable_area'], 
                data['rented_area']
            )
            
            result[category] = {
                'occupancy_rate': occupancy_rate,
                'rentable_area': data['rentable_area'],
                'rented_area': data['rented_area'],
                'unrented_area': data['rentable_area'] - data['rented_area'],
                'asset_count': data['asset_count']
            }
        
        return result