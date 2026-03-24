"""合同台账补偿服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.services.contract.ledger_service_v2 import (
    compute_expected_year_months,
    ledger_service_v2,
)
from src.services.contract.service_fee_ledger_service import service_fee_ledger_service


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class LedgerCompensationService:
    """扫描活跃合同并补齐缺失台账。"""

    async def run(self, db: AsyncSession) -> dict[str, Any]:
        contracts = await contract_crud.list_active_lease_contracts_for_ledger(db)
        summary: dict[str, Any] = {
            "contracts_scanned": 0,
            "contracts_repaired": 0,
            "rent_entries_created": 0,
            "rent_entries_voided": 0,
            "failures": [],
            "timestamp": _utcnow_iso(),
        }
        contract_group_ids = {
            str(getattr(contract, "contract_group_id", "")).strip()
            for contract in contracts
            if str(getattr(contract, "contract_group_id", "")).strip() != ""
        }

        for contract in contracts:
            contract_id = str(getattr(contract, "contract_id"))
            summary["contracts_scanned"] += 1

            try:
                rent_terms = await contract_group_crud.list_rent_terms_by_contract(
                    db,
                    contract_id=contract_id,
                )
                if not rent_terms:
                    continue

                existing_entries = await contract_group_crud.list_ledger_entries_by_contract(
                    db,
                    contract_id=contract_id,
                )
                expected_months = set(compute_expected_year_months(rent_terms))
                actual_months = {
                    str(entry.year_month)
                    for entry in existing_entries
                    if getattr(entry, "payment_status", None) != "voided"
                }

                if expected_months == actual_months:
                    continue

                result = await ledger_service_v2.recalculate_ledger(
                    db,
                    contract_id=contract_id,
                    commit=False,
                )
                await db.commit()

                summary["contracts_repaired"] += 1
                summary["rent_entries_created"] += int(result.get("created", 0))
                summary["rent_entries_voided"] += int(result.get("voided", 0))
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                summary["failures"].append(
                    {
                        "contract_id": contract_id,
                        "error": str(exc),
                    }
                )

        for group_id in sorted(contract_group_ids):
            try:
                fee_result = await service_fee_ledger_service.sync_contract_group(
                    db,
                    group_id=group_id,
                    commit=False,
                )
                if any(int(fee_result.get(key, 0)) > 0 for key in ("created", "updated", "voided")):
                    await db.commit()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                summary["failures"].append(
                    {
                        "contract_id": group_id,
                        "error": str(exc),
                    }
                )

        return summary


ledger_compensation_service = LedgerCompensationService()
