"""
合同组业务逻辑 Service（REQ-RNT-001 M2）。

核心职责：
  - group_code 生成
  - revenue_mode / group_relation_type 一致性校验
  - sign_date 约束校验
  - derived_status 计算（纯函数）
  - ContractGroup + Contract CRUD 编排
"""

import logging
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export `select` so that tests patching
# `src.services.contract.contract_group_service.select` continue to work
# (the lifecycle mixin uses `select` from sqlalchemy).
from src.core.exception_handler import (
    DuplicateResourceError,
    InvalidRequestError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.crud.query_builder import PartyFilter
from src.models.contract_group import (
    Contract,
    ContractGroup,
    ContractLifecycleStatus,
    GroupRelationType,
    RevenueMode,
)
from src.schemas.contract_group import (
    ContractCreate,
    ContractGroupCreate,
    ContractGroupDetail,
    ContractGroupListItem,
    ContractGroupUpdate,
    ContractSummary,
)
from src.services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)

# ── 业务常量 ─────────────────────────────────────────────────────────────────

# 合法的 revenue_mode → group_relation_type 组合
_VALID_RELATION_TYPES: dict[RevenueMode, frozenset[GroupRelationType]] = {
    RevenueMode.LEASE: frozenset(
        {GroupRelationType.UPSTREAM, GroupRelationType.DOWNSTREAM}
    ),
    RevenueMode.AGENCY: frozenset(
        {GroupRelationType.ENTRUSTED, GroupRelationType.DIRECT_LEASE}
    ),
}

# 进入非草稿状态前必须有 sign_date 的状态集
_STATUS_REQUIRES_SIGN_DATE = frozenset(
    {
        ContractLifecycleStatus.PENDING_REVIEW,
        ContractLifecycleStatus.ACTIVE,
    }
)

# group_code 段：只保留大写字母和数字，不足 8 位补 X
_CODE_SEGMENT_RE = re.compile(r"[A-Z0-9]")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── 纯函数（可直接单测）─────────────────────────────────────────────────────


def calculate_derived_status(contracts: list[Contract]) -> str:
    """
    根据合同列表计算合同组派生状态（纯函数，无 I/O）。

    规则（docs/features/requirements-appendix-fields.md §8.1）：
      - 组内无任何合同 → 筹备中
      - 有效合同中无 ACTIVE / PENDING_REVIEW → 筹备中
      - 至少一条处于 ACTIVE → 生效中
      - 全部为 EXPIRED / TERMINATED → 已结束
    """
    active_contracts = [c for c in contracts if c.data_status == "正常"]
    if not active_contracts:
        return "筹备中"

    statuses = {c.status for c in active_contracts}

    terminal = {ContractLifecycleStatus.EXPIRED, ContractLifecycleStatus.TERMINATED}
    if statuses.issubset(terminal):
        return "已结束"

    if ContractLifecycleStatus.ACTIVE in statuses:
        return "生效中"

    return "筹备中"


def _normalize_enum_member(enum_cls: Any, raw: Any) -> Any:
    if isinstance(raw, enum_cls):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip()
        if normalized != "":
            try:
                return enum_cls[normalized.upper()]
            except KeyError:
                for member in enum_cls:
                    if normalized == member.value:
                        return member
    raise OperationNotAllowedError(f"不支持的 {enum_cls.__name__} 值: {raw}")


def validate_revenue_mode_compatibility(
    revenue_mode: RevenueMode | str,
    group_relation_type: GroupRelationType | str,
) -> None:
    """校验 revenue_mode 与 group_relation_type 的合法组合，不合法时抛出 OperationNotAllowedError。"""
    normalized_revenue_mode = _normalize_enum_member(RevenueMode, revenue_mode)
    normalized_group_relation_type = _normalize_enum_member(
        GroupRelationType,
        group_relation_type,
    )
    allowed = _VALID_RELATION_TYPES.get(normalized_revenue_mode, frozenset())
    if normalized_group_relation_type not in allowed:
        mode_label = (
            "承租模式" if normalized_revenue_mode == RevenueMode.LEASE else "代理模式"
        )
        allowed_labels = [r.value for r in allowed]
        raise OperationNotAllowedError(
            f"{mode_label}合同组只允许以下合同角色：{allowed_labels}，"
            f"当前值：{normalized_group_relation_type.value}"
        )


def validate_sign_date_for_status(
    status: ContractLifecycleStatus,
    sign_date: Any,
) -> None:
    """进入待审 / 生效状态前 sign_date 必填，否则抛出 OperationNotAllowedError。"""
    if status in _STATUS_REQUIRES_SIGN_DATE and sign_date is None:
        raise OperationNotAllowedError(
            f"合同状态为 {status.value} 时，签订日期（sign_date）不能为空"
        )


def _build_operator_code_segment(party_code: str) -> str:
    """从 party_code 提取 ≤8 位大写字母数字，不足用 X 补齐。"""
    upper = party_code.upper()
    chars = _CODE_SEGMENT_RE.findall(upper)
    segment = "".join(chars)[:8]
    return segment.ljust(8, "X")


def _require_reason(action: str, reason: str | None) -> str:
    normalized_reason = (reason or "").strip()
    if normalized_reason == "":
        raise InvalidRequestError(f"{action}时 reason 不能为空", field="reason")
    return normalized_reason


def _compute_total_monthly_amount(
    monthly_rent: Decimal,
    management_fee: Decimal,
    other_fees: Decimal,
) -> Decimal:
    return monthly_rent + management_fee + other_fees


# ── Service 类 ───────────────────────────────────────────────────────────────

from src.services.contract.contract_group_lifecycle import ContractGroupLifecycleMixin

# Re-export dependencies used by the lifecycle mixin so that
# `src.services.contract.contract_group_service.party_service` etc. are patchable.
from src.services.contract.ledger_service_v2 import ledger_service_v2  # noqa: F401
from src.services.party import party_service  # noqa: F401


class ContractGroupService(ContractGroupLifecycleMixin):
    """合同组业务逻辑服务。"""

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

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return (
            len(
                [
                    party_id
                    for party_id in party_filter.party_ids
                    if str(party_id).strip() != ""
                ]
            )
            == 0
        )

    async def _get_scoped_group_or_raise(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
        load_contracts: bool = False,
    ) -> ContractGroup:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("合同组", group_id)

        group = await contract_group_crud.get(
            db,
            group_id,
            load_contracts=load_contracts,
            party_filter=resolved_party_filter,
        )
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)
        return group

    async def _get_scoped_contract_or_raise(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
        load_details: bool = False,
    ) -> Contract:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("合同", contract_id)

        contract = await contract_crud.get(db, contract_id, load_details=load_details)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)

        if resolved_party_filter is not None:
            scoped_group = await contract_group_crud.get(
                db,
                contract.contract_group_id,
                party_filter=resolved_party_filter,
            )
            if scoped_group is None:
                raise ResourceNotFoundError("合同", contract_id)
        return contract

    # ─── group_code 生成 ──────────────────────────────────────────────────

    async def generate_group_code(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        operator_party_code: str,
    ) -> str:
        """
        生成唯一合同组编码：GRP-{CODE_SEGMENT}-{YYYYMM}-{SEQ4}

        Args:
            operator_party_id: 运营方主体 ID（用于计数）
            operator_party_code: 运营方 party_code（用于构建字母段）
        """
        year_month = datetime.now(UTC).strftime("%Y%m")
        segment = _build_operator_code_segment(operator_party_code)
        existing_count = await contract_group_crud.count_by_operator_month(
            db, operator_party_id=operator_party_id, year_month=year_month
        )
        seq = str(existing_count + 1).zfill(4)
        return f"GRP-{segment}-{year_month}-{seq}"

    # ─── ContractGroup CRUD ─────────────────────────────────────────────

    async def create_contract_group(
        self,
        db: AsyncSession,
        *,
        obj_in: ContractGroupCreate,
        group_code: str,
        current_user: str | None = None,
        commit: bool = True,
    ) -> ContractGroup:
        """
        创建合同组。

        Args:
            group_code: 由调用方（API 层）预先生成的编码，避免 Service 依赖 Party CRUD
        Raises:
            DuplicateResourceError: group_code 已存在
        """
        existing = await contract_group_crud.get_by_code(db, group_code)
        if existing is not None:
            raise DuplicateResourceError("合同组", "group_code", group_code)

        now = _utcnow()
        data: dict[str, Any] = {
            "contract_group_id": str(uuid.uuid4()),
            "group_code": group_code,
            "revenue_mode": obj_in.revenue_mode.name,
            "operator_party_id": obj_in.operator_party_id,
            "owner_party_id": obj_in.owner_party_id,
            "effective_from": obj_in.effective_from,
            "effective_to": obj_in.effective_to,
            "settlement_rule": obj_in.settlement_rule.model_dump(),
            "revenue_attribution_rule": obj_in.revenue_attribution_rule,
            "revenue_share_rule": obj_in.revenue_share_rule,
            "risk_tags": obj_in.risk_tags,
            "predecessor_group_id": obj_in.predecessor_group_id,
            "data_status": "正常",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": current_user,
            "updated_by": current_user,
        }
        return await contract_group_crud.create(
            db, data=data, asset_ids=obj_in.asset_ids or None, commit=commit
        )

    async def update_contract_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        obj_in: ContractGroupUpdate,
        current_user: str | None = None,
    ) -> ContractGroup:
        """更新合同组（B12 group_code 不可修改）。"""
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)

        update_data: dict[str, Any] = {}
        set_fields = obj_in.model_fields_set

        # settlement_rule 不允许清空（DB NOT NULL），其余可空字段跟随 model_fields_set
        if "settlement_rule" in set_fields and obj_in.settlement_rule is not None:
            update_data["settlement_rule"] = obj_in.settlement_rule.model_dump()
        if "effective_to" in set_fields:
            update_data["effective_to"] = obj_in.effective_to
        if "revenue_attribution_rule" in set_fields:
            update_data["revenue_attribution_rule"] = obj_in.revenue_attribution_rule
        if "revenue_share_rule" in set_fields:
            update_data["revenue_share_rule"] = obj_in.revenue_share_rule
        if "risk_tags" in set_fields:
            update_data["risk_tags"] = obj_in.risk_tags
        if current_user is not None:
            update_data["updated_by"] = current_user

        return await contract_group_crud.update(
            db,
            db_obj=group,
            data=update_data,
            asset_ids=obj_in.asset_ids,
        )

    async def get_group_detail(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ContractGroupDetail:
        """
        获取合同组详情，包含：
          - 组内所有合同摘要
          - 派生状态（derived_status）
          - upstream / downstream contract_ids（来自 ContractRelation）
        """
        group = await self._get_scoped_group_or_raise(
            db,
            group_id=group_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )

        contracts = await contract_crud.list_by_group(db, group_id=group_id)
        derived = calculate_derived_status(contracts)

        # 聚合上下游 contract_ids（直接从合同的 group_relation_type 读取）
        upstream_ids = [
            c.contract_id
            for c in contracts
            if c.group_relation_type == GroupRelationType.UPSTREAM
        ]
        downstream_ids = [
            c.contract_id
            for c in contracts
            if c.group_relation_type == GroupRelationType.DOWNSTREAM
        ]

        contract_summaries = [ContractSummary.model_validate(c) for c in contracts]

        group_dict = {
            col: getattr(group, col) for col in group.__table__.columns.keys()
        }
        group_dict["derived_status"] = derived
        group_dict["upstream_contract_ids"] = upstream_ids
        group_dict["downstream_contract_ids"] = downstream_ids
        group_dict["contracts"] = contract_summaries

        return ContractGroupDetail(**group_dict)

    async def list_groups(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str | None = None,
        owner_party_id: str | None = None,
        revenue_mode: str | None = None,
        offset: int = 0,
        limit: int = 20,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[ContractGroupListItem], int]:
        """分页查询合同组列表，返回含 derived_status 的列表项。"""
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return [], 0

        items, total = await contract_group_crud.list_by_filters(
            db,
            operator_party_id=operator_party_id,
            owner_party_id=owner_party_id,
            revenue_mode=revenue_mode,
            offset=offset,
            limit=limit,
            party_filter=resolved_party_filter,
        )

        result = []
        for group in items:
            contracts = await contract_crud.list_by_group(
                db, group_id=group.contract_group_id
            )
            derived = calculate_derived_status(contracts)
            group_dict = {
                col: getattr(group, col) for col in group.__table__.columns.keys()
            }
            group_dict["derived_status"] = derived
            result.append(ContractGroupListItem(**group_dict))

        return result, total

    async def soft_delete_group(
        self, db: AsyncSession, *, group_id: str
    ) -> ContractGroup:
        """
        逻辑删除合同组。

        Raises:
            OperationNotAllowedError: 组内存在生效合同时拒绝删除（B11）
        """
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)

        active_count = await contract_crud.count_active_in_group(db, group_id=group_id)
        if active_count > 0:
            raise OperationNotAllowedError(
                f"合同组内存在 {active_count} 条生效合同，请先终止或等待到期后再删除"
            )

        return await contract_group_crud.soft_delete(db, db_obj=group)

    # ─── Contract CRUD ──────────────────────────────────────────────────

    async def add_contract_to_group(
        self,
        db: AsyncSession,
        *,
        obj_in: ContractCreate,
        current_user: str | None = None,
        commit: bool = True,
    ) -> Contract:
        """
        向合同组添加合同。

        业务校验：
          - B1/B2: revenue_mode ↔ group_relation_type 一致性
          - B8: 非草稿状态时 sign_date 必填
          - 合同组必须存在
        """
        group = await contract_group_crud.get(db, obj_in.contract_group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", obj_in.contract_group_id)

        revenue_mode = group.revenue_mode
        validate_revenue_mode_compatibility(revenue_mode, obj_in.group_relation_type)
        validate_sign_date_for_status(obj_in.status, obj_in.sign_date)
        existing_contract = await contract_crud.get_by_contract_number(
            db,
            contract_number=obj_in.contract_number,
        )
        if existing_contract is not None:
            raise DuplicateResourceError(
                "合同", "contract_number", obj_in.contract_number
            )

        now = _utcnow()
        data: dict[str, Any] = {
            "contract_id": str(uuid.uuid4()),
            "contract_group_id": obj_in.contract_group_id,
            "contract_number": obj_in.contract_number,
            "contract_direction": obj_in.contract_direction.name,
            "group_relation_type": obj_in.group_relation_type.name,
            "lessor_party_id": obj_in.lessor_party_id,
            "lessee_party_id": obj_in.lessee_party_id,
            "sign_date": obj_in.sign_date,
            "effective_from": obj_in.effective_from,
            "effective_to": obj_in.effective_to,
            "currency_code": obj_in.currency_code,
            "tax_rate": obj_in.tax_rate,
            "is_tax_included": obj_in.is_tax_included,
            "status": obj_in.status.name,
            "review_status": obj_in.review_status.name,
            "contract_notes": obj_in.contract_notes,
            "source_session_id": obj_in.source_session_id,
            "data_status": "正常",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": current_user,
            "updated_by": current_user,
        }

        lease_detail_data = (
            obj_in.lease_detail.model_dump() if obj_in.lease_detail else None
        )
        agency_detail_data = (
            obj_in.agency_detail.model_dump() if obj_in.agency_detail else None
        )

        return await contract_crud.create(
            db,
            data=data,
            lease_detail_data=lease_detail_data,
            agency_detail_data=agency_detail_data,
            asset_ids=obj_in.asset_ids or None,
            commit=commit,
        )

    async def list_contracts_in_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[Contract]:
        """
        列出合同组内所有生效数据合同。

        Raises:
            ResourceNotFoundError: 合同组不存在
        """
        await self._get_scoped_group_or_raise(
            db,
            group_id=group_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await contract_crud.list_by_group(db, group_id=group_id)


contract_group_service = ContractGroupService()
