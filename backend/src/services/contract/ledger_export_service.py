"""合同台账导出服务。"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

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

    EXPORT_COLUMNS = [
        "entry_id",
        "contract_id",
        "year_month",
        "due_date",
        "amount_due",
        "currency_code",
        "is_tax_included",
        "tax_rate",
        "payment_status",
        "paid_amount",
        "notes",
        "created_at",
        "updated_at",
    ]

    async def export_ledger_entries(
        self,
        db: AsyncSession,
        *,
        params: LedgerExportQueryParams,
    ) -> LedgerExportPayload:
        result = await ledger_service_v2.query_ledger_entries(
            db,
            asset_id=params.asset_id,
            party_id=params.party_id,
            contract_id=params.contract_id,
            year_month_start=params.year_month_start,
            year_month_end=params.year_month_end,
            payment_status=params.payment_status,
            include_voided=params.include_voided,
            offset=params.offset,
            limit=params.limit,
        )
        rows = [self._normalize_row(item) for item in result.get("items", [])]
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
            normalized[column] = "" if value is None else str(value)
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
