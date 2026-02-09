"""
Unit tests for organization permission middleware.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import PermissionDeniedError
from src.middleware.organization_permission import require_organization_access


def test_require_organization_access_denies_without_permission():
    dependency = require_organization_access()

    current_user = MagicMock()
    current_user.id = "user-1"

    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )
    db = MagicMock()

    with (
        patch(
            "src.middleware.organization_permission.OrganizationPermissionService"
        ) as mock_service,
        patch(
            "src.middleware.organization_permission.SecurityEventLogger"
        ) as mock_logger,
    ):
        mock_service.return_value.check_organization_access = AsyncMock(
            return_value=False
        )
        mock_logger.return_value.log_permission_denied = AsyncMock()
        mock_logger.return_value.should_alert = AsyncMock(return_value=False)

        with pytest.raises(PermissionDeniedError) as exc_info:
            asyncio.run(
                dependency(
                    organization_id="org-2",
                    current_user=current_user,
                    db=db,
                    request=request,
                )
            )

    assert exc_info.value.status_code == 403


def test_require_organization_access_allows_with_permission():
    dependency = require_organization_access()

    current_user = MagicMock()
    current_user.id = "user-1"

    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )
    db = MagicMock()

    with (
        patch(
            "src.middleware.organization_permission.OrganizationPermissionService"
        ) as mock_service,
        patch(
            "src.middleware.organization_permission.SecurityEventLogger"
        ) as mock_logger,
    ):
        mock_service.return_value.check_organization_access = AsyncMock(
            return_value=True
        )

        result = asyncio.run(
            dependency(
                organization_id="org-1",
                current_user=current_user,
                db=db,
                request=request,
            )
        )

    assert result == "org-1"
    mock_logger.assert_not_called()
