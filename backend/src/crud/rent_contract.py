from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models import Ownership
from ..models.rent_contract import (
    RentContract,
    RentLedger,
    RentTerm,
    rent_contract_assets,
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

    def create(
        self, db: Session, *, obj_in: RentContractCreate | dict[str, Any], **kwargs: Any
    ) -> RentContract:
        """创建合同 - 加密敏感字段"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        # 加密敏感字段
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return super().create(db=db, obj_in=encrypted_data, **kwargs)

    def get(self, db: Session, id: Any, use_cache: bool = True) -> RentContract | None:
        """获取合同 - 解密敏感字段"""
        result = super().get(db=db, id=id, use_cache=use_cache)
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, use_cache: bool = False
    ) -> list[RentContract]:
        """获取多个合同 - 解密敏感字段"""
        results = super().get_multi(db=db, skip=skip, limit=limit, use_cache=use_cache)
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results

    def update(
        self,
        db: Session,
        *,
        db_obj: RentContract,
        obj_in: RentContractUpdate | dict[str, Any],
    ) -> RentContract:
        """更新合同 - 加密新的敏感字段值"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 加密敏感字段
        encrypted_data = self._encrypt_update_data(update_data)
        return super().update(db=db, db_obj=db_obj, obj_in=encrypted_data)

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

    def get_with_details(self, db: Session, id: str) -> RentContract | None:
        """获取合同详情（包含关联的租金条款和资产）- V2使用多对多关系"""
        return (
            db.query(RentContract)
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
        """获取合同列表（支持筛选）- V2支持通过资产ID筛选"""

        # 使用 QueryBuilder
        filters = {}
        if ownership_id:
            filters["ownership_id"] = ownership_id
        if contract_status:
            filters["contract_status"] = contract_status

        # 构建基础查询
        query = db.query(RentContract)
        if include_relations:
            query = query.join(
                Ownership, RentContract.ownership_id == Ownership.id, isouter=True
            )

        # V2: 通过多对多关联表筛选资产
        if asset_id:
            query = query.join(
                rent_contract_assets,
                RentContract.id == rent_contract_assets.c.contract_id,
            ).filter(rent_contract_assets.c.asset_id == asset_id)

        if contract_number:
            query = query.filter(RentContract.contract_number.contains(contract_number))
        if tenant_name:
            query = query.filter(RentContract.tenant_name.contains(tenant_name))
        if start_date:
            query = query.filter(RentContract.start_date >= start_date)
        if end_date:
            query = query.filter(RentContract.end_date <= end_date)

        # Apply additional filters from QB
        from sqlalchemy import desc

        if ownership_id:
            query = query.filter(RentContract.ownership_id == ownership_id)
        if contract_status:
            query = query.filter(RentContract.contract_status == contract_status)

        # Apply sorting and pagination
        query = query.order_by(desc(RentContract.created_at))
        items = query.offset(skip).limit(limit).all()

        # For count, we need to rebuild the query without pagination
        # Re-apply filters for count
        count_query = db.query(RentContract)
        if asset_id:
            count_query = count_query.join(
                rent_contract_assets,
                RentContract.id == rent_contract_assets.c.contract_id,
            ).filter(rent_contract_assets.c.asset_id == asset_id)
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
        if ownership_id:
            count_query = count_query.filter(RentContract.ownership_id == ownership_id)
        if contract_status:
            count_query = count_query.filter(
                RentContract.contract_status == contract_status
            )

        total = count_query.count()

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

        # Apply filters from QB
        from sqlalchemy import desc

        if contract_id:
            query = query.filter(RentLedger.contract_id == contract_id)
        if asset_id:
            query = query.filter(RentLedger.asset_id == asset_id)
        if ownership_id:
            query = query.filter(RentLedger.ownership_id == ownership_id)
        if year_month:
            query = query.filter(RentLedger.year_month == year_month)
        if payment_status:
            query = query.filter(RentLedger.payment_status == payment_status)

        # Apply sorting and pagination
        query = query.order_by(desc(RentLedger.year_month), desc(RentLedger.due_date))
        items = query.offset(skip).limit(limit).all()

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
