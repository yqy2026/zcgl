"""
合同关系技术聚合 Service（REQ-RNT-001 M2）。

核心职责：
  - group_code 生成
  - revenue_mode / group_relation_type 一致性校验
  - sign_date 约束校验
  - derived_status 计算（纯函数）
  - ContractGroup 技术聚合根 + Contract CRUD 编排
"""

import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import (
    DuplicateResourceError,
    InvalidRequestError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractDirection,
    ContractGroup,
    ContractLifecycleStatus,
    ContractRentTerm,
    GroupRelationType,
    RevenueMode,
)
from src.schemas.contract_group import (
    AuditLogResponse,
    ContractCreate,
    ContractDetail,
    ContractGroupCreate,
    ContractGroupDetail,
    ContractGroupListItem,
    ContractGroupUpdate,
    ContractRentTermCreate,
    ContractRentTermUpdate,
    ContractScanDocumentCreate,
    ContractScanDocumentReplaceRequest,
    ContractScanDocumentResponse,
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
      - 有效合同中无 ACTIVE → 筹备中
      - 至少一条处于 ACTIVE → 生效中
      - 全部已终止或自然到期 → 已结束
    """
    active_contracts = [c for c in contracts if c.data_status == "正常"]
    if not active_contracts:
        return "筹备中"

    today = date.today()

    def is_ended(contract: Contract) -> bool:
        if contract.status == ContractLifecycleStatus.TERMINATED:
            return True
        effective_to = getattr(contract, "effective_to", None)
        return (
            contract.status == ContractLifecycleStatus.ACTIVE
            and isinstance(effective_to, date)
            and effective_to < today
        )

    if all(is_ended(contract) for contract in active_contracts):
        return "已结束"

    if any(c.status == ContractLifecycleStatus.ACTIVE for c in active_contracts):
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


def _normalize_required_project_id(group: ContractGroup) -> str:
    project_id = str(getattr(group, "project_id", "") or "").strip()
    if project_id == "":
        raise OperationNotAllowedError(
            "合同关系缺少所属项目，无法按项目校验合同号唯一性",
            reason="contract_group_project_required",
        )
    return project_id


def _normalize_snapshot_name(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


# ── Service 类 ───────────────────────────────────────────────────────────────


class ContractGroupService:
    """合同关系技术聚合服务。"""

    @staticmethod
    async def _ensure_assets_not_bound_to_other_groups(
        db: AsyncSession,
        *,
        current_group_id: str | None,
        project_id: str | None,
        asset_ids: list[str] | None,
    ) -> None:
        normalized_asset_ids = sorted(
            {
                str(asset_id).strip()
                for asset_id in (asset_ids or [])
                if str(asset_id).strip() != ""
            }
        )
        if not normalized_asset_ids:
            return

        conflicts = await contract_group_crud.list_active_group_bindings_for_assets(
            db,
            group_id=current_group_id,
            asset_ids=normalized_asset_ids,
        )
        if not conflicts:
            return

        normalized_project_id = (
            str(project_id).strip() if project_id is not None else ""
        )
        blocking_conflicts = [
            item
            for item in conflicts
            if normalized_project_id == ""
            or str(item.get("project_id") or "").strip() != normalized_project_id
        ]
        if not blocking_conflicts:
            return

        details = "；".join(
            f"{item['asset_id']} -> {item['group_code']}" for item in blocking_conflicts
        )
        raise OperationNotAllowedError(
            f"以下资产已绑定其他项目的有效合同关系：{details}",
            reason="asset_already_bound_to_active_contract_relation",
        )

    @staticmethod
    async def _ensure_assets_belong_to_project(
        db: AsyncSession,
        *,
        project_id: str | None,
        asset_ids: list[str] | None,
    ) -> None:
        normalized_project_id = (
            str(project_id).strip() if project_id is not None else ""
        )
        normalized_asset_ids = sorted(
            {
                str(asset_id).strip()
                for asset_id in (asset_ids or [])
                if str(asset_id).strip() != ""
            }
        )
        if not normalized_asset_ids:
            return

        bindings = await contract_group_crud.list_current_project_bindings_for_assets(
            db,
            asset_ids=normalized_asset_ids,
        )
        binding_by_asset_id = {
            item["asset_id"]: item.get("project_id") for item in bindings
        }
        mismatches = [
            asset_id
            for asset_id in normalized_asset_ids
            if normalized_project_id == ""
            or str(binding_by_asset_id.get(asset_id) or "").strip()
            != normalized_project_id
        ]
        if not mismatches:
            return

        details = "；".join(
            f"{asset_id} -> {binding_by_asset_id.get(asset_id) or '未绑定项目'}"
            for asset_id in mismatches
        )
        raise OperationNotAllowedError(
            f"以下资产不属于合同关系所属项目：{details}",
            reason="asset_project_mismatch",
        )

    @staticmethod
    async def _ensure_contract_assets_within_group(
        db: AsyncSession,
        *,
        group_id: str,
        asset_ids: list[str] | None,
    ) -> None:
        normalized_asset_ids = sorted(
            {
                str(asset_id).strip()
                for asset_id in (asset_ids or [])
                if str(asset_id).strip() != ""
            }
        )
        if not normalized_asset_ids:
            return

        group_asset_ids = set(
            await contract_group_crud.list_asset_ids_for_group(db, group_id=group_id)
        )
        out_of_scope = [
            asset_id
            for asset_id in normalized_asset_ids
            if asset_id not in group_asset_ids
        ]
        if not out_of_scope:
            return

        raise OperationNotAllowedError(
            "合同覆盖资产不得超出所属合同关系覆盖资产范围：" + "；".join(out_of_scope),
            reason="contract_assets_outside_group_scope",
        )

    @staticmethod
    async def _ensure_existing_contract_assets_within_group_assets(
        db: AsyncSession,
        *,
        group_id: str,
        asset_ids: list[str] | None,
    ) -> None:
        normalized_group_asset_ids = {
            str(asset_id).strip()
            for asset_id in (asset_ids or [])
            if str(asset_id).strip() != ""
        }
        contract_assets_by_group = (
            await contract_group_crud.list_contract_asset_ids_by_group(
                db,
                group_id=group_id,
            )
        )
        violations: list[str] = []
        for item in contract_assets_by_group:
            contract_id = item["contract_id"]
            out_of_scope = sorted(
                {
                    str(asset_id).strip()
                    for asset_id in item.get("asset_ids", [])
                    if str(asset_id).strip() != ""
                    and str(asset_id).strip() not in normalized_group_asset_ids
                }
            )
            if out_of_scope:
                violations.append(f"{contract_id}: {'、'.join(out_of_scope)}")

        if not violations:
            return

        raise OperationNotAllowedError(
            "合同关系覆盖资产不得小于已有合同显式覆盖资产：" + "；".join(violations),
            reason="contract_assets_outside_group_scope",
        )

    @staticmethod
    def _normalize_binding_type(
        binding_type: Literal["owner", "manager", "all"] | None,
    ) -> Literal["owner", "manager"] | None:
        if binding_type == "owner":
            return "owner"
        if binding_type == "manager":
            return "manager"
        return None

    @staticmethod
    def _normalize_effective_party_ids(
        effective_party_ids: list[str] | None,
    ) -> list[str]:
        if effective_party_ids is None:
            return []

        normalized_ids: list[str] = []
        seen: set[str] = set()
        for party_id in effective_party_ids:
            normalized_party_id = str(party_id).strip()
            if normalized_party_id == "" or normalized_party_id in seen:
                continue
            seen.add(normalized_party_id)
            normalized_ids.append(normalized_party_id)
        return normalized_ids

    @classmethod
    def _assert_group_in_scope(
        cls,
        *,
        group: ContractGroup,
        group_id: str,
        binding_type: Literal["owner", "manager", "all"] | None,
        effective_party_ids: list[str] | None,
    ) -> None:
        normalized_effective_party_ids = cls._normalize_effective_party_ids(
            effective_party_ids
        )
        if binding_type is None or len(normalized_effective_party_ids) == 0:
            return

        if binding_type == "all":
            owner_party_id = str(getattr(group, "owner_party_id", "")).strip()
            operator_party_id = str(getattr(group, "operator_party_id", "")).strip()
            if (
                owner_party_id in normalized_effective_party_ids
                or operator_party_id in normalized_effective_party_ids
            ):
                return
            raise ResourceNotFoundError("合同组", group_id)

        scoped_party_id = (
            str(getattr(group, "owner_party_id", "")).strip()
            if binding_type == "owner"
            else str(getattr(group, "operator_party_id", "")).strip()
        )
        if scoped_party_id not in normalized_effective_party_ids:
            raise ResourceNotFoundError("合同组", group_id)

    async def _get_contract_or_raise(
        self, db: AsyncSession, *, contract_id: str
    ) -> Contract:
        contract = await contract_crud.get(db, contract_id, load_details=True)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        return contract

    async def _build_party_name_snapshots(
        self,
        db: AsyncSession,
        *,
        lessor_party_id: str,
        lessee_party_id: str,
    ) -> dict[str, str | None]:
        snapshots: dict[str, str | None] = {
            "lessor_name_snapshot": None,
            "lessee_name_snapshot": None,
        }
        for key, party_id in (
            ("lessor_name_snapshot", lessor_party_id),
            ("lessee_name_snapshot", lessee_party_id),
        ):
            party = await party_service.get_party(db, party_id=party_id)
            if party is None:
                raise ResourceNotFoundError("主体", party_id)
            snapshots[key] = _normalize_snapshot_name(getattr(party, "name", None))
        return snapshots

    @staticmethod
    def _sync_lease_detail_with_lessee_snapshot(
        lease_detail_data: dict[str, Any] | None,
        *,
        lessee_name_snapshot: str | None,
    ) -> dict[str, Any] | None:
        if lease_detail_data is None:
            return None
        synced = dict(lease_detail_data)
        synced["tenant_name"] = lessee_name_snapshot
        return synced

    async def _append_audit_log(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
        action: str,
        old_status: ContractLifecycleStatus | None,
        new_status: ContractLifecycleStatus | None,
        reason: str | None,
        current_user: str | None,
        operator_name: str | None,
        related_entry_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ContractAuditLog:
        data = {
            "log_id": str(uuid.uuid4()),
            "contract_id": contract.contract_id,
            "action": action,
            "old_status": old_status.name if old_status is not None else None,
            "new_status": new_status.name if new_status is not None else None,
            "reason": reason,
            "operator_id": current_user,
            "operator_name": operator_name,
            "related_entry_id": related_entry_id,
            "context": context,
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
        current_user: str | None,
        operator_name: str | None,
        reason: str | None = None,
        related_entry_id: str | None = None,
        extra_updates: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> Contract:
        if contract.status not in allowed_statuses:
            allowed = sorted(status.value for status in allowed_statuses)
            raise OperationNotAllowedError(
                f"{action} 仅允许在以下状态执行：{allowed}，当前状态：{contract.status.value}"
            )

        old_status = contract.status
        update_data: dict[str, Any] = {
            "status": new_status,
            "updated_by": current_user,
        }
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
            reason=reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
            context=context,
        )
        if commit:
            await db.commit()
        return updated_contract

    @staticmethod
    def _draft_mutation_allowed(contract: Contract) -> bool:
        return (
            contract.data_status == "正常"
            and contract.status == ContractLifecycleStatus.DRAFT
        )

    async def _require_draft_contract_for_mutation(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        if not self._draft_mutation_allowed(contract):
            raise OperationNotAllowedError(
                "当前合同不是可编辑的纠错草稿或草稿合同，请先发起纠错草稿后再修改"
            )
        return contract

    async def _get_correction_source_contract(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
    ) -> Contract | None:
        source_contract_id = getattr(contract, "correction_source_contract_id", None)
        if not isinstance(source_contract_id, str) or source_contract_id.strip() == "":
            return None
        source_contract = await contract_crud.get(db, source_contract_id)
        source_contract_id = getattr(source_contract, "contract_id", None)
        if not isinstance(source_contract_id, str) or source_contract_id.strip() == "":
            return None
        return source_contract

    async def _classify_change_categories(
        self,
        db: AsyncSession,
        *,
        draft_contract: Contract,
        source_contract: Contract,
    ) -> set[str]:
        categories: set[str] = set()

        if draft_contract.lessor_party_id != source_contract.lessor_party_id:
            categories.add("parties")
        if draft_contract.lessee_party_id != source_contract.lessee_party_id:
            categories.add("parties")
        if (draft_contract.contract_notes or "") != (
            source_contract.contract_notes or ""
        ):
            categories.add("notes")

        draft_lease = getattr(draft_contract, "lease_detail", None)
        source_lease = getattr(source_contract, "lease_detail", None)
        if draft_lease is not None or source_lease is not None:
            if getattr(draft_lease, "payment_cycle", None) != getattr(
                source_lease, "payment_cycle", None
            ):
                categories.add("billing")

        draft_assets = sorted(
            str(getattr(asset, "id", asset))
            for asset in (getattr(draft_contract, "assets", None) or [])
        )
        source_assets = sorted(
            str(getattr(asset, "id", asset))
            for asset in (getattr(source_contract, "assets", None) or [])
        )
        if draft_assets != source_assets:
            categories.add("assets")

        draft_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=draft_contract.contract_id,
        )
        source_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=source_contract.contract_id,
        )
        draft_term_signature = [
            (
                term.sort_order,
                term.start_date,
                term.end_date,
                term.monthly_rent,
                term.management_fee,
                term.other_fees,
            )
            for term in draft_terms
        ]
        source_term_signature = [
            (
                term.sort_order,
                term.start_date,
                term.end_date,
                term.monthly_rent,
                term.management_fee,
                term.other_fees,
            )
            for term in source_terms
        ]
        if draft_term_signature != source_term_signature:
            categories.add("rent_terms")

        return categories

    async def _get_correction_effective_month(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
    ) -> str:
        rent_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract.contract_id,
        )
        if rent_terms:
            earliest_start = min(term.start_date for term in rent_terms)
        else:
            earliest_start = contract.effective_from
        return earliest_start.strftime("%Y-%m")

    def _clone_contract_base_data(
        self,
        *,
        source_contract: Contract,
        new_contract_id: str,
        new_contract_number: str,
        current_user: str | None,
    ) -> dict[str, Any]:
        contract_direction = _normalize_enum_member(
            ContractDirection,
            source_contract.contract_direction,
        )
        group_relation_type = _normalize_enum_member(
            GroupRelationType,
            source_contract.group_relation_type,
        )
        now = _utcnow()
        return {
            "contract_id": new_contract_id,
            "contract_group_id": source_contract.contract_group_id,
            "project_id": source_contract.project_id,
            "contract_number": new_contract_number,
            "contract_direction": contract_direction.name,
            "group_relation_type": group_relation_type.name,
            "lessor_party_id": source_contract.lessor_party_id,
            "lessee_party_id": source_contract.lessee_party_id,
            "lessor_name_snapshot": getattr(
                source_contract,
                "lessor_name_snapshot",
                None,
            ),
            "lessee_name_snapshot": getattr(
                source_contract,
                "lessee_name_snapshot",
                None,
            ),
            "sign_date": source_contract.sign_date,
            "effective_from": source_contract.effective_from,
            "effective_to": source_contract.effective_to,
            "currency_code": source_contract.currency_code,
            "tax_rate": source_contract.tax_rate,
            "is_tax_included": source_contract.is_tax_included,
            "status": ContractLifecycleStatus.DRAFT.name,
            "contract_notes": source_contract.contract_notes,
            "source_session_id": source_contract.source_session_id,
            "correction_source_contract_id": source_contract.contract_id,
            "data_status": "正常",
            "created_at": now,
            "updated_at": now,
            "created_by": current_user,
            "updated_by": current_user,
        }

    @staticmethod
    def _clone_lease_detail_data(source_contract: Contract) -> dict[str, Any] | None:
        lease_detail = getattr(source_contract, "lease_detail", None)
        if lease_detail is None:
            return None
        return {
            "total_deposit": getattr(lease_detail, "total_deposit", None),
            "rent_amount": getattr(lease_detail, "rent_amount", Decimal("0")),
            "monthly_rent_base": getattr(lease_detail, "monthly_rent_base", None),
            "payment_cycle": getattr(lease_detail, "payment_cycle", "月付"),
            "payment_terms": getattr(lease_detail, "payment_terms", None),
            "tenant_name": _normalize_snapshot_name(
                getattr(
                    source_contract,
                    "lessee_name_snapshot",
                    getattr(lease_detail, "tenant_name", None),
                )
            ),
            "tenant_contact": getattr(lease_detail, "tenant_contact", None),
            "tenant_phone": getattr(lease_detail, "tenant_phone", None),
            "tenant_address": getattr(lease_detail, "tenant_address", None),
            "tenant_usage": getattr(lease_detail, "tenant_usage", None),
            "owner_name": getattr(lease_detail, "owner_name", None),
            "owner_contact": getattr(lease_detail, "owner_contact", None),
            "owner_phone": getattr(lease_detail, "owner_phone", None),
        }

    @staticmethod
    def _clone_agency_detail_data(source_contract: Contract) -> dict[str, Any] | None:
        agency_detail = getattr(source_contract, "agency_detail", None)
        if agency_detail is None:
            return None
        return {
            "service_fee_ratio": getattr(
                agency_detail, "service_fee_ratio", Decimal("0")
            ),
            "fee_calculation_base": getattr(
                agency_detail, "fee_calculation_base", "actual_received"
            ),
            "agency_scope": getattr(agency_detail, "agency_scope", None),
        }

    async def start_correction(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str,
        current_user: str | None = None,
        operator_name: str | None = None,
    ) -> Contract:
        source_contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("发起纠错", reason)
        if source_contract.status != ContractLifecycleStatus.ACTIVE:
            raise OperationNotAllowedError("仅生效中的合同允许发起纠错草稿")

        new_contract_id = str(uuid.uuid4())
        new_contract_number = f"{source_contract.contract_number}-C01"
        asset_ids = [
            str(getattr(asset, "id", asset))
            for asset in (getattr(source_contract, "assets", None) or [])
        ]
        cloned_contract = await contract_crud.create(
            db,
            data=self._clone_contract_base_data(
                source_contract=source_contract,
                new_contract_id=new_contract_id,
                new_contract_number=new_contract_number,
                current_user=current_user,
            ),
            lease_detail_data=self._clone_lease_detail_data(source_contract),
            agency_detail_data=self._clone_agency_detail_data(source_contract),
            asset_ids=asset_ids or None,
            commit=False,
        )
        source_scan_documents = await contract_crud.list_scan_documents_by_contract(
            db,
            contract_id=contract_id,
        )
        if source_scan_documents:
            await contract_crud.replace_scan_document_links_for_contracts(
                db,
                contract_ids=[cloned_contract.contract_id],
                document_ids=[doc.document_id for doc in source_scan_documents],
            )

        source_rent_terms = await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract_id,
        )
        for source_term in source_rent_terms:
            await contract_group_crud.create_rent_term(
                db,
                data={
                    "rent_term_id": str(uuid.uuid4()),
                    "contract_id": cloned_contract.contract_id,
                    "sort_order": source_term.sort_order,
                    "start_date": source_term.start_date,
                    "end_date": source_term.end_date,
                    "monthly_rent": source_term.monthly_rent,
                    "management_fee": source_term.management_fee,
                    "other_fees": source_term.other_fees,
                    "total_monthly_amount": _compute_total_monthly_amount(
                        source_term.monthly_rent,
                        source_term.management_fee,
                        source_term.other_fees,
                    ),
                    "notes": source_term.notes,
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                },
                commit=False,
            )

        await self._append_audit_log(
            db,
            contract=source_contract,
            action="start_correction",
            old_status=source_contract.status,
            new_status=source_contract.status,
            reason=normalized_reason,
            current_user=current_user,
            operator_name=operator_name,
            context={
                "review_scope": "correction",
                "affected_contract_ids": [
                    source_contract.contract_id,
                    cloned_contract.contract_id,
                ],
                "change_categories": [],
                "correction_source_contract_id": source_contract.contract_id,
            },
        )
        await db.commit()
        return cloned_contract

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

        await self._ensure_assets_belong_to_project(
            db,
            project_id=obj_in.project_id,
            asset_ids=obj_in.asset_ids,
        )
        await self._ensure_assets_not_bound_to_other_groups(
            db,
            current_group_id=None,
            project_id=obj_in.project_id,
            asset_ids=obj_in.asset_ids,
        )

        now = _utcnow()
        data: dict[str, Any] = {
            "contract_group_id": str(uuid.uuid4()),
            "project_id": obj_in.project_id,
            "group_code": group_code,
            "revenue_mode": obj_in.revenue_mode.name,
            "operator_party_id": obj_in.operator_party_id,
            "owner_party_id": obj_in.owner_party_id,
            "effective_from": obj_in.effective_from,
            "effective_to": obj_in.effective_to,
            "settlement_rule": (
                obj_in.settlement_rule.model_dump()
                if obj_in.settlement_rule is not None
                else None
            ),
            "revenue_attribution_rule": obj_in.revenue_attribution_rule,
            "revenue_share_rule": obj_in.revenue_share_rule,
            "risk_tags": obj_in.risk_tags,
            "data_status": "正常",
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

        if "settlement_rule" in set_fields:
            update_data["settlement_rule"] = (
                obj_in.settlement_rule.model_dump()
                if obj_in.settlement_rule is not None
                else None
            )
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

        await self._ensure_assets_belong_to_project(
            db,
            project_id=getattr(group, "project_id", None),
            asset_ids=obj_in.asset_ids,
        )
        await self._ensure_assets_not_bound_to_other_groups(
            db,
            current_group_id=group_id,
            project_id=getattr(group, "project_id", None),
            asset_ids=obj_in.asset_ids,
        )
        if "asset_ids" in set_fields:
            await self._ensure_existing_contract_assets_within_group_assets(
                db,
                group_id=group_id,
                asset_ids=obj_in.asset_ids,
            )

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
        binding_type: Literal["owner", "manager", "all"] | None = None,
        effective_party_ids: list[str] | None = None,
    ) -> ContractGroupDetail:
        """
        获取合同组详情，包含：
          - 组内所有合同摘要
          - 派生状态（derived_status）
          - upstream / downstream contract_ids（按 group_relation_type 派生）
        """
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)
        self._assert_group_in_scope(
            group=group,
            group_id=group_id,
            binding_type=binding_type,
            effective_party_ids=effective_party_ids,
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
        binding_type: Literal["owner", "manager", "all"] | None = None,
        effective_party_ids: list[str] | None = None,
    ) -> tuple[list[ContractGroupListItem], int]:
        """分页查询合同组列表，返回含 derived_status 的列表项。"""
        normalized_effective_party_ids = self._normalize_effective_party_ids(
            effective_party_ids
        )
        normalized_binding_type = self._normalize_binding_type(binding_type)
        scoped_operator_party_ids: list[str] | None = None
        scoped_owner_party_ids: list[str] | None = None
        if binding_type == "all":
            if len(normalized_effective_party_ids) == 0:
                return [], 0
            scoped_operator_party_ids = normalized_effective_party_ids
            scoped_owner_party_ids = normalized_effective_party_ids
        elif normalized_binding_type == "manager":
            if len(normalized_effective_party_ids) == 0:
                return [], 0
            if (
                operator_party_id is not None
                and operator_party_id not in normalized_effective_party_ids
            ):
                return [], 0
            scoped_operator_party_ids = (
                [operator_party_id]
                if operator_party_id is not None
                else normalized_effective_party_ids
            )
        if normalized_binding_type == "owner":
            if len(normalized_effective_party_ids) == 0:
                return [], 0
            if (
                owner_party_id is not None
                and owner_party_id not in normalized_effective_party_ids
            ):
                return [], 0
            scoped_owner_party_ids = (
                [owner_party_id]
                if owner_party_id is not None
                else normalized_effective_party_ids
            )

        items, total = await contract_group_crud.list_by_filters(
            db,
            operator_party_id=operator_party_id,
            operator_party_ids=scoped_operator_party_ids,
            owner_party_id=owner_party_id,
            owner_party_ids=scoped_owner_party_ids,
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
            role_counts: dict[str, int] = {}
            for contract in contracts:
                try:
                    role = _normalize_enum_member(
                        GroupRelationType,
                        getattr(contract, "group_relation_type", None),
                    )
                except OperationNotAllowedError:
                    continue
                role_counts[role.name] = role_counts.get(role.name, 0) + 1
            group_dict = {
                col: getattr(group, col) for col in group.__table__.columns.keys()
            }
            group_dict["project_name"] = getattr(
                getattr(group, "project", None),
                "project_name",
                None,
            )
            group_dict["contract_role_counts"] = role_counts
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

        project_id = _normalize_required_project_id(group)
        revenue_mode = group.revenue_mode
        validate_revenue_mode_compatibility(revenue_mode, obj_in.group_relation_type)
        validate_sign_date_for_status(ContractLifecycleStatus.ACTIVE, obj_in.sign_date)
        await party_service.assert_parties_approved(
            db,
            party_ids=[
                obj_in.lessor_party_id,
                obj_in.lessee_party_id,
                group.operator_party_id,
                group.owner_party_id,
            ],
            operation="合同补录",
        )
        party_name_snapshots = await self._build_party_name_snapshots(
            db,
            lessor_party_id=obj_in.lessor_party_id,
            lessee_party_id=obj_in.lessee_party_id,
        )
        await self._ensure_contract_assets_within_group(
            db,
            group_id=obj_in.contract_group_id,
            asset_ids=obj_in.asset_ids,
        )
        existing_contract = await contract_crud.get_by_contract_number(
            db,
            contract_number=obj_in.contract_number,
            project_id=project_id,
        )
        if existing_contract is not None:
            raise DuplicateResourceError(
                "合同", "contract_number", obj_in.contract_number
            )

        now = _utcnow()
        data: dict[str, Any] = {
            "contract_id": str(uuid.uuid4()),
            "contract_group_id": obj_in.contract_group_id,
            "project_id": project_id,
            "contract_number": obj_in.contract_number,
            "contract_direction": obj_in.contract_direction.name,
            "group_relation_type": obj_in.group_relation_type.name,
            "lessor_party_id": obj_in.lessor_party_id,
            "lessee_party_id": obj_in.lessee_party_id,
            **party_name_snapshots,
            "sign_date": obj_in.sign_date,
            "effective_from": obj_in.effective_from,
            "effective_to": obj_in.effective_to,
            "currency_code": obj_in.currency_code,
            "tax_rate": obj_in.tax_rate,
            "is_tax_included": obj_in.is_tax_included,
            "status": ContractLifecycleStatus.ACTIVE.name,
            "contract_notes": obj_in.contract_notes,
            "source_session_id": obj_in.source_session_id,
            "data_status": "正常",
            "created_at": now,
            "updated_at": now,
            "created_by": current_user,
            "updated_by": current_user,
        }

        lease_detail_data = (
            obj_in.lease_detail.model_dump() if obj_in.lease_detail else None
        )
        lease_detail_data = self._sync_lease_detail_with_lessee_snapshot(
            lease_detail_data,
            lessee_name_snapshot=party_name_snapshots["lessee_name_snapshot"],
        )
        agency_detail_data = (
            obj_in.agency_detail.model_dump() if obj_in.agency_detail else None
        )

        created_contract = await contract_crud.create(
            db,
            data=data,
            lease_detail_data=lease_detail_data,
            agency_detail_data=agency_detail_data,
            asset_ids=obj_in.asset_ids or None,
            commit=False,
        )
        await ledger_service_v2.generate_ledger_on_activation(
            db,
            contract_id=created_contract.contract_id,
        )
        if commit:
            await db.commit()
        return created_contract

    async def get_contract_detail(
        self, db: AsyncSession, *, contract_id: str
    ) -> ContractDetail:
        """获取单合同详情（含明细）。"""
        contract = await contract_crud.get(db, contract_id, load_details=True)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        return ContractDetail.model_validate(contract)

    async def list_contract_scan_documents(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[ContractScanDocumentResponse]:
        await self._get_contract_or_raise(db, contract_id=contract_id)
        documents = await contract_crud.list_scan_documents_by_contract(
            db,
            contract_id=contract_id,
        )
        return [ContractScanDocumentResponse.model_validate(doc) for doc in documents]

    @staticmethod
    def _contract_uses_shared_scan_scope(contract: Contract) -> bool:
        contract_group = getattr(contract, "contract_group", None)
        return (
            contract.group_relation_type == GroupRelationType.ENTRUSTED
            and getattr(contract_group, "revenue_mode", None) == RevenueMode.AGENCY
        )

    async def list_shared_scan_affected_contract_ids(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[str]:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        if not self._contract_uses_shared_scan_scope(contract):
            return [contract.contract_id]

        sibling_contracts = await contract_crud.list_by_contract_number(
            db,
            contract_number=contract.contract_number,
            lessor_party_id=contract.lessor_party_id,
            lessee_party_id=contract.lessee_party_id,
            shared_scan_scope_only=True,
        )
        sibling_ids = [item.contract_id for item in sibling_contracts]
        if contract.contract_id not in sibling_ids:
            sibling_ids.append(contract.contract_id)
        return sorted(set(sibling_ids))

    async def _get_or_create_scan_documents(
        self,
        db: AsyncSession,
        *,
        documents: list[ContractScanDocumentCreate],
        affected_contract_ids: list[str],
        current_user: str | None,
    ) -> list[str]:
        document_ids: list[str] = []
        seen_storage_keys: set[str] = set()
        affected_contract_id_set = set(affected_contract_ids)
        now = _utcnow()
        for document in documents:
            storage_key = document.storage_key.strip()
            if storage_key in seen_storage_keys:
                continue
            seen_storage_keys.add(storage_key)
            existing = await contract_crud.get_scan_document_by_storage_key(
                db,
                storage_key=storage_key,
            )
            if existing is None:
                created = await contract_crud.create_scan_document(
                    db,
                    data={
                        "document_id": str(uuid.uuid4()),
                        "storage_key": storage_key,
                        "original_filename": document.original_filename,
                        "content_type": document.content_type,
                        "file_size": document.file_size,
                        "checksum_sha256": document.checksum_sha256,
                        "data_status": "正常",
                        "created_at": now,
                        "updated_at": now,
                        "created_by": current_user,
                        "updated_by": current_user,
                    },
                    commit=False,
                )
                document_ids.append(created.document_id)
                continue

            linked_contract_ids = (
                await contract_crud.list_contract_ids_linked_to_scan_document(
                    db,
                    document_id=existing.document_id,
                )
            )
            outside_scope_contract_ids = sorted(
                set(linked_contract_ids) - affected_contract_id_set
            )
            if outside_scope_contract_ids:
                raise OperationNotAllowedError(
                    "scan document is already linked outside affected contracts: "
                    + ", ".join(outside_scope_contract_ids),
                    reason="contract_scan_document_scope_conflict",
                    details={
                        "document_id": existing.document_id,
                        "storage_key": storage_key,
                        "outside_contract_ids": outside_scope_contract_ids,
                    },
                )

            await contract_crud.update_scan_document(
                db,
                db_obj=existing,
                data={
                    "original_filename": document.original_filename,
                    "content_type": document.content_type,
                    "file_size": document.file_size,
                    "checksum_sha256": document.checksum_sha256,
                    "updated_by": current_user,
                },
                commit=False,
            )
            document_ids.append(existing.document_id)
        return document_ids

    async def replace_contract_scan_documents(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        obj_in: ContractScanDocumentReplaceRequest,
        affected_contract_ids: list[str] | None = None,
        current_user: str | None = None,
        commit: bool = True,
    ) -> list[ContractScanDocumentResponse]:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        sibling_ids = affected_contract_ids
        if sibling_ids is None:
            sibling_ids = await self.list_shared_scan_affected_contract_ids(
                db,
                contract_id=contract.contract_id,
            )
        document_ids = await self._get_or_create_scan_documents(
            db,
            documents=obj_in.documents,
            affected_contract_ids=sibling_ids,
            current_user=current_user,
        )
        if not document_ids:
            raise OperationNotAllowedError(
                "contract scan document is required",
                reason="contract_scan_document_required",
            )

        await contract_crud.replace_scan_document_links_for_contracts(
            db,
            contract_ids=sibling_ids,
            document_ids=document_ids,
        )
        if commit:
            await db.commit()

        documents = await contract_crud.list_scan_documents_by_contract(
            db,
            contract_id=contract_id,
        )
        return [ContractScanDocumentResponse.model_validate(doc) for doc in documents]

    async def delete_contract_scan_document(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        document_id: str,
        affected_contract_ids: list[str] | None = None,
        commit: bool = True,
    ) -> None:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        sibling_ids = affected_contract_ids
        if sibling_ids is None:
            sibling_ids = await self.list_shared_scan_affected_contract_ids(
                db,
                contract_id=contract.contract_id,
            )
        linked_contract_ids = (
            await contract_crud.list_contract_ids_linked_to_scan_document(
                db,
                document_id=document_id,
                contract_ids=sibling_ids,
            )
        )
        if not linked_contract_ids:
            raise ResourceNotFoundError("contract scan document", document_id)

        counts = await contract_crud.count_scan_documents_by_contracts(
            db,
            contract_ids=linked_contract_ids,
        )
        would_be_empty = [
            linked_contract_id
            for linked_contract_id in linked_contract_ids
            if counts.get(linked_contract_id, 0) <= 1
        ]
        if would_be_empty:
            raise OperationNotAllowedError(
                "delete would leave contracts without scan documents: "
                + ", ".join(sorted(would_be_empty)),
                reason="contract_scan_document_required",
            )
        await contract_crud.unlink_scan_document_from_contracts(
            db,
            contract_ids=linked_contract_ids,
            document_id=document_id,
        )
        if commit:
            await db.commit()

    async def list_contract_audit_logs(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> list[AuditLogResponse]:
        await self._get_contract_or_raise(db, contract_id=contract_id)
        logs = await contract_group_crud.list_contract_audit_logs(
            db,
            contract_id=contract_id,
        )
        return [AuditLogResponse.model_validate(log) for log in logs]

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

    async def finalize_correction(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None = None,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        correction_source_contract = await self._get_correction_source_contract(
            db,
            contract=contract,
        )
        if correction_source_contract is None:
            raise OperationNotAllowedError("仅纠错草稿允许定稿")

        correction_reason = (reason or "").strip() or "纠错定稿"
        party_name_snapshots = await self._build_party_name_snapshots(
            db,
            lessor_party_id=contract.lessor_party_id,
            lessee_party_id=contract.lessee_party_id,
        )
        lease_detail = getattr(contract, "lease_detail", None)
        if lease_detail is not None:
            lease_detail.tenant_name = party_name_snapshots["lessee_name_snapshot"]
        correction_effective_month = await self._get_correction_effective_month(
            db,
            contract=contract,
        )
        voided_entry_ids = await ledger_service_v2.reverse_correction_source_entries(
            db,
            contract_id=correction_source_contract.contract_id,
            year_month_start=correction_effective_month,
        )
        await self._transition_contract(
            db,
            contract=correction_source_contract,
            allowed_statuses={
                ContractLifecycleStatus.ACTIVE,
                ContractLifecycleStatus.TERMINATED,
            },
            action="finalize_correction",
            new_status=ContractLifecycleStatus.TERMINATED,
            current_user=current_user,
            operator_name=operator_name,
            reason=correction_reason,
            context={
                "affected_contract_ids": [
                    correction_source_contract.contract_id,
                    contract.contract_id,
                ],
                "correction_source_contract_id": correction_source_contract.contract_id,
                "voided_entry_ids": voided_entry_ids,
            },
            commit=False,
        )
        updated_contract = await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.DRAFT},
            action="finalize_correction",
            new_status=ContractLifecycleStatus.ACTIVE,
            current_user=current_user,
            operator_name=operator_name,
            reason=correction_reason,
            extra_updates=party_name_snapshots,
            commit=False,
        )
        await ledger_service_v2.generate_ledger_on_activation(
            db,
            contract_id=contract_id,
        )
        if commit:
            await db.commit()
        return updated_contract

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
            },
            action="terminate",
            new_status=ContractLifecycleStatus.TERMINATED,
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
        updated_contract = await contract_crud.update(
            db,
            db_obj=contract,
            data={
                "data_status": "已作废",
                "updated_by": current_user,
            },
            commit=False,
        )
        await self._append_audit_log(
            db,
            contract=updated_contract,
            action="void",
            old_status=old_status,
            new_status=old_status,
            reason=normalized_reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
        )
        await db.commit()
        return updated_contract

    # ─── Rent Terms ─────────────────────────────────────────────────────

    async def create_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        obj_in: ContractRentTermCreate,
        commit: bool = True,
    ) -> ContractRentTerm:
        await self._require_draft_contract_for_mutation(db, contract_id=contract_id)
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
        await self._require_draft_contract_for_mutation(db, contract_id=contract_id)
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
        await self._require_draft_contract_for_mutation(db, contract_id=contract_id)
        rent_term = await contract_group_crud.get_rent_term(
            db, rent_term_id=rent_term_id
        )
        if rent_term is None or rent_term.contract_id != contract_id:
            raise ResourceNotFoundError("租金条款", rent_term_id)
        await contract_group_crud.delete_rent_term(db, db_obj=rent_term)


contract_group_service = ContractGroupService()
