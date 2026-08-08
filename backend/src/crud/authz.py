"""CRUD helpers for ABAC policy data access."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.abac import ABACPolicy, ABACRolePolicy


class CRUDAuthz:
    """ABAC policy and role-binding CRUD methods."""

    async def get_policies_by_role_ids(
        self,
        db: AsyncSession,
        *,
        role_ids: list[str],
        enabled_only: bool = True,
    ) -> list[ABACPolicy]:
        if not role_ids:
            return []

        stmt = (
            select(ABACPolicy)
            .join(ABACRolePolicy, ABACRolePolicy.policy_id == ABACPolicy.id)
            .where(ABACRolePolicy.role_id.in_(role_ids))
            .options(selectinload(ABACPolicy.rules))
            .distinct()
            .order_by(ABACPolicy.priority.asc())
        )

        if enabled_only:
            stmt = stmt.where(
                ABACPolicy.enabled.is_(True), ABACRolePolicy.enabled.is_(True)
            )

        return list((await db.execute(stmt)).scalars().all())

    async def update_policy(
        self,
        db: AsyncSession,
        *,
        db_obj: ABACPolicy,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> ABACPolicy:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj


crud_authz = CRUDAuthz()


__all__ = ["CRUDAuthz", "crud_authz"]
