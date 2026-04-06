from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error
from ...core.response_handler import ResponseHandler
from ...database import get_async_db
from ...middleware.auth import (
    DataScopeContext,
    get_current_active_user,
    require_data_scope_context,
)
from ...models.auth import User
from ...schemas.search import GlobalSearchResponse
from ...services.search import search_service

router = APIRouter(tags=["全局搜索"])


@router.get("", summary="全局搜索")
async def global_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="search")
    ),
) -> object:
    _ = current_user
    try:
        result = await search_service.search_global(
            db=db,
            query=q,
            scope_mode=_scope_ctx.scope_mode,
            effective_party_ids=_scope_ctx.effective_party_ids,
        )
        normalized_result = GlobalSearchResponse.model_validate(result)
        return ResponseHandler.success(
            data=normalized_result.model_dump(mode="json"),
            message="搜索成功",
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("执行全局搜索失败", original_error=exc) from exc
