"""
操作日志CRUD操作
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.operation_log import OperationLog


class OperationLogCRUD:
    """操作日志CRUD操作"""

    def _stats_start_date(self, days: int) -> datetime:
        return datetime.now() - timedelta(days=days)

    def _stats_query(
        self,
        db: Session,
        *,
        start_date: datetime,
        user_id: str | None = None,
        module: str | None = None,
        error_only: bool = False,
    ) -> Any:
        query = db.query(OperationLog).filter(OperationLog.created_at >= start_date)
        if user_id:
            query = query.filter(OperationLog.user_id == user_id)
        if module:
            query = query.filter(OperationLog.module == module)
        if error_only:
            query = query.filter(OperationLog.error_message.isnot(None))
        return query

    def _apply_filters(
        self,
        query: Any,
        *,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        response_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> Any:
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

        if response_status:
            if response_status == "success":
                query = query.filter(
                    OperationLog.response_status >= 200,
                    OperationLog.response_status < 300,
                )
            elif response_status == "warning":
                query = query.filter(
                    OperationLog.response_status >= 400,
                    OperationLog.response_status < 500,
                )
            elif response_status == "error":
                query = query.filter(OperationLog.response_status >= 500)
            elif response_status.isdigit():
                query = query.filter(
                    OperationLog.response_status == int(response_status)
                )

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

        return query

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
        request_params: str | None = None,
        request_body: str | None = None,
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
            request_params=request_params,
            request_body=request_body,
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
        response_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[OperationLog], int]:
        """获取操作日志列表"""
        query = self._apply_filters(
            db.query(OperationLog),
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            response_status=response_status,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )

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

    def get_multi_with_count(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        response_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[OperationLog], int]:
        """获取操作日志列表与总数"""
        query = self._apply_filters(
            db.query(OperationLog),
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            response_status=response_status,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )
        total = query.count()
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

    def get_user_statistics(
        self, db: Session, user_id: str, days: int = 30
    ) -> dict[str, Any]:
        """获取用户操作统计"""
        start_date = self._stats_start_date(days)
        base_query = self._stats_query(db, start_date=start_date, user_id=user_id)
        total_operations = base_query.with_entities(func.count(OperationLog.id)).scalar()

        # 按操作类型统计
        action_stats = (
            base_query.with_entities(OperationLog.action, func.count(OperationLog.id))
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "user_id": user_id,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {str(action): count for action, count in action_stats},
        }

    def get_module_statistics(
        self, db: Session, module: str, days: int = 30
    ) -> dict[str, Any]:
        """获取模块操作统计"""
        start_date = self._stats_start_date(days)
        base_query = self._stats_query(db, start_date=start_date, module=module)
        total_operations = base_query.with_entities(func.count(OperationLog.id)).scalar()

        # 按操作类型统计
        action_stats = (
            base_query.with_entities(OperationLog.action, func.count(OperationLog.id))
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "module": module,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {str(action): count for action, count in action_stats},
        }

    def get_daily_statistics(self, db: Session, days: int = 30) -> dict[str, Any]:
        """获取每日操作统计"""
        start_date = self._stats_start_date(days)
        daily_stats = (
            self._stats_query(db, start_date=start_date)
            .with_entities(
                func.date(OperationLog.created_at),
                func.count(OperationLog.id),
            )
            .group_by(func.date(OperationLog.created_at))
            .order_by(func.date(OperationLog.created_at))
            .all()
        )

        return {
            "days": days,
            "daily_breakdown": {str(date): count for date, count in daily_stats},
        }

    def get_error_statistics(self, db: Session, days: int = 30) -> dict[str, Any]:
        """获取错误操作统计"""
        start_date = self._stats_start_date(days)
        base_query = self._stats_query(db, start_date=start_date, error_only=True)
        total_errors = base_query.with_entities(func.count(OperationLog.id)).scalar()

        # 按错误类型统计
        error_types = (
            base_query.with_entities(
                OperationLog.action,
                func.count(OperationLog.id),
            )
            .group_by(OperationLog.action)
            .all()
        )

        return {
            "days": days,
            "total_errors": total_errors,
            "error_breakdown": {str(action): count for action, count in error_types},
        }

    def count(self, db: Session) -> int:
        """日志总数"""
        result = db.query(func.count(OperationLog.id)).scalar()
        return int(result) if result is not None else 0
