from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...constants.rent_contract_constants import SettlementStatus
from ...crud.rent_contract import rent_contract, rent_ledger
from ...models.rent_contract import (
    ContractType,
    RentContract,
    RentContractHistory,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
)


class RentContractHelperMixin:
    """租金合同服务公共辅助方法"""

    async def _check_asset_rent_conflicts_async(
        self,
        db: AsyncSession,
        *,
        asset_ids: list[str],
        start_date: date,
        end_date: date,
        exclude_contract_id: str | None = None,
    ) -> list[dict[str, Any]]:
        conflicts = []

        existing_contracts = await rent_contract.get_active_with_assets_async(
            db,
            exclude_contract_id=exclude_contract_id,
        )

        for contract in existing_contracts:
            contract_assets = [a.id for a in contract.assets]
            overlapping_assets = set(asset_ids) & set(contract_assets)

            if overlapping_assets:
                if start_date <= contract.end_date and end_date >= contract.start_date:
                    overlapping_asset_names = [
                        a.asset_name
                        if getattr(a, "asset_name", None)
                        else getattr(a, "name", None)
                        for a in contract.assets
                        if a.id in overlapping_assets
                    ]

                    conflicts.append(
                        {
                            "contract_id": contract.id,
                            "contract_number": contract.contract_number,
                            "contract_start_date": contract.start_date.isoformat(),
                            "contract_end_date": contract.end_date.isoformat(),
                            "asset_ids": list(overlapping_assets),
                            "asset_name": overlapping_asset_names[0]
                            if overlapping_asset_names
                            else "未知",
                        }
                    )

        return conflicts

    async def _create_history_async(
        self,
        db: AsyncSession,
        contract_id: str,
        change_type: str,
        change_description: str,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContractHistory:
        history = RentContractHistory()
        history.contract_id = contract_id
        history.change_type = change_type
        history.change_description = change_description
        history.old_data = old_data
        history.new_data = new_data
        history.operator = operator
        history.operator_id = operator_id
        db.add(history)
        await db.commit()
        return history

    def _generate_month_range(self, start_month: str, end_month: str) -> list[str]:
        """生成月份范围"""
        start_year, start_month_num = map(int, start_month.split("-"))
        end_year, end_month_num = map(int, end_month.split("-"))

        months = []
        current_year, current_month = start_year, start_month_num

        while (current_year < end_year) or (
            current_year == end_year and current_month <= end_month_num
        ):
            months.append(f"{current_year}-{current_month:02d}")
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return months

    def _get_rent_term_for_date(
        self, rent_terms: list[RentTerm], target_date: date
    ) -> RentTerm | None:
        """获取指定日期的租金条款"""
        for term in rent_terms:
            if term.start_date <= target_date <= term.end_date:
                return term
        return None

    def _calculate_due_date(self, month_date: date, contract: RentContract) -> date:
        """计算应缴日期（默认每月1号）"""
        return month_date.replace(day=1)

    async def _calculate_service_fee_for_ledger_async(
        self, db: AsyncSession, ledger: RentLedger
    ) -> ServiceFeeLedger | None:
        contract = await rent_contract.get_async(db, id=ledger.contract_id)
        if not contract:
            return None

        if contract.contract_type != ContractType.ENTRUSTED:
            return None

        if not contract.service_fee_rate or contract.service_fee_rate <= 0:
            return None

        existing = await rent_ledger.get_service_fee_by_source_ledger_async(
            db,
            source_ledger_id=ledger.id,
        )
        if existing:
            existing.paid_rent_amount = ledger.paid_amount
            existing.fee_amount = ledger.paid_amount * contract.service_fee_rate
            return existing

        fee_amount = ledger.paid_amount * contract.service_fee_rate

        service_fee = ServiceFeeLedger()
        service_fee.contract_id = contract.id
        service_fee.source_ledger_id = ledger.id
        service_fee.year_month = ledger.year_month
        service_fee.paid_rent_amount = ledger.paid_amount
        service_fee.fee_rate = contract.service_fee_rate
        service_fee.fee_amount = fee_amount
        service_fee.settlement_status = SettlementStatus.UNSETTLED
        service_fee.notes = (
            f"自动生成：基于租金台账 {ledger.year_month} 实收 {ledger.paid_amount}"
        )
        db.add(service_fee)
        return service_fee
