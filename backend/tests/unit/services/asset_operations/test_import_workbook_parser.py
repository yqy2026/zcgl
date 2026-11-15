"""Unit tests for the three-sheet import workbook parser and template."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from src.services.asset_operations.import_template_service import (
    build_template_workbook,
)
from src.services.asset_operations.import_workbook_parser import (
    STAGE_HEADERS,
    TEMPLATE_VERSION,
    TERMINAL_HEADERS,
    UNIT_HEADERS,
    UPSTREAM_HEADERS,
    WorkbookFormatError,
    parse_import_workbook,
)


def _workbook_bytes() -> Workbook:
    """A workbook pre-filled with headers and hidden version rows."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headers in (
        ("物业单元", UNIT_HEADERS),
        ("承租合同", UPSTREAM_HEADERS),
        ("终端合同", TERMINAL_HEADERS),
    ):
        sheet = workbook.create_sheet(title=sheet_name)
        sheet.append(list(headers))
        sheet.append(
            [f"template_version={TEMPLATE_VERSION}"] + [""] * (len(headers) - 1)
        )
        sheet.row_dimensions[2].hidden = True
    return workbook


def _as_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _unit_row(
    sheet,
    *,
    code="U-001",
    name="一号楼",
    party="示例产权方",
    project="PRJ-001",
    address="示例路 1 号",
    usage="commercial",
    acquisition="owned",
    managed="2026-01-01",
    land="100",
    building="200",
    rentable="180",
):
    sheet.append(
        [
            code,
            name,
            party,
            project,
            address,
            usage,
            acquisition,
            managed,
            "",
            land,
            building,
            rentable,
        ]
    )


def _stage_values(
    start,
    end,
    base="3000",
    actual="3000",
    percent="0",
    free="0",
    discount="0",
    cycle="monthly",
    due="15",
):
    return [start, end, base, percent, free, discount, actual, cycle, due]


def _upstream_main(
    number,
    *,
    type_="lease",
    name="示例合同",
    party="示例产权方",
    operator="示例运营方",
    unit="U-001",
    start="2026-01-01",
    end="2026-12-31",
    cycle="monthly",
    day="15",
    deposit="5000",
    fee_rate="",
    scan="scan-lease.pdf",
):
    return [
        number,
        type_,
        name,
        party,
        operator,
        unit,
        start,
        end,
        cycle,
        day,
        deposit,
        fee_rate,
        scan,
    ]


def _terminal_main(
    number,
    *,
    mode="sublease",
    tenant="示例租户",
    lessor="示例运营方",
    unit="U-001",
    upstream="",
    start="2026-01-01",
    end="2026-12-31",
    deposit="2000",
    collector="",
    scan="scan-t.pdf",
):
    return [
        number,
        mode,
        tenant,
        lessor,
        unit,
        upstream,
        start,
        end,
        deposit,
        collector,
        scan,
    ]


def test_template_round_trip_parses_clean() -> None:
    parsed = parse_import_workbook(build_template_workbook(), mode="create")
    assert parsed.template_version == TEMPLATE_VERSION
    assert parsed.issues == []
    assert parsed.row_count == 0


def test_create_mode_happy_path() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    upstream = workbook["承租合同"]
    upstream.append(
        _upstream_main("HT-001") + _stage_values("2026-01-01", "2026-06-30")
    )
    upstream.append(
        ["HT-001", "", "", "", "", "", "", "", "", "", "", "", ""]
        + _stage_values("2026-07-01", "2026-12-31", base="3200", actual="3200")
    )
    terminal = workbook["终端合同"]
    terminal.append(
        _terminal_main("ZD-001") + _stage_values("2026-01-01", "2026-12-31")
    )

    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")

    assert parsed.error_count == 0, [i.message for i in parsed.issues]
    assert len(parsed.units) == 1
    assert parsed.units[0].unit_code == "U-001"
    assert len(parsed.upstreams) == 1
    contract = parsed.upstreams[0]
    assert contract.contract_number == "HT-001"
    assert contract.unit_codes == ["U-001"]
    assert len(contract.stages) == 2
    assert contract.stages[0].actual_monthly_rent == Decimal("3000")
    assert len(parsed.terminals) == 1
    assert parsed.terminals[0].rent_collector is None
    assert parsed.row_count == 4


def test_stage_percent_converted_to_fraction() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    workbook["承租合同"].append(
        _upstream_main("HT-002")
        + _stage_values("2026-01-01", "2026-12-31", percent="2.5")
    )
    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    assert parsed.error_count == 0
    assert parsed.upstreams[0].stages[0].increase_rate == Decimal("0.025")


def test_stage_gap_and_overlap_rejected_in_create_mode() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    upstream = workbook["承租合同"]
    upstream.append(
        _upstream_main("HT-GAP") + _stage_values("2026-01-01", "2026-06-30")
    )
    upstream.append(["HT-GAP"] + [""] * 12 + _stage_values("2026-07-02", "2026-12-31"))
    upstream.append(
        _upstream_main("HT-OVL") + _stage_values("2026-01-01", "2026-06-30")
    )
    upstream.append(["HT-OVL"] + [""] * 12 + _stage_values("2026-06-30", "2026-12-31"))

    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    codes = [issue.code for issue in parsed.issues]
    assert "RENT_SCHEDULE_GAP_ERROR" in codes
    assert "RENT_SCHEDULE_OVERLAP_ERROR" in codes


def test_multi_row_contract_merges_units_and_flags_conflicts() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], code="U-001")
    _unit_row(workbook["物业单元"], code="U-002", name="二号楼")
    upstream = workbook["承租合同"]
    upstream.append(_upstream_main("HT-M") + _stage_values("2026-01-01", "2026-12-31"))
    upstream.append(
        ["HT-M", "", "", "", "", "U-002", "", "", "", "", "", "", ""]
        + [""] * len(STAGE_HEADERS)
    )
    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    assert parsed.error_count == 0, [i.message for i in parsed.issues]
    assert parsed.upstreams[0].unit_codes == ["U-001", "U-002"]

    conflict = _workbook_bytes()
    _unit_row(conflict["物业单元"])
    sheet = conflict["承租合同"]
    sheet.append(
        _upstream_main("HT-C", name="甲") + _stage_values("2026-01-01", "2026-12-31")
    )
    sheet.append(
        ["HT-C", "", "乙", "", "", "", "", "", "", "", "", "", ""]
        + _stage_values("2026-01-01", "2026-12-31")
    )
    parsed_conflict = parse_import_workbook(_as_bytes(conflict), mode="create")
    assert any(
        issue.code == "CONTRACT_MAIN_FIELD_CONFLICT_ERROR"
        for issue in parsed_conflict.issues
    )


@pytest.mark.parametrize(
    ("mutate", "message_part"),
    [
        (lambda wb: wb.remove(wb["终端合同"]), "缺少工作表"),
        (
            lambda wb: [
                wb[name].cell(row=2, column=1, value="template_version=1999-01-01")
                for name in ("物业单元", "承租合同", "终端合同")
            ],
            "模板版本不支持",
        ),
        (
            lambda wb: setattr(wb["承租合同"].cell(row=2, column=1), "value", None),
            "template_version",
        ),
    ],
)
def test_file_level_rejections(mutate, message_part) -> None:
    workbook = _workbook_bytes()
    mutate(workbook)
    with pytest.raises(WorkbookFormatError, match=message_part):
        parse_import_workbook(_as_bytes(workbook), mode="create")


def test_header_mismatch_rejected() -> None:
    workbook = _workbook_bytes()
    workbook["物业单元"].cell(row=1, column=2, value="改名列")
    with pytest.raises(WorkbookFormatError, match="表头不符"):
        parse_import_workbook(_as_bytes(workbook), mode="create")


def test_unit_row_errors() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], code="U-DUP")
    _unit_row(workbook["物业单元"], code="U-DUP", name="重复")
    _unit_row(
        workbook["物业单元"],
        code="U-BAD",
        acquisition="wrong",
        rentable="999",
        building="100",
    )
    _unit_row(workbook["物业单元"], code="U-NEG", building="-5")

    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    codes = [issue.code for issue in parsed.issues]
    assert "UNIT_DUPLICATE_KEY_ERROR" in codes
    assert "UNIT_ACQUISITION_INVALID_ERROR" in codes
    assert "UNIT_AREA_RANGE_ERROR" in codes
    assert "UNIT_BUILDING_AREA_INVALID_ERROR" in codes
    assert len(parsed.units) == 1


def test_create_mode_missing_required_fields_reported() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    workbook["承租合同"].append(
        [
            "HT-X",
            "lease",
            "",
            "",
            "",
            "",
            "2026-01-01",
            "2026-12-31",
            "",
            "",
            "",
            "",
            "s.pdf",
        ]
        + _stage_values("2026-01-01", "2026-12-31")
    )
    workbook["终端合同"].append(
        [
            "ZD-X",
            "sublease",
            "",
            "",
            "U-001",
            "",
            "2026-01-01",
            "2026-12-31",
            "",
            "",
            "s.pdf",
        ]
        + _stage_values("2026-01-01", "2026-12-31")
    )
    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    codes = [issue.code for issue in parsed.issues]
    assert "CONTRACT_NAME_MISSING_ERROR" in codes
    assert "CONTRACT_OWNER_MISSING_ERROR" in codes
    assert "CONTRACT_OPERATOR_MISSING_ERROR" in codes
    assert "CONTRACT_SCAN_MISSING_ERROR" not in codes
    assert "CONTRACT_TENANT_MISSING_ERROR" in codes
    assert "CONTRACT_LESSOR_MISSING_ERROR" in codes


def test_management_agreement_requires_fee_rate() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    workbook["承租合同"].append(
        _upstream_main("HT-F", type_="management_agreement", cycle="", fee_rate="")
        + _stage_values("2026-01-01", "2026-12-31")
    )
    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    assert any(
        issue.code == "CONTRACT_FEE_RATE_MISSING_ERROR" for issue in parsed.issues
    )


def test_update_mode_blank_cells_are_none_and_stages_warned() -> None:
    workbook = _workbook_bytes()
    workbook["物业单元"].append(["U-001", "新名称", "", "", "", "", "", "", "", "", "", ""])
    workbook["承租合同"].append(
        ["HT-U", "", "", "", "", "", "", "2026-06-30", "", "", "", "", ""]
        + _stage_values("2026-01-01", "2026-12-31")
    )
    workbook["终端合同"].append(
        _terminal_main("ZD-U", collector="owner") + ["", "", "", "", "", "", "", "", ""]
    )

    parsed = parse_import_workbook(_as_bytes(workbook), mode="update")
    codes = [issue.code for issue in parsed.issues]
    assert parsed.error_count == 0, [i.message for i in parsed.issues]
    assert "STAGES_NOT_UPDATABLE_WARNING" in codes
    assert "RENT_COLLECTOR_DERIVED_WARNING" in codes
    unit = parsed.units[0]
    assert unit.source_row == 3
    assert unit.name == "新名称"
    assert unit.owner_party_name is None
    assert parsed.upstreams[0].end_date == date(2026, 6, 30)


def test_stage_defaults_and_cycle_warning() -> None:
    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"])
    values = _stage_values("2026-01-01", "2026-12-31")
    values[7] = ""
    workbook["承租合同"].append(_upstream_main("HT-D") + values)
    parsed = parse_import_workbook(_as_bytes(workbook), mode="create")
    assert any(issue.code == "STAGE_CYCLE_MISSING_WARNING" for issue in parsed.issues)
    assert parsed.upstreams[0].stages[0].payment_cycle == "monthly"
