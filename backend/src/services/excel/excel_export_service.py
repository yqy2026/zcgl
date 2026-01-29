"""
Excel导出服务

提供将资产数据导出为Excel文件的功能
"""

import io
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from ...config.excel_config import STANDARD_SHEET_NAME
from ...crud.asset import asset_crud

logger = logging.getLogger(__name__)


# 反向字段映射：数据库字段名 -> Excel中文列名
EXPORT_FIELD_MAPPING = {
    "ownership_entity": "权属方",
    "ownership_category": "权属类别",
    "project_name": "项目名称",
    "property_name": "物业名称",
    "address": "物业地址",
    "land_area": "土地面积(平方米)",
    "actual_property_area": "实际房产面积(平方米)",
    "non_commercial_area": "非经营物业面积(平方米)",
    "rentable_area": "可出租面积(平方米)",
    "rented_area": "已出租面积(平方米)",
    "ownership_status": "确权状态",
    "property_nature": "物业性质",
    "usage_status": "使用状态",
    "business_category": "业态类别",
    "is_litigated": "是否涉诉",
    "notes": "备注",
    "created_at": "创建时间",
    "updated_at": "更新时间",
}


class ExcelExportService:
    """
    Excel导出服务

    负责将资产数据导出为Excel文件
    """

    def __init__(self, db: Session):
        """
        初始化导出服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def export_assets_to_excel(
        self,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        asset_ids: list[str] | None = None,
        fields: list[str] | None = None,
        sheet_name: str = STANDARD_SHEET_NAME,
        date_format: str = "%Y-%m-%d %H:%M:%S",
        limit: int = 5000,
    ) -> io.BytesIO:
        """
        导出资产数据到Excel文件（内存）

        Args:
            filters: 筛选条件
            search: 搜索关键词
            asset_ids: 资产ID列表
            fields: 要导出的字段列表
            sheet_name: 工作表名称
            date_format: 日期格式
            limit: 最大导出数量

        Returns:
            BytesIO缓冲区，包含Excel文件数据
        """
        try:
            # 构建筛选条件
            export_filters = filters or {}

            # 如果指定了资产ID，添加到筛选条件中
            if asset_ids:
                export_filters["ids"] = asset_ids

            # 从数据库获取资产数据
            assets, total = asset_crud.get_multi_with_search(
                db=self.db,
                search=search,
                filters=export_filters,
                limit=limit,
            )

            logger.info(f"准备导出 {total} 个资产")

            # 转换为导出格式
            export_data = self._convert_assets_to_export_format(
                assets, fields, date_format
            )

            # 如果没有数据，提供提示数据
            if not export_data:
                export_data = self._get_empty_export_data(fields)

            # 创建DataFrame
            df = pd.DataFrame(export_data)

            # 写入Excel文件（内存）
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # 设置列宽
                self._set_column_widths(writer.sheets[sheet_name])

            buffer.seek(0)

            logger.info(f"成功导出 {len(export_data)} 条资产数据到内存")
            return buffer

        except Exception as e:
            logger.error(f"导出Excel文件失败: {str(e)}")
            raise

    def export_analytics_to_excel(self, analytics_data: dict[str, Any]) -> io.BytesIO:
        try:
            rows: list[dict[str, Any]] = []
            for key, value in analytics_data.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    rows.append({"metric": key, "value": value})
                else:
                    rows.append(
                        {
                            "metric": key,
                            "value": json.dumps(value, ensure_ascii=False),
                        }
                    )

            if not rows:
                rows = [
                    {
                        "metric": "data",
                        "value": json.dumps(analytics_data, ensure_ascii=False),
                    }
                ]

            df = pd.DataFrame(rows)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="analytics", index=False)
                self._set_column_widths(writer.sheets["analytics"])

            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"导出分析Excel文件失败: {str(e)}")
            raise

    def export_assets_to_file(
        self,
        file_path: str,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        asset_ids: list[str] | None = None,
        fields: list[str] | None = None,
        sheet_name: str = STANDARD_SHEET_NAME,
        date_format: str = "%Y-%m-%d %H:%M:%S",
        limit: int = 5000,
    ) -> dict[str, Any]:
        """
        导出资产数据到Excel文件（磁盘）

        Args:
            file_path: 导出文件路径
            filters: 筛选条件
            search: 搜索关键词
            asset_ids: 资产ID列表
            fields: 要导出的字段列表
            sheet_name: 工作表名称
            date_format: 日期格式
            limit: 最大导出数量

        Returns:
            导出结果信息
        """
        try:
            # 获取内存中的Excel数据
            buffer = self.export_assets_to_excel(
                filters=filters,
                search=search,
                asset_ids=asset_ids,
                fields=fields,
                sheet_name=sheet_name,
                date_format=date_format,
                limit=limit,
            )

            # 写入文件
            with open(file_path, "wb") as f:
                f.write(buffer.read())

            file_size = os.path.getsize(file_path)

            logger.info(f"成功导出到文件: {file_path} (大小: {file_size} 字节)")

            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": file_size,
                "export_time": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"导出到文件失败: {str(e)}")
            raise

    def _convert_assets_to_export_format(
        self,
        assets: list[Any],
        fields: list[str] | None = None,
        date_format: str = "%Y-%m-%d %H:%M:%S",
    ) -> list[dict[str, Any]]:
        """
        将资产对象转换为导出格式

        Args:
            assets: 资产对象列表
            fields: 要导出的字段列表（None表示导出所有字段）
            date_format: 日期格式

        Returns:
            导出数据列表
        """
        export_data = []

        for asset in assets:
            row_data = {}

            for db_field, excel_header in EXPORT_FIELD_MAPPING.items():
                # 如果指定了字段列表，只导出指定字段
                if fields and db_field not in fields:
                    continue

                value = getattr(asset, db_field, None)

                # 特殊处理布尔字段
                if db_field == "is_litigated":
                    value = "是" if value else "否"
                # 处理日期字段
                elif db_field in ["created_at", "updated_at"] and value:
                    value = value.strftime(date_format)
                # 处理数值字段（保留2位小数）
                elif (
                    db_field
                    in [
                        "land_area",
                        "actual_property_area",
                        "non_commercial_area",
                        "rentable_area",
                        "rented_area",
                    ]
                    and value is not None
                ):
                    value = float(value)
                # 处理None值
                elif value is None:
                    value = ""

                row_data[excel_header] = value

            export_data.append(row_data)

        return export_data

    def _get_empty_export_data(
        self, fields: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        获取空数据的导出格式（提示信息）

        Args:
            fields: 要导出的字段列表

        Returns:
            空数据列表
        """
        # 根据字段列表生成列名
        if fields:
            columns = [
                EXPORT_FIELD_MAPPING.get(f, f)
                for f in fields
                if f in EXPORT_FIELD_MAPPING
            ]
        else:
            columns = list(EXPORT_FIELD_MAPPING.values())

        # 创建提示行
        empty_row = {col: "" for col in columns}
        if columns:
            empty_row[columns[0]] = "暂无数据"

        return [empty_row]

    def _set_column_widths(self, worksheet: Any) -> None:
        """
        设置Excel工作表列宽

        Args:
            worksheet: openpyxl工作表对象
        """
        column_widths = {
            "A": 20,  # 权属方
            "B": 15,  # 权属类别
            "C": 20,  # 项目名称
            "D": 20,  # 物业名称
            "E": 30,  # 物业地址
            "F": 18,  # 土地面积
            "G": 18,  # 实际房产面积
            "H": 20,  # 非经营物业面积
            "I": 18,  # 可出租面积
            "J": 18,  # 已出租面积
            "K": 15,  # 确权状态
            "L": 15,  # 物业性质
            "M": 15,  # 使用状态
            "N": 15,  # 业态类别
            "O": 12,  # 是否涉诉
            "P": 30,  # 备注
            "Q": 20,  # 创建时间
            "R": 20,  # 更新时间
        }

        for col, width in column_widths.items():
            if col in worksheet.column_dimensions:
                worksheet.column_dimensions[col].width = width

    def get_export_preview(
        self,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        asset_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        获取导出预览信息

        Args:
            filters: 筛选条件
            search: 搜索关键词
            asset_ids: 资产ID列表

        Returns:
            预览信息
        """
        try:
            export_filters = filters or {}

            if asset_ids:
                export_filters["ids"] = asset_ids

            assets, total = asset_crud.get_multi_with_search(
                db=self.db,
                search=search,
                filters=export_filters,
                limit=1,  # 只获取一条用于预览
            )

            if not assets:
                return {
                    "total_count": 0,
                    "sample_columns": list(EXPORT_FIELD_MAPPING.values()),
                    "sample_data": None,
                }

            # 转换第一条数据作为示例
            sample_data = self._convert_assets_to_export_format(assets)

            return {
                "total_count": total,
                "sample_columns": list(sample_data[0].keys()) if sample_data else [],
                "sample_data": sample_data[0] if sample_data else None,
            }

        except Exception as e:
            logger.error(f"获取导出预览失败: {str(e)}")
            raise
