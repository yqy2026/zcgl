"""Scoped read-only archive completion and property matrix, current or as-of."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import AuthzContext, get_current_active_user, require_authz
from ...models.auth import User
from ...schemas.archive_matrix import ArchiveCompletion, ArchiveMatrix
from ...services.asset_operations import AssetOperationsPermissionDeniedError
from ...services.asset_operations.archive_matrix_service import archive_matrix_service
from ...services.party_scope_resolver import party_scope_resolver

router = APIRouter()
ReadAccess = Annotated[
    AuthzContext | None,
    Depends(
        require_authz(
            action="read",
            resource_type="asset_ops",
            denial_error_factory=AssetOperationsPermissionDeniedError,
        )
    ),
]


@router.get("/archive/completion", response_model=ArchiveCompletion)
async def completion(
    project_id: str | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    as_of: date | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAccess = None,
) -> ArchiveCompletion:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await archive_matrix_service.completion(
        db, scope=scope, project_id=project_id, query=q, as_of=as_of
    )


@router.get("/archive/matrix", response_model=ArchiveMatrix)
async def matrix(
    project_id: str | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    as_of: date | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: ReadAccess = None,
) -> ArchiveMatrix:
    scope = await party_scope_resolver.resolve(db, user_id=str(current_user.id))
    return await archive_matrix_service.matrix(
        db,
        scope=scope,
        project_id=project_id,
        query=q,
        offset=offset,
        limit=limit,
        as_of=as_of,
    )


route_registry.register_router(
    router, prefix="/api/v1", tags=["资产运营档案"], version="v1"
)
