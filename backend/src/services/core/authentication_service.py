import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...crud.auth import UserCRUD, UserSessionCRUD
from ...exceptions import BusinessLogicError
from ...models.auth import User, UserSession
from ...security.token_blacklist import blacklist_manager
from .password_service import PasswordService
from .session_service import AsyncSessionService
from .user_management_service import AsyncUserManagementService

_user_crud = UserCRUD()
_session_crud = UserSessionCRUD()

logger = logging.getLogger(__name__)

# Type aliases for better readability
TokenType = str
JtiType = str

# Legacy exported constants (kept for backward compatibility in tests/importers).
# Runtime token operations below read from `settings` dynamically.
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = getattr(settings, "ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
JWT_AUDIENCE = settings.JWT_AUDIENCE
JWT_ISSUER = settings.JWT_ISSUER


def _utcnow_naive() -> datetime:
    """返回 naive UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class TokenPair:
    """Internal token container (not a public API schema)."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str | None = None


class AsyncAuthenticationService:
    """认证服务 - 协调者"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        password_service: PasswordService,
        user_service: AsyncUserManagementService,
        session_service: AsyncSessionService,
    ):
        self.db = db
        self.password_service = password_service
        self.user_service = user_service
        self.session_service = session_service
        self.token_blacklist = blacklist_manager

    def _generate_jti(self) -> JtiType:
        return secrets.token_urlsafe(32)

    def _build_device_fingerprint(
        self,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_id: str | None = None,
        platform: str | None = None,
    ) -> str | None:
        fingerprint_data: list[str] = [
            user_agent or "",
            ip_address or "",
            device_id or "",
            platform or "",
        ]
        fingerprint_string = "|".join(part for part in fingerprint_data if part != "")
        if fingerprint_string == "":
            return None
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    def _is_token_revoked(
        self, jti: JtiType | None, user_id: str | None = None
    ) -> bool:
        if not settings.TOKEN_BLACKLIST_ENABLED:
            return False
        if jti is None and user_id is None:
            return False
        return self.token_blacklist.is_blacklisted(jti=jti, user_id=user_id)

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await _user_crud.find_active_by_login_async(self.db, username)

        if not user:
            return None

        if user.is_locked_now():
            raise BusinessLogicError("账户已被锁定，请稍后再试")

        password_hash: str = getattr(user, "password_hash", "")
        if not self.password_service.verify_password(password, password_hash):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= settings.MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                user.locked_until = datetime.now() + timedelta(
                    minutes=settings.LOCKOUT_DURATION
                )

            await self.db.commit()
            return None

        if self.password_service.is_password_expired(user):
            raise BusinessLogicError("密码已过期，请修改密码后重新登录")

        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            user.last_login_at = datetime.now()

        await self.db.commit()
        return user

    def create_tokens(
        self, user: User, device_info: dict[str, Any] | None = None
    ) -> TokenPair:
        now = datetime.now(UTC)
        jti_access: JtiType = self._generate_jti()
        jti_refresh: JtiType = self._generate_jti()
        session_id: str = secrets.token_urlsafe(16)

        device_fingerprint: str | None = None
        if device_info:
            device_fingerprint = self._build_device_fingerprint(
                user_agent=device_info.get("user_agent"),
                ip_address=device_info.get("ip_address"),
                device_id=device_info.get("device_id"),
                platform=device_info.get("platform"),
            )

        access_token_data: dict[str, Any] = {
            "sub": user.id,
            "username": user.username,
            "type": "access",
            "jti": jti_access,
            "session_id": session_id,
            "device_fingerprint": device_fingerprint,
            "iat": int(now.timestamp()),
            "exp": int(
                (
                    now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                ).timestamp()
            ),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        access_token: TokenType = jwt.encode(
            access_token_data,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        refresh_token_data: dict[str, Any] = {
            "sub": user.id,
            "type": "refresh",
            "jti": jti_refresh,
            "session_id": session_id,
            "device_fingerprint": device_fingerprint,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()
            ),
            "nbf": int(now.timestamp()),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        refresh_token: TokenType = jwt.encode(
            refresh_token_data,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=session_id,
        )

    async def validate_refresh_token(
        self,
        refresh_token: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession | None:
        try:
            payload: dict[str, Any] = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[getattr(settings, "ALGORITHM", "HS256")],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
            user_id: Any = payload.get("sub")
            token_type: Any = payload.get("type")
            jti: Any = payload.get("jti")
            session_id: Any = payload.get("session_id")
            token_device_fingerprint: Any = payload.get("device_fingerprint")

            if user_id is None or token_type != "refresh":
                return None

            if self._is_token_revoked(jti, user_id=str(user_id) if user_id else None):
                return None

        except JWTError as e:
            logger.error(f"JWT validation failed: {str(e)}")
            return None

        session: UserSession | None = await _session_crud.get_active_by_refresh_token_async(
            self.db, refresh_token
        )

        if not session or session.is_expired():
            return None

        user = await self.user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            session.is_active = False
            await self.db.commit()
            return None

        if session_id and getattr(session, "session_id", None) != session_id:
            session.is_active = False
            await self.db.commit()
            return None

        if token_device_fingerprint:
            user_id_str = str(user_id)
            expected_fingerprints = {
                self._build_device_fingerprint(
                    user_agent=user_agent,
                    ip_address=client_ip,
                    device_id=user_id_str,
                    platform=None,
                ),
                # 兼容旧令牌（未纳入 user_id 参与指纹计算）
                self._build_device_fingerprint(
                    user_agent=user_agent,
                    ip_address=client_ip,
                    device_id=None,
                    platform=None,
                ),
            }
            expected_fingerprints.discard(None)
            if token_device_fingerprint not in expected_fingerprints:
                session.is_active = False
                await self.db.commit()
                return None

        session.last_accessed_at = _utcnow_naive()
        if client_ip:
            setattr(session, "ip_address", client_ip)
        if user_agent:
            setattr(session, "user_agent", user_agent)
        await self.db.commit()

        return session


