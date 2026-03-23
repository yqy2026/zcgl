"""
Excel preview service.

Moves Excel parsing and preview logic out of the API layer.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd


class ExcelPreviewService:
    """Service for building Excel preview payloads."""

    @staticmethod
    def build_preview(
        content: bytes, max_rows: int
    ) -> tuple[int, list[str], list[dict[str, Any]]]:
        df = pd.read_excel(io.BytesIO(content))
        total = len(df)
        columns = df.columns.tolist()
        preview_rows = min(max_rows, total)
        preview_df = df.head(preview_rows)

        preview_data: list[dict[str, Any]] = []
        for _, row in preview_df.iterrows():
            row_dict: dict[str, Any] = {}
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

        return total, columns, preview_data

    @staticmethod
    def build_preview_advanced(
        content: bytes, max_rows: int
    ) -> tuple[int, list[str], list[dict[str, Any]], list[dict[str, Any]]]:
        total, columns, preview_data = ExcelPreviewService.build_preview(
            content, max_rows
        )

        detected_mapping: list[dict[str, Any]] = []
        field_mapping_rules: dict[str, list[str]] = {
            "物业名称": ["asset_name", "物业名称", "资产名称"],
            "地址": ["address", "物业地址", "地址", "位置"],
            "确权状态": ["ownership_status", "确权状态", "权属状态"],
            "物业性质": ["property_nature", "物业性质", "资产性质"],
            "使用状态": ["usage_status", "使用状态", "状态"],
            "权属方": ["ownership_entity", "权属方", "所有权人"],
            "权属方ID": ["ownership_id", "权属方ID", "权属方编号"],
            "土地面积": ["land_area", "土地面积", "占地面积"],
            "实际房产面积": ["actual_property_area", "实际房产面积", "建筑面积"],
            "可出租面积": ["rentable_area", "可出租面积", "出租面积"],
            "已出租面积": ["rented_area", "已出租面积", "已租面积"],
        }

        for col in columns:
            col_text = str(col).lower()
            for chinese_name, possible_names in field_mapping_rules.items():
                if any(name.lower() in col_text for name in possible_names):
                    detected_mapping.append(
                        {
                            "excel_column": col,
                            "system_field": possible_names[0],
                            "data_type": "string",
                            "required": chinese_name in ["物业名称", "地址"],
                            "confidence": 0.8,
                        }
                    )
                    break

        return total, columns, preview_data, detected_mapping
