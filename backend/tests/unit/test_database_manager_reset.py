from unittest.mock import AsyncMock, MagicMock

import pytest

import src.database as database_module
from src.core.exception_handler import AuthenticationError
from src.database import DatabaseManager


@pytest.mark.asyncio
async def test_database_manager_dispose_clears_engine_and_session_factory():
    manager = DatabaseManager()
    mock_engine = AsyncMock()
    manager.engine = mock_engine
    manager.session_factory = object()

    await manager.dispose()

    mock_engine.dispose.assert_awaited_once()
    assert manager.engine is None
    assert manager.session_factory is None


@pytest.mark.asyncio
async def test_reset_database_manager_disposes_global_manager(monkeypatch):
    manager = DatabaseManager()
    mock_engine = AsyncMock()
    manager.engine = mock_engine
    manager.session_factory = object()
    monkeypatch.setattr(database_module, "_database_manager", manager)

    await database_module.reset_database_manager()

    mock_engine.dispose.assert_awaited_once()
    assert manager.engine is None
    assert manager.session_factory is None
    assert database_module._database_manager is None


@pytest.mark.asyncio
async def test_reset_database_manager_is_noop_when_not_initialized(monkeypatch):
    monkeypatch.setattr(database_module, "_database_manager", None)

    await database_module.reset_database_manager()

    assert database_module._database_manager is None


@pytest.mark.asyncio
async def test_init_db_should_not_call_create_tables(monkeypatch):
    mock_create_tables = AsyncMock()
    mock_status = {"healthy": True}

    monkeypatch.setattr(database_module, "create_tables", mock_create_tables)
    monkeypatch.setattr(database_module, "get_database_status", AsyncMock(return_value=mock_status))

    await database_module.init_db()

    mock_create_tables.assert_not_awaited()


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _install_session_factory(monkeypatch, session):
    manager = DatabaseManager()
    manager.session_factory = lambda: _SessionContext(session)
    monkeypatch.setattr(database_module, "_database_manager", manager)


@pytest.mark.asyncio
async def test_get_async_db_should_not_log_critical_for_business_error(monkeypatch):
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    _install_session_factory(monkeypatch, mock_session)

    mock_critical = MagicMock()
    monkeypatch.setattr(database_module.logger, "critical", mock_critical)

    dependency = database_module.get_async_db()
    yielded = await dependency.__anext__()
    assert yielded is mock_session

    with pytest.raises(AuthenticationError):
        await dependency.athrow(AuthenticationError("invalid"))

    mock_session.rollback.assert_awaited_once()
    mock_critical.assert_not_called()


@pytest.mark.asyncio
async def test_async_session_scope_should_not_log_critical_for_business_error(monkeypatch):
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    _install_session_factory(monkeypatch, mock_session)

    mock_critical = MagicMock()
    monkeypatch.setattr(database_module.logger, "critical", mock_critical)

    with pytest.raises(AuthenticationError):
        async with database_module.async_session_scope():
            raise AuthenticationError("invalid")

    mock_session.rollback.assert_awaited_once()
    mock_critical.assert_not_called()


@pytest.mark.asyncio
async def test_async_session_scope_should_log_critical_for_unexpected_error(monkeypatch):
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    _install_session_factory(monkeypatch, mock_session)

    mock_critical = MagicMock()
    monkeypatch.setattr(database_module.logger, "critical", mock_critical)

    with pytest.raises(RuntimeError, match="boom"):
        async with database_module.async_session_scope():
            raise RuntimeError("boom")

    mock_session.rollback.assert_awaited_once()
    mock_critical.assert_called_once()
