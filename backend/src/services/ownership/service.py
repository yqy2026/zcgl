from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.asset import asset_crud
from ...crud.ownership import ownership as ownership_crud
from ...crud.project import project_crud
from ...models.ownership import Ownership
from ...models.project_relations import ProjectOwnershipRelation
from ...schemas.ownership import OwnershipCreate, OwnershipUpdate


class OwnershipService:
    """权属方服务层"""

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def get_ownership(
        self, db: AsyncSession, *, ownership_id: str
    ) -> Ownership | None:
        return await ownership_crud.get(db, id=ownership_id)

    async def generate_ownership_code(self, db: AsyncSession) -> str:
        """生成权属方编码

        编码规则：[前缀][年月][序号]
        示例：OW2501001（2025年1月第001个权属方）
        """
        # 固定前缀
        prefix = "OW"

        # 获取当前年月
        current_date = datetime.now()
        year_month = current_date.strftime("%y%m")  # 如：2501

        # 构建基础编码格式
        base_format = f"{prefix}{year_month}"

        # 查询所有已存在的编码（包括新格式和旧格式）
        # 查询现有编码
        existing_codes = await ownership_crud.get_codes_by_prefix_async(db, prefix)

        # 找到新格式的最大序列号
        max_sequence = 0
        for code_str in existing_codes:
            if code_str is None:
                continue
            # 新格式：OW2501001 (9位)
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

        # 生成下一个序列号
        next_sequence = max_sequence + 1

        # 尝试生成唯一编码（通常不需要循环，但为了安全保留逻辑）
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            sequence_str = f"{next_sequence:03d}"
            code = f"{base_format}{sequence_str}"

            # 检查编码是否已存在
            if not await ownership_crud.get_by_code(db, code):
                return code

            next_sequence += 1
            attempts += 1

        # 兜底：使用时间戳
        return f"{base_format}{int(datetime.now().timestamp() % 1000):03d}"

    async def create_ownership(
        self, db: AsyncSession, *, obj_in: OwnershipCreate
    ) -> Ownership:
        """创建权属方"""
        # 检查名称是否已存在
        if await ownership_crud.get_by_name(db, obj_in.name):
            raise DuplicateResourceError("权属方", "name", obj_in.name)

        # 自动生成编码
        code = await self.generate_ownership_code(db)

        # 创建数据对象
        create_data = obj_in.model_dump()
        create_data["code"] = code

        return await ownership_crud.create(db, obj_in=create_data)

    async def update_ownership(
        self, db: AsyncSession, *, db_obj: Ownership, obj_in: OwnershipUpdate
    ) -> Ownership:
        """更新权属方"""
        # 检查名称是否已被其他权属方使用
        if obj_in.name and obj_in.name != db_obj.name:
            existing = await ownership_crud.get_by_name(db, obj_in.name)
            if existing and existing.id != db_obj.id:
                raise DuplicateResourceError("权属方", "name", obj_in.name)

        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = self._utcnow_naive()

        return await ownership_crud.update(db, db_obj=db_obj, obj_in=update_data)

    async def update_ownership_by_id(
        self, db: AsyncSession, *, ownership_id: str, obj_in: OwnershipUpdate
    ) -> Ownership:
        db_obj = await self.get_ownership(db, ownership_id=ownership_id)
        if not db_obj:
            raise ResourceNotFoundError("权属方", ownership_id)
        return await self.update_ownership(db, db_obj=db_obj, obj_in=obj_in)

    async def search_ownerships(
        self, db: AsyncSession, *, search_params: Any
    ) -> dict[str, Any]:
        return await ownership_crud.search(db, search_params)

    async def get_statistics(self, db: AsyncSession) -> dict[str, Any]:
        """获取权属方统计信息"""
        stats = await ownership_crud.get_statistics_async(db)
        recent_created = await ownership_crud.get_recent_created_async(db, limit=5)

        return {
            **stats,
            "recent_created": recent_created,
        }

    async def update_related_projects(
        self, db: AsyncSession, *, ownership_id: str, project_ids: list[str]
    ) -> None:
        """更新权属方关联的项目"""
        # 验证权属方是否存在
        ownership_obj = await ownership_crud.get(db, id=ownership_id)
        if not ownership_obj:
            raise ResourceNotFoundError("权属方", ownership_id)

        # 验证项目是否存在
        valid_projects: list[str] = []
        if project_ids:
            valid_projects = await project_crud.get_ids_by_filter_async(db, project_ids)
        valid_project_ids = [str(p_id) for p_id in valid_projects]

        if len(valid_project_ids) != len(project_ids):
            invalid_ids = set(project_ids) - set(valid_project_ids)
            raise BusinessValidationError(
                f"以下项目ID不存在: {invalid_ids}",
                field_errors={"project_ids": [str(i) for i in invalid_ids]},
            )

        # 删除现有关联
        await ownership_crud.delete_project_relations_async(db, ownership_id)

        # 创建新关联
        for project_id in project_ids:
            relation = ProjectOwnershipRelation()
            relation.project_id = project_id
            relation.ownership_id = ownership_id
            relation.is_active = True
            db.add(relation)

        await db.commit()

    async def get_project_count(self, db: AsyncSession, ownership_id: str) -> int:
        """获取权属方关联的项目数量"""
        return await ownership_crud.count_projects_async(db, ownership_id)

    async def get_asset_count(self, db: AsyncSession, ownership_id: str) -> int:
        """获取权属方关联的资产数量"""
        return await asset_crud.count_by_ownership_async(db, ownership_id)

    async def delete_ownership(self, db: AsyncSession, *, id: str) -> Ownership:
        """删除权属方"""
        db_obj = await ownership_crud.get(db, id=id)
        if not db_obj:
            raise ResourceNotFoundError("权属方", id)

        # 检查是否有关联的资产
        asset_count = await asset_crud.count_by_ownership_async(db, str(db_obj.id))

        if asset_count > 0:
            raise OperationNotAllowedError(
                f"该权属方还有 {asset_count} 个关联资产，无法删除",
                reason="ownership_has_assets",
            )

        await ownership_crud.remove(db, id=id)
        return db_obj

    async def toggle_status(
        self,
        db: AsyncSession,
        *,
        id: str,
        name: str | None = None,
        code: str | None = None,
    ) -> Ownership:
        """切换权属方状态"""
        db_obj = await ownership_crud.get(db, id=id)
        if not db_obj:
            raise ResourceNotFoundError("权属方", id)

        # Convert Column[str] to str using getattr
        obj_name: str | None = name or getattr(db_obj, "name", None)
        obj_code: str | None = code or getattr(db_obj, "code", None)
        obj_short_name: str | None = getattr(db_obj, "short_name", None)

        update_in = OwnershipUpdate(
            name=obj_name,
            code=obj_code,
            short_name=obj_short_name,
            is_active=not db_obj.is_active,
        )
        return await self.update_ownership(db, db_obj=db_obj, obj_in=update_in)

    async def get_ownership_dropdown_options(
        self, db: AsyncSession, is_active: bool | None = True
    ) -> list[dict[str, Any]]:
        """获取权属方下拉选项列表"""
        # 批量查询权属方
        ownerships = await ownership_crud.get_multi_for_select_async(
            db, is_active=is_active, limit=1000
        )
        if not ownerships:
            return []

        ownership_ids = [item.id for item in ownerships if item.id is not None]
        if not ownership_ids:
            return []

        # 批量获取资产计数（按权属方分组）
        asset_counts = await asset_crud.get_counts_by_ownerships_async(db, ownership_ids)

        # 批量获取项目计数（按权属方分组）
        project_counts = await ownership_crud.get_project_counts_by_ownerships_async(
            db, ownership_ids
        )

        responses = []
        for item in ownerships:
            item_id = str(item.id)
            responses.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "code": item.code,
                    "short_name": item.short_name,
                    "is_active": item.is_active,
                    "data_status": item.data_status,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "asset_count": asset_counts.get(item_id, 0),
                    "project_count": project_counts.get(item_id, 0),
                }
            )
        return responses


ownership_service = OwnershipService()
