from typing import Any
"""
Excel数据导出服务
使用Polars进行高性能数据处理和导�?
"""

import logging
import os
import tempfile
from datetime import datetime


import polars as pl
from sqlalchemy.orm import Session

from src.config.excel_config import STANDARD_SHEET_NAME
from src.crud.asset import CRUDAsset
from src.database import get_db
from src.models.asset import Asset
from src.schemas.asset import AssetSearchParams

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
        "land_area": "土地面积\n(平方米",
        "actual_property_area": "实际房产面积\n(平方米)",
        "rentable_area": "经营性物业可出租面积\n(平方米)",
        "rented_area": "经营性物业已出租面积\n(平方米)",
        "unrented_area": "经营性物业未出租面积\n(平方米)",
        "non_commercial_area": "非经营物业面积\n(平方米)",
        "ownership_status": "是否确权\n（已确权、未确权、部分确权）",
        "certificated_usage": "证载用途\n（商业、住宅、办公、厂房、车库等）",
        "actual_usage": "实际用途\n（商业、住宅、办公、厂房、车库等）",
        "business_category": "业态类别",
        "usage_status": "物业使用状态\n（出租、闲置、自用、公房、其他）",
        "is_litigated": "是否涉诉",
        "property_nature": "物业性质（经营类、非经营类）",
        "business_model": "经营模式",
        "include_in_occupancy_rate": "是否计入出租率统计",
        "occupancy_rate": "出租率(%)",
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
        "updated_at": "更新时间",
    }

    # 默认导出的列（按新顺序�?
    DEFAULT_EXPORT_COLUMNS = [
        "ownership_entity",
        "management_entity",
        "property_name",
        "address",
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "unrented_area",
        "non_commercial_area",
        "ownership_status",
        "certificated_usage",
        "actual_usage",
        "business_category",
        "usage_status",
        "is_litigated",
        "property_nature",
        "business_model",
        "include_in_occupancy_rate",
        "occupancy_rate",
        "lease_contract",
        "current_contract_start_date",
        "current_contract_end_date",
        "tenant_name",
        "ownership_category",
        "current_lease_contract",
        "wuyang_project_name",
        "agreement_start_date",
        "agreement_end_date",
        "current_terminal_contract",
        "description",
        "notes",
    ]

    @staticmethod
    def convert_assets_to_dataframe(
        assets: list[Asset], columns: list[str] | None = None
    ) -> pl.DataFrame:
        """将资产列表转换为Polars DataFrame"""
        try:
            if not assets:
                # 返回空的DataFrame，但包含列结�?
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

                    # 处理不同类型的数�?
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
        df: pl.DataFrame, include_headers: bool = True
    ) -> pl.DataFrame:
        """重命名列为Excel导出格式"""
        try:
            if not include_headers:
                return df

            # 创建重命名映�?
            rename_dict = {}
            for col in df.columns:
                if col in AssetDataExporter.FIELD_TO_COLUMN_MAPPING:
                    rename_dict[col] = AssetDataExporter.FIELD_TO_COLUMN_MAPPING[col]

            if rename_dict:
                df = df.rename(rename_dict)

            logger.info(f"重命名了 {len(rename_dict)} 个列")
            return df

        except Exception as e:
            logger.error(f"重命名列失败: {str(e)}")
            raise ExcelExportError(f"重命名列失败: {str(e)}")

    @staticmethod
    def export_to_excel(
        df: pl.DataFrame,
        file_path: str,
        sheet_name: str = STANDARD_SHEET_NAME,
        include_headers: bool = True,
    ) -> None:
        """导出DataFrame到Excel文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 导出到Excel
            df.write_excel(
                file_path, worksheet=sheet_name, include_header=include_headers
            )

            logger.info(f"成功导出 {len(df)} 行数据到 {file_path}")

        except Exception as e:
            logger.error(f"导出Excel文件失败: {str(e)}")
            raise ExcelExportError(f"导出Excel文件失败: {str(e)}")

    @staticmethod
    def calculate_export_stats(df: pl.DataFrame) -> dict[str, Any]:
        """计算导出统计信息"""
        try:
            stats = {
                "total_records": len(df),
                "total_columns": len(df.columns),
                "export_time": datetime.now().isoformat(),
            }

            # 如果有面积数据，计算统计
            if "actual_property_area" in df.columns:
                area_stats = df.select(
                    [
                        pl.col("actual_property_area").sum().alias("total_area"),
                        pl.col("actual_property_area").mean().alias("avg_area"),
                        pl.col("actual_property_area").max().alias("max_area"),
                        pl.col("actual_property_area").min().alias("min_area"),
                    ]
                ).to_dicts()[0]

                stats.update(
                    {
                        "total_area": round(area_stats["total_area"] or 0, 2),
                        "avg_area": round(area_stats["avg_area"] or 0, 2),
                        "max_area": area_stats["max_area"] or 0,
                        "min_area": area_stats["min_area"] or 0,
                    }
                )

            # 统计各种状态的分布
            if "ownership_status" in df.columns:
                ownership_counts = df.group_by("ownership_status").len().to_dicts()
                stats["ownership_distribution"] = {
                    item["ownership_status"]: item["len"] for item in ownership_counts
                }

            if "property_nature" in df.columns:
                nature_counts = df.group_by("property_nature").len().to_dicts()
                stats["nature_distribution"] = {
                    item["property_nature"]: item["len"] for item in nature_counts
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
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        format: str = "xlsx",
        include_headers: bool = True,
        db: Session | None = None,
    ) -> dict[str, Any]:
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
                    "stats": {"total_records": 0},
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
                sheet_name=STANDARD_SHEET_NAME,
                include_headers=include_headers,
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
                "stats": stats,
            }

        except Exception as e:
            logger.error(f"Excel导出失败: {str(e)}")
            return {
                "success": False,
                "message": f"导出失败: {str(e)}",
                "file_path": None,
                "stats": {"total_records": 0},
            }

    async def _get_filtered_assets(
        self, filters: dict[str, Any] | None, db: Session
    ) -> list[Asset]:
        """根据筛选条件获取资产数据"""
        try:
            if not filters:
                # 获取所有资�?
                return self.asset_crud.get_multi(db, limit=10000)  # 限制最大导出数�?

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

            # 构建筛选条�?
            filter_dict = {}
            if search_params.ownership_status:
                filter_dict["ownership_status"] = search_params.ownership_status
            if search_params.property_nature:
                filter_dict["property_nature"] = search_params.property_nature
            if search_params.usage_status:
                filter_dict["usage_status"] = search_params.usage_status
            if search_params.ownership_entity:
                filter_dict["ownership_entity"] = search_params.ownership_entity

            # 使用现有的搜索功�?
            assets = self.asset_crud.get_multi_with_search(
                db=db,
                search=search_params.search,
                filters=filter_dict if filter_dict else None,
                skip=0,
                limit=10000,  # 导出时不分页，但限制最大数�?
                sort_field=search_params.sort_field,
                sort_order=search_params.sort_order,
            )

            return assets

        except Exception as e:
            logger.error(f"获取筛选资产数据失�? {str(e)}")
            raise ExcelExportError(f"获取筛选资产数据失�? {str(e)}")

    async def get_export_template_info(self) -> dict[str, Any]:
        """获取导出模板信息"""
        return {
            "available_columns": list(AssetDataExporter.FIELD_TO_COLUMN_MAPPING.keys()),
            "column_descriptions": AssetDataExporter.FIELD_TO_COLUMN_MAPPING,
            "default_columns": AssetDataExporter.DEFAULT_EXPORT_COLUMNS,
            "supported_formats": ["xlsx", "xls", "csv"],
            "max_export_records": 10000,
            "export_options": {
                "include_headers": "是否包含表头",
                "format": "导出格式(xlsx/xls/csv)",
                "columns": "要导出的列(留空则导出所有默认列)",
            },
        }

    def cleanup_export_file(self, file_path: str) -> bool:
        """清理导出文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"已清理导出文�? {file_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"清理导出文件失败: {str(e)}")
            return False


def export_statistics_report(
    overview_data: dict[str, Any],
    ownership_data: list[dict[str, Any]],
    asset_data: list[dict[str, Any]],
    monthly_data: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
) -> bytes:
    """导出统计数据报表"""
    try:
        import io

        import xlsxwriter

        # 创建内存中的Excel文件
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # 设置格式
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#4F81BD",
                "font_color": "white",
                "border": 1,
                "align": "center",
            }
        )

        title_format = workbook.add_format(
            {"bold": True, "font_size": 16, "align": "center"}
        )

        currency_format = workbook.add_format({"num_format": "¥#,##0.00"})
        percentage_format = workbook.add_format({"num_format": "0.0%"})

        # 1. 概览数据工作表
        overview_sheet = workbook.add_worksheet("统计概览")
        overview_sheet.write(0, 0, "租金统计报表", title_format)
        overview_sheet.merge_range(0, 0, 0, 3, "租金统计报表", title_format)

        if start_date and end_date:
            overview_sheet.write(1, 0, f"统计期间: {start_date} 至 {end_date}")
            overview_sheet.merge_range(
                1, 0, 1, 3, f"统计期间: {start_date} 至 {end_date}"
            )

        # 概览统计
        overview_data_list = [
            ["指标", "数值"],
            ["应收总额", overview_data.get("total_due_amount", 0)],
            ["已收总额", overview_data.get("total_paid_amount", 0)],
            ["欠款总额", overview_data.get("total_overdue_amount", 0)],
            ["收缴率", overview_data.get("payment_rate", 0) / 100],
            ["总台账数", overview_data.get("total_records", 0)],
        ]

        for row_idx, row in enumerate(overview_data_list, start=3):
            for col_idx, value in enumerate(row):
                if row_idx == 3:  # 表头
                    overview_sheet.write(row_idx, col_idx, value, header_format)
                elif col_idx == 1 and row_idx in [4, 5, 6]:  # 金额
                    overview_sheet.write(row_idx, col_idx, value, currency_format)
                elif col_idx == 1 and row_idx == 7:  # 百分比
                    overview_sheet.write(row_idx, col_idx, value, percentage_format)
                else:
                    overview_sheet.write(row_idx, col_idx, value)

        # 2. 权属方统计工作表
        ownership_sheet = workbook.add_worksheet("权属方统计")
        ownership_headers = [
            "权属方名称",
            "简称",
            "合同数量",
            "应收总额",
            "已收总额",
            "欠款总额",
            "收缴率",
        ]

        for col_idx, header in enumerate(ownership_headers):
            ownership_sheet.write(0, col_idx, header, header_format)

        for row_idx, record in enumerate(ownership_data, start=1):
            ownership_sheet.write(row_idx, 0, record.get("ownership_name", ""))
            ownership_sheet.write(row_idx, 1, record.get("ownership_short_name", ""))
            ownership_sheet.write(row_idx, 2, record.get("contract_count", 0))
            ownership_sheet.write(
                row_idx, 3, record.get("total_due_amount", 0), currency_format
            )
            ownership_sheet.write(
                row_idx, 4, record.get("total_paid_amount", 0), currency_format
            )
            ownership_sheet.write(
                row_idx, 5, record.get("total_overdue_amount", 0), currency_format
            )
            ownership_sheet.write(
                row_idx, 6, record.get("payment_rate", 0) / 100, percentage_format
            )

        # 3. 资产统计工作表
        asset_sheet = workbook.add_worksheet("资产统计")
        asset_headers = [
            "资产名称",
            "地址",
            "合同数量",
            "应收总额",
            "已收总额",
            "欠款总额",
            "收缴率",
        ]

        for col_idx, header in enumerate(asset_headers):
            asset_sheet.write(0, col_idx, header, header_format)

        for row_idx, record in enumerate(asset_data, start=1):
            asset_sheet.write(row_idx, 0, record.get("asset_name", ""))
            asset_sheet.write(row_idx, 1, record.get("asset_address", ""))
            asset_sheet.write(row_idx, 2, record.get("contract_count", 0))
            asset_sheet.write(
                row_idx, 3, record.get("total_due_amount", 0), currency_format
            )
            asset_sheet.write(
                row_idx, 4, record.get("total_paid_amount", 0), currency_format
            )
            asset_sheet.write(
                row_idx, 5, record.get("total_overdue_amount", 0), currency_format
            )
            asset_sheet.write(
                row_idx, 6, record.get("payment_rate", 0) / 100, percentage_format
            )

        # 4. 月度统计工作表
        monthly_sheet = workbook.add_worksheet("月度统计")
        monthly_headers = [
            "年月",
            "合同数",
            "应收总额",
            "已收总额",
            "欠款总额",
            "收缴率",
        ]

        for col_idx, header in enumerate(monthly_headers):
            monthly_sheet.write(0, col_idx, header, header_format)

        for row_idx, record in enumerate(monthly_data, start=1):
            monthly_sheet.write(row_idx, 0, record.get("year_month", ""))
            monthly_sheet.write(row_idx, 1, record.get("total_contracts", 0))
            monthly_sheet.write(
                row_idx, 2, record.get("total_due_amount", 0), currency_format
            )
            monthly_sheet.write(
                row_idx, 3, record.get("total_paid_amount", 0), currency_format
            )
            monthly_sheet.write(
                row_idx, 4, record.get("total_overdue_amount", 0), currency_format
            )
            monthly_sheet.write(
                row_idx, 5, record.get("payment_rate", 0) / 100, percentage_format
            )

        # 设置列宽
        for sheet in [overview_sheet, ownership_sheet, asset_sheet, monthly_sheet]:
            sheet.set_column(0, 0, 20)  # 第一列
            sheet.set_column(1, 1, 15)  # 第二列
            sheet.set_column(2, 5, 12)  # 数据列

        workbook.close()
        output.seek(0)

        return output.read()

    except Exception as e:
        logger.error(f"导出统计报表失败: {str(e)}")
        raise ExcelExportError(f"导出统计报表失败: {str(e)}")
