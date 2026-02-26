"""
Rent contract Excel import/export service.

Provides a minimal, functional implementation for:
- template download
- contract import (contracts + optional terms)
- contract export (contracts + optional terms)
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.enums import ContractStatus
from ...core.exception_handler import BusinessValidationError
from ...crud.rent_contract import rent_contract as rent_contract_crud
from ...crud.rent_contract import rent_ledger as rent_ledger_crud
from ...crud.rent_contract import rent_term as rent_term_crud
from ...models.rent_contract import RentContract
from ...schemas.rent_contract import (
    ContractType,
    PaymentCycle,
    RentContractCreate,
    RentContractUpdate,
    RentTermCreate,
    RentTermUpdate,
)
from ...services.rent_contract import rent_contract_service
from ...utils.file_security import validate_file_path

logger = logging.getLogger(__name__)

CONTRACT_SHEET = "contracts"
TERM_SHEET = "terms"
LEDGER_SHEET = "ledger"

CONTRACT_COLUMNS: dict[str, str] = {
    "contract_number": "合同编号",
    "ownership_id": "权属方ID",
    "contract_type": "合同类型",
    "tenant_name": "承租方名称",
    "sign_date": "签订日期",
    "start_date": "租期开始日期",
    "end_date": "租期结束日期",
    "total_deposit": "押金总额",
    "monthly_rent_base": "基础月租金",
    "payment_cycle": "付款周期",
    "contract_status": "合同状态",
    "asset_ids": "资产ID列表",
    "tenant_contact": "承租方联系人",
    "tenant_phone": "承租方联系电话",
    "tenant_address": "承租方地址",
    "tenant_usage": "用途说明",
    "owner_name": "甲方名称",
    "owner_contact": "甲方联系人",
    "owner_phone": "甲方联系电话",
    "service_fee_rate": "服务费率",
    "payment_terms": "支付条款",
    "contract_notes": "合同备注",
    "upstream_contract_id": "上游合同ID",
}

TERM_COLUMNS: dict[str, str] = {
    "contract_number": "合同编号",
    "start_date": "条款开始日期",
    "end_date": "条款结束日期",
    "monthly_rent": "月租金",
    "management_fee": "管理费",
    "other_fees": "其他费用",
    "total_monthly_amount": "月总金额",
    "rent_description": "租金描述",
}

LEDGER_COLUMNS: dict[str, str] = {
    "contract_number": "合同编号",
    "year_month": "账期",
    "due_date": "应收日期",
    "amount_due": "应收金额",
    "payment_status": "支付状态",
    "paid_date": "实际收款日期",
    "remarks": "备注",
}

CONTRACT_TYPE_ALIASES = {
    "上游租赁": ContractType.LEASE_UPSTREAM.value,
    "下游租赁": ContractType.LEASE_DOWNSTREAM.value,
    "委托运营": ContractType.ENTRUSTED.value,
}

PAYMENT_CYCLE_ALIASES = {
    "月付": PaymentCycle.MONTHLY.value,
    "季付": PaymentCycle.QUARTERLY.value,
    "半年付": PaymentCycle.SEMI_ANNUAL.value,
    "年付": PaymentCycle.ANNUAL.value,
}

CONTRACT_STATUS_ALIASES = {
    "草稿": ContractStatus.DRAFT.value,
    "待审核": ContractStatus.PENDING.value,
    "执行中": ContractStatus.ACTIVE.value,
    "有效": ContractStatus.ACTIVE.value,
    "即将到期": ContractStatus.EXPIRING.value,
    "已到期": ContractStatus.EXPIRED.value,
    "到期": ContractStatus.EXPIRED.value,
    "终止": ContractStatus.TERMINATED.value,
    "已终止": ContractStatus.TERMINATED.value,
    "已续签": ContractStatus.RENEWED.value,
}


def _is_nan(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _parse_date(value: Any) -> date | None:
    if value is None or _is_nan(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    if _is_nan(parsed):
        return None
    if isinstance(parsed, datetime):
        return parsed.date()
    if isinstance(parsed, date):
        return parsed
    return None


def _parse_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    if value is None or _is_nan(value):
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _normalize_enum(value: Any, aliases: dict[str, str], default: str) -> str:
    if value is None or _is_nan(value):
        return default
    if isinstance(value, str):
        normalized = value.strip()
        if normalized in aliases:
            return aliases[normalized]
        return normalized
    return default


def _parse_asset_ids(value: Any) -> list[str]:
    if value is None or _is_nan(value):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    raw = str(value)
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]


def _map_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    reverse_mapping = {v: k for k, v in mapping.items()}
    normalized_columns: dict[str, str] = {}
    for column in df.columns:
        key = reverse_mapping.get(str(column).strip(), str(column).strip())
        normalized_columns[column] = key
    return df.rename(columns=normalized_columns)


class RentContractExcelService:
    """Rent contract Excel import/export service."""

    def _template_dir(self) -> Path:
        path = Path("temp_uploads") / "rent_contract_templates"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _export_dir(self) -> Path:
        path = Path("temp_uploads") / "rent_contract_exports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _cleanup_file(self, file_path: str) -> None:
        allowed_dirs = [
            str(Path("temp_uploads").resolve()),
            tempfile.gettempdir(),
        ]
        if not validate_file_path(file_path, allowed_dirs):
            return
        Path(file_path).unlink(missing_ok=True)

    def download_contract_template(self) -> dict[str, Any]:
        filename = f"rent_contract_template_{uuid.uuid4().hex[:8]}.xlsx"
        file_path = self._template_dir() / filename

        contracts_df = pd.DataFrame(columns=list(CONTRACT_COLUMNS.values()))
        terms_df = pd.DataFrame(columns=list(TERM_COLUMNS.values()))
        ledger_df = pd.DataFrame(columns=list(LEDGER_COLUMNS.values()))

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            contracts_df.to_excel(writer, sheet_name=CONTRACT_SHEET, index=False)
            terms_df.to_excel(writer, sheet_name=TERM_SHEET, index=False)
            ledger_df.to_excel(writer, sheet_name=LEDGER_SHEET, index=False)

        return {
            "success": True,
            "message": "模板生成成功",
            "file_path": str(file_path),
            "file_name": "租金合同导入模板.xlsx",
            "file_size": file_path.stat().st_size,
        }

    async def import_contracts_from_excel(
        self,
        *,
        db: AsyncSession,
        file_path: str,
        import_terms: bool = True,
        import_ledger: bool = False,
        overwrite_existing: bool = False,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        imported_contracts = 0
        imported_terms = 0

        try:
            contracts_df = pd.read_excel(file_path, sheet_name=CONTRACT_SHEET)
        except Exception as exc:
            raise BusinessValidationError(f"读取合同表失败: {exc}")

        contracts_df = _map_columns(contracts_df, CONTRACT_COLUMNS)

        terms_map: dict[str, list[dict[str, Any]]] = {}
        if import_terms:
            try:
                terms_df = pd.read_excel(file_path, sheet_name=TERM_SHEET)
                terms_df = _map_columns(terms_df, TERM_COLUMNS)
                for _, row in terms_df.iterrows():
                    row_dict = {k: row[k] for k in terms_df.columns}
                    contract_number = str(row_dict.get("contract_number", "")).strip()
                    if not contract_number:
                        continue
                    terms_map.setdefault(contract_number, []).append(row_dict)
            except Exception:
                warnings.append("未找到租金条款表，已按基础月租金生成默认条款。")

        contract_numbers_to_check = {
            str(value).strip()
            for value in contracts_df.get("contract_number", pd.Series())
            if value is not None and str(value).strip() != ""
        }
        existing_by_contract_number: dict[str, RentContract] = {}
        if contract_numbers_to_check:
            existing_contracts = await rent_contract_crud.get_by_contract_numbers_async(
                db,
                contract_numbers=list(contract_numbers_to_check),
            )
            existing_by_contract_number = {
                str(contract.contract_number): contract
                for contract in existing_contracts
            }

        for index, row in contracts_df.iterrows():
            row_data = {k: row[k] for k in contracts_df.columns}
            contract_number_raw = row_data.get("contract_number")
            contract_number = (
                str(contract_number_raw).strip() if contract_number_raw else ""
            )
            ownership_id_raw = row_data.get("ownership_id")
            ownership_id = str(ownership_id_raw).strip() if ownership_id_raw else ""
            tenant_name_raw = row_data.get("tenant_name")
            tenant_name = str(tenant_name_raw).strip() if tenant_name_raw else ""

            sign_date = _parse_date(row_data.get("sign_date"))
            start_date = _parse_date(row_data.get("start_date"))
            end_date = _parse_date(row_data.get("end_date"))

            missing_fields = []
            if not contract_number:
                missing_fields.append("合同编号")
            if not ownership_id:
                missing_fields.append("权属方ID")
            if not tenant_name:
                missing_fields.append("承租方名称")
            if sign_date is None:
                missing_fields.append("签订日期")
            if start_date is None:
                missing_fields.append("租期开始日期")
            if end_date is None:
                missing_fields.append("租期结束日期")

            if missing_fields:
                errors.append(
                    f"第 {index + 2} 行缺少字段: {', '.join(missing_fields)}"
                )
                continue
            try:
                assert sign_date is not None
                assert start_date is not None
                assert end_date is not None

                contract_type = ContractType(
                    _normalize_enum(
                        row_data.get("contract_type"),
                        CONTRACT_TYPE_ALIASES,
                        ContractType.LEASE_DOWNSTREAM.value,
                    )
                )
                payment_cycle = PaymentCycle(
                    _normalize_enum(
                        row_data.get("payment_cycle"),
                        PAYMENT_CYCLE_ALIASES,
                        PaymentCycle.MONTHLY.value,
                    )
                )
                contract_status = ContractStatus(
                    _normalize_enum(
                        row_data.get("contract_status"),
                        CONTRACT_STATUS_ALIASES,
                        ContractStatus.ACTIVE.value,
                    )
                )

                asset_ids = _parse_asset_ids(row_data.get("asset_ids"))

                base_rent = (
                    _parse_decimal(row_data.get("monthly_rent_base"), Decimal("0"))
                    or Decimal("0")
                )
                total_deposit = (
                    _parse_decimal(row_data.get("total_deposit"), Decimal("0"))
                    or Decimal("0")
                )
                service_fee_rate = _parse_decimal(row_data.get("service_fee_rate"))

                term_rows = terms_map.get(contract_number, [])
                terms: list[RentTermCreate] = []
                if term_rows:
                    for term_row in term_rows:
                        term_start = _parse_date(term_row.get("start_date"))
                        term_end = _parse_date(term_row.get("end_date"))
                        if term_start is None or term_end is None:
                            continue
                        term = RentTermCreate(
                            start_date=term_start,
                            end_date=term_end,
                            monthly_rent=(
                                _parse_decimal(
                                    term_row.get("monthly_rent"), Decimal("0")
                                )
                                or Decimal("0")
                            ),
                            management_fee=(
                                _parse_decimal(
                                    term_row.get("management_fee"), Decimal("0")
                                )
                                or Decimal("0")
                            ),
                            other_fees=(
                                _parse_decimal(
                                    term_row.get("other_fees"), Decimal("0")
                                )
                                or Decimal("0")
                            ),
                            total_monthly_amount=_parse_decimal(
                                term_row.get("total_monthly_amount")
                            ),
                            rent_description=(
                                str(term_row.get("rent_description")).strip()
                                if term_row.get("rent_description") is not None
                                else None
                            ),
                        )
                        terms.append(term)

                if not terms:
                    terms = [
                        RentTermCreate(
                            start_date=start_date,
                            end_date=end_date,
                            monthly_rent=base_rent,
                            management_fee=Decimal("0"),
                            other_fees=Decimal("0"),
                            total_monthly_amount=None,
                            rent_description=None,
                        )
                    ]
                    warnings.append(
                        f"合同 {contract_number} 未提供条款，已生成默认条款。"
                    )

                contract_data = RentContractCreate(
                    contract_number=contract_number,
                    ownership_id=ownership_id,
                    contract_type=contract_type,
                    tenant_name=tenant_name,
                    sign_date=sign_date,
                    start_date=start_date,
                    end_date=end_date,
                    total_deposit=total_deposit,
                    monthly_rent_base=base_rent,
                    payment_cycle=payment_cycle,
                    contract_status=contract_status,
                    asset_ids=asset_ids,
                    tenant_contact=(
                        str(row_data.get("tenant_contact")).strip()
                        if row_data.get("tenant_contact") is not None
                        else None
                    ),
                    tenant_phone=(
                        str(row_data.get("tenant_phone")).strip()
                        if row_data.get("tenant_phone") is not None
                        else None
                    ),
                    tenant_address=(
                        str(row_data.get("tenant_address")).strip()
                        if row_data.get("tenant_address") is not None
                        else None
                    ),
                    tenant_usage=(
                        str(row_data.get("tenant_usage")).strip()
                        if row_data.get("tenant_usage") is not None
                        else None
                    ),
                    owner_name=(
                        str(row_data.get("owner_name")).strip()
                        if row_data.get("owner_name") is not None
                        else None
                    ),
                    owner_contact=(
                        str(row_data.get("owner_contact")).strip()
                        if row_data.get("owner_contact") is not None
                        else None
                    ),
                    owner_phone=(
                        str(row_data.get("owner_phone")).strip()
                        if row_data.get("owner_phone") is not None
                        else None
                    ),
                    service_fee_rate=service_fee_rate,
                    payment_terms=(
                        str(row_data.get("payment_terms")).strip()
                        if row_data.get("payment_terms") is not None
                        else None
                    ),
                    contract_notes=(
                        str(row_data.get("contract_notes")).strip()
                        if row_data.get("contract_notes") is not None
                        else None
                    ),
                    upstream_contract_id=(
                        str(row_data.get("upstream_contract_id")).strip()
                        if row_data.get("upstream_contract_id") is not None
                        else None
                    ),
                    rent_terms=terms,
                )

                existing = existing_by_contract_number.get(contract_number)
                if existing:
                    if not overwrite_existing:
                        errors.append(f"合同编号已存在: {contract_number}")
                        continue
                    update_data = RentContractUpdate(
                        **contract_data.model_dump(exclude={"rent_terms"})
                    )
                    update_data.rent_terms = [
                        RentTermUpdate(**term.model_dump()) for term in terms
                    ]
                    updated_contract = await rent_contract_service.update_contract_async(
                        db=db, db_obj=existing, obj_in=update_data
                    )
                    existing_by_contract_number[contract_number] = updated_contract
                else:
                    created_contract = await rent_contract_service.create_contract_async(
                        db=db, obj_in=contract_data
                    )
                    existing_by_contract_number[contract_number] = created_contract

                imported_contracts += 1
                imported_terms += len(terms)
            except Exception as exc:
                await db.rollback()
                errors.append(f"第 {index + 2} 行导入失败: {exc}")
                continue

        if import_ledger:
            warnings.append("台账导入暂未实现，已跳过台账数据。")

        success = imported_contracts > 0 and len(errors) == 0
        return {
            "success": success,
            "message": "导入完成" if success else "导入完成，但存在错误",
            "imported_contracts": imported_contracts,
            "imported_terms": imported_terms,
            "imported_ledgers": 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def export_contracts_to_excel(
        self,
        *,
        db: AsyncSession,
        contract_ids: list[str] | None = None,
        include_terms: bool = True,
        include_ledger: bool = True,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        export_dir = self._export_dir()
        file_name = f"rent_contract_export_{uuid.uuid4().hex[:8]}.xlsx"
        file_path = export_dir / file_name

        contracts = await rent_contract_crud.get_export_contracts_async(
            db,
            contract_ids=contract_ids,
            start_date=start_date,
            end_date=end_date,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
        )

        contract_rows: list[dict[str, Any]] = []
        for contract in contracts:
            assets = []
            if hasattr(contract, "assets"):
                assets = [str(asset.id) for asset in contract.assets]
            contract_rows.append(
                {
                    CONTRACT_COLUMNS["contract_number"]: contract.contract_number,
                    CONTRACT_COLUMNS["ownership_id"]: contract.ownership_id,
                    CONTRACT_COLUMNS["contract_type"]: str(contract.contract_type),
                    CONTRACT_COLUMNS["tenant_name"]: contract.tenant_name,
                    CONTRACT_COLUMNS["sign_date"]: contract.sign_date,
                    CONTRACT_COLUMNS["start_date"]: contract.start_date,
                    CONTRACT_COLUMNS["end_date"]: contract.end_date,
                    CONTRACT_COLUMNS["total_deposit"]: contract.total_deposit,
                    CONTRACT_COLUMNS["monthly_rent_base"]: contract.monthly_rent_base,
                    CONTRACT_COLUMNS["payment_cycle"]: str(contract.payment_cycle),
                    CONTRACT_COLUMNS["contract_status"]: str(contract.contract_status),
                    CONTRACT_COLUMNS["asset_ids"]: ",".join(assets),
                    CONTRACT_COLUMNS["tenant_contact"]: contract.tenant_contact,
                    CONTRACT_COLUMNS["tenant_phone"]: contract.tenant_phone,
                    CONTRACT_COLUMNS["tenant_address"]: contract.tenant_address,
                    CONTRACT_COLUMNS["tenant_usage"]: contract.tenant_usage,
                    CONTRACT_COLUMNS["owner_name"]: contract.owner_name,
                    CONTRACT_COLUMNS["owner_contact"]: contract.owner_contact,
                    CONTRACT_COLUMNS["owner_phone"]: contract.owner_phone,
                    CONTRACT_COLUMNS["service_fee_rate"]: contract.service_fee_rate,
                    CONTRACT_COLUMNS["payment_terms"]: contract.payment_terms,
                    CONTRACT_COLUMNS["contract_notes"]: contract.contract_notes,
                    CONTRACT_COLUMNS["upstream_contract_id"]: contract.upstream_contract_id,
                }
            )

        terms_df = pd.DataFrame(columns=list(TERM_COLUMNS.values()))
        if include_terms and contracts:
            term_rows: list[dict[str, Any]] = []
            contract_ids_lookup = [contract.id for contract in contracts]
            terms = await rent_term_crud.get_by_contract_ids_async(
                db,
                contract_ids=contract_ids_lookup,
            )
            contract_number_map = {
                contract.id: contract.contract_number for contract in contracts
            }
            for term in terms:
                term_rows.append(
                    {
                        TERM_COLUMNS["contract_number"]: contract_number_map.get(
                            term.contract_id
                        ),
                        TERM_COLUMNS["start_date"]: term.start_date,
                        TERM_COLUMNS["end_date"]: term.end_date,
                        TERM_COLUMNS["monthly_rent"]: term.monthly_rent,
                        TERM_COLUMNS["management_fee"]: term.management_fee,
                        TERM_COLUMNS["other_fees"]: term.other_fees,
                        TERM_COLUMNS["total_monthly_amount"]: term.total_monthly_amount,
                        TERM_COLUMNS["rent_description"]: term.rent_description,
                    }
                )
            terms_df = pd.DataFrame(term_rows)

        ledger_df = pd.DataFrame(columns=list(LEDGER_COLUMNS.values()))
        if include_ledger and contracts:
            ledger_rows: list[dict[str, Any]] = []
            contract_ids_lookup = [contract.id for contract in contracts]
            ledgers = await rent_ledger_crud.get_by_contract_ids_async(
                db,
                contract_ids=contract_ids_lookup,
            )
            contract_number_map = {
                contract.id: contract.contract_number for contract in contracts
            }
            for ledger in ledgers:
                ledger_rows.append(
                    {
                        LEDGER_COLUMNS["contract_number"]: contract_number_map.get(
                            ledger.contract_id
                        ),
                        LEDGER_COLUMNS["year_month"]: ledger.year_month,
                        LEDGER_COLUMNS["due_date"]: ledger.due_date,
                        LEDGER_COLUMNS["amount_due"]: ledger.due_amount,
                        LEDGER_COLUMNS["payment_status"]: ledger.payment_status,
                        LEDGER_COLUMNS["paid_date"]: ledger.payment_date,
                        LEDGER_COLUMNS["remarks"]: ledger.notes,
                    }
                )
            ledger_df = pd.DataFrame(ledger_rows)

        contracts_df = pd.DataFrame(
            contract_rows, columns=list(CONTRACT_COLUMNS.values())
        )
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            contracts_df.to_excel(writer, sheet_name=CONTRACT_SHEET, index=False)
            if include_terms:
                terms_df.to_excel(writer, sheet_name=TERM_SHEET, index=False)
            if include_ledger:
                ledger_df.to_excel(writer, sheet_name=LEDGER_SHEET, index=False)

        return {
            "success": True,
            "message": "导出成功",
            "file_path": str(file_path),
            "file_name": file_name,
            "file_size": file_path.stat().st_size,
            "stats": {
                "total_contracts": len(contract_rows),
                "total_terms": len(terms_df.index),
                "total_ledgers": len(ledger_df.index),
            },
        }

    def cleanup_file(self, file_path: str) -> None:
        self._cleanup_file(file_path)


rent_contract_excel_service = RentContractExcelService()
