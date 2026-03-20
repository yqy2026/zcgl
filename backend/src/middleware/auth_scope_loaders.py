"""
ABAC 资源 scope loader — 从数据库加载资源的所属方/管理方信息，供鉴权决策使用。
本模块以 Mixin 形式提供，由 `AuthzPermissionChecker`（auth_authz.py）继承。
"""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.str import normalize_optional_str

logger = logging.getLogger(__name__)


class AuthzScopeLoaderMixin:
    """Mixin: 各类资源的 scope context 加载器。"""

    async def _load_contact_scope_context(
        self,
        *,
        db: AsyncSession,
        contact_id: str | None,
        request_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized_entity_type = normalize_optional_str(
            request_context.get("entity_type")
        )
        normalized_entity_id = normalize_optional_str(request_context.get("entity_id"))

        if normalized_entity_type is not None and normalized_entity_id is not None:
            return await self._load_contact_parent_scope_context(
                db=db,
                entity_type=normalized_entity_type,
                entity_id=normalized_entity_id,
            )
        if contact_id is None:
            return {}

        from ..models.contact import Contact

        stmt = select(
            Contact.id.label("contact_id"),
            Contact.entity_type.label("entity_type"),
            Contact.entity_id.label("entity_id"),
        ).where(Contact.id == contact_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        contact_scope = await self._load_contact_parent_scope_context(
            db=db,
            entity_type=row.get("entity_type"),
            entity_id=row.get("entity_id"),
        )
        if len(contact_scope) == 0:
            return {}
        return {
            **contact_scope,
            **self._normalize_scope_context({"contact_id": row.get("contact_id")}),
        }

    async def _load_contact_parent_scope_context(
        self,
        *,
        db: AsyncSession,
        entity_type: Any,
        entity_id: Any,
    ) -> dict[str, Any]:
        normalized_entity_type = normalize_optional_str(entity_type)
        normalized_entity_id = normalize_optional_str(entity_id)
        if normalized_entity_type is None or normalized_entity_id is None:
            return {}
        if normalized_entity_type == "ownership":
            return await self._load_ownership_scope_context(
                db=db, ownership_id=normalized_entity_id
            )
        if normalized_entity_type == "project":
            return await self._load_project_scope_context(
                db=db, project_id=normalized_entity_id
            )
        if normalized_entity_type in {"party", "tenant"}:
            return await self._load_party_scope_context(
                db=db, party_id=normalized_entity_id
            )
        if normalized_entity_type == "organization":
            return await self._load_organization_scope_context(
                db=db, organization_id=normalized_entity_id
            )
        return {}

    async def _load_asset_scope_context(
        self,
        *,
        db: AsyncSession,
        asset_id: str,
    ) -> dict[str, Any]:
        from ..models.asset import Asset

        stmt = select(
            Asset.id.label("asset_id"),
            Asset.owner_party_id,
            Asset.manager_party_id,
        ).where(Asset.id == asset_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        normalized_owner = normalize_optional_str(row.get("owner_party_id"))
        normalized_manager = normalize_optional_str(row.get("manager_party_id"))
        return self._normalize_scope_context(
            {
                "asset_id": row.get("asset_id"),
                "owner_party_id": normalized_owner,
                "manager_party_id": normalized_manager,
                "party_id": normalized_owner or normalized_manager,
            }
        )

    async def _load_project_scope_context(
        self,
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
        normalized_manager = normalize_optional_str(row.get("manager_party_id"))
        return self._normalize_scope_context(
            {
                "project_id": row.get("project_id"),
                "manager_party_id": normalized_manager,
                "party_id": normalized_manager,
            }
        )

    async def _load_contract_group_scope_context(
        self,
        *,
        db: AsyncSession,
        group_id: str,
    ) -> dict[str, Any]:
        from ..models.contract_group import ContractGroup

        stmt = select(
            ContractGroup.contract_group_id.label("contract_group_id"),
            ContractGroup.owner_party_id.label("owner_party_id"),
            ContractGroup.operator_party_id.label("manager_party_id"),
        ).where(ContractGroup.contract_group_id == group_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        normalized_owner = normalize_optional_str(row.get("owner_party_id"))
        normalized_manager = normalize_optional_str(row.get("manager_party_id"))
        return self._normalize_scope_context(
            {
                "contract_group_id": row.get("contract_group_id"),
                "owner_party_id": normalized_owner,
                "manager_party_id": normalized_manager,
                "party_id": normalized_owner or normalized_manager,
            }
        )

    async def _load_contract_scope_context(
        self,
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
        normalized_owner = normalize_optional_str(row.get("owner_party_id"))
        normalized_manager = normalize_optional_str(row.get("manager_party_id"))
        return self._normalize_scope_context(
            {
                "contract_id": row.get("contract_id"),
                "owner_party_id": normalized_owner,
                "manager_party_id": normalized_manager,
                "party_id": normalized_owner or normalized_manager,
                "tenant_party_id": row.get("tenant_party_id"),
            }
        )

    async def _load_ownership_scope_context(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
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
        scoped_party_id = await self._resolve_ownership_party_id(
            db=db,
            ownership_id=normalized_ownership_id,
            ownership_code=row.get("ownership_code"),
            ownership_name=row.get("ownership_name"),
        )
        if scoped_party_id is None:
            scoped_party_id = normalized_ownership_id  # Legacy fallback: fail-closed
        return self._normalize_scope_context(
            {
                "ownership_id": normalized_ownership_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_party_scope_context(
        self,
        *,
        db: AsyncSession,
        party_id: str,
    ) -> dict[str, Any]:
        from ..models.party import Party

        stmt = select(Party.id.label("party_id")).where(Party.id == party_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        return self._normalize_scope_context({"party_id": row.get("party_id")})

    async def _load_role_scope_context(
        self,
        *,
        db: AsyncSession,
        role_id: str,
    ) -> dict[str, Any]:
        from ..models.rbac import Role

        stmt = select(Role.id.label("role_id"), Role.party_id).where(Role.id == role_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        normalized_role_id = normalize_optional_str(row.get("role_id"))
        if normalized_role_id is None:
            return {}
        scoped_party_id = normalize_optional_str(row.get("party_id"))
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="role",
                resource_id=normalized_role_id,
            )
        return self._normalize_scope_context(
            {
                "role_id": normalized_role_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_user_scope_context(
        self,
        *,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        from ..models.auth import User
        from ..models.user_party_binding import UserPartyBinding

        user_stmt = select(
            User.id.label("user_id"),
            User.default_organization_id,
        ).where(User.id == user_id)
        user_row = (await db.execute(user_stmt)).mappings().one_or_none()
        if user_row is None:
            return {}
        normalized_user_id = normalize_optional_str(user_row.get("user_id"))
        if normalized_user_id is None:
            return {}

        now = datetime.now(UTC).replace(tzinfo=None)
        binding_stmt = (
            select(UserPartyBinding.party_id.label("party_id"))
            .where(UserPartyBinding.user_id == normalized_user_id)
            .where(UserPartyBinding.valid_from <= now)
            .where(
                (UserPartyBinding.valid_to.is_(None))
                | (UserPartyBinding.valid_to >= now)
            )
            .order_by(
                UserPartyBinding.is_primary.desc(),
                UserPartyBinding.valid_from.desc(),
                UserPartyBinding.created_at.desc(),
            )
            .limit(1)
        )
        binding_row = (await db.execute(binding_stmt)).mappings().one_or_none()

        scoped_party_id = normalize_optional_str(
            binding_row.get("party_id") if binding_row is not None else None
        )
        normalized_organization_id = normalize_optional_str(
            user_row.get("default_organization_id")
        )
        if scoped_party_id is None and normalized_organization_id is not None:
            scoped_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if scoped_party_id is None:
                scoped_party_id = normalized_organization_id
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="user",
                resource_id=normalized_user_id,
            )
        return self._normalize_scope_context(
            {
                "user_id": normalized_user_id,
                "organization_id": normalized_organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_task_scope_context(
        self,
        *,
        db: AsyncSession,
        task_id: str,
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
            user_scope = await self._load_user_scope_context(
                db=db, user_id=normalized_user_id
            )

        scoped_party_id = normalize_optional_str(user_scope.get("party_id"))
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="task",
                resource_id=normalized_task_id,
            )
        owner_party_id = normalize_optional_str(user_scope.get("owner_party_id"))
        manager_party_id = normalize_optional_str(user_scope.get("manager_party_id"))
        organization_id = normalize_optional_str(user_scope.get("organization_id"))
        return self._normalize_scope_context(
            {
                "task_id": normalized_task_id,
                "user_id": normalized_user_id,
                "organization_id": organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": owner_party_id or scoped_party_id,
                "manager_party_id": manager_party_id or scoped_party_id,
            }
        )

    async def _load_organization_scope_context(
        self,
        *,
        db: AsyncSession,
        organization_id: str,
    ) -> dict[str, Any]:
        from ..models.organization import Organization

        stmt = select(
            Organization.id.label("organization_id"),
            Organization.code.label("organization_code"),
            Organization.name.label("organization_name"),
        ).where(Organization.id == organization_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        normalized_org_id = normalize_optional_str(row.get("organization_id"))
        if normalized_org_id is None:
            return {}
        scoped_party_id = await self._resolve_organization_party_id(
            db=db,
            organization_id=normalized_org_id,
            organization_code=row.get("organization_code"),
            organization_name=row.get("organization_name"),
        )
        if scoped_party_id is None:
            scoped_party_id = normalized_org_id  # Legacy fallback: fail-closed
        return self._normalize_scope_context(
            {
                "organization_id": normalized_org_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_property_certificate_scope_context(
        self,
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
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="property_certificate",
                resource_id=str(certificate_id).strip(),
            )
        return self._normalize_scope_context(
            {
                "certificate_id": row.get("certificate_id"),
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    # -- Party-ID resolution helpers --

    async def _resolve_party_id_by_type(
        self,
        *,
        db: AsyncSession,
        party_type_value: str,
        entity_id: str,
        entity_code: Any,
        entity_name: Any,
    ) -> str | None:
        """Shared lookup: find Party.id matching a given party_type via id/external_ref/code/name."""
        from ..models.party import Party

        lookup_conditions = [
            Party.id == entity_id,
            Party.external_ref == entity_id,
        ]
        normalized_code = normalize_optional_str(entity_code)
        if normalized_code is not None:
            lookup_conditions.append(Party.code == normalized_code)
        normalized_name = normalize_optional_str(entity_name)
        if normalized_name is not None:
            lookup_conditions.append(Party.name == normalized_name)

        for condition in lookup_conditions:
            stmt = (
                select(Party.id.label("party_id"))
                .where(Party.party_type == party_type_value, condition)
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

    async def _resolve_organization_party_id(
        self,
        *,
        db: AsyncSession,
        organization_id: str,
        organization_code: Any,
        organization_name: Any,
    ) -> str | None:
        from ..models.party import PartyType

        return await self._resolve_party_id_by_type(
            db=db,
            party_type_value=PartyType.ORGANIZATION.value,
            entity_id=organization_id,
            entity_code=organization_code,
            entity_name=organization_name,
        )

    async def _resolve_ownership_party_id(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
        ownership_code: Any,
        ownership_name: Any,
    ) -> str | None:
        from ..models.party import PartyType

        return await self._resolve_party_id_by_type(
            db=db,
            party_type_value=PartyType.LEGAL_ENTITY.value,
            entity_id=ownership_id,
            entity_code=ownership_code,
            entity_name=ownership_name,
        )
