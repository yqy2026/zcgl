"""合同台账导出服务。"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.query_builder import PartyFilter
from src.schemas.contract_group import LedgerExportQueryParams
from src.services.contract.ledger_service_v2 import ledger_service_v2
from src.services.excel import ExcelExportService


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class LedgerExportPayload:
    filename: str
    media_type: str
    content: bytes


class LedgerExportService:
    """导出台账聚合查询结果。"""

    # S4：台账导出口径版本（与经营分析导出对齐，REQ-RNT-006 台账口径）
    LEDGER_METRICS_VERSION = "req-rnt-006-v1"

    EXPORT_COLUMNS = [
        "entry_id",
        "contract_id",
        "year_month",
        "ledger_views",
        "due_date",
        "amount_due",
        "currency_code",
        "is_tax_included",
        "tax_rate",
        "payment_status",
        "paid_amount",
        "flow_occurred_on_dates",
        "notes",
        "created_at",
        "updated_at",
        "metrics_version",
    ]

    async def export_ledger_entries(
        self,
        db: AsyncSession,
        *,
        params: LedgerExportQueryParams,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> LedgerExportPayload:
        items: list[Any] = []
        offset = 0
        page_size = 200
        while True:
            result = await ledger_service_v2.query_ledger_entries(
                db,
                ledger_view=params.ledger_view,
                project_id=params.project_id,
                asset_id=params.asset_id,
                party_id=params.party_id,
                contract_id=params.contract_id,
                year_month_start=params.year_month_start,
                year_month_end=params.year_month_end,
                flow_occurred_on_start=params.flow_occurred_on_start,
                flow_occurred_on_end=params.flow_occurred_on_end,
                payment_status=params.payment_status,
                include_voided=params.include_voided,
                offset=offset,
                limit=page_size,
                current_user_id=current_user_id,
                party_filter=party_filter,
            )
            page_items = list(result.get("items", []))
            items.extend(page_items)
            offset += len(page_items)
            if offset >= int(result.get("total", 0)) or len(page_items) == 0:
                break

        rows = [self._normalize_row(item) for item in items]
        timestamp = _utcnow_naive().strftime("%Y%m%d_%H%M%S")

        if params.export_format == "csv":
            return LedgerExportPayload(
                filename=f"ledger_entries_{timestamp}.csv",
                media_type="text/csv; charset=utf-8",
                content=self._to_csv(rows),
            )

        return LedgerExportPayload(
            filename=f"ledger_entries_{timestamp}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=self._to_excel(rows),
        )

    def _normalize_row(self, item: Any) -> dict[str, str]:
        if hasattr(item, "model_dump"):
            raw = item.model_dump()
        elif isinstance(item, dict):
            raw = item
        else:
            raw = {
                column: getattr(item, column, None) for column in self.EXPORT_COLUMNS
            }

        normalized: dict[str, str] = {}
        for column in self.EXPORT_COLUMNS:
            value = raw.get(column)
            if value is None:
                normalized[column] = ""
            elif isinstance(value, list):
                normalized[column] = ";".join(str(item) for item in value)
            else:
                normalized[column] = str(value)
        # S4：口径版本为合成列（与经营分析导出对齐），不依赖条目字段
        normalized["metrics_version"] = self.LEDGER_METRICS_VERSION
        return normalized

    def _to_csv(self, rows: list[dict[str, str]]) -> bytes:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=self.EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue().encode("utf-8")

    def _to_excel(self, rows: list[dict[str, str]]) -> bytes:
        data = rows if rows else [{column: "" for column in self.EXPORT_COLUMNS}]
        dataframe = pd.DataFrame(data, columns=self.EXPORT_COLUMNS)
        buffer = io.BytesIO()
        excel_service = ExcelExportService(None)
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            dataframe.to_excel(writer, sheet_name="ledger", index=False)
            excel_service._set_column_widths(writer.sheets["ledger"])
        buffer.seek(0)
        return buffer.read()


ledger_export_service = LedgerExportService()
