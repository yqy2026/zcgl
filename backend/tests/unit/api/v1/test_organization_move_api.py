"""Public API contract for sensitive Organization hierarchy moves."""

from fastapi import status

from tests.fixtures import fake_bcrypt_hash


def _add_move_fixture(db_session):
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
    old_party = Party(
        id="organization-move-party-old",
        party_type=PartyType.LEGAL_ENTITY,
        name="Old scope party",
        code="LE-009101",
        status="active",
        review_status="approved",
    )
    new_party = Party(
        id="organization-move-party-new",
        party_type=PartyType.LEGAL_ENTITY,
        name="New scope party",
        code="LE-009102",
        status="active",
        review_status="approved",
    )
    old_root = Organization(
        id="organization-move-old-root",
        name="Old root",
        code="OM-OLD-ROOT",
        level=1,
        type="headquarters",
        status="active",
        path="/organization-move-old-root",
        represented_party_id=old_party.id,
        represented_party_perspective="owner",
    )
    new_root = Organization(
        id="organization-move-new-root",
        name="New root",
        code="OM-NEW-ROOT",
        level=1,
        type="headquarters",
        status="active",
        path="/organization-move-new-root",
        represented_party_id=new_party.id,
        represented_party_perspective="manager",
    )
    source = Organization(
        id="organization-move-source",
        name="Moving organization",
        code="OM-SOURCE",
        level=2,
        type="department",
        status="active",
        parent_id=old_root.id,
        path=f"/{old_root.id}/organization-move-source",
    )
    descendant = Organization(
        id="organization-move-descendant",
        name="Moving descendant",
        code="OM-DESCENDANT",
        level=3,
        type="department",
        status="active",
        parent_id=source.id,
        path=f"/{old_root.id}/{source.id}/organization-move-descendant",
    )
    user = User(
        id="organization-move-human",
        username="organization_move_human",
        email="organization.move.human@example.com",
        phone="13900000091",
        full_name="Affected user",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        organization_id=descendant.id,
        is_active=True,
        is_locked=False,
    )
    db_session.add_all(
        [
            actor,
            old_party,
            new_party,
            old_root,
            new_root,
            source,
            descendant,
            user,
        ]
    )
    db_session.flush()
    return old_root, new_root, source, descendant


def test_organization_move_requires_preview_then_commits_subtree_atomically(
    client, db_session
) -> None:
    """A hierarchy move is preview-bound and updates the whole subtree once."""
    from src.models.organization_move_commit import OrganizationMoveCommit

    old_root, new_root, source, descendant = _add_move_fixture(db_session)

    direct_update = client.put(
        f"/api/v1/organizations/{source.id}",
        json={"parent_id": new_root.id},
    )
    assert direct_update.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    }

    preview_response = client.post(
        f"/api/v1/organizations/{source.id}/move/preview",
        json={"target_parent_id": new_root.id},
    )

    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["before_scope"]["parent_id"] == old_root.id
    assert preview_payload["after_scope"]["parent_id"] == new_root.id
    assert (
        preview_payload["before_scope"]["effective_party_id"]
        == "organization-move-party-old"
    )
    assert (
        preview_payload["after_scope"]["effective_party_id"]
        == "organization-move-party-new"
    )
    assert preview_payload["impact"]["organization_count"] == 2
    assert preview_payload["impact"]["user_count"] == 1
    assert source.parent_id == old_root.id

    commit_request = {
        "preview_token": preview_payload["preview_token"],
        "reason": "Move the department under the new operating root.",
        "idempotency_key": "organization-move-1",
    }
    commit_response = client.post(
        f"/api/v1/organizations/{source.id}/move",
        json=commit_request,
    )

    assert commit_response.status_code == status.HTTP_200_OK
    commit_payload = commit_response.json()
    assert commit_payload["organization"]["parent_id"] == new_root.id
    assert (
        commit_payload["after_scope"]["effective_party_id"]
        == "organization-move-party-new"
    )
    assert commit_payload["idempotent"] is False
    db_session.refresh(source)
    db_session.refresh(descendant)
    assert source.parent_id == new_root.id
    assert source.path == f"/{new_root.id}/{source.id}"
    assert descendant.path == f"/{new_root.id}/{source.id}/{descendant.id}"
    assert db_session.query(OrganizationMoveCommit).count() == 1

    repeated_commit = client.post(
        f"/api/v1/organizations/{source.id}/move",
        json=commit_request,
    )
    assert repeated_commit.status_code == status.HTTP_200_OK
    assert repeated_commit.json()["idempotent"] is True
    assert db_session.query(OrganizationMoveCommit).count() == 1


def test_organization_move_rejects_target_state_drift(client, db_session) -> None:
    """A changed target hierarchy invalidates the preview without moving the node."""
    old_root, new_root, source, _ = _add_move_fixture(db_session)

    preview_response = client.post(
        f"/api/v1/organizations/{source.id}/move/preview",
        json={"target_parent_id": new_root.id},
    )
    assert preview_response.status_code == status.HTTP_200_OK

    new_root.status = "inactive"
    db_session.flush()

    commit_response = client.post(
        f"/api/v1/organizations/{source.id}/move",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Move after target state drift.",
            "idempotency_key": "organization-move-stale-1",
        },
    )

    assert commit_response.status_code == status.HTTP_409_CONFLICT
    assert commit_response.json()["error"]["code"] == "SCOPE_CHANGE_PREVIEW_STALE"
    db_session.refresh(source)
    assert source.parent_id == old_root.id


def test_organization_move_rejects_a_target_inside_its_subtree(
    client, db_session
) -> None:
    """The dedicated move flow rejects cycle proposals before issuing a preview."""
    old_root, _, source, descendant = _add_move_fixture(db_session)

    preview_response = client.post(
        f"/api/v1/organizations/{source.id}/move/preview",
        json={"target_parent_id": descendant.id},
    )

    assert preview_response.status_code == status.HTTP_400_BAD_REQUEST
    assert preview_response.json()["error"]["code"] == "OPERATION_NOT_ALLOWED"
    db_session.refresh(source)
    assert source.parent_id == old_root.id


def test_organization_move_can_make_a_node_a_root(client, db_session) -> None:
    """An explicit null target parent is a valid root move, not a no-op."""
    _, _, source, _ = _add_move_fixture(db_session)

    preview_response = client.post(
        f"/api/v1/organizations/{source.id}/move/preview",
        json={"target_parent_id": None},
    )
    assert preview_response.status_code == status.HTTP_200_OK
    preview_payload = preview_response.json()
    assert preview_payload["before_scope"]["parent_id"] == "organization-move-old-root"
    assert preview_payload["after_scope"]["parent_id"] is None

    commit_response = client.post(
        f"/api/v1/organizations/{source.id}/move",
        json={
            "preview_token": preview_payload["preview_token"],
            "reason": "Promote the department to an independent root.",
            "idempotency_key": "organization-move-root-1",
        },
    )

    assert commit_response.status_code == status.HTTP_200_OK
    db_session.refresh(source)
    assert source.parent_id is None
    assert source.level == 1
    assert source.path == f"/{source.id}"
