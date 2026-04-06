"""Build authz subject context from user-party bindings."""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.party import CRUDParty, party_crud
from ...models.auth import User
from ...models.user_party_binding import RelationType, UserPartyBinding
from ...schemas.authz import PerspectiveName

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubjectContext:
    """Resolved subject context for ABAC evaluation."""

    user_id: str
    owner_party_ids: list[str]
    manager_party_ids: list[str]
    headquarters_party_ids: list[str]
    role_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "owner_party_ids": self.owner_party_ids,
            "manager_party_ids": self.manager_party_ids,
            "headquarters_party_ids": self.headquarters_party_ids,
            "role_ids": self.role_ids,
            "user_tags": [],
        }


class AuthzContextBuilder:
    """Build ABAC subject context from persistence layer."""

    def __init__(self, party_data_access: CRUDParty | None = None) -> None:
        self.party_crud = party_data_access or party_crud

    async def build_subject_context(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        role_ids: list[str] | None = None,
    ) -> SubjectContext:
        bindings = await self.party_crud.get_user_bindings(
            db,
            user_id=user_id,
            active_only=True,
        )

        owner_party_ids: set[str] = set()
        manager_party_ids: set[str] = set()
        headquarters_party_ids: set[str] = set()

        for binding in bindings:
            party_id = str(binding.party_id)
            relation_type = self._normalize_relation_type(binding)
            if relation_type == RelationType.OWNER.value:
                owner_party_ids.add(party_id)
                continue

            if relation_type == RelationType.MANAGER.value:
                manager_party_ids.add(party_id)
                continue

            if relation_type == RelationType.HEADQUARTERS.value:
                headquarters_party_ids.add(party_id)
                descendants = await self.party_crud.get_descendants(
                    db,
                    party_id=party_id,
                    include_self=True,
                )
                manager_party_ids.update(descendants)

        if (
            len(owner_party_ids) == 0
            and len(manager_party_ids) == 0
            and len(headquarters_party_ids) == 0
        ):
            legacy_org_id = await self._resolve_legacy_default_organization_id(
                db,
                user_id=user_id,
            )
            if legacy_org_id is not None:
                legacy_party_id = (
                    await self._resolve_legacy_default_organization_party_id(
                        db,
                        user_id=user_id,
                        organization_id=legacy_org_id,
                    )
                )
                if legacy_party_id is not None:
                    owner_party_ids.add(legacy_party_id)
                    manager_party_ids.add(legacy_party_id)

        return SubjectContext(
            user_id=user_id,
            owner_party_ids=sorted(owner_party_ids),
            manager_party_ids=sorted(manager_party_ids),
            headquarters_party_ids=sorted(headquarters_party_ids),
            role_ids=sorted(role_ids or []),
        )

    @staticmethod
    def resolve_allowed_binding_types(
        subject_context: SubjectContext,
    ) -> list[PerspectiveName]:
        perspectives: list[PerspectiveName] = []
        if len(subject_context.owner_party_ids) > 0:
            perspectives.append("owner")
        if len(subject_context.manager_party_ids) > 0:
            perspectives.append("manager")
        return perspectives

    @staticmethod
    def resolve_effective_party_ids(
        subject_context: SubjectContext,
        perspective: PerspectiveName,
    ) -> list[str]:
        if perspective == "owner":
            return list(subject_context.owner_party_ids)
        return list(subject_context.manager_party_ids)

    @staticmethod
    def _normalize_relation_type(binding: UserPartyBinding) -> str:
        relation_value = binding.relation_type
        if isinstance(relation_value, RelationType):
            return relation_value.value
        return str(relation_value)

    async def _resolve_legacy_default_organization_id(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> str | None:
        try:
            stmt = select(User.default_organization_id).where(User.id == user_id)
            default_org_id = (await db.execute(stmt)).scalar_one_or_none()
        except Exception:
            logger.exception(
                "Failed to resolve legacy default_organization_id for user %s",
                user_id,
            )
            return None

        if default_org_id is None:
            return None

        normalized = str(default_org_id).strip()
        if normalized == "":
            return None
        return normalized

    async def _resolve_legacy_default_organization_party_id(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        organization_id: str,
    ) -> str | None:
        try:
            return await self.party_crud.resolve_organization_party_id(
                db,
                organization_id=organization_id,
            )
        except Exception:
            logger.exception(
                "Failed to resolve legacy default organization party mapping for user %s (organization_id=%s)",
                user_id,
                organization_id,
            )
            return None


__all__ = ["AuthzContextBuilder", "SubjectContext"]
