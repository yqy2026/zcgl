from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.user_party_binding import RelationType
from src.services.authz.context_builder import AuthzContextBuilder

pytestmark = pytest.mark.asyncio


class _PartyCrudStub:
    def __init__(self) -> None:
        self.get_user_bindings = AsyncMock(return_value=[])
        self.get_descendants = AsyncMock(return_value=[])
        self.resolve_organization_party_id = AsyncMock(return_value=None)


class TestAuthzContextBuilder:
    async def test_should_build_context_from_bindings(self) -> None:
        db = MagicMock()
        party_crud_stub = _PartyCrudStub()
        party_crud_stub.get_user_bindings.return_value = [
            SimpleNamespace(party_id="owner-1", relation_type=RelationType.OWNER),
            SimpleNamespace(party_id="manager-1", relation_type=RelationType.MANAGER),
            SimpleNamespace(
                party_id="hq-1",
                relation_type=RelationType.HEADQUARTERS,
            ),
        ]
        party_crud_stub.get_descendants.return_value = ["hq-1", "child-1"]

        builder = AuthzContextBuilder(party_data_access=party_crud_stub)
        context = await builder.build_subject_context(
            db,
            user_id="user-1",
            role_ids=["role-2", "role-1"],
        )

        assert context.user_id == "user-1"
        assert context.owner_party_ids == ["owner-1"]
        assert context.manager_party_ids == ["child-1", "hq-1", "manager-1"]
        assert context.headquarters_party_ids == ["hq-1"]
        assert context.role_ids == ["role-1", "role-2"]

    async def test_should_fallback_to_mapped_party_scope_when_no_bindings(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "org-legacy"
        db.execute = AsyncMock(return_value=execute_result)

        party_crud_stub = _PartyCrudStub()
        party_crud_stub.resolve_organization_party_id.return_value = "party-legacy"
        builder = AuthzContextBuilder(party_data_access=party_crud_stub)
        context = await builder.build_subject_context(
            db,
            user_id="user-1",
            role_ids=[],
        )

        assert context.owner_party_ids == ["party-legacy"]
        assert context.manager_party_ids == ["party-legacy"]
        assert context.headquarters_party_ids == []
        party_crud_stub.resolve_organization_party_id.assert_awaited_once_with(
            db,
            organization_id="org-legacy",
        )

    async def test_should_fail_closed_when_legacy_org_not_mapped_to_party(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "org-legacy"
        db.execute = AsyncMock(return_value=execute_result)

        party_crud_stub = _PartyCrudStub()
        party_crud_stub.resolve_organization_party_id.return_value = None
        builder = AuthzContextBuilder(party_data_access=party_crud_stub)
        context = await builder.build_subject_context(
            db,
            user_id="user-1",
            role_ids=[],
        )

        assert context.owner_party_ids == []
        assert context.manager_party_ids == []
        assert context.headquarters_party_ids == []

    async def test_should_keep_fail_closed_when_no_bindings_and_no_legacy_org(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=execute_result)

        party_crud_stub = _PartyCrudStub()
        builder = AuthzContextBuilder(party_data_access=party_crud_stub)
        context = await builder.build_subject_context(
            db,
            user_id="user-1",
            role_ids=[],
        )

        assert context.owner_party_ids == []
        assert context.manager_party_ids == []
        assert context.headquarters_party_ids == []
