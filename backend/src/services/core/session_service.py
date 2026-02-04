import json
import logging
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ...core.config import settings
from ...models.auth import UserSession
from ...security.token_blacklist import blacklist_manager

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = getattr(settings, "ALGORITHM", "HS256")

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""

    def __init__(self, db: Session):
        self.db = db

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
            .filter(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .all()
        )

        # 限制并发会话数量
        if (
            len(existing_sessions) >= settings.MAX_CONCURRENT_SESSIONS
        ):  # pragma: no cover
            # 取消最旧的会话
            oldest_session = min(
                existing_sessions,
                key=lambda x: x.created_at,
            )  # pragma: no cover
            oldest_session.is_active = False  # pragma: no cover

        # 提取设备信息
        device_id = None
        platform = None
        if device_info:
            # 如果device_info是字符串，尝试解析为JSON
            try:
                if isinstance(device_info, str):
                    device_data = json.loads(device_info)
                else:
                    device_data = device_info
                device_id = device_data.get("device_id")
                platform = device_data.get("platform")
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                # 如果解析失败，将整个device_info作为device_info字段存储
                pass  # pragma: no cover

        user_session = UserSession()
        user_session.user_id = user_id
        user_session.refresh_token = refresh_token
        user_session.session_id = session_id
        user_session.device_info = (
            device_info
            if not isinstance(device_info, dict)
            else json.dumps(device_info)
        )
        user_session.device_id = device_id
        user_session.platform = platform
        user_session.ip_address = ip_address
        user_session.user_agent = user_agent
        user_session.expires_at = datetime.now(UTC) + timedelta(
            days=settings.SESSION_EXPIRE_DAYS
        )

        self.db.add(user_session)
        self.db.commit()
        self.db.refresh(user_session)

        return user_session

    def get_user_sessions(self, user_id: str) -> list[UserSession]:
        """获取用户会话列表"""
        return (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
            .all()
        )

    def revoke_session(self, refresh_token: str) -> bool:
        """撤销会话"""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.refresh_token == refresh_token)
            .first()
        )

        if session:
            session.is_active = False

            # 将令牌添加到黑名单
            try:
                payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                jti = payload.get("jti")  # pragma: no cover
                exp = payload.get("exp")  # pragma: no cover

                if jti and exp:  # pragma: no cover
                    blacklist_manager.add_token(jti, exp)  # pragma: no cover

            except Exception as e:  # pragma: no cover
                # 记录错误但不影响撤销操作
                logger.warning(f"添加令牌到黑名单失败: {e}")  # pragma: no cover

            self.db.commit()
            return True

        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """撤销用户的所有会话"""
        count = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .update({"is_active": False})
        )

        # 用户级撤销：确保访问令牌也失效
        try:
            blacklist_manager.revoke_all_user_tokens(user_id)
        except Exception as e:
            logger.warning(f"Failed to revoke user tokens for {user_id}: {e}")

        self.db.commit()
        return count


class AsyncSessionService:
    """会话管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user_session(
        self,
        user_id: str,
        refresh_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> UserSession:
        existing_stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.is_active.is_(True)
        )
        existing_sessions = list((await self.db.execute(existing_stmt)).scalars().all())

        if len(existing_sessions) >= settings.MAX_CONCURRENT_SESSIONS:  # pragma: no cover
            oldest_session = min(
                existing_sessions,
                key=lambda x: x.created_at,
            )  # pragma: no cover
            oldest_session.is_active = False  # pragma: no cover

        device_id = None
        platform = None
        if device_info:
            try:
                if isinstance(device_info, str):
                    device_data = json.loads(device_info)
                else:
                    device_data = device_info
                device_id = device_data.get("device_id")
                platform = device_data.get("platform")
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                pass  # pragma: no cover

        user_session = UserSession()
        user_session.user_id = user_id
        user_session.refresh_token = refresh_token
        user_session.session_id = session_id
        user_session.device_info = (
            device_info
            if not isinstance(device_info, dict)
            else json.dumps(device_info)
        )
        user_session.device_id = device_id
        user_session.platform = platform
        user_session.ip_address = ip_address
        user_session.user_agent = user_agent
        user_session.expires_at = datetime.now(UTC) + timedelta(
            days=settings.SESSION_EXPIRE_DAYS
        )

        self.db.add(user_session)
        await self.db.commit()
        await self.db.refresh(user_session)
        return user_session

    async def get_user_sessions(self, user_id: str) -> list[UserSession]:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_session(self, refresh_token: str) -> bool:
        stmt = select(UserSession).where(UserSession.refresh_token == refresh_token)
        session = (await self.db.execute(stmt)).scalars().first()

        if session:
            session.is_active = False

            try:
                payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                jti = payload.get("jti")  # pragma: no cover
                exp = payload.get("exp")  # pragma: no cover

                if jti and exp:  # pragma: no cover
                    blacklist_manager.add_token(jti, exp)  # pragma: no cover

            except Exception as e:  # pragma: no cover
                logger.warning(f"添加令牌到黑名单失败: {e}")  # pragma: no cover

            await self.db.commit()
            return True

        return False

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        result = await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .values({"is_active": False})
        )

        try:
            blacklist_manager.revoke_all_user_tokens(user_id)
        except Exception as e:
            logger.warning(f"Failed to revoke user tokens for {user_id}: {e}")

        await self.db.commit()
        return int(result.rowcount or 0)
