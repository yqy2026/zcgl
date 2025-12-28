from typing import Any

"""
资产CRUD操作 - 优化版本
"""

from sqlalchemy import and_, asc, desc, or_
from sqlalchemy.orm import Session

from ..core.performance import cache_manager, cached, monitor_query
from ..models.asset import Asset, AssetHistory
from ..schemas.asset import AssetCreate, AssetUpdate
from ..services.asset.asset_calculator import AssetCalculator


class SensitiveDataHandler:
    """敏感数据处理器"""

    def encrypt_sensitive_data(self, data):
        """加密敏感数据"""

        # 在实际应用中，这里应该实现真正的数据加密逻辑

        # 例如使用AES加密算法

        return data


class AssetCRUD:
    """资产CRUD操作类 - 优化版本"""

    def __init__(self):
        self.sensitive_data_handler = SensitiveDataHandler()

    @monitor_query("asset_get_by_id")
    @cached(ttl=300)  # 5分钟缓存
    def get(self, db: Session, id: str) -> Asset | None:
        """根据ID获取资产"""
        return db.query(Asset).filter(Asset.id == id).first()

    def get_by_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()

    def get_by_property_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产（别名方法）"""
        return self.get_by_name(db, property_name)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Asset]:
        """获取多个资产"""
        return db.query(Asset).offset(skip).limit(limit).all()

    @monitor_query("asset_get_multi_with_search")
    @cached(ttl=600)  # 10分钟缓存
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

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数
            search: 搜索关键词
            filters: 筛选条件
            sort_field: 排序字段
            sort_order: 排序方向

        Returns:
            (资产列表, 总记录数)
        """
        # 构建缓存键
        cache_key = f"asset_list:{skip}:{limit}:{search}:{hash(str(filters))}:{sort_field}:{sort_order}"

        # 尝试从缓存获取总数
        cache_key_total = f"{cache_key}:total"
        cached_total = cache_manager.get(cache_key_total)
        if cached_total is not None:
            # 如果总数已缓存，直接查询数据
            query = self._build_optimized_search_query(
                db, search, filters, sort_field, sort_order
            )
            assets = query.offset(skip).limit(limit).all()
            return assets, cached_total

        # 构建查询
        query = self._build_optimized_search_query(
            db, search, filters, sort_field, sort_order
        )

        # 获取总数
        total = query.count()

        # 缓存总数
        cache_manager.set(cache_key_total, total, ttl=300)

        # 分页获取数据
        assets = query.offset(skip).limit(limit).all()

        return assets, total

    def _build_optimized_search_query(
        self,
        db: Session,
        search: str | None,
        filters: dict | None,
        sort_field: str,
        sort_order: str,
    ):
        """构建优化的搜索查询"""
        from ..models.asset import Asset

        query = db.query(Asset)

        # 搜索条件 - 使用索引友好的查询
        if search:
            search_terms = search.split()
            search_conditions = []

            for term in search_terms:
                search_filter = or_(
                    Asset.property_name.ilike(f"%{term}%"),
                    Asset.address.ilike(f"%{term}%"),
                    Asset.ownership_entity.ilike(f"%{term}%"),
                    Asset.business_category.ilike(f"%{term}%"),
                )
                search_conditions.append(search_filter)

            # 所有搜索条件用OR连接，提高性能
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        # 筛选条件 - 批量处理
        if filters:
            filter_conditions = []

            for key, value in filters.items():
                if value is None:
                    continue

                if key == "min_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area >= float(value))
                elif key == "max_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area <= float(value))
                elif key == "ids" and isinstance(value, list):
                    # 使用IN查询，性能更好
                    if value:
                        filter_conditions.append(Asset.id.in_(value))
                elif hasattr(Asset, key):
                    if isinstance(value, list):
                        filter_conditions.append(getattr(Asset, key).in_(value))
                    else:
                        filter_conditions.append(getattr(Asset, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # 排序 - 使用索引友好的字段
        sortable_fields = ["created_at", "updated_at", "property_name", "id", "actual_property_area"]
        if sort_field in sortable_fields:
            sort_column = getattr(Asset, sort_field)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        return query

    def get_filtered_query(
        self,
        db: Session,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ):
        """
        获取过滤后的查询对象（不执行查询）
        用于组织权限过滤
        """
        query = db.query(Asset)

        # 搜索条件
        if search:
            search_filter = or_(
                Asset.property_name.contains(search),
                Asset.address.contains(search),
                Asset.ownership_entity.contains(search),
                Asset.business_category.contains(search),
            )
            query = query.filter(search_filter)

        # 筛选条件
        if filters:
            filter_conditions = []

            for key, value in filters.items():
                if value is None:
                    continue

                if key == "min_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area >= float(value))
                elif key == "max_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area <= float(value))
                elif key == "ids" and isinstance(value, list):
                    # 支持按多个资产ID筛选
                    filter_conditions.append(Asset.id.in_(value))
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # 排序
        if hasattr(Asset, sort_field):
            sort_column = getattr(Asset, sort_field)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        return query

    def execute_paginated_query(
        self, query, skip: int = 0, limit: int = 100
    ) -> tuple[list[Asset], int]:
        """
        执行分页查询
        """
        total = query.count()
        assets = query.offset(skip).limit(limit).all()
        return assets, total

    def count(self, db: Session) -> int:
        """获取资产总数"""
        return db.query(Asset).count()

    def count_with_search(
        self,
        db: Session,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """获取符合条件的资产数量"""
        query = db.query(Asset)

        # 搜索条件
        if search:
            search_filter = or_(
                Asset.property_name.contains(search),
                Asset.address.contains(search),
                Asset.ownership_entity.contains(search),
                Asset.business_category.contains(search),
            )
            query = query.filter(search_filter)

        # 筛选条件
        if filters:
            filter_conditions = []

            for key, value in filters.items():
                if value is None:
                    continue

                if key == "min_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area >= float(value))
                elif key == "max_area" and hasattr(Asset, "actual_property_area"):
                    filter_conditions.append(Asset.actual_property_area <= float(value))
                elif key == "ids" and isinstance(value, list):
                    # 支持按多个资产ID筛选
                    filter_conditions.append(Asset.id.in_(value))
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        return query.count()

    def create(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产"""
        # 获取数据
        asset_data = obj_in.model_dump()  # 修复：使用model_dump而不是dict()

        # 敏感数据加密暂时跳过，避免复杂化
        # asset_data = self.sensitive_data_handler.encrypt_sensitive_data(asset_data)

        # 获取计算字段但不覆盖原始数据
        calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)

        # 合并原始数据和计算字段，但保持原始数据优先
        final_data = {**asset_data, **calculated_fields}

        # 验证数据一致性
        errors = AssetCalculator.validate_area_consistency(final_data)
        if errors:
            raise ValueError(f"数据验证失败: {'; '.join(errors)}")

        db_obj = Asset(**final_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_history(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产并记录历史"""
        # 创建资产
        db_obj = self.create(db=db, obj_in=obj_in)

        # 记录创建历史
        history = AssetHistory(
            asset_id=db_obj.id,
            operation_type="CREATE",
            description=f"创建资产: {db_obj.property_name}",
            operator="system",
        )
        db.add(history)
        db.commit()

        return db_obj

    def update(self, db: Session, db_obj: Asset, obj_in: AssetUpdate) -> Asset:
        """更新资产"""
        update_data = obj_in.dict(exclude_unset=True)

        # 加密敏感数据
        update_data = self.sensitive_data_handler.encrypt_sensitive_data(update_data)

        # 合并当前数据和更新数据进行计算
        current_data = {}
        for field in [
            "rentable_area",
            "rented_area",
            "annual_income",
            "annual_expense",
        ]:
            if hasattr(db_obj, field):
                current_data[field] = getattr(db_obj, field)

        # 合并更新数据
        current_data.update(update_data)

        # 自动计算相关字段
        calculated_data = AssetCalculator.auto_calculate_fields(current_data)

        # 验证数据一致性
        errors = AssetCalculator.validate_area_consistency(calculated_data)
        if errors:
            raise ValueError(f"数据验证失败: {'; '.join(errors)}")

        # 首先更新原始数据中的字段
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        # 然后更新计算得出的字段
        for field, value in calculated_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        # 更新版本号
        if hasattr(db_obj, "version"):
            db_obj.version = (db_obj.version or 0) + 1

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_with_history(
        self, db: Session, db_obj: Asset, obj_in: AssetUpdate
    ) -> Asset:
        """更新资产并记录历史"""
        update_data = obj_in.dict(exclude_unset=True)

        # 记录变更历史
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

        # 更新资产
        updated_asset = self.update(db=db, db_obj=db_obj, obj_in=obj_in)
        db.commit()

        return updated_asset

    def get_multi_by_ids(self, db: Session, ids: list[str]) -> list[Asset]:
        """根据ID列表批量获取资产"""
        if not ids:
            return []
        return db.query(Asset).filter(Asset.id.in_(ids)).all()

    def remove(self, db: Session, id: str) -> Asset:
        """删除资产"""
        obj = db.query(Asset).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# 创建全局实例
asset_crud = AssetCRUD()
