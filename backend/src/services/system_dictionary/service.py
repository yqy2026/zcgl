from typing import Any

from sqlalchemy.orm import Session

from ...crud.system_dictionary import system_dictionary_crud
from ...models.asset import SystemDictionary
from ...schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate


class SystemDictionaryService:
    """系统字典服务层"""

    def create_dictionary(
        self, db: Session, *, obj_in: SystemDictionaryCreate
    ) -> SystemDictionary:
        """创建字典项"""
        # Check uniqueness
        existing = system_dictionary_crud.get_by_type_and_code(
            db, dict_type=obj_in.dict_type, dict_code=obj_in.dict_code
        )
        if existing:
            raise ValueError(f"字典代码 {obj_in.dict_code} 在类型 {obj_in.dict_type} 中已存在")

        return system_dictionary_crud.create(db, obj_in=obj_in)

    def update_dictionary(
        self, db: Session, *, id: str, obj_in: SystemDictionaryUpdate
    ) -> SystemDictionary:
        """更新字典项"""
        db_obj = system_dictionary_crud.get(db, id)
        if not db_obj:
            raise ValueError("字典项不存在")

        return system_dictionary_crud.update(db, db_obj=db_obj, obj_in=obj_in)

    def delete_dictionary(self, db: Session, *, id: str) -> SystemDictionary:
        """删除字典项"""
        db_obj = system_dictionary_crud.get(db, id)
        if not db_obj:
            raise ValueError("字典项不存在")
        
        # Soft delete logic if model supports it, otherwise hard delete
        # SystemDictionary usually hard delete or soft?
        # CRUDBase remove is hard delete unless overridden.
        # Let's check model.
        return system_dictionary_crud.remove(db, id=id)

    def toggle_active_status(self, db: Session, *, id: str) -> SystemDictionary:
        """切换启用状态"""
        dictionary = system_dictionary_crud.get(db, id)
        if not dictionary:
            raise ValueError("字典项不存在")
            
        dictionary.is_active = not dictionary.is_active
        db.add(dictionary)
        db.commit()
        db.refresh(dictionary)
        return dictionary

    def update_sort_orders(
        self, db: Session, *, dict_type: str, sort_data: list[dict[str, Any]]
    ) -> list[SystemDictionary]:
        """批量更新排序"""
        updated_items = []

        for item in sort_data:
            dictionary_id = item.get("id")
            sort_order = item.get("sort_order")

            if dictionary_id and sort_order is not None:
                dictionary = system_dictionary_crud.get(db, dictionary_id)
                # Verify type matches to prevent cross-type accidental sorts if IDs valid
                if dictionary and dictionary.dict_type == dict_type:
                    dictionary.sort_order = sort_order
                    db.add(dictionary)
                    updated_items.append(dictionary)

        db.commit()
        # Refresh all?
        for item in updated_items:
            db.refresh(item)
            
        return updated_items


system_dictionary_service = SystemDictionaryService()
