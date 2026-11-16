"""Workbook builders for annual ledger exports."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from src.schemas.management_fee_matrix import (
    ManagementFeeMatrixView,
    ManagementFeeMonthView,
    ManagementFeeOwnerRow,
)
from src.schemas.rent_queries import (
    RentContractRow,
    RentMatrixView,
    RentMonthView,
)
from src.services.asset_operations.ledger_export_service import (
    build_management_fee_workbook,
    build_rent_ledger_workbook,
)

pytestmark = pytest.mark.unit


def test_rent_ledger_export_mirrors_matrix_rows_and_totals():
    view = RentMatrixView(
        ledger_type="terminal_rent",
        year=2026,
        current_month=11,
        rows=[
            RentContractRow(
                contract_kind="terminal",
                contract_id="t1",
                contract_number="TM-001",
                contract_name="一号铺",
                months=[
                    RentMonthView(
                        month=1,
                        due_amount=Decimal("100"),
                        paid_amount=Decimal("60"),
                        remaining_amount=Decimal("40"),
                    ),
                    RentMonthView(
                        month=2,
                        due_amount=Decimal("100"),
                        paid_amount=Decimal("100"),
                        remaining_amount=Decimal("0"),
                    ),
                ],
                total_due_amount=Decimal("200"),
                total_paid_amount=Decimal("160"),
                total_remaining_amount=Decimal("40"),
            )
        ],
        total_due_amount=Decimal("200"),
        total_paid_amount=Decimal("160"),
        total_remaining_amount=Decimal("40"),
    )

    workbook = load_workbook_from_bytes(build_rent_ledger_workbook(view))
    sheet = workbook["租金台账"]
    header = [cell.value for cell in sheet[1]]
    assert header[0] == "合同编号"
    assert header[2:5] == ["1月应付", "1月实收", "1月剩余"]
    assert header[-3:] == ["年应付合计", "年实收合计", "年剩余合计"]

    row = [cell.value for cell in sheet[2]]
    assert row[0] == "TM-001"
    assert row[2:5] == [Decimal("100"), Decimal("60"), Decimal("40")]
    assert row[5:8] == [Decimal("100"), Decimal("100"), Decimal("0")]
    assert row[8:11] == [0, 0, 0]
    assert row[-3:] == [Decimal("200"), Decimal("160"), Decimal("40")]

    totals = [cell.value for cell in sheet[3]]
    assert totals[0] == "合计"
    assert totals[2:5] == [Decimal("100"), Decimal("60"), Decimal("40")]


def test_management_fee_export_uses_business_status_labels():
    view = ManagementFeeMatrixView(
        year=2026,
        current_month=11,
        rows=[
            ManagementFeeOwnerRow(
                owner_party_id="owner-1",
                owner_name="城投置业",
                months=[
                    ManagementFeeMonthView(
                        month=1, status="confirmed", fee_amount=Decimal("88.5")
                    ),
                    ManagementFeeMonthView(
                        month=2, status="pending_stamp", fee_amount=Decimal("12")
                    ),
                ],
                total_confirmed_amount=Decimal("88.5"),
            )
        ],
        total_confirmed_amount=Decimal("88.5"),
    )

    workbook = load_workbook_from_bytes(build_management_fee_workbook(view))
    sheet = workbook["委托管理费台账"]
    row = [cell.value for cell in sheet[2]]
    assert row[0] == "城投置业"
    assert row[1:3] == ["已确认", Decimal("88.5")]
    assert row[3:5] == ["待盖章", Decimal("12")]
    assert row[-1] == Decimal("88.5")

    # 合计行与「年确认合计」同口径：待盖章月的试算金额不进合计。
    totals = [cell.value for cell in sheet[3]]
    assert totals[1:3] == [None, Decimal("88.5")]
    assert totals[3:5] == [None, Decimal("0")]


_PAGELESS_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"trailer<</Size 3/Root 1 0 R>>\n%%EOF"
)


def test_render_pdf_first_page_fails_loud_on_pageless_pdf(tmp_path):
    from src.services.asset_operations.archive_document_query_service import (
        render_pdf_first_page,
    )

    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(_PAGELESS_PDF)
    with pytest.raises(ValueError):
        render_pdf_first_page(empty_path)


def load_workbook_from_bytes(content: bytes):
    return load_workbook(BytesIO(content))
