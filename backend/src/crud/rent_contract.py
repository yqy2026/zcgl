from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models.associations import rent_contract_assets
from ..models.ownership import Ownership
from ..models.rent_contract import (
    RentContract,
    RentLedger,
    RentTerm,
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


# 实例化CRUD对象
rent_contract = CRUDRentContract(RentContract)
rent_term = CRUDRentTerm(RentTerm)
rent_ledger = CRUDRentLedger(RentLedger)
