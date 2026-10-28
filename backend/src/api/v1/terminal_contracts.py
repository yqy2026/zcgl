"""Terminal-contract endpoints for the asset-operations workbench."""

from __future__ import annotations

from typing import Annotated, Literal

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
    TerminalContractDetail,
    TerminalContractListResponse,
    TerminalContractRenewalRequest,
    TerminalContractResponse,
    TerminalContractTerminationCommitRequest,
    TerminalContractTerminationPreviewResponse,
    TerminalContractTerminationProposal,
    TerminalContractTerminationReversalProposal,
    TerminalContractUpdate,
)
from ...schemas.rent_commands import (
    RentScheduleCorrectionCommit,
    RentScheduleCorrectionPreview,
    RentScheduleCorrectionProposal,
    RentScheduleCorrectionResponse,
)
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    asset_contract_command_service,
    asset_operations_query_service,
    contract_lifecycle_command_service,
)
from ...services.asset_operations.rent_schedule_correction_service import (
    rent_schedule_correction_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/terminal-contracts",
    response_model=TerminalContractListResponse,
    summary="查询终端合同列表",
)
async def list_terminal_contracts(
    contract_mode: str | None = Query(None, description="合同模式过滤"),
    upstream_contract_id: str | None = Query(None, description="上游合同过滤"),
    q: str | None = Query(None, max_length=100, description="编号搜索"),
    offset: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    filter: Literal["rent_unpaid"] | None = Query(None, description="租金未到账"),
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
) -> TerminalContractListResponse:
    """List scoped terminal contracts with replay-derived status and warnings."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        items, total = await asset_operations_query_service.list_terminal_contracts(
            db,
            scope=scope,
            contract_mode=contract_mode,
            upstream_contract_id=upstream_contract_id,
            query=q,
            rent_unpaid=filter == "rent_unpaid",
            offset=offset,
            limit=limit,
        )
        return TerminalContractListResponse(items=items, total=total)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询终端合同列表失败", original_error=exc) from exc


@router.get(
    "/terminal-contracts/{contract_id}",
    response_model=TerminalContractDetail,
    summary="查询终端合同详情",
)
async def get_terminal_contract(
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
) -> TerminalContractDetail:
    """Return terms, coverages, schedules, renewal chain, events and warnings."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        detail = await asset_operations_query_service.get_terminal_contract(
            db,
            contract_id,
            scope=scope,
        )
        if detail is None:
            raise ResourceNotFoundError("TerminalContract", contract_id)
        return detail
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询终端合同详情失败", original_error=exc) from exc


@router.patch(
    "/terminal-contracts/{contract_id}",
    response_model=TerminalContractResponse,
    summary="更新终端合同可编辑字段",
)
async def update_terminal_contract(
    contract_id: str,
    payload: TerminalContractUpdate,
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
) -> TerminalContractResponse:
    """Apply editable terms and return the recomputed derived risks."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_contract_command_service.update_terminal(
            db,
            contract_id=contract_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新终端合同失败", original_error=exc) from exc


@router.post(
    "/terminal-contracts/{contract_id}/termination/preview",
    response_model=TerminalContractTerminationPreviewResponse,
    summary="预览终端合同终止",
)
async def preview_terminal_contract_termination(
    contract_id: str,
    payload: TerminalContractTerminationProposal,
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
) -> TerminalContractTerminationPreviewResponse:
    """Report coverage, deposit and handover impact without writing facts."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.preview_terminal_termination(
            db,
            contract_id=contract_id,
            proposal=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("预览终端合同终止失败", original_error=exc) from exc


@router.post(
    "/terminal-contracts/{contract_id}/termination",
    response_model=ContractLifecycleEventResponse,
    summary="提交终端合同终止",
)
async def commit_terminal_contract_termination(
    contract_id: str,
    payload: TerminalContractTerminationCommitRequest,
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
    """Append one termination event and close coverage in the same transaction."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.commit_terminal_termination(
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
        raise internal_error("提交终端合同终止失败", original_error=exc) from exc


@router.post(
    "/terminal-contracts/{contract_id}/termination-reversal",
    response_model=ContractLifecycleEventResponse,
    summary="撤销终端合同终止",
)
async def reverse_terminal_contract_termination(
    contract_id: str,
    payload: TerminalContractTerminationReversalProposal,
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
    """Void one termination event and reopen the coverage it closed."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.reverse_terminal_termination(
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
        raise internal_error("撤销终端合同终止失败", original_error=exc) from exc


@router.post(
    "/terminal-contracts/{contract_id}/renewals",
    response_model=TerminalContractResponse,
    summary="登记终端合同续签",
)
async def renew_terminal_contract(
    contract_id: str,
    payload: TerminalContractRenewalRequest,
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
) -> TerminalContractResponse:
    """Create the signed terminal successor and chain it to this contract."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await contract_lifecycle_command_service.renew_terminal(
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
        raise internal_error("登记终端合同续签失败", original_error=exc) from exc


@router.post(
    "/terminal-contracts/{contract_id}/rent-schedule-correction/preview",
    response_model=RentScheduleCorrectionPreview,
    summary="预览终端租金阶段更正",
)
async def preview_terminal_rent_schedule_correction(
    contract_id: str,
    payload: RentScheduleCorrectionProposal,
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
) -> RentScheduleCorrectionPreview:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_schedule_correction_service.preview(
        db,
        contract_kind="terminal",
        contract_id=contract_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
    )


@router.post(
    "/terminal-contracts/{contract_id}/rent-schedule-correction",
    response_model=RentScheduleCorrectionResponse,
    summary="更正终端租金阶段",
)
async def commit_terminal_rent_schedule_correction(
    contract_id: str,
    payload: RentScheduleCorrectionCommit,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key", min_length=1, max_length=100, pattern=r".*\S.*"
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
) -> RentScheduleCorrectionResponse:
    actor_id = str(current_user.id)
    scope = await party_scope_resolver.resolve(db, user_id=actor_id)
    return await rent_schedule_correction_service.commit(
        db,
        contract_kind="terminal",
        contract_id=contract_id,
        request=payload,
        actor_id=actor_id,
        scope=scope,
        idempotency_key=idempotency_key.strip(),
    )


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
