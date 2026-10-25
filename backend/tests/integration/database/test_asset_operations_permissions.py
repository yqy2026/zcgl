"""PostgreSQL verification for asset-operations capability seeding."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.database import get_async_database_url
from src.models.rbac import Permission, Role, role_permissions

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.asyncio]


async def test_asset_operations_permissions_are_granted_to_builtin_roles() -> None:
    engine = create_async_engine(get_async_database_url(), poolclass=NullPool)
    try:
        async with AsyncSession(engine) as session:
            rows = (
                await session.execute(
                    select(Permission.name, Role.name)
                    .select_from(Permission)
                    .join(
                        role_permissions,
                        role_permissions.c.permission_id == Permission.id,
                    )
                    .join(Role, Role.id == role_permissions.c.role_id)
                    .where(Permission.resource == "asset_ops")
                    .order_by(Permission.name, Role.name)
                )
            ).all()
    finally:
        await engine.dispose()

    assert {(permission_name, role_name) for permission_name, role_name in rows} == {
        (f"asset_ops:{action}", role_name)
        for action in ("read", "write", "report", "archive", "import")
        for role_name in ("ops_admin", "system_admin")
    }
