"""Helpers for converting analytics payloads into export-friendly rows."""

from __future__ import annotations

import csv
import io
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any


class AnalyticsExportService:
    """Builds a stable tabular export payload for analytics responses."""

    def build_summary_rows(self, analytics_data: dict[str, Any]) -> list[dict[str, str]]:
        area_summary = self._as_dict(analytics_data.get("area_summary"))
        financial_summary = self._as_dict(analytics_data.get("financial_summary"))

        return [
            self._make_row("资产总数", analytics_data.get("total_assets"), "个", value_type="count"),
            self._make_row("总面积", area_summary.get("total_area"), "㎡"),
            self._make_row("可租面积", area_summary.get("total_rentable_area"), "㎡"),
            self._make_row("整体出租率", area_summary.get("occupancy_rate"), "%"),
            self._make_row("年收入", financial_summary.get("total_annual_income"), "元"),
            self._make_row("年支出", financial_summary.get("total_annual_expense"), "元"),
            self._make_row("净收益", financial_summary.get("total_net_income"), "元"),
            self._make_row("月租金", financial_summary.get("total_monthly_rent"), "元"),
            self._make_row("总收入（经营口径）", analytics_data.get("total_income"), "元"),
            self._make_row(
                "自营租金收入",
                analytics_data.get("self_operated_rent_income"),
                "元",
            ),
            self._make_row(
                "代理服务费收入",
                analytics_data.get("agency_service_income"),
                "元",
            ),
            self._make_row(
                "客户主体数",
                analytics_data.get("customer_entity_count"),
                "个",
                value_type="count",
            ),
            self._make_row(
                "客户合同数",
                analytics_data.get("customer_contract_count"),
                "份",
                value_type="count",
            ),
            self._make_row(
                "口径版本",
                analytics_data.get("metrics_version"),
                "",
                value_type="text",
            ),
        ]

    def build_export_rows(self, analytics_data: dict[str, Any]) -> list[dict[str, str]]:
        """Return the current shared export payload."""

        return self.build_summary_rows(analytics_data)

    def render_csv(self, rows: list[dict[str, str]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["指标", "数值", "单位"])
        for row in rows:
            writer.writerow(
                [
                    row.get("metric", ""),
                    row.get("value", ""),
                    row.get("unit", ""),
                ]
            )
        return output.getvalue()

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _make_row(
        self,
        metric: str,
        value: Any,
        unit: str,
        *,
        value_type: str = "money",
    ) -> dict[str, str]:
        return {
            "metric": metric,
            "value": self._format_value(value, value_type=value_type),
            "unit": unit,
        }

    def _format_value(self, value: Any, *, value_type: str) -> str:
        if value_type == "text":
            return "" if value is None else str(value).strip()
        if value_type == "count":
            return self._format_count(value)
        return self._format_decimal(value)

    @staticmethod
    def _format_count(value: Any) -> str:
        try:
            normalized = Decimal(str(0 if value is None else value))
        except (InvalidOperation, ValueError):
            normalized = Decimal("0")
        if normalized == normalized.to_integral():
            return str(int(normalized))
        return str(normalized.normalize())

    @staticmethod
    def _format_decimal(value: Any) -> str:
        try:
            normalized = Decimal(str(0 if value is None else value))
        except (InvalidOperation, ValueError):
            normalized = Decimal("0")
        return str(normalized.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
