"""API coverage for all-or-nothing Organization represented-Party batch changes."""

from fastapi import status


def _add_batch_fixture(db_session):
    from src.models.auth import User
    from src.models.organization import Organization
    from src.models.party import Party, PartyType

    actor = User(
        id="test_user_001",
        username="test_user_001",
        email="test.user.001@example.com",
        phone="13900000001",
        full_name="Scope manager",
        password_hash="hashed-password",
        account_type="service",
        is_active=True,
        is_locked=False,
    )
    old_party_a = Party(
        id="organization-batch-old-a",
        party_type=PartyType.LEGAL_ENTITY,
        name="Old Party A",
        code="LE-009201",
        status="active",
        review_status="approved",
    )
    old_party_b = Party(
        id="organization-batch-old-b",
        party_type=PartyType.LEGAL_ENTITY,
        name="Old Party B",
        code="LE-009202",
        status="active",
        review_status="approved",
    )
    next_party = Party(
        id="organization-batch-next",
        party_type=PartyType.LEGAL_ENTITY,
        name="Next Party",
        code="LE-009203",
        status="active",
        review_status="approved",
    )
    first = Organization(
        id="organization-batch-first",
        name="First Organization",
        code="OB-FIRST",
        level=1,
        type="headquarters",
        status="active",
        path="/organization-batch-first",
        represented_party_id=old_party_a.id,
        represented_party_perspective="owner",
    )
    second = Organization(
        id="organization-batch-second",
        name="Second Organization",
        code="OB-SECOND",
        level=1,
        type="headquarters",
        status="active",
        path="/organization-batch-second",
        represented_party_id=old_party_b.id,
        represented_party_perspective="manager",
    )
    descendant = Organization(
        id="organization-batch-descendant",
        name="First descendant",
        code="OB-DESCENDANT",
        level=2,
        type="department",
        status="active",
        parent_id=first.id,
        path=f"/{first.id}/organization-batch-descendant",
    )
    db_session.add_all(
        [
            actor,
            old_party_a,
            old_party_b,
            next_party,
            first,
            second,
            descendant,
        ]
    )
    db_session.flush()
    return first, second, descendant, next_party


def test_organization_party_scope_batch_requires_preview_and_commits_all_items(
    client, db_session
) -> None:
    """A batch persists every selected direct scope change once, or none of them."""
    from src.models.organization import OrganizationPartyScopeBatchCommit

    first, second, _, next_party = _add_batch_fixture(db_session)
    preview_response = client.post(
        "/api/v1/organizations/party-scope/batch/preview",
        json={
            "items": [
                {
                    "organization_id": first.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "owner",
                },
                {
                    "organization_id": second.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "manager",
                },
            ]
        },
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["impact"]["organization_count"] == 3
    assert first.represented_party_id == "organization-batch-old-a"
    assert second.represented_party_id == "organization-batch-old-b"

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "Align both operating units to the new Party scope.",
        "idempotency_key": "organization-party-scope-batch-1",
    }
    commit_response = client.post(
        "/api/v1/organizations/party-scope/batch/commit",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    assert commit_response.json()["idempotent"] is False
    assert len(commit_response.json()["items"]) == 2
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.represented_party_id == next_party.id
    assert second.represented_party_id == next_party.id
    assert db_session.query(OrganizationPartyScopeBatchCommit).count() == 1

    retry_response = client.post(
        "/api/v1/organizations/party-scope/batch/commit",
        json=commit_request,
    )
    assert retry_response.status_code == status.HTTP_200_OK
    assert retry_response.json()["idempotent"] is True
    assert db_session.query(OrganizationPartyScopeBatchCommit).count() == 1


def test_organization_party_scope_batch_rejects_state_drift_without_partial_write(
    client, db_session
) -> None:
    """One stale target prevents every batch item from being committed."""
    first, second, _, next_party = _add_batch_fixture(db_session)
    preview_response = client.post(
        "/api/v1/organizations/party-scope/batch/preview",
        json={
            "items": [
                {
                    "organization_id": first.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "owner",
                },
                {
                    "organization_id": second.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "manager",
                },
            ]
        },
    )
    assert preview_response.status_code == status.HTTP_200_OK

    second.status = "inactive"
    db_session.flush()

    commit_response = client.post(
        "/api/v1/organizations/party-scope/batch/commit",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This must not partially commit after state drift.",
            "idempotency_key": "organization-party-scope-batch-stale-1",
        },
    )

    assert commit_response.status_code == status.HTTP_409_CONFLICT
    assert commit_response.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"
    db_session.refresh(first)
    assert first.represented_party_id == "organization-batch-old-a"


def test_organization_party_scope_batch_rejects_overlapping_subtrees(client, db_session) -> None:
    """A batch cannot analyze a parent and descendant against separate baselines."""
    first, _, descendant, next_party = _add_batch_fixture(db_session)

    response = client.post(
        "/api/v1/organizations/party-scope/batch/preview",
        json={
            "items": [
                {
                    "organization_id": first.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "owner",
                },
                {
                    "organization_id": descendant.id,
                    "represented_party_id": next_party.id,
                    "represented_party_perspective": "manager",
                },
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "OPERATION_NOT_ALLOWED"
