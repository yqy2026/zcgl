"""Upstream-contract endpoints for the asset-operations workbench."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BaseBusinessError,
    ResourceNotFoundError,
    internal_error,
)
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.asset_operations import (
    ContractLifecycleEventResponse,
    UpstreamContractDetail,
    UpstreamContractExitCommitRequest,
    UpstreamContractExitPreviewResponse,
    UpstreamContractExitProposal,
    UpstreamContractExitReversalProposal,
    UpstreamContractListResponse,
    UpstreamContractRenewalRequest,
    UpstreamContractResponse,
    UpstreamContractUpdate,
)
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    asset_contract_command_service,
    asset_operations_query_service,
    contract_lifecycle_command_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/upstream-contracts",
    response_model=UpstreamContractListResponse,
    summary="查询上游合同列表",
)
async def list_upstream_contracts(
    contract_type: str | None = Query(None, description="合同类型过滤"),
    owner_party_id: str | None = Query(None, description="产权方过滤"),
    q: str | None = Query(None, max_length=100, description="编号/名称/OA 单号搜索"),
    offset: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> UpstreamContractListResponse:
    """List scoped upstream contracts with replay-derived status per row."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        items, total = await asset_operations_query_service.list_upstream_contracts(
            db,
            scope=scope,
            contract_type=contract_type,
            owner_party_id=owner_party_id,
            query=q,
            offset=offset,
            limit=limit,
        )
        return UpstreamContractListResponse(items=items, total=total)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询上游合同列表失败", original_error=exc) from exc


@router.get(
    "/upstream-contracts/{contract_id}",
    response_model=UpstreamContractDetail,
    summary="查询上游合同详情",
)
async def get_upstream_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> UpstreamContractDetail:
    """Return terms, coverages, schedules, renewal chain and events."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        detail = await asset_operations_query_service.get_upstream_contract(
            db,
            contract_id,
            scope=scope,
        )
        if detail is None:
            raise ResourceNotFoundError("UpstreamContract", contract_id)
        return detail
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询上游合同详情失败", original_error=exc) from exc


@router.patch(
    "/upstream-contracts/{contract_id}",
    response_model=UpstreamContractResponse,
    summary="更新上游合同可编辑字段",
)
async def update_upstream_contract(
    contract_id: str,
    payload: UpstreamContractUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> UpstreamContractResponse:
    """Apply editable terms under optimistic locking; coverage follows end_date."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_contract_command_service.update_upstream(
            db,
            contract_id=contract_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新上游合同失败", original_error=exc) from exc


@router.post(
    "/upstream-contracts/{contract_id}/exit/preview",
    response_model=UpstreamContractExitPreviewResponse,
    summary="预览上游合同退出",
)
async def preview_upstream_contract_exit(
    contract_id: str,
    payload: UpstreamContractExitProposal,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> UpstreamContractExitPreviewResponse:
    """Report coverage and deposit impact without writing lifecycle facts."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.preview_upstream_exit(
            db,
            contract_id=contract_id,
            proposal=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("预览上游合同退出失败", original_error=exc) from exc


@router.post(
    "/upstream-contracts/{contract_id}/exit",
    response_model=ContractLifecycleEventResponse,
    summary="提交上游合同退出",
)
async def commit_upstream_contract_exit(
    contract_id: str,
    payload: UpstreamContractExitCommitRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
            pattern=r".*\S.*",
        ),
    ],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> ContractLifecycleEventResponse:
    """Append one exit event and close upstream coverage in one transaction."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.commit_upstream_exit(
            db,
            contract_id=contract_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("提交上游合同退出失败", original_error=exc) from exc


@router.post(
    "/upstream-contracts/{contract_id}/exit-reversal",
    response_model=ContractLifecycleEventResponse,
    summary="撤销上游合同退出",
)
async def reverse_upstream_contract_exit(
    contract_id: str,
    payload: UpstreamContractExitReversalProposal,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
            pattern=r".*\S.*",
        ),
    ],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> ContractLifecycleEventResponse:
    """Void one exit event and reopen the upstream coverage it closed."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.reverse_upstream_exit(
            db,
            contract_id=contract_id,
            proposal=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("撤销上游合同退出失败", original_error=exc) from exc


@router.post(
    "/upstream-contracts/{contract_id}/renewals",
    response_model=UpstreamContractResponse,
    summary="登记上游合同续签",
)
async def renew_upstream_contract(
    contract_id: str,
    payload: UpstreamContractRenewalRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
            pattern=r".*\S.*",
        ),
    ],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{contract_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> UpstreamContractResponse:
    """Create the signed successor and chain it to this contract atomically."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.renew_upstream(
            db,
            contract_id=contract_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("登记上游合同续签失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
