"""
认证相关CRUD操作
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from ..models.auth import AuditLog, User, UserRole, UserSession
from ..schemas.auth import UserCreate, UserUpdate


class UserCRUD:
    """用户CRUD操作"""

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

    def get_multi_with_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[User], int]:
        """带筛选条件的用户列表"""
        query = db.query(User)

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

        # 总数
        total = query.count()

        # 分页
        users = query.offset(skip).limit(limit).all()

        return users, total

    def create(self, db: Session, obj_in: UserCreate) -> User:
        """创建用户"""
        from ..services.auth_service import AuthService

        auth_service = AuthService(db)
        return auth_service.create_user(obj_in)

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        """更新用户"""
        from ..services.auth_service import AuthService

        auth_service = AuthService(db)
        return auth_service.update_user(db_obj.id, obj_in)

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
        return db.query(func.count(User.id)).scalar()

    def count_active(self, db: Session) -> int:
        """活跃用户总数"""
        return db.query(func.count(User.id)).filter(User.is_active).scalar()

    def count_by_role(self, db: Session, role: UserRole) -> int:
        """按角色统计用户数"""
        return db.query(func.count(User.id)).filter(User.role == role).scalar()

    def get_recent_logins(self, db: Session, limit: int = 10) -> list[User]:
        """获取最近登录的用户"""
        return (
            db.query(User)
            .filter(User.last_login_at.isnot(None))
            .order_by(desc(User.last_login_at))
            .limit(limit)
            .all()
        )


class UserSessionCRUD:
    """用户会话CRUD操作"""

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
        user_session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(days=7),  # 7天过期
        )
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
        count = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active)
            .update({"is_active": False})
        )
        db.commit()
        return count

    def cleanup_expired_sessions(self, db: Session) -> int:
        """清理过期会话"""
        count = (
            db.query(UserSession)
            .filter(
                UserSession.expires_at < datetime.now(), UserSession.is_active
            )
            .update({"is_active": False})
        )
        db.commit()
        return count

    def count_active_sessions(self, db: Session) -> int:
        """活跃会话总数"""
        return (
            db.query(func.count(UserSession.id))
            .filter(UserSession.is_active)
            .scalar()
        )


class AuditLogCRUD:
    """审计日志CRUD操作"""

    def get(self, db: Session, log_id: str) -> AuditLog | None:
        """根据ID获取审计日志"""
        return db.query(AuditLog).filter(AuditLog.id == log_id).first()

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
        query = db.query(AuditLog)

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
    details: str | None = None,
    ) -> AuditLog:
        """创建审计日志"""
        from ..services.auth_service import AuthService

        auth_service = AuthService(db)
        return auth_service.create_audit_log(
            user_id=user_id,
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

    def count(self, db: Session) -> int:
        """审计日志总数"""
        return db.query(func.count(AuditLog.id)).scalar()

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

    def get_login_statistics(self, db: Session, days: int = 30) -> dict:
        """获取登录统计"""
        from datetime import datetime, timedelta

        start_date = datetime.now() - timedelta(days=days)

        # 总登录次数
        total_logins = (
            db.query(func.count(AuditLog.id))
            .filter(
                and_(AuditLog.action == "user_login", AuditLog.created_at >= start_date)
            )
            .scalar()
        )

        # 成功登录次数
        successful_logins = (
            db.query(func.count(AuditLog.id))
            .filter(
                and_(
                    AuditLog.action == "user_login",
                    AuditLog.response_status == 200,
                    AuditLog.created_at >= start_date,
                )
            )
            .scalar()
        )

        # 失败登录次数
        failed_logins = total_logins - successful_logins

        return {
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round(successful_logins / total_logins * 100, 2)
            if total_logins > 0
            else 0,
        }
