from datetime import date
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import ResourceNotFoundError
from src.crud.asset import asset_crud
from src.crud.ownership import ownership as ownership_crud
from src.crud.rent_contract import (
    rent_contract as rent_contract_crud,
)
from src.crud.rent_contract import (
    rent_term as rent_term_crud,
)
from src.crud.rent_contract_attachment import (
    rent_contract_attachment_crud,
)
from src.models.rent_contract import (
    RentContract,
    RentContractAttachment,
    RentLedger,
    RentTerm,
)
from src.schemas.rent_contract import RentTermCreate

from .ledger_service import RentContractLedgerService
from .lifecycle_service import RentContractLifecycleService
from .statistics_service import RentContractStatisticsService


def model_to_dict(model: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """
    将 SQLAlchemy 模型或 Pydantic 模型转换为字典

    Args:
        model: SQLAlchemy 或 Pydantic 模型实例
        exclude: 要排除的字段集合

    Returns:
        dict: 模型数据的字典表示
    """
    if model is None:
        return {}

    # Pydantic v2 模型
    if hasattr(model, "model_dump"):
        return cast(dict[str, Any], model.model_dump(exclude=exclude))

    # SQLAlchemy 模型
    if hasattr(model, "__table__"):
        columns = model.__table__.columns.keys()
        return {
            col: getattr(model, col)
            for col in columns
            if exclude is None or col not in exclude
        }

    # 其他对象，尝试转换为 dict
    return cast(dict[str, Any], dict(model))


class RentContractService(
    RentContractLifecycleService,
    RentContractLedgerService,
    RentContractStatisticsService,
):
    """租金合同业务服务"""

    async def get_contract_terms_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentTerm]:
        return cast(
            list[RentTerm],
            await rent_term_crud.get_by_contract_async(db, contract_id=contract_id),
        )

    async def add_contract_term_async(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        term_in: RentTermCreate,
    ) -> RentTerm:
        contract = await rent_contract_crud.get_with_details_async(db, id=contract_id)
        if not contract:
            raise ResourceNotFoundError("合同", contract_id)

        term_data = term_in.model_dump()
        term_data["contract_id"] = contract_id
        term = await rent_term_crud.create(db=db, obj_in=term_data)
        if not term:
            raise ResourceNotFoundError("合同", contract_id)
        return cast(RentTerm, term)

    async def get_contract_by_id_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> RentContract | None:
        return cast(
            RentContract | None,
            await rent_contract_crud.get_async(db, id=contract_id),
        )

    async def get_contract_with_details_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> RentContract | None:
        return cast(
            RentContract | None,
            await rent_contract_crud.get_with_details_async(db, id=contract_id),
        )

    async def get_contract_page_async(
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
    ) -> tuple[list[RentContract], int]:
        return cast(
            tuple[list[RentContract], int],
            await rent_contract_crud.get_multi_with_filters_async(
                db=db,
                skip=skip,
                limit=limit,
                contract_number=contract_number,
                tenant_name=tenant_name,
                asset_id=asset_id,
                ownership_id=ownership_id,
                contract_status=contract_status,
                start_date=start_date,
                end_date=end_date,
            ),
        )

    async def delete_contract_by_id_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> None:
        await rent_contract_crud.remove(db, id=contract_id)

    async def get_assets_by_ids_async(
        self, db: AsyncSession, *, asset_ids: list[str]
    ) -> list[Any]:
        return cast(
            list[Any],
            await asset_crud.get_multi_by_ids_async(
                db=db,
                ids=asset_ids,
                include_relations=False,
            ),
        )

    async def get_ownership_by_id_async(
        self, db: AsyncSession, *, ownership_id: str
    ) -> Any:
        return await ownership_crud.get(db, id=ownership_id)

    async def get_asset_contracts_async(
        self, db: AsyncSession, *, asset_id: str, limit: int = 1000
    ) -> list[RentContract]:
        contracts, _ = await self.get_contract_page_async(
            db=db,
            skip=0,
            limit=limit,
            asset_id=asset_id,
        )
        return contracts

    async def get_contract_attachments_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentContractAttachment]:
        return cast(
            list[RentContractAttachment],
            await rent_contract_attachment_crud.get_by_contract_async(
                db, contract_id=contract_id
            ),
        )

    async def get_contract_attachment_async(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        contract_id: str | None = None,
    ) -> RentContractAttachment | None:
        return cast(
            RentContractAttachment | None,
            await rent_contract_attachment_crud.get_async(
                db,
                attachment_id=attachment_id,
                contract_id=contract_id,
            ),
        )

    async def delete_contract_attachment_async(
        self,
        db: AsyncSession,
        *,
        attachment: RentContractAttachment,
    ) -> None:
        await db.delete(attachment)
        await db.commit()


rent_contract_service = RentContractService()

# 别名，用于测试兼容性
rent_contract = RentContract
rent_ledger = RentLedger
rent_term = RentTerm

__all__ = [
    "RentContractService",
    "rent_contract_service",
    "model_to_dict",
    "rent_contract",
    "rent_ledger",
    "rent_term",
]
