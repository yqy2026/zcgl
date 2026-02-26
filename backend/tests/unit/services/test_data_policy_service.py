"""Unit tests for DataPolicyService."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import InvalidRequestError, ResourceNotFoundError
from src.models.abac import ABACRolePolicy
from src.services.authz.data_policy_service import DataPolicyService
from src.services.authz.events import AUTHZ_ROLE_POLICY_UPDATED

pytestmark = pytest.mark.asyncio


class _ScalarResult:
    def __init__(self, value: object | None):
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _RowsResult:
    def __init__(self, rows: list[tuple[object, ...]]):
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return list(self._rows)


class _ScalarsResult:
    def __init__(self, values: list[object]):
        self._values = values

    def scalars(self) -> _ScalarsResult:
        return self

    def all(self) -> list[object]:
        return list(self._values)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


async def test_list_templates_returns_name_and_description_only(mock_db) -> None:
    service = DataPolicyService(mock_db)

    templates = service.list_templates()

    assert "platform_admin" in templates
    assert set(templates["platform_admin"].keys()) == {"name", "description"}


async def test_get_role_policy_packages_returns_ordered_unique_packages(mock_db) -> None:
    service = DataPolicyService(mock_db)
    mock_db.execute.side_effect = [
        _ScalarResult("role-1"),
        _RowsResult(
            [
                ("audit_viewer",),
                ("asset_owner_operator",),
                ("asset_owner_operator",),
                ("unknown_policy",),
            ]
        ),
    ]

    packages = await service.get_role_policy_packages("role-1")

    assert packages == ["asset_owner_operator", "audit_viewer"]


async def test_get_role_policy_packages_raises_when_role_missing(mock_db) -> None:
    service = DataPolicyService(mock_db)
    mock_db.execute.side_effect = [_ScalarResult(None)]

    with pytest.raises(ResourceNotFoundError):
        await service.get_role_policy_packages("missing-role")


async def test_set_role_policy_packages_persists_and_publishes_event(mock_db) -> None:
    mock_event_bus = MagicMock()
    service = DataPolicyService(mock_db, event_bus=mock_event_bus)

    owner_policy = SimpleNamespace(id="policy-owner", name="asset_owner_operator")
    audit_policy = SimpleNamespace(id="policy-audit", name="audit_viewer")

    mock_db.execute.side_effect = [
        _ScalarResult("role-1"),
        _ScalarsResult([owner_policy, audit_policy]),
        _RowsResult([("policy-owner",), ("policy-audit",)]),
        _RowsResult([]),
    ]

    packages = await service.set_role_policy_packages(
        "role-1",
        policy_packages=[
            " asset_owner_operator ",
            "audit_viewer",
            "asset_owner_operator",
            "",
        ],
    )

    assert packages == ["asset_owner_operator", "audit_viewer"]
    assert mock_db.add.call_count == 2

    bindings = [call.args[0] for call in mock_db.add.call_args_list]
    assert all(isinstance(binding, ABACRolePolicy) for binding in bindings)
    assert {binding.role_id for binding in bindings} == {"role-1"}
    assert {binding.policy_id for binding in bindings} == {"policy-owner", "policy-audit"}
    assert all(binding.enabled is True for binding in bindings)
    mock_db.commit.assert_awaited_once()

    mock_event_bus.publish_invalidation.assert_called_once_with(
        event_type=AUTHZ_ROLE_POLICY_UPDATED,
        payload={
            "role_id": "role-1",
            "policy_packages": ["asset_owner_operator", "audit_viewer"],
        },
    )


async def test_set_role_policy_packages_rejects_unknown_package(mock_db) -> None:
    service = DataPolicyService(mock_db)
    mock_db.execute.side_effect = [_ScalarResult("role-1")]

    with pytest.raises(InvalidRequestError) as exc_info:
        await service.set_role_policy_packages(
            "role-1",
            policy_packages=["unknown_policy"],
        )

    assert exc_info.value.details["invalid_code"] == "unknown_policy"
    mock_db.commit.assert_not_awaited()


async def test_load_template_policies_raises_when_seed_data_missing(mock_db) -> None:
    service = DataPolicyService(mock_db)
    mock_db.execute.side_effect = [_ScalarsResult([])]

    with pytest.raises(InvalidRequestError) as exc_info:
        await service._load_template_policies(["platform_admin"])

    assert exc_info.value.details["missing_policies"] == ["platform_admin"]
