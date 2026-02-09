"""ExcelTaskService 单元测试。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.enums.task import TaskStatus
from src.services.excel.excel_task_service import ExcelTaskService


def test_excel_task_service_module_should_not_use_datetime_utcnow() -> None:
    """服务模块不应直接调用 datetime.utcnow。"""
    from src.services.excel import excel_task_service as service_module

    module_source = inspect.getsource(service_module)
    assert "datetime.utcnow(" not in module_source


@pytest.mark.asyncio
async def test_mark_task_failed_should_rollback_and_update_failed_status():
    service = ExcelTaskService()
    db = MagicMock()
    db.rollback = AsyncMock()
    task = MagicMock(id="task-1")

    service.get_task = AsyncMock(return_value=task)  # type: ignore[method-assign]
    service.update_task = AsyncMock(return_value=task)  # type: ignore[method-assign]

    result = await service.mark_task_failed(
        db=db,
        task_id="task-1",
        error_message="failure",
    )

    assert result is task
    db.rollback.assert_awaited_once()
    service.get_task.assert_awaited_once_with(db=db, task_id="task-1")
    service.update_task.assert_awaited_once()
    task_data = service.update_task.await_args.kwargs["task_data"]
    assert task_data["status"] == TaskStatus.FAILED
    assert task_data["error_message"] == "failure"


@pytest.mark.asyncio
async def test_mark_task_failed_should_return_none_when_task_not_found():
    service = ExcelTaskService()
    db = MagicMock()
    db.rollback = AsyncMock()

    service.get_task = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service.update_task = AsyncMock()  # type: ignore[method-assign]

    result = await service.mark_task_failed(
        db=db,
        task_id="missing-task",
        error_message="failure",
    )

    assert result is None
    db.rollback.assert_awaited_once()
    service.get_task.assert_awaited_once_with(db=db, task_id="missing-task")
    service.update_task.assert_not_called()
