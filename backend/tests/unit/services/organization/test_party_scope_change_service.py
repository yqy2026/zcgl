from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import OrganizationPartyScopePreviewStaleError
from src.schemas.organization import (
    OrganizationPartyScopeCommitRequest,
    OrganizationPartyScopeImpact,
    OrganizationPartyScopeProposal,
    OrganizationPartyScopeState,
)
from src.services.organization.party_scope_change_service import (
    OrganizationPartyScopePreviewStore,
    OrganizationPartyScopeService,
)
from tests.fixtures import fake_access_token, fake_bcrypt_hash
from tests.shared.conftest_utils import AsyncSessionAdapter


class _PreviewStore:
    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        self.payload = payload
        return (
            "opaque-preview-token",
            datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10),
        )


class _CommitPreviewStore(_PreviewStore):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__()
        self.commit_payload = payload
        self.consume_calls = 0

    def consume(self, raw_token: str) -> dict[str, object] | None:
        self.consume_calls += 1
        return self.commit_payload


class _CommitReceiptCRUD:
    def __init__(self) -> None:
        self.existing = None
        self.created = None

    async def get_by_idempotency_async(self, *args, **kwargs):
        return self.existing

    async def create_async(self, *args, **kwargs):
        self.created = SimpleNamespace(result_data=kwargs["result_data"])
        return self.created


def test_preview_store_consumes_token_once() -> None:
    store = OrganizationPartyScopePreviewStore(
        clock=lambda: datetime(2026, 8, 4, 12, 0, 0)
    )
    token, _ = store.issue({"actor_id": "user-1", "organization_id": "org-1"})

    assert store.consume(token) == {
        "actor_id": "user-1",
        "organization_id": "org-1",
        "expires_at": "2026-08-04T12:10:00",
    }
    assert store.consume(token) is None


@pytest.mark.asyncio
async def test_commit_applies_scope_records_reason_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.models.organization import Organization
    from src.services.organization import party_scope_change_service as module

    committed_at = datetime(2026, 8, 4, 12, 0, 0)
    request = OrganizationPartyScopeCommitRequest(
        preview_token=fake_access_token(),
        reason="组织权属调整",
        idempotency_key="request-1",
    )
    before_scope = OrganizationPartyScopeState()
    after_scope = OrganizationPartyScopeState(
        represented_party_id="party-1",
        represented_party_perspective="owner",
        effective_party_id="party-1",
        effective_party_perspective="owner",
        source_organization_id="org-1",
    )
    impact = OrganizationPartyScopeImpact(
        organization_count=1,
        organization_scope_change_count=1,
        user_count=1,
        user_scope_change_count=1,
    )
    organization = Organization(
        id="org-1",
        name="总部",
        code="ORG-1",
        level=1,
        sort_order=0,
        type="headquarter",
        status="active",
        path="/org-1",
        is_deleted=False,
        created_at=committed_at,
        updated_at=committed_at,
    )
    analysis = SimpleNamespace(
        before_scope=before_scope,
        after_scope=after_scope,
        impact=impact,
        state_fingerprint="f" * 64,
    )
    store = _CommitPreviewStore(
        {
            "actor_id": "actor-1",
            "organization_id": "org-1",
            "proposal": {
                "represented_party_id": "party-1",
                "represented_party_perspective": "owner",
            },
            "state_fingerprint": "f" * 64,
            "expires_at": "2026-08-04T12:10:00",
        }
    )
    receipt_crud = _CommitReceiptCRUD()
    service = OrganizationPartyScopeService(
        preview_store=store,
        commit_crud=receipt_crud,
        clock=lambda: committed_at,
    )
    service._build_preview_analysis = AsyncMock(return_value=analysis)  # type: ignore[method-assign]
    history_crud = MagicMock()
    history_crud.create_async = AsyncMock()
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        module.organization_crud,
        "get_for_update_async",
        AsyncMock(return_value=organization),
    )
    monkeypatch.setattr(module, "OrganizationHistoryCRUD", lambda: history_crud)

    result = await service.commit(
        db,
        organization_id="org-1",
        request=request,
        actor_id="actor-1",
    )

    assert result.organization.represented_party_id == "party-1"
    assert result.idempotent is False
    assert organization.represented_party_id == "party-1"
    assert organization.represented_party_perspective == "owner"
    assert store.consume_calls == 1
    history_crud.create_async.assert_awaited_once()
    assert (
        history_crud.create_async.await_args.kwargs["change_reason"] == request.reason
    )
    db.commit.assert_awaited_once()

    receipt_crud.existing = receipt_crud.created
    repeated = await service.commit(
        db,
        organization_id="org-1",
        request=request,
        actor_id="actor-1",
    )

    assert repeated.idempotent is True
    assert store.consume_calls == 1


@pytest.mark.asyncio
async def test_commit_rejects_preview_bound_to_a_different_actor() -> None:
    request = OrganizationPartyScopeCommitRequest(
        preview_token=fake_access_token(),
        reason="组织权属调整",
        idempotency_key="request-actor-mismatch",
    )
    store = _CommitPreviewStore(
        {
            "actor_id": "actor-1",
            "organization_id": "org-1",
            "proposal": {
                "represented_party_id": None,
                "represented_party_perspective": None,
            },
            "state_fingerprint": "f" * 64,
            "expires_at": "2026-08-04T12:10:00",
        }
    )
    service = OrganizationPartyScopeService(
        preview_store=store,
        commit_crud=_CommitReceiptCRUD(),
    )

    with pytest.raises(OrganizationPartyScopePreviewStaleError) as exc_info:
        await service.commit(
            MagicMock(),
            organization_id="org-1",
            request=request,
            actor_id="actor-2",
        )

    assert exc_info.value.details["reason"] == "actor_mismatch"
    assert store.consume_calls == 1


@pytest.mark.asyncio
async def test_preview_returns_opaque_token_without_writing_database() -> None:
    store = _PreviewStore()
    service = OrganizationPartyScopeService(preview_store=store)
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    proposal = OrganizationPartyScopeProposal(
        represented_party_id="party-1",
        represented_party_perspective="owner",
    )
    service._build_preview_analysis = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(
            before_scope=OrganizationPartyScopeState(),
            after_scope=OrganizationPartyScopeState(
                represented_party_id="party-1",
                represented_party_perspective="owner",
                effective_party_id="party-1",
                effective_party_perspective="owner",
                source_organization_id="org-1",
            ),
            impact=OrganizationPartyScopeImpact(
                organization_count=2,
                organization_scope_change_count=2,
                user_count=3,
                user_scope_change_count=3,
            ),
            state_fingerprint="f" * 64,
        )
    )

    result = await service.preview(
        db,
        organization_id="org-1",
        proposal=proposal,
        actor_id="user-1",
    )

    assert result.preview_token == "opaque-preview-token"
    assert result.after_scope.effective_party_id == "party-1"
    assert store.payload == {
        "actor_id": "user-1",
        "organization_id": "org-1",
        "proposal": {
            "represented_party_id": "party-1",
            "represented_party_perspective": "owner",
        },
        "state_fingerprint": "f" * 64,
    }
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_preview_counts_inheriting_users_but_not_explicitly_bound_users(
    db_session,
) -> None:
    from src.models.auth import User
    from src.models.organization import Organization
    from src.models.party import Party, PartyReviewStatus, PartyType
    from src.models.user_party_binding import UserPartyBinding

    inherited_party = Party(
        id="party-inherited",
        party_type=PartyType.LEGAL_ENTITY,
        name="Inherited Party",
        code="LE-000101",
        status="active",
        review_status=PartyReviewStatus.APPROVED,
    )
    proposed_party = Party(
        id="party-proposed",
        party_type=PartyType.LEGAL_ENTITY,
        name="Proposed Party",
        code="LE-000102",
        status="active",
        review_status=PartyReviewStatus.APPROVED,
    )
    explicit_party = Party(
        id="party-explicit",
        party_type=PartyType.LEGAL_ENTITY,
        name="Explicit Party",
        code="LE-000103",
        status="active",
        review_status=PartyReviewStatus.APPROVED,
    )
    root = Organization(
        id="org-root",
        name="Root",
        code="ORG-ROOT",
        level=1,
        type="company",
        status="active",
        represented_party_id=inherited_party.id,
        represented_party_perspective="owner",
    )
    child = Organization(
        id="org-child",
        name="Child",
        code="ORG-CHILD",
        level=2,
        parent_id=root.id,
        type="department",
        status="active",
    )
    inheriting_user = User(
        id="user-inheriting",
        username="inheriting-user",
        email="inheriting@example.com",
        phone="13800000101",
        full_name="Inheriting User",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        organization_id=child.id,
        is_active=True,
    )
    explicit_user = User(
        id="user-explicit",
        username="explicit-user",
        email="explicit@example.com",
        phone="13800000102",
        full_name="Explicit User",
        password_hash=fake_bcrypt_hash(),
        account_type="human",
        organization_id=child.id,
        is_active=True,
    )
    explicit_binding = UserPartyBinding(
        user_id=explicit_user.id,
        party_id=explicit_party.id,
        relation_type="owner",
    )
    db_session.add_all(
        [
            inherited_party,
            proposed_party,
            explicit_party,
            root,
            child,
            inheriting_user,
            explicit_user,
        ]
    )
    db_session.flush()
    db_session.add(explicit_binding)
    db_session.flush()

    result = await OrganizationPartyScopeService().preview(
        AsyncSessionAdapter(db_session),
        organization_id=root.id,
        proposal=OrganizationPartyScopeProposal(
            represented_party_id=proposed_party.id,
            represented_party_perspective="owner",
        ),
        actor_id="admin-1",
    )

    assert result.before_scope.effective_party_id == inherited_party.id
    assert result.after_scope.effective_party_id == proposed_party.id
    assert result.impact.organization_count == 2
    assert result.impact.organization_scope_change_count == 2
    assert result.impact.user_count == 2
    assert result.impact.user_scope_change_count == 1
