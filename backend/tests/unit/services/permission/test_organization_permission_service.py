"""OrganizationPermissionService 静态分层/时间源约束测试。"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services import organization_permission_service
from src.services.organization_permission_service import OrganizationPermissionService


def test_organization_permission_service_module_avoids_datetime_utcnow() -> None:
    """服务模块不应直接调用 datetime.utcnow."""
    module_path = Path(organization_permission_service.__file__)
    content = module_path.read_text(encoding="utf-8")

    assert "datetime.utcnow(" not in content


@pytest.mark.asyncio
async def test_accessible_organizations_include_user_organization_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OrganizationPermissionService(MagicMock())
    service._get_user = AsyncMock(return_value=SimpleNamespace(organization_id="org-1"))
    service.rbac_service.is_admin = AsyncMock(return_value=False)
    service._has_global_permission = AsyncMock(return_value=False)
    service._get_user_roles = AsyncMock(return_value=[])
    service._get_resource_permissions = AsyncMock(return_value=[])
    monkeypatch.setattr(
        organization_permission_service.cache_manager,
        "get",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        organization_permission_service.cache_manager, "set", MagicMock()
    )

    result = await service.get_user_accessible_organizations("user-1")

    assert result == ["org-1"]
