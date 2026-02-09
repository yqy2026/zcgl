"""OrganizationPermissionService 静态分层/时间源约束测试。"""

from pathlib import Path

from src.services import organization_permission_service


def test_organization_permission_service_module_avoids_datetime_utcnow() -> None:
    """服务模块不应直接调用 datetime.utcnow."""
    module_path = Path(organization_permission_service.__file__)
    content = module_path.read_text(encoding="utf-8")

    assert "datetime.utcnow(" not in content
