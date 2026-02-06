from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.enums import ContractStatus
from ...models.asset import Asset
from ...models.ownership import Ownership
from ...models.rent_contract import (
    ContractType,
    RentContract,
    RentLedger,
    rent_contract_assets,
)
from ...schemas.rent_contract import RentStatisticsQuery
from .helpers import RentContractHelperMixin


class RentContractStatisticsService(RentContractHelperMixin):
    """合同统计相关服务"""

    async def get_statistics_async(
        self, db: AsyncSession, *, query_params: RentStatisticsQuery
    ) -> dict[str, Any]:
        filters = []
        if query_params.start_date:
            filters.append(RentLedger.due_date >= query_params.start_date)
        if query_params.end_date:
            filters.append(RentLedger.due_date <= query_params.end_date)
        if query_params.ownership_ids:
            filters.append(RentLedger.ownership_id.in_(query_params.ownership_ids))
        if query_params.asset_ids:
            filters.append(RentLedger.asset_id.in_(query_params.asset_ids))

        stats_stmt = select(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        )
        if filters:
            stats_stmt = stats_stmt.where(*filters)
        stats = (await db.execute(stats_stmt)).first()

        if stats is None:
            total_due = Decimal("0")
            total_paid = Decimal("0")
            total_overdue = Decimal("0")
            total_records = 0
        else:
            total_due = stats.total_due or Decimal("0")
            total_paid = stats.total_paid or Decimal("0")
            total_overdue = stats.total_overdue or Decimal("0")
            total_records = stats.total_records or 0

        status_stmt = select(
            RentLedger.payment_status,
            func.count(RentLedger.id).label("count"),
            func.sum(RentLedger.due_amount).label("due_amount"),
            func.sum(RentLedger.paid_amount).label("paid_amount"),
        ).group_by(RentLedger.payment_status)
        if filters:
            status_stmt = status_stmt.where(*filters)
        status_stats = (await db.execute(status_stmt)).all()

        monthly_stmt = select(
            RentLedger.year_month,
            func.sum(RentLedger.due_amount).label("due_amount"),
            func.sum(RentLedger.paid_amount).label("paid_amount"),
            func.sum(RentLedger.overdue_amount).label("overdue_amount"),
        ).group_by(RentLedger.year_month).order_by(RentLedger.year_month)
        if filters:
            monthly_stmt = monthly_stmt.where(*filters)
        monthly_stats = (await db.execute(monthly_stmt)).all()

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
        ownership_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Ownership.id,
                Ownership.name,
                Ownership.short_name,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(RentContract, RentContract.ownership_id == Ownership.id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Ownership.id, Ownership.name, Ownership.short_name)
        )

        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)
        if ownership_ids:
            stmt = stmt.where(Ownership.id.in_(ownership_ids))

        results = (await db.execute(stmt)).all()

        ownership_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

            ownership_stats.append(
                {
                    "ownership_id": result.id,
                    "ownership_name": result.name,
                    "total_contracts": result.contract_count,
                    "active_contracts": result.contract_count,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount
                    or Decimal("0"),
                    "occupancy_rate": payment_rate,
                }
            )

        return ownership_stats

    async def get_asset_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Asset.id,
                Asset.property_name,
                Asset.address,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(rent_contract_assets, rent_contract_assets.c.asset_id == Asset.id)
            .join(RentContract, RentContract.id == rent_contract_assets.c.contract_id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Asset.id, Asset.property_name, Asset.address)
        )

        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)
        if asset_ids:
            stmt = stmt.where(Asset.id.in_(asset_ids))

        results = (await db.execute(stmt)).all()

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
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                RentLedger.year_month,
                func.count(func.distinct(RentLedger.contract_id)).label(
                    "total_contracts"
                ),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
        )

        if year:
            stmt = stmt.where(RentLedger.year_month.like(f"{year}%"))
        if start_month:
            stmt = stmt.where(RentLedger.year_month >= start_month)
        if end_month:
            stmt = stmt.where(RentLedger.year_month <= end_month)

        results = (await db.execute(stmt)).all()

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
        stmt = select(RentContract).options(
            selectinload(RentContract.assets), selectinload(RentContract.rent_terms)
        )
        stmt = stmt.where(
            RentContract.contract_type == ContractType.LEASE_DOWNSTREAM,
            RentContract.contract_status == ContractStatus.ACTIVE,
        )

        if query_params.start_date and query_params.end_date:
            stmt = stmt.where(RentContract.start_date <= query_params.end_date)
        if query_params.end_date and query_params.start_date:
            stmt = stmt.where(RentContract.end_date >= query_params.start_date)

        if query_params.ownership_ids:
            stmt = stmt.where(RentContract.ownership_id.in_(query_params.ownership_ids))

        contracts = list((await db.execute(stmt)).scalars().all())
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
        stmt = (
            select(RentContract.contract_status, func.count(RentContract.id))
            .group_by(RentContract.contract_status)
        )

        if query_params.ownership_ids:
            stmt = stmt.where(RentContract.ownership_id.in_(query_params.ownership_ids))

        if query_params.start_date and query_params.end_date:
            stmt = stmt.where(
                RentContract.end_date.between(
                    query_params.start_date, query_params.end_date
                )
            )

        stats = {row[0]: row[1] for row in (await db.execute(stmt)).all()}

        renewed = stats.get(ContractStatus.RENEWED, 0)
        expired = stats.get(ContractStatus.EXPIRED, 0)
        terminated = stats.get(ContractStatus.TERMINATED, 0)

        total_ended = renewed + expired + terminated
        if total_ended == 0:
            return Decimal("0")

        rate = (Decimal(str(renewed)) / Decimal(str(total_ended))) * 100
        return rate.quantize(Decimal("0.00"))
