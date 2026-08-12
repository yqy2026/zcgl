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

from datetime import date, datetime
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
from src.models.project import Project
from src.schemas.contract_group import (
    ContractCreate,
    ContractDetail,
    ContractGroupCreate,
    ContractRentTermCreate,
    ContractScanDocumentCreate,
    ContractScanDocumentReplaceRequest,
    ContractSummary,
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
    effective_to: date | None = None,
) -> MagicMock:
    c = MagicMock(spec=Contract)
    c.status = status
    c.data_status = data_status
    c.group_relation_type = group_relation_type  # 枚举成员，非字符串
    c.effective_to = effective_to
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
        project_id="project-1",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id="party_op",
        owner_party_id="party_ow",
        effective_from=date(2026, 1, 1),
        settlement_rule=SettlementRuleSchema(**_valid_settlement_rule()),
    )
    defaults.update(kwargs)
    return ContractGroupCreate(**defaults)


def _valid_group_create_payload(**kwargs) -> dict:
    defaults = dict(
        project_id="project-1",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id="party_op",
        owner_party_id="party_ow",
        effective_from=date(2026, 1, 1),
    )
    defaults.update(kwargs)
    return defaults


def _valid_contract_create(**kwargs) -> ContractCreate:
    from src.models.contract_group import ContractDirection

    defaults = dict(
        contract_group_id="group_001",
        contract_number="HT-2026-0001",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id="party_lessor",
        lessee_party_id="party_lessee",
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        lease_detail=LeaseDetailCreate(rent_amount=Decimal("10000")),
    )
    defaults.update(kwargs)
    return ContractCreate(**defaults)


def _party_name_lookup() -> AsyncMock:
    names = {
        "party_lessor": "出租方签署名",
        "party_lessee": "承租方签署名",
        "party-operator": "运营方签署名",
        "party-owner": "产权方签署名",
    }

    async def _get_party(_db: MagicMock, *, party_id: str) -> SimpleNamespace:
        return SimpleNamespace(id=party_id, name=names.get(party_id, party_id))

    return AsyncMock(side_effect=_get_party)


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
        """B5: 有一条合同处于生效，其他自然到期 → 生效中"""
        contracts = [
            _make_contract(ContractLifecycleStatus.ACTIVE),
            _make_contract(
                ContractLifecycleStatus.ACTIVE, effective_to=date(2026, 1, 1)
            ),
            _make_contract(
                ContractLifecycleStatus.ACTIVE, effective_to=date(2026, 1, 2)
            ),
        ]
        assert calculate_derived_status(contracts) == "生效中"

    def test_b6_all_naturally_expired_or_terminated_returns_ended(self):
        """B6: 所有合同均已终止或自然到期 → 已结束"""
        contracts = [
            _make_contract(
                ContractLifecycleStatus.ACTIVE, effective_to=date(2026, 1, 1)
            ),
            _make_contract(ContractLifecycleStatus.TERMINATED),
        ]
        assert calculate_derived_status(contracts) == "已结束"

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
    def test_b8_active_without_sign_date_raises(self):
        """B8: 生效且 sign_date=None → OperationNotAllowedError"""
        with pytest.raises(OperationNotAllowedError, match="sign_date"):
            validate_sign_date_for_status(ContractLifecycleStatus.ACTIVE, None)

    def test_draft_without_sign_date_ok(self):
        """草稿状态 sign_date 可为空"""
        validate_sign_date_for_status(ContractLifecycleStatus.DRAFT, None)

    def test_active_with_sign_date_ok(self):
        """生效状态且有 sign_date 不报错"""
        validate_sign_date_for_status(ContractLifecycleStatus.ACTIVE, date(2026, 1, 1))


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
    def test_contract_group_create_allows_missing_settlement_rule(self):
        group = ContractGroupCreate(**_valid_group_create_payload())

        assert group.settlement_rule is None

    def test_contract_group_create_allows_null_settlement_rule(self):
        group = ContractGroupCreate(**_valid_group_create_payload(settlement_rule=None))

        assert group.settlement_rule is None

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
            ) as mock_create:
                result = await service.create_contract_group(
                    mock_db,
                    obj_in=_valid_group_create(),
                    group_code="GRP-NEW",
                )
        assert result.contract_group_id == "grp_001"
        assert mock_create.await_args.kwargs["data"]["project_id"] == "project-1"

    async def test_create_group_persists_null_settlement_rule(self, mock_db: MagicMock):
        service = ContractGroupService()
        created_group = MagicMock()
        created_group.contract_group_id = "grp_001"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create",
                new_callable=AsyncMock,
                return_value=created_group,
            ) as mock_create,
        ):
            result = await service.create_contract_group(
                mock_db,
                obj_in=ContractGroupCreate(**_valid_group_create_payload()),
                group_code="GRP-NEW",
            )

        assert result.contract_group_id == "grp_001"
        data = mock_create.await_args.kwargs["data"]
        assert data["settlement_rule"] is None
        assert "predecessor_group_id" not in data
        assert "version" not in data

    async def test_create_group_should_reject_assets_already_bound_elsewhere(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-1", "project_id": "project-1"}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_active_group_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "asset_id": "asset-1",
                        "project_id": "other-project",
                        "contract_group_id": "group-existing",
                        "group_code": "GRP-EXISTING",
                    }
                ],
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="asset-1"):
                await service.create_contract_group(
                    mock_db,
                    obj_in=_valid_group_create(asset_ids=["asset-1"]),
                    group_code="GRP-NEW",
                )

    async def test_create_group_should_reject_asset_outside_group_project(
        self, mock_db: MagicMock
    ) -> None:
        """C5: 合同关系覆盖资产必须属于该关系所属项目。"""
        service = ContractGroupService()

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-1", "project_id": "other-project"}],
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="asset-1"):
                await service.create_contract_group(
                    mock_db,
                    obj_in=_valid_group_create(asset_ids=["asset-1"]),
                    group_code="GRP-NEW",
                )

    async def test_update_group_should_reject_asset_outside_group_project(
        self, mock_db: MagicMock
    ) -> None:
        """C5: 编辑合同关系资产时仍按当前项目归属校验。"""
        service = ContractGroupService()
        existing_group = MagicMock()
        existing_group.contract_group_id = "group-current"
        existing_group.project_id = "project-1"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=existing_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-2", "project_id": "other-project"}],
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="asset-2"):
                await service.update_contract_group(
                    mock_db,
                    group_id="group-current",
                    obj_in=SimpleNamespace(
                        asset_ids=["asset-2"],
                        model_fields_set={"asset_ids"},
                        settlement_rule=None,
                        effective_to=None,
                        revenue_attribution_rule=None,
                        revenue_share_rule=None,
                        risk_tags=None,
                    ),
                )

    async def test_create_group_should_allow_assets_bound_in_same_project(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        created_group = MagicMock()
        created_group.contract_group_id = "group-new"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_by_code",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-1", "project_id": "project-1"}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_active_group_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "asset_id": "asset-1",
                        "project_id": "project-1",
                        "contract_group_id": "group-existing",
                        "group_code": "GRP-EXISTING",
                    }
                ],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create",
                new_callable=AsyncMock,
                return_value=created_group,
            ) as mock_create,
        ):
            result = await service.create_contract_group(
                mock_db,
                obj_in=_valid_group_create(asset_ids=["asset-1"]),
                group_code="GRP-NEW",
            )

        assert result.contract_group_id == "group-new"
        mock_create.assert_awaited_once()

    async def test_update_group_should_reject_assets_already_bound_elsewhere(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        existing_group = MagicMock()
        existing_group.contract_group_id = "group-current"
        existing_group.project_id = "project-1"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=existing_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-2", "project_id": "project-1"}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_active_group_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "asset_id": "asset-2",
                        "project_id": "other-project",
                        "contract_group_id": "group-other",
                        "group_code": "GRP-OTHER",
                    }
                ],
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="asset-2"):
                await service.update_contract_group(
                    mock_db,
                    group_id="group-current",
                    obj_in=SimpleNamespace(
                        asset_ids=["asset-2"],
                        model_fields_set={"asset_ids"},
                        settlement_rule=None,
                        effective_to=None,
                        revenue_attribution_rule=None,
                        revenue_share_rule=None,
                        risk_tags=None,
                    ),
                )

    async def test_update_group_should_reject_when_existing_contract_assets_exceed_new_scope(
        self, mock_db: MagicMock
    ) -> None:
        """C6: 缩小合同关系资产范围不得挤出已有合同显式覆盖资产。"""
        service = ContractGroupService()
        existing_group = MagicMock()
        existing_group.contract_group_id = "group-current"
        existing_group.project_id = "project-1"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=existing_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-1", "project_id": "project-1"}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_active_group_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_contract_asset_ids_by_group",
                new_callable=AsyncMock,
                return_value=[{"contract_id": "contract-1", "asset_ids": ["asset-2"]}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.update",
                new_callable=AsyncMock,
            ) as mock_update,
        ):
            with pytest.raises(OperationNotAllowedError, match="contract-1"):
                await service.update_contract_group(
                    mock_db,
                    group_id="group-current",
                    obj_in=SimpleNamespace(
                        asset_ids=["asset-1"],
                        model_fields_set={"asset_ids"},
                        settlement_rule=None,
                        effective_to=None,
                        revenue_attribution_rule=None,
                        revenue_share_rule=None,
                        risk_tags=None,
                    ),
                )

        mock_update.assert_not_awaited()

    async def test_update_group_should_clear_settlement_rule_when_explicit_null(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        existing_group = MagicMock()
        existing_group.contract_group_id = "group-current"
        existing_group.project_id = "project-1"
        updated_group = MagicMock()
        updated_group.contract_group_id = "group-current"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=existing_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.update",
                new_callable=AsyncMock,
                return_value=updated_group,
            ) as mock_update,
        ):
            result = await service.update_contract_group(
                mock_db,
                group_id="group-current",
                obj_in=SimpleNamespace(
                    asset_ids=None,
                    model_fields_set={"settlement_rule"},
                    settlement_rule=None,
                    effective_to=None,
                    revenue_attribution_rule=None,
                    revenue_share_rule=None,
                    risk_tags=None,
                ),
            )

        assert result.contract_group_id == "group-current"
        assert mock_update.await_args.kwargs["data"] == {"settlement_rule": None}

    async def test_update_group_should_allow_assets_bound_in_same_project(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        existing_group = MagicMock()
        existing_group.contract_group_id = "group-current"
        existing_group.project_id = "project-1"
        updated_group = MagicMock()
        updated_group.contract_group_id = "group-current"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=existing_group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_current_project_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[{"asset_id": "asset-2", "project_id": "project-1"}],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_active_group_bindings_for_assets",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "asset_id": "asset-2",
                        "project_id": "project-1",
                        "contract_group_id": "group-other",
                        "group_code": "GRP-OTHER",
                    }
                ],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_contract_asset_ids_by_group",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.update",
                new_callable=AsyncMock,
                return_value=updated_group,
            ) as mock_update,
        ):
            result = await service.update_contract_group(
                mock_db,
                group_id="group-current",
                obj_in=SimpleNamespace(
                    asset_ids=["asset-2"],
                    model_fields_set={"asset_ids"},
                    settlement_rule=None,
                    effective_to=None,
                    revenue_attribution_rule=None,
                    revenue_share_rule=None,
                    risk_tags=None,
                ),
            )

        assert result.contract_group_id == "group-current"
        mock_update.assert_awaited_once()


class TestPerspectiveScopedContractGroups:
    async def test_list_groups_enriches_project_name_and_contract_role_counts(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        group = ContractGroup(
            contract_group_id="group-1",
            project_id="project-1",
            group_code="GRP-TEST-202605-0001",
            revenue_mode=RevenueMode.LEASE,
            operator_party_id="manager-1",
            owner_party_id="owner-1",
            effective_from=date(2026, 5, 1),
            effective_to=None,
            settlement_rule=_valid_settlement_rule(),
            data_status="正常",
            created_at=datetime(2026, 5, 1),
            updated_at=datetime(2026, 5, 2),
        )
        group.project = Project(
            id="project-1",
            project_name="项目A",
            project_code="PRJ-A",
            status="active",
            data_status="正常",
        )
        contracts = [
            _make_contract(
                ContractLifecycleStatus.ACTIVE,
                group_relation_type=GroupRelationType.UPSTREAM,
            ),
            _make_contract(
                ContractLifecycleStatus.DRAFT,
                group_relation_type=GroupRelationType.DOWNSTREAM,
            ),
            _make_contract(
                ContractLifecycleStatus.DRAFT,
                group_relation_type=GroupRelationType.DOWNSTREAM,
            ),
        ]

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_by_filters",
                new_callable=AsyncMock,
                return_value=([group], 1),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_group",
                new_callable=AsyncMock,
                return_value=contracts,
            ),
        ):
            result, total = await service.list_groups(mock_db)

        assert total == 1
        assert result[0].project_name == "项目A"
        assert result[0].contract_role_counts == {
            "UPSTREAM": 1,
            "DOWNSTREAM": 2,
        }

    async def test_list_groups_should_apply_any_scope_effective_party_ids(
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
                binding_type="all",
                effective_party_ids=["owner-1", "manager-1"],
            )

        assert result == ([], 0)
        assert mock_list_by_filters.await_args.kwargs["operator_party_ids"] == [
            "owner-1",
            "manager-1",
        ]
        assert mock_list_by_filters.await_args.kwargs["owner_party_ids"] == [
            "owner-1",
            "manager-1",
        ]

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
                binding_type="manager",
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
                    binding_type="owner",
                    effective_party_ids=["owner-1"],
                )

    async def test_get_group_detail_should_allow_any_scope_when_owner_matches(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        group = MagicMock(spec=ContractGroup)
        group.contract_group_id = "group-1"
        group.owner_party_id = "owner-1"
        group.operator_party_id = "manager-2"
        group.__table__.columns.keys.return_value = [
            "contract_group_id",
            "owner_party_id",
            "operator_party_id",
        ]
        contracts: list[Contract] = []

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=group,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_group",
                new_callable=AsyncMock,
                return_value=contracts,
            ),
            patch(
                "src.services.contract.contract_group_service.ContractSummary.model_validate",
                side_effect=lambda contract: contract,
            ),
            patch(
                "src.services.contract.contract_group_service.ContractGroupDetail",
                side_effect=lambda **kwargs: SimpleNamespace(**kwargs),
            ),
        ):
            result = await service.get_group_detail(
                mock_db,
                group_id="group-1",
                binding_type="all",
                effective_party_ids=["owner-1", "manager-1"],
            )

        assert result.contract_group_id == "group-1"


# ─── add_contract_to_group（integration of business rules）───────────────────


class TestAddContractToGroup:
    def test_contract_create_requires_contract_number(self):
        """合同创建入参必须显式提供 contract_number。"""
        with pytest.raises(ValidationError) as exc_info:
            _valid_contract_create(contract_number=None)
        assert "contract_number" in str(exc_info.value)

    async def test_b1_lease_group_rejects_entrusted_contract(self, mock_db: MagicMock):
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
                await service.add_contract_to_group(mock_db, obj_in=contract_in)

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
                await service.add_contract_to_group(mock_db, obj_in=contract_in)

    async def test_duplicate_contract_number_raises(self, mock_db: MagicMock):
        """重复 contract_number 应在 Service 层直接拦截。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        existing_contract = MagicMock(spec=Contract)

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_by_contract_number",
                new_callable=AsyncMock,
                return_value=existing_contract,
            ) as mock_get_by_number,
        ):
            with pytest.raises(DuplicateResourceError):
                await service.add_contract_to_group(
                    mock_db,
                    obj_in=_valid_contract_create(contract_number="HT-DUP-001"),
                )
        mock_get_by_number.assert_awaited_once_with(
            mock_db,
            contract_number="HT-DUP-001",
            project_id="project-1",
        )

    async def test_duplicate_contract_number_in_other_project_is_allowed(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-2"
        mock_group.operator_party_id = "party-operator"
        mock_group.owner_party_id = "party-owner"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-002"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_by_contract_number",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_get_by_number,
            patch(
                "src.services.contract.contract_group_service.contract_crud.create",
                new_callable=AsyncMock,
                return_value=created_contract,
            ) as mock_create,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(contract_number="HT-SHARED-001"),
            )

        assert result is created_contract
        mock_get_by_number.assert_awaited_once_with(
            mock_db,
            contract_number="HT-SHARED-001",
            project_id="project-2",
        )
        assert mock_create.await_args.kwargs["data"]["project_id"] == "project-2"

    async def test_add_contract_should_not_write_payment_cycle_into_main_table(
        self, mock_db: MagicMock
    ) -> None:
        """C17: payment_cycle 属于 LeaseContractDetail；写入 Contract 主表会让真实 ORM 构造崩溃。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-2"
        mock_group.operator_party_id = "party-operator"
        mock_group.owner_party_id = "party-owner"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-003"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
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
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(
                    contract_number="HT-PCYCLE-001", payment_cycle="季付"
                ),
            )

        assert result is created_contract
        data = mock_create.await_args.kwargs["data"]
        assert "payment_cycle" not in data
        lease_detail_data = mock_create.await_args.kwargs["lease_detail_data"]
        assert lease_detail_data["payment_cycle"] == "季付"

    async def test_add_contract_should_reject_assets_outside_group_scope(
        self, mock_db: MagicMock
    ) -> None:
        """C6: 单合同覆盖资产不得超出所属合同关系覆盖资产。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_asset_ids_for_group",
                new_callable=AsyncMock,
                return_value=["asset-1"],
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="asset-2"):
                await service.add_contract_to_group(
                    mock_db,
                    obj_in=_valid_contract_create(asset_ids=["asset-2"]),
                )

    async def test_add_contract_should_allow_empty_asset_ids_as_whole_group_rent(
        self, mock_db: MagicMock
    ) -> None:
        """C6: asset_ids 留空表示覆盖合同关系全部资产，跳过子集校验。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-001"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_asset_ids_for_group",
                new_callable=AsyncMock,
                return_value=["asset-1"],
            ) as mock_list_assets,
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
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(asset_ids=[]),
            )

        assert result.contract_id == "contract-001"
        mock_list_assets.assert_not_awaited()
        assert mock_create.await_args.kwargs["asset_ids"] is None

    async def test_add_contract_passes_contract_number_to_crud(
        self, mock_db: MagicMock
    ):
        """创建合同时必须把 contract_number 写入新 contracts 基表。"""
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-001"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
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
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(contract_number="HT-2026-0099"),
            )

        assert result.contract_id == "contract-001"
        assert (
            mock_create.await_args.kwargs["data"]["contract_number"] == "HT-2026-0099"
        )

    async def test_add_contract_persists_initial_terms_before_generating_ledger(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        mock_group.operator_party_id = "party-operator"
        mock_group.owner_party_id = "party-owner"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-001"
        events: list[str] = []

        async def create_term(*args, **kwargs):  # noqa: ANN002, ANN003
            events.append("rent_term")
            return MagicMock()

        async def generate_ledger(*args, **kwargs):  # noqa: ANN002, ANN003
            events.append("ledger")
            return []

        rent_term = ContractRentTermCreate(
            sort_order=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            monthly_rent=Decimal("10000"),
            management_fee=Decimal("500"),
        )
        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
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
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_rent_term",
                new=AsyncMock(side_effect=create_term),
            ) as mock_create_term,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(side_effect=generate_ledger),
            ),
        ):
            await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(rent_terms=[rent_term]),
            )

        assert events == ["rent_term", "ledger"]
        term_data = mock_create_term.await_args.kwargs["data"]
        assert term_data["contract_id"] == "contract-001"
        assert term_data["total_monthly_amount"] == Decimal("10500")


class TestAddContractRequiresApprovedParties:
    async def test_add_contract_should_block_when_related_party_not_approved(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        mock_group.operator_party_id = "party-operator"
        mock_group.owner_party_id = "party-owner"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                side_effect=OperationNotAllowedError("存在未审核主体"),
            ) as mock_assert,
            patch(
                "src.services.contract.contract_group_service.contract_crud.create",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            with pytest.raises(OperationNotAllowedError, match="未审核主体"):
                await service.add_contract_to_group(
                    mock_db,
                    obj_in=_valid_contract_create(),
                )

        mock_assert.assert_awaited_once_with(
            mock_db,
            party_ids=[
                "party_lessor",
                "party_lessee",
                "party-operator",
                "party-owner",
            ],
            operation="合同补录",
        )
        mock_create.assert_not_awaited()

    async def test_add_contract_should_create_active_contract_and_generate_ledger(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        mock_group = MagicMock(spec=ContractGroup)
        mock_group.revenue_mode = RevenueMode.LEASE
        mock_group.project_id = "project-1"
        mock_group.operator_party_id = "party-operator"
        mock_group.owner_party_id = "party-owner"
        created_contract = MagicMock(spec=Contract)
        created_contract.contract_id = "contract-001"

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new_callable=AsyncMock,
                return_value=mock_group,
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_assert,
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=_party_name_lookup(),
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
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_generate_ledger,
        ):
            result = await service.add_contract_to_group(
                mock_db,
                obj_in=_valid_contract_create(),
            )

        assert result is created_contract
        assert mock_create.await_args.kwargs["data"]["status"] == "ACTIVE"
        assert mock_create.await_args.kwargs["data"]["project_id"] == "project-1"
        assert (
            mock_create.await_args.kwargs["data"]["lessor_name_snapshot"]
            == "出租方签署名"
        )
        assert (
            mock_create.await_args.kwargs["data"]["lessee_name_snapshot"]
            == "承租方签署名"
        )
        assert (
            mock_create.await_args.kwargs["lease_detail_data"]["tenant_name"]
            == "承租方签署名"
        )
        assert "review_status" not in mock_create.await_args.kwargs["data"]
        mock_assert.assert_awaited_once()
        mock_generate_ledger.assert_awaited_once_with(
            mock_db,
            contract_id="contract-001",
        )
        mock_db.commit.assert_awaited_once()


class TestContractScanDocuments:
    @staticmethod
    def _scan_contract(
        *,
        contract_id: str,
        contract_number: str = "HT-SHARED-001",
        group_relation_type: GroupRelationType = GroupRelationType.ENTRUSTED,
        revenue_mode: RevenueMode = RevenueMode.AGENCY,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            contract_id=contract_id,
            contract_number=contract_number,
            lessor_party_id="party-owner",
            lessee_party_id="party-operator",
            group_relation_type=group_relation_type,
            contract_group=SimpleNamespace(revenue_mode=revenue_mode),
        )

    async def test_replace_scan_documents_updates_same_number_sibling_contracts(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        source_contract = self._scan_contract(contract_id="contract-a")
        sibling_contract = self._scan_contract(contract_id="contract-b")
        created_document = SimpleNamespace(
            document_id="doc-1",
            storage_key="scans/HT-SHARED-001.pdf",
            original_filename="HT-SHARED-001.pdf",
            content_type="application/pdf",
            file_size=128,
            checksum_sha256="a" * 64,
            data_status="正常",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        payload = ContractScanDocumentReplaceRequest(
            documents=[
                ContractScanDocumentCreate(
                    storage_key="scans/HT-SHARED-001.pdf",
                    original_filename="HT-SHARED-001.pdf",
                    content_type="application/pdf",
                    file_size=128,
                    checksum_sha256="a" * 64,
                )
            ]
        )

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new_callable=AsyncMock,
                return_value=source_contract,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_scan_document_by_storage_key",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.create_scan_document",
                new_callable=AsyncMock,
                return_value=created_document,
            ) as mock_create_doc,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_contract_number",
                new_callable=AsyncMock,
                return_value=[source_contract, sibling_contract],
            ) as mock_list_by_number,
            patch(
                "src.services.contract.contract_group_service.contract_crud.replace_scan_document_links_for_contracts",
                new_callable=AsyncMock,
            ) as mock_replace_links,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_scan_documents_by_contract",
                new_callable=AsyncMock,
                return_value=[created_document],
            ),
        ):
            result = await service.replace_contract_scan_documents(
                mock_db,
                contract_id="contract-a",
                obj_in=payload,
                current_user="user-1",
            )

        assert [item.document_id for item in result] == ["doc-1"]
        mock_create_doc.assert_awaited_once()
        assert mock_create_doc.await_args.kwargs["data"]["data_status"] == "正常"
        mock_list_by_number.assert_awaited_once_with(
            mock_db,
            contract_number="HT-SHARED-001",
            lessor_party_id="party-owner",
            lessee_party_id="party-operator",
            shared_scan_scope_only=True,
        )
        mock_replace_links.assert_awaited_once_with(
            mock_db,
            contract_ids=["contract-a", "contract-b"],
            document_ids=["doc-1"],
        )
        mock_db.commit.assert_awaited_once()

    async def test_non_agency_or_non_entrusted_same_number_contract_updates_only_self(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        source_contract = self._scan_contract(
            contract_id="contract-a",
            group_relation_type=GroupRelationType.UPSTREAM,
            revenue_mode=RevenueMode.LEASE,
        )
        existing_document = SimpleNamespace(
            document_id="doc-1",
            storage_key="scans/HT-SHARED-001.pdf",
            original_filename="HT-SHARED-001.pdf",
            content_type="application/pdf",
            file_size=128,
            checksum_sha256="a" * 64,
            data_status="正常",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        payload = ContractScanDocumentReplaceRequest(
            documents=[
                ContractScanDocumentCreate(
                    storage_key="scans/HT-SHARED-001.pdf",
                    original_filename="HT-SHARED-001.pdf",
                    content_type="application/pdf",
                    file_size=128,
                    checksum_sha256="a" * 64,
                )
            ]
        )

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new_callable=AsyncMock,
                return_value=source_contract,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_scan_document_by_storage_key",
                new_callable=AsyncMock,
                return_value=existing_document,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_contract_ids_linked_to_scan_document",
                new_callable=AsyncMock,
                return_value=["contract-a"],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update_scan_document",
                new_callable=AsyncMock,
                return_value=existing_document,
            ) as mock_update_doc,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_contract_number",
                new_callable=AsyncMock,
            ) as mock_list_by_number,
            patch(
                "src.services.contract.contract_group_service.contract_crud.replace_scan_document_links_for_contracts",
                new_callable=AsyncMock,
            ) as mock_replace_links,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_scan_documents_by_contract",
                new_callable=AsyncMock,
                return_value=[existing_document],
            ),
        ):
            await service.replace_contract_scan_documents(
                mock_db,
                contract_id="contract-a",
                obj_in=payload,
                current_user="user-1",
            )

        mock_update_doc.assert_awaited_once()
        mock_list_by_number.assert_not_awaited()
        mock_replace_links.assert_awaited_once_with(
            mock_db,
            contract_ids=["contract-a"],
            document_ids=["doc-1"],
        )

    async def test_reusing_scan_document_linked_outside_scope_fails_before_mutation(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        source_contract = self._scan_contract(contract_id="contract-a")
        sibling_contract = self._scan_contract(contract_id="contract-b")
        existing_document = SimpleNamespace(
            document_id="doc-1",
            storage_key="scans/HT-SHARED-001.pdf",
            original_filename="old.pdf",
            content_type="application/pdf",
            file_size=64,
            checksum_sha256="b" * 64,
            data_status="正常",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        payload = ContractScanDocumentReplaceRequest(
            documents=[
                ContractScanDocumentCreate(
                    storage_key="scans/HT-SHARED-001.pdf",
                    original_filename="HT-SHARED-001.pdf",
                    content_type="application/pdf",
                    file_size=128,
                    checksum_sha256="a" * 64,
                )
            ]
        )

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new_callable=AsyncMock,
                return_value=source_contract,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_contract_number",
                new_callable=AsyncMock,
                return_value=[source_contract, sibling_contract],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get_scan_document_by_storage_key",
                new_callable=AsyncMock,
                return_value=existing_document,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_contract_ids_linked_to_scan_document",
                new_callable=AsyncMock,
                return_value=["contract-a", "contract-b", "contract-outside"],
            ) as mock_list_linked,
            patch(
                "src.services.contract.contract_group_service.contract_crud.update_scan_document",
                new_callable=AsyncMock,
            ) as mock_update_doc,
            patch(
                "src.services.contract.contract_group_service.contract_crud.replace_scan_document_links_for_contracts",
                new_callable=AsyncMock,
            ) as mock_replace_links,
        ):
            with pytest.raises(
                OperationNotAllowedError,
                match="outside affected contracts",
            ) as exc_info:
                await service.replace_contract_scan_documents(
                    mock_db,
                    contract_id="contract-a",
                    obj_in=payload,
                    current_user="user-1",
                )

        assert (
            exc_info.value.details["reason"] == "contract_scan_document_scope_conflict"
        )
        assert exc_info.value.details["outside_contract_ids"] == ["contract-outside"]
        mock_list_linked.assert_awaited_once_with(
            mock_db,
            document_id="doc-1",
        )
        mock_update_doc.assert_not_awaited()
        mock_replace_links.assert_not_awaited()
        mock_db.commit.assert_not_awaited()

    async def test_delete_scan_document_rejects_leaving_any_contract_empty(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        source_contract = self._scan_contract(contract_id="contract-a")
        sibling_contract = self._scan_contract(contract_id="contract-b")

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new_callable=AsyncMock,
                return_value=source_contract,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_contract_number",
                new_callable=AsyncMock,
                return_value=[source_contract, sibling_contract],
            ) as mock_list_by_number,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_contract_ids_linked_to_scan_document",
                new_callable=AsyncMock,
                return_value=["contract-a", "contract-b"],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.count_scan_documents_by_contracts",
                new_callable=AsyncMock,
                return_value={"contract-a": 1, "contract-b": 2},
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.unlink_scan_document_from_contracts",
                new_callable=AsyncMock,
            ) as mock_unlink,
        ):
            with pytest.raises(
                OperationNotAllowedError,
                match="delete would leave contracts without scan documents",
            ) as exc_info:
                await service.delete_contract_scan_document(
                    mock_db,
                    contract_id="contract-a",
                    document_id="doc-1",
                )

        assert exc_info.value.details["reason"] == "contract_scan_document_required"
        mock_unlink.assert_not_awaited()
        mock_list_by_number.assert_awaited_once_with(
            mock_db,
            contract_number="HT-SHARED-001",
            lessor_party_id="party-owner",
            lessee_party_id="party-operator",
            shared_scan_scope_only=True,
        )
        mock_db.commit.assert_not_awaited()

    async def test_delete_scan_document_unlinks_when_all_contracts_keep_documents(
        self, mock_db: MagicMock
    ) -> None:
        service = ContractGroupService()
        source_contract = self._scan_contract(contract_id="contract-a")
        sibling_contract = self._scan_contract(contract_id="contract-b")

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new_callable=AsyncMock,
                return_value=source_contract,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_contract_number",
                new_callable=AsyncMock,
                return_value=[source_contract, sibling_contract],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_contract_ids_linked_to_scan_document",
                new_callable=AsyncMock,
                return_value=["contract-a", "contract-b"],
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.count_scan_documents_by_contracts",
                new_callable=AsyncMock,
                return_value={"contract-a": 2, "contract-b": 2},
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.unlink_scan_document_from_contracts",
                new_callable=AsyncMock,
            ) as mock_unlink,
        ):
            await service.delete_contract_scan_document(
                mock_db,
                contract_id="contract-a",
                document_id="doc-1",
            )

        mock_unlink.assert_awaited_once_with(
            mock_db,
            contract_ids=["contract-a", "contract-b"],
            document_id="doc-1",
        )
        mock_db.commit.assert_awaited_once()


class TestContractDetailEnumCoercion:
    """同 session ORM 对象携带枚举 name 字符串时，详情/摘要序列化必须归一化为中文值。

    验收 5.1：add_contract_to_group 用 .name 构造 ORM 对象后，同一 session 的
    get_contract_detail 从 identity map 命中字符串属性，ContractDetail 枚举校验
    失败导致端点 500（数据已提交）。本测试锁定响应层归一化行为。
    """

    def _orm_like_contract(self) -> SimpleNamespace:
        return SimpleNamespace(
            contract_id="contract-1",
            contract_group_id="group-1",
            project_id="project-1",
            contract_number="CT-1",
            contract_direction="LESSEE",
            group_relation_type="UPSTREAM",
            lessor_party_id="lessor-1",
            lessee_party_id="lessee-1",
            lessor_name_snapshot=None,
            lessee_name_snapshot=None,
            sign_date=date(2026, 8, 1),
            effective_from=date(2026, 8, 1),
            effective_to=date(2027, 7, 31),
            currency_code="CNY",
            tax_rate=None,
            is_tax_included=True,
            status="ACTIVE",
            contract_notes=None,
            data_status="正常",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
            lease_detail=None,
            agency_detail=None,
        )

    def test_contract_detail_coerces_enum_names(self) -> None:
        detail = ContractDetail.model_validate(self._orm_like_contract())

        assert detail.contract_direction == "承租"
        assert detail.group_relation_type == "上游"
        assert detail.status == "生效"

    def test_contract_summary_coerces_enum_names(self) -> None:
        summary = ContractSummary.model_validate(self._orm_like_contract())

        assert summary.contract_direction == "承租"
        assert summary.group_relation_type == "上游"
