"""Sync xlsx export for annual rent and management-fee ledger matrices.

The exported workbook is a flat mirror of the matrix the workbench already
renders: one row per contract (or owner for management fees), one
amount/status pair per month, plus annual totals.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook

from ...schemas.management_fee_matrix import ManagementFeeMatrixView
from ...schemas.rent_queries import RentMatrixView

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_MONTH_LABELS = tuple(f"{month}月" for month in range(1, 13))

_MANAGEMENT_FEE_STATUS_LABELS = {
    "collecting": "收租中",
    "pending_stamp": "待盖章",
    "confirmed": "已确认",
    "upcoming": "未到",
    "missing": "暂无对账单",
}


def _workbook_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_rent_ledger_workbook(view: RentMatrixView) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "租金台账"
    header: list[str] = ["合同编号", "合同名称"]
    for label in _MONTH_LABELS:
        header.extend([f"{label}应付", f"{label}实收", f"{label}剩余"])
    header.extend(["年应付合计", "年实收合计", "年剩余合计"])
    sheet.append(header)

    month_due_totals = [Decimal("0")] * 12
    month_paid_totals = [Decimal("0")] * 12
    month_remaining_totals = [Decimal("0")] * 12
    for row in view.rows:
        months = {month.month: month for month in row.months}
        values: list[object] = [row.contract_number, row.contract_name]
        for month_number in range(1, 13):
            month = months.get(month_number)
            due = month.due_amount if month is not None else Decimal("0")
            paid = month.paid_amount if month is not None else Decimal("0")
            remaining = month.remaining_amount if month is not None else Decimal("0")
            values.extend([due, paid, remaining])
            month_due_totals[month_number - 1] += due
            month_paid_totals[month_number - 1] += paid
            month_remaining_totals[month_number - 1] += remaining
        values.extend(
            [row.total_due_amount, row.total_paid_amount, row.total_remaining_amount]
        )
        sheet.append(values)

    totals: list[object] = ["合计", None]
    for index in range(12):
        totals.extend(
            [
                month_due_totals[index],
                month_paid_totals[index],
                month_remaining_totals[index],
            ]
        )
    totals.extend(
        [view.total_due_amount, view.total_paid_amount, view.total_remaining_amount]
    )
    sheet.append(totals)
    return _workbook_bytes(workbook)


def build_management_fee_workbook(view: ManagementFeeMatrixView) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "委托管理费台账"
    header: list[str] = ["业主"]
    for label in _MONTH_LABELS:
        header.extend([f"{label}状态", f"{label}金额"])
    header.append("年确认合计")
    sheet.append(header)

    month_amount_totals = [Decimal("0")] * 12
    for row in view.rows:
        months = {month.month: month for month in row.months}
        values: list[object] = [row.owner_name]
        for month_number in range(1, 13):
            month = months.get(month_number)
            status = (
                _MANAGEMENT_FEE_STATUS_LABELS.get(month.status, month.status)
                if month is not None
                else "未到"
            )
            amount = (
                month.fee_amount
                if month is not None and month.fee_amount is not None
                else None
            )
            if month is not None and month.fee_amount is not None:
                month_amount_totals[month_number - 1] += month.fee_amount
            values.extend([status, amount])
        values.append(row.total_confirmed_amount)
        sheet.append(values)

    totals: list[object] = ["合计"]
    for index in range(12):
        totals.extend(["", month_amount_totals[index]])
    totals.append(view.total_confirmed_amount)
    sheet.append(totals)
    return _workbook_bytes(workbook)
