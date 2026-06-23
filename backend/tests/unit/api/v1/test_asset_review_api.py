"""资产审核 API 分层与契约测试。"""

from __future__ import annotations

import inspect
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def _asset_module():
    return import_module("src.api.v1.assets.assets")


def test_asset_review_routes_should_exist() -> None:
    router = _asset_module().router
    paths = {route.path for route in router.routes}  # type: ignore[attr-defined]
    required = {
        "/{asset_id}/submit-review",
        "/{asset_id}/approve-review",
        "/{asset_id}/reject-review",
        "/{asset_id}/reverse-review",
        "/{asset_id}/resubmit-review",
        "/{asset_id}/withdraw-review",
        "/{asset_id}/review-logs",
    }
    assert required.issubset(paths), f"缺少路径: {required - paths}"


def test_reject_and_reverse_review_should_require_reason_payload() -> None:
    mod = _asset_module()
    reject_endpoint = getattr(mod, "reject_asset_review", None)
    reverse_endpoint = getattr(mod, "reverse_asset_review", None)
    assert reject_endpoint is not None, "reject_asset_review 路由尚未实现"
    assert reverse_endpoint is not None, "reverse_asset_review 路由尚未实现"

    schema_module = import_module("src.schemas.asset")
    request_schema = getattr(schema_module, "AssetReviewRejectRequest", None)
    assert request_schema is not None, "AssetReviewRejectRequest 尚未实现"

    reject_payload = inspect.signature(reject_endpoint).parameters.get("payload")
    reverse_payload = inspect.signature(reverse_endpoint).parameters.get("payload")
    assert reject_payload is not None
    assert reverse_payload is not None
    assert reject_payload.default is inspect._empty
    assert reverse_payload.default is inspect._empty
    assert reject_payload.annotation is request_schema
    assert reverse_payload.annotation is request_schema


@pytest.mark.asyncio
async def test_get_asset_review_logs_should_delegate_to_service() -> None:
    mod = _asset_module()
    endpoint = getattr(mod, "get_asset_review_logs", None)
    assert endpoint is not None, "get_asset_review_logs 路由尚未实现"

    logs = [MagicMock(action="submit"), MagicMock(action="approve")]
    mock_service = MagicMock()
    mock_service.get_asset_review_logs = AsyncMock(return_value=logs)

    with patch(
        "src.api.v1.assets.assets.AsyncAssetService",
        return_value=mock_service,
    ):
        result = await endpoint(
            asset_id="asset-001",
            db=AsyncMock(),
            current_user=MagicMock(id="user-001"),
            _authz=None,
        )

    assert result == logs
    mock_service.get_asset_review_logs.assert_awaited_once_with(
        "asset-001",
        current_user_id="user-001",
    )
