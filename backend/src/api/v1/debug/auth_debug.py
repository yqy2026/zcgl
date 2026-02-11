"""
认证调试端点 - 从 authentication.py 迁移

仅在 DEBUG=true 时通过 main.py 条件加载。
生产环境不会注册这些路由。
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....security.route_guards import debug_only, require_localhost
from ....services.core.authentication_service import AsyncAuthenticationService
from ....services.core.password_service import PasswordService
from ....services.core.session_service import AsyncSessionService
from ....services.core.user_management_service import AsyncUserManagementService
from ....services.factory import ServiceFactory, get_service_factory
from ....services.permission.rbac_service import RBACService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth Debug"], dependencies=[Depends(require_localhost)])

_get_factory = get_service_factory()


def _build_legacy_services(
    db: AsyncSession,
) -> tuple[
    AsyncAuthenticationService,
    AsyncUserManagementService,
    PasswordService,
    RBACService,
]:
    password_service = PasswordService()
    session_service = AsyncSessionService(db)
    rbac_service = RBACService(db)
    user_service = AsyncUserManagementService(
        db,
        password_service=password_service,
        session_service=session_service,
        rbac_service=rbac_service,
    )
    auth_service = AsyncAuthenticationService(
        db,
        password_service=password_service,
        user_service=user_service,
        session_service=session_service,
    )
    return auth_service, user_service, password_service, rbac_service


@router.get("/test-features", summary="测试功能端点")
@debug_only
async def test_features() -> dict[str, Any]:
    """测试端点，验证功能可用性"""
    return {
        "success": True,
        "message": "功能测试正常",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/auth", summary="调试认证流程")
@debug_only
async def debug_auth(
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> dict[str, Any]:
    """调试认证流程，测试各个步骤"""
    try:
        test_username = os.getenv("DEBUG_AUTH_USERNAME", "admin")
        test_password = os.getenv("DEBUG_AUTH_PASSWORD")

        if not test_password:
            return {
                "error": "Test credentials not configured",
                "hint": "Set DEBUG_AUTH_PASSWORD environment variable for debug endpoint",
            }

        if isinstance(factory, ServiceFactory):
            auth_service = factory.authentication
            user_service = factory.user_management
            password_service = factory.password
            rbac_service = factory.rbac
        else:
            auth_service, user_service, password_service, rbac_service = (
                _build_legacy_services(db)
            )

        admin_user = await user_service.get_user_by_username(test_username)
        if not admin_user:
            return {"error": f"Test user '{test_username}' not found"}

        password_valid = password_service.verify_password(
            test_password, admin_user.password_hash
        )

        auth_error_debug: str | None = None
        authenticated_user = None
        try:
            authenticated_user = await auth_service.authenticate_user(
                test_username, test_password
            )
            auth_success = authenticated_user is not None
        except Exception as auth_exc:
            auth_success = False
            auth_error_debug = str(auth_exc)

        token_error: str | None = None
        try:
            if authenticated_user:
                tokens = auth_service.create_tokens(authenticated_user)
                token_success = True
                access_token_length = (
                    len(tokens.access_token) if tokens.access_token else 0
                )
            else:
                token_success = False
                access_token_length = 0
        except Exception as e:
            token_success = False
            access_token_length = 0
            token_error = str(e)

        role_summary = await rbac_service.get_user_role_summary(str(admin_user.id))

        return {
            "admin_user_found": admin_user is not None,
            "admin_username": admin_user.username if admin_user else None,
            "admin_roles": role_summary["roles"],
            "password_valid": password_valid,
            "auth_success": auth_success,
            "auth_error": auth_error_debug,
            "token_success": token_success,
            "token_error": token_error,
            "access_token_length": access_token_length,
        }

    except Exception as e:
        return {"error": f"Debug endpoint error: {str(e)}"}


@router.get("/me", summary="调试ME端点")
@debug_only
async def test_me_debug(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> dict[str, Any]:
    """调试ME端点，检查UserResponse内容"""
    # 检查 UserResponse 的所有字段
    user_dict = {
        key: value
        for key, value in vars(current_user).items()
        if not key.startswith("_")
    }
    logger.debug(f"UserResponse fields: {len(user_dict.keys())} fields")

    if isinstance(factory, ServiceFactory):
        rbac_service = factory.rbac
    else:
        rbac_service = RBACService(db)
    role_summary = await rbac_service.get_user_role_summary(str(current_user.id))

    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "id": current_user.id,
        "role_id": role_summary["primary_role_id"],
        "role_name": role_summary["primary_role_name"],
        "roles": role_summary["roles"],
        "role_ids": role_summary["role_ids"],
        "is_active": current_user.is_active,
        "is_admin": role_summary["is_admin"],
        "timestamp": datetime.now(UTC).isoformat(),
        "session_status": "active",
    }
