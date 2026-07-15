"""Identity resolution dependencies for auth middleware."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

import jwt
from fastapi import Cookie, Depends
from jwt import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.environment import is_production
from ..core.exception_handler import BaseBusinessError, bad_request, unauthorized
from ..database import get_async_db
from ..models.auth import User
from ..schemas.auth import TokenData
from ..security.cookie_manager import cookie_manager
from .token_blacklist_guard import TokenBlacklistGuard

logger = logging.getLogger(__name__)

TokenValidator = Callable[[str], TokenData]


class BlacklistChecker(Protocol):
    def __call__(
        self,
        *,
        jti: str | None,
        user_id: str | None = None,
        session_id: str | None = None,
        token_iat: int | float | None = None,
    ) -> bool: ...


_token_blacklist_guard = TokenBlacklistGuard(is_production=lambda: is_production())
_token_blacklist_circuit = _token_blacklist_guard.circuit


def _is_token_blacklisted(
    jti: str | None,
    user_id: str | None = None,
    session_id: str | None = None,
    token_iat: int | float | None = None,
) -> bool:
    """Check token blacklist state, failing closed on guard degradation."""
    return _token_blacklist_guard.is_token_blacklisted(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
        token_iat=token_iat,
    )


def _get_jwt_settings() -> tuple[str, str, str, str]:
    return (
        settings.SECRET_KEY,
        getattr(settings, "ALGORITHM", "HS256"),
        settings.JWT_AUDIENCE,
        settings.JWT_ISSUER,
    )


def _validate_jwt_token(
    token: str,
    *,
    blacklist_checker: BlacklistChecker | None = None,
    log: logging.Logger | None = None,
) -> TokenData:
    """Decode and validate a JWT access token."""
    credentials_exception = unauthorized("无效的认证凭据")
    active_blacklist_checker = blacklist_checker or _is_token_blacklisted
    active_logger = log or logger

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
        jti: str | None = payload.get("jti")

        if user_id is None or username is None:
            active_logger.warning(
                "JWT token missing required fields: sub=%s, username=%s",
                user_id,
                username,
            )
            raise credentials_exception

        if exp is None:
            active_logger.warning("JWT token missing expiration time")
            raise credentials_exception

        if iat is None:
            active_logger.warning("JWT token missing issued at time")
            raise credentials_exception

        if active_blacklist_checker(
            jti=jti,
            user_id=user_id,
            session_id=None,
            token_iat=iat,
        ):
            active_logger.warning("JWT token %s is blacklisted", jti)
            raise unauthorized("Token已失效")

        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as error:
            active_logger.error("TokenData validation failed: %s", error)
            raise credentials_exception

    except BaseBusinessError:
        raise
    except JWTError as error:
        active_logger.warning("JWT decode error: %s", error)
        raise credentials_exception
    except Exception as error:
        active_logger.exception("Unexpected JWT validation error: %s", error)
        raise credentials_exception

    return token_data


async def _load_user_by_token_data(
    *, db: AsyncSession, token_data: TokenData
) -> User | None:
    user_stmt = select(User).where(User.id == token_data.sub)
    return (await db.execute(user_stmt)).scalars().first()


async def resolve_current_user(
    *,
    auth_token: str | None,
    db: AsyncSession,
    missing_token_message: str,
    invalid_token_message: str,
    missing_user_message: str,
    disabled_user_message: str,
    locked_user_message: str,
    token_validator: TokenValidator = _validate_jwt_token,
) -> User:
    """Resolve a required authenticated user from a cookie token."""
    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    if not token:
        raise unauthorized(missing_token_message)

    try:
        token_data = token_validator(token)
    except Exception:
        raise unauthorized(invalid_token_message)

    user = await _load_user_by_token_data(db=db, token_data=token_data)
    if user is None:
        raise unauthorized(missing_user_message)

    if not user.is_active:
        raise unauthorized(disabled_user_message)

    if user.is_locked_now():
        raise unauthorized(locked_user_message)

    logger.debug("Successfully authenticated user %s", user.username)
    return user


async def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Get current authenticated user from the httpOnly auth cookie."""
    return await resolve_current_user(
        # The request-provided JWT is not a hardcoded credential.
        auth_token=auth_token,  # nosec B106
        db=db,
        missing_token_message="无效的认证凭据",
        invalid_token_message="无效的认证凭据",
        missing_user_message="无效的认证凭据",
        disabled_user_message="用户账户已被禁用",
        locked_user_message="用户账户已被锁定，请稍后再试",
    )


async def get_current_user_from_cookie(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Get current authenticated user from the httpOnly auth cookie."""
    return await resolve_current_user(
        # The request-provided JWT is not a hardcoded credential.
        auth_token=auth_token,  # nosec B106
        db=db,
        missing_token_message="Not authenticated",
        invalid_token_message="Invalid token",
        missing_user_message="Invalid authentication credentials",
        disabled_user_message="User account is disabled",
        locked_user_message="User account is locked, please try again later",
    )


def ensure_current_active_user(current_user: User) -> User:
    """Validate that the already-resolved user is active."""
    if not current_user.is_active:
        raise bad_request("用户账户未激活")
    return current_user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the active current user."""
    return ensure_current_active_user(current_user)


async def resolve_optional_current_user(
    *,
    auth_token: str | None,
    db: AsyncSession,
    token_validator: TokenValidator = _validate_jwt_token,
) -> User | None:
    """Resolve an optional authenticated user from a cookie token."""
    if not auth_token:
        return None

    try:
        token_data = token_validator(auth_token)
    except Exception:
        return None

    user = await _load_user_by_token_data(db=db, token_data=token_data)
    if user and user.is_active and not user.is_locked_now():
        return user

    return None


async def get_optional_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User | None:
    """Get optional current user for endpoints with optional auth."""
    return await resolve_optional_current_user(auth_token=auth_token, db=db)
