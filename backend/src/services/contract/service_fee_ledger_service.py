"""代理模式服务费台账派生服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import GroupRelationType, RevenueMode


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ServiceFeeLedgerService:
    """从直租租金台账派生代理服务费台账。"""

    async def sync_contract_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        commit: bool = True,
    ) -> dict[str, int]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)
        if getattr(group, "revenue_mode", None) != RevenueMode.AGENCY:
            return {"created": 0, "updated": 0, "voided": 0}

        contracts = await contract_crud.list_by_group(
            db,
            group_id=group_id,
            load_details=True,
        )
        entrusted_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None) == GroupRelationType.ENTRUSTED
            and getattr(contract, "agency_detail", None) is not None
        ]
        if len(entrusted_contracts) != 1:
            raise BusinessValidationError("代理合同组必须且只能有一份委托协议用于服务费比例")

        ratio = Decimal(
            getattr(entrusted_contracts[0].agency_detail, "service_fee_ratio", Decimal("0"))
        )
        direct_lease_contracts = [
            contract
            for contract in contracts
            if getattr(contract, "group_relation_type", None) == GroupRelationType.DIRECT_LEASE
        ]
        existing_entries = await contract_group_crud.list_service_fee_entries_by_group(
            db,
            group_id=group_id,
        )
        existing_by_source = {
            str(entry.source_ledger_id): entry for entry in existing_entries
        }

        created = 0
        updated = 0
        voided = 0
        seen_source_ids: set[str] = set()
        now = _utcnow()

        for contract in direct_lease_contracts:
            source_entries = await contract_group_crud.list_ledger_entries_by_contract(
                db,
                contract_id=str(contract.contract_id),
            )
            for source_entry in source_entries:
                source_id = str(source_entry.entry_id)
                seen_source_ids.add(source_id)

                amount_due = _quantize_money(Decimal(source_entry.amount_due) * ratio)
                paid_amount = _quantize_money(Decimal(source_entry.paid_amount) * ratio)
                existing_entry = existing_by_source.get(source_id)

                if existing_entry is None:
                    await contract_group_crud.create_service_fee_entry(
                        db,
                        data={
                            "contract_group_id": group_id,
                            "agency_contract_id": str(contract.contract_id),
                            "source_ledger_id": source_id,
                            "year_month": str(source_entry.year_month),
                            "amount_due": amount_due,
                            "paid_amount": paid_amount,
                            "payment_status": str(source_entry.payment_status),
                            "currency_code": str(source_entry.currency_code),
                            "service_fee_ratio": ratio,
                            "created_at": now,
                            "updated_at": now,
                        },
                        commit=False,
                    )
                    created += 1
                    continue

                requires_update = any(
                    [
                        existing_entry.amount_due != amount_due,
                        existing_entry.paid_amount != paid_amount,
                        existing_entry.payment_status != source_entry.payment_status,
                        existing_entry.currency_code != source_entry.currency_code,
                        existing_entry.service_fee_ratio != ratio,
                        existing_entry.year_month != source_entry.year_month,
                        existing_entry.agency_contract_id != contract.contract_id,
                    ]
                )
                if not requires_update:
                    continue

                existing_entry.agency_contract_id = str(contract.contract_id)
                existing_entry.year_month = str(source_entry.year_month)
                existing_entry.amount_due = amount_due
                existing_entry.paid_amount = paid_amount
                existing_entry.payment_status = str(source_entry.payment_status)
                existing_entry.currency_code = str(source_entry.currency_code)
                existing_entry.service_fee_ratio = ratio
                existing_entry.updated_at = now
                updated += 1

        for existing_entry in existing_entries:
            if str(existing_entry.source_ledger_id) in seen_source_ids:
                continue
            if existing_entry.payment_status == "voided":
                continue
            existing_entry.payment_status = "voided"
            existing_entry.updated_at = now
            voided += 1

        await db.flush()
        if commit:
            await db.commit()

        return {"created": created, "updated": updated, "voided": voided}


service_fee_ledger_service = ServiceFeeLedgerService()
