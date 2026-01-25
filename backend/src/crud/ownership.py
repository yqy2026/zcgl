from typing import Any

from sqlalchemy.orm import Session

from ..crud.base import CRUDBase
from ..models.asset import Ownership
from ..schemas.ownership import OwnershipCreate, OwnershipUpdate


class CRUDOwnership(CRUDBase[Ownership, OwnershipCreate, OwnershipUpdate]):
    """权属方CRUD操作类"""

    def get(self, db: Session, id: Any, use_cache: bool = True) -> Ownership | None:
        """获取单个权属方"""
        ownership_obj = super().get(db, id=id)
        if ownership_obj:
            # 临时禁用项目关联数据查询
            setattr(ownership_obj, "project_relations_data", [])

        return ownership_obj

    def get_by_name(self, db: Session, name: str) -> Ownership | None:
        """通过名称获取权属方"""
        return db.query(Ownership).filter(Ownership.name == name).first()

    def get_by_code(self, db: Session, code: str) -> Ownership | None:
        """通过编码获取权属方"""
        return db.query(Ownership).filter(Ownership.code == code).first()

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        keyword: str | None = None,
    ) -> list[Ownership]:
        """获取多个权属方"""
        filters = {}

        # 构造过滤条件
        if is_active is not None:
            filters["is_active"] = is_active

        # 构建基础查询
        stmt = self.query_builder.build_query(
            filters=filters,
            search_query=keyword,
            search_fields=["name", "short_name", "code"],
            sort_by="created_at",
            sort_desc=True,
            skip=skip,
            limit=limit,
        )

        # 执行查询
        result = db.execute(stmt)
        items = result.scalars().all()

        # 临时禁用项目关联数据查询
        for item in items:
            item.project_relations_data = []

        return list(items)

    def search(self, db: Session, search_params: Any) -> dict[str, Any]:
        """搜索权属方"""
        # 使用QueryBuilder通过get_multi_with_filters逻辑，或直接构建查询
        # 这里为了兼容性保持返回 dict 结构
        # 但 logic should use query_builder logic

        skip = (search_params.page - 1) * search_params.page_size
        limit = search_params.page_size

        filters = {}
        if search_params.is_active is not None:
            filters["is_active"] = search_params.is_active

        stmt = self.query_builder.build_query(
            filters=filters,
            search_query=search_params.keyword,
            search_fields=["name", "short_name", "code"],
            sort_by="created_at",
            sort_desc=True,
            skip=skip,
            limit=limit,
        )

        # Count
        count_stmt = self.query_builder.build_count_query(
            filters=filters,
            search_query=search_params.keyword,
            search_fields=["name", "short_name", "code"],
        )
        total = db.scalar(count_stmt) or 0

        result = db.execute(stmt)
        items = list(result.scalars().all())

        pages = (total + limit - 1) // limit

        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "page_size": limit,
            "pages": pages,
        }


# 创建CRUD实例
ownership = CRUDOwnership(Ownership)
