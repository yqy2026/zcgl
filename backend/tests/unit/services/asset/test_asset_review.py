"""资产审核流单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm.exc import StaleDataError

from src.core.exception_handler import OperationNotAllowedError, ResourceConflictError
from src.models.asset import Asset, AssetReviewStatus
from src.models.asset_review_log import AssetReviewLog
from src.models.auth import User
from src.schemas.asset import AssetUpdate
from src.services.asset.asset_service import AssetService

pytestmark = pytest.mark.asyncio


def _build_asset(*, review_status: str) -> Asset:
    asset = Asset(
        owner_party_id="owner-001",
        manager_party_id="manager-001",
        asset_name="测试资产",
        address="测试市测试路 123 号",
        ownership_status="已确权",
        property_nature="商业",
        usage_status="空置",
    )
    asset.id = "asset-001"
    asset.review_status = review_status
    asset.review_by = None
    asset.reviewed_at = None
    asset.review_reason = None
    return asset


def _extract_review_logs(mock_db: MagicMock) -> list[AssetReviewLog]:
    return [
        call.args[0]
        for call in mock_db.add.call_args_list
        if isinstance(call.args[0], AssetReviewLog)
    ]


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.in_transaction.return_value = True
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def service(mock_db: MagicMock) -> AssetService:
    return AssetService(mock_db)


@pytest.fixture
def mock_user() -> User:
    user = User()
    user.id = "user-001"
    user.username = "tester"
    return user


async def test_submit_asset_review_should_transition_to_pending_and_write_log(
    service: AssetService,
    mock_db: MagicMock,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.DRAFT.value)

    with patch.object(service, "get_asset", new=AsyncMock(return_value=asset)):
        updated = await service.submit_asset_review(asset.id, operator="alice")

    assert updated is asset
    assert asset.review_status == AssetReviewStatus.PENDING.value
    assert asset.review_by is None
    assert asset.reviewed_at is None
    assert asset.review_reason is None
    mock_db.flush.assert_awaited_once()

    logs = _extract_review_logs(mock_db)
    assert len(logs) == 1
    assert logs[0].action == "submit"
    assert logs[0].from_status == AssetReviewStatus.DRAFT.value
    assert logs[0].to_status == AssetReviewStatus.PENDING.value
    assert logs[0].operator == "alice"
    assert logs[0].reason is None


async def test_reverse_asset_review_should_record_context_and_reason(
    service: AssetService,
    mock_db: MagicMock,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.APPROVED.value)

    with (
        patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        patch.object(
            service,
            "_count_active_contracts_for_asset",
            new=AsyncMock(return_value=2),
        ),
    ):
        updated = await service.reverse_asset_review(
            asset.id,
            reviewer="reviewer-001",
            reason="审核后发现主数据有误",
        )

    assert updated is asset
    assert asset.review_status == AssetReviewStatus.REVERSED.value
    assert asset.review_by == "reviewer-001"
    assert asset.reviewed_at is not None
    assert asset.review_reason == "审核后发现主数据有误"
    mock_db.flush.assert_awaited_once()

    logs = _extract_review_logs(mock_db)
    assert len(logs) == 1
    assert logs[0].action == "reverse"
    assert logs[0].from_status == AssetReviewStatus.APPROVED.value
    assert logs[0].to_status == AssetReviewStatus.REVERSED.value
    assert logs[0].operator == "reviewer-001"
    assert logs[0].reason == "审核后发现主数据有误"
    assert logs[0].context == {"active_contract_count": 2}


async def test_update_asset_should_block_when_review_status_is_approved(
    service: AssetService,
    mock_user: User,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.APPROVED.value)

    with (
        patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        patch(
            "src.services.asset.asset_service.get_enum_validation_service_async",
            side_effect=AssertionError("审核守卫应在枚举校验前触发"),
        ),
    ):
        with pytest.raises(OperationNotAllowedError, match="不允许编辑业务字段"):
            await service.update_asset(
                asset.id,
                AssetUpdate(asset_name="新的资产名称"),
                current_user=mock_user,
            )


async def test_delete_asset_should_block_when_review_status_is_pending(
    service: AssetService,
    mock_user: User,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.PENDING.value)

    with (
        patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        patch.object(
            service,
            "_ensure_asset_not_linked",
            new=AsyncMock(side_effect=AssertionError("删除守卫应先于关联校验触发")),
        ),
    ):
        with pytest.raises(OperationNotAllowedError, match="不允许删除"):
            await service.delete_asset(asset.id, current_user=mock_user)


async def test_review_logs_should_be_listed_from_newest_to_oldest(
    service: AssetService,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.REVERSED.value)
    expected_logs = [
        AssetReviewLog(action="reverse", from_status="approved", to_status="reversed"),
        AssetReviewLog(action="approve", from_status="pending", to_status="approved"),
    ]

    with (
        patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        patch.object(
            service,
            "_list_asset_review_logs",
            new=AsyncMock(return_value=expected_logs),
        ),
    ):
        logs = await service.get_asset_review_logs("asset-001")

    assert logs == expected_logs
    assert [log.action for log in logs] == ["reverse", "approve"]


async def test_submit_asset_review_should_translate_stale_data_error_to_conflict(
    service: AssetService,
    mock_db: MagicMock,
) -> None:
    asset = _build_asset(review_status=AssetReviewStatus.DRAFT.value)
    mock_db.flush.side_effect = StaleDataError()

    with patch.object(service, "get_asset", new=AsyncMock(return_value=asset)):
        with pytest.raises(ResourceConflictError, match="刷新后重试"):
            await service.submit_asset_review(asset.id, operator="alice")

    mock_db.rollback.assert_awaited_once()
