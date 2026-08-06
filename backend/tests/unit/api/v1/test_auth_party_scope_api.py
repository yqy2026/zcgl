"""Read-only effective Party-scope diagnostics for self and administrators."""

from fastapi import status


def _add_diagnostic_fixture(db_session):
    from src.models.auth import User
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import UserPartyBinding

    admin = User(
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
    user = User(
        id="party-scope-diagnostic-user",
        username="party_scope_diagnostic_user",
        email="party.scope.diagnostic.user@example.com",
        phone="13900000051",
        full_name="Diagnostic scoped user",
        password_hash="hashed-password",
        account_type="human",
        is_active=False,
        is_locked=False,
    )
    party = Party(
        id="party-scope-diagnostic-party",
        party_type=PartyType.LEGAL_ENTITY,
        name="Diagnostic Party",
        code="LE-009401",
        status="active",
        review_status="approved",
    )
    binding = UserPartyBinding(
        user_id=user.id,
        party_id=party.id,
        relation_type="owner",
    )
    db_session.add_all([admin, user, party, binding])
    db_session.flush()
    return user, party


def test_self_party_scope_view_omits_node_refs(client, db_session) -> None:
    """A user's self diagnostic exposes the scope but never internal node refs."""
    user, party = _add_diagnostic_fixture(db_session)

    response = client.get("/api/v1/auth/users/party-scope-diagnostic-user/party-scope")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["source"] == "explicit"
    assert payload["owner_party_ids"] == [party.id]
    assert payload["issues"] == []

    self_response = client.get("/api/v1/auth/me/party-scope")
    assert self_response.status_code == status.HTTP_200_OK
    assert self_response.json()["user_id"] == "test_user_001"


def test_admin_party_scope_view_includes_issue_node_refs(client, db_session) -> None:
    """Administrators see structured issues with node references for diagnosis."""
    from src.models.auth import User
    from src.models.organization import Organization
    from src.models.party import Party, PartyType
    from src.models.user_party_binding import UserPartyBinding

    _add_diagnostic_fixture(db_session)
    organization = Organization(
        id="party-scope-diagnostic-org",
        name="Diagnostic Organization",
        code="DIAG-ORG",
        level=1,
        type="headquarters",
        status="active",
        path="/party-scope-diagnostic-org",
    )
    user = User(
        id="party-scope-diagnostic-invalid",
        username="party_scope_diagnostic_invalid",
        email="party.scope.diagnostic.invalid@example.com",
        phone="13900000052",
        full_name="Invalid binding user",
        password_hash="hashed-password",
        account_type="human",
        is_active=True,
        is_locked=False,
        organization_id=organization.id,
    )
    party = Party(
        id="party-scope-diagnostic-invalid-party",
        party_type=PartyType.LEGAL_ENTITY,
        name="Invalid Diagnostic Party",
        code="LE-009402",
        status="inactive",
        review_status="approved",
    )
    binding = UserPartyBinding(
        user_id=user.id,
        party_id=party.id,
        relation_type="owner",
    )
    db_session.add_all([organization, user, party])
    db_session.flush()
    db_session.add(binding)
    db_session.flush()

    response = client.get(
        f"/api/v1/auth/users/{user.id}/party-scope",
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["error_code"] == "PARTY_SCOPE_INVALID_BINDING"
    assert payload["issues"][0]["node_ref"] == binding.id
