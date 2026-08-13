"""Public API contract for sensitive user Party-scope changes."""

from datetime import datetime

from fastapi import status

from tests.fixtures import fake_bcrypt_hash


def test_user_party_binding_mutations_require_preview_then_commit(
    client, db_session
) -> None:
    """Only a bound preview/commit can change a user's explicit Party scope."""
    from src.models.auth import User
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import UserPartyBinding

    actor = User(
        id="test_user_001",
        username="test_user_001",
        email="test.user.001@example.com",
        phone="13900000001",
        full_name="范围管理员",
        password_hash=fake_bcrypt_hash(),
        account_type="service",
        is_active=True,
        is_locked=False,
    )
    user = User(
        id="user-party-scope-api-1",
        username="user_party_scope_api_1",
        email="user.party.scope.api.1@example.com",
        phone="13900000031",
        full_name="用户主体范围接口测试",
        password_hash=fake_bcrypt_hash(),
        is_active=False,
        is_locked=False,
    )
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="User Scope Party",
        code="LE-000031",
        status="active",
        review_status="approved",
    )
    db_session.add_all([actor, user, party])
    db_session.flush()

    preview_response = client.post(
        f"/api/v1/users/{user.id}/party-bindings/preview",
        json={
            "operation": "create",
            "party_id": party.id,
            "relation_type": "owner",
        },
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["after_scope"]["source"] == "explicit"
    assert db_session.query(UserPartyBinding).filter_by(user_id=user.id).count() == 0

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "明确用户数据范围",
        "idempotency_key": "user-party-scope-api-1",
    }
    commit_response = client.post(
        f"/api/v1/users/{user.id}/party-bindings/commit",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    commit_payload = commit_response.json()
    assert commit_payload["binding"]["user_id"] == user.id
    assert commit_payload["binding"]["party_id"] == party.id
    assert commit_payload["binding"]["relation_type"] == "owner"

    repeated_commit = client.post(
        f"/api/v1/users/{user.id}/party-bindings/commit",
        json=commit_request,
    )
    assert repeated_commit.status_code == status.HTTP_200_OK
    assert repeated_commit.json()["idempotent"] is True

    stale_commit = client.post(
        f"/api/v1/users/{user.id}/party-bindings/commit",
        json={
            **commit_request,
            "idempotency_key": "user-party-scope-api-1-stale",
        },
    )
    assert stale_commit.status_code == status.HTTP_409_CONFLICT
    assert stale_commit.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"

    binding_id = commit_payload["binding"]["id"]
    direct_create = client.post(
        f"/api/v1/users/{user.id}/party-bindings",
        json={"party_id": party.id, "relation_type": "manager"},
    )
    direct_update = client.put(
        f"/api/v1/users/{user.id}/party-bindings/{binding_id}",
        json={"relation_type": "manager"},
    )
    direct_close = client.delete(f"/api/v1/users/{user.id}/party-bindings/{binding_id}")

    assert direct_create.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert direct_update.status_code == status.HTTP_404_NOT_FOUND
    assert direct_close.status_code == status.HTTP_404_NOT_FOUND


def test_user_party_scope_proposal_normalizes_aware_datetimes_to_naive_utc() -> None:
    """Database-backed binding comparisons always use the canonical UTC form."""
    from src.schemas.user_party_scope import UserPartyBindingScopeProposal

    proposal = UserPartyBindingScopeProposal.model_validate(
        {
            "operation": "create",
            "party_id": "party-1",
            "relation_type": "owner",
            "valid_from": "2026-08-04T08:00:00+08:00",
            "valid_to": "2026-08-04T09:00:00+08:00",
        }
    )

    assert proposal.valid_from == datetime(2026, 8, 4, 0, 0)
    assert proposal.valid_to == datetime(2026, 8, 4, 1, 0)
    assert proposal.valid_from.tzinfo is None
    assert proposal.valid_to.tzinfo is None


def test_user_party_binding_update_and_close_require_fresh_previews(
    client, db_session
) -> None:
    """Update and close carry the same durable preview/commit guarantee as create."""
    from src.models.auth import User
    from src.models.party import Party, PartyType

    actor = User(
        id="test_user_001",
        username="test_user_001",
        email="test.user.001@example.com",
        phone="13900000001",
        full_name="Scope manager",
        password_hash=fake_bcrypt_hash(),
        account_type="service",
        is_active=True,
        is_locked=False,
    )
    user = User(
        id="user-party-scope-api-2",
        username="user_party_scope_api_2",
        email="user.party.scope.api.2@example.com",
        phone="13900000032",
        full_name="Scoped user",
        password_hash=fake_bcrypt_hash(),
        is_active=False,
        is_locked=False,
    )
    owner_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Owner scope party",
        code="LE-000041",
        status="active",
        review_status="approved",
    )
    manager_party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Manager scope party",
        code="LE-000042",
        status="active",
        review_status="approved",
    )
    db_session.add_all([actor, user, owner_party, manager_party])
    db_session.flush()

    def preview_and_commit(proposal: dict[str, object], idempotency_key: str) -> dict:
        preview_response = client.post(
            f"/api/v1/users/{user.id}/party-bindings/preview",
            json=proposal,
        )
        assert preview_response.status_code == status.HTTP_200_OK
        preview_payload = preview_response.json()
        commit_response = client.post(
            f"/api/v1/users/{user.id}/party-bindings/commit",
            json={
                "preview_token": preview_payload["preview_token"],
                "reason": "Exercise the user Party scope operation.",
                "idempotency_key": idempotency_key,
            },
        )
        assert commit_response.status_code == status.HTTP_200_OK
        return commit_response.json()

    created = preview_and_commit(
        {
            "operation": "create",
            "party_id": owner_party.id,
            "relation_type": "owner",
        },
        "user-party-scope-create-2",
    )
    binding_id = created["binding"]["id"]

    updated = preview_and_commit(
        {
            "operation": "update",
            "binding_id": binding_id,
            "party_id": manager_party.id,
            "relation_type": "manager",
        },
        "user-party-scope-update-2",
    )
    assert updated["operation"] == "update"
    assert updated["binding"]["party_id"] == manager_party.id
    assert updated["binding"]["relation_type"] == "manager"

    closed = preview_and_commit(
        {
            "operation": "close",
            "binding_id": binding_id,
        },
        "user-party-scope-close-2",
    )
    assert closed["operation"] == "close"
    assert closed["binding"]["valid_to"] is not None
    assert closed["impact"]["after_current_binding_count"] == 0
    assert closed["after_scope"]["source"] == "none"
