"""Assessment-scope endpoints for the asset-operations reporting vertical."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.asset_operations import (
    AssessmentScopeCommitRequest,
    AssessmentScopeCommitResponse,
    AssessmentScopeDraftResponse,
    AssessmentScopeOverviewResponse,
    AssessmentScopePreviewResponse,
    CreateAssessmentScopeDraftRequest,
    UpdateAssessmentScopeDraftRequest,
)
from ...services.asset_operations import (
    AssetOperationsPermissionDeniedError,
    assessment_scope_command_service,
)
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter(tags=["资产运营"])


@router.get(
    "/assessment-scopes/{year}",
    response_model=AssessmentScopeOverviewResponse,
    summary="查询年度考核范围当前版本",
)
async def get_assessment_scope_overview(
    year: int,
    operator_party_id: Annotated[str, Query(min_length=1)],
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
) -> AssessmentScopeOverviewResponse:
    """Return the active version, decisions, pending units and current rate."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.get_overview(
            db,
            operator_party_id=operator_party_id,
            year=year,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询年度考核范围失败", original_error=exc) from exc


@router.get(
    "/assessment-scope-drafts/{draft_id}",
    response_model=AssessmentScopeDraftResponse,
    summary="查询考核范围草稿",
)
async def get_assessment_scope_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="asset_ops",
                resource_id="{draft_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssessmentScopeDraftResponse:
    """Resolve the draft's operator party and re-authorize the whole unit."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.get_draft(
            db,
            draft_id=draft_id,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询考核范围草稿失败", original_error=exc) from exc


@router.post(
    "/assessment-scopes/{year}/drafts",
    response_model=AssessmentScopeDraftResponse,
    summary="创建年度考核范围草稿",
)
async def create_assessment_scope_draft(
    year: int,
    payload: CreateAssessmentScopeDraftRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssessmentScopeDraftResponse:
    """Derive one editable draft per operator party and year."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.create_draft(
            db,
            year=year,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建考核范围草稿失败", original_error=exc) from exc


@router.put(
    "/assessment-scope-drafts/{draft_id}",
    response_model=AssessmentScopeDraftResponse,
    summary="更新考核范围草稿决定",
)
async def update_assessment_scope_draft(
    draft_id: str,
    payload: UpdateAssessmentScopeDraftRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                resource_id="{draft_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssessmentScopeDraftResponse:
    """Apply explicit include/exclude decisions under optimistic locking."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.update_draft(
            db,
            draft_id=draft_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更新考核范围草稿失败", original_error=exc) from exc


@router.post(
    "/assessment-scope-drafts/{draft_id}/preview",
    response_model=AssessmentScopePreviewResponse,
    summary="预览考核范围草稿影响",
)
async def preview_assessment_scope_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="report",
                resource_type="asset_ops",
                resource_id="{draft_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssessmentScopePreviewResponse:
    """Compare the draft with the active version and bind a commit token."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.preview(
            db,
            draft_id=draft_id,
            actor_id=actor_id,
            scope=scope,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("预览考核范围草稿失败", original_error=exc) from exc


@router.post(
    "/assessment-scope-drafts/{draft_id}/commit",
    response_model=AssessmentScopeCommitResponse,
    summary="保存年度考核范围新版本",
)
async def commit_assessment_scope_draft(
    draft_id: str,
    payload: AssessmentScopeCommitRequest,
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
                action="report",
                resource_type="asset_ops",
                resource_id="{draft_id}",
                denial_error_factory=AssetOperationsPermissionDeniedError,
            )
        ),
    ] = None,
) -> AssessmentScopeCommitResponse:
    """Activate the draft atomically and supersede the previous version."""
    _ = _authz
    try:
        actor_id = str(current_user.id)
        scope = await party_scope_resolver.resolve(db, user_id=actor_id)
        return await assessment_scope_command_service.commit(
            db,
            draft_id=draft_id,
            request=payload,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key.strip(),
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("保存考核范围版本失败", original_error=exc) from exc


route_registry.register_router(
    router,
    prefix="/api/v1",
    tags=["资产运营"],
    version="v1",
)


__all__ = ["router"]
