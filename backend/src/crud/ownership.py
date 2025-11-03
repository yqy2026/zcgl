from typing import Any
"""
权属方相关CRUD操作
"""

from datetime import UTC, datetime


from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from ..models import Asset, Ownership, Project
from ..schemas.ownership import OwnershipCreate, OwnershipSearchRequest, OwnershipUpdate


class CRUDOwnership:
    """权属方CRUD操作类"""

    def get(self, db: Session, id: str) -> Ownership | None:
        """获取单个权属方"""
        ownership_obj = db.query(Ownership).filter(Ownership.id == id).first()
        if ownership_obj:
            # 临时禁用项目关联数据查询
            ownership_obj.project_relations_data = []

        return ownership_obj

    def get_by_name(self, db: Session, name: str) -> Ownership | None:
        """通过名称获取权属方"""
        return db.query(Ownership).filter(Ownership.name == name).first()

    def get_by_code(self, db: Session, code: str) -> Ownership | None:
        """通过编码获取权属方"""
        return db.query(Ownership).filter(Ownership.code == code).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        keyword: str | None = None,
    ) -> list[Ownership]:
        """获取多个权属方"""
        query = db.query(Ownership)

        # 应用过滤条件
        if is_active is not None:
            query = query.filter(Ownership.is_active == is_active)

        if keyword:
            query = query.filter(
                or_(
                    Ownership.name.contains(keyword),
                    Ownership.short_name.contains(keyword),
                    Ownership.code.contains(keyword),
                )
            )

        # 获取权属方列表
        ownerships = (
            query.order_by(desc(Ownership.created_at)).offset(skip).limit(limit).all()
        )

        # 临时禁用项目关联数据查询
        for ownership_obj in ownerships:
            ownership_obj.project_relations_data = []

        return ownerships

    def generate_ownership_code(self, db: Session, name: str = None) -> str:
        """生成权属方编码，采用与项目编码相同的独立自动生成方式

        编码规则：[前缀][年月][序号]
        示例：OW2501001（2025年1月第001个权属方）

        Args:
            db: 数据库会话
            name: 权属方名称（保留参数以兼容现有代码）

        Returns:
            str: 唯一的权属方编码
        """
        from datetime import datetime

        # 固定前缀
        prefix = "OW"

        # 获取当前年月
        current_date = datetime.now()
        year_month = current_date.strftime("%y%m")  # 如：2501

        # 构建基础编码格式
        base_format = f"{prefix}{year_month}"

        # 查询所有已存在的编码（包括新格式和旧格式）
        existing_codes = (
            db.query(Ownership.code)
            .filter(Ownership.code.like(f"{prefix}%"))
            .order_by(Ownership.code.desc())
            .all()
        )

        # 找到新格式的最大序列号
        max_sequence = 0
        for existing_code in existing_codes:
            code_str = existing_code[0]
            # 新格式：OW2509001 (9位)
            if (
                len(code_str) == 9
                and code_str[:2] == prefix
                and code_str[2:6].isdigit()
            ):
                try:
                    sequence = int(code_str[6:])
                    if sequence > max_sequence:
                        max_sequence = sequence
                except ValueError:
                    continue

        # 如果没有找到新格式编码，从1开始
        if max_sequence == 0:
            max_sequence = 0

        # 尝试生成唯一编码
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            attempts += 1
            sequence_num = max_sequence + attempts
            sequence_str = f"{sequence_num:03d}"
            code = f"{base_format}{sequence_str}"

            # 检查编码是否已存在
            if not self.get_by_code(db, code):
                return code

        # 如果所有尝试都失败了，返回一个基于时间戳的编码
        import time

        timestamp = int(time.time())
        code = f"{base_format}{timestamp % 1000:03d}"
        return code

    def create(self, db: Session, *, obj_in: OwnershipCreate) -> Ownership:
        """创建权属方"""
        # 检查名称是否已存在
        if self.get_by_name(db, obj_in.name):
            raise ValueError(f"权属方名称 {obj_in.name} 已存在")

        # 自动生成编码
        code = self.generate_ownership_code(db, obj_in.name)

        # 创建数据对象
        create_data = obj_in.model_dump()
        create_data["code"] = code
        db_obj = Ownership(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Ownership, obj_in: OwnershipUpdate
    ) -> Ownership:
        """更新权属方"""
        # 检查名称是否已被其他权属方使用
        if obj_in.name and obj_in.name != db_obj.name:
            existing = self.get_by_name(db, obj_in.name)
            if existing and existing.id != db_obj.id:
                raise ValueError(f"权属方名称 {obj_in.name} 已存在")

        # 检查编码是否已被其他权属方使用
        if obj_in.code and obj_in.code != db_obj.code:
            existing = self.get_by_code(db, obj_in.code)
            if existing and existing.id != db_obj.id:
                raise ValueError(f"权属方编码 {obj_in.code} 已存在")

        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: str) -> Ownership:
        """删除权属方"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise ValueError(f"权属方ID {id} 不存在")

        # 检查是否有关联的资产
        asset_count = (
            db.query(Asset).filter(Asset.ownership_entity == db_obj.name).count()
        )

        if asset_count > 0:
            raise ValueError(f"该权属方还有 {asset_count} 个关联资产，无法删除")

        db.delete(db_obj)
        db.commit()
        return db_obj

    def search(
        self, db: Session, search_params: OwnershipSearchRequest
    ) -> dict[str, Any]:
        """搜索权属方"""
        query = db.query(Ownership)

        # 应用过滤条件
        if search_params.keyword:
            query = query.filter(
                or_(
                    Ownership.name.contains(search_params.keyword),
                    Ownership.short_name.contains(search_params.keyword),
                    Ownership.code.contains(search_params.keyword),
                )
            )

        if search_params.is_active is not None:
            query = query.filter(Ownership.is_active == search_params.is_active)

        # 获取总数
        total = query.count()

        # 分页
        skip = (search_params.page - 1) * search_params.size
        items = (
            query.order_by(desc(Ownership.created_at))
            .offset(skip)
            .limit(search_params.size)
            .all()
        )

        # 计算页数
        pages = (total + search_params.size - 1) // search_params.size

        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "size": search_params.size,
            "pages": pages,
        }

    def get_statistics(self, db: Session) -> dict[str, Any]:
        """获取权属方统计信息"""
        # 基础统计
        total_count = db.query(Ownership).count()
        active_count = db.query(Ownership).filter(Ownership.is_active).count()
        inactive_count = total_count - active_count

        # 最近创建的权属方
        recent_created = (
            db.query(Ownership).order_by(desc(Ownership.created_at)).limit(5).all()
        )

        return {
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "recent_created": recent_created,
        }

    def get_asset_count(self, db: Session, ownership_id: str) -> int:
        """获取权属方关联的资产数量"""
        # 直接通过ownership_id字段查询资产数量
        return db.query(Asset).filter(Asset.ownership_id == ownership_id).count()

    def toggle_status(self, db: Session, *, id: str) -> Ownership:
        """切换权属方状态"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise ValueError(f"权属方ID {id} 不存在")

        db_obj.is_active = not db_obj.is_active
        db_obj.updated_at = datetime.now(UTC)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_project_count(self, db: Session, ownership_id: str) -> int:
        """获取权属方关联的项目数量"""
        try:
            from ..models import ProjectOwnershipRelation

            return (
                db.query(ProjectOwnershipRelation)
                .filter(
                    ProjectOwnershipRelation.ownership_id == ownership_id,
                    ProjectOwnershipRelation.is_active,
                )
                .count()
            )
        except Exception:
            # 如果查询失败，返回0
            return 0

    def update_related_projects(
        self, db: Session, *, ownership_id: str, project_ids: list[str]
    ) -> None:
        """更新权属方关联的项目"""
        # 验证权属方是否存在
        ownership_obj = self.get(db, id=ownership_id)
        if not ownership_obj:
            raise ValueError(f"权属方ID {ownership_id} 不存在")

        # 验证项目是否存在
        from ..models import ProjectOwnershipRelation

        valid_projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
        valid_project_ids = [p.id for p in valid_projects]

        if len(valid_project_ids) != len(project_ids):
            invalid_ids = set(project_ids) - set(valid_project_ids)
            raise ValueError(f"以下项目ID不存在: {invalid_ids}")

        # 删除现有关联
        db.query(ProjectOwnershipRelation).filter(
            ProjectOwnershipRelation.ownership_id == ownership_id
        ).delete()

        # 创建新关联
        for project_id in project_ids:
            relation = ProjectOwnershipRelation(
                project_id=project_id, ownership_id=ownership_id, is_active=True
            )
            db.add(relation)

        db.commit()


# 创建CRUD实例
ownership = CRUDOwnership()
