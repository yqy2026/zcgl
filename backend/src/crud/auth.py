"""
认证相关CRUD操作

注意: CRUD层只负责数据库操作，不应依赖Service层。
如需业务逻辑（如密码验证、用户校验等），请使用Service层。
"""

import re
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.validation_constants import AuthFields
from ..models.auth import AuditLog, User, UserSession
from ..models.rbac import Role, UserRoleAssignment
from ..schemas.auth import UserCreate, UserUpdate


class UserCRUD:
    """用户CRUD操作（异步）"""

    @staticmethod
    def _normalize_phone_identifier(identifier: str) -> str | None:
        candidate = identifier.strip()
        if candidate == "":
            return None

        # Accept common phone formatting used by external systems.
        digits = re.sub(r"[\s\-\(\)]", "", candidate)
        if digits.startswith("+"):
            digits = digits[1:]
        if digits.startswith("86") and len(digits) == 13:
            digits = digits[2:]

        if re.fullmatch(r"1[3-9]\d{9}", digits):
            return digits
        return None

    def _apply_user_filters_stmt(
        self,
        stmt: Any,
        *,
        search: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> Any:
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)

        if role_id is not None:
            stmt = stmt.join(
                UserRoleAssignment,
                UserRoleAssignment.user_id == User.id,
            ).where(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        if organization_id is not None:
            stmt = stmt.where(User.default_organization_id == organization_id)

        return stmt

    async def get_async(self, db: AsyncSession, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_username_async(
        self, db: AsyncSession, username: str
    ) -> User | None:
        stmt = select(User).where(User.username == username)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_email_async(self, db: AsyncSession, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_async(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_username_map_async(
        self, db: AsyncSession, user_ids: set[str]
    ) -> dict[str, str]:
        user_id_list = list(user_ids)
        if not user_id_list:
            return {}
        stmt = select(User.id, User.username).where(User.id.in_(user_id_list))
        rows = (await db.execute(stmt)).all()
        return {str(user_id): username for user_id, username in rows}

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        stmt = self._apply_user_filters_stmt(
            stmt,
            search=search,
            role_id=role_id,
            is_active=is_active,
            organization_id=organization_id,
        )
        count_stmt = select(func.count(func.distinct(User.id))).select_from(User)
        count_stmt = self._apply_user_filters_stmt(
            count_stmt,
            search=search,
            role_id=role_id,
            is_active=is_active,
            organization_id=organization_id,
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)
        result = await db.execute(stmt.distinct(User.id).offset(skip).limit(limit))
        users = list(result.scalars().all())
        return users, total

    async def create_async(self, db: AsyncSession, obj_in: UserCreate) -> User:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(obj_in.password.encode("utf-8"), salt).decode(
            "utf-8"
        )

        db_user = User()
        db_user.username = obj_in.username
        db_user.email = obj_in.email
        db_user.phone = obj_in.phone
        db_user.full_name = obj_in.full_name
        db_user.password_hash = hashed_password
        db_user.default_organization_id = obj_in.default_organization_id

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def update_async(
        self, db: AsyncSession, db_obj: User, obj_in: UserUpdate
    ) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "role_id":
                continue
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now()
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_async(self, db: AsyncSession, user_id: str) -> bool:
        user = await self.get_async(db, user_id)
        if not user:
            return False

        user.is_active = False
        await db.commit()
        return True

    async def count_async(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count(User.id)))
        return int(result.scalar() or 0)

    async def count_active_async(self, db: AsyncSession) -> int:
        stmt = select(func.count(User.id)).where(User.is_active.is_(True))
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_locked_async(self, db: AsyncSession) -> int:
        stmt = select(func.count(User.id)).where(User.is_locked.is_(True))
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_inactive_async(self, db: AsyncSession) -> int:
        stmt = select(func.count(User.id)).where(User.is_active.is_(False))
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_user_statistics_async(self, db: AsyncSession) -> dict[str, int]:
        """获取用户统计数据（total/active/locked/inactive）"""
        total = await self.count_async(db)
        active = await self.count_active_async(db)
        locked = await self.count_locked_async(db)
        inactive = await self.count_inactive_async(db)
        return {
            "total_users": total,
            "active_users": active,
            "locked_users": locked,
            "inactive_users": inactive,
        }

    async def find_by_username_or_email_async(
        self, db: AsyncSession, username: str, email: str
    ) -> User | None:
        """查找用户名或邮箱匹配的用户（用于唯一性校验）"""
        stmt = select(User).where(or_(User.username == username, User.email == email))
        return (await db.execute(stmt)).scalars().first()

    async def _find_by_identifier_async(
        self, db: AsyncSession, identifier: str, *, active_only: bool
    ) -> User | None:
        normalized_identifier = identifier.strip()
        if normalized_identifier == "":
            return None

        username_conditions: list[Any] = [User.username == normalized_identifier]
        if active_only:
            username_conditions.append(User.is_active.is_(True))

        # 优先按用户名精确匹配，避免 username 与其他用户手机号重叠时误命中。
        username_stmt = select(User).where(*username_conditions)
        user = (await db.execute(username_stmt)).scalars().first()
        if user is not None:
            return user

        normalized_phone = self._normalize_phone_identifier(normalized_identifier)
        if normalized_phone is None:
            return None

        phone_conditions: list[Any] = [User.phone == normalized_phone]
        if active_only:
            phone_conditions.append(User.is_active.is_(True))

        phone_stmt = select(User).where(*phone_conditions)
        user = (await db.execute(phone_stmt)).scalars().first()
        if user is not None:
            return user

        return None

    async def find_by_identifier_async(
        self, db: AsyncSession, identifier: str
    ) -> User | None:
        """通过用户名或手机号查找用户（不区分启用状态，用于审计等场景）。"""
        return await self._find_by_identifier_async(db, identifier, active_only=False)

    async def find_active_by_identifier_async(
        self, db: AsyncSession, identifier: str
    ) -> User | None:
        """通过用户名或手机号查找活跃用户（用于登录认证）。"""
        return await self._find_by_identifier_async(db, identifier, active_only=True)

    async def find_active_by_login_async(
        self, db: AsyncSession, login: str
    ) -> User | None:
        """兼容旧接口，等价于 find_active_by_identifier_async。"""
        return await self.find_active_by_identifier_async(db, login)

    async def get_recent_logins_async(
        self, db: AsyncSession, limit: int = 10
    ) -> list[User]:
        stmt = (
            select(User)
            .where(User.last_login_at.isnot(None))
            .order_by(desc(User.last_login_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_users_by_role(
        self, db: AsyncSession, role_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[User], int]:
        """根据角色ID获取用户列表"""
        stmt = (
            select(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active.is_(True),
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )
            .distinct(User.id)
            .offset(skip)
            .limit(limit)
        )
        count_stmt = (
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active.is_(True),
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )
        )

        users = list((await db.execute(stmt)).scalars().all())
        total = int((await db.execute(count_stmt)).scalar() or 0)
        return users, total


class UserSessionCRUD:
    """用户会话CRUD操作（异步）"""

    async def get_async(self, db: AsyncSession, session_id: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.id == session_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_refresh_token_async(
        self, db: AsyncSession, refresh_token: str
    ) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.refresh_token == refresh_token)
        return (await db.execute(stmt)).scalars().first()

    async def get_active_by_refresh_token_async(
        self, db: AsyncSession, refresh_token: str
    ) -> UserSession | None:
        """按 refresh_token 查找活跃会话（用于令牌刷新验证）"""
        stmt = select(UserSession).where(
            UserSession.refresh_token == refresh_token,
            UserSession.is_active.is_(True),
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_active_sessions_by_user_async(
        self, db: AsyncSession, user_id: str
    ) -> list[UserSession]:
        """获取用户所有活跃会话（用于并发会话控制）"""
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active.is_(True),
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_user_sessions_async(
        self, db: AsyncSession, user_id: str, active_only: bool = True
    ) -> list[UserSession]:
        stmt = select(UserSession).where(UserSession.user_id == user_id)
        if active_only:
            stmt = stmt.where(UserSession.is_active)
        result = await db.execute(stmt.order_by(desc(UserSession.created_at)))
        return list(result.scalars().all())

    async def create_async(
        self,
        db: AsyncSession,
        user_id: str,
        refresh_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        user_session = UserSession()
        user_session.user_id = user_id
        user_session.refresh_token = refresh_token
        user_session.device_info = device_info
        user_session.ip_address = ip_address
        user_session.user_agent = user_agent
        user_session.expires_at = datetime.now() + timedelta(days=7)
        db.add(user_session)
        await db.commit()
        await db.refresh(user_session)
        return user_session

    async def deactivate_async(self, db: AsyncSession, session_id: str) -> bool:
        session = await self.get_async(db, session_id)
        if not session:
            return False

        session.is_active = False
        await db.commit()
        return True

    async def deactivate_by_user_async(self, db: AsyncSession, user_id: str) -> int:
        count = await self.deactivate_by_user_no_commit_async(db, user_id)
        await db.commit()
        return count

    async def deactivate_by_user_no_commit_async(
        self, db: AsyncSession, user_id: str
    ) -> int:
        result = await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .values({AuthFields.IS_ACTIVE: False})
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def cleanup_expired_sessions_async(self, db: AsyncSession) -> int:
        result = await db.execute(
            update(UserSession)
            .where(
                UserSession.expires_at < datetime.now(),
                UserSession.is_active.is_(True),
            )
            .values({AuthFields.IS_ACTIVE: False})
        )
        await db.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    async def count_active_sessions_async(self, db: AsyncSession) -> int:
        stmt = select(func.count(UserSession.id)).where(UserSession.is_active.is_(True))
        result = await db.execute(stmt)
        return int(result.scalar() or 0)


class AuditLogCRUD:
    """审计日志CRUD操作（异步）"""

    def _apply_audit_filters_stmt(
        self,
        stmt: Any,
        *,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Any:
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)
        return stmt

    async def get_async(self, db: AsyncSession, log_id: str) -> AuditLog | None:
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_async(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        stmt = self._apply_audit_filters_stmt(
            stmt,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
        )

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await db.execute(total_stmt)).scalar() or 0)
        result = await db.execute(
            stmt.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        )
        logs = list(result.scalars().all())
        return logs, total

    async def create_async(
        self,
        db: AsyncSession,
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
    ) -> AuditLog | None:
        user_stmt = select(User).where(User.id == user_id)
        user = (await db.execute(user_stmt)).scalars().first()
        if not user:
            return None

        audit_log = AuditLog()
        audit_log.user_id = user_id
        audit_log.username = user.username
        role_stmt = (
            select(Role.display_name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )
            .order_by(Role.level.asc())
            .limit(1)
        )
        audit_log.user_role = (await db.execute(role_stmt)).scalar()
        audit_log.action = action
        audit_log.resource_type = resource_type
        audit_log.resource_id = resource_id
        audit_log.resource_name = resource_name
        audit_log.api_endpoint = api_endpoint
        audit_log.http_method = http_method
        audit_log.request_params = request_params
        audit_log.request_body = request_body
        audit_log.response_status = response_status
        audit_log.response_message = response_message
        audit_log.ip_address = ip_address
        audit_log.user_agent = user_agent
        audit_log.session_id = session_id

        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        return audit_log

    async def count_async(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count(AuditLog.id)))
        return int(result.scalar() or 0)

    async def get_user_actions_async(
        self, db: AsyncSession, user_id: str, days: int = 30
    ) -> list[str]:
        start_date = datetime.now() - timedelta(days=days)
        stmt = (
            select(AuditLog.action)
            .where(AuditLog.user_id == user_id, AuditLog.created_at >= start_date)
            .distinct()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_login_statistics_async(
        self, db: AsyncSession, days: int = 7
    ) -> dict[str, Any]:
        start_date = datetime.now() - timedelta(days=days)
        total_stmt = (
            select(func.count(AuditLog.id))
            .where(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
            )
            .select_from(AuditLog)
        )
        success_stmt = (
            select(func.count(AuditLog.id))
            .where(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
                AuditLog.response_status == 200,
            )
            .select_from(AuditLog)
        )
        total_logins = int((await db.execute(total_stmt)).scalar() or 0)
        successful_logins = int((await db.execute(success_stmt)).scalar() or 0)
        failed_logins = max(total_logins - successful_logins, 0)

        return {
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round(successful_logins / total_logins * 100, 2)
            if total_logins > 0
            else 0,
        }
