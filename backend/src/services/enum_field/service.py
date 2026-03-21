import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from ...constants.message_constants import EMPTY_STRING
from ...core.exception_handler import bad_request, conflict, not_found
from ...crud.enum_field import (
    get_enum_field_history_crud,
    get_enum_field_type_crud,
    get_enum_field_usage_crud,
    get_enum_field_value_crud,
)
from ...schemas.enum_field import (
    EnumFieldBatchCreate,
    EnumFieldHistoryResponse,
    EnumFieldStatistics,
    EnumFieldTree,
    EnumFieldTypeCreate,
    EnumFieldTypeResponse,
    EnumFieldTypeUpdate,
    EnumFieldUsageCreate,
    EnumFieldUsageResponse,
    EnumFieldUsageUpdate,
    EnumFieldValueCreate,
    EnumFieldValueResponse,
    EnumFieldValueUpdate,
)


class EnumFieldService:
    """枚举字段业务服务。"""

    logger = logging.getLogger(__name__)

    @staticmethod
    def _clear_enum_children(value: Any) -> None:
        try:
            set_committed_value(value, "children", [])
            return
        except Exception as exc:
            last_error = exc

        try:
            object.__setattr__(value, "children", [])
            return
        except Exception as exc:
            last_error = exc

        try:
            setattr(value, "children", [])
        except Exception as exc:
            EnumFieldService.logger.debug(
                "failed to clear enum children for %r: %s (previous: %s)",
                value,
                exc,
                last_error,
            )

    @staticmethod
    def _strip_enum_children(enum_values: list[Any] | None) -> None:
        """Remove children relationships to avoid async lazy-load in response models."""
        if not enum_values:
            return
        for value in enum_values:
            EnumFieldService._clear_enum_children(value)

    def _build_tree_response(self, values: list[Any]) -> list[EnumFieldTree]:
        tree: list[EnumFieldTree] = []
        for value in values:
            children = self._build_tree_response(getattr(value, "children", []))
            tree_node = EnumFieldTree(
                id=value.id,
                label=value.label,
                value=value.value,
                code=value.code,
                level=value.level,
                sort_order=value.sort_order,
                is_active=value.is_active,
                color=value.color,
                icon=value.icon,
                children=children,
            )
            tree.append(tree_node)
        return tree

    async def get_enum_field_types(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        category: str | None,
        status: str | None,
        is_system: bool | None,
        keyword: str | None,
    ) -> list[EnumFieldTypeResponse]:
        actual_skip = (page - 1) * page_size
        actual_limit = page_size

        actual_category = (
            str(category) if category is not None and category != EMPTY_STRING else None
        )
        actual_status = (
            str(status) if status is not None and status != EMPTY_STRING else None
        )
        actual_keyword = (
            str(keyword) if keyword is not None and keyword != EMPTY_STRING else None
        )

        actual_is_system = None
        if is_system is not None:
            try:
                actual_is_system = bool(is_system)
            except (ValueError, TypeError):
                actual_is_system = None

        crud = get_enum_field_type_crud(db)
        enum_types = await crud.get_multi_async(
            db,
            skip=actual_skip,
            limit=actual_limit,
            category=actual_category,
            status=actual_status,
            is_system=actual_is_system,
            keyword=actual_keyword,
        )
        for enum_type in enum_types:
            self._strip_enum_children(getattr(enum_type, "enum_values", None))
        return [
            EnumFieldTypeResponse.model_validate(enum_type) for enum_type in enum_types
        ]

    async def get_enum_field_statistics(self, db: AsyncSession) -> EnumFieldStatistics:
        type_crud = get_enum_field_type_crud(db)
        value_crud = get_enum_field_value_crud(db)
        usage_crud = get_enum_field_usage_crud(db)

        type_stats = await type_crud.get_statistics_async(db)
        total_values = await value_crud.count_all_async(db)
        active_values = await value_crud.count_active_async(db)
        usage_count = await usage_crud.count_active_async(db)

        return EnumFieldStatistics(
            total_types=type_stats["total_types"],
            active_types=type_stats["active_types"],
            total_values=total_values,
            active_values=active_values,
            usage_count=usage_count,
            categories=type_stats["categories"],
        )

    async def get_enum_field_type(
        self, db: AsyncSession, *, type_id: str
    ) -> EnumFieldTypeResponse:
        crud = get_enum_field_type_crud(db)
        enum_type = await crud.get_async(db, type_id)
        if not enum_type:
            raise not_found(
                "枚举类型不存在", resource_type="enum_type", resource_id=type_id
            )
        self._strip_enum_children(getattr(enum_type, "enum_values", None))
        return EnumFieldTypeResponse.model_validate(enum_type)

    async def create_enum_field_type(
        self, db: AsyncSession, *, enum_type: EnumFieldTypeCreate
    ) -> EnumFieldTypeResponse:
        crud = get_enum_field_type_crud(db)
        existing = await crud.get_by_code_async(db, enum_type.code)
        if existing:
            raise conflict(f"编码 {enum_type.code} 已存在", resource_type="enum_type")

        try:
            db_enum_type = await crud.create_async(db, enum_type)
            return EnumFieldTypeResponse.model_validate(db_enum_type)
        except ValueError as e:
            raise bad_request(str(e))

    async def update_enum_field_type(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        enum_type: EnumFieldTypeUpdate,
    ) -> EnumFieldTypeResponse:
        crud = get_enum_field_type_crud(db)
        db_enum_type = await crud.get_async(db, type_id)
        if not db_enum_type:
            raise not_found(
                "枚举类型不存在", resource_type="enum_type", resource_id=type_id
            )

        if enum_type.code and enum_type.code != db_enum_type.code:
            existing = await crud.get_by_code_async(db, enum_type.code)
            if existing and existing.id != type_id:
                raise conflict(
                    f"编码 {enum_type.code} 已存在", resource_type="enum_type"
                )

        try:
            updated_enum_type = await crud.update_async(db, db_enum_type, enum_type)
            return EnumFieldTypeResponse.model_validate(updated_enum_type)
        except ValueError as e:
            raise bad_request(str(e))

    async def delete_enum_field_type(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        deleted_by: str | None,
    ) -> dict[str, str]:
        crud = get_enum_field_type_crud(db)
        try:
            success = await crud.delete_async(db, type_id, deleted_by=deleted_by)
            if not success:
                raise not_found(
                    "枚举类型不存在", resource_type="enum_type", resource_id=type_id
                )
            return {"message": "枚举类型删除成功"}
        except ValueError as e:
            raise bad_request(str(e))

    async def get_enum_field_categories(self, db: AsyncSession) -> dict[str, list[str]]:
        crud = get_enum_field_type_crud(db)
        categories = await crud.get_categories_async(db)
        return {"categories": categories}

    async def get_enum_field_values(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        parent_id: str | None,
        is_active: bool | None,
    ) -> list[EnumFieldValueResponse]:
        crud = get_enum_field_value_crud(db)
        enum_values = await crud.get_by_type_async(
            db, type_id, parent_id=parent_id, is_active=is_active
        )
        self._strip_enum_children(enum_values)
        return [EnumFieldValueResponse.model_validate(value) for value in enum_values]

    async def get_enum_field_values_tree(
        self, db: AsyncSession, *, type_id: str
    ) -> list[EnumFieldTree]:
        crud = get_enum_field_value_crud(db)
        tree_values = await crud.get_tree_async(db, type_id)
        return self._build_tree_response(tree_values)

    async def get_enum_field_value(
        self, db: AsyncSession, *, value_id: str
    ) -> EnumFieldValueResponse:
        crud = get_enum_field_value_crud(db)
        enum_value = await crud.get_async(db, value_id)
        if not enum_value:
            raise not_found(
                "枚举值不存在", resource_type="enum_value", resource_id=value_id
            )
        self._strip_enum_children([enum_value])
        return EnumFieldValueResponse.model_validate(enum_value)

    async def create_enum_field_value(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        enum_value: EnumFieldValueCreate,
    ) -> EnumFieldValueResponse:
        value_crud = get_enum_field_value_crud(db)
        type_crud = get_enum_field_type_crud(db)

        enum_type = await type_crud.get_async(db, type_id)
        if not enum_type:
            raise not_found(
                "枚举类型不存在", resource_type="enum_type", resource_id=type_id
            )

        existing = await value_crud.get_by_type_and_value_async(
            db, type_id, enum_value.value
        )
        if existing:
            raise conflict(f"值 {enum_value.value} 已存在", resource_type="enum_value")

        enum_value.enum_type_id = type_id

        try:
            db_enum_value = await value_crud.create_async(db, enum_value)
            return EnumFieldValueResponse.model_validate(db_enum_value)
        except ValueError as e:
            raise bad_request(str(e))

    async def update_enum_field_value(
        self,
        db: AsyncSession,
        *,
        value_id: str,
        enum_value: EnumFieldValueUpdate,
    ) -> EnumFieldValueResponse:
        crud = get_enum_field_value_crud(db)
        db_enum_value = await crud.get_async(db, value_id)
        if not db_enum_value:
            raise not_found(
                "枚举值不存在", resource_type="enum_value", resource_id=value_id
            )

        if enum_value.value and enum_value.value != db_enum_value.value:
            existing = await crud.get_by_type_and_value_async(
                db, getattr(db_enum_value, "enum_type_id", ""), enum_value.value
            )
            if existing and existing.id != value_id:
                raise conflict(
                    f"值 {enum_value.value} 已存在", resource_type="enum_value"
                )

        try:
            updated_enum_value = await crud.update_async(db, db_enum_value, enum_value)
            return EnumFieldValueResponse.model_validate(updated_enum_value)
        except ValueError as e:
            raise bad_request(str(e))

    async def delete_enum_field_value(
        self,
        db: AsyncSession,
        *,
        value_id: str,
        deleted_by: str | None,
    ) -> dict[str, str]:
        crud = get_enum_field_value_crud(db)
        try:
            success = await crud.delete_async(db, value_id, deleted_by=deleted_by)
            if not success:
                raise not_found(
                    "枚举值不存在", resource_type="enum_value", resource_id=value_id
                )
            return {"message": "枚举值删除成功"}
        except ValueError as e:
            raise bad_request(str(e))

    async def batch_create_enum_field_values(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        batch_data: EnumFieldBatchCreate,
    ) -> list[EnumFieldValueResponse]:
        value_crud = get_enum_field_value_crud(db)
        type_crud = get_enum_field_type_crud(db)
        enum_type = await type_crud.get_async(db, type_id)
        if not enum_type:
            raise not_found(
                "枚举类型不存在", resource_type="enum_type", resource_id=type_id
            )

        try:
            created_values = await value_crud.batch_create_async(
                db, type_id, batch_data.values, batch_data.created_by
            )
            return [
                EnumFieldValueResponse.model_validate(value) for value in created_values
            ]
        except ValueError as e:
            raise bad_request(str(e))

    async def get_enum_field_usage(
        self,
        db: AsyncSession,
        *,
        enum_type_id: str | None,
        table_name: str | None,
        module_name: str | None,
    ) -> list[EnumFieldUsageResponse]:
        _ = table_name, module_name
        crud = get_enum_field_usage_crud(db)
        usage_records = (
            await crud.get_by_enum_type_async(db, enum_type_id) if enum_type_id else []
        )
        return [EnumFieldUsageResponse.model_validate(usage) for usage in usage_records]

    async def create_enum_field_usage(
        self, db: AsyncSession, *, usage: EnumFieldUsageCreate
    ) -> EnumFieldUsageResponse:
        crud = get_enum_field_usage_crud(db)
        existing = await crud.get_by_field_async(db, usage.table_name, usage.field_name)
        if existing:
            raise conflict(
                f"表 {usage.table_name} 的字段 {usage.field_name} 已存在使用记录",
                resource_type="enum_usage",
            )

        db_usage = await crud.create_async(db, usage)
        return EnumFieldUsageResponse.model_validate(db_usage)

    async def update_enum_field_usage(
        self,
        db: AsyncSession,
        *,
        usage_id: str,
        usage: EnumFieldUsageUpdate,
    ) -> EnumFieldUsageResponse:
        crud = get_enum_field_usage_crud(db)
        db_usage = await crud.get_async(db, usage_id)
        if not db_usage:
            raise not_found(
                "使用记录不存在", resource_type="enum_usage", resource_id=usage_id
            )

        updated_usage = await crud.update_async(db, db_usage, usage)
        return EnumFieldUsageResponse.model_validate(updated_usage)

    async def delete_enum_field_usage(
        self, db: AsyncSession, *, usage_id: str
    ) -> dict[str, str]:
        crud = get_enum_field_usage_crud(db)
        success = await crud.delete_async(db, usage_id)
        if not success:
            raise not_found(
                "使用记录不存在", resource_type="enum_usage", resource_id=usage_id
            )
        return {"message": "使用记录删除成功"}

    async def get_enum_field_type_history(
        self,
        db: AsyncSession,
        *,
        type_id: str,
        page: int,
        page_size: int,
    ) -> list[EnumFieldHistoryResponse]:
        skip = (page - 1) * page_size
        history_crud = get_enum_field_history_crud(db)
        history_records = await history_crud.get_multi_async(
            db, enum_type_id=type_id, skip=skip, limit=page_size
        )
        return [
            EnumFieldHistoryResponse.model_validate(history)
            for history in history_records
        ]

    async def get_enum_field_value_history(
        self,
        db: AsyncSession,
        *,
        value_id: str,
        page: int,
        page_size: int,
    ) -> list[EnumFieldHistoryResponse]:
        skip = (page - 1) * page_size
        history_crud = get_enum_field_history_crud(db)
        history_records = await history_crud.get_multi_async(
            db, enum_value_id=value_id, skip=skip, limit=page_size
        )
        return [
            EnumFieldHistoryResponse.model_validate(history)
            for history in history_records
        ]


enum_field_service = EnumFieldService()


def get_enum_field_service() -> EnumFieldService:
    return enum_field_service
