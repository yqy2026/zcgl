from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.enums import ContractStatus
from ...crud.rent_contract import rent_contract as rent_contract_crud
from ...crud.rent_contract import rent_ledger as rent_ledger_crud
from ...models.rent_contract import ContractType
from ...schemas.rent_contract import RentStatisticsQuery
from .helpers import RentContractHelperMixin


class RentContractStatisticsService(RentContractHelperMixin):
    """合同统计相关服务"""

    async def get_statistics_async(
        self, db: AsyncSession, *, query_params: RentStatisticsQuery
    ) -> dict[str, Any]:
        # 使用 CRUD 方法获取总体统计
        total_due, total_paid, total_overdue, total_records = (
            await rent_ledger_crud.get_ledger_statistics_async(
                db,
                start_date=query_params.start_date,
                end_date=query_params.end_date,
                owner_party_ids=query_params.owner_party_ids,
                manager_party_ids=query_params.manager_party_ids,
                ownership_ids=query_params.ownership_ids,  # DEPRECATED alias
                asset_ids=query_params.asset_ids,
            )
        )

        total_due = total_due or Decimal("0")
        total_paid = total_paid or Decimal("0")
        total_overdue = total_overdue or Decimal("0")

        # 使用 CRUD 方法获取支付状态分组统计
        status_stats = await rent_ledger_crud.get_ledger_status_breakdown_async(
            db,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            owner_party_ids=query_params.owner_party_ids,
            manager_party_ids=query_params.manager_party_ids,
            ownership_ids=query_params.ownership_ids,  # DEPRECATED alias
            asset_ids=query_params.asset_ids,
        )

        # 使用 CRUD 方法获取月度分组统计
        monthly_stats = await rent_ledger_crud.get_ledger_monthly_breakdown_async(
            db,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            owner_party_ids=query_params.owner_party_ids,
            manager_party_ids=query_params.manager_party_ids,
            ownership_ids=query_params.ownership_ids,  # DEPRECATED alias
            asset_ids=query_params.asset_ids,
        )

        payment_rate = (total_paid / total_due * 100) if total_due else Decimal("0")

        return {
            "total_due": total_due,
            "total_paid": total_paid,
            "total_overdue": total_overdue,
            "total_records": total_records,
            "payment_rate": payment_rate,
            "average_unit_price": await self._calculate_average_unit_price_async(
                db, query_params
            ),
            "renewal_rate": await self._calculate_renewal_rate_async(db, query_params),
            "status_breakdown": [
                {
                    "status": stat.payment_status,
                    "count": stat.count,
                    "due_amount": stat.due_amount or Decimal("0"),
                    "paid_amount": stat.paid_amount or Decimal("0"),
                }
                for stat in status_stats
            ],
            "monthly_breakdown": [
                {
                    "year_month": stat.year_month,
                    "due_amount": stat.due_amount or Decimal("0"),
                    "paid_amount": stat.paid_amount or Decimal("0"),
                    "overdue_amount": stat.overdue_amount or Decimal("0"),
                }
                for stat in monthly_stats
            ],
        }

    async def get_ownership_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
    ) -> list[dict[str, Any]]:
        owner_party_filter_ids = owner_party_ids
        if owner_party_filter_ids is None and ownership_ids is not None:  # DEPRECATED bridge alias
            owner_party_filter_ids = (
                await rent_contract_crud.get_distinct_owner_party_ids_by_ownership_ids_async(  # DEPRECATED bridge lookup
                    db,
                    ownership_ids=ownership_ids,  # DEPRECATED bridge alias
                )
            )

        owner_party_results = []
        if not (
            owner_party_ids is None
            and ownership_ids is not None  # DEPRECATED bridge alias
            and owner_party_filter_ids == []
        ):
            owner_party_results = await rent_ledger_crud.get_owner_party_statistics_async(
                db,
                start_date=start_date,
                end_date=end_date,
                owner_party_ids=owner_party_filter_ids,
                manager_party_ids=manager_party_ids,
            )

        merged_stats: dict[str, dict[str, Any]] = {}
        for result in owner_party_results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

            merged_stats[str(result.id)] = {
                "owner_party_id": result.id,
                "owner_party_name": result.name,
                "ownership_id": None,  # DEPRECATED: 仅在 legacy ownership 维度回填
                "ownership_name": None,  # DEPRECATED: 仅在 legacy ownership 维度回填
                "total_contracts": result.contract_count,
                "active_contracts": result.contract_count,
                "total_due_amount": total_due,
                "total_paid_amount": total_paid,
                "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                "occupancy_rate": payment_rate,
            }

        legacy_ownership_ids = ownership_ids  # DEPRECATED bridge alias
        if legacy_ownership_ids is None and owner_party_ids:  # DEPRECATED bridge alias
            legacy_ownership_ids = (  # DEPRECATED bridge alias
                await rent_contract_crud.get_distinct_ownership_ids_by_owner_party_ids_async(  # DEPRECATED bridge lookup
                    db,
                    owner_party_ids=owner_party_ids,
                )
            )

        legacy_results = []
        should_query_legacy = True
        if ownership_ids == []:  # DEPRECATED bridge alias
            should_query_legacy = False
        elif owner_party_ids and legacy_ownership_ids == []:  # DEPRECATED bridge alias
            should_query_legacy = False

        if should_query_legacy:
            legacy_results = await rent_ledger_crud.get_ownership_statistics_async(
                db,
                start_date=start_date,
                end_date=end_date,
                manager_party_ids=manager_party_ids,
                ownership_ids=legacy_ownership_ids,  # DEPRECATED alias
                legacy_only=True,
            )
        for result in legacy_results:
            key = str(result.id)
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            total_overdue = result.total_overdue_amount or Decimal("0")
            if key not in merged_stats:
                payment_rate = (
                    (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
                )
                merged_stats[key] = {
                    "owner_party_id": result.id,
                    "owner_party_name": result.name,
                    "ownership_id": result.id,  # DEPRECATED: 兼容旧键
                    "ownership_name": result.name,  # DEPRECATED: 兼容旧键
                    "total_contracts": result.contract_count,
                    "active_contracts": result.contract_count,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": total_overdue,
                    "occupancy_rate": payment_rate,
                }
                continue

            existing = merged_stats[key]
            existing["total_contracts"] = int(existing["total_contracts"]) + int(
                result.contract_count
            )
            existing["active_contracts"] = int(existing["active_contracts"]) + int(
                result.contract_count
            )
            existing["total_due_amount"] = (
                existing["total_due_amount"] + total_due
            )
            existing["total_paid_amount"] = (
                existing["total_paid_amount"] + total_paid
            )
            existing["total_overdue_amount"] = (
                existing["total_overdue_amount"] + total_overdue
            )
            if not existing.get("ownership_name"):
                existing["ownership_name"] = result.name
            if not existing.get("owner_party_name"):
                existing["owner_party_name"] = result.name

            merged_total_due = existing["total_due_amount"]
            merged_total_paid = existing["total_paid_amount"]
            existing["occupancy_rate"] = (
                (merged_total_paid / merged_total_due * 100)
                if merged_total_due > 0
                else Decimal("0")
            )

        return list(merged_stats.values())

    async def get_asset_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        # 使用 CRUD 方法获取资产统计
        results = await rent_ledger_crud.get_asset_statistics_async(
            db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            asset_ids=asset_ids,
        )

        asset_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

            asset_stats.append(
                {
                    "asset_id": result.id,
                    "asset_name": result.property_name,
                    "asset_address": result.address,
                    "contract_count": result.contract_count,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "payment_rate": payment_rate,
                }
            )

        return asset_stats

    async def get_monthly_statistics_async(
        self,
        db: AsyncSession,
        *,
        year: int | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        # 使用 CRUD 方法获取月度统计
        results = await rent_ledger_crud.get_monthly_statistics_async(
            db,
            year=year,
            start_month=start_month,
            end_month=end_month,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
        )

        monthly_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

            monthly_stats.append(
                {
                    "year_month": result.year_month,
                    "total_contracts": result.total_contracts,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "payment_rate": payment_rate,
                }
            )

        return monthly_stats

    async def _calculate_average_unit_price_async(
        self, db: AsyncSession, query_params: RentStatisticsQuery
    ) -> Decimal:
        # 使用 CRUD 方法获取合同列表
        contracts = await rent_contract_crud.get_contracts_for_price_calculation_async(
            db,
            contract_type=ContractType.LEASE_DOWNSTREAM,
            contract_status=ContractStatus.ACTIVE,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            owner_party_ids=query_params.owner_party_ids,
            manager_party_ids=query_params.manager_party_ids,
            ownership_ids=query_params.ownership_ids,  # DEPRECATED alias
        )

        if not contracts:
            return Decimal("0")

        total_rent = Decimal("0")
        total_area = Decimal("0")

        for contract in contracts:
            rent = contract.monthly_rent_base or Decimal("0")
            if rent == 0 and contract.rent_terms:
                rent = contract.rent_terms[0].monthly_rent

            assets = contract.assets
            area = sum((asset.rentable_area or Decimal("0")) for asset in assets)

            if area > 0:
                total_rent += rent
                total_area += area

        if total_area == 0:
            return Decimal("0")

        return (total_rent / total_area).quantize(Decimal("0.00"))

    async def _calculate_renewal_rate_async(
        self, db: AsyncSession, query_params: RentStatisticsQuery
    ) -> Decimal:
        # 使用 CRUD 方法获取合同状态统计
        stats = await rent_contract_crud.get_contract_status_counts_async(
            db,
            owner_party_ids=query_params.owner_party_ids,
            manager_party_ids=query_params.manager_party_ids,
            ownership_ids=query_params.ownership_ids,  # DEPRECATED alias
            start_date=query_params.start_date,
            end_date=query_params.end_date,
        )

        renewed = stats.get(ContractStatus.RENEWED, 0)
        expired = stats.get(ContractStatus.EXPIRED, 0)
        terminated = stats.get(ContractStatus.TERMINATED, 0)

        total_ended = renewed + expired + terminated
        if total_ended == 0:
            return Decimal("0")

        rate = (Decimal(str(renewed)) / Decimal(str(total_ended))) * 100
        return rate.quantize(Decimal("0.00"))

