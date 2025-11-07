class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
认证服务
"""

import base64
import json
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.token_blacklist import blacklist_manager
from ...exceptions import BusinessLogicError
from ...models.auth import AuditLog, User, UserSession
from ...schemas.auth import (
    TokenResponse,
    UserCreate,
    UserSessionResponse,
    UserUpdate,
)

# JWT配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# 密码策略
MIN_PASSWORD_LENGTH = settings.MIN_PASSWORD_LENGTH
MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_ATTEMPTS
LOCKOUT_DURATION_MINUTES = settings.LOCKOUT_DURATION
# 密码过期策略（天数）
PASSWORD_EXPIRE_DAYS = int(getattr(settings, "PASSWORD_EXPIRE_DAYS", 90))


class AuthService:
    """认证服务"""

    def __init__(self, db: Session):
        self.db = db
        self.token_blacklist = blacklist_manager
        
    def _generate_jti(self) -> str:
        """生成JWT ID"""
        import secrets
        return secrets.token_urlsafe(32)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            # 处理base64编码的哈希
            if isinstance(hashed_password, str):
                if hashed_password.startswith("$2b$"):
                    # 标准bcrypt哈希
                    return bcrypt.checkpw(
                        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
                    )
                else:
                    # 可能是base64编码的
                    try:
                        decoded_hash = base64.b64decode(hashed_password)
                        return bcrypt.checkpw(
                            plain_password.encode("utf-8"), decoded_hash
                        )
                    except (base64.binascii.Error, ValueError):
                        return bcrypt.checkpw(
                            plain_password.encode("utf-8"),
                            hashed_password.encode("utf-8"),
                        )
            else:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password)
        except Exception:
            return False

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < MIN_PASSWORD_LENGTH:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return has_upper and has_lower and has_digit and has_special

    def is_password_in_history(self, user: User, password: str) -> bool:
        """检查密码是否在历史记录中"""
        if not user.password_history:
            return False

        try:
            # 解析密码历史记录
            if isinstance(user.password_history, str):
                password_history = json.loads(user.password_history)
            else:
                password_history = user.password_history

            # 检查密码是否与历史记录中的任何密码匹配
            for old_hash in password_history:
                if self.verify_password(password, old_hash):
                    return True
        except (json.JSONDecodeError, TypeError):
            # 如果解析失败，返回False
            return False

        return False

    def add_password_to_history(self, user: User, password_hash: str):
        """将密码哈希添加到历史记录中"""
        # 获取现有历史记录或创建空列表
        if user.password_history:
            try:
                if isinstance(user.password_history, str):
                    password_history = json.loads(user.password_history)
                else:
                    password_history = user.password_history
            except (json.JSONDecodeError, TypeError):
                password_history = []
        else:
            password_history = []

        # 添加新密码哈希到历史记录
        password_history.append(password_hash)

        # 保留最近10个密码
        if len(password_history) > 10:
            password_history = password_history[-10:]

        # 更新用户记录
        user.password_history = json.dumps(password_history)
        user.password_last_changed = datetime.now()

    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = (
            self.db.query(User)
            .filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
            .first()
        )
        if existing_user:
            if existing_user.username == user_data.username:
                raise BusinessLogicError("用户名已存在")
            else:
                raise BusinessLogicError("邮箱已存在")

        # 验证密码强度
        if not self.validate_password_strength(user_data.password):
            raise BusinessLogicError("密码不符合安全要求")

        # 创建新用户
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password,
            role=user_data.role,
            employee_id=user_data.employee_id,
            default_organization_id=user_data.default_organization_id,
        )

        # 将密码添加到历史记录
        self.add_password_to_history(db_user, hashed_password)

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

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
        if not self.verify_password(password, user.password_hash):
            # 增加失败次数
            user.failed_login_attempts += 1

            # 如果达到最大失败次数，锁定账户
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                user.locked_until = datetime.now() + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )

            self.db.commit()
            return None

        # 检查密码是否过期
        if self.is_password_expired(user):
            raise BusinessLogicError("密码已过期，请修改密码后重新登录")

        # 登录成功，重置失败次数
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            user.last_login_at = datetime.now()

        self.db.commit()
        return user

    def is_password_expired(self, user: User) -> bool:
        """检查密码是否过期"""
        if not user.password_last_changed:
            return False

        # 如果PASSWORD_EXPIRE_DAYS为0或负数，表示不启用密码过期策略
        if PASSWORD_EXPIRE_DAYS <= 0:
            return False

        # 计算密码过期时间
        expire_time = user.password_last_changed + timedelta(days=PASSWORD_EXPIRE_DAYS)
        return datetime.now() > expire_time

    def create_tokens(self, user: User, device_info: dict | None = None) -> TokenResponse:
        """创建JWT令牌 - 增强安全性"""
        now = datetime.now(UTC)
        jti_access = self._generate_jti()
        jti_refresh = self._generate_jti()
        session_id = secrets.token_urlsafe(16)
        
        # 生成设备指纹
        device_fingerprint = None
        if device_info:
            import hashlib
            fingerprint_data = [
                device_info.get("user_agent", ""),
                device_info.get("ip_address", ""),
                device_info.get("device_id", ""),
                device_info.get("platform", ""),
            ]
            fingerprint_string = "|".join(filter(None, fingerprint_data))
            device_fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

        # 访问令牌 - 增强安全性
        access_token_data = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "type": "access",
            "jti": jti_access,  # JWT ID用于撤销
            "session_id": session_id,  # 会话ID
            "device_fingerprint": device_fingerprint,  # 设备指纹
            "iat": int(now.timestamp()),  # 签发时间
            "exp": int(
                (now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
            ),
            "aud": "land-property-system",  # 受众
            "iss": "land-property-auth",     # 签发者
        }
        access_token = jwt.encode(access_token_data, SECRET_KEY, algorithm=ALGORITHM)

        # 刷新令牌 - 增强安全性
        refresh_token_data = {
            "sub": user.id,
            "type": "refresh",
            "jti": jti_refresh,  # JWT ID用于撤销
            "session_id": session_id,  # 会话ID
            "device_fingerprint": device_fingerprint,  # 设备指纹
            "iat": int(now.timestamp()),  # 签发时间
            "exp": int((now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
            "nbf": int(now.timestamp()),  # 生效时间
            "aud": "land-property-system",  # 受众
            "iss": "land-property-auth",     # 签发者
        }
        refresh_token = jwt.encode(refresh_token_data, SECRET_KEY, algorithm=ALGORITHM)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=session_id,
        )

    def create_user_session(
        self,
        user_id: str,
        refresh_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> UserSession:
        """创建用户会话"""
        # 检查是否已有活跃会话
        existing_sessions = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active)
            .all()
        )

        # 限制并发会话数量
        if len(existing_sessions) >= settings.MAX_CONCURRENT_SESSIONS:
            # 取消最旧的会话
            oldest_session = min(existing_sessions, key=lambda x: x.created_at)
            oldest_session.is_active = False

        # 提取设备信息
        device_id = None
        platform = None
        if device_info:
            # 如果device_info是字符串，尝试解析为JSON
            import json
            try:
                if isinstance(device_info, str):
                    device_data = json.loads(device_info)
                else:
                    device_data = device_info
                device_id = device_data.get("device_id")
                platform = device_data.get("platform")
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，将整个device_info作为device_info字段存储
                pass

        user_session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            session_id=session_id,
            device_info=device_info if not isinstance(device_info, dict) else json.dumps(device_info),
            device_id=device_id,
            platform=platform,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(days=settings.SESSION_EXPIRE_DAYS),
        )

        self.db.add(user_session)
        self.db.commit()
        self.db.refresh(user_session)

        return user_session

    def validate_refresh_token(self, refresh_token: str, client_ip: str | None = None, user_agent: str | None = None) -> UserSession | None:
        """验证刷新令牌 - 增强安全性"""
        try:
            # 增强JWT验证，添加受众和签发者验证
            payload = jwt.decode(
                refresh_token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="land-property-system",
                issuer="land-property-auth"
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")
            jti = payload.get("jti")
            iat = payload.get("iat")
            nbf = payload.get("nbf")
            exp = payload.get("exp")
            aud = payload.get("aud")
            iss = payload.get("iss")
            session_id = payload.get("session_id")
            device_fingerprint = payload.get("device_fingerprint")

            # 严格验证令牌字段
            if user_id is None or token_type != "refresh":
                return None

            if jti is None or iat is None:
                return None

            # 验证受众和签发者
            if aud != "land-property-system" or iss != "land-property-auth":
                return None

            # 验证生效时间（防止时间攻击）
            if nbf and nbf > datetime.now(UTC).timestamp():
                return None

            # 验证过期时间
            if exp and exp < datetime.now(UTC).timestamp():
                return None

        except JWTError as e:
            # 记录具体的JWT错误用于安全监控
            print(f"JWT validation failed: {str(e)}")
            return None

        # 查找会话
        session = (
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
        user = self.get_user_by_id(user_id)
        if not user or not user.is_active:
            # 用户已被停用，撤销会话
            session.is_active = False
            self.db.commit()
            return None

        # 检查令牌是否已被撤销（通过JTI）
        if self._is_token_revoked(jti):
            session.is_active = False
            self.db.commit()
            return None

        # 检查会话ID匹配
        if session_id and getattr(session, 'session_id', None) != session_id:
            # 会话ID不匹配，可能存在安全问题
            session.is_active = False
            self.db.commit()
            return None

        # 检查设备指纹（如果提供）
        if device_fingerprint and client_ip and user_agent:
            import hashlib
            current_fingerprint_data = [
                user_agent or "",
                client_ip or "",
                getattr(session, 'device_id', ""),
                getattr(session, 'platform', ""),
            ]
            current_fingerprint_string = "|".join(filter(None, current_fingerprint_data))
            current_fingerprint = hashlib.sha256(current_fingerprint_string.encode()).hexdigest()[:16]
            
            if device_fingerprint != current_fingerprint:
                # 设备指纹不匹配，记录安全事件但允许继续（可配置）
                print(f"警告：设备指纹不匹配，用户 {getattr(user, 'username', 'unknown')} 的设备可能发生变化")

        # 检查IP变化（可选安全检查）
        if client_ip and getattr(session, 'ip_address', None):
            session_ip = str(getattr(session, 'ip_address', ''))
            if session_ip and session_ip != client_ip:
                # IP地址发生变化，记录警告
                print(f"警告：用户 {getattr(user, 'username', 'unknown')} 的IP地址发生变化：{session_ip} -> {client_ip}")

        # 更新最后访问时间
        session.last_accessed_at = datetime.now()
        # 更新IP地址和User-Agent（如果提供）
        if client_ip:
            setattr(session, 'ip_address', client_ip)
        if user_agent:
            setattr(session, 'user_agent', user_agent)
        self.db.commit()

        return session

    def _is_token_revoked(self, jti: str) -> bool:
        """检查令牌是否已被撤销"""
        from ...core.token_blacklist import blacklist_manager

        return blacklist_manager.is_blacklisted(jti)

    def revoke_session(self, refresh_token: str) -> bool:
        """撤销会话 - 增强安全性"""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.refresh_token == refresh_token)
            .first()
        )

        if session:
            session.is_active = False

            # 将令牌添加到黑名单
            try:
                from jose import jwt

                payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                jti = payload.get("jti")
                exp = payload.get("exp")

                if jti and exp:
                    from ...core.token_blacklist import blacklist_manager

                    blacklist_manager.add_token(jti, exp)

            except Exception as e:
                # 记录错误但不影响撤销操作
                print(f"添加令牌到黑名单失败: {e}")

            self.db.commit()
            return True

        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """撤销用户的所有会话"""
        count = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active)
            .update({"is_active": False})
        )

        self.db.commit()
        return count

    def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        """修改密码"""
        # 验证当前密码
        if not self.verify_password(current_password, user.password_hash):
            raise BusinessLogicError("当前密码不正确")

        # 验证新密码强度
        if not self.validate_password_strength(new_password):
            raise BusinessLogicError("新密码不符合安全要求")

        # 检查新密码是否与历史记录中的密码相同
        if self.is_password_in_history(user, new_password):
            raise BusinessLogicError("新密码不能与最近使用过的密码相同")

        # 更新密码
        new_password_hash = self.get_password_hash(new_password)
        user.password_hash = new_password_hash

        # 将新密码添加到历史记录
        self.add_password_to_history(user, new_password_hash)

        self.db.commit()

        # 撤销所有会话，强制重新登录
        self.revoke_all_user_sessions(user.id)

        return True

    def get_user_by_id(self, user_id: str) -> User | None:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()

    def update_user(self, user_id: str, user_data: UserUpdate) -> User | None:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # 检查邮箱和用户名唯一性
        if user_data.email and user_data.email != user.email:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise BusinessLogicError("邮箱已被其他用户使用")

        if user_data.username and user_data.username != user.username:
            existing_user = self.get_user_by_username(user_data.username)
            if existing_user:
                raise BusinessLogicError("用户名已被其他用户使用")

        # 更新字段
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)

        return user

    def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.now()

        # 撤销所有会话
        self.revoke_all_user_sessions(user_id)

        self.db.commit()
        return True

    def activate_user(self, user_id: str) -> bool:
        """激活用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        self.db.commit()
        return True

    def get_user_sessions(self, user_id: str) -> list[UserSessionResponse]:
        """获取用户会话列表"""
        sessions = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
            .all()
        )

        return [UserSessionResponse.from_orm(session) for session in sessions]

    def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> AuditLog:
        """创建审计日志"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        audit_log = AuditLog(
            user_id=user_id,
            username=user.username,
            user_role=user.role.value if hasattr(user.role, "value") else user.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            api_endpoint=api_endpoint,
            http_method=http_method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_message=response_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def unlock_user(self, user_id: str) -> bool:
        """解锁用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        self.db.commit()
        return True


# 定期清理过期任务的后台任务
# 注意：这些函数尚未实现，需要task_store支持
# import asyncio
# from contextlib import asynccontextmanager
#
#
#
# async def cleanup_expired_tasks():
#     """定期清理过期任务"""
#     while True:
#         try:
#             task_store.cleanup_expired()
#             await asyncio.sleep(300)  # 5分钟清理一次
#         except Exception as e:
#             print(f"清理过期任务时出错: {e}")
#             await asyncio.sleep(60)  # 出错时等1分钟再重试
#
#
#
# 注意：这些函数是示例代码，实际使用时需要在应用启动时正确配置
# import asyncio
# from contextlib import asynccontextmanager
#
#
# async def cleanup_expired_sessions():
#     """定期清理过期会话"""
#     from ..database import SessionLocal
#
#     while True:
#         try:
#             # 创建数据库会话
#             db = SessionLocal()
#             try:
#                 # 获取所有过期且活跃的会话
#                 expired_sessions = (
#                     db.query(UserSession)
#                     .filter(
#                         UserSession.is_active,
#                         UserSession.expires_at < datetime.now(),
#                     )
#                     .all()
#                 )
#
#                 # 撤销过期会话
#                 for session in expired_sessions:
#                     session.is_active = False
#
#                 if expired_sessions:
#                     db.commit()
#                     print(f"清理了 {len(expired_sessions)} 个过期会话")
#             finally:
#                 db.close()
#
#             await asyncio.sleep(3600)  # 1小时清理一次
#         except Exception as e:
#             print(f"清理过期会话时出错: {e}")
#             await asyncio.sleep(300)  # 出错时等5分钟再重试
#
#
# @asynccontextmanager
# async def lifespan(app):
#     """应用生命周期管理"""
#     # 启动时
#     print("🚀 启动土地物业资产管理系统（简化版）")
#     print(f"📊 数据库: {settings.DATABASE_URL}")
#     print(f"🔧 调试模式: {settings.DEBUG}")
#
#     # 启动后台清理任务
#     # cleanup_task = asyncio.create_task(cleanup_expired_tasks())
#     # cleanup_sessions_task = asyncio.create_task(cleanup_expired_sessions())
#
#     yield
#
#     # 关闭时
#     # cleanup_task.cancel()
#     # cleanup_sessions_task.cancel()
#     print("🛑 系统已关闭")
