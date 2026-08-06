"""Build authz subject context from user-party bindings."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.authz import PerspectiveName
from ..party_scope_resolver import PartyScopeResolver, party_scope_resolver


@dataclass(frozen=True)
class SubjectContext:
    """Resolved subject context for ABAC evaluation."""

    user_id: str
    owner_party_ids: list[str]
    manager_party_ids: list[str]
    role_ids: list[str]
    scope_error_code: str | None = None
    next_transition_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "owner_party_ids": self.owner_party_ids,
            "manager_party_ids": self.manager_party_ids,
            "role_ids": self.role_ids,
            "user_tags": [],
        }


class AuthzContextBuilder:
    """Build ABAC subject context from persistence layer."""

    def __init__(self, resolver: PartyScopeResolver | None = None) -> None:
        self.resolver = resolver or party_scope_resolver

    async def build_subject_context(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        role_ids: list[str] | None = None,
    ) -> SubjectContext:
        scope = await self.resolver.resolve(
            db,
            user_id=user_id,
        )

        return SubjectContext(
            user_id=user_id,
            owner_party_ids=scope.owner_party_ids,
            manager_party_ids=scope.manager_party_ids,
            role_ids=sorted(role_ids or []),
            scope_error_code=scope.error_code,
            next_transition_at=scope.next_transition_at,
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

__all__ = ["AuthzContextBuilder", "SubjectContext"]
