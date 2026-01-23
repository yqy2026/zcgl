import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ...core.config import settings
from ...exceptions import BusinessLogicError
from ...models.auth import User, UserSession
from ...schemas.auth import TokenResponse
from ...security.token_blacklist import blacklist_manager
from .password_service import PasswordService
from .session_service import SessionService
from .user_management_service import UserManagementService

logger = logging.getLogger(__name__)

# Type aliases for better readability
TokenType = str
JtiType = str

# JWT配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


class AuthenticationService:
    """认证服务 - 协调者"""

    def __init__(self, db: Session):
        self.db = db
        self.password_service = PasswordService()
        self.user_service = UserManagementService(db)
        self.session_service = SessionService(db)
        self.token_blacklist = blacklist_manager

    def _generate_jti(self) -> JtiType:
        """生成JWT ID"""
        return secrets.token_urlsafe(32)

    def _is_token_revoked(self, jti: JtiType) -> bool:
        """检查令牌是否已被撤销"""
        return self.token_blacklist.is_blacklisted(jti)

    def authenticate_user(self, username: str, password: str) -> User | None:
        """用户认证"""
        # 支持用户名或邮箱登录
        user = (
            self.db.query(User)
            .filter(
                (User.username == username) | (User.email == username),
                User.is_active,
            )
            .first()
        )

        if not user:
            return None

        # 检查账户是否被锁定
        if user.is_locked_now():
            raise BusinessLogicError("账户已被锁定，请稍后再试")

        # 验证密码
        password_hash: str = getattr(user, "password_hash", "")
        if not self.password_service.verify_password(password, password_hash):
            # 增加失败次数
            user.failed_login_attempts += 1

            # 如果达到最大失败次数，锁定账户
            if user.failed_login_attempts >= settings.MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                user.locked_until = datetime.now() + timedelta(
                    minutes=settings.LOCKOUT_DURATION
                )

            self.db.commit()
            return None

        # 检查密码是否过期
        if self.password_service.is_password_expired(user):
            raise BusinessLogicError("密码已过期，请修改密码后重新登录")

        # 登录成功，重置失败次数
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            user.last_login_at = datetime.now()

        self.db.commit()
        return user

    def create_tokens(
        self, user: User, device_info: dict[str, Any] | None = None
    ) -> TokenResponse:
        """创建JWT令牌"""
        now = datetime.now(UTC)
        jti_access: JtiType = self._generate_jti()
        jti_refresh: JtiType = self._generate_jti()
        session_id: str = secrets.token_urlsafe(16)

        # 生成设备指纹
        device_fingerprint: str | None = None
        if device_info:
            import hashlib

            fingerprint_data: list[str] = [
                device_info.get("user_agent", ""),
                device_info.get("ip_address", ""),
                device_info.get("device_id", ""),
                device_info.get("platform", ""),
            ]
            fingerprint_string: str = "|".join(filter(None, fingerprint_data))
            device_fingerprint = hashlib.sha256(
                fingerprint_string.encode()
            ).hexdigest()[:16]

        # 访问令牌
        access_token_data: dict[str, Any] = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "type": "access",
            "jti": jti_access,
            "session_id": session_id,
            "device_fingerprint": device_fingerprint,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
            ),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        access_token: TokenType = jwt.encode(
            access_token_data, SECRET_KEY, algorithm=ALGORITHM
        )

        # 刷新令牌
        refresh_token_data: dict[str, Any] = {
            "sub": user.id,
            "type": "refresh",
            "jti": jti_refresh,
            "session_id": session_id,
            "device_fingerprint": device_fingerprint,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
            "nbf": int(now.timestamp()),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        refresh_token: TokenType = jwt.encode(
            refresh_token_data, SECRET_KEY, algorithm=ALGORITHM
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # nosec B106  # Standard OAuth token type, not a password
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=session_id,
        )

    def validate_refresh_token(
        self,
        refresh_token: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession | None:
        """验证刷新令牌"""
        try:
            payload: dict[str, Any] = jwt.decode(
                refresh_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                audience="land-property-system",
                issuer="land-property-auth",
            )
            user_id: Any = payload.get("sub")
            token_type: Any = payload.get("type")
            jti: Any = payload.get("jti")
            session_id: Any = payload.get("session_id")

            if user_id is None or token_type != "refresh":  # nosec B105  # Token type string, not a password
                return None

            if jti and self._is_token_revoked(jti):
                return None

        except JWTError as e:
            logger.error(f"JWT validation failed: {str(e)}")
            return None

        # 查找会话 (Delegating to SessionService would be cleaner but requires careful session loop handling)
        # Using session service for specific lookup
        session: UserSession | None = (
            self.db.query(UserSession)
            .filter(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active,
            )
            .first()
        )

        if not session or session.is_expired():
            return None

        # 检查用户是否仍然活跃
        user = self.user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            session.is_active = False
            self.db.commit()
            return None

        # 检查会话ID匹配
        if session_id and getattr(session, "session_id", None) != session_id:
            session.is_active = False
            self.db.commit()
            return None

        # 更新最后访问时间等
        session.last_accessed_at = datetime.now()
        if client_ip:
            setattr(session, "ip_address", client_ip)
        if user_agent:
            setattr(session, "user_agent", user_agent)
        self.db.commit()

        return session
