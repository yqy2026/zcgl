"""
Excel数据导出服务
使用Polars进行高性能数据处理和导出
"""

import polars as pl
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
from datetime import datetime, timedelta
import tempfile
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.models.asset import Asset
from src.crud.asset import CRUDAsset
from src.schemas.asset import AssetSearchParams
from src.database import get_db

logger = logging.getLogger(__name__)


class ExcelExportError(Exception):
    """Excel导出异常"""
    pass


class AssetDataExporter:
    """使用Polars进行高性能数据导出"""
    
    # 数据库字段到Excel列名的映射（与导入相反）
    FIELD_TO_COLUMN_MAPPING = {
        "ownership_entity": "权属方",
        "management_entity": "经营管理方",
        "property_name": "物业名称",
        "address": "所在地址",
        "land_area": "土地面积\n(平方米)",
        "actual_property_area": "实际房产面积\n(平方米)",
        "rentable_area": "经营性物业可出租面积\n(平方米)",
        "rented_area": "经营性物业已出租面积\n(平方米)",
        "unrented_area": "经营性物业未出租面积\n(平方米)",
        "non_commercial_area": "非经营物业面积\n(平方米)",
        "ownership_status": "是否确权\n（已确权、未确权、部分确权）",
        "certificated_usage": "证载用途\n（商业、住宅、办公、厂房、车位..）",
        "actual_usage": "实际用途\n（商业、住宅、办公、厂房、车位..）",
        "business_category": "业态类别",
        "usage_status": "物业使用状态\n（出租、闲置、自用、公房、其他）",
        "is_litigated": "是否涉诉",
        "property_nature": "物业性质（经营类、非经营类）",
        "business_model": "经营模式",
        "include_in_occupancy_rate": "是否计入出租率",
        "occupancy_rate": "出租率",
        "lease_contract": "承租合同/代理协议",
        "current_contract_start_date": "现合同开始日期",
        "current_contract_end_date": "现合同结束日期",
        "tenant_name": "租户名称",
        "ownership_category": "权属类别",
        "current_lease_contract": "现租赁合同",
        "wuyang_project_name": "五羊运营项目名称",
        "agreement_start_date": "协议开始日期",
        "agreement_end_date": "协议结束日期",
        "current_terminal_contract": "现终端出租合同",
        "description": "说明",
        "notes": "其他备注",
        "created_at": "创建时间",
        "updated_at": "更新时间"
    }
    
    # 默认导出的列（按Excel模板顺序）
    DEFAULT_EXPORT_COLUMNS = [
        "ownership_entity", "management_entity", "property_name", "address",
        "land_area", "actual_property_area", "rentable_area", "rented_area",
        "unrented_area", "non_commercial_area", "ownership_status",
        "certificated_usage", "actual_usage", "business_category",
        "usage_status", "is_litigated", "property_nature", "business_model",
        "include_in_occupancy_rate", "occupancy_rate", "lease_contract",
        "current_contract_start_date", "current_contract_end_date",
        "tenant_name", "ownership_category", "current_lease_contract",
        "wuyang_project_name", "agreement_start_date", "agreement_end_date",
        "current_terminal_contract", "description", "notes"
    ]
    
    @staticmethod
    def convert_assets_to_dataframe(
        assets: List[Asset], 
        columns: Optional[List[str]] = None
    ) -> pl.DataFrame:
        """将资产列表转换为Polars DataFrame"""
        try:
            if not assets:
                # 返回空的DataFrame，但包含列结构
                columns_to_use = columns or AssetDataExporter.DEFAULT_EXPORT_COLUMNS
                empty_data = {col: [] for col in columns_to_use}
                return pl.DataFrame(empty_data)
            
            # 准备数据
            data_rows = []
            columns_to_use = columns or AssetDataExporter.DEFAULT_EXPORT_COLUMNS
            
            for asset in assets:
                row = {}
                for field in columns_to_use:
                    value = getattr(asset, field, None)
                    
                    # 处理不同类型的数据
                    if value is None:
                        row[field] = ""
                    elif isinstance(value, datetime):
                        # 格式化日期为中文格式
                        row[field] = value.strftime("%Y年%m月%d日")
                    elif isinstance(value, (int, float)):
                        row[field] = value
                    else:
                        row[field] = str(value)
                
                data_rows.append(row)
            
            # 创建DataFrame
            df = pl.DataFrame(data_rows)
            
            logger.info(f"成功转换 {len(assets)} 条资产数据为DataFrame")
            return df
            
        except Exception as e:
            logger.error(f"转换资产数据失败: {str(e)}")
            raise ExcelExportError(f"转换资产数据失败: {str(e)}")
    
    @staticmethod
    def rename_columns_for_export(
        df: pl.DataFrame, 
        include_headers: bool = True
    ) -> pl.DataFrame:
        """重命名列为Excel导出格式"""
        try:
            if not include_headers:
                return df
            
            # 创建重命名映射
            rename_dict = {}
            for col in df.columns:
                if col in AssetDataExporter.FIELD_TO_COLUMN_MAPPING:
                    rename_dict[col] = AssetDataExporter.FIELD_TO_COLUMN_MAPPING[col]
            
            if rename_dict:
                df = df.rename(rename_dict)
            
            logger.info(f"重命名了 {len(rename_dict)} 个列名")
            return df
            
        except Exception as e:
            logger.error(f"重命名列失败: {str(e)}")
            raise ExcelExportError(f"重命名列失败: {str(e)}")
    
    @staticmethod
    def export_to_excel(
        df: pl.DataFrame,
        file_path: str,
        sheet_name: str = "资产清单",
        include_headers: bool = True
    ) -> None:
        """导出DataFrame到Excel文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 导出到Excel
            df.write_excel(
                file_path,
                worksheet=sheet_name,
                include_header=include_headers
            )
            
            logger.info(f"成功导出 {len(df)} 行数据到 {file_path}")
            
        except Exception as e:
            logger.error(f"导出Excel文件失败: {str(e)}")
            raise ExcelExportError(f"导出Excel文件失败: {str(e)}")
    
    @staticmethod
    def calculate_export_stats(df: pl.DataFrame) -> Dict[str, Any]:
        """计算导出统计信息"""
        try:
            stats = {
                "total_records": len(df),
                "total_columns": len(df.columns),
                "export_time": datetime.now().isoformat(),
            }
            
            # 如果有面积数据，计算统计
            if "actual_property_area" in df.columns:
                area_stats = df.select([
                    pl.col("actual_property_area").sum().alias("total_area"),
                    pl.col("actual_property_area").mean().alias("avg_area"),
                    pl.col("actual_property_area").max().alias("max_area"),
                    pl.col("actual_property_area").min().alias("min_area")
                ]).to_dicts()[0]
                
                stats.update({
                    "total_area": round(area_stats["total_area"] or 0, 2),
                    "avg_area": round(area_stats["avg_area"] or 0, 2),
                    "max_area": area_stats["max_area"] or 0,
                    "min_area": area_stats["min_area"] or 0
                })
            
            # 统计各种状态的分布
            if "ownership_status" in df.columns:
                ownership_counts = df.group_by("ownership_status").len().to_dicts()
                stats["ownership_distribution"] = {
                    item["ownership_status"]: item["len"] 
                    for item in ownership_counts
                }
            
            if "property_nature" in df.columns:
                nature_counts = df.group_by("property_nature").len().to_dicts()
                stats["nature_distribution"] = {
                    item["property_nature"]: item["len"] 
                    for item in nature_counts
                }
            
            return stats
            
        except Exception as e:
            logger.warning(f"计算导出统计失败: {str(e)}")
            return {
                "total_records": len(df),
                "total_columns": len(df.columns),
                "export_time": datetime.now().isoformat(),
            }


class ExcelExportService:
    """Excel导出服务"""
    
    def __init__(self):
        self.exporter = AssetDataExporter()
        self.asset_crud = CRUDAsset(Asset)
    
    async def export_assets_to_excel(
        self,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        format: str = "xlsx",
        include_headers: bool = True,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """导出资产数据到Excel文件"""
        try:
            if db is None:
                db = next(get_db())
            
            # 获取资产数据
            assets = await self._get_filtered_assets(filters, db)
            
            if not assets:
                return {
                    "success": False,
                    "message": "没有找到符合条件的资产数据",
                    "file_path": None,
                    "stats": {"total_records": 0}
                }
            
            # 转换为DataFrame
            df = self.exporter.convert_assets_to_dataframe(assets, columns)
            
            # 重命名列
            df = self.exporter.rename_columns_for_export(df, include_headers)
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"资产导出_{timestamp}.{format}"
            file_path = os.path.join(temp_dir, filename)
            
            # 导出到Excel
            self.exporter.export_to_excel(
                df, 
                file_path, 
                sheet_name="资产清单",
                include_headers=include_headers
            )
            
            # 计算统计信息
            stats = self.exporter.calculate_export_stats(df)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            return {
                "success": True,
                "message": f"成功导出 {len(assets)} 条资产数据",
                "file_path": file_path,
                "file_name": filename,
                "file_size": file_size,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Excel导出失败: {str(e)}")
            return {
                "success": False,
                "message": f"导出失败: {str(e)}",
                "file_path": None,
                "stats": {"total_records": 0}
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
                return self.asset_crud.get_multi(db, limit=10000)  # 限制最大导出数量
            
            # 检查是否是通过ID列表导出
            if "asset_ids" in filters:
                asset_ids = filters["asset_ids"]
                if not asset_ids:
                    return []
                
                # 通过ID列表获取资产
                assets = []
                for asset_id in asset_ids:
                    asset = self.asset_crud.get(db, id=asset_id)
                    if asset:
                        assets.append(asset)
                
                return assets
            
            # 构建查询参数
            search_params = AssetSearchParams(**filters)
            
            # 构建筛选条件
            filter_dict = {}
            if search_params.ownership_status:
                filter_dict["ownership_status"] = search_params.ownership_status
            if search_params.property_nature:
                filter_dict["property_nature"] = search_params.property_nature
            if search_params.usage_status:
                filter_dict["usage_status"] = search_params.usage_status
            if search_params.ownership_entity:
                filter_dict["ownership_entity"] = search_params.ownership_entity
            
            # 使用现有的搜索功能
            assets = self.asset_crud.get_multi_with_search(
                db=db,
                search=search_params.search,
                filters=filter_dict if filter_dict else None,
                skip=0,
                limit=10000,  # 导出时不分页，但限制最大数量
                sort_field=search_params.sort_field,
                sort_order=search_params.sort_order
            )
            
            return assets
            
        except Exception as e:
            logger.error(f"获取筛选资产数据失败: {str(e)}")
            raise ExcelExportError(f"获取筛选资产数据失败: {str(e)}")
    
    async def get_export_template_info(self) -> Dict[str, Any]:
        """获取导出模板信息"""
        return {
            "available_columns": list(AssetDataExporter.FIELD_TO_COLUMN_MAPPING.keys()),
            "column_descriptions": AssetDataExporter.FIELD_TO_COLUMN_MAPPING,
            "default_columns": AssetDataExporter.DEFAULT_EXPORT_COLUMNS,
            "supported_formats": ["xlsx", "xls", "csv"],
            "max_export_records": 10000,
            "export_options": {
                "include_headers": "是否包含表头",
                "format": "导出格式（xlsx/xls/csv）",
                "columns": "要导出的列（留空则导出所有默认列）"
            }
        }
    
    def cleanup_export_file(self, file_path: str) -> bool:
        """清理导出文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"已清理导出文件: {file_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"清理导出文件失败: {str(e)}")
            return False