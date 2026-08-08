"""Party API behavior tests."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi import status


def test_party_hierarchy_routes_are_removed() -> None:
    from src.api.v1 import party as party_module

    assert all("/hierarchy" not in route.path for route in party_module.router.routes)


def _create_user(
    db_session,
    *,
    user_id: str,
    organization_id: str | None = None,
) -> None:
    from src.models.auth import User

    # Derive a stable unique phone from user_id to avoid UniqueViolation when
    # multiple users are created within the same test.
    phone_suffix = f"{abs(hash(user_id)) % 99999999:08d}"
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id}",
            email=f"{user_id}@example.com",
            phone=f"1{phone_suffix[:10]}",
            full_name=f"用户{user_id}",
            password_hash="hashed-password",
            is_active=organization_id is not None,
            is_locked=False,
            organization_id=organization_id,
        )
    )
    db_session.flush()


def test_list_parties_should_filter_by_search_query(client, db_session) -> None:
    """`/parties` 应根据 search 过滤名称/编码匹配结果。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")

    matching_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Acme Holdings",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    other_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Beta Group",
        code="LE-000002",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=matching_party.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties?search=acme")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Acme Holdings"
    assert payload[0]["code"] == "LE-000001"


def test_list_parties_should_filter_by_search_code(client, db_session) -> None:
    """`/parties` 应支持按编码模糊搜索。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")

    matching_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Code Match Party",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    other_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Other Party",
        code="LE-000002",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=matching_party.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties?search=LE-000001")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Code Match Party"
    assert payload[0]["code"] == "LE-000001"


def test_list_parties_should_return_stable_403_when_user_has_no_bindings(
    client, db_session
) -> None:
    """无绑定时列表接口应 fail-closed 返回空列表。"""
    from src.models.party import Party, PartyType

    db_session.add(
        Party(
            party_type=PartyType.LEGAL_ENTITY,
            name="Acme Holdings",
            code="LE-000001",
            status="active",
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "PARTY_SCOPE_MISSING"


def test_list_parties_should_derive_current_business_roles_within_party_scope(
    client, db_session
) -> None:
    """Role slices use only current relations and respect Party scope."""
    from src.models.asset import Asset
    from src.models.contract_group import (
        Contract,
        ContractDirection,
        ContractGroup,
        ContractLifecycleStatus,
        GroupRelationType,
        RevenueMode,
    )
    from src.models.party import Party, PartyType
    from src.models.project import Project
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")
    current_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Current Multi-role Party",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    direct_lease_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Direct Lease Tenant Party",
        code="LE-000002",
        status="active",
        review_status="approved",
    )
    expired_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Expired Tenant Party",
        code="LE-000003",
        status="active",
        review_status="approved",
    )
    out_of_scope_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Out Of Scope Tenant Party",
        code="LE-000004",
        status="active",
    )
    db_session.add_all(
        [current_party, direct_lease_party, expired_party, out_of_scope_party]
    )
    db_session.flush()
    db_session.add_all(
        [
            UserPartyBinding(
                user_id="test_user_001",
                party_id=current_party.id,
                relation_type=RelationType.OWNER,
            ),
            UserPartyBinding(
                user_id="test_user_001",
                party_id=direct_lease_party.id,
                relation_type=RelationType.OWNER,
            ),
            UserPartyBinding(
                user_id="test_user_001",
                party_id=expired_party.id,
                relation_type=RelationType.OWNER,
            ),
        ]
    )

    today = date.today()
    project = Project(
        project_name="Current Operator Project",
        project_code="PRJ-PTY-ROLE-0001",
        status="active",
        manager_party_id=current_party.id,
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Asset(
            asset_name="Current Owner Asset",
            asset_code="AST-PTY-ROLE-0001",
            address="Current Owner Asset Address",
            ownership_status="confirmed",
            property_nature="commercial",
            usage_status="in_use",
            owner_party_id=current_party.id,
        )
    )

    active_group = ContractGroup(
        contract_group_id="group-party-role-active",
        project_id=project.id,
        group_code="GRP-PTY-ROLE-ACTIVE",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=current_party.id,
        owner_party_id=current_party.id,
        effective_from=today - timedelta(days=1),
    )
    direct_lease_group = ContractGroup(
        contract_group_id="group-party-role-direct",
        project_id=project.id,
        group_code="GRP-PTY-ROLE-DIRECT",
        revenue_mode=RevenueMode.AGENCY,
        operator_party_id=current_party.id,
        owner_party_id=current_party.id,
        effective_from=today - timedelta(days=1),
    )
    expired_group = ContractGroup(
        contract_group_id="group-party-role-expired",
        project_id=project.id,
        group_code="GRP-PTY-ROLE-EXPIRED",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=current_party.id,
        owner_party_id=current_party.id,
        effective_from=today - timedelta(days=30),
        effective_to=today - timedelta(days=1),
    )
    out_of_scope_group = ContractGroup(
        contract_group_id="group-party-role-out",
        project_id=project.id,
        group_code="GRP-PTY-ROLE-OUT",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=current_party.id,
        owner_party_id=current_party.id,
        effective_from=today - timedelta(days=1),
    )
    db_session.add_all(
        [active_group, direct_lease_group, expired_group, out_of_scope_group]
    )
    db_session.flush()
    db_session.add_all(
        [
            Contract(
                contract_id="contract-party-role-active",
                contract_group_id=active_group.contract_group_id,
                project_id=project.id,
                contract_number="CTR-PTY-ROLE-ACTIVE",
                contract_direction=ContractDirection.LESSOR,
                group_relation_type=GroupRelationType.DOWNSTREAM,
                lessor_party_id=current_party.id,
                lessee_party_id=current_party.id,
                effective_from=today - timedelta(days=1),
                status=ContractLifecycleStatus.ACTIVE,
            ),
            Contract(
                contract_id="contract-party-role-direct",
                contract_group_id=direct_lease_group.contract_group_id,
                project_id=project.id,
                contract_number="CTR-PTY-ROLE-DIRECT",
                contract_direction=ContractDirection.LESSOR,
                group_relation_type=GroupRelationType.DIRECT_LEASE,
                lessor_party_id=current_party.id,
                lessee_party_id=direct_lease_party.id,
                effective_from=today - timedelta(days=1),
                status=ContractLifecycleStatus.ACTIVE,
            ),
            Contract(
                contract_id="contract-party-role-expired",
                contract_group_id=expired_group.contract_group_id,
                project_id=project.id,
                contract_number="CTR-PTY-ROLE-EXPIRED",
                contract_direction=ContractDirection.LESSOR,
                group_relation_type=GroupRelationType.DOWNSTREAM,
                lessor_party_id=current_party.id,
                lessee_party_id=expired_party.id,
                effective_from=today - timedelta(days=30),
                effective_to=today - timedelta(days=1),
                status=ContractLifecycleStatus.ACTIVE,
            ),
            Contract(
                contract_id="contract-party-role-out",
                contract_group_id=out_of_scope_group.contract_group_id,
                project_id=project.id,
                contract_number="CTR-PTY-ROLE-OUT",
                contract_direction=ContractDirection.LESSOR,
                group_relation_type=GroupRelationType.DOWNSTREAM,
                lessor_party_id=current_party.id,
                lessee_party_id=out_of_scope_party.id,
                effective_from=today - timedelta(days=1),
                status=ContractLifecycleStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    response = client.get("/api/v1/parties?business_role=terminal_tenant")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    payload_by_party_id = {item["id"]: item for item in payload}
    assert set(payload_by_party_id) == {current_party.id, direct_lease_party.id}
    assert payload_by_party_id[current_party.id]["business_roles"] == [
        "owner",
        "operator",
        "terminal_tenant",
    ]
    assert payload_by_party_id[direct_lease_party.id]["business_roles"] == [
        "terminal_tenant"
    ]


def test_user_party_bindings_list_should_work(client, db_session) -> None:
    """用户主体绑定查询接口应保留，只读数据不需要预览令牌。"""
    from src.models.auth import User
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    user = User(
        id="binding-user-1",
        username="binding_user_1",
        email="binding.user.1@example.com",
        phone="13900000001",
        full_name="绑定用户1",
        password_hash="hashed-password",
        is_active=False,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Binding Party",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    db_session.add_all([user, party])
    db_session.flush()
    binding = UserPartyBinding(
        user_id=user.id,
        party_id=party.id,
        relation_type=RelationType.OWNER,
    )
    db_session.add(binding)
    db_session.flush()

    list_response = client.get(f"/api/v1/users/{user.id}/party-bindings")

    assert list_response.status_code == status.HTTP_200_OK
    listed_payload = list_response.json()
    assert isinstance(listed_payload, list)
    assert len(listed_payload) == 1
    assert listed_payload[0]["id"] == binding.id
    assert listed_payload[0]["relation_type"] == "owner"
    assert "is_primary" not in listed_payload[0]


def test_party_review_endpoints_should_transition_review_status(
    client, db_session
) -> None:
    """主体审核接口应支持提审、通过、驳回三段流转。"""
    from src.models.party import Party, PartyReviewStatus, PartyType

    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Review Party",
        code="LE-000001",
        status="active",
        review_status=PartyReviewStatus.DRAFT,
    )
    db_session.add(party)
    db_session.flush()

    submit_response = client.post(f"/api/v1/parties/{party.id}/submit-review")
    assert submit_response.status_code == status.HTTP_200_OK
    assert submit_response.json()["review_status"] == PartyReviewStatus.PENDING

    approve_response = client.post(f"/api/v1/parties/{party.id}/approve-review")
    assert approve_response.status_code == status.HTTP_200_OK
    approve_payload = approve_response.json()
    assert approve_payload["review_status"] == PartyReviewStatus.APPROVED
    assert approve_payload["reviewed_at"] is not None

    party_reject = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Reject Party",
        code="LE-000002",
        status="active",
        review_status=PartyReviewStatus.PENDING,
    )
    db_session.add(party_reject)
    db_session.flush()

    reject_response = client.post(
        f"/api/v1/parties/{party_reject.id}/reject-review",
        json={"reason": "资料不完整"},
    )
    assert reject_response.status_code == status.HTTP_200_OK
    reject_payload = reject_response.json()
    assert reject_payload["review_status"] == PartyReviewStatus.REJECTED
    assert reject_payload["review_reason"] == "资料不完整"


def test_import_parties_should_return_created_and_error_summary(client) -> None:
    with patch(
        "src.api.v1.party.party_service.import_parties",
        new=AsyncMock(
            return_value={
                "created_count": 1,
                "error_count": 1,
                "items": [
                    {
                        "index": 0,
                        "status": "created",
                        "party_id": "party-1",
                        "message": None,
                    },
                    {
                        "index": 1,
                        "status": "error",
                        "party_id": None,
                        "message": "主体重复",
                    },
                ],
            }
        ),
    ) as mock_import:
        response = client.post(
            "/api/v1/parties/import",
            json={
                "items": [
                    {
                        "party_type": "legal_entity",
                        "name": "导入主体1",
                    },
                    {
                        "party_type": "legal_entity",
                        "name": "导入主体2",
                    },
                ]
            },
        )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["created_count"] == 1
    assert payload["error_count"] == 1
    assert payload["items"][0]["status"] == "created"
    assert payload["items"][1]["status"] == "error"
    mock_import.assert_awaited_once()


def test_get_party_review_logs_should_return_entries(client) -> None:
    log_entry = type(
        "LogEntry",
        (),
        {
            "id": "log-1",
            "party_id": "party-1",
            "action": "update",
            "from_status": "draft",
            "to_status": "draft",
            "operator": "tester",
            "reason": "fields:name",
            "created_at": "2026-03-29T08:00:00Z",
        },
    )()

    with (
        patch(
            "src.api.v1.party.party_service.get_party",
            new=AsyncMock(return_value=type("Party", (), {"id": "party-1"})()),
        ),
        patch(
            "src.api.v1.party.party_service.get_review_logs",
            new=AsyncMock(return_value=[log_entry]),
        ),
    ):
        response = client.get("/api/v1/parties/party-1/review-logs")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]["action"] == "update"
    assert payload[0]["reason"] == "fields:name"


def test_party_contact_endpoints_should_use_party_scoped_path(client) -> None:
    with (
        patch(
            "src.api.v1.party.party_service.get_party",
            new=AsyncMock(return_value=type("Party", (), {"id": "party-1"})()),
        ),
        patch(
            "src.api.v1.party.party_service.get_contacts",
            new=AsyncMock(
                return_value=[
                    type(
                        "PartyContact",
                        (),
                        {
                            "id": "contact-1",
                            "party_id": "party-1",
                            "contact_name": "张三",
                            "contact_phone": "13800000000",
                            "contact_email": None,
                            "position": None,
                            "is_primary": True,
                            "notes": None,
                            "created_at": datetime(2026, 6, 3, 10, 0, 0),
                            "updated_at": datetime(2026, 6, 3, 10, 0, 0),
                        },
                    )()
                ]
            ),
        ) as mock_get_contacts,
    ):
        response = client.get("/api/v1/parties/party-1/contacts")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload[0]["party_id"] == "party-1"
    assert payload[0]["contact_name"] == "张三"
    mock_get_contacts.assert_awaited_once()


def test_get_customer_profile_should_require_perspective_and_return_profile(
    client, db_session
) -> None:
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")
    scoped_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="经营主体",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    db_session.add(scoped_party)
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=scoped_party.id,
            relation_type=RelationType.MANAGER,
        )
    )
    db_session.flush()

    with patch(
        "src.api.v1.party.party_service.get_customer_profile",
        new=AsyncMock(
            return_value={
                "customer_party_id": "party-customer-1",
                "customer_name": "终端租户甲",
                "customer_type": "external",
                "subject_nature": "enterprise",
                "binding_type": "manager",
                "contract_role": "entrusted_operation",
                "contact_name": "张三",
                "contact_phone": "13800000000",
                "identifier_type": "unified_social_credit_code",
                "identifier_display": "91310000123456789A",
                "address": "上海市徐汇区测试路 1 号",
                "status": "active",
                "historical_contract_count": 2,
                "risk_tags": ["手工关注", "代理口径冲突"],
                "risk_tag_items": [
                    {"tag": "手工关注", "source": "manual", "updated_at": None},
                    {
                        "tag": "代理口径冲突",
                        "source": "rule",
                        "updated_at": "2026-03-30T00:00:00",
                    },
                ],
                "payment_term_preference": "月付",
                "contracts": [
                    {
                        "contract_id": "contract-1",
                        "contract_number": "CTR-001",
                        "group_code": "GRP-001",
                        "revenue_mode": "AGENCY",
                        "group_relation_type": "DIRECT_LEASE",
                        "status": "ACTIVE",
                        "effective_from": "2026-01-01T00:00:00",
                        "effective_to": "2026-12-31T00:00:00",
                    }
                ],
            }
        ),
    ) as mock_get_customer_profile:
        response = client.get(
            "/api/v1/customers/party-customer-1",
            headers={"X-Perspective": "manager"},
        )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["customer_party_id"] == "party-customer-1"
    assert payload["binding_type"] == "manager"
    assert payload["historical_contract_count"] == 2
    assert payload["risk_tag_items"][1]["source"] == "rule"
    mock_get_customer_profile.assert_awaited_once()


def test_create_user_party_binding_should_return_400_for_invalid_time_range(
    client, db_session
) -> None:
    """生效区间非法时应返回业务 400，而不是 500。"""
    from datetime import UTC, datetime, timedelta

    from src.models.auth import User
    from src.models.party import Party, PartyType

    user = User(
        id="binding-user-invalid-time",
        username="binding_user_invalid_time",
        email="binding.user.invalid.time@example.com",
        phone="13900000002",
        full_name="绑定用户非法时间",
        password_hash="hashed-password",
        is_active=False,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Binding Party Invalid Time",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    db_session.add_all([user, party])
    db_session.flush()

    response = client.post(
        f"/api/v1/users/{user.id}/party-bindings/preview",
        json={
            "operation": "create",
            "party_id": party.id,
            "relation_type": "owner",
            "valid_to": (
                datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_unit_client_should_bypass_closure_based_require_any_role_dependencies(
    client, monkeypatch
) -> None:
    """unit client 应覆盖路由导入时生成的 require_any_role 闭包依赖。"""
    from src.api.v1 import party as party_module

    monkeypatch.setattr(
        "src.security.permissions.RBACService.get_user_roles",
        AsyncMock(
            side_effect=AssertionError(
                "closure-based role dependency was not bypassed by unit client"
            )
        ),
    )
    monkeypatch.setattr(
        party_module.party_service,
        "get_user_party_bindings",
        AsyncMock(return_value=[]),
    )

    response = client.get("/api/v1/users/test-user-1/party-bindings")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_parties_should_inherit_scope_from_user_organization(
    client, db_session
) -> None:
    """没有当前显式绑定时，应继承最近组织的有效代表主体。"""
    from src.models.organization import Organization
    from src.models.party import Party, PartyType

    represented_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="代表主体",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    db_session.add(represented_party)
    db_session.flush()

    organization = Organization(
        id="org-1",
        name="组织一",
        code="ORG-001",
        level=1,
        type="company",
        status="active",
        represented_party_id=represented_party.id,
        represented_party_perspective="owner",
    )
    db_session.add(organization)
    db_session.flush()

    _create_user(
        db_session,
        user_id="test_user_001",
        organization_id=organization.id,
    )

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.json()] == [represented_party.id]


def test_list_parties_should_bypass_scope_for_admin_user(client, db_session) -> None:
    """管理员应保留全量旁路能力。"""
    from src.models.party import Party, PartyType

    db_session.add_all(
        [
            Party(
                party_type=PartyType.LEGAL_ENTITY,
                name="Acme Holdings",
                code="LE-000001",
                status="active",
            ),
            Party(
                party_type=PartyType.LEGAL_ENTITY,
                name="Beta Group",
                code="LE-000002",
                status="active",
            ),
        ]
    )
    db_session.flush()

    from src.services.party_scope_resolver import EffectivePartyScope

    with patch(
        "src.services.party_scope.party_scope_resolver.resolve",
        new=AsyncMock(
            return_value=EffectivePartyScope(
                user_id="test_user_001",
                source="unrestricted",
                scope_mode="unrestricted",
            )
        ),
    ):
        response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    codes = {item["code"] for item in payload}
    assert {"LE-000001", "LE-000002"}.issubset(codes)


def test_list_parties_cross_user_isolation(client, db_session) -> None:
    """§6.1 用户 A 的请求不应返回仅绑定给用户 B 的主体（跨用户隔离）。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    # client fixture 的认证用户为 test_user_001
    _create_user(db_session, user_id="test_user_001")
    _create_user(db_session, user_id="test_user_002")

    party_a = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Party Alpha",
        code="LE-000001",
        status="active",
        review_status="approved",
    )
    party_b = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Party Beta",
        code="LE-000002",
        status="active",
        review_status="approved",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=party_a.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.add(
        UserPartyBinding(
            user_id="test_user_002",
            party_id=party_b.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    ids = [p["id"] for p in payload]
    assert party_a.id in ids, "用户 A 应能看到自己绑定的主体"
    assert party_b.id not in ids, "用户 A 不应看到仅属于用户 B 的主体"


def test_list_parties_returns_empty_when_scope_resolver_raises(
    client, db_session
) -> None:
    """§6.6 scope 解析异常时必须 fail-closed，不得泄露全量数据。"""
    from src.models.party import Party, PartyType

    db_session.add(
        Party(
            party_type=PartyType.LEGAL_ENTITY,
            name="Should Not Be Visible",
            code="LE-000001",
            status="active",
        )
    )
    db_session.flush()

    with patch(
        "src.services.party_scope.party_scope_resolver.resolve",
        new=AsyncMock(side_effect=RuntimeError("simulated scope resolution failure")),
    ):
        response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [], "scope 异常时必须 fail-closed，不得返回全量数据"


def test_approved_party_lifecycle_requires_preview_then_commit(
    client, db_session
) -> None:
    """Approved Party activation changes are auditable, previewed mutations."""
    from src.models.auth import User
    from src.models.party import Party, PartyReviewStatus, PartyType

    actor = User(
        id="test_user_001",
        username="test_user_001",
        email="test.user.001@example.com",
        phone="13900000001",
        full_name="Party lifecycle manager",
        password_hash="hashed-password",
        account_type="service",
        is_active=True,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Lifecycle Party",
        code="LE-000061",
        status="active",
        review_status=PartyReviewStatus.APPROVED,
    )
    db_session.add_all([actor, party])
    db_session.flush()

    preview_response = client.post(
        f"/api/v1/parties/{party.id}/status/preview",
        json={"operation": "deactivate"},
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["before_state"]["status"] == "active"
    assert preview_payload["after_state"]["status"] == "inactive"
    db_session.refresh(party)
    assert party.status == "active"

    direct_status_write = client.put(
        f"/api/v1/parties/{party.id}",
        json={"status": "inactive"},
    )
    assert direct_status_write.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "Retire the Party from new references.",
        "idempotency_key": "party-lifecycle-api-1",
    }
    commit_response = client.post(
        f"/api/v1/parties/{party.id}/deactivate",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    commit_payload = commit_response.json()
    assert commit_payload["operation"] == "deactivate"
    assert commit_payload["party"]["status"] == "inactive"
    assert commit_payload["idempotent"] is False

    repeated_commit = client.post(
        f"/api/v1/parties/{party.id}/deactivate",
        json=commit_request,
    )
    assert repeated_commit.status_code == status.HTTP_200_OK
    assert repeated_commit.json()["idempotent"] is True

    stale_commit = client.post(
        f"/api/v1/parties/{party.id}/deactivate",
        json={
            **commit_request,
            "idempotency_key": "party-lifecycle-api-1-stale",
        },
    )
    assert stale_commit.status_code == status.HTTP_409_CONFLICT
    assert stale_commit.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"

    reactivate_preview = client.post(
        f"/api/v1/parties/{party.id}/status/preview",
        json={"operation": "reactivate"},
    )
    assert reactivate_preview.status_code == status.HTTP_200_OK

    reactivate_commit = client.post(
        f"/api/v1/parties/{party.id}/reactivate",
        json={
            "preview_token": reactivate_preview.json()["preview_token"],
            "reason": "Restore approved Party references.",
            "idempotency_key": "party-lifecycle-api-2",
        },
    )
    assert reactivate_commit.status_code == status.HTTP_200_OK
    assert reactivate_commit.json()["party"]["status"] == "active"


def test_party_lifecycle_preview_reports_scope_impact_and_rejects_status_drift(
    client, db_session
) -> None:
    """A Party preview captures scope impact and refuses a changed target state."""
    from src.models.auth import User
    from src.models.organization import Organization
    from src.models.party import Party, PartyReviewStatus, PartyType
    from src.models.party_lifecycle_commit import PartyLifecycleCommit
    from src.models.user_party_binding import RelationType, UserPartyBinding

    actor = User(
        id="test_user_001",
        username="test_user_001",
        email="test.user.001@example.com",
        phone="13900000001",
        full_name="Party lifecycle manager",
        password_hash="hashed-password",
        account_type="service",
        is_active=True,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Impacted Party",
        code="LE-000062",
        status="active",
        review_status=PartyReviewStatus.APPROVED,
    )
    organization = Organization(
        id="party-lifecycle-org-1",
        name="Lifecycle Organization",
        code="ORG-LIFECYCLE-1",
        level=1,
        sort_order=1,
        type="department",
        status="active",
        represented_party_id=None,
        represented_party_perspective=None,
        is_deleted=False,
    )
    db_session.add_all([actor, party, organization])
    db_session.flush()
    organization.represented_party_id = party.id
    organization.represented_party_perspective = "owner"
    user = User(
        id="party-lifecycle-user-1",
        username="party_lifecycle_user_1",
        email="party.lifecycle.user.1@example.com",
        phone="13900000062",
        full_name="Affected human user",
        password_hash="hashed-password",
        account_type="human",
        organization_id=organization.id,
        is_active=True,
        is_locked=False,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id=user.id,
            party_id=party.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.flush()

    preview_response = client.post(
        f"/api/v1/parties/{party.id}/status/preview",
        json={"operation": "deactivate"},
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["impact"] == {
        "represented_organization_count": 1,
        "potentially_affected_organization_count": 1,
        "current_user_binding_count": 1,
        "affected_user_count": 1,
        "user_scope_change_count": 1,
        "asset_reference_count": 0,
        "project_reference_count": 0,
        "contract_group_reference_count": 0,
        "contract_reference_count": 0,
    }

    party.status = "inactive"
    db_session.flush()
    stale_commit = client.post(
        f"/api/v1/parties/{party.id}/deactivate",
        json={
            "preview_token": preview_payload["preview_token"],
            "reason": "This preview must not commit after a status change.",
            "idempotency_key": "party-lifecycle-status-drift",
        },
    )

    assert stale_commit.status_code == status.HTTP_409_CONFLICT
    assert stale_commit.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"
    assert (
        db_session.query(PartyLifecycleCommit).filter_by(party_id=party.id).count() == 0
    )
