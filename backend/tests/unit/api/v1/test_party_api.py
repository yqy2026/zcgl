"""Party API behavior tests."""

from unittest.mock import AsyncMock, patch

from fastapi import status


def _create_user(
    db_session,
    *,
    user_id: str,
    default_organization_id: str | None = None,
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
            is_active=True,
            is_locked=False,
            default_organization_id=default_organization_id,
        )
    )
    db_session.flush()


def test_list_parties_should_filter_by_search_query(client, db_session) -> None:
    """`/parties` 应根据 search 过滤名称/编码匹配结果。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")

    matching_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Acme Holdings",
        code="ACME-001",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Beta Group",
        code="BETA-001",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=matching_party.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties?search=acme")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Acme Holdings"
    assert payload[0]["code"] == "ACME-001"


def test_list_parties_should_filter_by_search_code(client, db_session) -> None:
    """`/parties` 应支持按编码模糊搜索。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")

    matching_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Code Match Party",
        code="ACME-001",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Other Party",
        code="BETA-001",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=matching_party.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties?search=ACME-001")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Code Match Party"
    assert payload[0]["code"] == "ACME-001"


def test_list_parties_should_fail_closed_when_user_has_no_bindings(
    client, db_session
) -> None:
    """无绑定时列表接口应 fail-closed 返回空列表。"""
    from src.models.party import Party, PartyType

    db_session.add(
        Party(
            party_type=PartyType.ORGANIZATION,
            name="Acme Holdings",
            code="ACME-001",
            status="active",
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_user_party_bindings_crud_should_work(client, db_session) -> None:
    """用户主体绑定接口应支持新增、查询、更新和关闭。"""
    from src.models.auth import User
    from src.models.party import Party, PartyType

    user = User(
        id="binding-user-1",
        username="binding_user_1",
        email="binding.user.1@example.com",
        phone="13900000001",
        full_name="绑定用户1",
        password_hash="hashed-password",
        is_active=True,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Binding Party",
        code="BIND-001",
        status="active",
    )
    db_session.add_all([user, party])
    db_session.flush()

    create_response = client.post(
        f"/api/v1/users/{user.id}/party-bindings",
        json={
            "party_id": party.id,
            "relation_type": "owner",
            "is_primary": True,
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    created_payload = create_response.json()
    assert created_payload["user_id"] == user.id
    assert created_payload["party_id"] == party.id
    assert created_payload["relation_type"] == "owner"
    assert created_payload["is_primary"] is True

    list_response = client.get(f"/api/v1/users/{user.id}/party-bindings")
    assert list_response.status_code == status.HTTP_200_OK
    listed_payload = list_response.json()
    assert isinstance(listed_payload, list)
    assert len(listed_payload) == 1
    assert listed_payload[0]["id"] == created_payload["id"]

    update_response = client.put(
        f"/api/v1/users/{user.id}/party-bindings/{created_payload['id']}",
        json={
            "relation_type": "manager",
            "is_primary": False,
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_payload = update_response.json()
    assert updated_payload["relation_type"] == "manager"
    assert updated_payload["is_primary"] is False

    delete_response = client.delete(
        f"/api/v1/users/{user.id}/party-bindings/{created_payload['id']}"
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "用户主体绑定已关闭"

    active_response = client.get(
        f"/api/v1/users/{user.id}/party-bindings?active_only=true"
    )
    assert active_response.status_code == status.HTTP_200_OK
    assert active_response.json() == []


def test_party_review_endpoints_should_transition_review_status(
    client, db_session
) -> None:
    """主体审核接口应支持提审、通过、驳回三段流转。"""
    from src.models.party import Party, PartyReviewStatus, PartyType

    party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Review Party",
        code="REVIEW-001",
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
        party_type=PartyType.ORGANIZATION,
        name="Reject Party",
        code="REJECT-001",
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
    assert reject_payload["review_status"] == PartyReviewStatus.DRAFT
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
                        "party_type": "organization",
                        "name": "导入主体1",
                        "code": "IMP-001",
                    },
                    {
                        "party_type": "organization",
                        "name": "导入主体2",
                        "code": "IMP-002",
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


def test_get_customer_profile_should_require_perspective_and_return_profile(
    client, db_session
) -> None:
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")
    scoped_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="经营主体",
        code="MGR-001",
        status="active",
    )
    db_session.add(scoped_party)
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=scoped_party.id,
            relation_type=RelationType.MANAGER,
            is_primary=True,
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
                "identifier_type": "USCC",
                "unified_identifier": "91310000123456789A",
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
        is_active=True,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Binding Party Invalid Time",
        code="BIND-002",
        status="active",
    )
    db_session.add_all([user, party])
    db_session.flush()

    response = client.post(
        f"/api/v1/users/{user.id}/party-bindings",
        json={
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


def test_list_parties_should_ignore_legacy_default_org_fallback(
    client, db_session
) -> None:
    """无绑定时即使存在 legacy default_organization 映射也应 fail-closed。"""
    from src.models.organization import Organization
    from src.models.party import Party, PartyType

    organization = Organization(
        id="org-legacy-1",
        name="组织一",
        code="ORG-001",
        level=1,
        type="company",
        status="active",
    )
    db_session.add(organization)
    db_session.flush()

    _create_user(
        db_session,
        user_id="test_user_001",
        default_organization_id=organization.id,
    )
    db_session.add(
        Party(
            party_type=PartyType.ORGANIZATION,
            name="映射主体",
            code="PARTY-ORG-001",
            external_ref=organization.id,
            status="active",
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_parties_should_bypass_scope_for_admin_user(client, db_session) -> None:
    """管理员应保留全量旁路能力。"""
    from src.models.party import Party, PartyType

    db_session.add_all(
        [
            Party(
                party_type=PartyType.ORGANIZATION,
                name="Acme Holdings",
                code="ACME-001",
                status="active",
            ),
            Party(
                party_type=PartyType.ORGANIZATION,
                name="Beta Group",
                code="BETA-001",
                status="active",
            ),
        ]
    )
    db_session.flush()

    with patch(
        "src.services.party_scope._has_unrestricted_party_scope_access",
        new=AsyncMock(return_value=True),
    ):
        response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    codes = {item["code"] for item in payload}
    assert {"ACME-001", "BETA-001"}.issubset(codes)


def test_list_parties_cross_user_isolation(client, db_session) -> None:
    """§6.1 用户 A 的请求不应返回仅绑定给用户 B 的主体（跨用户隔离）。"""
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    # client fixture 的认证用户为 test_user_001
    _create_user(db_session, user_id="test_user_001")
    _create_user(db_session, user_id="test_user_002")

    party_a = Party(
        party_type=PartyType.ORGANIZATION,
        name="Party Alpha",
        code="ALPHA-001",
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION,
        name="Party Beta",
        code="BETA-002",
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=party_a.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )
    db_session.add(
        UserPartyBinding(
            user_id="test_user_002",
            party_id=party_b.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    ids = [p["id"] for p in payload]
    assert party_a.id in ids, "用户 A 应能看到自己绑定的主体"
    assert party_b.id not in ids, "用户 A 不应看到仅属于用户 B 的主体"


def test_list_parties_headquarters_expands_to_manager_descendants(
    client, db_session
) -> None:
    """§6.2 headquarters 绑定应展开子树（含自身）纳入 manager 视角，无关主体不可见。"""
    from src.models.party import Party, PartyHierarchy, PartyType
    from src.models.user_party_binding import RelationType, UserPartyBinding

    _create_user(db_session, user_id="test_user_001")

    party_h = Party(
        party_type=PartyType.ORGANIZATION,
        name="Headquarters Party",
        code="HQ-001",
        status="active",
    )
    party_m1 = Party(
        party_type=PartyType.ORGANIZATION,
        name="Manager Child Party",
        code="MGR-001",
        status="active",
    )
    party_x = Party(
        party_type=PartyType.ORGANIZATION,
        name="Unrelated Party",
        code="UNRELATED-001",
        status="active",
    )
    db_session.add_all([party_h, party_m1, party_x])
    db_session.flush()

    db_session.add(
        PartyHierarchy(
            parent_party_id=party_h.id,
            child_party_id=party_m1.id,
        )
    )
    db_session.add(
        UserPartyBinding(
            user_id="test_user_001",
            party_id=party_h.id,
            relation_type=RelationType.HEADQUARTERS,
            is_primary=True,
        )
    )
    db_session.flush()

    response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    ids = [p["id"] for p in payload]
    assert party_h.id in ids, "headquarters 自身应在可见范围内"
    assert party_m1.id in ids, "headquarters 直接子节点应在可见范围内"
    assert party_x.id not in ids, "无关主体不应出现在 headquarters 范围内"


def test_list_parties_returns_empty_when_scope_resolver_raises(
    client, db_session
) -> None:
    """§6.6 scope 解析异常时必须 fail-closed，不得泄露全量数据。"""
    from src.models.party import Party, PartyType

    db_session.add(
        Party(
            party_type=PartyType.ORGANIZATION,
            name="Should Not Be Visible",
            code="SECRET-001",
            status="active",
        )
    )
    db_session.flush()

    with patch(
        "src.crud.party.CRUDParty.get_user_bindings",
        new=AsyncMock(side_effect=RuntimeError("simulated scope resolution failure")),
    ):
        response = client.get("/api/v1/parties")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [], "scope 异常时必须 fail-closed，不得返回全量数据"
