"""ABAC authorization endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, internal_error
from ...core.router_registry import route_registry
from ...database import get_async_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.authz import AuthzCheckRequest, AuthzCheckResponse
from ...services.authz import authz_service

router = APIRouter(tags=["鉴权服务"])


@router.post("/authz/check", response_model=AuthzCheckResponse, summary="ABAC 判定")
async def check_authz(
    request: AuthzCheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> AuthzCheckResponse:
    """Evaluate whether current user can perform action on target resource."""
    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type=request.resource_type,
            action=request.action,
            resource_id=request.resource_id,
            resource=request.resource,
        )
        return AuthzCheckResponse(
            allowed=decision.allowed,
            reason_code=decision.reason_code,
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("ABAC 判定失败", original_error=exc) from exc


route_registry.register_router(router, prefix="/api/v1", tags=["鉴权服务"], version="v1")


__all__ = ["router"]
