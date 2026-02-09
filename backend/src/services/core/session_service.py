import json
import logging
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...models.auth import UserSession
from ...security.token_blacklist import blacklist_manager

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = getattr(settings, "ALGORITHM", "HS256")

logger = logging.getLogger(__name__)


def _naive_utc_now() -> datetime:
    """Return a naive UTC datetime for storage in TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(UTC).replace(tzinfo=None)


class AsyncSessionService:
    """会话管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user_session(
        self,
        user_id: str,
        refresh_token: str,
        device_info: str | dict[str, str] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> UserSession:
        existing_stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.is_active.is_(True)
        )
        existing_sessions = list((await self.db.execute(existing_stmt)).scalars().all())

        if (
            len(existing_sessions) >= settings.MAX_CONCURRENT_SESSIONS
        ):  # pragma: no cover
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
        user_session.is_active = True
        now = _naive_utc_now()
        user_session.created_at = now
        user_session.last_accessed_at = now
        user_session.expires_at = now + timedelta(days=settings.SESSION_EXPIRE_DAYS)

        self.db.add(user_session)
        await self.db.commit()
        await self.db.refresh(user_session)
        return user_session

    async def get_user_sessions(
        self, user_id: str, active_only: bool = True
    ) -> list[UserSession]:
        stmt = select(UserSession).where(UserSession.user_id == user_id)
        if active_only:
            stmt = stmt.where(UserSession.is_active.is_(True))
        stmt = stmt.order_by(UserSession.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_session_by_id(self, session_id: str) -> UserSession | None:
        """根据会话 ID 获取会话。"""
        stmt = select(UserSession).where(UserSession.id == session_id)
        return (await self.db.execute(stmt)).scalars().first()

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
