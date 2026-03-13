"""
合同组业务逻辑 Service（REQ-RNT-001 M2）。

核心职责：
  - group_code 生成
  - revenue_mode / group_relation_type 一致性校验
  - sign_date 约束校验
  - derived_status 计算（纯函数）
  - ContractGroup + Contract CRUD 编排
"""

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import (
    DuplicateResourceError,
    InvalidRequestError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.asset import Asset, AssetReviewStatus
from src.models.associations import contract_assets
from src.models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractGroup,
    ContractLifecycleStatus,
    ContractRentTerm,
    ContractReviewStatus,
    GroupRelationType,
    RevenueMode,
)
from src.schemas.contract_group import (
    ContractCreate,
    ContractDetail,
    ContractGroupCreate,
    ContractGroupDetail,
    ContractGroupListItem,
    ContractGroupUpdate,
    ContractRentTermCreate,
    ContractRentTermUpdate,
    ContractSummary,
)
from src.services.contract.ledger_service_v2 import ledger_service_v2
from src.services.party import party_service

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


class ContractGroupService:
    """合同组业务逻辑服务。"""

    async def _get_contract_or_raise(
        self, db: AsyncSession, *, contract_id: str
    ) -> Contract:
        contract = await contract_crud.get(db, contract_id, load_details=True)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        return contract

    async def _append_audit_log(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
        action: str,
        old_status: ContractLifecycleStatus | None,
        new_status: ContractLifecycleStatus | None,
        old_review_status: ContractReviewStatus | None,
        new_review_status: ContractReviewStatus | None,
        reason: str | None,
        current_user: str | None,
        operator_name: str | None,
        related_entry_id: str | None = None,
    ) -> ContractAuditLog:
        data = {
            "log_id": str(uuid.uuid4()),
            "contract_id": contract.contract_id,
            "action": action,
            "old_status": old_status.name if old_status is not None else None,
            "new_status": new_status.name if new_status is not None else None,
            "review_status_old": (
                old_review_status.name if old_review_status is not None else None
            ),
            "review_status_new": (
                new_review_status.name if new_review_status is not None else None
            ),
            "reason": reason,
            "operator_id": current_user,
            "operator_name": operator_name,
            "related_entry_id": related_entry_id,
            "created_at": _utcnow(),
        }
        return await contract_group_crud.create_audit_log(db, data=data, commit=False)

    async def _transition_contract(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
        allowed_statuses: set[ContractLifecycleStatus],
        action: str,
        new_status: ContractLifecycleStatus,
        new_review_status: ContractReviewStatus | None,
        current_user: str | None,
        operator_name: str | None,
        reason: str | None = None,
        related_entry_id: str | None = None,
        review_by: str | None = None,
        reviewed_at: datetime | None = None,
        extra_updates: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> Contract:
        if contract.status not in allowed_statuses:
            allowed = sorted(status.value for status in allowed_statuses)
            raise OperationNotAllowedError(
                f"{action} 仅允许在以下状态执行：{allowed}，当前状态：{contract.status.value}"
            )

        old_status = contract.status
        old_review_status = contract.review_status
        update_data: dict[str, Any] = {
            "status": new_status,
            "updated_by": current_user,
        }
        if new_review_status is not None:
            update_data["review_status"] = new_review_status
        if review_by is not None:
            update_data["review_by"] = review_by
        if reviewed_at is not None:
            update_data["reviewed_at"] = reviewed_at
        if reason is not None:
            update_data["review_reason"] = reason
        if extra_updates:
            update_data.update(extra_updates)

        updated_contract = await contract_crud.update(
            db,
            db_obj=contract,
            data=update_data,
            commit=False,
        )
        await self._append_audit_log(
            db,
            contract=updated_contract,
            action=action,
            old_status=old_status,
            new_status=new_status,
            old_review_status=old_review_status,
            new_review_status=updated_contract.review_status,
            reason=reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
        )
        if commit:
            await db.commit()
        return updated_contract

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
        self, db: AsyncSession, *, group_id: str
    ) -> ContractGroupDetail:
        """
        获取合同组详情，包含：
          - 组内所有合同摘要
          - 派生状态（derived_status）
          - upstream / downstream contract_ids（来自 ContractRelation）
        """
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)

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
    ) -> tuple[list[ContractGroupListItem], int]:
        """分页查询合同组列表，返回含 derived_status 的列表项。"""
        items, total = await contract_group_crud.list_by_filters(
            db,
            operator_party_id=operator_party_id,
            owner_party_id=owner_party_id,
            revenue_mode=revenue_mode,
            offset=offset,
            limit=limit,
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
            raise DuplicateResourceError("合同", "contract_number", obj_in.contract_number)

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

    async def get_contract_detail(
        self, db: AsyncSession, *, contract_id: str
    ) -> ContractDetail:
        """获取单合同详情（含明细）。"""
        contract = await contract_crud.get(db, contract_id, load_details=True)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        return ContractDetail.model_validate(contract)

    async def list_contracts_in_group(
        self, db: AsyncSession, *, group_id: str
    ) -> list[Contract]:
        """
        列出合同组内所有生效数据合同。

        Raises:
            ResourceNotFoundError: 合同组不存在
        """
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)
        return await contract_crud.list_by_group(db, group_id=group_id)

    async def soft_delete_contract(
        self, db: AsyncSession, *, contract_id: str
    ) -> Contract:
        """
        逻辑删除合同。

        Raises:
            ResourceNotFoundError: 合同不存在
            OperationNotAllowedError: 合同处于生效状态时禁止删除
        """
        contract = await contract_crud.get(db, contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        if contract.status == ContractLifecycleStatus.ACTIVE:
            raise OperationNotAllowedError(
                "生效中的合同不可直接删除，请先将合同状态变更为已终止后再操作"
            )
        return await contract_crud.soft_delete(db, db_obj=contract)

    # ─── Lifecycle ──────────────────────────────────────────────────────

    async def submit_review(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> tuple[Contract, list[str]]:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        group = await contract_group_crud.get(db, contract.contract_group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", contract.contract_group_id)
        await party_service.assert_parties_approved(
            db,
            party_ids=[
                contract.lessor_party_id,
                contract.lessee_party_id,
                group.operator_party_id,
                group.owner_party_id,
            ],
            operation="合同提审",
        )
        validate_sign_date_for_status(
            ContractLifecycleStatus.PENDING_REVIEW, contract.sign_date
        )
        stmt = (
            select(Asset.asset_name, Asset.review_status)
            .join(contract_assets, contract_assets.c.asset_id == Asset.id)
            .where(
                contract_assets.c.contract_id == contract_id,
                Asset.review_status != AssetReviewStatus.APPROVED.value,
            )
        )
        non_approved_assets = (await db.execute(stmt)).all()
        asset_warnings = [
            f"关联资产 {row.asset_name} 尚未审核通过（当前状态：{row.review_status}），请注意核实"
            for row in non_approved_assets
        ]

        updated_contract = await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.DRAFT},
            action="submit_review",
            new_status=ContractLifecycleStatus.PENDING_REVIEW,
            new_review_status=ContractReviewStatus.PENDING,
            current_user=current_user,
            operator_name=operator_name,
            commit=commit,
        )
        return updated_contract, asset_warnings

    async def approve(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        reviewer = operator_name or current_user
        updated_contract = await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.PENDING_REVIEW},
            action="approve",
            new_status=ContractLifecycleStatus.ACTIVE,
            new_review_status=ContractReviewStatus.APPROVED,
            current_user=current_user,
            operator_name=operator_name,
            review_by=reviewer,
            reviewed_at=_utcnow(),
            extra_updates={"review_reason": None},
            commit=False,
        )
        await ledger_service_v2.generate_ledger_on_activation(
            db,
            contract_id=contract_id,
        )
        if commit:
            await db.commit()
        return updated_contract

    async def reject(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("驳回", reason)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.PENDING_REVIEW},
            action="reject",
            new_status=ContractLifecycleStatus.DRAFT,
            new_review_status=ContractReviewStatus.DRAFT,
            current_user=current_user,
            operator_name=operator_name,
            reason=normalized_reason,
            commit=commit,
        )

    async def expire(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.ACTIVE},
            action="expire",
            new_status=ContractLifecycleStatus.EXPIRED,
            new_review_status=None,
            current_user=current_user,
            operator_name=operator_name,
            commit=commit,
        )

    async def terminate_contract_v2(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("终止", reason)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={
                ContractLifecycleStatus.ACTIVE,
                ContractLifecycleStatus.EXPIRED,
            },
            action="terminate",
            new_status=ContractLifecycleStatus.TERMINATED,
            new_review_status=None,
            current_user=current_user,
            operator_name=operator_name,
            reason=normalized_reason,
            commit=commit,
        )

    async def void_contract(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        related_entry_id: str | None = None,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("作废", reason)
        if contract.status == ContractLifecycleStatus.ACTIVE:
            raise OperationNotAllowedError("ACTIVE 合同必须先终止后才能作废，请先终止")
        has_ledger_entries = await contract_group_crud.has_contract_ledger_entries(
            db,
            contract_id=contract_id,
        )
        if has_ledger_entries:
            raise OperationNotAllowedError("合同已存在台账，请先冲销台账后再作废")

        old_status = contract.status
        old_review_status = contract.review_status
        updated_contract = await contract_crud.update(
            db,
            db_obj=contract,
            data={
                "data_status": "已作废",
                "updated_by": current_user,
                "review_reason": normalized_reason,
            },
            commit=False,
        )
        await self._append_audit_log(
            db,
            contract=updated_contract,
            action="void",
            old_status=old_status,
            new_status=old_status,
            old_review_status=old_review_status,
            new_review_status=old_review_status,
            reason=normalized_reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
        )
        await db.commit()
        return updated_contract

    async def submit_group_review(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
    ) -> dict[str, Any]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)

        contracts = await contract_crud.list_by_group(db, group_id=group_id)
        draft_contracts = [
            contract
            for contract in contracts
            if contract.data_status == "正常"
            and contract.status == ContractLifecycleStatus.DRAFT
        ]

        validation_errors: list[str] = []
        for contract in draft_contracts:
            if contract.sign_date is None:
                validation_errors.append(f"{contract.contract_id}: sign_date 不能为空")

        if validation_errors:
            raise InvalidRequestError(
                "批量提审失败，请先补齐草稿合同签订日期: "
                + "; ".join(validation_errors),
                details={"contracts": validation_errors},
            )

        updated_contract_ids: list[str] = []
        warnings: list[str] = []
        for contract in draft_contracts:
            _, contract_warnings = await self.submit_review(
                db,
                contract_id=contract.contract_id,
                current_user=current_user,
                operator_name=operator_name,
                commit=False,
            )
            updated_contract_ids.append(contract.contract_id)
            warnings.extend(contract_warnings)

        if updated_contract_ids:
            await db.commit()

        return {
            "updated_count": len(updated_contract_ids),
            "skipped_count": len(contracts) - len(updated_contract_ids),
            "contract_ids": updated_contract_ids,
            "warnings": warnings,
        }

    # ─── Rent Terms ─────────────────────────────────────────────────────

    async def create_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        obj_in: ContractRentTermCreate,
        commit: bool = True,
    ) -> ContractRentTerm:
        await self._get_contract_or_raise(db, contract_id=contract_id)
        now = _utcnow()
        total_monthly_amount = _compute_total_monthly_amount(
            obj_in.monthly_rent,
            obj_in.management_fee,
            obj_in.other_fees,
        )
        data = {
            "rent_term_id": str(uuid.uuid4()),
            "contract_id": contract_id,
            "sort_order": obj_in.sort_order,
            "start_date": obj_in.start_date,
            "end_date": obj_in.end_date,
            "monthly_rent": obj_in.monthly_rent,
            "management_fee": obj_in.management_fee,
            "other_fees": obj_in.other_fees,
            "total_monthly_amount": total_monthly_amount,
            "notes": obj_in.notes,
            "created_at": now,
            "updated_at": now,
        }
        return await contract_group_crud.create_rent_term(
            db,
            data=data,
            commit=commit,
        )

    async def list_rent_terms(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractRentTerm]:
        await self._get_contract_or_raise(db, contract_id=contract_id)
        return await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract_id,
        )

    async def update_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        rent_term_id: str,
        obj_in: ContractRentTermUpdate,
    ) -> ContractRentTerm:
        rent_term = await contract_group_crud.get_rent_term(
            db, rent_term_id=rent_term_id
        )
        if rent_term is None or rent_term.contract_id != contract_id:
            raise ResourceNotFoundError("租金条款", rent_term_id)

        start_date = (
            obj_in.start_date if obj_in.start_date is not None else rent_term.start_date
        )
        end_date = (
            obj_in.end_date if obj_in.end_date is not None else rent_term.end_date
        )
        if end_date < start_date:
            raise InvalidRequestError("租金条款结束日期不得早于开始日期")

        monthly_rent = (
            obj_in.monthly_rent
            if obj_in.monthly_rent is not None
            else rent_term.monthly_rent
        )
        management_fee = (
            obj_in.management_fee
            if obj_in.management_fee is not None
            else rent_term.management_fee
        )
        other_fees = (
            obj_in.other_fees if obj_in.other_fees is not None else rent_term.other_fees
        )
        data = obj_in.model_dump(exclude_unset=True)
        data["total_monthly_amount"] = _compute_total_monthly_amount(
            monthly_rent,
            management_fee,
            other_fees,
        )
        return await contract_group_crud.update_rent_term(
            db,
            db_obj=rent_term,
            data=data,
        )

    async def delete_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        rent_term_id: str,
    ) -> None:
        rent_term = await contract_group_crud.get_rent_term(
            db, rent_term_id=rent_term_id
        )
        if rent_term is None or rent_term.contract_id != contract_id:
            raise ResourceNotFoundError("租金条款", rent_term_id)
        await contract_group_crud.delete_rent_term(db, db_obj=rent_term)


contract_group_service = ContractGroupService()
