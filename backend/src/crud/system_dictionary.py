"""
系统字典CRUD操作
"""

from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models.asset import SystemDictionary
from ..schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate
from .base import CRUDBase


class CRUDSystemDictionary(
    CRUDBase[SystemDictionary, SystemDictionaryCreate, SystemDictionaryUpdate]
):
    """系统字典CRUD操作类"""

    def get_by_type_and_code(
        self, db: Session, *, dict_type: str, dict_code: str
    ) -> SystemDictionary | None:
        """根据类型和代码获取字典项"""
        return (
            db.query(SystemDictionary)
            .filter(
                and_(
                    SystemDictionary.dict_type == dict_type,
                    SystemDictionary.dict_code == dict_code,
                )
            )
            .first()
        )

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        filters: dict[str, Any] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SystemDictionary]:
        """根据筛选条件获取字典列表"""
        query = db.query(self.model)

        if filters:
            if "dict_type" in filters:
                query = query.filter(SystemDictionary.dict_type == filters["dict_type"])
            if "is_active" in filters:
                query = query.filter(SystemDictionary.is_active == filters["is_active"])

        return (
            query.order_by(SystemDictionary.sort_order, SystemDictionary.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_type(
        self, db: Session, *, dict_type: str, is_active: bool = True
    ) -> List[SystemDictionary]:
        """根据类型获取字典列表"""
        query = db.query(SystemDictionary).filter(
            SystemDictionary.dict_type == dict_type
        )

        if is_active is not None:
            query = query.filter(SystemDictionary.is_active == is_active)

        return query.order_by(
            SystemDictionary.sort_order, SystemDictionary.created_at
        ).all()

    def get_types(self, db: Session) -> List[str]:
        """获取所有字典类型"""
        result = db.query(SystemDictionary.dict_type).distinct().all()
        return [row[0] for row in result if row[0]]

    def get_active_by_type(
        self, db: Session, *, dict_type: str
    ) -> List[SystemDictionary]:
        """获取指定类型的启用字典项"""
        return self.get_by_type(db=db, dict_type=dict_type, is_active=True)

    def update_sort_orders(
        self, db: Session, *, dict_type: str, sort_data: list[dict[str, Any]]
    ) -> List[SystemDictionary]:
        """批量更新排序"""
        updated_items = []

        for item in sort_data:
            dictionary_id = item.get("id")
            sort_order = item.get("sort_order")

            if dictionary_id and sort_order is not None:
                dictionary = self.get(db=db, id=dictionary_id)
                if dictionary and dictionary.dict_type == dict_type:
                    dictionary.sort_order = sort_order
                    db.add(dictionary)
                    updated_items.append(dictionary)

        db.commit()
        return updated_items

    def toggle_active_status(self, db: Session, *, id: str) -> SystemDictionary | None:
        """切换启用状态"""
        dictionary = self.get(db=db, id=id)
        if dictionary:
            dictionary.is_active = not dictionary.is_active
            db.add(dictionary)
            db.commit()
            db.refresh(dictionary)
        return dictionary


# 创建系统字典CRUD实例
system_dictionary_crud = CRUDSystemDictionary(SystemDictionary)
