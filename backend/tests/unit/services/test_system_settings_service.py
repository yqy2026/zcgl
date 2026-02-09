"""SystemSettingsService 单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.services.system_settings.service import SystemSettingsService


@pytest.mark.asyncio
async def test_check_database_connection_returns_true_when_query_succeeds():
    service = SystemSettingsService()
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())

    connected = await service.check_database_connection(db=mock_db)

    assert connected is True
    mock_db.execute.assert_awaited_once()
    assert str(mock_db.execute.await_args.args[0]) == "SELECT 1"


@pytest.mark.asyncio
async def test_check_database_connection_returns_false_when_query_fails():
    service = SystemSettingsService()
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=SQLAlchemyError("db unavailable"))

    connected = await service.check_database_connection(db=mock_db)

    assert connected is False
