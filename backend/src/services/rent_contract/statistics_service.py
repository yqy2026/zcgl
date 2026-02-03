from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ...core.enums import ContractStatus
from ...models.asset import Asset, Ownership
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

    def get_statistics(
        self, db: Session, *, query_params: RentStatisticsQuery
    ) -> dict[str, Any]:
        """获取统计信息"""
        # 构建基础查询
        base_query = db.query(RentLedger)

        # 应用筛选条件
        if query_params.start_date:
            base_query = base_query.filter(
                RentLedger.due_date >= query_params.start_date
            )
        if query_params.end_date:
            base_query = base_query.filter(RentLedger.due_date <= query_params.end_date)
        if query_params.ownership_ids:
            base_query = base_query.filter(
                RentLedger.ownership_id.in_(query_params.ownership_ids)
            )
        if query_params.asset_ids:
            base_query = base_query.filter(
                RentLedger.asset_id.in_(query_params.asset_ids)
            )

        # 基础统计
        stats = base_query.with_entities(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        ).first()

        # Handle None case for stats
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

        # 按状态统计
        status_stats = (
            base_query.with_entities(
                RentLedger.payment_status,
                func.count(RentLedger.id).label("count"),
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
            )
            .group_by(RentLedger.payment_status)
            .all()
        )

        # 按月份统计
        monthly_stats = (
            base_query.with_entities(
                RentLedger.year_month,
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
                func.sum(RentLedger.overdue_amount).label("overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
            .all()
        )

        payment_rate = (total_paid / total_due * 100) if total_due else Decimal("0")

        return {
            "total_due": total_due,
            "total_paid": total_paid,
            "total_overdue": total_overdue,
            "total_records": total_records,
            "payment_rate": payment_rate,
            # V2: New Operational Metrics
            "average_unit_price": self._calculate_average_unit_price(db, query_params),
            "renewal_rate": self._calculate_renewal_rate(db, query_params),
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

    def get_ownership_statistics(
        self,
        db: Session,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """按权属方统计租金情况"""
        # ... logic moved from CRUD ...
        query = (
            db.query(
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
            query = query.filter(RentLedger.due_date >= start_date)
        if end_date:
            query = query.filter(RentLedger.due_date <= end_date)
        if ownership_ids:
            query = query.filter(Ownership.id.in_(ownership_ids))

        results = query.all()

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
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "occupancy_rate": payment_rate,
                }
            )

        return ownership_stats

    def get_asset_statistics(
        self,
        db: Session,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """按资产统计租金情况"""
        query = (
            db.query(
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
            query = query.filter(RentLedger.due_date >= start_date)
        if end_date:
            query = query.filter(RentLedger.due_date <= end_date)
        if asset_ids:
            query = query.filter(Asset.id.in_(asset_ids))

        results = query.all()

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

    def get_monthly_statistics(
        self,
        db: Session,
        *,
        year: int | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取月度租金统计"""
        query = (
            db.query(
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
            query = query.filter(RentLedger.year_month.like(f"{year}%"))

        if start_month:
            query = query.filter(RentLedger.year_month >= start_month)
        if end_month:
            query = query.filter(RentLedger.year_month <= end_month)

        results = query.all()

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

    def _calculate_average_unit_price(
        self, db: Session, query_params: RentStatisticsQuery
    ) -> Decimal:
        """
        Calculates the average unit price (Monthly Rent / Rentable Area).
        Note: Only considers 'lease_downstream' contracts which typically generate revenue.
        Formula: Sum(Monthly Rent) / Sum(Rentable Area)
        """
        # Join RentContract with Asset to get area
        # V2: Contracts have many-to-many relationship with Assets, but here we can approximate
        # by checking contracts that have associated assets.
        # Since calculating exact area share for multi-asset contracts is complex,
        # we will aggregate total rent of downstream contracts and divide by total area of assets linked to them.

        # 1. Filter valid downstream contracts
        query = db.query(RentContract).options(
            selectinload(RentContract.assets), selectinload(RentContract.rent_terms)
        )
        query = query.filter(
            RentContract.contract_type == ContractType.LEASE_DOWNSTREAM,
            RentContract.contract_status == ContractStatus.ACTIVE,
        )

        if query_params.start_date:
            # Check if contract is active during the period
            query = query.filter(RentContract.start_date <= query_params.end_date)
        if query_params.end_date:
            query = query.filter(RentContract.end_date >= query_params.start_date)

        if query_params.ownership_ids:
            query = query.filter(
                RentContract.ownership_id.in_(query_params.ownership_ids)
            )

        contracts = query.all()
        if not contracts:
            return Decimal("0")

        total_rent = Decimal("0")
        total_area = Decimal("0")

        for contract in contracts:
            # Monthly Rent
            # If monthly_rent_base is set, use it. Otherwise try to get from current term
            rent = contract.monthly_rent_base or Decimal("0")
            if rent == 0 and contract.rent_terms:
                # Use first active term or just first term as fallback
                rent = contract.rent_terms[0].monthly_rent

            # Asset Area
            # Sum area of all associated assets
            assets = contract.assets
            area = sum((asset.rentable_area or Decimal("0")) for asset in assets)

            if area > 0:
                total_rent += rent
                total_area += area

        if total_area == 0:
            return Decimal("0")

        return (total_rent / total_area).quantize(Decimal("0.00"))

    def _calculate_renewal_rate(
        self, db: Session, query_params: RentStatisticsQuery
    ) -> Decimal:
        """
        Calculates renewal rate.
        Formula: Renewed Contracts / (Renewed + Expired + Terminated)
        Renewal Rate = 'RENEWED' / ('RENEWED' + 'EXPIRED' + 'TERMINATED')
        """
        query = db.query(
            RentContract.contract_status, func.count(RentContract.id)
        ).group_by(RentContract.contract_status)

        if query_params.ownership_ids:
            query = query.filter(
                RentContract.ownership_id.in_(query_params.ownership_ids)
            )

        # Date filtering for renewal rate
        if query_params.start_date and query_params.end_date:
            query = query.filter(
                RentContract.end_date.between(
                    query_params.start_date, query_params.end_date
                )
            )

        stats = {row[0]: row[1] for row in query.all()}

        renewed = stats.get(ContractStatus.RENEWED, 0)
        expired = stats.get(ContractStatus.EXPIRED, 0)
        terminated = stats.get(ContractStatus.TERMINATED, 0)

        total_ended = renewed + expired + terminated
        if total_ended == 0:
            return Decimal("0")

        rate = (Decimal(str(renewed)) / Decimal(str(total_ended))) * 100
        return rate.quantize(Decimal("0.00"))
