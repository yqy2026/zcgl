from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import DuplicateResourceError, ResourceNotFoundError
from ...crud.system_dictionary import system_dictionary_crud
from ...models.system_dictionary import SystemDictionary
from ...schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate


class SystemDictionaryService:
    """系统字典服务层"""

    async def create_dictionary_async(
        self, db: AsyncSession, *, obj_in: SystemDictionaryCreate
    ) -> SystemDictionary:
        existing = await system_dictionary_crud.get_by_type_and_code_async(
            db, dict_type=obj_in.dict_type, dict_code=obj_in.dict_code
        )
        if existing:
            raise DuplicateResourceError(
                "字典项",
                "dict_code",
                obj_in.dict_code,
                details={"dict_type": obj_in.dict_type},
            )

        result: SystemDictionary = await system_dictionary_crud.create(
            db, obj_in=obj_in
        )
        return result

    async def update_dictionary_async(
        self, db: AsyncSession, *, id: str, obj_in: SystemDictionaryUpdate
    ) -> SystemDictionary:
        db_obj = await system_dictionary_crud.get(db, id)
        if not db_obj:
            raise ResourceNotFoundError("字典项", id)

        result: SystemDictionary = await system_dictionary_crud.update(
            db, db_obj=db_obj, obj_in=obj_in
        )
        return result

    async def delete_dictionary_async(
        self, db: AsyncSession, *, id: str
    ) -> SystemDictionary:
        db_obj = await system_dictionary_crud.get(db, id)
        if not db_obj:
            raise ResourceNotFoundError("字典项", id)

        result: SystemDictionary = await system_dictionary_crud.remove(db, id=id)
        return result

    async def toggle_active_status_async(
        self, db: AsyncSession, *, id: str
    ) -> SystemDictionary:
        dictionary: SystemDictionary | None = await system_dictionary_crud.get(db, id)
        if not dictionary:
            raise ResourceNotFoundError("字典项", id)

        dictionary.is_active = not dictionary.is_active
        db.add(dictionary)
        await db.commit()
        await db.refresh(dictionary)
        return dictionary

    async def update_sort_orders_async(
        self, db: AsyncSession, *, dict_type: str, sort_data: list[dict[str, Any]]
    ) -> list[SystemDictionary]:
        updates_by_id: dict[str, Any] = {}
        ordered_ids: list[str] = []
        for item in sort_data:
            dictionary_id = item.get("id")
            sort_order = item.get("sort_order")
            if dictionary_id and sort_order is not None:
                dictionary_id_str = str(dictionary_id)
                updates_by_id[dictionary_id_str] = sort_order
                ordered_ids.append(dictionary_id_str)

        if not updates_by_id:
            await db.commit()
            return []

        dictionaries = await system_dictionary_crud.get_multi_by_ids_and_type_async(
            db, ids=list(updates_by_id.keys()), dict_type=dict_type
        )
        dictionary_by_id: dict[str, SystemDictionary] = {
            str(item.id): item for item in dictionaries
        }

        updated_items: list[SystemDictionary] = []
        seen: set[str] = set()
        for dictionary_id in ordered_ids:
            if dictionary_id in seen:
                continue
            dictionary_obj = dictionary_by_id.get(dictionary_id)
            if dictionary_obj is None:
                continue
            dictionary_obj.sort_order = updates_by_id[dictionary_id]
            db.add(dictionary_obj)
            updated_items.append(dictionary_obj)
            seen.add(dictionary_id)

        await db.commit()

        return updated_items


system_dictionary_service = SystemDictionaryService()
