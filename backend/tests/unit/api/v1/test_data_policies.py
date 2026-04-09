"""Unit tests for data policy package API handlers."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BaseBusinessError, ResourceNotFoundError

pytestmark = pytest.mark.api


def test_data_policies_module_should_use_require_any_role() -> None:
    from src.api.v1.auth import data_policies as data_policies_module

    module_source = Path(data_policies_module.__file__).read_text(encoding="utf-8")
    assert "require_any_role" in module_source
    assert "require_admin" not in module_source


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_get_role_data_policies_success(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    mock_service = MagicMock()
    mock_service.get_role_policy_packages = AsyncMock(return_value=["audit_viewer"])
    mock_service_cls.return_value = mock_service

    result = asyncio.run(
        data_policies_module.get_role_data_policies(
            role_id="role-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )
    )

    assert result == {"role_id": "role-1", "policy_packages": ["audit_viewer"]}
    mock_service.get_role_policy_packages.assert_awaited_once_with("role-1")


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_get_role_data_policies_wraps_unexpected_errors(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    mock_service = MagicMock()
    mock_service.get_role_policy_packages = AsyncMock(side_effect=RuntimeError("boom"))
    mock_service_cls.return_value = mock_service

    with pytest.raises(BaseBusinessError) as exc_info:
        asyncio.run(
            data_policies_module.get_role_data_policies(
                role_id="role-1",
                db=MagicMock(),
                current_user=MagicMock(),
            )
        )

    assert getattr(exc_info.value, "code", None) == "INTERNAL_SERVER_ERROR"
    assert getattr(exc_info.value, "status_code", None) == 500
    assert (
        getattr(exc_info.value, "message", None)
        == "Failed to fetch role data policy packages."
    )


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_put_role_data_policies_success(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    mock_service = MagicMock()
    mock_service.set_role_policy_packages = AsyncMock(
        return_value=["asset_owner_operator", "audit_viewer"]
    )
    mock_service_cls.return_value = mock_service

    payload = data_policies_module.RolePolicyUpdateRequest(
        policy_packages=["asset_owner_operator", "audit_viewer"]
    )
    result = asyncio.run(
        data_policies_module.put_role_data_policies(
            role_id="role-1",
            payload=payload,
            db=MagicMock(),
            current_user=MagicMock(),
        )
    )

    assert result == {
        "role_id": "role-1",
        "policy_packages": ["asset_owner_operator", "audit_viewer"],
    }
    mock_service.set_role_policy_packages.assert_awaited_once_with(
        "role-1", policy_packages=["asset_owner_operator", "audit_viewer"]
    )


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_put_role_data_policies_preserves_business_error(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    mock_service = MagicMock()
    mock_service.set_role_policy_packages = AsyncMock(
        side_effect=ResourceNotFoundError("角色", "missing-role")
    )
    mock_service_cls.return_value = mock_service

    with pytest.raises(ResourceNotFoundError):
        asyncio.run(
            data_policies_module.put_role_data_policies(
                role_id="missing-role",
                payload=data_policies_module.RolePolicyUpdateRequest(
                    policy_packages=["audit_viewer"]
                ),
                db=MagicMock(),
                current_user=MagicMock(),
            )
        )


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_put_role_data_policies_wraps_unexpected_errors(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    mock_service = MagicMock()
    mock_service.set_role_policy_packages = AsyncMock(
        side_effect=RuntimeError("invalid package")
    )
    mock_service_cls.return_value = mock_service

    with pytest.raises(BaseBusinessError) as exc_info:
        asyncio.run(
            data_policies_module.put_role_data_policies(
                role_id="role-1",
                payload=data_policies_module.RolePolicyUpdateRequest(
                    policy_packages=["audit_viewer"]
                ),
                db=MagicMock(),
                current_user=MagicMock(),
            )
        )

    assert getattr(exc_info.value, "code", None) == "INTERNAL_SERVER_ERROR"
    assert getattr(exc_info.value, "status_code", None) == 500
    assert (
        getattr(exc_info.value, "message", None)
        == "Failed to update role data policy packages."
    )


@patch("src.api.v1.auth.data_policies.DataPolicyService")
def test_get_data_policy_templates_success(mock_service_cls):
    from src.api.v1.auth import data_policies as data_policies_module

    templates = {
        "audit_viewer": {
            "name": "审计只读",
            "description": "审计视角访问",
        }
    }

    mock_service = MagicMock()
    mock_service.list_templates.return_value = templates
    mock_service_cls.return_value = mock_service

    result = asyncio.run(
        data_policies_module.get_data_policy_templates(
            db=MagicMock(),
            current_user=MagicMock(),
        )
    )

    assert result == templates
    mock_service.list_templates.assert_called_once_with()
