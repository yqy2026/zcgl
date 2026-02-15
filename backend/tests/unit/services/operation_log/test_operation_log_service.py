"""OperationLogService unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BaseBusinessError, ResourceNotFoundError
from src.services.operation_log.service import OperationLogService

pytestmark = pytest.mark.asyncio


def _build_get_logs_kwargs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "page": 2,
        "page_size": 20,
        "user_id": "user-1",
        "action": "view",
        "module": "asset",
        "resource_type": "asset",
        "response_status": "success",
        "search": "keyword",
        "start_date": "2026-02-01",
        "end_date": "2026-02-14",
    }
    payload.update(overrides)
    return payload


async def test_get_operation_logs_parses_dates_and_enriches_missing_usernames() -> None:
    service = OperationLogService()
    db = MagicMock()

    log_missing_name = SimpleNamespace(user_id="user-1", username=None)
    log_has_name = SimpleNamespace(user_id="user-2", username="existing")
    mock_log_crud = MagicMock()
    mock_log_crud.get_multi_with_count_async = AsyncMock(
        return_value=([log_missing_name, log_has_name], 2)
    )
    mock_user_crud = MagicMock()
    mock_user_crud.get_username_map_async = AsyncMock(return_value={"user-1": "alice"})

    with (
        patch(
            "src.services.operation_log.service.OperationLogCRUD",
            return_value=mock_log_crud,
        ),
        patch(
            "src.services.operation_log.service.UserCRUD",
            return_value=mock_user_crud,
        ),
    ):
        logs, total = await service.get_operation_logs(
            db,
            **_build_get_logs_kwargs(),
        )

    assert total == 2
    assert logs[0].username == "alice"
    assert logs[1].username == "existing"

    kwargs = mock_log_crud.get_multi_with_count_async.await_args.kwargs
    assert kwargs["skip"] == 20
    assert kwargs["limit"] == 20
    assert isinstance(kwargs["start_date"], datetime)
    assert isinstance(kwargs["end_date"], datetime)
    assert kwargs["end_date"] - kwargs["start_date"] == timedelta(days=13, hours=24)
    mock_user_crud.get_username_map_async.assert_awaited_once_with(db, {"user-1"})


async def test_get_operation_logs_raises_bad_request_when_start_date_invalid() -> None:
    service = OperationLogService()
    db = MagicMock()

    with pytest.raises(BaseBusinessError, match="开始日期格式错误"):
        await service.get_operation_logs(
            db,
            **_build_get_logs_kwargs(start_date="2026/02/01"),
        )


async def test_get_operation_logs_raises_bad_request_when_end_date_invalid() -> None:
    service = OperationLogService()
    db = MagicMock()

    with pytest.raises(BaseBusinessError, match="结束日期格式错误"):
        await service.get_operation_logs(
            db,
            **_build_get_logs_kwargs(end_date="2026/02/14"),
        )


async def test_get_operation_log_raises_not_found_for_missing_record() -> None:
    service = OperationLogService()
    db = MagicMock()

    mock_log_crud = MagicMock()
    mock_log_crud.get_async = AsyncMock(return_value=None)

    with patch(
        "src.services.operation_log.service.OperationLogCRUD",
        return_value=mock_log_crud,
    ):
        with pytest.raises(ResourceNotFoundError, match="operation_log"):
            await service.get_operation_log(db, log_id="log-404")


async def test_get_operation_log_enriches_username_when_missing() -> None:
    service = OperationLogService()
    db = MagicMock()

    log = SimpleNamespace(id="log-1", user_id="user-1", username=None)
    mock_log_crud = MagicMock()
    mock_log_crud.get_async = AsyncMock(return_value=log)
    mock_user_crud = MagicMock()
    mock_user_crud.get_async = AsyncMock(return_value=SimpleNamespace(username="alice"))

    with (
        patch(
            "src.services.operation_log.service.OperationLogCRUD",
            return_value=mock_log_crud,
        ),
        patch(
            "src.services.operation_log.service.UserCRUD",
            return_value=mock_user_crud,
        ),
    ):
        resolved_log = await service.get_operation_log(db, log_id="log-1")

    assert resolved_log.username == "alice"
    mock_user_crud.get_async.assert_awaited_once_with(db, "user-1")


async def test_get_operation_log_summary_aggregates_crud_results() -> None:
    service = OperationLogService()
    db = MagicMock()

    mock_log_crud = MagicMock()
    mock_log_crud.get_daily_statistics_async = AsyncMock(
        return_value={"daily_breakdown": {"2026-02-14": 5}}
    )
    mock_log_crud.get_error_statistics_async = AsyncMock(
        return_value={"total_errors": 1, "error_breakdown": {"delete": 1}}
    )
    mock_log_crud.count_async = AsyncMock(return_value=42)

    with patch(
        "src.services.operation_log.service.OperationLogCRUD",
        return_value=mock_log_crud,
    ):
        summary = await service.get_operation_log_summary(db, days=7)

    assert summary == {
        "total_logs": 42,
        "days": 7,
        "daily_statistics": {"2026-02-14": 5},
        "error_statistics": {"total_errors": 1, "error_breakdown": {"delete": 1}},
    }


async def test_export_and_cleanup_delegate_to_crud() -> None:
    service = OperationLogService()
    db = MagicMock()
    filters = {"user_id": "user-1", "module": "asset"}

    mock_log_crud = MagicMock()
    mock_log_crud.get_multi_with_count_async = AsyncMock(
        return_value=([SimpleNamespace(id="log-1")], 1)
    )
    mock_log_crud.delete_old_logs_async = AsyncMock(return_value=17)

    with patch(
        "src.services.operation_log.service.OperationLogCRUD",
        return_value=mock_log_crud,
    ):
        exported = await service.export_operation_logs(db, filters=filters)
        deleted = await service.cleanup_old_logs(db, days=90)

    assert len(exported) == 1
    assert deleted == 17
    mock_log_crud.get_multi_with_count_async.assert_awaited_once_with(
        db=db,
        skip=0,
        limit=10000,
        **filters,
    )
    mock_log_crud.delete_old_logs_async.assert_awaited_once_with(db, 90)

