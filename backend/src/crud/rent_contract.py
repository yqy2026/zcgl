from datetime import date
from typing import Any

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..constants.business_constants import DataStatusValues
from ..constants.rent_contract_constants import PaymentStatus
from ..core.enums import ContractStatus
from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models.associations import rent_contract_assets
from ..models.ownership import Ownership
from ..models.rent_contract import (
    RentContract,
    RentDepositLedger,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
)
from ..schemas.rent_contract import (
    RentContractCreate,
    RentContractUpdate,
    RentLedgerCreate,
    RentLedgerUpdate,
    RentTermCreate,
    RentTermUpdate,
)


class CRUDRentContract(CRUDBase[RentContract, RentContractCreate, RentContractUpdate]):
    """租金合同CRUD操作 - 支持敏感字段加密"""

    def __init__(self, model: type[RentContract]) -> None:
        super().__init__(model)
        # RentContract 模型的敏感字段
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "owner_phone",  # 业主电话 - 敏感，需要搜索
                "tenant_phone",  # 租户电话 - 敏感，需要搜索
            }
        )

    async def get_async(
        self, db: AsyncSession, id: Any, use_cache: bool = False
    ) -> RentContract | None:
        stmt = select(RentContract).where(
            RentContract.id == id,
            or_(RentContract.data_status.is_(None), RentContract.data_status != "已删除"),
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> list[RentContract]:
        stmt = (
            select(RentContract)
            .where(
                or_(
                    RentContract.data_status.is_(None),
                    RentContract.data_status != "已删除",
                )
            )
            .offset(skip)
            .limit(limit)
        )
        results = list((await db.execute(stmt)).scalars().all())
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: RentContractCreate | dict[str, Any],
        **kwargs: Any,
    ) -> RentContract:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return await super().create(db=db, obj_in=encrypted_data, **kwargs)

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: RentContract,
        obj_in: RentContractUpdate | dict[str, Any],
        commit: bool = True,
    ) -> RentContract:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        encrypted_data = self._encrypt_update_data(update_data)
        return await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )

    def _encrypt_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """加密更新数据中的敏感字段"""
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    async def get_with_details_async(
        self, db: AsyncSession, id: str
    ) -> RentContract | None:
        stmt = (
            select(RentContract)
            .options(
                selectinload(RentContract.assets),
                selectinload(RentContract.rent_terms),
            )
            .join(Ownership, RentContract.ownership_id == Ownership.id, isouter=True)
            .where(
                RentContract.id == id,
                or_(
                    RentContract.data_status.is_(None),
                    RentContract.data_status != "已删除",
                ),
            )
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def get_by_contract_numbers_async(
        self, db: AsyncSession, *, contract_numbers: list[str]
    ) -> list[RentContract]:
        if not contract_numbers:
            return []
        stmt = select(RentContract).where(
            RentContract.contract_number.in_(contract_numbers)
        )
        contracts = list((await db.execute(stmt)).scalars().all())
        for contract in contracts:
            self.sensitive_data_handler.decrypt_data(contract.__dict__)
        return contracts

    async def get_export_contracts_async(
        self,
        db: AsyncSession,
        *,
        contract_ids: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[RentContract]:
        stmt = select(RentContract).options(selectinload(RentContract.assets))
        if contract_ids:
            stmt = stmt.where(RentContract.id.in_(contract_ids))
        if start_date:
            stmt = stmt.where(RentContract.start_date >= start_date)
        if end_date:
            stmt = stmt.where(RentContract.end_date <= end_date)

        stmt = stmt.order_by(RentContract.created_at.desc())
        contracts = list((await db.execute(stmt)).scalars().all())
        for contract in contracts:
            self.sensitive_data_handler.decrypt_data(contract.__dict__)
        return contracts

    async def get_active_with_assets_async(
        self, db: AsyncSession, *, exclude_contract_id: str | None = None
    ) -> list[RentContract]:
        stmt = (
            select(RentContract)
            .options(selectinload(RentContract.assets))
            .where(RentContract.contract_status == ContractStatus.ACTIVE)
        )
        if exclude_contract_id:
            stmt = stmt.where(RentContract.id != exclude_contract_id)
        return list((await db.execute(stmt)).scalars().all())

    async def get_expiring_contracts_async(
        self, db: AsyncSession, *, today: date, warning_date: date
    ) -> list[RentContract]:
        stmt = select(RentContract).where(
            RentContract.contract_status == ContractStatus.ACTIVE,
            RentContract.end_date <= warning_date,
            RentContract.end_date >= today,
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        contract_number: str | None = None,
        tenant_name: str | None = None,
        asset_id: str | None = None,
        ownership_id: str | None = None,
        contract_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        include_relations: bool = True,
    ) -> tuple[list[RentContract], int]:
        stmt = select(RentContract)
        if include_relations:
            stmt = stmt.options(
                selectinload(RentContract.assets),
                selectinload(RentContract.rent_terms),
            )
        if include_relations:
            stmt = stmt.join(
                Ownership, RentContract.ownership_id == Ownership.id, isouter=True
            )
        stmt = self._apply_contract_filters_async(
            stmt,
            contract_number=contract_number,
            tenant_name=tenant_name,
            asset_id=asset_id,
            ownership_id=ownership_id,
            contract_status=contract_status,
            start_date=start_date,
            end_date=end_date,
        )

        from sqlalchemy import desc

        stmt = stmt.order_by(desc(RentContract.created_at)).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        for item in items:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        count_stmt = select(func.count(RentContract.id))
        if include_relations:
            count_stmt = count_stmt.join(
                Ownership, RentContract.ownership_id == Ownership.id, isouter=True
            )
        count_stmt = self._apply_contract_filters_async(
            count_stmt,
            contract_number=contract_number,
            tenant_name=tenant_name,
            asset_id=asset_id,
            ownership_id=ownership_id,
            contract_status=contract_status,
            start_date=start_date,
            end_date=end_date,
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)

        return items, total

    def _apply_contract_filters_async(
        self,
        stmt: Any,
        *,
        contract_number: str | None,
        tenant_name: str | None,
        asset_id: str | None,
        ownership_id: str | None,
        contract_status: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> Any:
        stmt = stmt.where(
            or_(
                RentContract.data_status.is_(None),
                RentContract.data_status != "已删除",
            )
        )
        if asset_id:
            stmt = stmt.join(
                rent_contract_assets,
                RentContract.id == rent_contract_assets.c.contract_id,
            ).where(rent_contract_assets.c.asset_id == asset_id)

        if contract_number:
            stmt = stmt.where(RentContract.contract_number.contains(contract_number))
        if tenant_name:
            stmt = stmt.where(RentContract.tenant_name.contains(tenant_name))
        if start_date:
            stmt = stmt.where(RentContract.start_date >= start_date)
        if end_date:
            stmt = stmt.where(RentContract.end_date <= end_date)
        if ownership_id:
            stmt = stmt.where(RentContract.ownership_id == ownership_id)
        if contract_status:
            stmt = stmt.where(RentContract.contract_status == contract_status)

        return stmt

    async def count_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> int:
        """统计权属方的合同总数"""
        stmt = select(func.count(RentContract.id)).where(
            RentContract.ownership_id == ownership_id
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_active_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> int:
        """统计权属方的活跃合同数（状态为'有效'）"""
        from sqlalchemy import and_

        stmt = select(func.count(RentContract.id)).where(
            and_(
                RentContract.ownership_id == ownership_id,
                RentContract.contract_status == "有效",
            )
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_contracts_for_price_calculation_async(
        self,
        db: AsyncSession,
        *,
        contract_type: str | None = None,
        contract_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
    ) -> list[RentContract]:
        """获取用于单价计算的合同（含关联的资产和租金条款）"""
        stmt = select(RentContract).options(
            selectinload(RentContract.assets), selectinload(RentContract.rent_terms)
        )

        if contract_type:
            stmt = stmt.where(RentContract.contract_type == contract_type)
        if contract_status:
            stmt = stmt.where(RentContract.contract_status == contract_status)

        if start_date and end_date:
            stmt = stmt.where(RentContract.start_date <= end_date)
        if end_date and start_date:
            stmt = stmt.where(RentContract.end_date >= start_date)

        if ownership_ids:
            stmt = stmt.where(RentContract.ownership_id.in_(ownership_ids))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_contract_status_counts_async(
        self,
        db: AsyncSession,
        *,
        ownership_ids: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        """按合同状态分组计数（用于续租率计算）"""
        stmt = select(
            RentContract.contract_status, func.count(RentContract.id)
        ).group_by(RentContract.contract_status)

        if ownership_ids:
            stmt = stmt.where(RentContract.ownership_id.in_(ownership_ids))

        if start_date and end_date:
            stmt = stmt.where(
                RentContract.end_date.between(start_date, end_date)
            )

        result = await db.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}


class CRUDRentTerm(CRUDBase[RentTerm, RentTermCreate, RentTermUpdate]):
    """租金条款CRUD操作"""

    async def get_by_contract_async(
        self, db: AsyncSession, contract_id: str
    ) -> list[RentTerm]:
        stmt = (
            select(RentTerm)
            .where(RentTerm.contract_id == contract_id)
            .order_by(RentTerm.start_date)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_by_contract_ids_async(
        self, db: AsyncSession, *, contract_ids: list[str]
    ) -> list[RentTerm]:
        if not contract_ids:
            return []
        stmt = (
            select(RentTerm)
            .where(RentTerm.contract_id.in_(contract_ids))
            .order_by(RentTerm.contract_id, RentTerm.start_date)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def delete_by_contract_async(self, db: AsyncSession, contract_id: str) -> None:
        stmt = delete(RentTerm).where(RentTerm.contract_id == contract_id)
        await db.execute(stmt)


class CRUDRentLedger(CRUDBase[RentLedger, RentLedgerCreate, RentLedgerUpdate]):
    """租金台账CRUD操作"""

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        contract_id: str | None = None,
        asset_id: str | None = None,
        ownership_id: str | None = None,
        year_month: str | None = None,
        payment_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[RentLedger], int]:
        stmt = select(RentLedger)
        stmt = self._apply_ledger_filters_async(
            stmt,
            contract_id=contract_id,
            asset_id=asset_id,
            ownership_id=ownership_id,
            year_month=year_month,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
        )

        from sqlalchemy import desc

        stmt = (
            stmt.order_by(desc(RentLedger.year_month), desc(RentLedger.due_date))
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(stmt)).scalars().all())

        count_stmt = select(func.count(RentLedger.id))
        count_stmt = self._apply_ledger_filters_async(
            count_stmt,
            contract_id=contract_id,
            asset_id=asset_id,
            ownership_id=ownership_id,
            year_month=year_month,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)

        return items, total

    def _apply_ledger_filters_async(
        self,
        stmt: Any,
        *,
        contract_id: str | None,
        asset_id: str | None,
        ownership_id: str | None,
        year_month: str | None,
        payment_status: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> Any:
        if contract_id:
            stmt = stmt.where(RentLedger.contract_id == contract_id)
        if asset_id:
            stmt = stmt.where(RentLedger.asset_id == asset_id)
        if ownership_id:
            stmt = stmt.where(RentLedger.ownership_id == ownership_id)
        if year_month:
            stmt = stmt.where(RentLedger.year_month == year_month)
        if payment_status:
            stmt = stmt.where(RentLedger.payment_status == payment_status)
        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)

        return stmt

    async def get_by_contract_and_month_async(
        self, db: AsyncSession, contract_id: str, year_month: str
    ) -> RentLedger | None:
        from sqlalchemy import and_

        stmt = select(RentLedger).where(
            and_(
                RentLedger.contract_id == contract_id,
                RentLedger.year_month == year_month,
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_by_ids_async(
        self, db: AsyncSession, *, ledger_ids: list[str]
    ) -> list[RentLedger]:
        if not ledger_ids:
            return []
        stmt = select(RentLedger).where(RentLedger.id.in_(ledger_ids))
        return list((await db.execute(stmt)).scalars().all())

    async def get_by_contract_ids_async(
        self, db: AsyncSession, *, contract_ids: list[str]
    ) -> list[RentLedger]:
        if not contract_ids:
            return []
        stmt = (
            select(RentLedger)
            .where(RentLedger.contract_id.in_(contract_ids))
            .order_by(RentLedger.contract_id, RentLedger.year_month)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_deposit_ledger_by_contract_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentDepositLedger]:
        stmt = (
            select(RentDepositLedger)
            .where(RentDepositLedger.contract_id == contract_id)
            .order_by(desc(RentDepositLedger.created_at))
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_service_fee_ledger_by_contract_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[ServiceFeeLedger]:
        stmt = (
            select(ServiceFeeLedger)
            .where(ServiceFeeLedger.contract_id == contract_id)
            .order_by(desc(ServiceFeeLedger.year_month))
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_service_fee_by_source_ledger_async(
        self, db: AsyncSession, *, source_ledger_id: str
    ) -> ServiceFeeLedger | None:
        stmt = select(ServiceFeeLedger).where(
            ServiceFeeLedger.source_ledger_id == source_ledger_id
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_overdue_with_contract_async(
        self, db: AsyncSession, *, today: date
    ) -> list[RentLedger]:
        stmt = (
            select(RentLedger)
            .options(selectinload(RentLedger.contract))
            .where(
                RentLedger.payment_status.in_(
                    [PaymentStatus.UNPAID, PaymentStatus.PARTIAL]
                ),
                RentLedger.due_date < today,
                RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_due_soon_with_contract_async(
        self, db: AsyncSession, *, today: date, warning_date: date
    ) -> list[RentLedger]:
        stmt = (
            select(RentLedger)
            .options(selectinload(RentLedger.contract))
            .where(
                RentLedger.payment_status == PaymentStatus.UNPAID,
                RentLedger.due_date <= warning_date,
                RentLedger.due_date >= today,
                RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_existing_year_months_async(
        self, db: AsyncSession, *, contract_id: str, year_months: list[str]
    ) -> set[str]:
        if len(year_months) == 0:
            return set()

        stmt = select(RentLedger.year_month).where(
            RentLedger.contract_id == contract_id,
            RentLedger.year_month.in_(year_months),
        )
        rows = (await db.execute(stmt)).scalars().all()
        return {str(year_month) for year_month in rows if year_month is not None}

    async def sum_due_amount_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> float:
        """统计权属方的应收总额（通过合同ID关联）"""
        # 子查询：获取该权属方下所有合同ID
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id
        )
        # 聚合查询：统计应收总额
        stmt = select(func.coalesce(func.sum(RentLedger.due_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_paid_amount_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> float:
        """统计权属方的实收总额（通过合同ID关联）"""
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id
        )
        stmt = select(func.coalesce(func.sum(RentLedger.paid_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_overdue_amount_by_ownership_async(
        self, db: AsyncSession, ownership_id: str
    ) -> float:
        """统计权属方的欠款总额（通过合同ID关联）"""
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id
        )
        stmt = select(func.coalesce(func.sum(RentLedger.overdue_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def get_ledger_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> tuple[Any, Any, Any, int]:
        """获取租金台账总体统计（总应收/实收/欠款/记录数）"""
        stmt = select(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        )

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        if ownership_ids:
            filters.append(RentLedger.ownership_id.in_(ownership_ids))
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        stats = result.first()

        if stats is None:
            return None, None, None, 0

        return (
            stats.total_due,
            stats.total_paid,
            stats.total_overdue,
            stats.total_records or 0,
        )

    async def get_ledger_status_breakdown_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """按支付状态分组统计"""
        stmt = select(
            RentLedger.payment_status,
            func.count(RentLedger.id).label("count"),
            func.sum(RentLedger.due_amount).label("due_amount"),
            func.sum(RentLedger.paid_amount).label("paid_amount"),
        ).group_by(RentLedger.payment_status)

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        if ownership_ids:
            filters.append(RentLedger.ownership_id.in_(ownership_ids))
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return list(result.all())

    async def get_ledger_monthly_breakdown_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """按月份分组统计"""
        stmt = (
            select(
                RentLedger.year_month,
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
                func.sum(RentLedger.overdue_amount).label("overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
        )

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        if ownership_ids:
            filters.append(RentLedger.ownership_id.in_(ownership_ids))
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return list(result.all())

    async def get_ownership_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
    ) -> list[Any]:
        """权属方维度统计（JOIN Ownership + RentContract + RentLedger）"""
        from ..models.ownership import Ownership

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

        result = await db.execute(stmt)
        return list(result.all())

    async def get_asset_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """资产维度统计（JOIN Asset + RentContract + RentLedger）"""
        from ..models.asset import Asset

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

        result = await db.execute(stmt)
        return list(result.all())

    async def get_monthly_statistics_async(
        self,
        db: AsyncSession,
        *,
        year: int | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
    ) -> list[Any]:
        """月度统计（年月维度聚合）"""
        stmt = (
            select(
                RentLedger.year_month,
                func.count(func.distinct(RentLedger.contract_id)).label("total_contracts"),
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

        result = await db.execute(stmt)
        return list(result.all())


# 实例化CRUD对象
rent_contract = CRUDRentContract(RentContract)
rent_term = CRUDRentTerm(RentTerm)
rent_ledger = CRUDRentLedger(RentLedger)
