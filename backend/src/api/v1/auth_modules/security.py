"""
安全配置API路由

包含: 安全配置查询
"""

from typing import Any

from fastapi import APIRouter, Depends

from ....middleware.auth import require_admin, SecurityConfig
from ....schemas.auth import UserResponse

router = APIRouter(prefix="/security", tags=["安全配置"])


@router.get("/config", response_model=dict[str, Any], summary="获取安全配置")
async def get_security_config(
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    获取安全配置信息（仅管理员）
    """
    return {
        "password_policy": SecurityConfig.get_password_policy(),
        "token_config": SecurityConfig.get_token_config(),
        "session_config": {
            "max_concurrent_sessions": SecurityConfig.MAX_CONCURRENT_SESSIONS,
            "session_expire_days": SecurityConfig.SESSION_EXPIRE_DAYS,
        },
        "audit_config": {"log_retention_days": SecurityConfig.AUDIT_LOG_RETENTION_DAYS},
    }
