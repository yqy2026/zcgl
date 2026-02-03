"""
租金条款模块
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ....core.exception_handler import not_found
from ....crud.rent_contract import rent_contract, rent_term
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.rent_contract import RentTermCreate, RentTermResponse

router = APIRouter()


@router.get(
    "/contracts/{contract_id}/terms",
    response_model=list[RentTermResponse],
    summary="获取合同租金条款",
)
async def get_contract_terms(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定合同的所有租金条款
    """
    terms = await db.run_sync(
        lambda sync_db: rent_term.get_by_contract(sync_db, contract_id=contract_id)
    )
    return terms


@router.post(
    "/contracts/{contract_id}/terms",
    response_model=RentTermResponse,
    summary="添加租金条款",
)
async def add_rent_term(
    contract_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    term_in: RentTermCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    为合同添加新的租金条款
    """

    def _sync(sync_db: Session) -> object | None:
        contract = rent_contract.get(sync_db, id=contract_id)
        if not contract:
            return None
        term_data = term_in.model_dump()
        term_data["contract_id"] = contract_id
        return rent_term.create(db=sync_db, obj_in=term_data)

    term = await db.run_sync(_sync)
    if not term:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    return term
