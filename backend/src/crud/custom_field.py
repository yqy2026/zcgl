from typing import Any

from sqlalchemy.orm import Session

from ..models.asset import AssetCustomField
from ..schemas.asset import AssetCustomFieldCreate, AssetCustomFieldUpdate
from .base import CRUDBase


class CRUDCustomField(CRUDBase):
    """自定义字段CRUD操作类"""

    def get_by_field_name(
        self, db: Session, *, field_name: str
    ) -> AssetCustomField | None:
        """根据字段名获取字段配置"""
        return (
            db.query(AssetCustomField)
            .filter(AssetCustomField.field_name == field_name)
            .first()
        )

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AssetCustomField]:
        """根据筛选条件获取字段列表"""
        if filters is None:
            filters = {}

        from sqlalchemy import select

        base_query = select(self.model)

        qb_filters: dict[str, Any] = {}
        if filters:
            if "field_type" in filters:
                qb_filters["field_type"] = filters["field_type"]
            if "is_required" in filters:
                qb_filters["is_required"] = filters["is_required"]
            if "is_active" in filters:
                qb_filters["is_active"] = filters["is_active"]
            # asset_id logic in original was pass/empty, keeping it implicitly handled or ignored

        query = self.query_builder.build_query(
            filters=qb_filters,
            base_query=base_query,
            sort_by="sort_order",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        return list(db.execute(query).scalars().all())

    def get_active_fields(self, db: Session) -> list[AssetCustomField]:
        """获取所有启用的字段"""
        from sqlalchemy import select

        base_query = select(self.model)

        query = self.query_builder.build_query(
            filters={"is_active": True},
            base_query=base_query,
            sort_by="sort_order",
            sort_desc=False,
        )
        return list(db.execute(query).scalars().all())

    def get_asset_field_values(
        self, db: Session, *, asset_id: str
    ) -> list[dict[str, Any]]:
        """获取资产的自定义字段值"""
        # 这是一个存根，逻辑上属于数据访问，保留在CRUD中
        # 实际实现中应查询 asset_field_values 表
        return []

    # Removed: validate_field_value (moved to Service)
    # Removed: update_asset_field_values (moved to Service)
    # Removed: toggle_active_status (moved to Service)
    # Removed: update_sort_orders (moved to Service)


# 创建自定义字段CRUD实例
custom_field_crud: CRUDCustomField = CRUDCustomField(AssetCustomField)
