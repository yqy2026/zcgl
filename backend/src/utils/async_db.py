from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class SupportsDBInit(Protocol):
    def __init__(self, db: Session, *args: Any, **kwargs: Any) -> None: ...

async def run_sync[T](db: AsyncSession, func: Callable[[Session], T]) -> T:
    """
    Run sync DB logic against an AsyncSession without blocking the event loop.

    The callback receives a sync Session bound to the AsyncSession connection.
    """
    return await db.run_sync(func)


class AsyncDBMethodAdapter[S]:
    """
    Adapt sync methods that expect (db: Session, ...) into awaitable calls.

    Example:
        adapter = AsyncDBMethodAdapter(db, UserCRUD())
        user = await adapter.get(user_id)
    """

    def __init__(self, db: AsyncSession, target: S) -> None:
        self._db = db
        self._target = target

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self._db.run_sync(
                lambda sync_db: attr(sync_db, *args, **kwargs)
            )

        return wrapper


class AsyncServiceClassAdapter[ServiceT: SupportsDBInit]:
    """
    Adapt sync service classes that accept (db: Session) in the constructor.

    Example:
        service = AsyncServiceClassAdapter(db, RBACService)
        result = await service.check_user_permission(...)
    """

    def __init__(
        self, db: AsyncSession, service_cls: type[ServiceT], *args: Any, **kwargs: Any
    ) -> None:
        self._db = db
        self._service_cls = service_cls
        self._args = args
        self._kwargs = kwargs

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._service_cls, name)
        if not callable(attr):
            return attr

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            def _call(sync_db: Session) -> Any:
                service = self._service_cls(sync_db, *self._args, **self._kwargs)
                method = getattr(service, name)
                return method(*args, **kwargs)

            return await self._db.run_sync(_call)

        return wrapper
