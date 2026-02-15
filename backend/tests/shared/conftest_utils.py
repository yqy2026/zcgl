"""
共享测试工具模块

此模块包含在多个测试目录中重复使用的测试工具类和函数。
避免代码重复，提高可维护性。
"""

from __future__ import annotations

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.base import Transaction
from sqlalchemy.orm import Session, sessionmaker


class AsyncSessionAdapter:
    """
    将同步 SQLAlchemy Session 包装为异步兼容接口的适配器。

    用于测试中，当需要模拟 AsyncSession 但实际使用同步 session 时。
    所有异步方法实际上是同步调用，但返回协程以兼容异步代码。

    Usage:
        @pytest.fixture
        def mock_db():
            sync_session = Session(engine)
            return AsyncSessionAdapter(sync_session)
    """

    def __init__(self, session):  # noqa: ANN001 - test helper
        """Initialize adapter with a sync session."""
        self._session = session

    async def execute(self, *args, **kwargs):  # noqa: ANN001
        """Execute a statement."""
        return self._session.execute(*args, **kwargs)

    async def commit(self):  # noqa: D401 - test helper
        """Commit the transaction."""
        return self._session.commit()

    async def refresh(self, *args, **kwargs):  # noqa: ANN001
        """Refresh an instance."""
        return self._session.refresh(*args, **kwargs)

    async def flush(self):  # noqa: D401 - test helper
        """Flush pending changes."""
        return self._session.flush()

    async def rollback(self):  # noqa: D401 - test helper
        """Rollback the transaction."""
        return self._session.rollback()

    async def get(self, *args, **kwargs):  # noqa: ANN001
        """Get an instance by primary key."""
        return self._session.get(*args, **kwargs)

    async def scalar(self, *args, **kwargs):  # noqa: ANN001
        """Execute and return scalar result."""
        return self._session.scalar(*args, **kwargs)

    def add(self, *args, **kwargs):  # noqa: ANN001
        """Add an instance to the session."""
        return self._session.add(*args, **kwargs)

    async def delete(self, *args, **kwargs):  # noqa: ANN001
        """Delete an instance."""
        return self._session.delete(*args, **kwargs)

    def __getattr__(self, name: str):  # noqa: D401 - test helper
        """Delegate unknown attributes to the wrapped session."""
        return getattr(self._session, name)


def create_transactional_session(
    engine: Engine,
) -> tuple[Session, Connection, Transaction]:
    """
    Create a transactional sync SQLAlchemy session for tests.

    Returns:
        (session, connection, transaction)
    """
    connection = engine.connect()
    transaction = connection.begin()
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = test_session_local()
    return session, connection, transaction


def cleanup_transactional_session(
    session: Session,
    connection: Connection,
    transaction: Transaction,
) -> None:
    """Best-effort cleanup for transactional test sessions."""
    try:
        session.close()
        transaction.rollback()
        connection.close()
    except Exception:
        pass


__all__ = [
    "AsyncSessionAdapter",
    "cleanup_transactional_session",
    "create_transactional_session",
]
