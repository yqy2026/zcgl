"""
操作日志CRUD操作
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models.operation_log import OperationLog


class OperationLogCRUD:
    """操作日志CRUD操作"""

    def create(
        self,
        db: Session,
        user_id: str,
        action: str,
        module: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
        response_status: int | None = None,
        response_time: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        error_message: str | None = None,
        details: str | None = None,
        username: str | None = None,
        action_name: str | None = None,
        module_name: str | None = None,
    ) -> OperationLog:
        """创建操作日志"""
        log = OperationLog(
            user_id=user_id,
            username=username,
            action=action,
            action_name=action_name,
            module=module,
            module_name=module_name,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            request_method=request_method,
            request_url=request_url,
            response_status=response_status,
            response_time=response_time,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            details=details,
            created_at=datetime.now(),
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        return log

    def get(self, db: Session, log_id: str) -> OperationLog | None:
        """根据ID获取操作日志"""
        return db.query(OperationLog).filter(OperationLog.id == log_id).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[OperationLog], int]:
        """获取操作日志列表"""
        query = db.query(OperationLog)

        # 用户筛选
        if user_id:
            query = query.filter(OperationLog.user_id == user_id)

        # 操作类型筛选
        if action:
            query = query.filter(OperationLog.action == action)

        # 模块筛选
        if module:
            query = query.filter(OperationLog.module == module)

        # 资源类型筛选
        if resource_type:
            query = query.filter(OperationLog.resource_type == resource_type)

        # 日期范围筛选
        if start_date:
            query = query.filter(OperationLog.created_at >= start_date)
        if end_date:
            query = query.filter(OperationLog.created_at <= end_date)

        # 关键词搜索
        if search:
            search_filter = or_(
                OperationLog.username.ilike(f"%{search}%"),
                OperationLog.action_name.ilike(f"%{search}%"),
                OperationLog.resource_name.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # 总数
        total = query.count()

        # 分页和排序
        logs = (
            query.order_by(OperationLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return logs, total

    def delete_old_logs(self, db: Session, days: int = 90) -> int:
        """删除指定天数前的日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = (
            db.query(OperationLog)
            .filter(OperationLog.created_at < cutoff_date)
            .delete()
        )
        db.commit()
        return deleted

    def get_user_statistics(self, db: Session, user_id: str, days: int = 30) -> dict:
        """获取用户操作统计"""
        start_date = datetime.now() - timedelta(days=days)

        total_operations = (
            db.query(func.count(OperationLog.id))
            .filter(
                and_(
                    OperationLog.user_id == user_id,
                    OperationLog.created_at >= start_date,
                )
            )
            .scalar()
        )

        # 按操作类型统计
        action_stats = (
            db.query(OperationLog.action, func.count(OperationLog.id))
            .filter(
                and_(
                    OperationLog.user_id == user_id,
                    OperationLog.created_at >= start_date,
                )
            )
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "user_id": user_id,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {action: count for action, count in action_stats},
        }

    def get_module_statistics(self, db: Session, module: str, days: int = 30) -> dict:
        """获取模块操作统计"""
        start_date = datetime.now() - timedelta(days=days)

        total_operations = (
            db.query(func.count(OperationLog.id))
            .filter(
                and_(
                    OperationLog.module == module,
                    OperationLog.created_at >= start_date,
                )
            )
            .scalar()
        )

        # 按操作类型统计
        action_stats = (
            db.query(OperationLog.action, func.count(OperationLog.id))
            .filter(
                and_(
                    OperationLog.module == module,
                    OperationLog.created_at >= start_date,
                )
            )
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "module": module,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {action: count for action, count in action_stats},
        }

    def get_daily_statistics(self, db: Session, days: int = 30) -> dict:
        """获取每日操作统计"""
        start_date = datetime.now() - timedelta(days=days)

        daily_stats = (
            db.query(
                func.date(OperationLog.created_at),
                func.count(OperationLog.id),
            )
            .filter(OperationLog.created_at >= start_date)
            .group_by(func.date(OperationLog.created_at))
            .order_by(func.date(OperationLog.created_at))
            .all()
        )

        return {
            "days": days,
            "daily_breakdown": {str(date): count for date, count in daily_stats},
        }

    def get_error_statistics(self, db: Session, days: int = 30) -> dict:
        """获取错误操作统计"""
        start_date = datetime.now() - timedelta(days=days)

        total_errors = (
            db.query(func.count(OperationLog.id))
            .filter(
                and_(
                    OperationLog.error_message != None,
                    OperationLog.created_at >= start_date,
                )
            )
            .scalar()
        )

        # 按错误类型统计
        error_types = (
            db.query(
                OperationLog.action,
                func.count(OperationLog.id),
            )
            .filter(
                and_(
                    OperationLog.error_message != None,
                    OperationLog.created_at >= start_date,
                )
            )
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "days": days,
            "total_errors": total_errors,
            "error_breakdown": {action: count for action, count in error_types},
        }

    def count(self, db: Session) -> int:
        """日志总数"""
        return db.query(func.count(OperationLog.id)).scalar()
