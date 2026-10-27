"""Asset-unit command endpoints for the asset-operations workbench."""

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
    AssetUnitBoundaryCommitResponse,
    AssetUnitBoundaryPreviewResponse,
    AssetUnitDetail,
    AssetUnitListResponse,
    AssetUnitMergeCommitRequest,
    AssetUnitMergePreviewRequest,
    AssetUnitMergeProposal,
    AssetUnitResponse,
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPreviewRequest,
    AssetUnitSplitProposal,
    AssetUnitUpdate,
    AssetUnitVacancyNoteUpdate,
)
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    asset_operations_query_service,
    asset_unit_boundary_command_service,
    asset_unit_command_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/asset-units",
    response_model=AssetUnitListResponse,
    summary="查询资产单元列表",
)
async def list_asset_units(
    project_id: str | None = Query(None, description="项目过滤"),
    owner_party_id: str | None = Query(None, description="产权方过滤"),
    usage_type: str | None = Query(None, description="用途过滤"),
    q: str | None = Query(None, max_length=100, description="编号/名称/地址搜索"),
    filter: Literal["all", "non_rentable"] | None = Query(
        None, description="视图过滤：all / non_rentable"
    ),
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
) -> AssetUnitListResponse:
    """List scoped units with rental facts derived from live coverage."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        items, total = await asset_operations_query_service.list_asset_units(
            db,
            scope=scope,
            project_id=project_id,
            owner_party_id=owner_party_id,
            usage_type=usage_type,
            query=q,
            filter=filter,
            offset=offset,
            limit=limit,
        )
        return AssetUnitListResponse(items=items, total=total)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询资产单元列表失败", original_error=exc) from exc


@router.get(
    "/asset-units/{unit_id}",
    response_model=AssetUnitDetail,
    summary="查询资产单元详情",
)
async def get_asset_unit(
    unit_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                resource_id="{unit_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitDetail:
    """Return unit facts, derived rental status and live terminal contracts."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        detail = await asset_operations_query_service.get_asset_unit_detail(
            db,
            unit_id,
            scope=scope,
        )
        if detail is None:
            raise ResourceNotFoundError("AssetUnit", unit_id)
        return detail
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询资产单元详情失败", original_error=exc) from exc


@router.patch(
    "/asset-units/{unit_id}",
    response_model=AssetUnitResponse,
    summary="更新资产单元基本信息",
)
async def update_asset_unit(
    unit_id: str,
    payload: AssetUnitUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{unit_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitResponse:
    """Apply manual field edits under optimistic locking."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_command_service.update_asset_unit(
            db,
            unit_id=unit_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新资产单元失败", original_error=exc) from exc


@router.put(
    "/asset-units/{unit_id}/vacancy-note",
    response_model=AssetUnitResponse,
    summary="更新空置备注",
)
async def update_asset_unit_vacancy_note(
    unit_id: str,
    payload: AssetUnitVacancyNoteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{unit_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitResponse:
    """Record the vacancy reason and expected lease start."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_command_service.update_vacancy_note(
            db,
            unit_id=unit_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新空置备注失败", original_error=exc) from exc


@router.post(
    "/asset-units/{unit_id}/split/preview",
    response_model=AssetUnitBoundaryPreviewResponse,
    summary="预览资产单元拆分",
)
async def preview_asset_unit_split(
    unit_id: str,
    payload: AssetUnitSplitPreviewRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                resource_id="{unit_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitBoundaryPreviewResponse:
    """Validate one split proposal without writing boundary facts."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_boundary_command_service.preview(
            db,
            proposal=AssetUnitSplitProposal(
                source_unit_id=unit_id,
                effective_date=payload.effective_date,
                parts=payload.parts,
            ),
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("预览资产单元拆分失败", original_error=exc) from exc


@router.post(
    "/asset-units/{unit_id}/split",
    response_model=AssetUnitBoundaryCommitResponse,
    summary="提交资产单元拆分",
)
async def commit_asset_unit_split(
    unit_id: str,
    payload: AssetUnitSplitCommitRequest,
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
                resource_id="{unit_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitBoundaryCommitResponse:
    """Atomically commit the split described by a current preview token."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_boundary_command_service.commit(
            db,
            source_unit_id=unit_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("提交资产单元拆分失败", original_error=exc) from exc


@router.post(
    "/asset-units/merge/preview",
    response_model=AssetUnitBoundaryPreviewResponse,
    summary="预览资产单元合并",
)
async def preview_asset_unit_merge(
    payload: AssetUnitMergePreviewRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="write",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitBoundaryPreviewResponse:
    """Validate one merge proposal without writing boundary facts."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_boundary_command_service.preview_merge(
            db,
            proposal=AssetUnitMergeProposal.model_validate(
                payload.model_dump(mode="json")
            ),
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("预览资产单元合并失败", original_error=exc) from exc


@router.post(
    "/asset-units/merge",
    response_model=AssetUnitBoundaryCommitResponse,
    summary="提交资产单元合并",
)
async def commit_asset_unit_merge(
    payload: AssetUnitMergeCommitRequest,
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
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssetUnitBoundaryCommitResponse:
    """Atomically commit the merge described by a current preview token."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await asset_unit_boundary_command_service.commit_merge(
            db,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("提交资产单元合并失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
