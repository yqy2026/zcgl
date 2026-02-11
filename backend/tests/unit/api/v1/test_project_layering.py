"""分层约束测试：project 路由应委托服务层。"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_project_api_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 project_crud。"""
    from src.api.v1.assets import project as project_module

    module_source = Path(project_module.__file__).read_text(encoding="utf-8")
    assert "project_crud." not in module_source


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
    mock_service.get_project_statistics.assert_awaited_once()


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
