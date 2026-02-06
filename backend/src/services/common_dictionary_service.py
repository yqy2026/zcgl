"""
统一字典服务层
封装字典相关的所有业务逻辑，API 层只负责路由转发
"""

from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import conflict, not_found
from ..crud.enum_field import get_enum_field_type_crud, get_enum_field_value_crud
from ..models.asset import SystemDictionary
from ..models.enum_field import EnumFieldHistory, EnumFieldValue
from ..schemas.dictionary import (
    DictionaryOptionResponse,
    DictionaryValueCreate,
    SimpleDictionaryCreate,
)
from ..schemas.enum_field import EnumFieldTypeCreate, EnumFieldValueCreate


class CommonDictionaryService:
    """统一字典服务"""

    async def get_combined_options_async(
        self, db: AsyncSession, dict_type: str, is_active: bool | None = True
    ) -> list[DictionaryOptionResponse]:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = await enum_type_crud.get_by_code_async(db, dict_type)

        if enum_type:
            enum_value_crud = get_enum_field_value_crud(db)
            enum_type_id_str = str(enum_type.id)
            enum_values = await enum_value_crud.get_by_type_async(
                db,
                enum_type_id_str,
                is_active=is_active if is_active is not None else None,
            )

            return [
                DictionaryOptionResponse(
                    label=str(value.label),
                    value=str(value.value),
                    code=str(value.code) if value.code is not None else None,
                    sort_order=int(value.sort_order or 0),
                    color=str(value.color) if value.color is not None else None,
                    icon=str(value.icon) if value.icon is not None else None,
                )
                for value in enum_values
            ]

        stmt = select(SystemDictionary).where(SystemDictionary.dict_type == dict_type)
        if is_active is not None:
            stmt = stmt.where(SystemDictionary.is_active == is_active)

        result = await db.execute(
            stmt.order_by(SystemDictionary.sort_order, SystemDictionary.created_at)
        )
        system_dicts = list(result.scalars().all())

        return [
            DictionaryOptionResponse(
                label=item.dict_label,
                value=item.dict_value,
                code=item.dict_code,
                sort_order=item.sort_order,
            )
            for item in system_dicts
        ]

    async def quick_create_enum_dictionary_async(
        self,
        db: AsyncSession,
        dict_type: str,
        data: SimpleDictionaryCreate,
        operator: str,
    ) -> dict[str, Any]:
        enum_type_crud = get_enum_field_type_crud(db)

        existing_type = await enum_type_crud.get_by_code_async(db, dict_type)
        if existing_type:
            raise conflict(f"字典类型 {dict_type} 已存在", resource_type="dictionary")

        enum_type_create = EnumFieldTypeCreate(
            name=dict_type.replace("_", " ").title(),
            code=dict_type,
            category="简单字典",
            description=data.description or f"{dict_type} 字典",
            is_system=False,
            is_hierarchical=False,
            is_multiple=False,
            created_by=operator,
            default_value=None,
            validation_rules=None,
            display_config=None,
        )

        enum_type = await enum_type_crud.create_async(db, enum_type_create)

        enum_value_crud = get_enum_field_value_crud(db)
        created_values = []
        enum_type_id_str = str(enum_type.id)

        for i, option in enumerate(data.options):
            enum_value_create = EnumFieldValueCreate(
                enum_type_id=enum_type_id_str,
                label=option.label,
                value=option.value,
                code=option.code,
                description=option.description,
                sort_order=option.sort_order if option.sort_order > 0 else i + 1,
                color=option.color,
                icon=option.icon,
                is_active=option.is_active,
                created_by=operator,
                parent_id=None,
                extra_properties=None,
            )
            created_value = await enum_value_crud.create_async(db, enum_value_create)
            created_values.append(created_value)

        return {
            "message": f"字典 {dict_type} 创建成功",
            "type_id": str(enum_type.id),
            "values_count": len(created_values),
        }

    async def add_dictionary_value_async(
        self,
        db: AsyncSession,
        dict_type: str,
        value_data: DictionaryValueCreate,
        operator: str,
    ) -> dict[str, Any]:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = await enum_type_crud.get_by_code_async(db, dict_type)

        if not enum_type:
            raise not_found(f"字典类型 {dict_type} 不存在", resource_type="dictionary")

        enum_value_crud = get_enum_field_value_crud(db)
        enum_type_id_str = str(enum_type.id)
        existing_value = await enum_value_crud.get_by_type_and_value_async(
            db, enum_type_id_str, value_data.value
        )
        if existing_value:
            raise conflict(
                f"值 {value_data.value} 已存在", resource_type="dictionary_value"
            )

        enum_value_create = EnumFieldValueCreate(
            enum_type_id=enum_type_id_str,
            label=value_data.label,
            value=value_data.value,
            code=value_data.code,
            description=value_data.description,
            sort_order=value_data.sort_order,
            color=value_data.color,
            icon=value_data.icon,
            is_active=value_data.is_active,
            created_by=operator,
            parent_id=None,
            extra_properties=None,
        )

        created_value = await enum_value_crud.create_async(db, enum_value_create)

        return {"message": "字典值添加成功", "value_id": str(created_value.id)}

    async def delete_dictionary_type_async(
        self, db: AsyncSession, dict_type: str, operator: str
    ) -> dict[str, str]:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = await enum_type_crud.get_by_code_async(db, dict_type)

        if not enum_type:
            raise not_found(f"字典类型 {dict_type} 不存在", resource_type="dictionary")

        enum_type_id_str = str(enum_type.id)
        values_stmt = (
            select(EnumFieldValue.id)
            .where(
                EnumFieldValue.enum_type_id == enum_type_id_str,
                EnumFieldValue.is_deleted.is_(False),
            )
            .order_by(EnumFieldValue.level.desc())
        )
        value_ids = list((await db.execute(values_stmt)).scalars().all())

        if value_ids:
            await db.execute(
                delete(EnumFieldHistory).where(
                    EnumFieldHistory.enum_value_id.in_(value_ids)
                )
            )
            await db.execute(
                update(EnumFieldValue)
                .where(EnumFieldValue.id.in_(value_ids))
                .values(
                    {
                        EnumFieldValue.is_deleted: True,
                        EnumFieldValue.updated_by: operator,
                    }
                )
            )
            await db.flush()

        await enum_type_crud.delete_async(db, enum_type_id_str, deleted_by=operator)

        return {"message": f"字典类型 {dict_type} 删除成功"}

    async def get_all_dictionary_types_async(self, db: AsyncSession) -> list[str]:
        from ..models.enum_field import EnumFieldType

        stmt = select(EnumFieldType.code).where(EnumFieldType.is_deleted.is_(False))
        enum_types = list((await db.execute(stmt)).scalars().all())
        return sorted([code for code in enum_types if code])


# 单例服务实例
common_dictionary_service = CommonDictionaryService()
