from typing import Any, cast

"""
认证相关CRUD操作

注意: CRUD层只负责数据库操作，不应依赖Service层。
如需业务逻辑（如密码验证、用户校验等），请使用Service层。
"""

from datetime import datetime, timedelta

import bcrypt
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from ..constants.validation_constants import AuthFields
from ..models.auth import AuditLog, User, UserRole, UserSession
from ..schemas.auth import UserCreate, UserUpdate


class UserCRUD:
    """用户CRUD操作"""

    def _count_query(self, db: Session) -> Any:
        return db.query(User)

    def get(self, db: Session, user_id: str) -> User | None:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, db: Session, username: str) -> User | None:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """获取用户列表"""
        return db.query(User).offset(skip).limit(limit).all()

    def get_username_map(self, db: Session, user_ids: set[str]) -> dict[str, str]:
        """批量获取用户ID到用户名映射"""
        user_id_list = list(user_ids)
        if not user_id_list:
            return {}
        rows = db.query(User.id, User.username).filter(User.id.in_(user_id_list)).all()
        return {str(user_id): username for user_id, username in rows}

    def get_multi_with_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role: UserRole | str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[User], int]:
        """带筛选条件的用户列表"""
        query = self._apply_user_filters(
            db.query(User),
            search=search,
            role=role,
            is_active=is_active,
            organization_id=organization_id,
        )

        # 总数
        total = query.count()

        # 分页
        users = query.offset(skip).limit(limit).all()

        return users, total

    def _apply_user_filters(
        self,
        query: Any,
        *,
        search: str | None = None,
        role: UserRole | str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> Any:
        # 搜索条件
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # 角色筛选
        if role is not None:
            query = query.filter(User.role == role)

        # 状态筛选
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # 组织筛选
        if organization_id is not None:
            query = query.filter(
                or_(
                    User.default_organization_id == organization_id,
                    # Employee功能暂时注释掉，等待模型定义
                    # User.employee_id.in_(
                    #     db.query(Employee.id)
                    #     .filter(Employee.organization_id == organization_id)
                    #     .subquery()
                    # ),
                )
            )

        return query

    def create(self, db: Session, obj_in: UserCreate) -> User:
        """
        创建用户 (纯CRUD操作)

        注意: 此方法仅执行数据库操作。
        如需完整的用户创建逻辑（包括密码验证、重复检查等），
        请使用 UserManagementService.create_user()
        """
        # 密码哈希
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(obj_in.password.encode("utf-8"), salt).decode(
            "utf-8"
        )

        role_value = obj_in.role.value if hasattr(obj_in.role, "value") else obj_in.role

        db_user = User()
        db_user.username = obj_in.username
        db_user.email = obj_in.email
        db_user.full_name = obj_in.full_name
        db_user.password_hash = hashed_password
        db_user.role = role_value
        db_user.employee_id = obj_in.employee_id
        db_user.default_organization_id = obj_in.default_organization_id

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        """
        更新用户 (纯CRUD操作)

        注意: 此方法仅执行数据库操作。
        如需完整的用户更新逻辑（包括唯一性检查等），
        请使用 UserManagementService.update_user()
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "role" and value is not None:
                value = value.value if hasattr(value, "value") else value
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, user_id: str) -> bool:
        """删除用户（软删除）"""
        user = self.get(db, user_id)
        if not user:
            return False

        # 软删除
        user.is_active = False
        db.commit()
        return True

    def count(self, db: Session) -> int:
        """用户总数"""
        result = self._count_query(db).with_entities(func.count(User.id)).scalar()
        return int(result) if result is not None else 0

    def count_active(self, db: Session) -> int:
        """活跃用户总数"""
        result = (
            self._count_query(db)
            .filter(User.is_active.is_(True))
            .with_entities(func.count(User.id))
            .scalar()
        )
        return int(result) if result is not None else 0

    def count_by_role(self, db: Session, role: UserRole) -> int:
        """按角色统计用户数"""
        result = (
            self._count_query(db)
            .filter(User.role == role)
            .with_entities(func.count(User.id))
            .scalar()
        )
        return int(result) if result is not None else 0

    def get_recent_logins(self, db: Session, limit: int = 10) -> list[User]:
        """获取最近登录的用户"""
        return (
            db.query(User)
            .filter(User.last_login_at.isnot(None))
            .order_by(desc(User.last_login_at))
            .limit(limit)
            .all()
        )

    def get_users_by_role(
        self, db: Session, role_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[User], int]:
        """根据角色ID获取用户列表"""
        # Note: This implementation assumes role_id is a UserRole enum value
        # If you need role-based filtering by Role model ID, this needs adjustment
        query = self._apply_user_filters(db.query(User), role=role_id)
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        return users, total


class UserSessionCRUD:
    """用户会话CRUD操作"""

    def _session_query(self, db: Session) -> Any:
        return db.query(UserSession)

    def get(self, db: Session, session_id: str) -> UserSession | None:
        """根据ID获取会话"""
        return db.query(UserSession).filter(UserSession.id == session_id).first()

    def get_by_refresh_token(
        self, db: Session, refresh_token: str
    ) -> UserSession | None:
        """根据刷新令牌获取会话"""
        return (
            db.query(UserSession)
            .filter(UserSession.refresh_token == refresh_token)
            .first()
        )

    def get_user_sessions(
        self, db: Session, user_id: str, active_only: bool = True
    ) -> list[UserSession]:
        """获取用户的所有会话"""
        query = db.query(UserSession).filter(UserSession.user_id == user_id)
        if active_only:
            query = query.filter(UserSession.is_active)
        return query.order_by(desc(UserSession.created_at)).all()

    def create(
        self,
        db: Session,
        user_id: str,
        refresh_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        """创建用户会话"""
        user_session = UserSession()
        user_session.user_id = user_id
        user_session.refresh_token = refresh_token
        user_session.device_info = device_info
        user_session.ip_address = ip_address
        user_session.user_agent = user_agent
        user_session.expires_at = datetime.now() + timedelta(days=7)
        db.add(user_session)
        db.commit()
        db.refresh(user_session)
        return user_session

    def deactivate(self, db: Session, session_id: str) -> bool:
        """停用会话"""
        session = self.get(db, session_id)
        if not session:
            return False

        session.is_active = False
        db.commit()
        return True

    def deactivate_by_user(self, db: Session, user_id: str) -> int:
        """停用用户的所有会话"""
        count = int(
            self._session_query(db)
            .filter(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .update({AuthFields.IS_ACTIVE: False})
        )
        db.commit()
        return count

    def cleanup_expired_sessions(self, db: Session) -> int:
        """清理过期会话"""
        count = int(
            self._session_query(db)
            .filter(
                UserSession.expires_at < datetime.now(),
                UserSession.is_active.is_(True),
            )
            .update({AuthFields.IS_ACTIVE: False})
        )
        db.commit()
        return count

    def count_active_sessions(self, db: Session) -> int:
        """活跃会话总数"""
        result = (
            self._session_query(db)
            .filter(UserSession.is_active.is_(True))
            .with_entities(func.count(UserSession.id))
            .scalar()
        )
        return int(result) if result is not None else 0


class AuditLogCRUD:
    """审计日志CRUD操作"""

    def _audit_query(self, db: Session) -> Any:
        return db.query(AuditLog)

    def _apply_audit_filters(
        self,
        query: Any,
        *,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Any:
        # 筛选条件
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query

    def get(self, db: Session, log_id: str) -> AuditLog | None:
        """根据ID获取审计日志"""
        return cast(
            AuditLog | None,
            self._audit_query(db).filter(AuditLog.id == log_id).first(),
        )

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        """获取审计日志列表"""
        query = self._apply_audit_filters(
            self._audit_query(db),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
        )

        # 总数
        total = query.count()

        # 分页
        logs = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

        return logs, total

    def create(
        self,
        db: Session,
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
        """
        创建审计日志 (纯CRUD操作)

        注意: 此方法仅执行数据库操作。
        如需完整的审计日志逻辑，请使用 AuditService.create_audit_log()
        """
        # 获取用户信息以记录用户名和角色
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        audit_log = AuditLog()
        audit_log.user_id = user_id
        audit_log.username = user.username
        audit_log.user_role = (
            user.role.value if hasattr(user.role, "value") else user.role
        )
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
        db.commit()
        db.refresh(audit_log)
        return audit_log

    def count(self, db: Session) -> int:
        """审计日志总数"""
        result = self._audit_query(db).with_entities(func.count(AuditLog.id)).scalar()
        return int(result) if result is not None else 0

    def get_user_actions(self, db: Session, user_id: str, days: int = 30) -> list[str]:
        """获取用户最近操作"""
        from datetime import datetime, timedelta

        start_date = datetime.now() - timedelta(days=days)

        actions = (
            db.query(AuditLog.action)
            .filter(AuditLog.user_id == user_id, AuditLog.created_at >= start_date)
            .distinct()
            .all()
        )

        return [action[0] for action in actions]

    def get_login_statistics(self, db: Session, days: int = 7) -> dict[str, Any]:
        """获取登录统计"""
        from datetime import datetime, timedelta

        start_date = datetime.now() - timedelta(days=days)

        total_logins = (
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
            )
            .scalar()
        )
        successful_logins = (
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
                AuditLog.response_status == 200,
            )
            .scalar()
        )

        total_logins = int(total_logins or 0)
        successful_logins = int(successful_logins or 0)

        # 失败登录次数
        failed_logins = max(total_logins - successful_logins, 0)

        return {
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round(successful_logins / total_logins * 100, 2)
            if total_logins > 0
            else 0,
        }
