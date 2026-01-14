from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models.asset import SystemDictionary
from .base import CRUDBase


class CRUDSystemDictionary(CRUDBase):
    """系统字典CRUD操作类"""

    def __init__(self) -> None:
        super().__init__(SystemDictionary)

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
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SystemDictionary]:
        """根据筛选条件获取字典列表"""
        # Use simple filter dict mapping for consistency if possible, or QueryBuilder
        # Given existing logic was simple, let's keep it but enhance with QueryBuilder if complex features needed
        # Or just stick to manual filtering for this specific case if simple enough.
        # But standardize means using QueryBuilder is better.

        qb_filters: dict[str, Any] = {}
        if filters:
            if "dict_type" in filters:
                qb_filters["dict_type"] = filters["dict_type"]
            if "is_active" in filters:
                qb_filters["is_active"] = filters["is_active"]

        query = self.query_builder.build_query(
            filters=qb_filters,
            sort_by="sort_order",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        return list(db.execute(query).scalars().all())

    def get_by_type(
        self, db: Session, *, dict_type: str, is_active: bool = True
    ) -> list[SystemDictionary]:
        """根据类型获取字典列表"""
        filters: dict[str, Any] = {"dict_type": dict_type}
        if is_active is not None:
            filters["is_active"] = is_active

        query = self.query_builder.build_query(
            filters=filters,
            sort_by="sort_order",
            sort_desc=False,
            # No pagination usually for get_by_type usage (dropdowns), but safer to limit?
            # Existing code didn't limit.
        )
        return list(db.execute(query).scalars().all())

    def get_types(self, db: Session) -> list[str]:
        """
        获取所有字典类型

        注意：已废弃旧的system_dictionaries表，统一使用enum_field表
        """
        # 从枚举字段表获取类型
        try:
            from ..models.enum_field import EnumFieldType

            enum_types = (
                db.query(EnumFieldType.code)
                .filter(EnumFieldType.is_deleted.is_(False))
                .distinct()
                .all()
            )
            return sorted([row[0] for row in enum_types if row[0]])
        except ImportError:
            # 如果枚举字段模型不存在（向后兼容）
            return []


# 创建系统字典CRUD实例
system_dictionary_crud = CRUDSystemDictionary()
