"""Focused tests for explicit Organization-to-Party resource scoping."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.resource_context import (
    load_organization_scope_context,
    load_user_scope_context,
    resolve_organization_party_id,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.asyncio


def _mapping_result(row: dict[str, str | None] | None) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    return result


async def test_resolve_organization_party_reads_only_explicit_link() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=_mapping_result({"party_id": "party-legal-1"}))

    result = await resolve_organization_party_id(
        db=db,
        organization_id="org-1",
    )

    assert result == "party-legal-1"
    statement = str(db.execute.await_args.args[0])
    assert "organizations.represented_party_id" in statement
    assert "parties" not in statement


async def test_organization_scope_fails_closed_without_represented_party() -> None:
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_mapping_result({"organization_id": "org-1", "party_id": None})
    )

    result = await load_organization_scope_context(db=db, organization_id="org-1")

    sentinel = "__unscoped__:organization:org-1"
    assert result == {
        "organization_id": "org-1",
        "party_id": sentinel,
        "owner_party_id": sentinel,
        "manager_party_id": sentinel,
    }


async def test_user_scope_uses_organization_id_and_explicit_represented_party() -> None:
    db = MagicMock()
    with patch(
        "src.services.party_scope_resolver.party_scope_resolver.resolve",
        new=AsyncMock(
            return_value=EffectivePartyScope(
                user_id="user-1",
                source="organization",
                scope_mode="owner",
                owner_party_ids=["party-legal-1"],
                organization_id="org-1",
                source_organization_id="org-1",
            )
        ),
    ) as resolve_scope:
        result = await load_user_scope_context(db=db, user_id="user-1")

    assert result["organization_id"] == "org-1"
    assert result["party_id"] == "party-legal-1"
    assert result["owner_party_id"] == "party-legal-1"
    resolve_scope.assert_awaited_once_with(db, user_id="user-1")
