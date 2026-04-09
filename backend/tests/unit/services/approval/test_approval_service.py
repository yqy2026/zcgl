"""审批服务第一阶段单元测试。"""

from __future__ import annotations

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.asset import AssetReviewStatus

pytestmark = pytest.mark.asyncio


def _service_module():
    return import_module("src.services.approval.service")


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
def mock_asset_service() -> MagicMock:
    service = MagicMock()
    service.get_asset = AsyncMock(
        return_value=MagicMock(id="asset-001", review_status=AssetReviewStatus.DRAFT.value)
    )
    service.submit_asset_review = AsyncMock()
    service.approve_asset_review = AsyncMock()
    service.reject_asset_review = AsyncMock()
    service.withdraw_asset_review = AsyncMock()
    return service


@pytest.fixture
def mock_notification_service() -> MagicMock:
    service = MagicMock()
    service.create_approval_pending_notification = AsyncMock()
    service.mark_approval_notifications_read = AsyncMock()
    return service


def _build_service(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
):
    module = _service_module()
    service_cls = getattr(module, "ApprovalService", None)
    assert service_cls is not None, "ApprovalService 尚未实现"
    return service_cls(
        mock_db,
        asset_service=mock_asset_service,
        notification_service=mock_notification_service,
    )


def _added_instances(mock_db: MagicMock) -> list[object]:
    return [call.args[0] for call in mock_db.add.call_args_list]


async def test_start_process_should_create_pending_instance_task_and_notification(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    service = _build_service(
        mock_db,
        mock_asset_service,
        mock_notification_service,
    )

    with (
        patch.object(service, "_generate_approval_no", return_value="APR-20260402-0001"),
        patch(
            "src.services.approval.service.approval_crud.find_active_instance",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await service.start_process(
            business_type="asset",
            business_id="asset-001",
            assignee_user_id="reviewer-001",
            starter_id="starter-001",
            comment="发起资产审批",
        )

    assert result.business_id == "asset-001"
    assert result.business_type == "asset"
    assert result.status == "pending"
    assert result.assignee_user_id == "reviewer-001"
    assert result.starter_id == "starter-001"
    assert result.current_task_id is not None

    created = _added_instances(mock_db)
    created_names = {instance.__class__.__name__ for instance in created}
    assert "ApprovalInstance" in created_names
    assert "ApprovalTaskSnapshot" in created_names
    assert "ApprovalActionLog" in created_names

    mock_asset_service.get_asset.assert_awaited_once()
    mock_asset_service.submit_asset_review.assert_awaited_once_with(
        "asset-001",
        operator="starter-001",
    )
    mock_notification_service.create_approval_pending_notification.assert_awaited_once()


async def test_approve_task_should_mark_task_and_instance_completed(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    service = _build_service(
        mock_db,
        mock_asset_service,
        mock_notification_service,
    )

    task = MagicMock(
        id="task-001",
        approval_instance_id="approval-001",
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        status="pending",
        completed_at=None,
    )
    instance = MagicMock(
        id="approval-001",
        business_type="asset",
        business_id="asset-001",
        starter_id="starter-001",
        status="pending",
        ended_at=None,
        current_task_id="task-001",
    )

    with (
        patch.object(service, "_get_task_or_raise", new=AsyncMock(return_value=task)),
        patch.object(
            service,
            "_get_instance_or_raise",
            new=AsyncMock(return_value=instance),
        ),
    ):
        result = await service.approve_task(
            task_id="task-001",
            operator_id="reviewer-001",
            comment="审批通过",
        )

    assert result.status == "approved"
    assert task.status == "completed"
    assert task.completed_at is not None
    assert instance.status == "approved"
    assert instance.ended_at is not None
    assert instance.current_task_id is None
    mock_asset_service.approve_asset_review.assert_awaited_once_with(
        "asset-001",
        reviewer="reviewer-001",
    )


async def test_reject_task_should_restore_asset_to_draft(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    service = _build_service(
        mock_db,
        mock_asset_service,
        mock_notification_service,
    )

    task = MagicMock(
        id="task-001",
        approval_instance_id="approval-001",
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        status="pending",
        completed_at=None,
    )
    instance = MagicMock(
        id="approval-001",
        business_type="asset",
        business_id="asset-001",
        starter_id="starter-001",
        status="pending",
        ended_at=None,
        current_task_id="task-001",
    )

    with (
        patch.object(service, "_get_task_or_raise", new=AsyncMock(return_value=task)),
        patch.object(
            service,
            "_get_instance_or_raise",
            new=AsyncMock(return_value=instance),
        ),
    ):
        result = await service.reject_task(
            task_id="task-001",
            operator_id="reviewer-001",
            comment="资料不完整",
        )

    assert result.status == "rejected"
    assert task.status == "completed"
    assert instance.status == "rejected"
    mock_asset_service.reject_asset_review.assert_awaited_once_with(
        "asset-001",
        reviewer="reviewer-001",
        reason="资料不完整",
    )


async def test_withdraw_task_should_only_allow_starter(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    service = _build_service(
        mock_db,
        mock_asset_service,
        mock_notification_service,
    )

    task = MagicMock(
        id="task-001",
        approval_instance_id="approval-001",
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        status="pending",
    )
    instance = MagicMock(
        id="approval-001",
        business_type="asset",
        business_id="asset-001",
        starter_id="starter-001",
        status="pending",
        current_task_id="task-001",
    )

    with (
        patch.object(service, "_get_task_or_raise", new=AsyncMock(return_value=task)),
        patch.object(
            service,
            "_get_instance_or_raise",
            new=AsyncMock(return_value=instance),
        ),
    ):
        with pytest.raises(Exception, match="仅发起人可撤回"):
            await service.withdraw_task(
                task_id="task-001",
                operator_id="other-user",
                comment="撤回重提",
            )


async def test_withdraw_task_should_restore_asset_and_complete_instance(
    mock_db: MagicMock,
    mock_asset_service: MagicMock,
    mock_notification_service: MagicMock,
) -> None:
    service = _build_service(
        mock_db,
        mock_asset_service,
        mock_notification_service,
    )

    task = MagicMock(
        id="task-001",
        approval_instance_id="approval-001",
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        status="pending",
        completed_at=None,
    )
    instance = MagicMock(
        id="approval-001",
        business_type="asset",
        business_id="asset-001",
        starter_id="starter-001",
        status="pending",
        ended_at=None,
        current_task_id="task-001",
    )

    with (
        patch.object(service, "_get_task_or_raise", new=AsyncMock(return_value=task)),
        patch.object(
            service,
            "_get_instance_or_raise",
            new=AsyncMock(return_value=instance),
        ),
    ):
        result = await service.withdraw_task(
            task_id="task-001",
            operator_id="starter-001",
            comment="撤回重提",
        )

    assert result.status == "withdrawn"
    assert task.status == "cancelled"
    assert task.completed_at is not None
    assert instance.status == "withdrawn"
    assert instance.ended_at is not None
    assert instance.current_task_id is None
    mock_asset_service.withdraw_asset_review.assert_awaited_once_with(
        "asset-001",
        operator="starter-001",
        reason="撤回重提",
    )
    mock_notification_service.mark_approval_notifications_read.assert_awaited_once_with(
        mock_db,
        approval_instance_id="approval-001",
    )
