"""Build authz subject context from user-party bindings."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.party import CRUDParty, party_crud
from ...models.user_party_binding import RelationType, UserPartyBinding


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

        return SubjectContext(
            user_id=user_id,
            owner_party_ids=sorted(owner_party_ids),
            manager_party_ids=sorted(manager_party_ids),
            headquarters_party_ids=sorted(headquarters_party_ids),
            role_ids=sorted(role_ids or []),
        )

    @staticmethod
    def _normalize_relation_type(binding: UserPartyBinding) -> str:
        relation_value = binding.relation_type
        if isinstance(relation_value, RelationType):
            return relation_value.value
        return str(relation_value)


__all__ = ["AuthzContextBuilder", "SubjectContext"]
