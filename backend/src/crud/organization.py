from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models.organization import Organization
from ..schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    """组织架构CRUD操作 - 支持敏感字段加密"""

    def __init__(self, model: type[Organization]) -> None:
        super().__init__(model)
        # Organization 模型的敏感字段（全部需要可搜索）
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "id_card",  # 身份证号 - 高度敏感，需要搜索
                "phone",  # 联系电话 - 敏感，需要搜索
                "leader_phone",  # 负责人电话 - 敏感，需要搜索
                "emergency_phone",  # 紧急联系电话 - 敏感，需要搜索
            }
        )

    def create(
        self, db: Session, *, obj_in: OrganizationCreate | dict[str, Any], **kwargs: Any
    ) -> Organization:
        """创建组织 - 加密敏感字段"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        # 加密敏感字段
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return super().create(db=db, obj_in=encrypted_data, **kwargs)

    def get(self, db: Session, id: Any, use_cache: bool = True) -> Organization | None:
        """获取组织 - 解密敏感字段"""
        result = super().get(db=db, id=id, use_cache=use_cache)
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> list[Organization]:
        """获取多个组织 - 解密敏感字段"""
        results = super().get_multi(
            db=db, skip=skip, limit=limit, use_cache=use_cache, **kwargs
        )
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results

    def update(
        self,
        db: Session,
        *,
        db_obj: Organization,
        obj_in: OrganizationUpdate | dict[str, Any],
        commit: bool = True,
    ) -> Organization:
        """更新组织 - 加密新的敏感字段值"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 加密敏感字段
        encrypted_data = self._encrypt_update_data(update_data)
        return super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )

    def _encrypt_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """加密更新数据中的敏感字段"""
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        parent_id: str | None = None,
        keyword: str | None = None,
    ) -> list[Organization]:
        """获取多个组织 - 解密敏感字段"""
        query = db.query(Organization).filter(Organization.is_deleted.is_(False))
        filters: dict[str, Any] = {}

        if parent_id:
            filters["parent_id"] = parent_id

        # Apply filters and search directly on query, then paginate
        if keyword:
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    Organization.name.ilike(f"%{keyword}%"),
                    Organization.description.ilike(f"%{keyword}%"),
                )
            )

        # Apply sorting
        query = query.order_by(Organization.level.asc(), Organization.sort_order.asc())

        # Apply pagination
        result: list[Organization] = query.offset(skip).limit(limit).all()

        # 解密敏感字段
        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    def get_tree(self, db: Session, parent_id: str | None = None) -> list[Organization]:
        """获取组织树形结构 - 解密敏感字段"""
        query = db.query(Organization).filter(
            and_(
                Organization.is_deleted.is_(False), Organization.parent_id == parent_id
            )
        )
        result: list[Organization] = query.order_by(
            Organization.sort_order, Organization.name
        ).all()

        # 解密敏感字段
        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    def get_children(
        self, db: Session, parent_id: str, recursive: bool = False
    ) -> list[Organization]:
        """获取子组织 - 解密敏感字段"""
        if not recursive:
            result = (
                db.query(Organization)
                .filter(
                    and_(
                        Organization.parent_id == parent_id,
                        Organization.is_deleted.is_(False),
                    )
                )
                .order_by(Organization.sort_order, Organization.name)
                .all()
            )
        else:
            # 递归获取所有子组织
            recursive_result: list[Organization] = []
            direct_children = self.get_children(db, parent_id, False)
            for child in direct_children:
                recursive_result.append(child)
                recursive_result.extend(self.get_children(db, str(child.id), True))
            result = recursive_result

        # 解密敏感字段
        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    def get_path_to_root(self, db: Session, org_id: str) -> list[Organization]:
        """获取到根节点的路径 - 已通过get()方法解密"""
        path: list[Organization] = []
        current: Organization | None = self.get(db, id=org_id)

        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.get(db, id=current.parent_id)
            else:
                break

        return path

    def search(
        self, db: Session, keyword: str, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        """搜索组织 - 已通过get_multi_with_filters()解密"""
        return self.get_multi_with_filters(db, skip=skip, limit=limit, keyword=keyword)


# 创建CRUD实例
organization = CRUDOrganization(Organization)
