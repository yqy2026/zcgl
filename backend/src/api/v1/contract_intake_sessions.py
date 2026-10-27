"""Contract-intake upload, review, confirmation and cancellation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import RedisCache, cache_manager
from ...core.exception_handler import (
    BaseBusinessError,
    ServiceUnavailableError,
    internal_error,
)
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.asset_operations import (
    ContractIntakeSessionResponse,
    ContractIntakeType,
    TerminalContractConfirmRequest,
    TerminalContractResponse,
    UpstreamContractConfirmRequest,
    UpstreamContractResponse,
)
from ...services.asset_operations.contract_intake_service import (
    ContractIntakeSessionService,
    build_contract_intake_session_service,
)
from ...services.asset_operations.errors import AssetOperationsPermissionDeniedError
from ...services.document.extraction_sessions import ExtractionSessionRepository
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


def _intake_service() -> ContractIntakeSessionService:
    backend = cache_manager.backend
    if not isinstance(backend, RedisCache):
        raise ServiceUnavailableError(
            "合同录入会话需要 Redis",
            service_name="contract_intake_sessions",
        )
    return build_contract_intake_session_service(
        repository=ExtractionSessionRepository(backend.client)
    )


AssetOpsWrite = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="write",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
    ),
]


@router.post(
    "/contract-intake-sessions",
    response_model=ContractIntakeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传已签合同扫描件并创建录入会话",
)
async def create_contract_intake_session(
    contract_type: Annotated[ContractIntakeType, Form()],
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AssetOpsWrite = None,
) -> ContractIntakeSessionResponse:
    _ = _authz
    try:
        return await _intake_service().create(
            db,
            file=file,
            contract_type=contract_type,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建合同录入会话失败", original_error=exc) from exc


@router.get(
    "/contract-intake-sessions/{session_id}",
    response_model=ContractIntakeSessionResponse,
    summary="读取合同录入会话",
)
async def get_contract_intake_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    _authz: AssetOpsWrite = None,
) -> ContractIntakeSessionResponse:
    _ = _authz
    try:
        return _intake_service().get(
            session_id=session_id,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("读取合同录入会话失败", original_error=exc) from exc


@router.post(
    "/contract-intake-sessions/{session_id}/confirm-upstream",
    response_model=UpstreamContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="确认并创建上游合同",
)
async def confirm_upstream_contract_intake(
    session_id: str,
    payload: UpstreamContractConfirmRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AssetOpsWrite = None,
) -> UpstreamContractResponse:
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await _intake_service().confirm_upstream(
            db,
            session_id=session_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("确认上游合同失败", original_error=exc) from exc


@router.post(
    "/contract-intake-sessions/{session_id}/confirm-terminal",
    response_model=TerminalContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="确认并创建终端合同",
)
async def confirm_terminal_contract_intake(
    session_id: str,
    payload: TerminalContractConfirmRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AssetOpsWrite = None,
) -> TerminalContractResponse:
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await _intake_service().confirm_terminal(
            db,
            session_id=session_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("确认终端合同失败", original_error=exc) from exc


@router.post(
    "/contract-intake-sessions/{session_id}/cancel",
    response_model=ContractIntakeSessionResponse,
    summary="取消合同录入会话",
)
async def cancel_contract_intake_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AssetOpsWrite = None,
) -> ContractIntakeSessionResponse:
    _ = _authz
    try:
        return await _intake_service().cancel(
            db,
            session_id=session_id,
            actor_id=str(current_user.id),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("取消合同录入会话失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
