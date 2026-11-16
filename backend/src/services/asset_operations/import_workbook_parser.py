"""Parse the V4-0 three-sheet import workbook (pure, database-free).

The parser owns the structural layers of the V4-0 validation order:
file level (sheets/headers/template version), row level (types/enums),
intra-row (date order, non-negative amounts), cross-row within the workbook
(duplicate keys, per-contract field consistency, stage completeness) and
workbook-internal reference existence. Database resolution (parties, projects,
units, upstream contracts) and business validation belong to the import batch
service, which reuses the formal contract commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

TEMPLATE_VERSION = "2026-11-15"

UNIT_SHEET = "物业单元"
UPSTREAM_SHEET = "承租合同"
TERMINAL_SHEET = "终端合同"
SHEET_NAMES = (UNIT_SHEET, UPSTREAM_SHEET, TERMINAL_SHEET)

UPSTREAM_TYPES = ("lease", "management_agreement")
TERMINAL_MODES = ("sublease", "direct_lease")
ACQUISITION_MODES = ("owned", "leased", "managed")
PAYMENT_CYCLES = ("monthly", "quarterly", "yearly", "custom")
RENT_COLLECTORS = ("operator", "owner")

UNIT_HEADERS = (
    "单元编号",
    "单元名称",
    "主体全称",
    "项目编号",
    "地址",
    "业态",
    "获取方式",
    "接管日",
    "管理至",
    "土地面积(㎡)",
    "建筑面积(㎡)",
    "可租面积(㎡)",
)
STAGE_HEADERS = (
    "阶段起",
    "阶段止",
    "原定月租(元)",
    "递增%",
    "免租月数",
    "减免额(元)",
    "实际月租(元)",
    "阶段周期",
    "缴租日",
)
UPSTREAM_MAIN_HEADERS = (
    "合同编号",
    "类型",
    "名称",
    "主体全称",
    "运营主体全称",
    "单元编号",
    "开始日",
    "结束日",
    "周期",
    "付款日",
    "保证金(元)",
    "管理费率(如0.0225)",
    "扫描件文件名",
)
TERMINAL_MAIN_HEADERS = (
    "合同编号",
    "模式",
    "租户主体全称",
    "出租方主体全称",
    "单元编号",
    "上游合同编号",
    "开始日",
    "结束日",
    "押金(元)",
    "收租方",
    "扫描件文件名",
)
UPSTREAM_HEADERS = UPSTREAM_MAIN_HEADERS + STAGE_HEADERS
TERMINAL_HEADERS = TERMINAL_MAIN_HEADERS + STAGE_HEADERS


class WorkbookFormatError(ValueError):
    """File-level rejection: unreadable file, sheets, headers or version."""


@dataclass(frozen=True)
class WorkbookIssue:
    sheet: str
    row_number: int
    code: str
    message: str


@dataclass(frozen=True)
class StageRowInput:
    stage_start: date
    stage_end: date
    base_monthly_rent: Decimal
    increase_rate: Decimal
    free_rent_months: Decimal
    discount_amount: Decimal
    actual_monthly_rent: Decimal
    payment_cycle: str
    due_day: int
    source_row: int


@dataclass
class UnitRow:
    source_row: int
    unit_code: str
    name: str | None = None
    owner_party_name: str | None = None
    project_code: str | None = None
    address: str | None = None
    usage_type: str | None = None
    acquisition_mode: str | None = None
    managed_from: date | None = None
    managed_to: date | None = None
    land_area: Decimal | None = None
    building_area: Decimal | None = None
    rentable_area: Decimal | None = None


@dataclass
class ContractRow:
    source_rows: tuple[int, ...]
    contract_number: str
    # shared
    unit_codes: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    scan_file_name: str | None = None
    stages: list[StageRowInput] = field(default_factory=list)
    # upstream only
    name: str | None = None
    contract_type: str | None = None
    owner_party_name: str | None = None
    operator_party_name: str | None = None
    payment_cycle: str | None = None
    payment_day: int | None = None
    deposit_amount: Decimal | None = None
    management_fee_rate: Decimal | None = None
    # terminal only
    contract_mode: str | None = None
    tenant_party_name: str | None = None
    lessor_party_name: str | None = None
    upstream_contract_number: str | None = None
    rent_collector: str | None = None


@dataclass
class ParsedWorkbook:
    template_version: str
    mode: str
    units: list[UnitRow] = field(default_factory=list)
    upstreams: list[ContractRow] = field(default_factory=list)
    terminals: list[ContractRow] = field(default_factory=list)
    issues: list[WorkbookIssue] = field(default_factory=list)
    row_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.code.endswith("_ERROR"))

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.code.endswith("_WARNING"))


def parse_import_workbook(data: bytes, *, mode: str) -> ParsedWorkbook:
    """Parse and structurally validate a three-sheet import workbook."""
    if mode not in ("create", "update"):
        raise ValueError(f"unknown import mode: {mode}")
    try:
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - 任何解析失败统一为文件级错误
        raise WorkbookFormatError(f"无法读取工作簿: {exc}") from exc

    try:
        missing = [n for n in SHEET_NAMES if n not in workbook.sheetnames]
        if missing:
            raise WorkbookFormatError(f"缺少工作表: {','.join(missing)}")
        template_version = _read_template_version(workbook)
        _check_headers(workbook)
        parsed = ParsedWorkbook(template_version=template_version, mode=mode)
        parsed.units = _parse_units(workbook[UNIT_SHEET], parsed)
        parsed.upstreams = _parse_contracts(
            workbook[UPSTREAM_SHEET], parsed, sheet_name=UPSTREAM_SHEET
        )
        parsed.terminals = _parse_contracts(
            workbook[TERMINAL_SHEET], parsed, sheet_name=TERMINAL_SHEET
        )
        unit_rows = parsed.units
        upstream_rows = parsed.upstreams
        terminal_rows = parsed.terminals
    finally:
        workbook.close()

    _validate_cross_rows(parsed, upstream_rows, terminal_rows)
    parsed.row_count = (
        len(unit_rows)
        + sum(len(r.source_rows) for r in upstream_rows)
        + sum(len(r.source_rows) for r in terminal_rows)
    )
    return parsed


def _read_template_version(workbook: Any) -> str:
    versions: list[str] = []
    for sheet_name in SHEET_NAMES:
        sheet = workbook[sheet_name]
        row = next(
            sheet.iter_rows(min_row=2, max_row=2, max_col=1, values_only=True),
            (None,),
        )
        marker = row[0]
        if not isinstance(marker, str) or not marker.startswith("template_version="):
            raise WorkbookFormatError(
                f"工作表[{sheet_name}]第 2 行缺少 template_version 标记"
                "（隐藏行被删除或模板不符）"
            )
        versions.append(marker.split("=", 1)[1].strip())
    if len(set(versions)) != 1:
        raise WorkbookFormatError(f"各工作表模板版本不一致: {versions}")
    version = versions[0]
    if version != TEMPLATE_VERSION:
        raise WorkbookFormatError(
            f"模板版本不支持: {version}（当前支持 {TEMPLATE_VERSION}）"
        )
    return version


def _check_headers(workbook: Any) -> None:
    expected = (
        (UNIT_SHEET, UNIT_HEADERS),
        (UPSTREAM_SHEET, UPSTREAM_HEADERS),
        (TERMINAL_SHEET, TERMINAL_HEADERS),
    )
    for sheet_name, headers in expected:
        sheet = workbook[sheet_name]
        row = next(
            sheet.iter_rows(
                min_row=1, max_row=1, max_col=len(headers), values_only=True
            ),
            (),
        )
        actual = tuple(str(c).strip() if c is not None else "" for c in row)
        if actual != headers:
            raise WorkbookFormatError(
                f"工作表[{sheet_name}]表头不符：期望 {headers}，实际 {actual}"
            )


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    text = _cell_text(value).replace(",", "")
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _row_is_empty(values: tuple[Any, ...]) -> bool:
    return all(_cell_text(v) == "" for v in values)


def _issue(
    parsed: ParsedWorkbook, sheet: str, row_number: int, code: str, message: str
) -> None:
    parsed.issues.append(WorkbookIssue(sheet, row_number, code, message))


def _has_row_error(parsed: ParsedWorkbook, sheet: str, row_number: int) -> bool:
    return any(
        i.sheet == sheet and i.row_number == row_number and i.code.endswith("_ERROR")
        for i in parsed.issues
    )


def _parse_units(sheet: Any, parsed: ParsedWorkbook) -> list[UnitRow]:
    rows: list[UnitRow] = []
    seen: dict[str, int] = {}
    for row_number, values in enumerate(
        sheet.iter_rows(min_row=3, values_only=True), start=3
    ):
        if _row_is_empty(values):
            continue
        cell = dict(zip(UNIT_HEADERS, values, strict=False))
        unit_code = _cell_text(cell["单元编号"])
        if unit_code == "":
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_CODE_MISSING_ERROR",
                "单元编号为空",
            )
            continue
        if unit_code in seen:
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_DUPLICATE_KEY_ERROR",
                f"单元编号重复: {unit_code}（首次见第 {seen[unit_code]} 行）",
            )
            continue
        seen[unit_code] = row_number

        acquisition = _cell_text(cell["获取方式"])
        managed_text = _cell_text(cell["接管日"])
        managed_from = _parse_date(cell["接管日"])
        managed_to = _parse_date(cell.get("管理至"))
        land_area = _parse_decimal(cell["土地面积(㎡)"])
        building_area = _parse_decimal(cell["建筑面积(㎡)"])
        rentable_area = _parse_decimal(cell["可租面积(㎡)"])

        if managed_text != "" and managed_from is None:
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_MANAGED_FROM_INVALID_ERROR",
                "接管日格式错误（支持 YYYY-MM-DD）",
            )
        if _cell_text(cell.get("管理至")) != "" and managed_to is None:
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_MANAGED_TO_INVALID_ERROR",
                "管理至格式错误（支持 YYYY-MM-DD）",
            )
        if (
            managed_from is not None
            and managed_to is not None
            and managed_to < managed_from
        ):
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_MANAGED_PERIOD_INVALID_ERROR",
                "管理至不得早于接管日",
            )
        if acquisition != "" and acquisition not in ACQUISITION_MODES:
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_ACQUISITION_INVALID_ERROR",
                f"获取方式无效: {acquisition}（可选 {ACQUISITION_MODES}）",
            )
        for label, value, code in (
            ("土地面积", land_area, "UNIT_LAND_AREA_INVALID_ERROR"),
            ("建筑面积", building_area, "UNIT_BUILDING_AREA_INVALID_ERROR"),
            ("可租面积", rentable_area, "UNIT_RENTABLE_AREA_INVALID_ERROR"),
        ):
            if value is None and _cell_text(cell[f"{label}(㎡)"]) != "":
                _issue(parsed, UNIT_SHEET, row_number, code, f"{label}非数字")
            elif value is not None and value < 0:
                _issue(parsed, UNIT_SHEET, row_number, code, f"{label}为负数")
        if (
            rentable_area is not None
            and building_area is not None
            and rentable_area > building_area
        ):
            _issue(
                parsed,
                UNIT_SHEET,
                row_number,
                "UNIT_AREA_RANGE_ERROR",
                "可租面积不得大于建筑面积",
            )
        if _has_row_error(parsed, UNIT_SHEET, row_number):
            continue
        rows.append(
            UnitRow(
                source_row=row_number,
                unit_code=unit_code,
                name=_cell_text(cell["单元名称"]) or None,
                owner_party_name=_cell_text(cell["主体全称"]) or None,
                project_code=_cell_text(cell["项目编号"]) or None,
                address=_cell_text(cell["地址"]) or None,
                usage_type=_cell_text(cell["业态"]) or None,
                acquisition_mode=acquisition or None,
                managed_from=managed_from,
                managed_to=managed_to,
                land_area=land_area,
                building_area=building_area,
                rentable_area=rentable_area,
            )
        )
    return rows


def _parse_stages(
    cell: dict[str, Any],
    *,
    sheet: str,
    row_number: int,
    parsed: ParsedWorkbook,
) -> StageRowInput | None:
    if not any(_cell_text(cell[c]) != "" for c in STAGE_HEADERS):
        return None
    stage_start = _parse_date(cell["阶段起"])
    stage_end = _parse_date(cell["阶段止"])
    base_rent = _parse_decimal(cell["原定月租(元)"])
    actual_rent = _parse_decimal(cell["实际月租(元)"])
    increase_percent = _parse_decimal(cell["递增%"])
    free_months = _parse_decimal(cell["免租月数"])
    discount = _parse_decimal(cell["减免额(元)"])
    cycle = _cell_text(cell["阶段周期"])
    due_day_text = _cell_text(cell["缴租日"])
    due_day: int | None = None
    if due_day_text != "":
        try:
            due_day = int(float(due_day_text))
        except ValueError:
            due_day = -1

    failed = False
    if stage_start is None or stage_end is None:
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_DATE_INVALID_ERROR",
            "阶段起/阶段止缺失或格式错误",
        )
        failed = True
    elif stage_end < stage_start:
        _issue(parsed, sheet, row_number, "STAGE_RANGE_ERROR", "阶段止早于阶段起")
        failed = True
    if base_rent is None or base_rent < 0:
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_BASE_RENT_INVALID_ERROR",
            "原定月租缺失或为负",
        )
        failed = True
    if actual_rent is None or actual_rent < 0:
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_ACTUAL_RENT_INVALID_ERROR",
            "实际月租缺失或为负",
        )
        failed = True
    if increase_percent is None or not 0 <= increase_percent <= 100:
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_INCREASE_INVALID_ERROR",
            "递增%须在 0–100 之间",
        )
        failed = True
    if free_months is not None and free_months < 0:
        _issue(
            parsed, sheet, row_number, "STAGE_FREE_MONTHS_INVALID_ERROR", "免租月数为负"
        )
        failed = True
    if discount is not None and discount < 0:
        _issue(parsed, sheet, row_number, "STAGE_DISCOUNT_INVALID_ERROR", "减免额为负")
        failed = True
    if cycle == "":
        cycle = "monthly"
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_CYCLE_MISSING_WARNING",
            "阶段周期为空，按 monthly 处理",
        )
    elif cycle not in PAYMENT_CYCLES:
        _issue(
            parsed,
            sheet,
            row_number,
            "STAGE_CYCLE_INVALID_ERROR",
            f"阶段周期无效: {cycle}（可选 {PAYMENT_CYCLES}）",
        )
        failed = True
    if due_day is None or not 1 <= due_day <= 31:
        _issue(
            parsed, sheet, row_number, "STAGE_DUE_DAY_INVALID_ERROR", "缴租日须为 1–31"
        )
        failed = True
    if failed:
        return None
    # failed 为 False 时上述校验已保证这些值非 None；cast 仅做类型收窄。
    from typing import cast

    return StageRowInput(
        stage_start=cast("date", stage_start),
        stage_end=cast("date", stage_end),
        base_monthly_rent=cast("Decimal", base_rent),
        increase_rate=cast("Decimal", increase_percent) / Decimal("100"),
        free_rent_months=free_months or Decimal("0"),
        discount_amount=discount or Decimal("0"),
        actual_monthly_rent=cast("Decimal", actual_rent),
        payment_cycle=cycle,
        due_day=cast("int", due_day),
        source_row=row_number,
    )


def _merge_text(
    parsed: ParsedWorkbook,
    sheet: str,
    row_number: int,
    first_row: int,
    label: str,
    row: ContractRow,
    attr: str,
    value: str,
) -> None:
    if value == "":
        return
    current = getattr(row, attr)
    if current is not None and current != value:
        _issue(
            parsed,
            sheet,
            row_number,
            "CONTRACT_MAIN_FIELD_CONFLICT_ERROR",
            f"{label}与第 {first_row} 行不一致: {value!r} vs {current!r}",
        )
        return
    setattr(row, attr, value)


def _merge_decimal(
    parsed: ParsedWorkbook,
    sheet: str,
    row_number: int,
    first_row: int,
    label: str,
    row: ContractRow,
    attr: str,
    value: Decimal | None,
) -> None:
    if value is None:
        return
    current = getattr(row, attr)
    if current is not None and current != value:
        _issue(
            parsed,
            sheet,
            row_number,
            "CONTRACT_MAIN_FIELD_CONFLICT_ERROR",
            f"{label}与第 {first_row} 行不一致",
        )
        return
    setattr(row, attr, value)


def _parse_contracts(
    sheet: Any,
    parsed: ParsedWorkbook,
    *,
    sheet_name: str,
) -> list[ContractRow]:
    is_upstream = sheet_name == UPSTREAM_SHEET
    main_headers = UPSTREAM_MAIN_HEADERS if is_upstream else TERMINAL_MAIN_HEADERS
    by_number: dict[str, ContractRow] = {}
    order: list[ContractRow] = []

    for row_number, values in enumerate(
        sheet.iter_rows(min_row=3, values_only=True), start=3
    ):
        if _row_is_empty(values):
            continue
        cell = dict(zip(main_headers + STAGE_HEADERS, values, strict=False))
        contract_number = _cell_text(cell["合同编号"])
        if contract_number == "":
            _issue(
                parsed,
                sheet_name,
                row_number,
                "CONTRACT_NUMBER_MISSING_ERROR",
                "合同编号为空",
            )
            continue
        row = by_number.get(contract_number)
        if row is None:
            row = ContractRow(
                source_rows=(row_number,), contract_number=contract_number
            )
            by_number[contract_number] = row
            order.append(row)
        else:
            row.source_rows = row.source_rows + (row_number,)
        first_row = row.source_rows[0]

        _merge_text(
            parsed,
            sheet_name,
            row_number,
            first_row,
            "扫描件文件名",
            row,
            "scan_file_name",
            _cell_text(cell["扫描件文件名"]),
        )
        start = _parse_date(cell["开始日"])
        end = _parse_date(cell["结束日"])
        if _cell_text(cell["开始日"]) != "" and start is None:
            _issue(
                parsed,
                sheet_name,
                row_number,
                "CONTRACT_DATE_INVALID_ERROR",
                "开始日格式错误",
            )
        if _cell_text(cell["结束日"]) != "" and end is None:
            _issue(
                parsed,
                sheet_name,
                row_number,
                "CONTRACT_DATE_INVALID_ERROR",
                "结束日格式错误",
            )
        if start is not None:
            if row.start_date is None:
                row.start_date = start
            elif row.start_date != start:
                _issue(
                    parsed,
                    sheet_name,
                    row_number,
                    "CONTRACT_MAIN_FIELD_CONFLICT_ERROR",
                    f"开始日与第 {first_row} 行不一致",
                )
        if end is not None:
            if row.end_date is None:
                row.end_date = end
            elif row.end_date != end:
                _issue(
                    parsed,
                    sheet_name,
                    row_number,
                    "CONTRACT_MAIN_FIELD_CONFLICT_ERROR",
                    f"结束日与第 {first_row} 行不一致",
                )

        unit_refs = [
            code.strip()
            for code in _cell_text(cell["单元编号"]).split(",")
            if code.strip() != ""
        ]
        for unit_code in unit_refs:
            if unit_code in row.unit_codes:
                _issue(
                    parsed,
                    sheet_name,
                    row_number,
                    "CONTRACT_UNIT_DUPLICATE_ERROR",
                    f"同一合同重复引用单元: {unit_code}",
                )
            else:
                row.unit_codes.append(unit_code)

        if is_upstream:
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "名称",
                row,
                "name",
                _cell_text(cell["名称"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "类型",
                row,
                "contract_type",
                _cell_text(cell["类型"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "主体全称",
                row,
                "owner_party_name",
                _cell_text(cell["主体全称"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "运营主体全称",
                row,
                "operator_party_name",
                _cell_text(cell["运营主体全称"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "周期",
                row,
                "payment_cycle",
                _cell_text(cell["周期"]),
            )
            _merge_decimal(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "保证金(元)",
                row,
                "deposit_amount",
                _parse_decimal(cell["保证金(元)"]),
            )
            _merge_decimal(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "管理费率(如0.0225)",
                row,
                "management_fee_rate",
                _parse_decimal(cell["管理费率(如0.0225)"]),
            )
            payment_day_text = _cell_text(cell["付款日"])
            if payment_day_text != "":
                try:
                    day = int(float(payment_day_text))
                except ValueError:
                    day = -1
                if not 1 <= day <= 31:
                    _issue(
                        parsed,
                        sheet_name,
                        row_number,
                        "CONTRACT_PAY_DAY_INVALID_ERROR",
                        "付款日须为 1–31",
                    )
                elif row.payment_day is not None and row.payment_day != day:
                    _issue(
                        parsed,
                        sheet_name,
                        row_number,
                        "CONTRACT_MAIN_FIELD_CONFLICT_ERROR",
                        f"付款日与第 {first_row} 行不一致",
                    )
                else:
                    row.payment_day = day
        else:
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "模式",
                row,
                "contract_mode",
                _cell_text(cell["模式"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "租户主体全称",
                row,
                "tenant_party_name",
                _cell_text(cell["租户主体全称"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "出租方主体全称",
                row,
                "lessor_party_name",
                _cell_text(cell["出租方主体全称"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "上游合同编号",
                row,
                "upstream_contract_number",
                _cell_text(cell["上游合同编号"]),
            )
            _merge_text(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "收租方",
                row,
                "rent_collector",
                _cell_text(cell["收租方"]),
            )
            _merge_decimal(
                parsed,
                sheet_name,
                row_number,
                first_row,
                "押金(元)",
                row,
                "deposit_amount",
                _parse_decimal(cell["押金(元)"]),
            )

        stage = _parse_stages(
            cell, sheet=sheet_name, row_number=row_number, parsed=parsed
        )
        if stage is not None:
            row.stages.append(stage)

        if _row_contributes_nothing(row, cell, stage is not None):
            _issue(
                parsed,
                sheet_name,
                row_number,
                "CONTRACT_ROW_EMPTY_ERROR",
                f"第 {row_number} 行除合同编号外无有效内容",
            )
    return order


def _row_contributes_nothing(
    row: ContractRow,
    cell: dict[str, Any],
    row_has_stage: bool,
) -> bool:
    content_columns = (
        "名称",
        "类型",
        "主体全称",
        "运营主体全称",
        "周期",
        "付款日",
        "保证金(元)",
        "管理费率(如0.0225)",
        "模式",
        "租户主体全称",
        "出租方主体全称",
        "上游合同编号",
        "押金(元)",
        "收租方",
        "开始日",
        "结束日",
        "扫描件文件名",
        "单元编号",
    )
    has_content = any(_cell_text(cell.get(c)) != "" for c in content_columns)
    return not has_content and not row_has_stage


def _validate_cross_rows(
    parsed: ParsedWorkbook,
    upstreams: list[ContractRow],
    terminals: list[ContractRow],
) -> None:
    unit_codes = {unit.unit_code for unit in parsed.units}
    for row in upstreams:
        _validate_contract_row(parsed, row, UPSTREAM_SHEET, unit_codes)
    for row in terminals:
        _validate_contract_row(parsed, row, TERMINAL_SHEET, unit_codes)


def _validate_contract_row(
    parsed: ParsedWorkbook,
    row: ContractRow,
    sheet: str,
    unit_codes: set[str],
) -> None:
    first_row = row.source_rows[0]
    if row.start_date is not None and row.end_date is not None:
        if row.end_date < row.start_date:
            _issue(
                parsed,
                sheet,
                first_row,
                "CONTRACT_PERIOD_INVALID_ERROR",
                f"{row.contract_number} 结束日早于开始日",
            )

    if parsed.mode == "create":
        for label, value, code in (
            ("开始日", row.start_date, "CONTRACT_START_MISSING_ERROR"),
            ("结束日", row.end_date, "CONTRACT_END_MISSING_ERROR"),
            ("扫描件文件名", row.scan_file_name, "CONTRACT_SCAN_MISSING_ERROR"),
        ):
            if value is None:
                _issue(
                    parsed, sheet, first_row, code, f"{row.contract_number} 缺少{label}"
                )
        if not row.unit_codes:
            _issue(
                parsed,
                sheet,
                first_row,
                "CONTRACT_UNIT_MISSING_ERROR",
                f"{row.contract_number} 未引用任何单元编号",
            )
        if not row.stages:
            _issue(
                parsed,
                sheet,
                first_row,
                "CONTRACT_STAGE_MISSING_ERROR",
                f"{row.contract_number} 无租金阶段行",
            )
        if sheet == UPSTREAM_SHEET:
            if row.contract_type is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_TYPE_MISSING_ERROR",
                    f"{row.contract_number} 缺少类型",
                )
            if row.name is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_NAME_MISSING_ERROR",
                    f"{row.contract_number} 缺少名称",
                )
            if row.owner_party_name is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_OWNER_MISSING_ERROR",
                    f"{row.contract_number} 缺少主体全称",
                )
            if row.operator_party_name is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_OPERATOR_MISSING_ERROR",
                    f"{row.contract_number} 缺少运营主体全称",
                )
            if row.contract_type == "lease" and row.payment_cycle in (None, ""):
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_CYCLE_MISSING_ERROR",
                    f"{row.contract_number} lease 类型必须提供周期",
                )
            if (
                row.contract_type == "management_agreement"
                and row.management_fee_rate is None
            ):
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_FEE_RATE_MISSING_ERROR",
                    f"{row.contract_number} management_agreement 必须提供管理费率",
                )
        else:
            if row.contract_mode is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_MODE_MISSING_ERROR",
                    f"{row.contract_number} 缺少模式",
                )
            if row.tenant_party_name is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_TENANT_MISSING_ERROR",
                    f"{row.contract_number} 缺少租户主体全称",
                )
            if row.lessor_party_name is None:
                _issue(
                    parsed,
                    sheet,
                    first_row,
                    "CONTRACT_LESSOR_MISSING_ERROR",
                    f"{row.contract_number} 缺少出租方主体全称",
                )

    if sheet == TERMINAL_SHEET and row.rent_collector is not None:
        _issue(
            parsed,
            sheet,
            first_row,
            "RENT_COLLECTOR_DERIVED_WARNING",
            f"{row.contract_number} 收租方按模式派生，填写值已忽略",
        )

    if parsed.mode == "update" and row.stages:
        _issue(
            parsed,
            sheet,
            first_row,
            "STAGES_NOT_UPDATABLE_WARNING",
            f"{row.contract_number} 阶段列不走导入更新，已忽略",
        )

    # 阶段覆盖完整性：阶段须无缝覆盖合同期（create 模式）。
    if parsed.mode == "create" and row.stages and row.start_date and row.end_date:
        stages = sorted(row.stages, key=lambda s: s.stage_start)
        cursor: date | None = None
        for stage in stages:
            if cursor is not None:
                if stage.stage_start <= cursor:
                    _issue(
                        parsed,
                        sheet,
                        stage.source_row,
                        "RENT_SCHEDULE_OVERLAP_ERROR",
                        f"{row.contract_number} 阶段重叠: {stage.stage_start}",
                    )
                elif stage.stage_start > cursor + timedelta(days=1):
                    _issue(
                        parsed,
                        sheet,
                        stage.source_row,
                        "RENT_SCHEDULE_GAP_ERROR",
                        f"{row.contract_number} 阶段空洞: "
                        f"{cursor + timedelta(days=1)} ~ "
                        f"{stage.stage_start - timedelta(days=1)}",
                    )
                cursor = max(cursor, stage.stage_end)
            else:
                cursor = stage.stage_end
        if stages[0].stage_start > row.start_date:
            _issue(
                parsed,
                sheet,
                stages[0].source_row,
                "RENT_SCHEDULE_GAP_ERROR",
                f"{row.contract_number} 首阶段晚于合同开始日",
            )
        if cursor is not None and cursor < row.end_date:
            _issue(
                parsed,
                sheet,
                stages[-1].source_row,
                "RENT_SCHEDULE_GAP_ERROR",
                f"{row.contract_number} 末阶段早于合同结束日",
            )
