import logging
from datetime import UTC, date, datetime, timedelta
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
from ...crud.contract import contract_crud
from ...crud.contract_group import contract_group_crud
from ...crud.party import party_crud
from ...crud.project import project_crud
from ...crud.project_asset import project_asset_crud
from ...crud.property_certificate import property_certificate_crud
from ...crud.query_builder import PartyFilter
from ...models import Asset, Project
from ...models.contract_group import (
    ContractLifecycleStatus,
    GroupRelationType,
    RevenueMode,
)
from ...schemas.project import (
    ProjectAnalysisModeSummary,
    ProjectAnalyticsResponse,
    ProjectAssetSummary,
    ProjectContractRelationItem,
    ProjectContractRelationsResponse,
    ProjectCreate,
    ProjectLedgerMetricGroup,
    ProjectLedgerSummaryResponse,
    ProjectMonthlyTrendItem,
    ProjectOperatingResultSummary,
    ProjectResponse,
    ProjectRiskItem,
    ProjectRisksResponse,
    ProjectSearchRequest,
    ProjectTenantSummaryItem,
    ProjectTenantSummaryResponse,
    ProjectUpdate,
)
from ...services.code_segments import build_party_code_segment
from ...services.contract.contract_group_service import calculate_derived_status
from ...services.contract.ledger_scope import is_resource_in_scope
from ...services.contract.ledger_service_v2 import (
    find_stale_paid_or_partial_ledger_entries,
)
from ...services.contract.service_fee_ledger_service import service_fee_ledger_service
from ...services.party_scope import resolve_user_party_filter
from ...services.property_certificate.risks import (
    AssetOwnerSnapshot,
    HolderRelationSnapshot,
    calculate_holder_owner_mismatch,
    calculate_incomplete_certificate_info,
)

logger = logging.getLogger(__name__)


def _certificate_asset_snapshots(
    certificate: Any, active_asset_by_id: dict[str, Any]
) -> list[AssetOwnerSnapshot]:
    """Project-active assets linked to the certificate, as risk snapshots."""
    return [
        AssetOwnerSnapshot(
            asset_id=asset_id,
            owner_party_id=getattr(asset, "owner_party_id", None),
            asset_name=(
                getattr(asset, "asset_name", None) or getattr(asset, "name", None)
            ),
        )
        for asset_id, asset in active_asset_by_id.items()
        if any(
            str(getattr(linked_asset, "id", "") or "").strip() == asset_id
            for linked_asset in certificate.assets
        )
    ]


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
    def _normalize_revenue_mode(raw: Any) -> RevenueMode:
        if isinstance(raw, RevenueMode):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip()
            if normalized != "":
                try:
                    return RevenueMode[normalized.upper()]
                except KeyError:
                    for member in RevenueMode:
                        if normalized == member.value:
                            return member
        raise OperationNotAllowedError(f"不支持的经营模式: {raw}")

    @staticmethod
    def _normalize_group_relation_type(raw: Any) -> GroupRelationType | None:
        if isinstance(raw, GroupRelationType):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip()
            if normalized != "":
                try:
                    return GroupRelationType[normalized.upper()]
                except KeyError:
                    for member in GroupRelationType:
                        if normalized == member.value:
                            return member
        return None

    @staticmethod
    def _relation_kind_from_revenue_mode(revenue_mode: RevenueMode) -> str:
        if revenue_mode == RevenueMode.LEASE:
            return "lease_sublease"
        return "agency_operation"

    @staticmethod
    def _contract_from_ledger_entry(entry: Any) -> Any | None:
        return getattr(entry, "contract", None) or getattr(
            entry,
            "agency_contract",
            None,
        )

    @staticmethod
    def _group_from_ledger_entry(entry: Any) -> Any | None:
        contract = ProjectService._contract_from_ledger_entry(entry)
        return (
            getattr(contract, "contract_group", None) if contract is not None else None
        )

    @classmethod
    def _ledger_entry_context(cls, entry: Any) -> tuple[RevenueMode, GroupRelationType]:
        contract = cls._contract_from_ledger_entry(entry)
        group = (
            getattr(contract, "contract_group", None) if contract is not None else None
        )
        revenue_mode = cls._normalize_revenue_mode(getattr(group, "revenue_mode", None))
        relation_type = cls._normalize_group_relation_type(
            getattr(contract, "group_relation_type", None)
        )
        if relation_type is None:
            raise OperationNotAllowedError(
                "台账条目缺少合同关系类型，无法聚合项目历史口径"
            )
        return revenue_mode, relation_type

    @staticmethod
    def _asset_ids_from_group(group: Any) -> list[str]:
        asset_ids: list[str] = []
        for asset in getattr(group, "assets", None) or []:
            asset_id = getattr(asset, "id", None)
            if asset_id is None:
                asset_id = getattr(asset, "asset_id", None)
            normalized_asset_id = str(asset_id).strip() if asset_id is not None else ""
            if normalized_asset_id != "":
                asset_ids.append(normalized_asset_id)
        return asset_ids

    @staticmethod
    def _asset_ids_from_contract(contract: Any) -> set[str]:
        asset_ids: set[str] = set()
        for asset in getattr(contract, "assets", None) or []:
            asset_id = getattr(asset, "id", None)
            if asset_id is None:
                asset_id = getattr(asset, "asset_id", None)
            normalized_asset_id = str(asset_id).strip() if asset_id is not None else ""
            if normalized_asset_id != "":
                asset_ids.add(normalized_asset_id)
        return asset_ids

    @classmethod
    def _contract_relation_item_from_group(
        cls,
        *,
        group: Any,
        contracts: list[Any],
    ) -> ProjectContractRelationItem:
        revenue_mode = cls._normalize_revenue_mode(getattr(group, "revenue_mode", None))
        primary_types = (
            {GroupRelationType.UPSTREAM}
            if revenue_mode == RevenueMode.LEASE
            else {GroupRelationType.ENTRUSTED}
        )
        terminal_types = (
            {GroupRelationType.DOWNSTREAM}
            if revenue_mode == RevenueMode.LEASE
            else {GroupRelationType.DIRECT_LEASE}
        )

        primary_contract_ids: list[str] = []
        terminal_contract_ids: list[str] = []
        for contract in contracts:
            relation_type = cls._normalize_group_relation_type(
                getattr(contract, "group_relation_type", None)
            )
            contract_id = str(getattr(contract, "contract_id", "")).strip()
            if contract_id == "":
                continue
            if relation_type in primary_types:
                primary_contract_ids.append(contract_id)
            elif relation_type in terminal_types:
                terminal_contract_ids.append(contract_id)

        group_code = str(getattr(group, "group_code", "")).strip()
        display_name = (
            group_code or str(getattr(group, "contract_group_id", "")).strip()
        )

        return ProjectContractRelationItem(
            contract_relation_id=str(getattr(group, "contract_group_id")),
            project_id=str(getattr(group, "project_id")),
            display_name=display_name,
            revenue_mode=revenue_mode.value,
            relation_kind=cls._relation_kind_from_revenue_mode(revenue_mode),
            owner_party_id=str(getattr(group, "owner_party_id")),
            operator_party_id=str(getattr(group, "operator_party_id")),
            asset_ids=cls._asset_ids_from_group(group),
            primary_contract_ids=primary_contract_ids,
            terminal_contract_ids=terminal_contract_ids,
            derived_status=calculate_derived_status(contracts),
            risk_tags=getattr(group, "risk_tags", None),
        )

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

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
    def _has_active_ledger_allocation(entry: Any) -> bool:
        try:
            return int(getattr(entry, "active_allocation_count", 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    @classmethod
    def _unpaid_amount_from_entry(cls, entry: Any) -> Decimal:
        amount_due = cls._as_decimal(getattr(entry, "amount_due", None))
        paid_amount = cls._as_decimal(getattr(entry, "paid_amount", None))
        return max(amount_due - paid_amount, Decimal(0))

    @classmethod
    def _overdue_amount_from_entry(cls, entry: Any, today: date) -> Decimal:
        payment_status = str(getattr(entry, "payment_status", "") or "").strip()
        due_date = getattr(entry, "due_date", None)
        if not isinstance(due_date, date):
            due_date = getattr(getattr(entry, "source_ledger", None), "due_date", None)
        if (
            payment_status == "voided"
            or not isinstance(due_date, date)
            or due_date >= today
        ):
            return Decimal(0)
        return cls._unpaid_amount_from_entry(entry)

    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _empty_mode_amounts() -> dict[str, Decimal]:
        return {
            "receivable_amount": Decimal(0),
            "payable_amount": Decimal(0),
            "received_amount": Decimal(0),
            "paid_amount": Decimal(0),
            "overdue_amount": Decimal(0),
        }

    @staticmethod
    def _empty_ledger_metric_group() -> dict[str, Decimal]:
        return {
            "amount_due": Decimal(0),
            "paid_amount": Decimal(0),
            "overdue_amount": Decimal(0),
        }

    @staticmethod
    def _ledger_views(entry: Any) -> set[str]:
        raw_views = getattr(entry, "ledger_views", []) or []
        if isinstance(raw_views, str):
            raw_views = [raw_views]
        return {str(getattr(view, "value", view)).strip() for view in raw_views}

    @classmethod
    def _ledger_metric_group_response(
        cls,
        amounts: dict[str, Decimal],
    ) -> ProjectLedgerMetricGroup:
        amount_due = cls._quantize_money(amounts["amount_due"])
        paid_amount = cls._quantize_money(amounts["paid_amount"])
        return ProjectLedgerMetricGroup(
            amount_due=amount_due,
            paid_amount=paid_amount,
            outstanding_amount=cls._quantize_money(
                max(amount_due - paid_amount, Decimal(0))
            ),
            overdue_amount=cls._quantize_money(amounts["overdue_amount"]),
        )

    @staticmethod
    def _empty_trend_amounts() -> dict[str, Decimal]:
        return {
            "receivable_amount": Decimal(0),
            "payable_amount": Decimal(0),
            "received_amount": Decimal(0),
            "paid_amount": Decimal(0),
            "overdue_amount": Decimal(0),
        }

    @staticmethod
    def _year_month_from_entry(entry: Any) -> str:
        year_month = str(getattr(entry, "year_month", "") or "").strip()
        if year_month != "":
            return year_month
        due_date = getattr(entry, "due_date", None)
        if isinstance(due_date, date):
            return due_date.strftime("%Y-%m")
        return "unknown"

    @staticmethod
    def _party_name_from_contract(contract: Any) -> str:
        party = getattr(contract, "lessee_party", None)
        for attr in ("name", "party_name", "display_name"):
            value = getattr(party, attr, None) if party is not None else None
            normalized = str(value).strip() if value is not None else ""
            if normalized != "":
                return normalized
        return str(getattr(contract, "lessee_party_id", "") or "").strip()

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
        _ = db, project_id, operator_id
        if party_relations is not None:
            raise OperationNotAllowedError(
                "项目 party_relations 写入口已下线；项目主体关系由产权/运营方字段派生，禁止通过该字段写入",
                reason="project_party_relations_write_removed",
            )

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

    async def _resolve_operator_party_for_code(
        self, db: AsyncSession, obj_in: ProjectCreate
    ) -> tuple[str | None, str | None]:
        operator_party_id = (
            obj_in.manager_party_id or obj_in.organization_id or ""
        ).strip()
        if operator_party_id == "":
            raise OperationNotAllowedError(
                "自动生成 project_code 必须提供运营方 manager_party_id",
                reason="project_operator_required_for_code",
            )

        party = await party_crud.get_party(db, party_id=operator_party_id)
        if party is None:
            raise ResourceNotFoundError("运营方主体", operator_party_id)
        party_code = str(getattr(party, "code", "") or "").strip()
        if party_code == "":
            raise OperationNotAllowedError(
                "自动生成 project_code 的运营方必须配置 party.code",
                reason="project_operator_code_required",
            )
        return operator_party_id, party_code

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
        )

    async def create_project(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate,
        created_by: str | None = None,
        organization_id: str | None = None,  # DEPRECATED alias
        commit: bool = True,
    ) -> Project:
        """创建项目"""
        try:
            # 1. 生成项目编码 (如果未提供)
            if "party_relations" in obj_in.model_fields_set:
                raise OperationNotAllowedError(
                    "项目 party_relations 写入口已下线；项目主体关系由产权/运营方字段派生，禁止通过该字段写入",
                    reason="project_party_relations_write_removed",
                )
            if not obj_in.project_code:
                (
                    operator_party_id,
                    operator_party_code,
                ) = await self._resolve_operator_party_for_code(db, obj_in)
                obj_in.project_code = await self.generate_project_code(
                    db,
                    obj_in.project_name,
                    operator_party_id=operator_party_id,
                    operator_party_code=operator_party_code,
                )

            # 2. 检查编码唯一性
            existing_project = await project_crud.get_by_code(
                db, code=obj_in.project_code
            )
            if existing_project:
                raise DuplicateResourceError(
                    "项目", "project_code", obj_in.project_code
                )

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
            if commit:
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

        if "party_relations" in obj_in.model_fields_set:
            raise OperationNotAllowedError(
                "项目 party_relations 写入口已下线；项目主体关系由产权/运营方字段派生，禁止通过该字段写入",
                reason="project_party_relations_write_removed",
            )
        result: Project = await project_crud.update(
            db,
            db_obj=project,
            obj_in=obj_in,
            commit=False,
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
        self,
        db: AsyncSession,
        name: str | None = None,
        *,
        operator_party_id: str | None = None,
        operator_party_code: str | None = None,
    ) -> str:
        """生成项目编码，格式：PRJ-<运营方段>-<YYYYMM>-<4位序号>。"""
        _ = name
        _ = operator_party_id
        if not operator_party_code or str(operator_party_code).strip() == "":
            raise OperationNotAllowedError(
                "自动生成 project_code 必须提供运营方 party.code",
                reason="project_operator_code_required",
            )
        year_month = self._utcnow_naive().strftime("%Y%m")
        segment = build_party_code_segment(operator_party_code)
        prefix = f"PRJ-{segment}-{year_month}-"
        await project_crud.acquire_code_generation_lock(db, prefix=prefix)
        last_project = await project_crud.get_latest_by_code_prefix(db, prefix=prefix)

        if last_project:
            try:
                next_seq = int(str(last_project.project_code)[-4:]) + 1
            except (ValueError, IndexError, TypeError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"

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
            if items:
                asset_counts = await project_crud.get_asset_counts(
                    db, [str(item.id) for item in items]
                )
                manager_names = await project_crud.get_manager_party_names(
                    db, [str(item.id) for item in items]
                )
                for item in items:
                    item_id = str(item.id)
                    setattr(item, "asset_count", asset_counts.get(item_id, 0))
                    setattr(item, "manager_party_name", manager_names.get(item_id))
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
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[Asset], ProjectAssetSummary]:
        """获取项目当前有效关联资产列表及面积汇总。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
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

        return await self._load_project_active_assets(db, project_id=project_id)

    async def _load_project_active_assets(
        self,
        db: AsyncSession,
        *,
        project_id: str,
    ) -> tuple[list[Asset], ProjectAssetSummary]:
        """加载项目当前有效资产；调用方负责完成项目可见性校验。"""
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
            (
                self._as_decimal(getattr(asset, "rentable_area", None))
                for asset in ordered_assets
            ),
            start=Decimal(0),
        )
        total_rented_area = sum(
            (
                self._as_decimal(getattr(asset, "rented_area", None))
                for asset in ordered_assets
            ),
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

    async def get_project_contract_relations(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ProjectContractRelationsResponse:
        """获取项目下合同关系展示投影。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
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

        groups = await contract_group_crud.list_by_project(
            db,
            project_id=project_id,
        )
        items: list[ProjectContractRelationItem] = []
        for group in groups:
            contracts = await contract_crud.list_by_group(
                db,
                group_id=str(getattr(group, "contract_group_id")),
            )
            items.append(
                self._contract_relation_item_from_group(
                    group=group,
                    contracts=contracts,
                )
            )
        return ProjectContractRelationsResponse(items=items, total=len(items))

    async def get_project_risks(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ProjectRisksResponse:
        """获取项目风险提示。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)
        relations = await self.get_project_contract_relations(
            db=db,
            project_id=project_id,
            current_user_id=current_user_id,
            party_filter=resolved_party_filter,
        )

        items: list[ProjectRiskItem] = []
        seen: set[str] = set()
        today = self._today()
        expiring_until = today + timedelta(days=30)

        def add_risk(
            relation: ProjectContractRelationItem,
            *,
            risk_type: str,
            message: str,
            severity: str = "warning",
        ) -> None:
            risk_id = f"{relation.contract_relation_id}:{risk_type}:{message}"
            if risk_id in seen:
                return
            seen.add(risk_id)
            items.append(
                ProjectRiskItem(
                    risk_id=risk_id,
                    risk_type=risk_type,
                    severity=severity,
                    message=message,
                    contract_relation_id=relation.contract_relation_id,
                    display_name=relation.display_name,
                )
            )

        def add_asset_risk(
            *,
            asset_id: str,
            asset_name: str,
            risk_type: str,
            message: str,
            severity: str = "warning",
        ) -> None:
            risk_id = f"asset:{asset_id}:{risk_type}:{message}"
            if risk_id in seen:
                return
            seen.add(risk_id)
            items.append(
                ProjectRiskItem(
                    risk_id=risk_id,
                    risk_type=risk_type,
                    severity=severity,
                    message=message,
                    contract_relation_id=None,
                    display_name=asset_name,
                    asset_id=asset_id,
                )
            )

        def contract_display_name(contract: Any) -> str:
            contract_number = str(
                getattr(contract, "contract_number", "") or ""
            ).strip()
            if contract_number != "":
                return contract_number
            return str(getattr(contract, "contract_id", "") or "").strip()

        def contract_role_label(contract: Any) -> str:
            relation_type = self._normalize_group_relation_type(
                getattr(contract, "group_relation_type", None)
            )
            labels = {
                GroupRelationType.UPSTREAM: "上游承租合同",
                GroupRelationType.DOWNSTREAM: "下游出租合同",
                GroupRelationType.ENTRUSTED: "委托协议",
                GroupRelationType.DIRECT_LEASE: "直租合同",
            }
            if relation_type is None:
                return "合同"
            return labels.get(relation_type, "合同")

        def format_money(value: Decimal) -> str:
            return f"¥{self._quantize_money(value):,.2f}"

        for relation in relations.items:
            for tag in relation.risk_tags or []:
                normalized_tag = str(tag).strip()
                if normalized_tag != "":
                    add_risk(
                        relation,
                        risk_type="manual_tag",
                        message=normalized_tag,
                    )

            contracts = await contract_crud.list_by_group(
                db,
                group_id=relation.contract_relation_id,
                load_details=True,
            )
            for contract in contracts:
                relation_type = self._normalize_group_relation_type(
                    getattr(contract, "group_relation_type", None)
                )
                effective_to = getattr(contract, "effective_to", None)
                status = getattr(contract, "status", None)
                is_inactive = status == ContractLifecycleStatus.TERMINATED
                if (
                    isinstance(effective_to, date)
                    and today <= effective_to <= expiring_until
                    and not is_inactive
                ):
                    add_risk(
                        relation,
                        risk_type="contract_expiring",
                        message=(
                            f"{contract_role_label(contract)} "
                            f"{contract_display_name(contract)} 将于 {effective_to.isoformat()} 到期"
                        ),
                        severity="warning",
                    )

                ledger_entries = (
                    await contract_group_crud.list_ledger_entries_by_contract(
                        db,
                        contract_id=str(getattr(contract, "contract_id")),
                    )
                )
                ledger_entries = [
                    entry
                    for entry in ledger_entries
                    if is_resource_in_scope(
                        entry,
                        party_filter=resolved_party_filter,
                    )
                ]
                protected_payment_entries = [
                    entry
                    for entry in ledger_entries
                    if str(getattr(entry, "payment_status", "") or "").strip()
                    in {"paid", "partial"}
                    or self._has_active_ledger_allocation(entry)
                ]
                if protected_payment_entries:
                    rent_terms = await contract_group_crud.list_rent_terms_by_contract(
                        db,
                        contract_id=str(getattr(contract, "contract_id")),
                    )
                    payment_cycle = (
                        getattr(
                            getattr(contract, "lease_detail", None),
                            "payment_cycle",
                            None,
                        )
                        or "月付"
                    )
                    stale_entries = find_stale_paid_or_partial_ledger_entries(
                        rent_terms=rent_terms,
                        ledger_entries=protected_payment_entries,
                        payment_cycle=payment_cycle,
                    )
                    if stale_entries:
                        add_risk(
                            relation,
                            risk_type="ledger_stale_after_correction",
                            message=(
                                f"{contract_role_label(contract)} "
                                f"{contract_display_name(contract)} "
                                f"存在 {len(stale_entries)} 条已收台账与当前合同条款不一致"
                            ),
                            severity="warning",
                        )

                is_project_receivable_contract = (
                    relation.revenue_mode == RevenueMode.LEASE.value
                    and relation_type == GroupRelationType.DOWNSTREAM
                )
                if not is_project_receivable_contract:
                    continue

                overdue_amount = Decimal(0)
                for entry in ledger_entries:
                    overdue_amount += self._overdue_amount_from_entry(entry, today)
                if overdue_amount > Decimal(0):
                    add_risk(
                        relation,
                        risk_type="payment_overdue",
                        message=(
                            f"{contract_role_label(contract)} "
                            f"{contract_display_name(contract)} 逾期未收 {format_money(overdue_amount)}"
                        ),
                        severity="high",
                    )

            if relation.revenue_mode != RevenueMode.AGENCY.value:
                continue

            source_mismatches = await service_fee_ledger_service.find_source_mismatches(
                db,
                group_id=relation.contract_relation_id,
                current_user_id=current_user_id,
                party_filter=resolved_party_filter,
            )
            if source_mismatches:
                add_risk(
                    relation,
                    risk_type="service_fee_source_mismatch",
                    message=(
                        f"{relation.display_name} 存在 "
                        f"{len(source_mismatches)} 条服务费台账来源租金不一致"
                    ),
                    severity="warning",
                )

        active_assets, _summary = await self._load_project_active_assets(
            db,
            project_id=project_id,
        )
        active_asset_by_id: dict[str, Any] = {}
        for asset in active_assets:
            asset_id = str(getattr(asset, "id", "") or "").strip()
            if asset_id == "":
                continue
            active_asset_by_id[asset_id] = asset
            rentable_area = self._as_decimal(getattr(asset, "rentable_area", None))
            rented_area = self._as_decimal(getattr(asset, "rented_area", None))
            vacant_area = max(rentable_area - rented_area, Decimal(0))
            if vacant_area <= Decimal(0):
                continue
            asset_name = str(
                getattr(asset, "asset_name", None)
                or getattr(asset, "name", None)
                or asset_id
            ).strip()
            add_asset_risk(
                asset_id=asset_id,
                asset_name=asset_name,
                risk_type="vacancy",
                message=f"空置资产 {asset_name} 空置面积 {vacant_area:.2f}㎡",
                severity="warning",
            )

        if active_asset_by_id:
            certificates = await property_certificate_crud.list_by_asset_ids(
                db,
                asset_ids=list(active_asset_by_id),
            )
            as_of = self._utcnow_naive()
            for certificate in certificates:
                risk_result = calculate_holder_owner_mismatch(
                    certificate_id=str(certificate.id),
                    certificate_number=str(certificate.certificate_number),
                    holder_relations=(
                        HolderRelationSnapshot(
                            party_id=str(relation.party_id),
                            relation_role=relation.relation_role,
                            valid_from=relation.valid_from,
                            valid_to=relation.valid_to,
                        )
                        for relation in certificate.party_relations
                    ),
                    assets=_certificate_asset_snapshots(
                        certificate, active_asset_by_id
                    ),
                    as_of=as_of,
                )
                incomplete_result = calculate_incomplete_certificate_info(
                    certificate_id=str(certificate.id),
                    certificate_number=str(certificate.certificate_number),
                    certificate_type=certificate.certificate_type,
                    building_area=getattr(certificate, "building_area", None),
                    land_area=getattr(certificate, "land_area", None),
                    land_use_term_start=getattr(
                        certificate, "land_use_term_start", None
                    ),
                    land_use_term_end=getattr(certificate, "land_use_term_end", None),
                    restrictions=getattr(certificate, "restrictions", None),
                    assets=_certificate_asset_snapshots(
                        certificate, active_asset_by_id
                    ),
                )
                if risk_result.missing_current_holders:
                    logger.warning(
                        "Project certificate risk skipped holder-owner comparison "
                        "because no current holder exists "
                        "(project_id=%s, certificate_id=%s)",
                        project_id,
                        certificate.id,
                    )
                for asset_id in risk_result.asset_ids_missing_owner:
                    logger.warning(
                        "Project certificate risk skipped holder-owner comparison "
                        "because asset has no owner_party_id "
                        "(project_id=%s, certificate_id=%s, asset_id=%s)",
                        project_id,
                        certificate.id,
                        asset_id,
                    )
                for warning in (
                    *risk_result.warnings,
                    *incomplete_result.warnings,
                ):
                    if warning.risk_id in seen:
                        continue
                    seen.add(warning.risk_id)
                    asset = active_asset_by_id[warning.asset_id]
                    asset_name = str(
                        getattr(asset, "asset_name", None)
                        or getattr(asset, "name", None)
                        or warning.asset_id
                    ).strip()
                    items.append(
                        ProjectRiskItem(
                            risk_id=warning.risk_id,
                            risk_type="property_certificate_data_quality",
                            severity=warning.severity,
                            message=warning.message,
                            contract_relation_id=None,
                            display_name=asset_name,
                            asset_id=warning.asset_id,
                            property_certificate_id=warning.certificate_id,
                            warning_code=warning.risk_type,
                        )
                    )

        return ProjectRisksResponse(items=items, total=len(items))

    async def get_project_ledger_summary(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ProjectLedgerSummaryResponse:
        """获取项目维度收付款摘要。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
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

        ledger_entries = (
            await contract_group_crud.list_ledger_entries_by_attributed_project(
                db,
                project_id=project_id,
            )
        )

        terminal_collection = self._empty_ledger_metric_group()
        operator_income = self._empty_ledger_metric_group()
        operator_cost = self._empty_ledger_metric_group()
        service_fee_settlement = self._empty_ledger_metric_group()
        today = self._today()

        for entry in ledger_entries:
            if not is_resource_in_scope(
                entry,
                party_filter=resolved_party_filter,
            ):
                continue
            payment_status = str(getattr(entry, "payment_status", "") or "").strip()
            if payment_status == "voided":
                continue

            amount_due = self._as_decimal(getattr(entry, "amount_due", None))
            entry_paid_amount = self._as_decimal(getattr(entry, "paid_amount", None))
            ledger_views = self._ledger_views(entry)
            if "terminal_collection" in ledger_views:
                terminal_collection["amount_due"] += amount_due
                terminal_collection["paid_amount"] += entry_paid_amount
                terminal_collection["overdue_amount"] += (
                    self._overdue_amount_from_entry(entry, today)
                )
            if "operator_income" in ledger_views:
                operator_income["amount_due"] += amount_due
                operator_income["paid_amount"] += entry_paid_amount
            if "operator_cost" in ledger_views:
                operator_cost["amount_due"] += amount_due
                operator_cost["paid_amount"] += entry_paid_amount

        service_fee_entries = (
            await contract_group_crud.list_service_fee_entries_by_attributed_project(
                db,
                project_id=project_id,
            )
        )
        for service_fee_entry in service_fee_entries:
            if not is_resource_in_scope(
                service_fee_entry,
                party_filter=resolved_party_filter,
            ):
                continue
            payment_status = str(
                getattr(service_fee_entry, "payment_status", "") or ""
            ).strip()
            if payment_status == "voided":
                continue

            amount_due = self._as_decimal(
                getattr(service_fee_entry, "amount_due", None)
            )
            entry_paid_amount = self._as_decimal(
                getattr(service_fee_entry, "paid_amount", None)
            )
            service_fee_settlement["amount_due"] += amount_due
            service_fee_settlement["paid_amount"] += entry_paid_amount
            operator_income["amount_due"] += amount_due
            operator_income["paid_amount"] += entry_paid_amount

        terminal_response = self._ledger_metric_group_response(terminal_collection)
        income_response = self._ledger_metric_group_response(operator_income)
        cost_response = self._ledger_metric_group_response(operator_cost)
        service_fee_response = self._ledger_metric_group_response(
            service_fee_settlement
        )

        return ProjectLedgerSummaryResponse(
            receivable_amount=income_response.amount_due,
            payable_amount=cost_response.amount_due,
            received_amount=income_response.paid_amount,
            paid_amount=cost_response.paid_amount,
            overdue_amount=terminal_response.overdue_amount,
            service_fee_receivable=service_fee_response.amount_due,
            service_fee_received=service_fee_response.paid_amount,
            terminal_collection=terminal_response,
            operator_income=income_response,
            operator_cost=cost_response,
            service_fee_settlement=service_fee_response,
            operating_result=ProjectOperatingResultSummary(
                accrual_net_amount=self._quantize_money(
                    income_response.amount_due - cost_response.amount_due
                ),
                cash_net_amount=self._quantize_money(
                    income_response.paid_amount - cost_response.paid_amount
                ),
            ),
        )

    async def get_project_tenants(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ProjectTenantSummaryResponse:
        """获取项目终端租户和客户主体摘要。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
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

        groups = await contract_group_crud.list_by_project(
            db,
            project_id=project_id,
        )

        terminal_types = {
            RevenueMode.LEASE: {GroupRelationType.DOWNSTREAM},
            RevenueMode.AGENCY: {GroupRelationType.DIRECT_LEASE},
        }
        relation_labels = {
            GroupRelationType.DOWNSTREAM: "下游",
            GroupRelationType.DIRECT_LEASE: "直租",
        }
        tenants_by_party_id: dict[str, ProjectTenantSummaryItem] = {}

        for group in groups:
            revenue_mode = self._normalize_revenue_mode(
                getattr(group, "revenue_mode", None)
            )
            allowed_types = terminal_types[revenue_mode]
            contracts = await contract_crud.list_by_group(
                db,
                group_id=str(getattr(group, "contract_group_id")),
            )

            for contract in contracts:
                relation_type = self._normalize_group_relation_type(
                    getattr(contract, "group_relation_type", None)
                )
                if relation_type not in allowed_types:
                    continue

                party_id = str(getattr(contract, "lessee_party_id", "") or "").strip()
                if party_id == "":
                    continue

                item = tenants_by_party_id.get(party_id)
                if item is None:
                    item = ProjectTenantSummaryItem(
                        party_id=party_id,
                        party_name=self._party_name_from_contract(contract),
                        group_relation_type=relation_labels[relation_type],
                        contract_count=0,
                    )
                    tenants_by_party_id[party_id] = item
                item.contract_count += 1

        items = list(tenants_by_party_id.values())
        return ProjectTenantSummaryResponse(items=items, total=len(items))

    async def get_project_analytics(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ProjectAnalyticsResponse:
        """获取项目维度分析摘要，按经营模式分区。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("项目", project_id)
        should_suppress_customer_metrics = (
            getattr(resolved_party_filter, "filter_mode", None) == "any"
        )
        _, asset_summary = await self.get_project_active_assets(
            db=db,
            project_id=project_id,
            current_user_id=current_user_id,
            party_filter=resolved_party_filter,
        )
        relations = await self.get_project_contract_relations(
            db=db,
            project_id=project_id,
            current_user_id=current_user_id,
            party_filter=resolved_party_filter,
        )
        ledger_summary = await self.get_project_ledger_summary(
            db=db,
            project_id=project_id,
            current_user_id=current_user_id,
            party_filter=resolved_party_filter,
        )
        tenants = (
            ProjectTenantSummaryResponse(items=[], total=0)
            if should_suppress_customer_metrics
            else await self.get_project_tenants(
                db=db,
                project_id=project_id,
                current_user_id=current_user_id,
                party_filter=resolved_party_filter,
            )
        )
        risks = await self.get_project_risks(
            db=db,
            project_id=project_id,
            current_user_id=current_user_id,
            party_filter=resolved_party_filter,
        )

        mode_meta = {
            "lease_sublease": "承租转租",
            "agency_operation": "代理运营",
        }
        mode_amounts = {
            "lease_sublease": self._empty_mode_amounts(),
            "agency_operation": self._empty_mode_amounts(),
        }
        trend_amounts: dict[str, dict[str, Decimal]] = {}
        customer_ids_by_mode: dict[str, set[str]] = {
            "lease_sublease": set(),
            "agency_operation": set(),
        }
        customer_contract_counts: dict[str, int] = {
            "lease_sublease": 0,
            "agency_operation": 0,
        }
        today = self._today()

        for tenant in tenants.items:
            relation_type = self._normalize_group_relation_type(
                tenant.group_relation_type
            )
            if relation_type == GroupRelationType.DOWNSTREAM:
                relation_kind = "lease_sublease"
            elif relation_type == GroupRelationType.DIRECT_LEASE:
                relation_kind = "agency_operation"
            else:
                continue
            customer_ids_by_mode[relation_kind].add(tenant.party_id)
            customer_contract_counts[relation_kind] += tenant.contract_count

        ledger_entries = (
            await contract_group_crud.list_ledger_entries_by_attributed_project(
                db,
                project_id=project_id,
            )
        )
        for entry in ledger_entries:
            if not is_resource_in_scope(
                entry,
                party_filter=resolved_party_filter,
            ):
                continue
            payment_status = str(getattr(entry, "payment_status", "") or "").strip()
            if payment_status == "voided":
                continue
            revenue_mode, relation_type = self._ledger_entry_context(entry)
            relation_kind = self._relation_kind_from_revenue_mode(revenue_mode)
            is_payable_contract = (
                revenue_mode == RevenueMode.LEASE
                and relation_type == GroupRelationType.UPSTREAM
            )
            is_receivable_contract = (
                revenue_mode == RevenueMode.LEASE
                and relation_type == GroupRelationType.DOWNSTREAM
            )
            if not (is_payable_contract or is_receivable_contract):
                continue

            amount_due = self._as_decimal(getattr(entry, "amount_due", None))
            entry_paid_amount = self._as_decimal(getattr(entry, "paid_amount", None))
            period = self._year_month_from_entry(entry)
            period_amounts = trend_amounts.setdefault(
                period, self._empty_trend_amounts()
            )
            if is_payable_contract:
                mode_amounts[relation_kind]["payable_amount"] += amount_due
                mode_amounts[relation_kind]["paid_amount"] += entry_paid_amount
                period_amounts["payable_amount"] += amount_due
                period_amounts["paid_amount"] += entry_paid_amount
            else:
                mode_amounts[relation_kind]["receivable_amount"] += amount_due
                mode_amounts[relation_kind]["received_amount"] += entry_paid_amount
                period_amounts["receivable_amount"] += amount_due
                period_amounts["received_amount"] += entry_paid_amount
                overdue_amount = self._overdue_amount_from_entry(entry, today)
                mode_amounts[relation_kind]["overdue_amount"] += overdue_amount
                period_amounts["overdue_amount"] += overdue_amount

        service_fee_entries = (
            await contract_group_crud.list_service_fee_entries_by_attributed_project(
                db,
                project_id=project_id,
            )
        )
        for service_fee_entry in service_fee_entries:
            if not is_resource_in_scope(
                service_fee_entry,
                party_filter=resolved_party_filter,
            ):
                continue
            payment_status = str(
                getattr(service_fee_entry, "payment_status", "") or ""
            ).strip()
            if payment_status == "voided":
                continue
            amount_due = self._as_decimal(
                getattr(service_fee_entry, "amount_due", None)
            )
            entry_paid_amount = self._as_decimal(
                getattr(service_fee_entry, "paid_amount", None)
            )
            period = self._year_month_from_entry(service_fee_entry)
            period_amounts = trend_amounts.setdefault(
                period, self._empty_trend_amounts()
            )
            relation_kind = "agency_operation"
            mode_amounts[relation_kind]["receivable_amount"] += amount_due
            mode_amounts[relation_kind]["received_amount"] += entry_paid_amount
            period_amounts["receivable_amount"] += amount_due
            period_amounts["received_amount"] += entry_paid_amount
            overdue_amount = self._overdue_amount_from_entry(
                service_fee_entry,
                today,
            )
            mode_amounts[relation_kind]["overdue_amount"] += overdue_amount
            period_amounts["overdue_amount"] += overdue_amount

        risk_counts: dict[str, int] = {"lease_sublease": 0, "agency_operation": 0}
        relation_kind_by_id = {
            relation.contract_relation_id: relation.relation_kind
            for relation in relations.items
        }
        for risk in risks.items:
            relation_id = risk.contract_relation_id
            if relation_id is None:
                continue
            risk_relation_kind = relation_kind_by_id.get(relation_id)
            if risk_relation_kind in risk_counts:
                risk_counts[risk_relation_kind] += 1

        mode_summaries: list[ProjectAnalysisModeSummary] = []
        for relation_kind, label in mode_meta.items():
            mode_relations = [
                relation
                for relation in relations.items
                if relation.relation_kind == relation_kind
            ]
            mode_asset_ids = {
                asset_id
                for relation in mode_relations
                for asset_id in relation.asset_ids
            }
            amounts = mode_amounts[relation_kind]
            mode_summaries.append(
                ProjectAnalysisModeSummary(
                    relation_kind=relation_kind,
                    label=label,
                    contract_relation_count=len(mode_relations),
                    asset_count=len(mode_asset_ids),
                    primary_contract_count=sum(
                        len(relation.primary_contract_ids)
                        for relation in mode_relations
                    ),
                    terminal_contract_count=sum(
                        len(relation.terminal_contract_ids)
                        for relation in mode_relations
                    ),
                    customer_count=None
                    if should_suppress_customer_metrics
                    else len(customer_ids_by_mode[relation_kind]),
                    customer_contract_count=None
                    if should_suppress_customer_metrics
                    else customer_contract_counts[relation_kind],
                    receivable_amount=self._quantize_money(
                        amounts["receivable_amount"]
                    ),
                    payable_amount=self._quantize_money(amounts["payable_amount"]),
                    received_amount=self._quantize_money(amounts["received_amount"]),
                    paid_amount=self._quantize_money(amounts["paid_amount"]),
                    overdue_amount=self._quantize_money(amounts["overdue_amount"]),
                    risk_count=risk_counts[relation_kind],
                )
            )

        high_risk_count = len(
            [
                risk
                for risk in risks.items
                if str(risk.severity).strip() in {"critical", "error", "high"}
            ]
        )

        return ProjectAnalyticsResponse(
            asset_summary=asset_summary,
            contract_relation_count=relations.total,
            tenant_count=None if should_suppress_customer_metrics else tenants.total,
            customer_contract_count=None
            if should_suppress_customer_metrics
            else sum(tenant.contract_count for tenant in tenants.items),
            customer_metrics_suppression_reason="customer_metrics_requires_single_perspective"
            if should_suppress_customer_metrics
            else None,
            risk_count=risks.total,
            high_risk_count=high_risk_count,
            receivable_amount=ledger_summary.receivable_amount,
            payable_amount=ledger_summary.payable_amount,
            received_amount=ledger_summary.received_amount,
            paid_amount=ledger_summary.paid_amount,
            overdue_amount=ledger_summary.overdue_amount,
            service_fee_receivable=ledger_summary.service_fee_receivable,
            service_fee_received=ledger_summary.service_fee_received,
            mode_summaries=mode_summaries,
            monthly_trends=[
                ProjectMonthlyTrendItem(
                    period=period,
                    receivable_amount=self._quantize_money(
                        amounts["receivable_amount"]
                    ),
                    payable_amount=self._quantize_money(amounts["payable_amount"]),
                    received_amount=self._quantize_money(amounts["received_amount"]),
                    paid_amount=self._quantize_money(amounts["paid_amount"]),
                    overdue_amount=self._quantize_money(amounts["overdue_amount"]),
                )
                for period, amounts in sorted(trend_amounts.items())
                if period != "unknown"
            ],
        )

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
