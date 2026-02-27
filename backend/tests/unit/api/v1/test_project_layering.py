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
            current_user=MagicMock(id="user-1", default_organization_id=None),
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
async def test_project_create_authz_should_infer_subject_scope_when_request_is_unscoped() -> None:
    """创建项目缺少主体字段时应回退到 subject manager scope。"""
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
        monkeypatch.setattr(
            module,
            "_build_subject_scope_hint",
            AsyncMock(
                return_value={
                    "manager_party_id": "subject-manager-party-1",
                    "manager_party_ids": ["subject-manager-party-1"],
                    "party_id": "subject-manager-party-1",
                }
            ),
            raising=False,
        )
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["manager_party_id"] == "subject-manager-party-1"
    assert result.resource_context["party_id"] == "subject-manager-party-1"
    assert result.resource_context["manager_party_ids"] == ["subject-manager-party-1"]


@pytest.mark.asyncio
async def test_project_create_authz_should_keep_unscoped_sentinel_when_subject_scope_is_empty() -> None:
    """创建项目在无任何主体上下文时应保持 fail-closed 哨兵。"""
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
        monkeypatch.setattr(
            module,
            "_build_subject_scope_hint",
            AsyncMock(return_value={}),
            raising=False,
        )
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["party_id"] == module._PROJECT_CREATE_UNSCOPED_PARTY_ID  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_project_create_authz_should_backfill_manager_party_id_from_mapped_organization_party() -> None:
    """创建项目应通过 organization->party 映射回填 manager_party_id。"""
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
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-org-1"),
            raising=False,
        )
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert project_in.manager_party_id == "party-org-1"
    assert result.resource_context["manager_party_id"] == "party-org-1"
    assert result.resource_context["party_id"] == "party-org-1"


@pytest.mark.asyncio
async def test_project_create_authz_should_not_copy_raw_organization_id_into_manager_party_id(
) -> None:
    """organization 映射缺失时不应把原始 organization_id 写入 manager_party_id。"""
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
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value=None),
            raising=False,
        )
        monkeypatch.setattr(
            module,
            "_build_subject_scope_hint",
            AsyncMock(return_value={}),
            raising=False,
        )
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(id="user-1"),
            db=MagicMock(),
        )

    assert project_in.manager_party_id is None
    assert result.resource_context["organization_id"] == "org-1"
    assert "manager_party_id" not in result.resource_context
    assert result.resource_context["party_id"] == "org-1"


@pytest.mark.asyncio
async def test_project_create_authz_should_use_default_org_scope_when_request_is_unscoped() -> None:
    """创建项目请求未携带 organization_id 时应使用用户默认组织鉴权。"""
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
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-org-default"),
            raising=False,
        )
        result = await module._require_project_create_authz(  # type: ignore[attr-defined]
            project_in=project_in,
            current_user=MagicMock(
                id="user-1",
                default_organization_id="org-default",
            ),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert project_in.manager_party_id == "party-org-default"
    assert result.resource_context["organization_id"] == "org-default"
    assert result.resource_context["manager_party_id"] == "party-org-default"
    assert result.resource_context["party_id"] == "party-org-default"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource"]["organization_id"] == "org-default"
    assert kwargs["resource"]["party_id"] == "party-org-default"


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
        resource_context={
            "manager_party_id": "manager-party-from-authz",
            "organization_id": "org-from-authz",
        },
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
    assert mock_service.create_project.await_args.kwargs["organization_id"] == "org-from-authz"


@pytest.mark.asyncio
async def test_create_project_should_use_request_organization_id_before_default_organization() -> None:
    """创建项目应优先使用请求 organization_id，再回退 default_organization_id。"""
    from src.api.v1.assets import project as module

    project_in = MagicMock(
        manager_party_id="manager-party-1",
        organization_id="org-request",
    )
    current_user = MagicMock(id="user-1", default_organization_id="org-default")

    mock_service = MagicMock()
    mock_service.create_project = AsyncMock(return_value=MagicMock(id="project-1"))
    mock_service.project_to_response = MagicMock(return_value={"id": "project-1"})

    authz_ctx = module.AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="project",
        resource_id=None,
        resource_context={},
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

    assert result["id"] == "project-1"
    assert mock_service.create_project.await_args.kwargs["organization_id"] == "org-request"


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
