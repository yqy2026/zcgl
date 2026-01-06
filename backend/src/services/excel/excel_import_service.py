"""
Excel导入服务

提供从Excel文件导入资产数据的功能
"""

import logging
import os
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from ...config.excel_config import STANDARD_SHEET_NAME
from ...core.exception_handler import BusinessValidationError
from ...crud.asset import asset_crud
from ...schemas.asset import AssetCreate
from ..asset.validators import AssetBatchValidator

logger = logging.getLogger(__name__)


# 字段映射：Excel中文列名 -> 数据库字段名
FIELD_MAPPING = {
    "权属方": "ownership_entity",
    "权属类别": "ownership_category",
    "项目名称": "project_name",
    "物业名称": "property_name",
    "物业地址": "address",
    "土地面积(平方米)": "land_area",
    "实际房产面积(平方米)": "actual_property_area",
    "非经营物业面积(平方米)": "non_commercial_area",
    "可出租面积(平方米)": "rentable_area",
    "已出租面积(平方米)": "rented_area",
    "确权状态（已确权、未确权、部分确权）": "ownership_status",
    "证载用途（商业、住宅、办公、厂房、车库等）": "certificate_usage",
    "实际用途（商业、住宅、办公、厂房、车库等）": "actual_usage",
    "业态类别": "business_category",
    "使用状态（出租、闲置、自用、公房、其他）": "usage_status",
    "是否涉诉": "is_litigated",
    "物业性质（经营类、非经营类）": "property_nature",
    "是否计入出租率": "include_in_occupancy_rate",
    "接收模式": "reception_mode",
    "(当前)接收协议开始日期": "operation_agreement_start_date",
    "(当前)接收协议结束日期": "operation_agreement_end_date",
}


class ExcelImportService:
    """
    Excel导入服务

    负责将Excel文件中的资产数据导入到数据库
    """

    def __init__(self, db: Session | None = None):
        """
        初始化导入服务

        Args:
            db: 数据库会话（可选，用于同步导入）
        """
        self.db = db
        self.validator = AssetBatchValidator()

    async def import_assets_from_excel(
        self,
        file_path: str,
        sheet_name: str = STANDARD_SHEET_NAME,
        validate_data: bool = True,
        create_assets: bool = True,
        update_existing: bool = False,
        skip_errors: bool = False,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        从Excel文件导入资产数据

        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称
            validate_data: 是否验证数据
            create_assets: 是否创建资产
            update_existing: 是否更新已存在的资产
            skip_errors: 是否跳过错误行
            batch_size: 批处理大小

        Returns:
            导入结果字典
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            if df.empty:
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "created_assets": 0,
                    "updated_assets": 0,
                    "errors": [],
                    "warnings": [],
                }

            total_rows = len(df)
            results = {
                "total": total_rows,
                "success": 0,
                "failed": 0,
                "created_assets": 0,
                "updated_assets": 0,
                "errors": [],
                "warnings": [],
            }

            # 处理每一行数据
            for idx, row in df.iterrows():
                try:
                    # 转换Excel列为数据库字段
                    asset_data = self._map_excel_row_to_asset_data(row, idx + 1)

                    # 验证数据
                    if validate_data:
                        (
                            is_valid,
                            errors,
                            warnings,
                            validated_fields,
                        ) = self.validator.validate_all(asset_data)

                        if not is_valid:
                            results["errors"].append(
                                {
                                    "row": idx + 2,  # Excel行号（包含表头）
                                    "error": "; ".join(
                                        [f"{e['field']}: {e['error']}" for e in errors]
                                    ),
                                }
                            )
                            results["failed"] += 1
                            if not skip_errors:
                                raise BusinessValidationError(
                                    f"第{idx + 2}行数据验证失败"
                                )
                            continue

                        results["warnings"].extend(
                            [{**w, "row": idx + 2} for w in warnings if "row" not in w]
                        )

                    # 创建资产
                    if create_assets and self.db:
                        # 检查是否已存在（根据物业名称和地址）
                        existing_asset = self._find_existing_asset(asset_data)

                        if existing_asset and update_existing:
                            # 更新现有资产
                            from ...schemas.asset import AssetUpdate

                            update_schema = AssetUpdate(**asset_data)
                            asset_crud.update(
                                db=self.db,
                                db_obj=existing_asset,
                                obj_in=update_schema,
                            )
                            results["updated_assets"] += 1
                        elif not existing_asset:
                            # 创建新资产
                            create_schema = AssetCreate(**asset_data)
                            asset_crud.create(db=self.db, obj_in=create_schema)
                            results["created_assets"] += 1
                        else:
                            results["warnings"].append(
                                {
                                    "row": idx + 2,
                                    "warning": "资产已存在，跳过创建",
                                }
                            )

                    results["success"] += 1

                except Exception as e:
                    results["errors"].append({"row": idx + 2, "error": str(e)})
                    results["failed"] += 1

                    if not skip_errors:
                        raise

            # 提交事务
            if create_assets and self.db:
                self.db.commit()

            logger.info(
                f"Excel导入完成: 总行数={total_rows}, "
                f"成功={results['success']}, 失败={results['failed']}, "
                f"创建={results['created_assets']}, 更新={results['updated_assets']}"
            )

            return results

        except Exception as e:
            if self.db:
                self.db.rollback()
            logger.error(f"Excel导入失败: {str(e)}")
            raise

    def _map_excel_row_to_asset_data(
        self, row: pd.Series, row_num: int
    ) -> dict[str, Any]:
        """
        将Excel行数据映射为资产数据字典

        Args:
            row: pandas Series，表示Excel的一行
            row_num: 行号（用于错误报告）

        Returns:
            资产数据字典
        """
        asset_data = {}

        for excel_col, db_field in FIELD_MAPPING.items():
            if excel_col in row and pd.notna(row[excel_col]):
                value = row[excel_col]

                # 特殊处理布尔字段
                if db_field == "is_litigated":
                    value = str(value).strip() in ["是", "True", "true", "1", "yes"]
                elif db_field == "include_in_occupancy_rate":
                    value = str(value).strip() in ["是", "True", "true", "1", "yes"]
                # 处理数值字段
                elif db_field in [
                    "land_area",
                    "actual_property_area",
                    "non_commercial_area",
                    "rentable_area",
                    "rented_area",
                ]:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = None
                # 处理日期字段
                elif db_field in [
                    "operation_agreement_start_date",
                    "operation_agreement_end_date",
                ]:
                    if isinstance(value, datetime):
                        value = value.date()
                    elif isinstance(value, str):
                        try:
                            value = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            value = None

                asset_data[db_field] = value

        return asset_data

    def _find_existing_asset(self, asset_data: dict[str, Any]) -> Any | None:
        """
        根据物业名称和地址查找已存在的资产

        Args:
            asset_data: 资产数据

        Returns:
            已存在的资产对象，如果不存在则返回None
        """
        if not self.db:
            return None

        try:
            # 使用物业名称和地址作为唯一标识
            filters = {
                "property_name": asset_data.get("property_name"),
                "address": asset_data.get("address"),
            }

            assets, _ = asset_crud.get_multi_with_search(
                db=self.db, filters=filters, limit=1
            )

            return assets[0] if assets else None

        except Exception as e:
            logger.warning(f"查找现有资产失败: {str(e)}")
            return None

    def validate_excel_file(
        self, file_path: str, sheet_name: str = STANDARD_SHEET_NAME
    ) -> dict[str, Any]:
        """
        验证Excel文件的格式和内容

        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称

        Returns:
            验证结果
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    "valid": False,
                    "errors": [f"文件不存在: {file_path}"],
                }

            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # 检查是否有数据
            if df.empty:
                return {
                    "valid": False,
                    "errors": ["Excel文件没有数据"],
                }

            # 检查必需列
            required_columns = ["物业名称", "物业地址"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                return {
                    "valid": False,
                    "errors": [f"缺少必需列: {', '.join(missing_columns)}"],
                    "found_columns": list(df.columns),
                }

            return {
                "valid": True,
                "total_rows": len(df),
                "columns": list(df.columns),
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"验证失败: {str(e)}"],
            }

    async def preview_excel_file(
        self,
        file_path: str,
        max_rows: int = 10,
        sheet_name: str = STANDARD_SHEET_NAME,
    ) -> dict[str, Any]:
        """
        预览Excel文件内容

        Args:
            file_path: Excel文件路径
            max_rows: 预览的最大行数
            sheet_name: 工作表名称

        Returns:
            预览数据
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            total = len(df)
            columns = df.columns.tolist()

            # 限制预览行数
            preview_rows = min(max_rows, total)
            preview_df = df.head(preview_rows)

            # 转换为字典格式，处理NaN值
            preview_data = []
            for _, row in preview_df.iterrows():
                row_dict = {}
                for col in columns:
                    value = row[col]
                    if pd.isna(value):
                        row_dict[col] = None
                    else:
                        row_dict[col] = (
                            str(value)
                            if not isinstance(value, (str, int, float))
                            else value
                        )
                preview_data.append(row_dict)

            return {
                "total_rows": total,
                "columns": columns,
                "preview_rows": preview_rows,
                "preview_data": preview_data,
            }

        except Exception as e:
            raise BusinessValidationError(f"预览Excel文件失败: {str(e)}")
