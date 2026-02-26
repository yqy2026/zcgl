"""分层约束测试：project 路由应委托服务层。"""

import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import project as project_module

    return Path(project_module.__file__).read_text(encoding="utf-8")


def test_project_api_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 project_crud。"""
    module_source = _read_module_source()
    assert "project_crud." not in module_source


def test_project_read_endpoints_should_use_require_authz() -> None:
    """project 读端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def create_project[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_project_create_authz\)",
        r"async def list_projects[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"project\"",
        r"async def search_projects[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"project\"",
        r"async def get_project_options[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"project\"",
        r"async def get_project_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"project\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_project_create_authz_should_include_manager_scope_context() -> None:
    """创建项目鉴权应携带 manager 主体上下文。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(
        manager_party_id="manager-party-1",
        organization_id="org-1",
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "project"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_project_create_authz_should_normalize_party_fields_on_input_model() -> None:
    """创建项目鉴权应将 manager/org 字段归一化回写到入参。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(
        manager_party_id=" manager-party-1 ",
        organization_id=" org-1 ",
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert project_in.manager_party_id == "manager-party-1"
    assert project_in.organization_id == "org-1"


@pytest.mark.asyncio
async def test_project_create_authz_should_fallback_to_unscoped_party_context() -> None:
    """创建项目缺少主体字段时应写入 unscoped 哨兵，避免空上下文放行。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(
        manager_party_id=None,
        organization_id=None,
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["party_id"] == module._PROJECT_CREATE_UNSCOPED_PARTY_ID  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_project_create_authz_should_backfill_manager_party_id_from_organization() -> None:
    """创建项目使用 organization fallback 时应回填 manager_party_id 到入参对象。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(
        manager_party_id=None,
        organization_id="org-1",
    )

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            reason_code="allow",
        )
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert project_in.manager_party_id == "org-1"


@pytest.mark.asyncio
async def test_create_project_should_backfill_manager_party_from_authz_context() -> None:
    """创建项目端点应基于鉴权上下文兜底回填 manager_party_id。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(manager_party_id=None, organization_id=None)
    current_user = MagicMock(id="user-1", default_organization_id="org-1")

    mock_service = MagicMock()
    mock_service.create_project = AsyncMock(return_value=MagicMock(id="project-1"))
    mock_service.project_to_response = MagicMock(return_value={"id": "project-1"})

    authz_ctx = module.AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="project",
        resource_id=None,
        resource_context={"manager_party_id": "manager-party-from-authz"},
        allowed=True,
        reason_code="allow",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "project_service", mock_service)
        result = await module.create_project(  # type: ignore[attr-defined]
            project_in=project_in,
            db=MagicMock(),
            current_user=current_user,
            _authz_ctx=authz_ctx,
        )

    assert project_in.manager_party_id == "manager-party-from-authz"
    assert result["id"] == "project-1"
    assert mock_service.create_project.await_args.kwargs["obj_in"] is project_in


@pytest.mark.asyncio
async def test_get_project_statistics_should_delegate_project_service() -> None:
    """项目统计接口应委托 project_service.get_project_statistics。"""
    from src.api.v1.assets.project import get_project_statistics

    mock_service = MagicMock()
    mock_service.get_project_statistics = AsyncMock(return_value={"total_projects": 8})

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.api.v1.assets.project.project_service", mock_service)
        result = await get_project_statistics(
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result["total_projects"] == 8
    mock_service.get_project_statistics.assert_awaited_once_with(
        db=ANY,
        current_user_id=ANY,
    )


@pytest.mark.asyncio
async def test_get_project_should_delegate_project_service_lookup() -> None:
    """项目详情接口应委托 project_service.get_project_by_id。"""
    from src.api.v1.assets.project import get_project
    from src.models.project import Project

    project = Project()
    project.id = "project-1"
    project.name = "P1"
    project.code = "PJ2602001"
    project.project_status = "规划中"
    project.is_active = True
    project.data_status = "正常"
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)

    mock_service = MagicMock()
    mock_service.get_project_by_id = AsyncMock(return_value=project)
    mock_service.project_to_response = MagicMock(side_effect=lambda value: value)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.api.v1.assets.project.project_service", mock_service)
        result = await get_project(
            project_id="project-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result.id == "project-1"
    mock_service.get_project_by_id.assert_awaited_once_with(
        db=ANY,
        project_id="project-1",
        current_user_id=ANY,
    )
