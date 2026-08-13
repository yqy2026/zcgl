"""Public API contract for sensitive human-user organization transfers."""

from fastapi import status

from tests.fixtures import fake_bcrypt_hash


def _add_transfer_fixture(db_session):
    from src.models.auth import User
    from src.models.organization import Organization
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
    party = Party(
        id="user-transfer-party-1",
        party_type=PartyType.LEGAL_ENTITY,
        name="Transfer scope party",
        code="LE-009001",
        status="active",
        review_status="approved",
    )
    source = Organization(
        id="user-transfer-source-1",
        name="Source organization",
        code="UT-SOURCE-1",
        level=1,
        type="headquarters",
        status="active",
        path="/user-transfer-source-1",
        represented_party_id=party.id,
        represented_party_perspective="owner",
    )
    target = Organization(
        id="user-transfer-target-1",
        name="Target organization",
        code="UT-TARGET-1",
        level=2,
        type="department",
        status="active",
        parent_id=source.id,
        path="/user-transfer-source-1/user-transfer-target-1",
    )
    user = User(
        id="user-transfer-human-1",
        username="user_transfer_human_1",
        email="user.transfer.human.1@example.com",
        phone="13900000031",
        full_name="Transfer user",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        organization_id=source.id,
        is_active=True,
        is_locked=False,
    )
    db_session.add_all([actor, party, source, target, user])
    db_session.flush()
    return actor, source, target, user


def test_human_user_organization_transfer_requires_preview_then_commit(
    client, db_session
) -> None:
    """A transfer cannot bypass a bound preview and only writes once."""
    from src.models.user_organization_transfer_commit import (
        UserOrganizationTransferCommit,
    )

    _, source, target, user = _add_transfer_fixture(db_session)

    direct_update = client.put(
        f"/api/v1/auth/users/{user.id}",
        json={"organization_id": target.id},
    )
    assert direct_update.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    }

    preview_response = client.post(
        f"/api/v1/auth/users/{user.id}/organization/preview",
        json={"organization_id": target.id},
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["before_scope"]["organization_id"] == source.id
    assert preview_payload["after_scope"]["organization_id"] == target.id
    assert preview_payload["after_scope"]["source_organization_id"] == source.id
    assert preview_payload["impact"]["organization_changed"] is True
    assert user.organization_id == source.id

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "Move the user into the target organization.",
        "idempotency_key": "user-organization-transfer-1",
    }
    commit_response = client.put(
        f"/api/v1/auth/users/{user.id}/organization",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    commit_payload = commit_response.json()
    assert commit_payload["user_id"] == user.id
    assert commit_payload["after_scope"]["organization_id"] == target.id
    assert commit_payload["idempotent"] is False
    db_session.refresh(user)
    assert user.organization_id == target.id
    assert user.updated_by == "test_user_001"
    assert db_session.query(UserOrganizationTransferCommit).count() == 1

    repeated_commit = client.put(
        f"/api/v1/auth/users/{user.id}/organization",
        json=commit_request,
    )
    assert repeated_commit.status_code == status.HTTP_200_OK
    assert repeated_commit.json()["idempotent"] is True
    assert db_session.query(UserOrganizationTransferCommit).count() == 1

    stale_commit = client.put(
        f"/api/v1/auth/users/{user.id}/organization",
        json={
            **commit_request,
            "idempotency_key": "user-organization-transfer-1-stale",
        },
    )
    assert stale_commit.status_code == status.HTTP_409_CONFLICT
    assert stale_commit.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"


def test_user_organization_transfer_rejects_target_state_drift(
    client, db_session
) -> None:
    """A target organization change after preview invalidates the pending write."""
    _, source, target, user = _add_transfer_fixture(db_session)

    preview_response = client.post(
        f"/api/v1/auth/users/{user.id}/organization/preview",
        json={"organization_id": target.id},
    )
    assert preview_response.status_code == status.HTTP_200_OK

    target.status = "inactive"
    db_session.flush()

    commit_response = client.put(
        f"/api/v1/auth/users/{user.id}/organization",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Move after target state drift.",
            "idempotency_key": "user-organization-transfer-stale-1",
        },
    )

    assert commit_response.status_code == status.HTTP_409_CONFLICT
    assert commit_response.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"
    db_session.refresh(user)
    assert user.organization_id == source.id
