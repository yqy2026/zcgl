"""
Excel数据导入服务
使用Polars进行高性能数据处理
"""

import polars as pl
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime
import re

from src.schemas.asset import AssetCreate, OwnershipStatus, UsageStatus, PropertyNature
from src.crud.asset import CRUDAsset
from src.models.asset import Asset
from src.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ExcelImportError(Exception):
    """Excel导入异常"""
    pass


class AssetDataProcessor:
    """使用Polars进行高性能数据处理"""
    
    # Excel列名到数据库字段的映射
    COLUMN_MAPPING = {
        "权属方": "ownership_entity",
        "经营管理方": "management_entity",
        "物业名称": "property_name",
        "所在地址": "address",
        "土地面积\n(平方米)": "land_area",
        "实际房产面积\n(平方米)": "actual_property_area",
        "经营性物业可出租面积\n(平方米)": "rentable_area",
        "经营性物业已出租面积\n(平方米)": "rented_area",
        "经营性物业未出租面积\n(平方米)": "unrented_area",
        "非经营物业面积\n(平方米)": "non_commercial_area",
        "是否确权\n（已确权、未确权、部分确权）": "ownership_status",
        "证载用途\n（商业、住宅、办公、厂房、车位..）": "certificated_usage",
        "实际用途\n（商业、住宅、办公、厂房、车位..）": "actual_usage",
        "物业使用状态\n（出租、闲置、自用、公房、其他）": "usage_status",
        "是否涉诉": "is_litigated",
        "物业性质（经营类、非经营类）": "property_nature",
        "经营模式": "business_model",
        "承租合同/代理协议": "lease_contract",
        "说明": "description",
        "现合同结束日期": "current_contract_end_date",
        "现合同开始日期": "current_contract_start_date",
        "租户名称": "tenant_name",
        "权属类别": "ownership_category",
        "业态类别": "business_category",
        "是否计入出租率": "include_in_occupancy_rate",
        "出租率": "occupancy_rate",
        "现租赁合同": "current_lease_contract",
        "五羊运营项目名称": "wuyang_project_name",
        "协议开始日期": "agreement_start_date",
        "协议结束日期": "agreement_end_date",
        "现终端出租合同": "current_terminal_contract",
    }
    
    @staticmethod
    def read_excel_file(file_path: str, sheet_name: str = "物业总表") -> pl.DataFrame:
        """从Excel文件读取数据"""
        try:
            # 使用Polars读取Excel文件
            df = pl.read_excel(
                file_path,
                sheet_name=sheet_name,
                infer_schema_length=1000  # 推断更多行的数据类型
            )
            
            logger.info(f"成功读取Excel文件: {file_path}, 行数: {len(df)}, 列数: {len(df.columns)}")
            return df
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {file_path}, 错误: {str(e)}")
            raise ExcelImportError(f"读取Excel文件失败: {str(e)}")
    
    @staticmethod
    def clean_and_transform_data(df: pl.DataFrame) -> pl.DataFrame:
        """数据清洗和标准化"""
        try:
            # 重命名列
            rename_dict = {}
            for old_col in df.columns:
                # 清理列名中的空白字符和换行符（处理\r\n和\n）
                clean_col = old_col.strip().replace('\r\n', '\n').replace('\r', '\n')
                if clean_col in AssetDataProcessor.COLUMN_MAPPING:
                    rename_dict[old_col] = AssetDataProcessor.COLUMN_MAPPING[clean_col]
                else:
                    # 如果找不到精确匹配，尝试模糊匹配
                    for excel_col, db_col in AssetDataProcessor.COLUMN_MAPPING.items():
                        # 标准化比较：移除所有空白字符和换行符
                        excel_normalized = excel_col.replace('\n', '').replace('\r', '').replace(' ', '')
                        col_normalized = clean_col.replace('\n', '').replace('\r', '').replace(' ', '')
                        if excel_normalized == col_normalized:
                            rename_dict[old_col] = db_col
                            break
            
            if rename_dict:
                df = df.rename(rename_dict)
            
            # 数据清洗和转换
            transformations = []
            
            # 处理字符串字段的空值和空白
            string_fields = [
                "ownership_entity", "management_entity", "property_name", "address",
                "certificated_usage", "actual_usage", "business_model", "lease_contract",
                "description", "tenant_name", "ownership_category", "business_category",
                "include_in_occupancy_rate", "occupancy_rate", "current_lease_contract",
                "wuyang_project_name", "current_terminal_contract"
            ]
            
            for field in string_fields:
                if field in df.columns:
                    transformations.append(
                        pl.col(field).fill_null("").str.strip_chars().alias(field)
                    )
            
            # 处理数值字段
            numeric_fields = [
                "land_area", "actual_property_area", "rentable_area", 
                "rented_area", "unrented_area", "non_commercial_area"
            ]
            
            for field in numeric_fields:
                if field in df.columns:
                    transformations.append(
                        pl.col(field).cast(pl.Float64, strict=False).fill_null(0.0).alias(field)
                    )
            
            # 处理枚举字段
            if "ownership_status" in df.columns:
                transformations.append(
                    pl.col("ownership_status").fill_null("未确权").str.strip_chars().alias("ownership_status")
                )
            
            if "usage_status" in df.columns:
                transformations.append(
                    pl.col("usage_status").fill_null("其他").str.strip_chars().alias("usage_status")
                )
            
            if "property_nature" in df.columns:
                transformations.append(
                    pl.col("property_nature").fill_null("经营类").str.strip_chars().alias("property_nature")
                )
            
            if "is_litigated" in df.columns:
                transformations.append(
                    pl.col("is_litigated").fill_null("否").str.strip_chars().alias("is_litigated")
                )
            
            # 处理日期字段
            date_fields = [
                "current_contract_start_date", "current_contract_end_date",
                "agreement_start_date", "agreement_end_date"
            ]
            
            for field in date_fields:
                if field in df.columns:
                    transformations.append(
                        AssetDataProcessor._parse_date_column(field)
                    )
            
            if transformations:
                df = df.with_columns(transformations)
            
            logger.info(f"数据清洗完成，处理后行数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"数据清洗失败: {str(e)}")
            raise ExcelImportError(f"数据清洗失败: {str(e)}")
    
    @staticmethod
    def _parse_date_column(field_name: str) -> pl.Expr:
        """解析日期列，支持多种日期格式"""
        return (
            pl.col(field_name)
            .str.strip_chars()
            .str.replace_all(r"年|月", "-")
            .str.replace_all(r"日", "")
            .str.to_datetime(format="%Y-%m-%d", strict=False)
            .alias(field_name)
        )
    
    @staticmethod
    def validate_data(df: pl.DataFrame) -> List[str]:
        """数据验证"""
        errors = []
        
        # 检查必填字段
        required_fields = ["ownership_entity", "property_name", "address", "actual_property_area"]
        
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必填字段: {field}")
                continue
            
            # 检查空值 - 分别处理字符串和数值字段
            try:
                if field in ["ownership_entity", "property_name", "address"]:
                    # 字符串字段检查
                    null_count = df.filter(
                        pl.col(field).is_null() | 
                        (pl.col(field).cast(pl.Utf8) == "")
                    ).height
                else:
                    # 数值字段检查
                    null_count = df.filter(pl.col(field).is_null()).height
                
                if null_count > 0:
                    errors.append(f"字段 {field} 有 {null_count} 行数据为空")
            except Exception as e:
                errors.append(f"验证字段 {field} 时出错: {str(e)}")
        
        # 检查数值字段的有效性
        numeric_fields = ["actual_property_area", "rentable_area", "rented_area", "unrented_area", "non_commercial_area"]
        
        for field in numeric_fields:
            if field in df.columns:
                try:
                    negative_count = df.filter(pl.col(field) < 0).height
                    if negative_count > 0:
                        errors.append(f"字段 {field} 有 {negative_count} 行数据为负数")
                except Exception as e:
                    errors.append(f"验证数值字段 {field} 时出错: {str(e)}")
        
        # 检查枚举字段的有效值
        enum_validations = [
            ("ownership_status", ["已确权", "未确权", "部分确权"], "确权状态字段"),
            ("usage_status", ["出租", "闲置", "自用", "公房", "其他"], "使用状态字段"),
            ("property_nature", ["经营类", "非经营类"], "物业性质字段")
        ]
        
        for field, valid_values, field_desc in enum_validations:
            if field in df.columns:
                try:
                    invalid_count = df.filter(~pl.col(field).is_in(valid_values)).height
                    if invalid_count > 0:
                        errors.append(f"{field_desc}有 {invalid_count} 行数据值无效")
                except Exception as e:
                    errors.append(f"验证枚举字段 {field} 时出错: {str(e)}")
        
        return errors
    
    @staticmethod
    def convert_to_asset_models(df: pl.DataFrame) -> List[AssetCreate]:
        """将DataFrame转换为AssetCreate模型列表"""
        assets = []
        
        for row in df.iter_rows(named=True):
            try:
                # 构建资产数据字典
                asset_data = {}
                
                # 映射所有字段
                for db_field, value in row.items():
                    if value is not None and value != "":
                        if db_field in ["current_contract_start_date", "current_contract_end_date", 
                                       "agreement_start_date", "agreement_end_date"]:
                            # 日期字段处理
                            if isinstance(value, str):
                                try:
                                    asset_data[db_field] = datetime.strptime(value, "%Y-%m-%d")
                                except:
                                    pass  # 忽略无效日期
                            elif hasattr(value, 'date'):
                                asset_data[db_field] = value
                        else:
                            asset_data[db_field] = value
                
                # 确保必填字段有默认值
                if "occupancy_rate" not in asset_data or not asset_data["occupancy_rate"]:
                    asset_data["occupancy_rate"] = "0%"
                
                if "ownership_status" not in asset_data:
                    asset_data["ownership_status"] = "未确权"
                
                if "usage_status" not in asset_data:
                    asset_data["usage_status"] = "其他"
                
                if "property_nature" not in asset_data:
                    asset_data["property_nature"] = "经营类"
                
                if "is_litigated" not in asset_data:
                    asset_data["is_litigated"] = "否"
                
                # 创建AssetCreate实例
                asset = AssetCreate(**asset_data)
                assets.append(asset)
                
            except Exception as e:
                logger.warning(f"转换行数据失败: {str(e)}, 数据: {row}")
                continue
        
        logger.info(f"成功转换 {len(assets)} 条资产数据")
        return assets


class ExcelImportService:
    """Excel导入服务"""
    
    def __init__(self):
        self.processor = AssetDataProcessor()
        self.asset_crud = CRUDAsset(Asset)
    
    async def import_assets_from_excel(
        self, 
        file_path: str, 
        sheet_name: str = "物业总表",
        db: Session = None
    ) -> Dict[str, Any]:
        """从Excel导入资产数据"""
        try:
            # 读取Excel文件
            df = self.processor.read_excel_file(file_path, sheet_name)
            
            # 数据清洗和转换
            df = self.processor.clean_and_transform_data(df)
            
            # 数据验证
            validation_errors = self.processor.validate_data(df)
            if validation_errors:
                return {
                    "success": 0,
                    "failed": len(df),
                    "total": len(df),
                    "errors": validation_errors
                }
            
            # 转换为资产模型
            assets = self.processor.convert_to_asset_models(df)
            
            if not assets:
                return {
                    "success": 0,
                    "failed": 0,
                    "total": len(df),
                    "errors": ["没有有效的资产数据可以导入"]
                }
            
            # 保存到数据库
            if db is None:
                db = next(get_db())
            
            success_count, failed_count, errors = await self._save_assets(assets, db)
            
            return {
                "success": success_count,
                "failed": failed_count,
                "total": len(assets),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Excel导入失败: {str(e)}")
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": [f"导入失败: {str(e)}"]
            }
    
    async def _save_assets(
        self, 
        assets: List[AssetCreate], 
        db: Session
    ) -> tuple[int, int, List[str]]:
        """保存资产到数据库"""
        success_count = 0
        failed_count = 0
        errors = []
        
        for i, asset in enumerate(assets):
            try:
                # 检查是否已存在相同名称的资产
                existing = self.asset_crud.get_by_name(db, property_name=asset.property_name)
                if existing:
                    errors.append(f"第{i+1}行: 物业名称 '{asset.property_name}' 已存在")
                    failed_count += 1
                    continue
                
                # 创建资产
                self.asset_crud.create(db, obj_in=asset)
                success_count += 1
                
            except Exception as e:
                error_msg = f"第{i+1}行: 保存失败 - {str(e)}"
                errors.append(error_msg)
                failed_count += 1
                logger.warning(error_msg)
        
        # 提交事务
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库提交失败: {str(e)}")
            return 0, len(assets), [f"数据库提交失败: {str(e)}"]
        
        logger.info(f"导入完成: 成功 {success_count}, 失败 {failed_count}")
        return success_count, failed_count, errors