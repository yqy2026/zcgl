"""
分析导出映射服务

将综合分析结果转换为稳定的表格行，供 CSV/XLSX 统一复用。
"""

import csv
import io
from typing import Any


class AnalyticsExportService:
    """分析导出映射服务。"""

    _SUMMARY_SECTION = "总览"
    _SUMMARY_METRICS: tuple[tuple[str, tuple[str, ...], str], ...] = (
        ("资产总数", ("total_assets", "area_summary.total_assets"), "项"),
        ("总面积", ("area_summary.total_area",), "平方米"),
        ("可出租面积", ("area_summary.total_rentable_area",), "平方米"),
        ("出租率", ("area_summary.occupancy_rate", "occupancy_rate.overall_rate"), "%"),
        ("年度收入", ("financial_summary.total_annual_income",), "元"),
        ("总收入（经营口径）", ("total_income",), "元"),
        ("自营租金收入", ("self_operated_rent_income",), "元"),
        ("代理服务费收入", ("agency_service_income",), "元"),
        ("客户主体数", ("customer_entity_count",), "个"),
        ("客户合同数", ("customer_contract_count",), "份"),
        ("口径版本", ("metrics_version",), ""),
    )
    _DISTRIBUTION_SECTIONS: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...], str], ...] = (
        (
            "property_nature_distribution",
            "物业性质分布",
            ("name", "nature", "label"),
            ("count", "value"),
            "项",
        ),
        (
            "ownership_status_distribution",
            "权属状态分布",
            ("status", "name", "label"),
            ("count", "value"),
            "项",
        ),
        (
            "usage_status_distribution",
            "使用状态分布",
            ("status", "name", "label"),
            ("count", "value"),
            "项",
        ),
        (
            "business_category_distribution",
            "业态分布",
            ("category", "name", "label"),
            ("count", "value"),
            "项",
        ),
        (
            "occupancy_distribution",
            "出租率分布",
            ("range", "name", "label"),
            ("count", "value"),
            "项",
        ),
        (
            "property_nature_area_distribution",
            "物业性质面积分布",
            ("name", "nature", "label"),
            ("total_area", "value"),
            "平方米",
        ),
        (
            "ownership_status_area_distribution",
            "权属状态面积分布",
            ("status", "name", "label"),
            ("total_area", "value"),
            "平方米",
        ),
        (
            "usage_status_area_distribution",
            "使用状态面积分布",
            ("status", "name", "label"),
            ("total_area", "value"),
            "平方米",
        ),
        (
            "business_category_area_distribution",
            "业态面积分布",
            ("category", "name", "label"),
            ("total_area", "value", "count"),
            "平方米",
        ),
    )
    _CUSTOMER_BREAKDOWN_SECTION = "客户统计拆分"
    _CUSTOMER_BREAKDOWN_LABELS: tuple[tuple[str, str], ...] = (
        ("upstream_lease", "上游承租"),
        ("downstream_sublease", "下游转租"),
        ("entrusted_operation", "委托运营"),
    )

    def build_summary_rows(self, analytics_data: dict[str, Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for metric, paths, unit in self._SUMMARY_METRICS:
            value = self._get_first_value(analytics_data, paths)
            rows.append(
                {
                    "section": self._SUMMARY_SECTION,
                    "metric": metric,
                    "value": self._format_value(value, unit),
                    "unit": unit,
                }
            )
        return rows

    def build_distribution_rows(self, analytics_data: dict[str, Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for field, section, label_keys, value_keys, unit in self._DISTRIBUTION_SECTIONS:
            items = analytics_data.get(field)
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                label = self._get_item_value(item, label_keys)
                if label == "":
                    continue

                rows.append(
                    {
                        "section": section,
                        "metric": label,
                        "value": self._format_value(
                            self._get_item_value(item, value_keys, raw=True),
                            unit,
                        ),
                        "unit": unit,
                    }
                )
        return rows

    def build_export_rows(self, analytics_data: dict[str, Any]) -> list[dict[str, str]]:
        return (
            self.build_summary_rows(analytics_data)
            + self.build_customer_breakdown_rows(analytics_data)
            + self.build_distribution_rows(analytics_data)
        )

    def build_customer_breakdown_rows(
        self, analytics_data: dict[str, Any]
    ) -> list[dict[str, str]]:
        entity_breakdown = analytics_data.get("customer_entity_breakdown")
        contract_breakdown = analytics_data.get("customer_contract_breakdown")
        if not isinstance(entity_breakdown, dict) and not isinstance(contract_breakdown, dict):
            return []

        rows: list[dict[str, str]] = []
        for key, label in self._CUSTOMER_BREAKDOWN_LABELS:
            rows.append(
                {
                    "section": self._CUSTOMER_BREAKDOWN_SECTION,
                    "metric": label,
                    "value": f"主体 {int((entity_breakdown or {}).get(key, 0) or 0)} / 合同 {int((contract_breakdown or {}).get(key, 0) or 0)}",
                    "unit": "",
                }
            )
        return rows

    def render_csv(self, rows: list[dict[str, Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["分组", "指标", "数值", "单位"])
        for row in rows:
            writer.writerow(
                [
                    row.get("section", ""),
                    row.get("metric", ""),
                    row.get("value", ""),
                    row.get("unit", ""),
                ]
            )
        return output.getvalue()

    def _get_first_value(
        self, analytics_data: dict[str, Any], paths: tuple[str, ...]
    ) -> Any:
        for path in paths:
            value = self._get_nested_value(analytics_data, path)
            if value is not None:
                return value
        return None

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _get_item_value(
        self,
        item: dict[str, Any],
        keys: tuple[str, ...],
        *,
        raw: bool = False,
    ) -> Any:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            if raw:
                return value
            text = str(value).strip()
            if text != "":
                return text
        return None if raw else ""

    def _format_value(self, value: Any, unit: str) -> str:
        if unit == "":
            return "" if value is None else str(value)
        if value is None:
            return ""
        if unit in {"元", "平方米", "%"}:
            return f"{self._to_number(value):.2f}"
        if unit in {"项", "个", "份"}:
            number = self._to_number(value)
            if float(number).is_integer():
                return str(int(number))
            return f"{number:.2f}"
        return str(value)

    def _to_number(self, value: Any) -> float:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        return 0.0
