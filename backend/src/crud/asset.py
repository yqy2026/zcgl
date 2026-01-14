from typing import Any

"""
资产CRUD操作 - 优化版本

注意: 此层为纯数据访问层，不包含业务逻辑。
资产计算逻辑（AssetCalculator）应在 API 或 Service 层调用。
"""

from sqlalchemy.orm import Session

from ..core.performance import cached, monitor_query
from ..models.asset import Asset, AssetHistory
from ..schemas.asset import AssetCreate, AssetUpdate
from .base import CRUDBase


class SensitiveDataHandler:
    """敏感数据处理器"""

    def encrypt_sensitive_data(self, data: Any) -> Any:
        """加密敏感数据"""

        # 在实际应用中，这里应该实现真正的数据加密逻辑

        # 例如使用AES加密算法

        return data


class AssetCRUD(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """资产CRUD操作类 - 优化版本"""

    def __init__(self) -> None:
        super().__init__(Asset)
        self.sensitive_data_handler = SensitiveDataHandler()

    def get_by_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()

    def get_by_property_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产（别名方法）"""
        return self.get_by_name(db, property_name)

    @monitor_query("asset_get_multi_with_search")
    @cached(ttl=600)
    def get_multi_with_search(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Asset], int]:
        """
        获取资产列表，支持搜索、筛选和排序 - 优化版本
        """
        # 映射特定过滤器到 QueryBuilder 格式
        qb_filters = {}
        if filters:
            for key, value in filters.items():
                if key == "min_area":
                    qb_filters["min_actual_property_area"] = value
                elif key == "max_area":
                    qb_filters["max_actual_property_area"] = value
                elif key == "ids":
                    qb_filters["id__in"] = value
                else:
                    qb_filters[key] = value

        # 定义搜索字段
        search_fields = [
            "property_name",
            "address",
            "ownership_entity",
            "business_category",
        ]

        # 使用 CRUDBase (QueryBuilder) 获取数据
        # 注意：QueryBuilder 默认处理 skip/limit
        assets: list[Asset] = self.get_with_filters(
            db,
            filters=qb_filters,
            search=search,
            search_fields=search_fields,
            skip=skip,
            limit=limit,
            order_by=sort_field,
            order_desc=(sort_order.lower() == "desc"),
        )

        # 获取总数 (用于分页)
        cnt_query = self.query_builder.build_count_query(
            filters=qb_filters, search_query=search, search_fields=search_fields
        )
        total = db.execute(cnt_query).scalar() or 0

        return assets, total

    def create_with_history(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产并记录历史"""
        db_obj: Asset = self.create(db=db, obj_in=obj_in)

        history = AssetHistory(
            asset_id=db_obj.id,
            operation_type="CREATE",
            description=f"创建资产: {db_obj.property_name}",
            operator="system",
        )
        db.add(history)
        db.commit()
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate | dict[str, Any],
    ) -> Asset:
        """更新资产，增加版本号

        Note: Signature intentionally specializes generic CRUDBase.update for Asset type
        """
        # CRUDBase.update returns db_obj
        # We need to hook in before commit?
        # CRUDBase.update does commit.
        # So we should prepare data before calling super().update?

        # If we use super().update, we can't easily increment version inside the same atomic block unless we modify obj_in.
        if hasattr(db_obj, "version"):
            # Update version on the object before passing to super?
            # super().update updates from obj_in.
            # We can add version to obj_in?
            pass

        # To strictly follow "AssetCRUD" logic (version++), we might need to override completely
        # or rely on model events or adjust obj_in.

        # Let's use the explicit implementation for update to ensure version increment works
        if hasattr(db_obj, "version") and db_obj.version is not None:
            current_version = int(db_obj.version)
            db_obj.version = current_version + 1

        # Call super().update (which handles mapping obj_in to db_obj and commit)
        result: Asset = super().update(db=db, db_obj=db_obj, obj_in=obj_in)
        return result

    def update_with_history(
        self, db: Session, db_obj: Asset, obj_in: AssetUpdate
    ) -> Asset:
        """更新资产并记录历史"""
        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field, new_value in update_data.items():
            if hasattr(db_obj, field):
                old_value = getattr(db_obj, field)
                if old_value != new_value:
                    history = AssetHistory(
                        asset_id=db_obj.id,
                        operation_type="UPDATE",
                        field_name=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                        description=f"更新字段 {field}: {old_value} -> {new_value}",
                        operator="system",
                    )
                    db.add(history)

        return self.update(db=db, db_obj=db_obj, obj_in=obj_in)

    def get_multi_by_ids(self, db: Session, ids: list[str]) -> list[Asset]:
        """根据ID列表批量获取资产"""
        return self.get_with_filters(
            db, filters={"id__in": ids}, limit=len(ids) if ids else 100
        )

    # remove is inherited
    # create is inherited (check notes about calculation)


# 创建全局实例
asset_crud = AssetCRUD()
