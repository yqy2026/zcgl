"""Excel 配置服务层。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.task import excel_task_config_crud
from ...models.task import ExcelTaskConfig


class ExcelConfigService:
    """Excel 配置服务。"""

    async def create_config(
        self,
        db: AsyncSession,
        *,
        config_data: dict[str, Any],
    ) -> ExcelTaskConfig:
        if config_data.get("is_default") is True:
            await excel_task_config_crud.unset_default_configs_async(
                db=db,
                config_type=config_data["config_type"],
                task_type=config_data["task_type"],
            )
        return await excel_task_config_crud.create(db=db, obj_in=config_data)

    async def get_configs(
        self,
        db: AsyncSession,
        *,
        config_type: str | None,
        task_type: str | None,
        limit: int,
    ) -> list[ExcelTaskConfig]:
        return await excel_task_config_crud.get_multi_async(
            db=db,
            limit=limit,
            config_type=config_type,
            task_type=task_type,
        )

    async def get_default_config(
        self,
        db: AsyncSession,
        *,
        config_type: str,
        task_type: str,
    ) -> ExcelTaskConfig | None:
        return await excel_task_config_crud.get_default_async(
            db=db,
            config_type=config_type,
            task_type=task_type,
        )

    async def get_config(
        self,
        db: AsyncSession,
        *,
        config_id: str,
    ) -> ExcelTaskConfig | None:
        return await excel_task_config_crud.get(db=db, id=config_id)

    async def update_config(
        self,
        db: AsyncSession,
        *,
        config: ExcelTaskConfig,
        config_data: dict[str, Any],
    ) -> ExcelTaskConfig:
        if config_data.get("is_default") is True:
            target_config_type = config_data.get("config_type")
            if not isinstance(target_config_type, str):
                target_config_type = config.config_type or ""

            target_task_type = config_data.get("task_type")
            if not isinstance(target_task_type, str):
                target_task_type = config.task_type or ""

            await excel_task_config_crud.unset_default_configs_async(
                db=db,
                config_type=target_config_type,
                task_type=target_task_type,
                exclude_config_id=config.id,
            )
        return await excel_task_config_crud.update(
            db=db,
            db_obj=config,
            obj_in=config_data,
        )

    async def delete_config(self, db: AsyncSession, *, config_id: str) -> Any:
        return await excel_task_config_crud.remove(db=db, id=config_id)


excel_config_service = ExcelConfigService()


def get_excel_config_service() -> ExcelConfigService:
    return excel_config_service
