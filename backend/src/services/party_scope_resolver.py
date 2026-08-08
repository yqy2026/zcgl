"""Single source of truth for resolving a user's effective Party scope."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.auth import User
from ..models.organization import Organization
from ..models.party import Party
from ..models.rbac import Role, UserRoleAssignment
from ..models.user_party_binding import UserPartyBinding

ScopeMode = Literal["owner", "manager", "all", "unrestricted", "none"]
ScopeSource = Literal["explicit", "organization", "unrestricted", "none"]
ScopeErrorCode = Literal[
    "PARTY_SCOPE_MISSING",
    "PARTY_SCOPE_INVALID_ORGANIZATION",
    "PARTY_SCOPE_INVALID_PARTY",
    "PARTY_SCOPE_INVALID_BINDING",
]


@dataclass(frozen=True)
class PartyScopeIssue:
    code: str
    node_type: Literal["organization", "party", "binding"]
    safe_label: str
    node_ref: str | None = None


@dataclass(frozen=True)
class EffectivePartyScope:
    user_id: str
    source: ScopeSource
    scope_mode: ScopeMode
    owner_party_ids: list[str] = field(default_factory=list)
    manager_party_ids: list[str] = field(default_factory=list)
    organization_id: str | None = None
    source_organization_id: str | None = None
    next_transition_at: datetime | None = None
    error_code: ScopeErrorCode | None = None
    issues: list[PartyScopeIssue] = field(default_factory=list)

    @property
    def effective_party_ids(self) -> list[str]:
        return sorted(set(self.owner_party_ids + self.manager_party_ids))


class PartyScopeRepositoryProtocol(Protocol):
    async def load_role_names(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[str]: ...

    async def load_user(
        self, db: AsyncSession, *, user_id: str
    ) -> Mapping[str, Any] | None: ...

    async def load_bindings(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[Mapping[str, Any]]: ...

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None: ...


class PartyScopeRepository:
    """Persistence queries used by PartyScopeResolver."""

    async def load_role_names(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                Role.is_active.is_(True),
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > now,
                ),
            )
        )
        return [str(name).strip() for name in (await db.execute(stmt)).scalars().all()]

    async def load_user(
        self, db: AsyncSession, *, user_id: str
    ) -> Mapping[str, Any] | None:
        stmt = select(
            User.id,
            User.account_type,
            User.organization_id,
        ).where(User.id == user_id)
        return (await db.execute(stmt)).mappings().one_or_none()

    async def load_bindings(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[Mapping[str, Any]]:
        stmt = (
            select(
                UserPartyBinding.id,
                UserPartyBinding.party_id,
                UserPartyBinding.relation_type,
                UserPartyBinding.valid_from,
                UserPartyBinding.valid_to,
                Party.status.label("party_status"),
                Party.review_status.label("party_review_status"),
            )
            .outerjoin(Party, Party.id == UserPartyBinding.party_id)
            .where(
                UserPartyBinding.user_id == user_id,
                or_(
                    UserPartyBinding.valid_to.is_(None),
                    UserPartyBinding.valid_to >= now,
                ),
            )
            .order_by(UserPartyBinding.valid_from, UserPartyBinding.created_at)
        )
        return list((await db.execute(stmt)).mappings().all())

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None:
        stmt = (
            select(
                Organization.id,
                Organization.parent_id,
                Organization.status,
                Organization.is_deleted,
                Organization.represented_party_id,
                Organization.represented_party_perspective,
                Party.party_type,
                Party.status.label("party_status"),
                Party.review_status.label("party_review_status"),
            )
            .outerjoin(Party, Party.id == Organization.represented_party_id)
            .where(Organization.id == organization_id)
        )
        return (await db.execute(stmt)).mappings().one_or_none()


class PartyScopeResolver:
    """Resolve effective Party scope with explicit bindings before Organization."""

    _UNRESTRICTED_ROLE_NAMES = {"admin", "system_admin"}

    def __init__(
        self,
        *,
        repository: PartyScopeRepositoryProtocol | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or PartyScopeRepository()
        self.clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))

    async def resolve(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> EffectivePartyScope:
        normalized_user_id = str(user_id).strip()
        now = self.clock()
        role_names = {
            name.strip()
            for name in await self.repository.load_role_names(
                db,
                user_id=normalized_user_id,
                now=now,
            )
            if name.strip() != ""
        }
        if len(role_names.intersection(self._UNRESTRICTED_ROLE_NAMES)) > 0:
            return EffectivePartyScope(
                user_id=normalized_user_id,
                source="unrestricted",
                scope_mode="unrestricted",
            )

        user = await self.repository.load_user(db, user_id=normalized_user_id)
        if user is None:
            return self._denied(
                normalized_user_id,
                error_code="PARTY_SCOPE_MISSING",
                safe_label="用户不存在",
            )

        organization_id = self._normalize(user.get("organization_id"))
        if self._normalize_enum(user.get("account_type")) != "human":
            return self._denied(
                normalized_user_id,
                error_code="PARTY_SCOPE_MISSING",
                safe_label="非人员账号未配置业务主体范围",
                organization_id=organization_id,
            )

        bindings = await self.repository.load_bindings(
            db,
            user_id=normalized_user_id,
            now=now,
        )
        explicit_scope = self._resolve_explicit_bindings(
            user_id=normalized_user_id,
            organization_id=organization_id,
            bindings=bindings,
            now=now,
        )
        if explicit_scope is not None:
            return explicit_scope

        return await self._resolve_organization_scope(
            db,
            user_id=normalized_user_id,
            organization_id=organization_id,
            next_transition_at=self._next_transition(bindings, now=now),
        )

    def _resolve_explicit_bindings(
        self,
        *,
        user_id: str,
        organization_id: str | None,
        bindings: list[Mapping[str, Any]],
        now: datetime,
    ) -> EffectivePartyScope | None:
        current_bindings = [
            binding
            for binding in bindings
            if self._is_current_binding(binding, now=now)
        ]
        if len(current_bindings) == 0:
            return None

        owner_party_ids: set[str] = set()
        manager_party_ids: set[str] = set()
        issues: list[PartyScopeIssue] = []
        for binding in current_bindings:
            binding_id = self._normalize(binding.get("id"))
            party_id = self._normalize(binding.get("party_id"))
            relation_type = self._normalize_enum(binding.get("relation_type"))
            if (
                party_id is None
                or self._normalize_enum(binding.get("party_status")) != "active"
                or self._normalize_enum(binding.get("party_review_status"))
                != "approved"
            ):
                issues.append(
                    PartyScopeIssue(
                        code="PARTY_SCOPE_INVALID_BINDING",
                        node_type="binding",
                        safe_label="显式主体范围目标无效",
                        node_ref=binding_id,
                    )
                )
                continue
            if relation_type == "owner":
                owner_party_ids.add(party_id)
            elif relation_type == "manager":
                manager_party_ids.add(party_id)
            else:
                issues.append(
                    PartyScopeIssue(
                        code="PARTY_SCOPE_INVALID_BINDING",
                        node_type="binding",
                        safe_label="显式主体范围视角无效",
                        node_ref=binding_id,
                    )
                )

        next_transition_at = self._next_transition(bindings, now=now)
        if len(owner_party_ids) == 0 and len(manager_party_ids) == 0:
            return EffectivePartyScope(
                user_id=user_id,
                source="none",
                scope_mode="none",
                organization_id=organization_id,
                next_transition_at=next_transition_at,
                error_code="PARTY_SCOPE_INVALID_BINDING",
                issues=issues,
            )

        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode=self._scope_mode(owner_party_ids, manager_party_ids),
            owner_party_ids=sorted(owner_party_ids),
            manager_party_ids=sorted(manager_party_ids),
            organization_id=organization_id,
            next_transition_at=next_transition_at,
            issues=issues,
        )

    async def _resolve_organization_scope(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        organization_id: str | None,
        next_transition_at: datetime | None,
    ) -> EffectivePartyScope:
        if organization_id is None:
            return self._denied(
                user_id,
                error_code="PARTY_SCOPE_MISSING",
                safe_label="用户未归属组织",
                next_transition_at=next_transition_at,
            )

        current_organization_id: str | None = organization_id
        visited: set[str] = set()
        while current_organization_id is not None:
            if current_organization_id in visited:
                return self._denied(
                    user_id,
                    error_code="PARTY_SCOPE_INVALID_ORGANIZATION",
                    safe_label="组织层级存在循环",
                    organization_id=organization_id,
                    node_ref=current_organization_id,
                    next_transition_at=next_transition_at,
                )
            visited.add(current_organization_id)
            organization = await self.repository.load_organization(
                db,
                organization_id=current_organization_id,
            )
            if (
                organization is None
                or self._normalize_enum(organization.get("status")) != "active"
                or bool(organization.get("is_deleted"))
            ):
                return self._denied(
                    user_id,
                    error_code="PARTY_SCOPE_INVALID_ORGANIZATION",
                    safe_label="组织链无效或已停用",
                    organization_id=organization_id,
                    node_ref=current_organization_id,
                    next_transition_at=next_transition_at,
                )

            represented_party_id = self._normalize(
                organization.get("represented_party_id")
            )
            perspective = self._normalize_enum(
                organization.get("represented_party_perspective")
            )
            if represented_party_id is not None:
                if (
                    perspective not in {"owner", "manager"}
                    or self._normalize_enum(organization.get("party_type"))
                    != "legal_entity"
                    or self._normalize_enum(organization.get("party_status"))
                    != "active"
                    or self._normalize_enum(organization.get("party_review_status"))
                    != "approved"
                ):
                    return self._denied(
                        user_id,
                        error_code="PARTY_SCOPE_INVALID_PARTY",
                        safe_label="组织直接代表主体无效",
                        organization_id=organization_id,
                        node_type="party",
                        node_ref=represented_party_id,
                        next_transition_at=next_transition_at,
                    )
                owner_ids = [represented_party_id] if perspective == "owner" else []
                manager_ids = [represented_party_id] if perspective == "manager" else []
                return EffectivePartyScope(
                    user_id=user_id,
                    source="organization",
                    scope_mode=perspective,
                    owner_party_ids=owner_ids,
                    manager_party_ids=manager_ids,
                    organization_id=organization_id,
                    source_organization_id=current_organization_id,
                    next_transition_at=next_transition_at,
                )
            if perspective is not None:
                return self._denied(
                    user_id,
                    error_code="PARTY_SCOPE_INVALID_ORGANIZATION",
                    safe_label="组织代表主体配置不完整",
                    organization_id=organization_id,
                    node_ref=current_organization_id,
                    next_transition_at=next_transition_at,
                )
            current_organization_id = self._normalize(organization.get("parent_id"))

        return self._denied(
            user_id,
            error_code="PARTY_SCOPE_MISSING",
            safe_label="组织链未配置代表主体",
            organization_id=organization_id,
            next_transition_at=next_transition_at,
        )

    @staticmethod
    def _scope_mode(
        owner_party_ids: set[str], manager_party_ids: set[str]
    ) -> Literal["owner", "manager", "all"]:
        if len(owner_party_ids) > 0 and len(manager_party_ids) > 0:
            return "all"
        if len(owner_party_ids) > 0:
            return "owner"
        return "manager"

    @classmethod
    def _is_current_binding(cls, binding: Mapping[str, Any], *, now: datetime) -> bool:
        valid_from = binding.get("valid_from")
        valid_to = binding.get("valid_to")
        return (
            isinstance(valid_from, datetime)
            and valid_from <= now
            and (
                valid_to is None or (isinstance(valid_to, datetime) and valid_to >= now)
            )
        )

    @classmethod
    def _next_transition(
        cls, bindings: list[Mapping[str, Any]], *, now: datetime
    ) -> datetime | None:
        transitions: list[datetime] = []
        for binding in bindings:
            valid_from = binding.get("valid_from")
            valid_to = binding.get("valid_to")
            if isinstance(valid_from, datetime) and valid_from > now:
                transitions.append(valid_from)
            if isinstance(valid_to, datetime) and valid_to > now:
                transitions.append(valid_to)
        return min(transitions) if len(transitions) > 0 else None

    @staticmethod
    def _normalize(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized if normalized != "" else None

    @classmethod
    def _normalize_enum(cls, value: Any) -> str | None:
        return cls._normalize(getattr(value, "value", value))

    @staticmethod
    def _denied(
        user_id: str,
        *,
        error_code: ScopeErrorCode,
        safe_label: str,
        organization_id: str | None = None,
        node_type: Literal["organization", "party", "binding"] = "organization",
        node_ref: str | None = None,
        next_transition_at: datetime | None = None,
    ) -> EffectivePartyScope:
        return EffectivePartyScope(
            user_id=user_id,
            source="none",
            scope_mode="none",
            organization_id=organization_id,
            next_transition_at=next_transition_at,
            error_code=error_code,
            issues=[
                PartyScopeIssue(
                    code=error_code,
                    node_type=node_type,
                    safe_label=safe_label,
                    node_ref=node_ref,
                )
            ],
        )


party_scope_resolver = PartyScopeResolver()

__all__ = [
    "EffectivePartyScope",
    "PartyScopeIssue",
    "PartyScopeRepository",
    "PartyScopeResolver",
    "party_scope_resolver",
]
