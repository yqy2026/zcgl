"""Generate the V4-0 three-sheet import template workbook.

The generated template is the round-trip counterpart of
``import_workbook_parser``: what this service writes, the parser must accept.
Layout is uniform across the three sheets: row 1 headers, row 2 hidden
``template_version`` marker, data from row 3. A separate read-me sheet lists
the enum dictionaries; the parser ignores extra sheets.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from .import_workbook_parser import (
    ACQUISITION_MODES,
    PAYMENT_CYCLES,
    RENT_COLLECTORS,
    SHEET_NAMES,
    TEMPLATE_VERSION,
    TERMINAL_HEADERS,
    TERMINAL_MODES,
    UNIT_HEADERS,
    UPSTREAM_HEADERS,
    UPSTREAM_TYPES,
)
from .import_workbook_parser import (
    STAGE_HEADERS as STAGE_HEADERS_IMPORT,
)

_GUIDE_ROWS: tuple[tuple[str, ...], ...] = (
    ("列", "取值说明"),
    (
        "类型（承租合同）",
        f"{UPSTREAM_TYPES}：lease=承租合同，management_agreement=委托管理协议",
    ),
    ("周期（承租合同）", f"{PAYMENT_CYCLES}：lease 类型必填"),
    ("管理费率（承租合同）", "小数形式，如 0.0225；management_agreement 必填"),
    ("模式（终端合同）", f"{TERMINAL_MODES}：sublease=转租，direct_lease=直租"),
    (
        "收租方（终端合同）",
        f"{RENT_COLLECTORS}：按模式派生（sublease→operator，direct_lease→owner），留空",
    ),
    ("获取方式（物业单元）", f"{ACQUISITION_MODES}"),
    ("日期列", "YYYY-MM-DD"),
    ("金额列", "数字，可为小数；负数报错"),
    ("递增%", "百分数数值，如 2.5 表示 2.5%（入库为 0.025）"),
    (
        "租金阶段",
        "不进主行：在阶段起/阶段止等阶段列填写；同一合同可跨多行，阶段须无缝覆盖合同期",
    ),
    (
        "多单元合同",
        "合同主字段重复填写于多行，每行填一个单元编号；同编号各行主字段必须一致",
    ),
    ("新增模式", "遇库内已存在编号报错；扫描件列填批量上传暂存文件名"),
    (
        "更新模式",
        "只按编号匹配既有对象；空白不覆盖；派生列与阶段列忽略并提示；收租方填写即提示",
    ),
)


def build_template_workbook() -> bytes:
    """Build the empty three-sheet template with hidden version rows."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headers in (
        (SHEET_NAMES[0], UNIT_HEADERS),
        (SHEET_NAMES[1], UPSTREAM_HEADERS),
        (SHEET_NAMES[2], TERMINAL_HEADERS),
    ):
        sheet = workbook.create_sheet(title=sheet_name)
        sheet.append(list(headers))
        sheet.append(
            [f"template_version={TEMPLATE_VERSION}"] + [""] * (len(headers) - 1)
        )
        for column in range(1, len(headers) + 1):
            sheet.cell(row=1, column=column).font = Font(bold=True)
            letter = get_column_letter(column)
            sheet.column_dimensions[letter].width = max(
                12, len(headers[column - 1]) * 2
            )
        version_cell = sheet.cell(row=2, column=1)
        version_cell.font = Font(italic=True, color="FF999999")
        sheet.row_dimensions[2].hidden = True
        sheet.freeze_panes = "A3"

    guide = workbook.create_sheet(title="填写说明")
    for row in _GUIDE_ROWS:
        guide.append(list(row))
    guide.column_dimensions["A"].width = 24
    guide.column_dimensions["B"].width = 96

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_update_workbook(
    *,
    units: list[dict[str, object]],
    upstreams: list[dict[str, object]],
    terminals: list[dict[str, object]],
) -> bytes:
    """Build an update-mode base workbook prefilled with current scoped facts.

    Stage columns stay empty: rent-schedule changes do not go through import.
    """
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headers in (
        (SHEET_NAMES[0], UNIT_HEADERS),
        (SHEET_NAMES[1], UPSTREAM_HEADERS),
        (SHEET_NAMES[2], TERMINAL_HEADERS),
    ):
        sheet = workbook.create_sheet(title=sheet_name)
        sheet.append(list(headers))
        sheet.append(
            [f"template_version={TEMPLATE_VERSION}"] + [""] * (len(headers) - 1)
        )
        sheet.row_dimensions[2].hidden = True
        sheet.freeze_panes = "A3"

    unit_sheet = workbook[SHEET_NAMES[0]]
    for unit in units:
        unit_sheet.append(
            [
                unit.get("unit_code"),
                unit.get("name"),
                unit.get("owner_party_name"),
                unit.get("project_code"),
                unit.get("address"),
                unit.get("usage_type"),
                unit.get("acquisition_mode"),
                unit.get("managed_from"),
                unit.get("managed_to"),
                unit.get("land_area"),
                unit.get("building_area"),
                unit.get("rentable_area"),
            ]
        )
    upstream_sheet = workbook[SHEET_NAMES[1]]
    for contract in upstreams:
        upstream_sheet.append(
            [
                contract.get("contract_number"),
                contract.get("contract_type"),
                contract.get("name"),
                contract.get("owner_party_name"),
                contract.get("operator_party_name"),
                contract.get("unit_codes"),
                contract.get("start_date"),
                contract.get("end_date"),
                "",
                "",
                contract.get("deposit_amount"),
                contract.get("management_fee_rate"),
            ]
            + [""] * len(STAGE_HEADERS_IMPORT)
        )
    terminal_sheet = workbook[SHEET_NAMES[2]]
    for contract in terminals:
        terminal_sheet.append(
            [
                contract.get("contract_number"),
                contract.get("contract_mode"),
                contract.get("tenant_party_name"),
                contract.get("lessor_party_name"),
                contract.get("unit_codes"),
                contract.get("upstream_contract_number"),
                contract.get("start_date"),
                contract.get("end_date"),
                contract.get("deposit_amount"),
                "",
            ]
            + [""] * len(STAGE_HEADERS_IMPORT)
        )

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
