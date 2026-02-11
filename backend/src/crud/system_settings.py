"""System settings related CRUD helpers."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemSettingsCRUD:
    """系统设置相关 CRUD 操作。"""

    async def check_database_connection_async(self, db: AsyncSession) -> bool:
        result = await db.scalar(text("SELECT 1"))
        return bool(result == 1)


system_settings_crud = SystemSettingsCRUD()
