"""
合同组与合同 API 端点（REQ-RNT-001 M3）

路径：
  /contract-groups          (合同组 CRUD)
  /contract-groups/{id}/contracts
  /contracts/{id}           (合同 CRUD)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error, not_found
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from ....models.auth import User
from ....schemas.contract_group import (
    ContractCreate,
    ContractDetail,
    ContractGroupCreate,
    ContractGroupDetail,
    ContractGroupListItem,
    ContractGroupUpdate,
    ContractSummary,
)
from ....services.party import party_service
from ....services.rent_contract.contract_group_service import contract_group_service

router = APIRouter()

# ─────────────────────── ContractGroup endpoints ────────────────────────────


@router.post(
    "/contract-groups",
    response_model=ContractGroupDetail,
    status_code=201,
    summary="创建合同组",
)
async def create_contract_group(
    payload: ContractGroupCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="contract_group",
            )
        ),
    ] = None,
) -> ContractGroupDetail:
    _ = _authz
    operator_party = await party_service.get_party(
        db, party_id=payload.operator_party_id
    )
    if operator_party is None:
        raise not_found(
            "运营方主体不存在",
            resource_type="party",
            resource_id=payload.operator_party_id,
        )
    owner_party = await party_service.get_party(
        db, party_id=payload.owner_party_id
    )
    if owner_party is None:
        raise not_found(
            "产权方主体不存在",
            resource_type="party",
            resource_id=payload.owner_party_id,
        )
    try:
        group_code = await contract_group_service.generate_group_code(
            db,
            operator_party_id=payload.operator_party_id,
            operator_party_code=operator_party.code,
        )
        group = await contract_group_service.create_contract_group(
            db,
            obj_in=payload,
            group_code=group_code,
            current_user=str(current_user.id),
        )
        return await contract_group_service.get_group_detail(
            db, group_id=group.contract_group_id
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建合同组失败", original_error=exc) from exc


@router.get(
    "/contract-groups",
    response_model=dict,
    summary="分页查询合同组列表",
)
async def list_contract_groups(
    operator_party_id: str | None = Query(None, description="运营方主体 ID"),
    owner_party_id: str | None = Query(None, description="产权方主体 ID"),
    revenue_mode: str | None = Query(None, description="经营模式：LEASE / AGENCY"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(20, ge=1, le=200, description="每页条数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract_group",
            )
        ),
    ] = None,
) -> dict:
    _ = current_user
    _ = _authz
    items, total = await contract_group_service.list_groups(
        db,
        operator_party_id=operator_party_id,
        owner_party_id=owner_party_id,
        revenue_mode=revenue_mode,
        offset=offset,
        limit=limit,
    )
    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get(
    "/contract-groups/{group_id}",
    response_model=ContractGroupDetail,
    summary="获取合同组详情",
)
async def get_contract_group(
    group_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract_group",
                resource_id="{group_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> ContractGroupDetail:
    _ = current_user
    _ = _authz
    try:
        return await contract_group_service.get_group_detail(db, group_id=group_id)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("获取合同组详情失败", original_error=exc) from exc


@router.put(
    "/contract-groups/{group_id}",
    response_model=ContractGroupDetail,
    summary="更新合同组",
)
async def update_contract_group(
    group_id: str,
    payload: ContractGroupUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="contract_group",
                resource_id="{group_id}",
            )
        ),
    ] = None,
) -> ContractGroupDetail:
    _ = _authz
    try:
        await contract_group_service.update_contract_group(
            db,
            group_id=group_id,
            obj_in=payload,
            current_user=str(current_user.id),
        )
        return await contract_group_service.get_group_detail(db, group_id=group_id)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新合同组失败", original_error=exc) from exc


@router.delete(
    "/contract-groups/{group_id}",
    status_code=204,
    summary="逻辑删除合同组",
)
async def delete_contract_group(
    group_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="delete",
                resource_type="contract_group",
                resource_id="{group_id}",
            )
        ),
    ] = None,
) -> None:
    _ = current_user
    _ = _authz
    try:
        await contract_group_service.soft_delete_group(db, group_id=group_id)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("删除合同组失败", original_error=exc) from exc


# ─────────────────────── Contract-in-group endpoints ────────────────────────


@router.post(
    "/contract-groups/{group_id}/contracts",
    response_model=ContractDetail,
    status_code=201,
    summary="向合同组添加合同",
)
async def add_contract_to_group(
    group_id: str,
    payload: ContractCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="contract_group",
                resource_id="{group_id}",
            )
        ),
    ] = None,
) -> ContractDetail:
    _ = _authz
    # 保证路径中的 group_id 与 payload 一致
    if payload.contract_group_id != group_id:
        raise HTTPException(
            status_code=422,
            detail="路径 group_id 与请求体 contract_group_id 不一致",
        )
    try:
        contract = await contract_group_service.add_contract_to_group(
            db,
            obj_in=payload,
            current_user=str(current_user.id),
        )
        return await contract_group_service.get_contract_detail(
            db, contract_id=contract.contract_id
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("添加合同失败", original_error=exc) from exc


@router.get(
    "/contract-groups/{group_id}/contracts",
    response_model=list[ContractSummary],
    summary="获取合同组内所有合同",
)
async def list_contracts_in_group(
    group_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract_group",
                resource_id="{group_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> list[ContractSummary]:
    _ = current_user
    _ = _authz
    try:
        contracts = await contract_group_service.list_contracts_in_group(
            db, group_id=group_id
        )
        return [ContractSummary.model_validate(c) for c in contracts]
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("获取合同组合同列表失败", original_error=exc) from exc


# ─────────────────────── Standalone Contract endpoints ──────────────────────


@router.get(
    "/contracts/{contract_id}",
    response_model=ContractDetail,
    summary="获取单合同详情",
)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract",
                resource_id="{contract_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> ContractDetail:
    _ = current_user
    _ = _authz
    try:
        return await contract_group_service.get_contract_detail(
            db, contract_id=contract_id
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("获取合同详情失败", original_error=exc) from exc


@router.delete(
    "/contracts/{contract_id}",
    status_code=204,
    summary="逻辑删除合同",
)
async def delete_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="delete",
                resource_type="contract",
                resource_id="{contract_id}",
            )
        ),
    ] = None,
) -> None:
    _ = current_user
    _ = _authz
    try:
        await contract_group_service.soft_delete_contract(db, contract_id=contract_id)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("删除合同失败", original_error=exc) from exc
