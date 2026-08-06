"""Trusted ABAC resource-context loaders."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserScopeContextLoader(Protocol):
    async def __call__(self, *, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Load trusted scope context for a user resource."""


class OwnershipPartyResolver(Protocol):
    async def __call__(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
        ownership_code: Any,
        ownership_name: Any,
    ) -> str | None:
        """Resolve an ownership resource to a Party id."""


def is_queryable_session(db: Any) -> bool:
    if isinstance(db, AsyncSession):
        return True
    execute = getattr(db, "execute", None)
    if execute is None:
        return False
    return inspect.iscoroutinefunction(execute)


async def load_asset_scope_context(
    *,
    db: AsyncSession,
    asset_id: str,
) -> dict[str, Any]:
    from ..models.asset import Asset
    from ..models.project import Project
    from ..models.project_asset import ProjectAsset

    stmt = (
        select(
            Asset.id.label("asset_id"),
            Asset.owner_party_id,
            Project.manager_party_id.label("manager_party_id"),
        )
        .outerjoin(
            ProjectAsset,
            (ProjectAsset.asset_id == Asset.id) & ProjectAsset.valid_to.is_(None),
        )
        .outerjoin(Project, Project.id == ProjectAsset.project_id)
        .where(Asset.id == asset_id)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_owner_party_id = normalize_optional_str(row.get("owner_party_id"))
    normalized_manager_party_id = normalize_optional_str(row.get("manager_party_id"))
    scoped_party_id = normalized_owner_party_id or normalized_manager_party_id

    return normalize_scope_context(
        {
            "asset_id": row.get("asset_id"),
            "owner_party_id": normalized_owner_party_id,
            "manager_party_id": normalized_manager_party_id,
            "party_id": scoped_party_id,
        }
    )


async def load_project_scope_context(
    *,
    db: AsyncSession,
    project_id: str,
) -> dict[str, Any]:
    from ..models.project import Project

    stmt = select(
        Project.id.label("project_id"),
        Project.manager_party_id,
    ).where(Project.id == project_id)
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_manager_party_id = normalize_optional_str(row.get("manager_party_id"))

    return normalize_scope_context(
        {
            "project_id": row.get("project_id"),
            "manager_party_id": normalized_manager_party_id,
            "party_id": normalized_manager_party_id,
        }
    )


async def load_contract_scope_context(
    *,
    db: AsyncSession,
    contract_id: str,
) -> dict[str, Any]:
    from ..models.contract_group import Contract, ContractGroup

    stmt = (
        select(
            Contract.contract_id.label("contract_id"),
            ContractGroup.owner_party_id.label("owner_party_id"),
            ContractGroup.operator_party_id.label("manager_party_id"),
            Contract.lessee_party_id.label("tenant_party_id"),
        )
        .join(
            ContractGroup,
            Contract.contract_group_id == ContractGroup.contract_group_id,
        )
        .where(Contract.contract_id == contract_id)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_owner_party_id = normalize_optional_str(row.get("owner_party_id"))
    normalized_manager_party_id = normalize_optional_str(row.get("manager_party_id"))

    return normalize_scope_context(
        {
            "contract_id": row.get("contract_id"),
            "owner_party_id": normalized_owner_party_id,
            "manager_party_id": normalized_manager_party_id,
            "party_id": normalized_owner_party_id or normalized_manager_party_id,
            "tenant_party_id": row.get("tenant_party_id"),
        }
    )


async def load_ownership_scope_context(
    *,
    db: AsyncSession,
    ownership_id: str,
    resolve_ownership_party_id: OwnershipPartyResolver,
) -> dict[str, Any]:
    from ..models.ownership import Ownership

    stmt = select(
        Ownership.id.label("ownership_id"),
        Ownership.code.label("ownership_code"),
        Ownership.name.label("ownership_name"),
    ).where(Ownership.id == ownership_id)
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_ownership_id = normalize_optional_str(row.get("ownership_id"))
    if normalized_ownership_id is None:
        return {}

    scoped_party_id = await resolve_ownership_party_id(
        db=db,
        ownership_id=normalized_ownership_id,
        ownership_code=row.get("ownership_code"),
        ownership_name=row.get("ownership_name"),
    )
    if scoped_party_id is None:
        scoped_party_id = normalized_ownership_id

    return normalize_scope_context(
        {
            "ownership_id": normalized_ownership_id,
            "party_id": scoped_party_id,
            "owner_party_id": scoped_party_id,
            "manager_party_id": scoped_party_id,
        }
    )


async def load_party_scope_context(
    *,
    db: AsyncSession,
    party_id: str,
) -> dict[str, Any]:
    from ..models.party import Party

    stmt = select(Party.id.label("party_id")).where(Party.id == party_id)
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}
    return normalize_scope_context({"party_id": row.get("party_id")})


async def load_role_scope_context(
    *,
    db: AsyncSession,
    role_id: str,
) -> dict[str, Any]:
    from ..models.rbac import Role

    stmt = select(
        Role.id.label("role_id"),
        Role.party_id,
    ).where(Role.id == role_id)
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_role_id = normalize_optional_str(row.get("role_id"))
    if normalized_role_id is None:
        return {}

    scoped_party_id = normalize_optional_str(row.get("party_id"))
    if scoped_party_id is None:
        scoped_party_id = build_unscoped_party_id(
            resource_type="role",
            resource_id=normalized_role_id,
        )

    return normalize_scope_context(
        {
            "role_id": normalized_role_id,
            "party_id": scoped_party_id,
            "owner_party_id": scoped_party_id,
            "manager_party_id": scoped_party_id,
        }
    )


async def load_user_scope_context(
    *,
    db: AsyncSession,
    user_id: str,
) -> dict[str, Any]:
    from ..services.party_scope_resolver import party_scope_resolver

    normalized_user_id = normalize_optional_str(user_id)
    if normalized_user_id is None:
        return {}
    scope = await party_scope_resolver.resolve(db, user_id=normalized_user_id)
    scoped_party_id = next(iter(scope.effective_party_ids), None)
    if scoped_party_id is None:
        scoped_party_id = build_unscoped_party_id(
            resource_type="user",
            resource_id=normalized_user_id,
        )
    owner_party_id = next(iter(scope.owner_party_ids), scoped_party_id)
    manager_party_id = next(iter(scope.manager_party_ids), scoped_party_id)

    return normalize_scope_context(
        {
            "user_id": normalized_user_id,
            "organization_id": scope.organization_id,
            "party_id": scoped_party_id,
            "owner_party_id": owner_party_id,
            "manager_party_id": manager_party_id,
        }
    )


async def load_task_scope_context(
    *,
    db: AsyncSession,
    task_id: str,
    load_user_scope_context: UserScopeContextLoader,
) -> dict[str, Any]:
    from ..models.task import AsyncTask

    task_stmt = select(
        AsyncTask.id.label("task_id"),
        AsyncTask.user_id,
    ).where(AsyncTask.id == task_id)
    task_row = (await db.execute(task_stmt)).mappings().one_or_none()
    if task_row is None:
        return {}

    normalized_task_id = normalize_optional_str(task_row.get("task_id"))
    if normalized_task_id is None:
        return {}

    normalized_user_id = normalize_optional_str(task_row.get("user_id"))
    user_scope: dict[str, Any] = {}
    if normalized_user_id is not None:
        user_scope = await load_user_scope_context(
            db=db,
            user_id=normalized_user_id,
        )

    scoped_party_id = normalize_optional_str(user_scope.get("party_id"))
    if scoped_party_id is None:
        scoped_party_id = build_unscoped_party_id(
            resource_type="task",
            resource_id=normalized_task_id,
        )

    owner_party_id = normalize_optional_str(user_scope.get("owner_party_id"))
    manager_party_id = normalize_optional_str(user_scope.get("manager_party_id"))
    organization_id = normalize_optional_str(user_scope.get("organization_id"))

    return normalize_scope_context(
        {
            "task_id": normalized_task_id,
            "user_id": normalized_user_id,
            "organization_id": organization_id,
            "party_id": scoped_party_id,
            "owner_party_id": owner_party_id or scoped_party_id,
            "manager_party_id": manager_party_id or scoped_party_id,
        }
    )


def build_unscoped_party_id(*, resource_type: str, resource_id: str) -> str:
    return f"__unscoped__:{resource_type}:{resource_id}"


async def load_organization_scope_context(
    *,
    db: AsyncSession,
    organization_id: str,
) -> dict[str, Any]:
    from ..models.organization import Organization

    stmt = select(
        Organization.id.label("organization_id"),
        Organization.represented_party_id.label("party_id"),
    ).where(Organization.id == organization_id)
    row = (await db.execute(stmt)).mappings().one_or_none()
    if row is None:
        return {}

    normalized_org_id = normalize_optional_str(row.get("organization_id"))
    if normalized_org_id is None:
        return {}

    scoped_party_id = normalize_optional_str(row.get("party_id"))
    if scoped_party_id is None:
        scoped_party_id = build_unscoped_party_id(
            resource_type="organization",
            resource_id=normalized_org_id,
        )

    return normalize_scope_context(
        {
            "organization_id": normalized_org_id,
            "party_id": scoped_party_id,
            "owner_party_id": scoped_party_id,
            "manager_party_id": scoped_party_id,
        }
    )


async def resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str,
) -> str | None:
    from ..models.organization import Organization

    normalized_organization_id = normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    stmt = (
        select(Organization.represented_party_id.label("party_id"))
        .where(Organization.id == normalized_organization_id)
        .limit(1)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    return normalize_optional_str(row.get("party_id") if row is not None else None)


async def resolve_ownership_party_id(
    *,
    db: AsyncSession,
    ownership_id: str,
    ownership_code: Any,
    ownership_name: Any,
) -> str | None:
    from ..models.party import Party, PartyType

    lookup_conditions = [
        Party.id == ownership_id,
        Party.external_ref == ownership_id,
    ]

    normalized_code = normalize_optional_str(ownership_code)
    if normalized_code is not None:
        lookup_conditions.append(Party.code == normalized_code)

    normalized_name = normalize_optional_str(ownership_name)
    if normalized_name is not None:
        lookup_conditions.append(Party.name == normalized_name)

    for condition in lookup_conditions:
        stmt = (
            select(Party.id.label("party_id"))
            .where(
                Party.party_type == PartyType.LEGAL_ENTITY.value,
                condition,
            )
            .order_by(Party.id)
            .limit(1)
        )
        row = (await db.execute(stmt)).mappings().one_or_none()
        party_id = normalize_optional_str(
            row.get("party_id") if row is not None else None
        )
        if party_id is not None:
            return party_id
    return None


async def load_property_certificate_scope_context(
    *,
    db: AsyncSession,
    certificate_id: str,
) -> dict[str, Any]:
    from ..models.certificate_party_relation import CertificatePartyRelation
    from ..models.property_certificate import PropertyCertificate

    certificate_stmt = select(
        PropertyCertificate.id.label("certificate_id"),
    ).where(PropertyCertificate.id == certificate_id)
    row = (await db.execute(certificate_stmt)).mappings().one_or_none()
    if row is None:
        return {}

    relation_stmt = (
        select(CertificatePartyRelation.party_id.label("party_id"))
        .where(CertificatePartyRelation.certificate_id == certificate_id)
        .order_by(
            CertificatePartyRelation.is_primary.desc(),
            CertificatePartyRelation.created_at.desc(),
        )
        .limit(1)
    )
    relation_row = (await db.execute(relation_stmt)).mappings().one_or_none()
    scoped_party_id = normalize_optional_str(
        relation_row.get("party_id") if relation_row is not None else None
    )
    if scoped_party_id is None:
        scoped_party_id = build_unscoped_party_id(
            resource_type="property_certificate",
            resource_id=str(certificate_id).strip(),
        )

    return normalize_scope_context(
        {
            "certificate_id": row.get("certificate_id"),
            "party_id": scoped_party_id,
            "owner_party_id": scoped_party_id,
            "manager_party_id": scoped_party_id,
        }
    )


def normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def normalize_scope_context(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = normalize_optional_str(key)
        if normalized_key is None:
            continue
        normalized_value = normalize_optional_str(item)
        if normalized_value is None:
            continue
        normalized[normalized_key] = normalized_value
    return normalized
