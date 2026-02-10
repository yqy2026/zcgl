"""
操作日志CRUD操作
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operation_log import OperationLog


class OperationLogCRUD:
    """操作日志CRUD操作"""

    def _stats_start_date(self, days: int) -> datetime:
        return datetime.now() - timedelta(days=days)

    def _build_filter_clauses(
        self,
        *,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        response_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> list[Any]:
        clauses: list[Any] = []
        if user_id:
            clauses.append(OperationLog.user_id == user_id)
        if action:
            clauses.append(OperationLog.action == action)
        if module:
            clauses.append(OperationLog.module == module)
        if resource_type:
            clauses.append(OperationLog.resource_type == resource_type)
        if response_status:
            if response_status == "success":
                clauses.append(OperationLog.response_status >= 200)
                clauses.append(OperationLog.response_status < 300)
            elif response_status == "warning":
                clauses.append(OperationLog.response_status >= 400)
                clauses.append(OperationLog.response_status < 500)
            elif response_status == "error":
                clauses.append(OperationLog.response_status >= 500)
            elif response_status.isdigit():
                clauses.append(OperationLog.response_status == int(response_status))
        if start_date:
            clauses.append(OperationLog.created_at >= start_date)
        if end_date:
            clauses.append(OperationLog.created_at <= end_date)
        if search:
            clauses.append(
                or_(
                    OperationLog.username.ilike(f"%{search}%"),
                    OperationLog.action_name.ilike(f"%{search}%"),
                    OperationLog.resource_name.ilike(f"%{search}%"),
                )
            )
        return clauses

    def _build_stats_filter_clauses(
        self,
        *,
        start_date: datetime,
        user_id: str | None = None,
        module: str | None = None,
        error_only: bool = False,
    ) -> list[Any]:
        clauses: list[Any] = [OperationLog.created_at >= start_date]
        if user_id:
            clauses.append(OperationLog.user_id == user_id)
        if module:
            clauses.append(OperationLog.module == module)
        if error_only:
            clauses.append(OperationLog.error_message.isnot(None))
        return clauses

    async def create_async(
        self,
        db: AsyncSession,
        *,
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
        await db.commit()
        await db.refresh(log)

        return log

    async def get_async(self, db: AsyncSession, log_id: str) -> OperationLog | None:
        stmt = select(OperationLog).where(OperationLog.id == log_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_with_count_async(
        self,
        db: AsyncSession,
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
        clauses = self._build_filter_clauses(
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            response_status=response_status,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )
        count_stmt = select(func.count()).select_from(OperationLog).where(*clauses)
        total = int((await db.execute(count_stmt)).scalar() or 0)
        logs_stmt = (
            select(OperationLog)
            .where(*clauses)
            .order_by(OperationLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = list((await db.execute(logs_stmt)).scalars().all())
        return logs, total

    async def delete_old_logs_async(self, db: AsyncSession, days: int = 90) -> int:
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await db.execute(
            delete(OperationLog).where(OperationLog.created_at < cutoff_date)
        )
        await db.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    async def get_user_statistics_async(
        self, db: AsyncSession, user_id: str, days: int = 30
    ) -> dict[str, Any]:
        start_date = self._stats_start_date(days)
        clauses = self._build_stats_filter_clauses(
            start_date=start_date, user_id=user_id
        )
        total_stmt = select(func.count(OperationLog.id)).where(*clauses)
        total_operations = (await db.execute(total_stmt)).scalar()
        action_stmt = (
            select(OperationLog.action, func.count(OperationLog.id))
            .where(*clauses)
            .group_by(OperationLog.action)
        )
        action_stats = (await db.execute(action_stmt)).all()
        return {
            "user_id": user_id,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {str(action): count for action, count in action_stats},
        }

    async def get_module_statistics_async(
        self, db: AsyncSession, module: str, days: int = 30
    ) -> dict[str, Any]:
        start_date = self._stats_start_date(days)
        clauses = self._build_stats_filter_clauses(start_date=start_date, module=module)
        total_stmt = select(func.count(OperationLog.id)).where(*clauses)
        total_operations = (await db.execute(total_stmt)).scalar()
        action_stmt = (
            select(OperationLog.action, func.count(OperationLog.id))
            .where(*clauses)
            .group_by(OperationLog.action)
        )
        action_stats = (await db.execute(action_stmt)).all()
        return {
            "module": module,
            "days": days,
            "total_operations": total_operations,
            "action_breakdown": {str(action): count for action, count in action_stats},
        }

    async def get_daily_statistics_async(
        self, db: AsyncSession, days: int = 30
    ) -> dict[str, Any]:
        start_date = self._stats_start_date(days)
        clauses = self._build_stats_filter_clauses(start_date=start_date)
        daily_stmt = (
            select(func.date(OperationLog.created_at), func.count(OperationLog.id))
            .where(*clauses)
            .group_by(func.date(OperationLog.created_at))
            .order_by(func.date(OperationLog.created_at))
        )
        daily_stats = (await db.execute(daily_stmt)).all()
        return {
            "days": days,
            "daily_breakdown": {str(date): count for date, count in daily_stats},
        }

    async def get_error_statistics_async(
        self, db: AsyncSession, days: int = 30
    ) -> dict[str, Any]:
        start_date = self._stats_start_date(days)
        clauses = self._build_stats_filter_clauses(
            start_date=start_date, error_only=True
        )
        total_stmt = select(func.count(OperationLog.id)).where(*clauses)
        total_errors = (await db.execute(total_stmt)).scalar()
        error_stmt = (
            select(OperationLog.action, func.count(OperationLog.id))
            .where(*clauses)
            .group_by(OperationLog.action)
        )
        error_types = (await db.execute(error_stmt)).all()
        return {
            "days": days,
            "total_errors": total_errors,
            "error_breakdown": {str(action): count for action, count in error_types},
        }

    async def count_async(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count(OperationLog.id)))
        return int(result.scalar() or 0)
