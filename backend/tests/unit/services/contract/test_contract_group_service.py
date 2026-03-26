"""
单元测试：ContractGroupService — 纯函数与业务规则校验。

覆盖范围：
  - calculate_derived_status（B3/B4/B5/B6）
  - validate_revenue_mode_compatibility（B1/B2）
  - validate_sign_date_for_status（B8）
  - SettlementRuleSchema 必填键校验（B7）
  - generate_group_code（编码格式）
  - ContractCreate 基本 schema 校验
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
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
    LeaseDetailCreate,
    SettlementRuleSchema,
)
from src.services.contract.contract_group_service import (
    ContractGroupService,
    _build_operator_code_segment,
    calculate_derived_status,
    validate_revenue_mode_compatibility,
    validate_sign_date_for_status,
)

pytestmark = pytest.mark.asyncio


# ─── helpers ──────────────────────────────────────────────────────────────────


def _make_contract(
    status: ContractLifecycleStatus,
    data_status: str = "正常",
    group_relation_type: GroupRelationType = GroupRelationType.UPSTREAM,
) -> MagicMock:
    c = MagicMock(spec=Contract)
    c.status = status
    c.data_status = data_status
    c.group_relation_type = group_relation_type  # 枚举成员，非字符串
    return c


def _valid_settlement_rule() -> dict:
    return {
        "version": "v1",
        "cycle": "月付",
        "settlement_mode": "fixed",
        "amount_rule": {"base": 1000},
        "payment_rule": {"day": 5},
    }


def _valid_group_create(**kwargs) -> ContractGroupCreate:
    defaults = dict(
        revenue_mode=RevenueMode.LEASE,
        operator_party_id="party_op",
        owner_party_id="party_ow",
        effective_from=date(2026, 1, 1),
        settlement_rule=SettlementRuleSchema(**_valid_settlement_rule()),
    )
    defaults.update(kwargs)
    return ContractGroupCreate(**defaults)


def _valid_contract_create(**kwargs) -> ContractCreate:
    from src.models.contract_group import ContractDirection

    defaults = dict(
        contract_group_id="group_001",
        contract_number="HT-2026-0001",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id="party_lessor",
        lessee_party_id="party_lessee",
        effective_from=date(2026, 1, 1),
        lease_detail=LeaseDetailCreate(rent_amount=Decimal("10000")),
    )
    defaults.update(kwargs)
    return ContractCreate(**defaults)


# ─── calculate_derived_status ─────────────────────────────────────────────────


class TestCalculateDerivedStatus:
    def test_b3_no_contracts_returns_preparing(self):
        """B3: 合同组内无任何合同 → 筹备中"""
        assert calculate_derived_status([]) == "筹备中"

    def test_b4_all_draft_returns_preparing(self):
        """B4: 所有合同均为草稿 → 筹备中"""
        contracts = [_make_contract(ContractLifecycleStatus.DRAFT) for _ in range(3)]
        assert calculate_derived_status(contracts) == "筹备中"

    def test_b5_one_active_returns_active(self):
        """B5: 有一条合同处于生效，其他已到期 → 生效中"""
        contracts = [
            _make_contract(ContractLifecycleStatus.ACTIVE),
            _make_contract(ContractLifecycleStatus.EXPIRED),
            _make_contract(ContractLifecycleStatus.EXPIRED),
        ]
        assert calculate_derived_status(contracts) == "生效中"

    def test_b6_all_expired_or_terminated_returns_ended(self):
        """B6: 所有合同均已终止或已到期 → 已结束"""
        contracts = [
            _make_contract(ContractLifecycleStatus.EXPIRED),
            _make_contract(ContractLifecycleStatus.TERMINATED),
        ]
        assert calculate_derived_status(contracts) == "已结束"

    def test_pending_review_still_preparing(self):
        """待审状态不触发生效中（只有 ACTIVE 才算）"""
        contracts = [_make_contract(ContractLifecycleStatus.PENDING_REVIEW)]
        assert calculate_derived_status(contracts) == "筹备中"

    def test_deleted_contracts_excluded(self):
        """已删除合同不参与计算"""
        contracts = [
            _make_contract(ContractLifecycleStatus.ACTIVE, data_status="已删除"),
        ]
        assert calculate_derived_status(contracts) == "筹备中"

    def test_mixed_active_and_terminated(self):
        """生效与终止并存 → 生效中（ACTIVE 优先）"""
        contracts = [
            _make_contract(ContractLifecycleStatus.ACTIVE),
            _make_contract(ContractLifecycleStatus.TERMINATED),
        ]
        assert calculate_derived_status(contracts) == "生效中"


# ─── validate_revenue_mode_compatibility ─────────────────────────────────────


class TestRevenueModeCompatibility:
    def test_b1_lease_mode_with_entrusted_raises(self):
        """B1: 承租模式下使用委托角色 → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError, match="承租模式"):
            validate_revenue_mode_compatibility(
                RevenueMode.LEASE, GroupRelationType.ENTRUSTED
            )

    def test_b1_lease_mode_with_direct_lease_raises(self):
        """B1: 承租模式下使用直租角色 → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError):
            validate_revenue_mode_compatibility(
                RevenueMode.LEASE, GroupRelationType.DIRECT_LEASE
            )

    def test_b2_agency_mode_with_upstream_raises(self):
        """B2: 代理模式下使用上游角色 → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError, match="代理模式"):
            validate_revenue_mode_compatibility(
                RevenueMode.AGENCY, GroupRelationType.UPSTREAM
            )

    def test_b2_agency_mode_with_downstream_raises(self):
        """B2: 代理模式下使用下游角色 → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError):
            validate_revenue_mode_compatibility(
                RevenueMode.AGENCY, GroupRelationType.DOWNSTREAM
            )

    def test_lease_upstream_is_valid(self):
        validate_revenue_mode_compatibility(
            RevenueMode.LEASE, GroupRelationType.UPSTREAM
        )  # 不抛异常

    def test_lease_downstream_is_valid(self):
        validate_revenue_mode_compatibility(
            RevenueMode.LEASE, GroupRelationType.DOWNSTREAM
        )

    def test_agency_entrusted_is_valid(self):
        validate_revenue_mode_compatibility(
            RevenueMode.AGENCY, GroupRelationType.ENTRUSTED
        )

    def test_agency_direct_lease_is_valid(self):
        validate_revenue_mode_compatibility(
            RevenueMode.AGENCY, GroupRelationType.DIRECT_LEASE
        )

    def test_string_enum_names_from_db_are_normalized(self):
        validate_revenue_mode_compatibility("LEASE", "UPSTREAM")


# ─── validate_sign_date_for_status ───────────────────────────────────────────


class TestValidateSignDate:
    def test_b8_pending_review_without_sign_date_raises(self):
        """B8: 待审且 sign_date=None → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError, match="sign_date"):
            validate_sign_date_for_status(
                ContractLifecycleStatus.PENDING_REVIEW, None
            )

    def test_b8_active_without_sign_date_raises(self):
        """B8: 生效且 sign_date=None → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError, match="sign_date"):
            validate_sign_date_for_status(ContractLifecycleStatus.ACTIVE, None)

    def test_draft_without_sign_date_ok(self):
        """草稿状态 sign_date 可为空"""
        validate_sign_date_for_status(ContractLifecycleStatus.DRAFT, None)

    def test_active_with_sign_date_ok(self):
        """生效状态且有 sign_date 不报错"""
        validate_sign_date_for_status(
            ContractLifecycleStatus.ACTIVE, date(2026, 1, 1)
        )


# ─── SettlementRuleSchema ─────────────────────────────────────────────────────


class TestSettlementRuleSchema:
    def test_valid_rule_passes(self):
        rule = SettlementRuleSchema(**_valid_settlement_rule())
        assert rule.version == "v1"
        assert rule.cycle == "月付"

    def test_b7_missing_payment_rule_raises(self):
        """B7: 缺少 payment_rule → ValidationError"""
        data = _valid_settlement_rule()
        del data["payment_rule"]
        with pytest.raises(ValidationError) as exc_info:
            SettlementRuleSchema(**data)
        assert "payment_rule" in str(exc_info.value)

    def test_b7_missing_amount_rule_raises(self):
        data = _valid_settlement_rule()
        del data["amount_rule"]
        with pytest.raises(ValidationError):
            SettlementRuleSchema(**data)

    def test_b7_missing_version_raises(self):
        data = _valid_settlement_rule()
        del data["version"]
        with pytest.raises(ValidationError):
            SettlementRuleSchema(**data)

    def test_b7_invalid_cycle_raises(self):
        data = _valid_settlement_rule()
        data["cycle"] = "不合法周期"
        with pytest.raises(ValidationError, match="invalid_payment_cycle"):
            SettlementRuleSchema(**data)

    def test_all_valid_cycles(self):
        for cycle in ("月付", "季付", "半年付", "年付"):
            data = _valid_settlement_rule()
            data["cycle"] = cycle
            rule = SettlementRuleSchema(**data)
            assert rule.cycle == cycle


# ─── _build_operator_code_segment ────────────────────────────────────────────


class TestBuildOperatorCodeSegment:
    def test_short_code_padded_with_x(self):
        assert _build_operator_code_segment("ABCD") == "ABCDXXXX"

    def test_exactly_8_chars_unchanged(self):
        assert _build_operator_code_segment("OPER0001") == "OPER0001"

    def test_longer_than_8_truncated(self):
        assert len(_build_operator_code_segment("ABCDEFGHIJ")) == 8

    def test_lowercase_converted(self):
        result = _build_operator_code_segment("abcd")
        assert result == "ABCDXXXX"

    def test_special_chars_stripped(self):
        result = _build_operator_code_segment("AB-CD_EF")
        assert result == "ABCDEFXX"


# ─── generate_group_code ─────────────────────────────────────────────────────


class TestGenerateGroupCode:
    async def test_code_format(self, mock_db: MagicMock):
        service = ContractGroupService()
        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.count_by_operator_month",
            new_callable=AsyncMock,
            return_value=0,
        ):
            code = await service.generate_group_code(
                mock_db,
                operator_party_id="party_001",
                operator_party_code="OPER0001",
            )
        import re

        assert re.match(r"^GRP-[A-Z0-9]{8}-\d{6}-\d{4}$", code), f"格式不符：{code}"

    async def test_seq_increments(self, mock_db: MagicMock):
        service = ContractGroupService()
        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.count_by_operator_month",
            new_callable=AsyncMock,
            return_value=5,
        ):
            code = await service.generate_group_code(
                mock_db,
                operator_party_id="party_001",
                operator_party_code="OPER0001",
            )
        assert code.endswith("-0006")


# ─── create_contract_group（duplicate check）─────────────────────────────────


class TestCreateContractGroupDuplicateCheck:
    async def test_b12_duplicate_code_raises(self, mock_db: MagicMock):
        """B12: group_code 重复 → DuplicateResourceError"""
        service = ContractGroupService()
        existing = MagicMock()

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=existing,
        ):
            with pytest.raises(DuplicateResourceError):
                await service.create_contract_group(
                    mock_db,
                    obj_in=_valid_group_create(),
                    group_code="GRP-TEST",
                )

    async def test_new_group_created_ok(self, mock_db: MagicMock):
        service = ContractGroupService()
        created_group = MagicMock()
        created_group.contract_group_id = "grp_001"

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.services.contract.contract_group_service.contract_group_crud.create",
                new_callable=AsyncMock,
                return_value=created_group,
            ):
                result = await service.create_contract_group(
                    mock_db,
                    obj_in=_valid_group_create(),
                    group_code="GRP-NEW",
                )
        assert result.contract_group_id == "grp_001"


class TestPerspectiveScopedContractGroups:
    async def test_list_groups_should_apply_manager_effective_party_ids(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.list_by_filters",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_list_by_filters:
            result = await service.list_groups(
                mock_db,
                perspective="manager",
                effective_party_ids=["manager-1"],
            )

        assert result == ([], 0)
        assert mock_list_by_filters.await_args.kwargs["operator_party_ids"] == [
            "manager-1"
        ]

    async def test_get_group_detail_should_fail_closed_when_owner_scope_mismatches(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        group = MagicMock(spec=ContractGroup)
        group.contract_group_id = "group-1"
        group.owner_party_id = "owner-2"
        group.operator_party_id = "manager-1"

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.get",
            new_callable=AsyncMock,
            return_value=group,
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.get_group_detail(
                    mock_db,
                    group_id="group-1",
                    perspective="owner",
                    effective_party_ids=["owner-1"],
                )


# ─── add_contract_to_group（integration of business rules）───────────────────


class TestAddContractToGroup:
    def test_contract_create_requires_contract_number(self):
        """合同创建入参必须显式提供 contract_number。"""
        with pytest.raises(ValidationError) as exc_info:
            _valid_contract_create(contract_number=None)
        assert "contract_number" in str(exc_info.value)

    async def test_b1_lease_group_rejects_entrusted_contract(
        self, mock_db: MagicMock
    ):
        """B1: LEASE 合同组不允许添加 ENTRUSTED 角色合同"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.get",
            new_callable=AsyncMock,
            return_value=mock_group,
        ):
            contract_in = _valid_contract_create(
                group_relation_type=GroupRelationType.ENTRUSTED
            )
            with pytest.raises(OperationNotAllowedError, match="承租模式"):
                await service.add_contract_to_group(
                    mock_db, obj_in=contract_in
                )

    async def test_b8_active_contract_without_sign_date_raises(
        self, mock_db: MagicMock
    ):
        """B8: 合同状态为 ACTIVE 但 sign_date=None → OperationNotAllowedError"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE

        with patch(
            "src.services.contract.contract_group_service.contract_group_crud.get",
            new_callable=AsyncMock,
            return_value=mock_group,
        ):
            contract_in = _valid_contract_create(
                status=ContractLifecycleStatus.ACTIVE,
                sign_date=None,
            )
            with pytest.raises(OperationNotAllowedError, match="sign_date"):
                await service.add_contract_to_group(
                    mock_db, obj_in=contract_in
                )

    async def test_duplicate_contract_number_raises(
        self, mock_db: MagicMock
    ):
        """重复 contract_number 应在 Service 层直接拦截。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        existing_contract = MagicMock(spec=Contract)

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_by_contract_number",
                new_callable=AsyncMock,
                return_value=existing_contract,
            ),
        ):
            with pytest.raises(DuplicateResourceError):
                await service.add_contract_to_group(
                    mock_db,
                    obj_in=_valid_contract_create(contract_number="HT-DUP-001"),
                )

    async def test_add_contract_passes_contract_number_to_crud(
        self, mock_db: MagicMock
    ):
        """创建合同时必须把 contract_number 写入新 contracts 基表。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-001"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_by_contract_number",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.create",
                new_callable=AsyncMock,
                return_value=created_contract,
            ) as mock_create,
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(contract_number="HT-2026-0099"),
            )

        assert result.contract_id == "contract-001"
        assert mock_create.await_args.kwargs["data"]["contract_number"] == "HT-2026-0099"


class TestSubmitReviewRequiresApprovedParties:
    async def test_submit_review_should_block_when_related_party_not_approved(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        contract = MagicMock(spec=Contract)
        contract.contract_id = "contract-001"
        contract.contract_group_id = "group-001"
        contract.sign_date = date(2026, 1, 1)
        contract.status = ContractLifecycleStatus.DRAFT
        contract.lessor_party_id = "party-lessor"
        contract.lessee_party_id = "party-lessee"

        group = SimpleNamespace(
            contract_group_id="group-001",
            operator_party_id="party-operator",
            owner_party_id="party-owner",
        )

        with (
            patch.object(service, "_get_contract_or_raise", AsyncMock(return_value=contract)),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=group,
            ),
            patch.object(
                mock_db,
                "execute",
                new=AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                side_effect=OperationNotAllowedError("存在未审核主体"),
            ) as mock_assert,
            patch.object(service, "_transition_contract", AsyncMock()) as mock_transition,
        ):
            with pytest.raises(OperationNotAllowedError, match="未审核主体"):
                await service.submit_review(mock_db, contract_id="contract-001")

        mock_assert.assert_awaited_once_with(
            mock_db,
            party_ids=[
                "party-lessor",
                "party-lessee",
                "party-operator",
                "party-owner",
            ],
            operation="合同提审",
        )
        mock_transition.assert_not_awaited()

    async def test_submit_review_should_transition_when_all_related_parties_approved(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        contract = MagicMock(spec=Contract)
        contract.contract_id = "contract-001"
        contract.contract_group_id = "group-001"
        contract.sign_date = date(2026, 1, 1)
        contract.status = ContractLifecycleStatus.DRAFT
        contract.lessor_party_id = "party-lessor"
        contract.lessee_party_id = "party-lessee"

        group = SimpleNamespace(
            contract_group_id="group-001",
            operator_party_id="party-operator",
            owner_party_id="party-owner",
        )

        with (
            patch.object(service, "_get_contract_or_raise", AsyncMock(return_value=contract)),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=group,
            ),
            patch.object(
                mock_db,
                "execute",
                new=AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_assert,
            patch.object(service, "_transition_contract", AsyncMock(return_value=contract)) as mock_transition,
        ):
            result = await service.submit_review(mock_db, contract_id="contract-001")

        assert result == (contract, [])
        mock_assert.assert_awaited_once()
        mock_transition.assert_awaited_once()
