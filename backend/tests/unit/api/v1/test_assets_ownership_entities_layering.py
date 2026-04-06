"""分层约束测试：assets ownership-entities 端点应委托服务层。"""

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_assets_module_should_not_query_ownership_via_db_execute() -> None:
    """assets 路由模块不应在 ownership-entities 端点直接执行 SQL。"""
    from src.api.v1.assets import assets as assets_module

    module_source = Path(assets_module.__file__).read_text(encoding="utf-8")
    assert "select(Ownership.name)" not in module_source
    assert "await db.execute(stmt)" not in module_source


@pytest.mark.asyncio
async def test_get_ownership_entities_should_delegate_asset_service() -> None:
    """ownership-entities 接口应委托 AsyncAssetService.get_ownership_entity_names。"""
    from src.api.v1.assets import assets as module
    from src.api.v1.assets.assets import get_ownership_entities
    from src.middleware.auth import DataScopeContext

    mock_service = MagicMock()
    mock_service.get_ownership_entity_names = AsyncMock(return_value=["A公司", "B公司"])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            module, "AsyncAssetService", MagicMock(return_value=mock_service)
        )
        result = await get_ownership_entities(
            db=MagicMock(),
            current_user=MagicMock(),
            _scope_ctx=DataScopeContext(
                scope_mode="owner",
                allowed_binding_types=["owner"],
                owner_party_ids=["owner-1"],
                manager_party_ids=[],
                effective_party_ids=["owner-1"],
                source="header",
            ),
        )

    assert result == ["A公司", "B公司"]
    mock_service.get_ownership_entity_names.assert_awaited_once_with(
        current_user_id=ANY,
        party_filter=ANY,
    )
