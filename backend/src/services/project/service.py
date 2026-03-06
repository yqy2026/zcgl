import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from pinyin import get as get_pinyin
except ImportError:

    def get_pinyin(*args: Any, **kwargs: Any) -> Any:
        return None


from ...constants.business_constants import DataStatusValues
from ...core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.asset import asset_crud
from ...crud.project import project_crud
from ...crud.project_asset import project_asset_crud
from ...crud.query_builder import PartyFilter
from ...models import Asset, Project
from ...schemas.project import (
    ProjectAssetSummary,
    ProjectCreate,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectUpdate,
)
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class ProjectService:
    """项目服务层"""

    @staticmethod
    def project_to_response(project: Project) -> ProjectResponse:
        """
        将 Project 模型转换为 ProjectResponse。

        这个方法封装了模型到响应 Schema 的转换逻辑，
        确保所有属性都被正确提取和格式化。

        Args:
            project: Project 模型实例

        Returns:
            ProjectResponse: 转换后的响应 Schema
        """
        # 交由 ProjectResponse 的 model_validator 处理关系字段懒加载安全与兼容转换
        return ProjectResponse.model_validate(project)

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return (
            len(
                [
                    org_id
                    for org_id in party_filter.party_ids
                    if str(org_id).strip() != ""
                ]
            )
            == 0
        )

    @staticmethod
    def _as_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal(0)
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal(0)

    @staticmethod
    def _normalize_owner_party_relations(
        party_relations: list[Any] | None,
    ) -> list[dict[str, Any]]:
        if party_relations is None:
            return []

        normalized_relations: list[dict[str, Any]] = []
        seen_party_ids: set[str] = set()
        for relation in party_relations:
            if isinstance(relation, dict):
                party_id_raw = relation.get("party_id")
                relation_type_raw = relation.get("relation_type", "owner")
                is_active_raw = relation.get("is_active", True)
            else:
                party_id_raw = getattr(relation, "party_id", None)
                relation_type_raw = getattr(relation, "relation_type", "owner")
                is_active_raw = getattr(relation, "is_active", True)

            party_id = str(party_id_raw).strip() if party_id_raw is not None else ""
            if party_id == "" or party_id in seen_party_ids:
                continue

            relation_type = str(relation_type_raw).strip()
            if relation_type != "owner":
                continue

            seen_party_ids.add(party_id)
            normalized_relations.append(
                {
                    "party_id": party_id,
                    "is_active": bool(is_active_raw),
                }
            )

        return normalized_relations

    async def _replace_project_owner_relations(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        party_relations: list[Any] | None,
        operator_id: str | None = None,
    ) -> None:
        normalized_relations = self._normalize_owner_party_relations(party_relations)
        if len(normalized_relations) == 0:
            return

        # Legacy relation table `project_ownership_relations` has been removed by migrations.
        # Keep accepting party_relations at API boundary, but do not persist into dropped schema.
        logger.warning(
            "Skip persisting project owner relations to removed legacy table: project_id=%s relation_count=%s operator=%s",
            project_id,
            len(normalized_relations),
            operator_id,
        )

    async def _resolve_party_filter(
        self,
        db: AsyncSession,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    async def create_project(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate,
        created_by: str | None = None,
        organization_id: str | None = None,  # DEPRECATED alias
    ) -> Project:
        """创建项目"""
        try:
            # 1. 生成项目编码 (如果未提供)
            if not obj_in.project_code:
                obj_in.project_code = await self.generate_project_code(db, obj_in.project_name)

            # 2. 检查编码唯一性
            existing_project = await project_crud.get_by_code(db, code=obj_in.project_code)
            if existing_project:
                raise DuplicateResourceError("项目", "project_code", obj_in.project_code)

            # 3. 创建项目
            project: Project = await project_crud.create(
                db,
                obj_in=obj_in,
                created_by=created_by,
                organization_id=organization_id,  # DEPRECATED alias
                commit=False,
            )
            await self._replace_project_owner_relations(
                db,
                project_id=str(project.id),
                party_relations=obj_in.party_relations,
                operator_id=created_by,
            )
            await db.commit()
            await db.refresh(project)
            return project

        except Exception as e:
            if isinstance(e, BaseBusinessError):
                raise
            raise InternalServerError("创建项目失败", original_error=e) from e

    async def update_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        obj_in: ProjectUpdate,
        updated_by: str | None = None,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Project:
        """更新项目"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)

        project: Project | None = await project_crud.get(
            db,
            id=project_id,
            party_filter=resolved_party_filter,
        )
        if not project:
            raise ResourceNotFoundError("项目", project_id)

        party_relations_provided = "party_relations" in obj_in.model_fields_set
        result: Project = await project_crud.update(
            db,
            db_obj=project,
            obj_in=obj_in,
            commit=False,
        )
        if party_relations_provided:
            await self._replace_project_owner_relations(
                db,
                project_id=str(result.id),
                party_relations=obj_in.party_relations,
                operator_id=updated_by,
            )
        await db.commit()
        await db.refresh(result)
        return result

    async def toggle_status(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        updated_by: str | None = None,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Project:
        """切换项目状态"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)

        project: Project | None = await project_crud.get(
            db,
            id=project_id,
            party_filter=resolved_party_filter,
        )
        if not project:
            raise ResourceNotFoundError("项目", project_id)

        # Toggle logic: 按英文枚举切换状态
        if project.status in ("planning", "active"):
            project.status = "paused"
        elif project.status == "paused":
            project.status = "active"
        else:
            project.status = "active"

        project.updated_by = updated_by
        project.updated_at = self._utcnow_naive()
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def delete_project(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> None:
        """删除项目"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)

        count = await project_crud.get_asset_count(db, project_id)
        if count > 0:
            raise OperationNotAllowedError(
                f"项目包含 {count} 个资产，无法删除",
                reason="project_has_assets",
            )

        # Use remove instead of delete
        project = await project_crud.get(
            db,
            id=project_id,
            party_filter=resolved_party_filter,
        )
        if project:
            await project_crud.remove(db, id=project_id)

    async def generate_project_code(
        self, db: AsyncSession, name: str | None = None
    ) -> str:
        """生成项目编码，格式：PRJ-YYYYMM-NNNNNN"""
        segment = datetime.now().strftime("%Y%m")
        prefix = f"PRJ-{segment}-"
        last_project = await project_crud.get_latest_by_code_prefix(db, prefix=prefix)

        if last_project:
            try:
                seq = int(last_project.project_code[-6:])
                next_seq = seq + 1
            except (ValueError, IndexError, TypeError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:06d}"

    async def search_projects(
        self,
        db: AsyncSession,
        search_params: ProjectSearchRequest,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            items: list[Project] = []
            total = 0
        else:
            items, total = await project_crud.search(
                db,
                search_params,
                party_filter=resolved_party_filter,
            )
        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "page_size": search_params.page_size,
            "pages": (total + search_params.page_size - 1) // search_params.page_size,
        }

    async def get_project_dropdown_options(
        self,
        db: AsyncSession,
        status: str | None = "active",
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取项目下拉选项列表"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return []

        normalized_status = None if status is None else str(status).strip()
        status_filter = normalized_status if normalized_status else None
        projects = await project_crud.get_multi(
            db,
            skip=0,
            limit=1000,
            status=status_filter,
            party_filter=resolved_party_filter,
        )
        projects.sort(key=lambda project: str(project.project_name or ""))
        return [
            {
                "id": p.id,
                "project_name": p.project_name,
                "project_code": p.project_code,
            }
            for p in projects
        ]

    async def get_project_statistics(
        self,
        db: AsyncSession,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> dict[str, Any]:
        """获取项目统计信息。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return {"total_projects": 0, "active_projects": 0}

        return await project_crud.get_statistics(
            db=db,
            party_filter=resolved_party_filter,
        )

    async def get_project_active_assets(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
    ) -> tuple[list[Asset], ProjectAssetSummary]:
        """获取项目当前有效关联资产列表及面积汇总。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=None,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)

        project = await self.get_project_by_id(
            db,
            project_id=project_id,
            party_filter=resolved_party_filter,
        )
        if project is None:
            raise ResourceNotFoundError("项目", project_id)

        project_assets = await project_asset_crud.get_project_assets(
            db,
            project_id=project_id,
            active_only=True,
        )
        active_project_assets = [
            relation
            for relation in project_assets
            if getattr(relation, "valid_to", None) is None
        ]
        asset_ids = list(
            {
                str(relation.asset_id)
                for relation in active_project_assets
                if str(getattr(relation, "asset_id", "")).strip() != ""
            }
        )

        if len(asset_ids) == 0:
            return [], ProjectAssetSummary(
                total_assets=0,
                total_rentable_area=0.0,
                total_rented_area=0.0,
                occupancy_rate=0.0,
            )

        assets = await asset_crud.get_multi_by_ids_async(
            db,
            ids=asset_ids,
            include_deleted=False,
        )

        asset_by_id: dict[str, Asset] = {}
        for asset in assets:
            if getattr(asset, "data_status", None) != DataStatusValues.ASSET_NORMAL:
                continue
            asset_id = str(getattr(asset, "id", "")).strip()
            if asset_id == "":
                continue
            asset_by_id[asset_id] = asset

        ordered_assets = [
            asset_by_id[asset_id] for asset_id in asset_ids if asset_id in asset_by_id
        ]

        total_rentable_area = sum(
            (self._as_decimal(getattr(asset, "rentable_area", None)) for asset in ordered_assets),
            start=Decimal(0),
        )
        total_rented_area = sum(
            (self._as_decimal(getattr(asset, "rented_area", None)) for asset in ordered_assets),
            start=Decimal(0),
        )
        if total_rentable_area == Decimal(0):
            occupancy_rate = 0.0
        else:
            occupancy_decimal = (
                (total_rented_area / total_rentable_area) * Decimal(100)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            occupancy_rate = float(occupancy_decimal)

        summary = ProjectAssetSummary(
            total_assets=len(ordered_assets),
            total_rentable_area=float(total_rentable_area),
            total_rented_area=float(total_rented_area),
            occupancy_rate=occupancy_rate,
        )
        return ordered_assets, summary

    async def get_project_by_id(
        self,
        db: AsyncSession,
        project_id: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Project | None:
        """根据 ID 获取项目。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return None

        return await project_crud.get(
            db=db,
            id=project_id,
            party_filter=resolved_party_filter,
        )


project_service = ProjectService()
