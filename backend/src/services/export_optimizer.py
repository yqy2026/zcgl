from typing import Any
"""
数据导出优化服务
提供高性能的数据导出功能，使用分页查询和批量处理
"""

import csv
import io
import logging
from collections.abc import Iterator
from datetime import datetime


from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ExportOptimizer:
    """数据导出优化器"""

    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size

    def export_assets_to_csv_optimized(
        self,
        db: Session,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        progress_callback: callable | None = None,
    ) -> Iterator[str]:
        """
        优化的CSV导出功能，使用流式处理减少内存占用

        Args:
            db: 数据库会话
            columns: 导出列
            filters: 过滤条件
            progress_callback: 进度回调函数

        Yields:
            CSV数据块
        """
        # 默认导出字段
        default_columns = [
            "property_name",
            "address",
            "ownership_entity",
            "ownership_status",
            "property_nature",
            "usage_status",
            "actual_property_area",
            "rentable_area",
            "rented_area",
            "annual_income",
            "annual_expense",
            "tenant_name",
            "contract_start_date",
            "contract_end_date",
        ]

        export_columns = columns or default_columns

        # 构建SQL查询
        query = self._build_optimized_query(export_columns, filters)

        # 获取总记录数
        total_count = self._get_total_count(db, filters)

        if progress_callback:
            progress_callback(5, "开始查询数据")

        # 分批处理数据
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_columns)
        writer.writeheader()

        # 生成CSV头部
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        processed = 0
        batch_num = 0

        for batch_data in self._batch_query(db, query, export_columns):
            batch_num += 1

            # 处理当前批次
            for row in batch_data:
                # 数据类型转换
                processed_row = {}
                for col in export_columns:
                    value = row.get(col, "")
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d")
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    elif value is None:
                        value = ""
                    processed_row[col] = value

                writer.writerow(processed_row)

                # 每处理100行输出一次
                if processed % 100 == 0:
                    chunk = output.getvalue()
                    if chunk:
                        yield chunk
                        output.seek(0)
                        output.truncate(0)

                processed += 1

            # 更新进度
            if progress_callback:
                progress = min(5 + int((processed / total_count) * 85), 90)
                progress_callback(progress, f"已处理 {processed}/{total_count} 条记录")

            # 输出当前批次剩余数据
            chunk = output.getvalue()
            if chunk:
                yield chunk
                output.seek(0)
                output.truncate(0)

        output.close()

        if progress_callback:
            progress_callback(100, "导出完成")

    def export_assets_to_json_optimized(
        self,
        db: Session,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        progress_callback: callable | None = None,
    ) -> list[dict[str, Any]]:
        """
        优化的JSON导出功能

        Args:
            db: 数据库会话
            columns: 导出列
            filters: 过滤条件
            progress_callback: 进度回调函数

        Returns:
            JSON数据列表
        """
        default_columns = [
            "property_name",
            "address",
            "ownership_entity",
            "ownership_status",
            "property_nature",
            "usage_status",
            "actual_property_area",
            "rentable_area",
            "rented_area",
            "annual_income",
            "annual_expense",
            "tenant_name",
            "contract_start_date",
            "contract_end_date",
        ]

        export_columns = columns or default_columns

        # 构建SQL查询
        query = self._build_optimized_query(export_columns, filters)

        # 获取总记录数
        total_count = self._get_total_count(db, filters)

        if progress_callback:
            progress_callback(5, "开始查询数据")

        # 分批处理数据
        result = []
        processed = 0

        for batch_data in self._batch_query(db, query, export_columns):
            # 处理当前批次
            for row in batch_data:
                # 数据类型转换
                processed_row = {}
                for col in export_columns:
                    value = row.get(col, "")
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d")
                    elif isinstance(value, (int, float)):
                        value = value
                    elif value is None:
                        value = None
                    processed_row[col] = value

                result.append(processed_row)
                processed += 1

            # 更新进度
            if progress_callback:
                progress = min(5 + int((processed / total_count) * 90), 95)
                progress_callback(progress, f"已处理 {processed}/{total_count} 条记录")

        if progress_callback:
            progress_callback(100, "导出完成")

        return result

    def _build_optimized_query(
        self, columns: list[str], filters: dict[str, Any] | None = None
    ) -> str:
        """构建优化的SQL查询"""

        # 构建SELECT子句
        select_clause = ", ".join([f"assets.{col}" for col in columns])

        # 构建WHERE子句
        where_conditions = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    # IN查询
                    placeholders = ", ".join([f"'{v}'" for v in value])
                    where_conditions.append(f"assets.{key} IN ({placeholders})")
                elif isinstance(value, str):
                    where_conditions.append(f"assets.{key} = '{value}'")
                elif isinstance(value, bool):
                    where_conditions.append(f"assets.{key} = {value}")
                elif isinstance(value, (int, float)):
                    where_conditions.append(f"assets.{key} = {value}")

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # 构建完整查询
        query = f"""
        SELECT {select_clause}
        FROM assets
        {where_clause}
        ORDER BY assets.created_at DESC
        """

        return query

    def _get_total_count(
        self, db: Session, filters: dict[str, Any] | None = None
    ) -> int:
        """获取总记录数"""
        where_conditions = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    placeholders = ", ".join([f"'{v}'" for v in value])
                    where_conditions.append(f"assets.{key} IN ({placeholders})")
                elif isinstance(value, str):
                    where_conditions.append(f"assets.{key} = '{value}'")
                elif isinstance(value, bool):
                    where_conditions.append(f"assets.{key} = {value}")
                elif isinstance(value, (int, float)):
                    where_conditions.append(f"assets.{key} = {value}")

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        query = f"SELECT COUNT(*) FROM assets {where_clause}"
        result = db.execute(text(query)).scalar()
        return result or 0

    def _batch_query(
        self, db: Session, query: str, columns: list[str], offset: int = 0
    ) -> Iterator[list[dict[str, Any]]]:
        """分批查询数据"""

        while True:
            # 添加LIMIT和OFFSET
            batch_query = f"{query} LIMIT {self.batch_size} OFFSET {offset}"

            try:
                result = db.execute(text(batch_query))
                rows = result.fetchall()

                if not rows:
                    break

                # 转换为字典列表
                batch_data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    batch_data.append(row_dict)

                yield batch_data

                if len(rows) < self.batch_size:
                    break

                offset += self.batch_size

            except Exception as e:
                logger.error(f"查询批次数据时出错: {e}")
                break


# 全局导出优化器实例
export_optimizer = ExportOptimizer(batch_size=1000)
