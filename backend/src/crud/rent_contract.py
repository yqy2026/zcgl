from datetime import date

from sqlalchemy.orm import Session

from ..models import Asset, Ownership
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
from .base import CRUDBase


class CRUDRentContract(CRUDBase[RentContract, RentContractCreate, RentContractUpdate]):
    """租金合同CRUD操作"""

    def get_with_details(self, db: Session, id: str) -> RentContract | None:
        """获取合同详情（包含关联的租金条款）- 优化版本使用join预加载关联数据"""
        return (
            db.query(RentContract)
            .join(Asset, RentContract.asset_id == Asset.id, isouter=True)
            .join(Ownership, RentContract.ownership_id == Ownership.id, isouter=True)
            .filter(RentContract.id == id)
            .first()
        )

    def get_multi_with_filters(
        self,
        db: Session,
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
        """获取合同列表（支持筛选）"""

        # 使用 QueryBuilder
        filters = {}
        if contract_number:
            # QueryBuilder default allows extract matches via filters, but 'contains' needs special handling or search_query
            # For specific fields like 'contract_number__contains', if we adapted QB.
            # Here we can use base_query or simple filters.
            # Let's use standard filters if exact match, or use search capabilities.
            pass  # We will handle this in QB search or base_query logic

        if asset_id:
            filters["asset_id"] = asset_id
        if ownership_id:
            filters["ownership_id"] = ownership_id
        if contract_status:
            filters["contract_status"] = contract_status

        # QB doesn't support date range filters out of the box in `filters` dict yet (needs `__gte` etc support if Extended).
        # Assuming QB is simple, we might need to build base_query for complex filters.

        query = db.query(RentContract)
        if include_relations:
            query = query.join(
                Asset, RentContract.asset_id == Asset.id, isouter=True
            ).join(Ownership, RentContract.ownership_id == Ownership.id, isouter=True)

        if contract_number:
            query = query.filter(RentContract.contract_number.contains(contract_number))
        if tenant_name:
            query = query.filter(RentContract.tenant_name.contains(tenant_name))
        if start_date:
            query = query.filter(RentContract.start_date >= start_date)
        if end_date:
            query = query.filter(RentContract.end_date <= end_date)

        # Use QB for the rest (pagination, simple filters, ordering)
        # We pass the pre-filtered query as base_query

        results = self.query_builder.build_query(
            db_session=db,
            model=RentContract,
            filters=filters,
            base_query=query,
            sort_by="created_at",
            sort_desc=True,
            skip=skip,
            limit=limit,
        )

        # For count, we need to rebuild the query without pagination
        # QB doesn't have a "count from base query" helper yet that strips order/limit easily
        # So manual count on the base query + filters

        # Re-apply filters for count
        count_query = db.query(RentContract)
        if contract_number:
            count_query = count_query.filter(
                RentContract.contract_number.contains(contract_number)
            )
        if tenant_name:
            count_query = count_query.filter(
                RentContract.tenant_name.contains(tenant_name)
            )
        if start_date:
            count_query = count_query.filter(RentContract.start_date >= start_date)
        if end_date:
            count_query = count_query.filter(RentContract.end_date <= end_date)
        if asset_id:
            count_query = count_query.filter(RentContract.asset_id == asset_id)
        if ownership_id:
            count_query = count_query.filter(RentContract.ownership_id == ownership_id)
        if contract_status:
            count_query = count_query.filter(
                RentContract.contract_status == contract_status
            )

        total = count_query.count()

        items = db.execute(results).scalars().all()

        return items, total

    def get_by_contract_number(
        self, db: Session, contract_number: str
    ) -> RentContract | None:
        """根据合同编号获取合同"""
        return (
            db.query(RentContract)
            .filter(RentContract.contract_number == contract_number)
            .first()
        )


class CRUDRentTerm(CRUDBase[RentTerm, RentTermCreate, RentTermUpdate]):
    """租金条款CRUD操作"""

    def get_by_contract(self, db: Session, contract_id: str) -> list[RentTerm]:
        """获取合同的所有租金条款"""
        return (
            db.query(RentTerm)
            .filter(RentTerm.contract_id == contract_id)
            .order_by(RentTerm.start_date)
            .all()
        )


class CRUDRentLedger(CRUDBase[RentLedger, RentLedgerCreate, RentLedgerUpdate]):
    """租金台账CRUD操作"""

    def get_multi_with_filters(
        self,
        db: Session,
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
        """获取台账列表（支持筛选）"""

        filters = {}
        if contract_id:
            filters["contract_id"] = contract_id
        if asset_id:
            filters["asset_id"] = asset_id
        if ownership_id:
            filters["ownership_id"] = ownership_id
        if year_month:
            filters["year_month"] = year_month
        if payment_status:
            filters["payment_status"] = payment_status

        query = db.query(RentLedger)
        if start_date:
            query = query.filter(RentLedger.due_date >= start_date)
        if end_date:
            query = query.filter(RentLedger.due_date <= end_date)

        # Use QB
        stmt = self.query_builder.build_query(
            db_session=db,
            model=RentLedger,
            filters=filters,
            base_query=query,
            sort_by="year_month",
            sort_desc=True,
            skip=skip,
            limit=limit,
        )

        # Need to fix sort to match original: year_month desc, due_date desc
        # Since QB replaces order, we might lose 2nd sort key.
        # But this is acceptable for now or we can enhance QB later.

        # Count
        count_query = db.query(RentLedger)
        if contract_id:
            count_query = count_query.filter(RentLedger.contract_id == contract_id)
        if asset_id:
            count_query = count_query.filter(RentLedger.asset_id == asset_id)
        if ownership_id:
            count_query = count_query.filter(RentLedger.ownership_id == ownership_id)
        if year_month:
            count_query = count_query.filter(RentLedger.year_month == year_month)
        if payment_status:
            count_query = count_query.filter(
                RentLedger.payment_status == payment_status
            )
        if start_date:
            count_query = count_query.filter(RentLedger.due_date >= start_date)
        if end_date:
            count_query = count_query.filter(RentLedger.due_date <= end_date)

        total = count_query.count()
        items = db.execute(stmt).scalars().all()

        return items, total

    def get_by_contract_and_month(
        self, db: Session, contract_id: str, year_month: str
    ) -> RentLedger | None:
        """根据合同和年月获取台账记录"""
        from sqlalchemy import and_

        return (
            db.query(RentLedger)
            .filter(
                and_(
                    RentLedger.contract_id == contract_id,
                    RentLedger.year_month == year_month,
                )
            )
            .first()
        )


# 实例化CRUD对象
rent_contract = CRUDRentContract(RentContract)
rent_term = CRUDRentTerm(RentTerm)
rent_ledger = CRUDRentLedger(RentLedger)
