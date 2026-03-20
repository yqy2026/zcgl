"""
Analytics API 集成测试
测试 analytics.py 的真实认证与真实数据链路
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.asset import Asset
from src.models.contract_group import (
    AgencyAgreementDetail,
    Contract,
    ContractDirection,
    ContractGroup,
    ContractLifecycleStatus,
    ContractReviewStatus,
    GroupRelationType,
    LeaseContractDetail,
    RevenueMode,
)
from src.models.party import Party, PartyReviewStatus, PartyType

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """使用真实登录流程为客户端注入认证 cookie。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    """返回 cookie-only 认证下写操作所需 CSRF 头。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


def _seed_assets_for_analytics(
    db_session,
    *,
    organization_id: str,
    suffix: str,
) -> tuple[str, str]:
    """写入可预测资产数据用于分析断言。"""
    unique_nature_normal = f"分析性质-正常-{suffix}"
    unique_nature_deleted = f"分析性质-删除-{suffix}"

    db_session.add_all(
        [
            Asset(
                asset_name=f"分析资产-正常-{suffix}",
                address=f"分析地址-正常-{suffix}",
                ownership_status="已确权",
                property_nature=unique_nature_normal,
                usage_status="出租",
                business_category=f"分析业态-正常-{suffix}",
                organization_id=organization_id,
                rentable_area=1000,
                rented_area=800,
                data_status="正常",
            ),
            Asset(
                asset_name=f"分析资产-删除-{suffix}",
                address=f"分析地址-删除-{suffix}",
                ownership_status="待确权",
                property_nature=unique_nature_deleted,
                usage_status="空置",
                business_category=f"分析业态-删除-{suffix}",
                organization_id=organization_id,
                rentable_area=500,
                rented_area=0,
                data_status="已删除",
            ),
        ]
    )
    db_session.commit()
    return unique_nature_normal, unique_nature_deleted


def _seed_operational_contracts_for_analytics(
    db_session,
    *,
    suffix: str,
    same_customer_for_direct: bool = False,
    direct_customer_review_status: str = PartyReviewStatus.APPROVED.value,
    entrusted_party_review_status: str | None = None,
    direct_rent_amount: Decimal = Decimal("2000.00"),
    extra_direct_rent_amounts: tuple[Decimal, ...] = (),
    include_agency_detail: bool = True,
) -> dict[str, float | int | str]:
    """写入 ANA-001 最小口径样本。"""
    operator_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析运营方-{suffix}",
        code=f"ANA-OP-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    owner_party = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"分析产权方-{suffix}",
        code=f"ANA-OWNER-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    customer_one = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析客户一-{suffix}",
        code=f"ANA-C1-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    customer_two = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析客户二-{suffix}",
        code=f"ANA-C2-{suffix}",
        status="active",
        review_status=direct_customer_review_status,
    )
    db_session.add_all([operator_party, owner_party, customer_one, customer_two])
    db_session.flush()

    entrusted_party = operator_party
    if entrusted_party_review_status is not None:
        entrusted_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name=f"分析委托受托方-{suffix}",
            code=f"ANA-ENTRUSTED-{suffix}",
            status="active",
            review_status=entrusted_party_review_status,
        )
        db_session.add(entrusted_party)
        db_session.flush()

    settlement_rule = {
        "version": "v1",
        "cycle": "月付",
        "settlement_mode": "manual",
        "amount_rule": {"basis": "fixed"},
        "payment_rule": {"due_day": 1},
    }
    lease_group = ContractGroup(
        group_code=f"ANA-LEASE-{suffix}",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=operator_party.id,
        owner_party_id=owner_party.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        settlement_rule=settlement_rule,
        data_status="正常",
    )
    agency_group = ContractGroup(
        group_code=f"ANA-AGENCY-{suffix}",
        revenue_mode=RevenueMode.AGENCY,
        operator_party_id=operator_party.id,
        owner_party_id=owner_party.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        settlement_rule=settlement_rule,
        data_status="正常",
    )
    db_session.add_all([lease_group, agency_group])
    db_session.flush()

    lease_contract = Contract(
        contract_group_id=lease_group.contract_group_id,
        contract_number=f"ANA-LEASE-CONTRACT-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.DOWNSTREAM,
        lessor_party_id=owner_party.id,
        lessee_party_id=customer_one.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
    )
    lease_contract.lease_detail = LeaseContractDetail(
        rent_amount=Decimal("1000.00"),
        total_deposit=Decimal("0.00"),
        payment_cycle="月付",
    )

    entrusted_contract = Contract(
        contract_group_id=agency_group.contract_group_id,
        contract_number=f"ANA-ENTRUSTED-CONTRACT-{suffix}",
        contract_direction=ContractDirection.LESSEE,
        group_relation_type=GroupRelationType.ENTRUSTED,
        lessor_party_id=owner_party.id,
        lessee_party_id=entrusted_party.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
    )
    if include_agency_detail:
        entrusted_contract.agency_detail = AgencyAgreementDetail(
            service_fee_ratio=Decimal("0.1000"),
            fee_calculation_base="actual_received",
        )

    direct_customer = customer_one if same_customer_for_direct else customer_two

    direct_contracts: list[Contract] = []
    direct_rent_amounts = (direct_rent_amount, *extra_direct_rent_amounts)
    for index, rent_amount in enumerate(direct_rent_amounts, start=1):
        direct_contract = Contract(
            contract_group_id=agency_group.contract_group_id,
            contract_number=f"ANA-DIRECT-CONTRACT-{suffix}-{index}",
            contract_direction=ContractDirection.LESSOR,
            group_relation_type=GroupRelationType.DIRECT_LEASE,
            lessor_party_id=owner_party.id,
            lessee_party_id=direct_customer.id,
            sign_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
            data_status="正常",
        )
        direct_contract.lease_detail = LeaseContractDetail(
            rent_amount=rent_amount,
            total_deposit=Decimal("0.00"),
            payment_cycle="月付",
        )
        direct_contracts.append(direct_contract)

    db_session.add_all([lease_contract, entrusted_contract, *direct_contracts])
    db_session.commit()

    direct_contract_is_eligible = (
        direct_customer_review_status == PartyReviewStatus.APPROVED.value
    )
    entrusted_ratio_is_eligible = (
        entrusted_party_review_status is None
        or entrusted_party_review_status == PartyReviewStatus.APPROVED.value
    )
    agency_service_income = (
        float(
            (
                sum(direct_rent_amounts, start=Decimal("0.00")) * Decimal("0.1000")
            ).quantize(Decimal("0.01"))
        )
        if direct_contract_is_eligible
        and entrusted_ratio_is_eligible
        and include_agency_detail
        else 0.0
    )

    return {
        "total_income": 1000.0 + agency_service_income,
        "self_operated_rent_income": 1000.0,
        "agency_service_income": agency_service_income,
        "customer_entity_count": (
            1
            if same_customer_for_direct
            else (
                2
                if direct_contract_is_eligible
                else 1
            )
        ),
        "customer_contract_count": (
            1 + len(direct_rent_amounts)
            if direct_contract_is_eligible
            else 1
        ),
        "metrics_version": "req-ana-001-v1",
    }


def _seed_self_operated_group_party_unapproved_for_analytics(
    db_session,
    *,
    suffix: str,
    lease_group_operator_review_status: str = PartyReviewStatus.DRAFT.value,
) -> dict[str, float | int | str]:
    """写入自营组内主体未审核、代理链路仍合规的 ANA-001 样本。"""
    lease_operator_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析自营运营方-{suffix}",
        code=f"ANA-LEASE-OP-{suffix}",
        status="active",
        review_status=lease_group_operator_review_status,
    )
    lease_owner_party = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"分析自营产权方-{suffix}",
        code=f"ANA-LEASE-OWNER-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    agency_operator_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析代理运营方-{suffix}",
        code=f"ANA-AGENCY-OP-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    agency_owner_party = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"分析代理产权方-{suffix}",
        code=f"ANA-AGENCY-OWNER-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    lease_customer = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析自营客户-{suffix}",
        code=f"ANA-LEASE-CUSTOMER-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    agency_customer = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"分析代理客户-{suffix}",
        code=f"ANA-AGENCY-CUSTOMER-{suffix}",
        status="active",
        review_status=PartyReviewStatus.APPROVED.value,
    )
    db_session.add_all(
        [
            lease_operator_party,
            lease_owner_party,
            agency_operator_party,
            agency_owner_party,
            lease_customer,
            agency_customer,
        ]
    )
    db_session.flush()

    settlement_rule = {
        "version": "v1",
        "cycle": "月付",
        "settlement_mode": "manual",
        "amount_rule": {"basis": "fixed"},
        "payment_rule": {"due_day": 1},
    }
    lease_group = ContractGroup(
        group_code=f"ANA-LEASE-GROUP-{suffix}",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=lease_operator_party.id,
        owner_party_id=lease_owner_party.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        settlement_rule=settlement_rule,
        data_status="正常",
    )
    agency_group = ContractGroup(
        group_code=f"ANA-AGENCY-GROUP-{suffix}",
        revenue_mode=RevenueMode.AGENCY,
        operator_party_id=agency_operator_party.id,
        owner_party_id=agency_owner_party.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        settlement_rule=settlement_rule,
        data_status="正常",
    )
    db_session.add_all([lease_group, agency_group])
    db_session.flush()

    lease_contract = Contract(
        contract_group_id=lease_group.contract_group_id,
        contract_number=f"ANA-LEASE-GROUP-CONTRACT-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.DOWNSTREAM,
        lessor_party_id=lease_owner_party.id,
        lessee_party_id=lease_customer.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
    )
    lease_contract.lease_detail = LeaseContractDetail(
        rent_amount=Decimal("1000.00"),
        total_deposit=Decimal("0.00"),
        payment_cycle="月付",
    )

    entrusted_contract = Contract(
        contract_group_id=agency_group.contract_group_id,
        contract_number=f"ANA-AGENCY-ENTRUSTED-{suffix}",
        contract_direction=ContractDirection.LESSEE,
        group_relation_type=GroupRelationType.ENTRUSTED,
        lessor_party_id=agency_owner_party.id,
        lessee_party_id=agency_operator_party.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
    )
    entrusted_contract.agency_detail = AgencyAgreementDetail(
        service_fee_ratio=Decimal("0.1000"),
        fee_calculation_base="actual_received",
    )

    direct_contract = Contract(
        contract_group_id=agency_group.contract_group_id,
        contract_number=f"ANA-AGENCY-DIRECT-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.DIRECT_LEASE,
        lessor_party_id=agency_owner_party.id,
        lessee_party_id=agency_customer.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
    )
    direct_contract.lease_detail = LeaseContractDetail(
        rent_amount=Decimal("2000.00"),
        total_deposit=Decimal("0.00"),
        payment_cycle="月付",
    )

    db_session.add_all([lease_contract, entrusted_contract, direct_contract])
    db_session.commit()

    return {
        "total_income": 200.0,
        "self_operated_rent_income": 0.0,
        "agency_service_income": 200.0,
        "customer_entity_count": 1,
        "customer_contract_count": 1,
        "metrics_version": "req-ana-001-v1",
    }


class TestAnalyticsAPIContracts:
    """Analytics API 真实契约测试。"""

    def test_analytics_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/v1/analytics/comprehensive")
        assert response.status_code == 401
        payload = response.json()
        assert payload.get("success") is False

    def test_analytics_comprehensive_endpoint_exists(self, authenticated_client):
        """综合分析端点返回统一结构。"""
        response = authenticated_client.get("/api/v1/analytics/comprehensive")

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert isinstance(data.get("total_assets"), int)
        assert isinstance(data.get("timestamp"), str)
        assert isinstance(data.get("area_summary"), dict)
        assert isinstance(data.get("occupancy_rate"), dict)

    def test_analytics_comprehensive_with_params(self, authenticated_client):
        """综合分析端点参数化请求。"""
        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_include_deleted=false&should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

    def test_comprehensive_includes_req_ana_001_operational_metrics(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """ANA-001 口径字段应走真实数据库链路返回正确值。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == expected["total_income"]
        assert (
            data["self_operated_rent_income"]
            == expected["self_operated_rent_income"]
        )
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == expected["customer_contract_count"]
        assert data["metrics_version"] == expected["metrics_version"]

    def test_comprehensive_include_deleted_expands_scope(
        self,
        authenticated_client: TestClient,
        db_session,
        test_data,
    ) -> None:
        """include_deleted=true 应至少包含多出的已删除资产。"""
        suffix = uuid4().hex[:8]
        _seed_assets_for_analytics(
            db_session,
            organization_id=test_data["organization"].id,
            suffix=suffix,
        )

        without_deleted = authenticated_client.get(
            "/api/v1/analytics/comprehensive"
            "?should_include_deleted=false&should_use_cache=false"
        )
        with_deleted = authenticated_client.get(
            "/api/v1/analytics/comprehensive"
            "?should_include_deleted=true&should_use_cache=false"
        )

        assert without_deleted.status_code == 200
        assert with_deleted.status_code == 200

        without_total = without_deleted.json()["data"]["total_assets"]
        with_total = with_deleted.json()["data"]["total_assets"]
        assert isinstance(without_total, int)
        assert isinstance(with_total, int)
        assert with_total >= without_total + 1

    def test_comprehensive_deduplicates_customer_entities_for_req_ana_001(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """同一客户主体多份合同时应只计 1 个客户主体。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            same_customer_for_direct=True,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == expected["total_income"]
        assert data["customer_entity_count"] == 1
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 2
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_excludes_unapproved_party_from_req_ana_001(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """未审核通过的相关 Party 不得进入 ANA-001 统计。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            direct_customer_review_status=PartyReviewStatus.DRAFT.value,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 1000.0
        assert data["total_income"] == expected["total_income"]
        assert data["agency_service_income"] == 0.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 1
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 1
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_returns_zero_agency_income_when_direct_rent_is_zero(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """代理直租金额为 0 时不应产生代理服务费收入。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            direct_rent_amount=Decimal("0.00"),
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 1000.0
        assert data["total_income"] == expected["total_income"]
        assert data["agency_service_income"] == 0.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 2
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 2
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_does_not_use_ratio_from_unapproved_entrusted_party(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """未审核委托协议不得为代理收入提供费率口径。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            entrusted_party_review_status=PartyReviewStatus.DRAFT.value,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 1000.0
        assert data["total_income"] == expected["total_income"]
        assert data["agency_service_income"] == 0.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 2
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 2
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_returns_zero_agency_income_without_agency_detail(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """委托协议缺失费率明细时代理收入应为 0。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            include_agency_detail=False,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 1000.0
        assert data["total_income"] == expected["total_income"]
        assert data["agency_service_income"] == 0.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 2
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 2
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_counts_multiple_direct_leases_for_same_customer(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """同一代理客户多份直租合同时主体数去重、合同数累计。"""
        suffix = uuid4().hex[:8]
        expected = _seed_operational_contracts_for_analytics(
            db_session,
            suffix=suffix,
            extra_direct_rent_amounts=(Decimal("1500.00"),),
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 1350.0
        assert data["total_income"] == expected["total_income"]
        assert data["agency_service_income"] == 350.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 2
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 3
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_comprehensive_excludes_self_operated_income_when_group_party_unapproved(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        """自营组内主体未审核时，自营收入应被排除但代理链路仍可统计。"""
        suffix = uuid4().hex[:8]
        expected = _seed_self_operated_group_party_unapproved_for_analytics(
            db_session,
            suffix=suffix,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

        data = payload["data"]
        assert data["total_income"] == 200.0
        assert data["total_income"] == expected["total_income"]
        assert data["self_operated_rent_income"] == 0.0
        assert (
            data["self_operated_rent_income"]
            == expected["self_operated_rent_income"]
        )
        assert data["agency_service_income"] == 200.0
        assert data["agency_service_income"] == expected["agency_service_income"]
        assert data["customer_entity_count"] == 1
        assert data["customer_entity_count"] == expected["customer_entity_count"]
        assert data["customer_contract_count"] == 1
        assert data["customer_contract_count"] == expected["customer_contract_count"]

    def test_analytics_cache_stats_endpoint_exists(self, authenticated_client):
        """缓存统计端点返回统一结构。"""
        response = authenticated_client.get("/api/v1/analytics/cache/stats")

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert isinstance(data.get("cache_type"), str)
        assert isinstance(data.get("stats"), dict)
        assert isinstance(data.get("timestamp"), str)

    def test_analytics_cache_clear_endpoint_exists(
        self, authenticated_client, csrf_headers
    ):
        """清除缓存端点返回稳定数据。"""
        response = authenticated_client.post(
            "/api/v1/analytics/cache/clear", headers=csrf_headers
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("status") in {"success", "failed"}
        assert isinstance(data.get("cleared_keys"), int)
        assert isinstance(data.get("timestamp"), str)

    def test_analytics_trend_endpoint_exists(self, authenticated_client):
        """趋势端点返回统一结构。"""
        response = authenticated_client.get(
            "/api/v1/analytics/trend?trend_type=occupancy&time_dimension=monthly"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("trend_type") == "occupancy"
        assert data.get("time_dimension") == "monthly"
        assert isinstance(data.get("data"), list)

    def test_analytics_distribution_endpoint_contains_seeded_data(
        self, authenticated_client, db_session, test_data
    ):
        """分布端点应包含测试写入的唯一分类值。"""
        suffix = uuid4().hex[:8]
        unique_nature_normal, _ = _seed_assets_for_analytics(
            db_session,
            organization_id=test_data["organization"].id,
            suffix=suffix,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/distribution?distribution_type=property_nature"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("distribution_type") == "property_nature"
        distribution = data.get("data")
        assert isinstance(distribution, dict)
        assert unique_nature_normal in distribution
        seeded_entry = distribution[unique_nature_normal]
        assert isinstance(seeded_entry, dict)
        assert int(seeded_entry.get("count", 0)) >= 1

    def test_analytics_distribution_invalid_type(self, authenticated_client):
        """非法分布类型应返回 400 业务错误。"""
        response = authenticated_client.get(
            "/api/v1/analytics/distribution?distribution_type=invalid_type"
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error")
        assert isinstance(error, dict)
        assert error.get("code") == "INVALID_REQUEST"

    def test_analytics_debug_cache_endpoint_exists(self, authenticated_client):
        """调试缓存端点在测试环境保持不可见（404）。"""
        with TestClient(
            authenticated_client.app,
            raise_server_exceptions=False,
        ) as debug_client:
            debug_client.cookies.update(authenticated_client.cookies)
            response = debug_client.get("/api/v1/analytics/debug/cache")

            # debug-only + localhost 限制：测试环境应返回 404（不暴露端点）
            assert response.status_code == 404
            payload = response.json()
            assert payload.get("success") is False

    def test_router_registration_via_openapi(self, authenticated_client):
        """路由应在 OpenAPI 中可见（真实注册验证）。"""
        response = authenticated_client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        assert "/api/v1/analytics/comprehensive" in paths
        assert "/api/v1/analytics/cache/stats" in paths
        assert "/api/v1/analytics/cache/clear" in paths
        assert "/api/v1/analytics/trend" in paths
        assert "/api/v1/analytics/distribution" in paths
        assert "/api/v1/analytics/debug/cache" in paths
