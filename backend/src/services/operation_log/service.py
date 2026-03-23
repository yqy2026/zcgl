from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import bad_request, not_found
from ...crud.auth import UserCRUD
from ...crud.operation_log import OperationLogCRUD


class OperationLogService:
    """操作日志业务服务。"""

    async def get_operation_logs(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        user_id: str | None,
        action: str | None,
        module: str | None,
        resource_type: str | None,
        response_status: str | None,
        search: str | None,
        start_date: str | None,
        end_date: str | None,
    ) -> tuple[list[Any], int]:
        log_crud = OperationLogCRUD()
        user_crud = UserCRUD()
        skip = (page - 1) * page_size

        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise bad_request("开始日期格式错误，应为YYYY-MM-DD")

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise bad_request("结束日期格式错误，应为YYYY-MM-DD")

        logs, total = await log_crud.get_multi_with_count_async(
            db=db,
            skip=skip,
            limit=page_size,
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            response_status=response_status,
            start_date=start_dt,
            end_date=end_dt,
            search=search,
        )

        missing_user_ids = {
            log.user_id for log in logs if log.user_id and not log.username
        }
        if missing_user_ids:
            username_map = await user_crud.get_username_map_async(db, missing_user_ids)
            for log in logs:
                if log.user_id and not log.username:
                    resolved_username = username_map.get(str(log.user_id))
                    if resolved_username:
                        log.username = resolved_username

        return logs, total

    async def get_operation_log(self, db: AsyncSession, *, log_id: str) -> Any:
        log_crud = OperationLogCRUD()
        log = await log_crud.get_async(db, log_id)

        if not log:
            raise not_found(
                "日志不存在", resource_type="operation_log", resource_id=log_id
            )

        if log.user_id and not log.username:
            user_crud = UserCRUD()
            user = await user_crud.get_async(db, log.user_id)
            if user:
                log.username = user.username

        return log

    async def get_user_operation_statistics(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        days: int,
    ) -> dict[str, Any]:
        log_crud = OperationLogCRUD()
        return await log_crud.get_user_statistics_async(db, user_id, days)

    async def get_module_operation_statistics(
        self,
        db: AsyncSession,
        *,
        module: str,
        days: int,
    ) -> dict[str, Any]:
        log_crud = OperationLogCRUD()
        return await log_crud.get_module_statistics_async(db, module, days)

    async def get_daily_operation_statistics(
        self,
        db: AsyncSession,
        *,
        days: int,
    ) -> dict[str, Any]:
        log_crud = OperationLogCRUD()
        return await log_crud.get_daily_statistics_async(db, days)

    async def get_error_operation_statistics(
        self,
        db: AsyncSession,
        *,
        days: int,
    ) -> dict[str, Any]:
        log_crud = OperationLogCRUD()
        return await log_crud.get_error_statistics_async(db, days)

    async def get_operation_log_summary(
        self,
        db: AsyncSession,
        *,
        days: int,
    ) -> dict[str, Any]:
        log_crud = OperationLogCRUD()

        daily_stats = await log_crud.get_daily_statistics_async(db, days)
        error_stats = await log_crud.get_error_statistics_async(db, days)
        total_count = await log_crud.count_async(db)

        return {
            "total_logs": total_count,
            "days": days,
            "daily_statistics": daily_stats.get("daily_breakdown", {}),
            "error_statistics": error_stats,
        }

    async def export_operation_logs(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any],
    ) -> list[Any]:
        log_crud = OperationLogCRUD()
        logs, _ = await log_crud.get_multi_with_count_async(
            db=db,
            skip=0,
            limit=10000,
            **filters,
        )
        return logs

    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        *,
        days: int,
    ) -> int:
        log_crud = OperationLogCRUD()
        return await log_crud.delete_old_logs_async(db, days)


operation_log_service = OperationLogService()


def get_operation_log_service() -> OperationLogService:
    return operation_log_service
