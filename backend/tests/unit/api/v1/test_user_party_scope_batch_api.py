"""Public API contract for all-or-nothing user Party-scope batches."""

from fastapi import status

from tests.fixtures import fake_bcrypt_hash


def _add_batch_fixture(db_session):
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
    first_user = User(
        id="user-party-batch-first",
        username="user_party_batch_first",
        email="user.party.batch.first@example.com",
        phone="13900000041",
        full_name="First scoped user",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        is_active=False,
        is_locked=False,
    )
    second_user = User(
        id="user-party-batch-second",
        username="user_party_batch_second",
        email="user.party.batch.second@example.com",
        phone="13900000042",
        full_name="Second scoped user",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        is_active=False,
        is_locked=False,
    )
    first_party = Party(
        id="user-party-batch-party-first",
        party_type=PartyType.LEGAL_ENTITY,
        name="Batch Party First",
        code="LE-009301",
        status="active",
        review_status="approved",
    )
    second_party = Party(
        id="user-party-batch-party-second",
        party_type=PartyType.LEGAL_ENTITY,
        name="Batch Party Second",
        code="LE-009302",
        status="active",
        review_status="approved",
    )
    db_session.add_all(
        [
            actor,
            first_user,
            second_user,
            first_party,
            second_party,
        ]
    )
    db_session.flush()
    return first_user, second_user, first_party, second_party


def test_user_party_scope_batch_requires_preview_and_commits_all_items(
    client, db_session
) -> None:
    """A batch persists every selected explicit binding once, or none of them."""
    from src.models.user_party_binding import UserPartyBinding
    from src.models.user_party_scope_batch_commit import UserPartyScopeBatchCommit

    first_user, second_user, first_party, second_party = _add_batch_fixture(db_session)
    preview_response = client.post(
        "/api/v1/users/party-bindings/batch/preview",
        json={
            "items": [
                {
                    "user_id": first_user.id,
                    "operation": "create",
                    "party_id": first_party.id,
                    "relation_type": "owner",
                },
                {
                    "user_id": second_user.id,
                    "operation": "create",
                    "party_id": second_party.id,
                    "relation_type": "manager",
                },
            ]
        },
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["impact"]["user_count"] == 2
    assert preview_payload["impact"]["binding_change_count"] == 2
    assert {item["user"]["id"] for item in preview_payload["items"]} == {
        first_user.id,
        second_user.id,
    }
    assert db_session.query(UserPartyBinding).count() == 0

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "Align both user scopes in one transaction.",
        "idempotency_key": "user-party-scope-batch-1",
    }
    commit_response = client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    commit_payload = commit_response.json()
    assert commit_payload["idempotent"] is False
    assert len(commit_payload["items"]) == 2
    assert db_session.query(UserPartyBinding).count() == 2
    assert db_session.query(UserPartyScopeBatchCommit).count() == 1

    retry_response = client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json=commit_request,
    )
    assert retry_response.status_code == status.HTTP_200_OK
    assert retry_response.json()["idempotent"] is True
    assert db_session.query(UserPartyScopeBatchCommit).count() == 1


def test_user_party_scope_batch_rejects_state_drift_without_partial_write(
    client, db_session
) -> None:
    """One stale user prevents every batch item from being committed."""
    from src.models.user_party_binding import UserPartyBinding

    first_user, second_user, first_party, second_party = _add_batch_fixture(db_session)
    preview_response = client.post(
        "/api/v1/users/party-bindings/batch/preview",
        json={
            "items": [
                {
                    "user_id": first_user.id,
                    "operation": "create",
                    "party_id": first_party.id,
                    "relation_type": "owner",
                },
                {
                    "user_id": second_user.id,
                    "operation": "create",
                    "party_id": second_party.id,
                    "relation_type": "manager",
                },
            ]
        },
    )
    assert preview_response.status_code == status.HTTP_200_OK

    first_user.full_name = "Stale scoped user"
    db_session.flush()

    commit_response = client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This must not partially commit after state drift.",
            "idempotency_key": "user-party-scope-batch-stale-1",
        },
    )

    assert commit_response.status_code == status.HTTP_409_CONFLICT
    assert commit_response.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"
    assert db_session.query(UserPartyBinding).count() == 0


def test_user_party_scope_batch_can_close_existing_bindings(client, db_session) -> None:
    """Close proposals remain valid after preview serialization and commit."""
    from src.models.user_party_binding import UserPartyBinding
    from src.models.user_party_scope_batch_commit import UserPartyScopeBatchCommit

    first_user, second_user, first_party, second_party = _add_batch_fixture(db_session)
    first_binding = UserPartyBinding(
        user_id=first_user.id,
        party_id=first_party.id,
        relation_type="owner",
    )
    second_binding = UserPartyBinding(
        user_id=second_user.id,
        party_id=second_party.id,
        relation_type="manager",
    )
    db_session.add_all([first_binding, second_binding])
    db_session.flush()

    preview_response = client.post(
        "/api/v1/users/party-bindings/batch/preview",
        json={
            "items": [
                {
                    "user_id": first_user.id,
                    "operation": "close",
                    "binding_id": first_binding.id,
                },
                {
                    "user_id": second_user.id,
                    "operation": "close",
                    "binding_id": second_binding.id,
                },
            ]
        },
    )

    assert preview_response.status_code == status.HTTP_200_OK
    assert all(
        item["after_scope"]["source"] == "none"
        for item in preview_response.json()["items"]
    )

    commit_response = client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Close both retired scopes.",
            "idempotency_key": "user-party-scope-batch-close-1",
        },
    )

    assert commit_response.status_code == status.HTTP_200_OK
    assert commit_response.json()["idempotent"] is False
    db_session.refresh(first_binding)
    db_session.refresh(second_binding)
    assert first_binding.valid_to is not None
    assert second_binding.valid_to is not None
    assert db_session.query(UserPartyScopeBatchCommit).count() == 1
