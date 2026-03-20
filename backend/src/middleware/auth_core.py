"""
认证核心 — Token 验证与用户解析。
"""

import logging

from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.environment import is_production
from ..core.exception_handler import (
    BaseBusinessError,
    bad_request,
    unauthorized,
)
from ..database import get_async_db
from ..models.auth import User
from ..schemas.auth import TokenData
from ..security.cookie_manager import cookie_manager
from ..services import RBACService
from .token_blacklist_guard import TokenBlacklistGuard

try:
    import jwt
    from jwt import PyJWTError as JWTError
except ImportError:  # pragma: no cover
    raise

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token blacklist guard (module-level singleton)
# ---------------------------------------------------------------------------

_token_blacklist_guard = TokenBlacklistGuard(is_production=lambda: is_production())
_token_blacklist_circuit = _token_blacklist_guard.circuit


def _is_token_blacklisted(
    jti: str | None,
    user_id: str | None = None,
    session_id: str | None = None,
    token_iat: int | float | None = None,
) -> bool:
    """检查 token 是否在黑名单中（熔断/异常统一 fail-closed）。"""
    return _token_blacklist_guard.is_token_blacklisted(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
        token_iat=token_iat,
    )


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _get_jwt_settings() -> tuple[str, str, str, str]:
    return (
        settings.SECRET_KEY,
        getattr(settings, "ALGORITHM", "HS256"),
        settings.JWT_AUDIENCE,
        settings.JWT_ISSUER,
    )


def _validate_jwt_token(token: str) -> TokenData:
    """
    共享的JWT验证逻辑

    Args:
        token: JWT token string

    Returns:
        TokenData: 解析并验证后的token数据

    Raises:
        HTTPException: 如果token无效或验证失败
    """
    credentials_exception = unauthorized("无效的认证凭据")

    try:
        secret_key, algorithm, audience, issuer = _get_jwt_settings()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
        )

        user_id: str | None = payload.get("sub")
        username: str | None = payload.get("username")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")
        jti: str | None = payload.get("jti")  # JWT ID for token tracking

        # 验证必需字段
        if user_id is None or username is None:
            logger.warning(
                f"JWT token missing required fields: sub={user_id}, username={username}"
            )
            raise credentials_exception

        # 验证过期时间（虽然jwt.decode已经验证，但双重检查更安全）
        if exp is None:
            logger.warning("JWT token missing expiration time")
            raise credentials_exception

        # 验证签发时间
        if iat is None:
            logger.warning("JWT token missing issued at time")
            raise credentials_exception

        # 验证token是否在黑名单中（如果实现了token黑名单）
        if _is_token_blacklisted(
            jti=jti, user_id=user_id, session_id=None, token_iat=iat
        ):
            logger.warning(f"JWT token {jti} is blacklisted")
            raise unauthorized("Token已失效")

        # 使用标准的TokenData Pydantic模型
        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as e:
            # 如果TokenData验证失败，记录错误并抛出认证异常
            logger.error(f"TokenData validation failed: {e}")
            raise credentials_exception

    except BaseBusinessError:
        raise
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception("Unexpected JWT validation error: %s", e)
        raise credentials_exception

    return token_data


# ---------------------------------------------------------------------------
# User resolution dependencies (FastAPI Depends)
# ---------------------------------------------------------------------------


async def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Cookie-only authentication. Tokens are read from httpOnly cookies.
    """
    credentials_exception = unauthorized("无效的认证凭据")

    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in cookie
    if not token:
        raise credentials_exception

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise credentials_exception

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise unauthorized("用户账户已被禁用")

    if user.is_locked_now():
        raise unauthorized("用户账户已被锁定，请稍后再试")

    logger.debug(f"Successfully authenticated user {user.username}")
    return user


async def get_current_user_from_cookie(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current user from httpOnly cookie.

    Args:
        auth_token: JWT from httpOnly cookie (automatically sent by browser)
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        unauthorized: If no valid token found or user is inactive/locked
    """
    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in either cookie or header
    if not token:
        raise unauthorized("Not authenticated")

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise unauthorized("Invalid token")

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise unauthorized("Invalid authentication credentials")

    # Check if user is active
    if not user.is_active:
        raise unauthorized("User account is disabled")

    # Check if user is locked
    if user.is_locked_now():
        raise unauthorized("User account is locked, please try again later")

    logger.debug(
        f"Successfully authenticated user {user.username} via cookie-based auth"
    )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise bad_request("用户账户未激活")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """要求管理员权限"""
    from ..core.exception_handler import forbidden

    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id):
        raise forbidden("需要管理员权限")
    return current_user


async def get_optional_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User | None:
    """获取可选的当前用户（用于可选认证的端点）"""
    resolved_token = auth_token

    if not resolved_token:
        return None

    try:
        token_data = _validate_jwt_token(resolved_token)
    except Exception:
        return None

    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user and user.is_active and not user.is_locked_now():
        return user

    return None
