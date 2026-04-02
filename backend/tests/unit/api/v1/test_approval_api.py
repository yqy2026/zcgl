"""审批 API 分层与契约测试。"""

from __future__ import annotations

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def _module():
    return import_module("src.api.v1.approval")


def test_approval_routes_should_exist() -> None:
    router = _module().router
    paths = {route.path for route in router.routes}  # type: ignore[attr-defined]
    required = {
        "/processes/start",
        "/tasks/pending",
        "/processes/mine",
        "/processes/{approval_instance_id}/timeline",
        "/tasks/{task_id}/approve",
        "/tasks/{task_id}/reject",
        "/tasks/{task_id}/withdraw",
    }
    assert required.issubset(paths), f"缺少路径: {required - paths}"


@pytest.mark.asyncio
async def test_start_process_should_delegate_to_service() -> None:
    module = _module()
    endpoint = getattr(module, "start_approval_process", None)
    assert endpoint is not None, "start_approval_process 路由尚未实现"

    schema_module = import_module("src.schemas.approval")
    request_schema = getattr(schema_module, "ApprovalProcessStartRequest", None)
    assert request_schema is not None, "ApprovalProcessStartRequest 尚未实现"

    payload = request_schema(
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        comment="发起审批",
    )
    user = MagicMock(id="starter-001")
    approval = MagicMock(id="approval-001")
    db = AsyncMock()
    mock_service = MagicMock()
    mock_service.start_process = AsyncMock(return_value=approval)

    with patch(
        "src.api.v1.approval.ApprovalService",
        return_value=mock_service,
    ) as mock_service_cls:
        result = await endpoint(
            payload=payload,
            db=db,
            current_user=user,
        )

    assert result is approval
    mock_service_cls.assert_called_once_with(db)
    mock_service.start_process.assert_awaited_once_with(
        business_type="asset",
        business_id="asset-001",
        assignee_user_id="reviewer-001",
        starter_id="starter-001",
        comment="发起审批",
    )


@pytest.mark.asyncio
async def test_list_pending_tasks_should_delegate_to_service() -> None:
    module = _module()
    endpoint = getattr(module, "list_pending_approval_tasks", None)
    assert endpoint is not None, "list_pending_approval_tasks 路由尚未实现"

    tasks = [MagicMock(id="task-001")]
    db = AsyncMock()
    mock_service = MagicMock()
    mock_service.list_pending_tasks = AsyncMock(return_value=tasks)

    with patch(
        "src.api.v1.approval.ApprovalService",
        return_value=mock_service,
    ) as mock_service_cls:
        result = await endpoint(
            db=db,
            current_user=MagicMock(id="reviewer-001"),
        )

    assert result is tasks
    mock_service_cls.assert_called_once_with(db)
    mock_service.list_pending_tasks.assert_awaited_once_with(
        assignee_user_id="reviewer-001"
    )


@pytest.mark.asyncio
async def test_approve_task_should_delegate_to_service() -> None:
    module = _module()
    endpoint = getattr(module, "approve_approval_task", None)
    assert endpoint is not None, "approve_approval_task 路由尚未实现"

    schema_module = import_module("src.schemas.approval")
    request_schema = getattr(schema_module, "ApprovalTaskActionRequest", None)
    assert request_schema is not None, "ApprovalTaskActionRequest 尚未实现"

    payload = request_schema(comment="通过")
    result_payload = MagicMock(id="approval-001", status="approved")
    db = AsyncMock()
    mock_service = MagicMock()
    mock_service.approve_task = AsyncMock(return_value=result_payload)

    with patch(
        "src.api.v1.approval.ApprovalService",
        return_value=mock_service,
    ) as mock_service_cls:
        result = await endpoint(
            task_id="task-001",
            payload=payload,
            db=db,
            current_user=MagicMock(id="reviewer-001"),
        )

    assert result is result_payload
    mock_service_cls.assert_called_once_with(db)
    mock_service.approve_task.assert_awaited_once_with(
        task_id="task-001",
        operator_id="reviewer-001",
        comment="通过",
    )


@pytest.mark.asyncio
async def test_get_process_timeline_should_delegate_to_service() -> None:
    module = _module()
    endpoint = getattr(module, "get_approval_process_timeline", None)
    assert endpoint is not None, "get_approval_process_timeline 路由尚未实现"

    timeline = [MagicMock(action="start"), MagicMock(action="approve")]
    db = AsyncMock()
    mock_service = MagicMock()
    mock_service.get_process_timeline = AsyncMock(return_value=timeline)

    with patch(
        "src.api.v1.approval.ApprovalService",
        return_value=mock_service,
    ) as mock_service_cls:
        result = await endpoint(
            approval_instance_id="approval-001",
            db=db,
            current_user=MagicMock(id="starter-001"),
        )

    assert result is timeline
    mock_service_cls.assert_called_once_with(db)
    mock_service.get_process_timeline.assert_awaited_once_with(
        approval_instance_id="approval-001",
        current_user_id="starter-001",
    )
