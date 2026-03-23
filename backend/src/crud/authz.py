"""CRUD helpers for ABAC policy data access."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy


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

    async def create_policy(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> ABACPolicy:
        policy = ABACPolicy(**obj_in)
        db.add(policy)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(policy)
        return policy

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

    async def create_policy_rule(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> ABACPolicyRule:
        rule = ABACPolicyRule(**obj_in)
        db.add(rule)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(rule)
        return rule

    async def bind_role_policy(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> ABACRolePolicy:
        binding = ABACRolePolicy(**obj_in)
        db.add(binding)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(binding)
        return binding

    async def unbind_role_policy(
        self,
        db: AsyncSession,
        *,
        role_id: str,
        policy_id: str,
        commit: bool = True,
    ) -> int:
        stmt = delete(ABACRolePolicy).where(
            ABACRolePolicy.role_id == role_id,
            ABACRolePolicy.policy_id == policy_id,
        )
        result = await db.execute(stmt)
        if commit:
            await db.commit()
        else:
            await db.flush()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)


crud_authz = CRUDAuthz()


__all__ = ["CRUDAuthz", "crud_authz"]
