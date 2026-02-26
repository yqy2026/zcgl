"""
租金条款模块
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.rent_contract import RentTermCreate, RentTermResponse
from ....services.rent_contract import rent_contract_service

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
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
            resource_id="{contract_id}",
            deny_as_not_found=True,
        )
    ),
) -> Any:
    """
    获取指定合同的所有租金条款
    """
    try:
        return await rent_contract_service.get_contract_terms_async(
            db=db,
            contract_id=contract_id,
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取合同租金条款失败: {str(e)}")


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
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="rent_contract",
            resource_id="{contract_id}",
        )
    ),
) -> Any:
    """
    为合同添加新的租金条款
    """
    try:
        return await rent_contract_service.add_contract_term_async(
            db=db,
            contract_id=contract_id,
            term_in=term_in,
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"添加租金条款失败: {str(e)}")
