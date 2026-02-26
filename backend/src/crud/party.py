"""CRUD helpers for party-domain entities."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.party import Party, PartyContact, PartyHierarchy, PartyType
from ..models.user_party_binding import UserPartyBinding


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDParty:
    """Party and related hierarchy/contact/user-binding CRUD methods."""

    @staticmethod
    def _normalize_identifier(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if normalized == "":
            return None
        return normalized

    async def create_party(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> Party:
        party = Party(**obj_in)
        db.add(party)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(party)
        return party

    async def get_party(self, db: AsyncSession, party_id: str) -> Party | None:
        stmt = select(Party).where(Party.id == party_id)
        return (await db.execute(stmt)).scalars().first()

    async def resolve_organization_party_id(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        organization_code: str | None = None,
        organization_name: str | None = None,
    ) -> str | None:
        normalized_organization_id = self._normalize_identifier(organization_id)
        if normalized_organization_id is None:
            return None

        for condition in (
            Party.id == normalized_organization_id,
            Party.external_ref == normalized_organization_id,
        ):
            stmt = (
                select(Party.id.label("party_id"))
                .where(
                    Party.party_type == PartyType.ORGANIZATION.value,
                    condition,
                )
                .order_by(Party.id)
                .limit(1)
            )
            row = (await db.execute(stmt)).mappings().one_or_none()
            resolved_party_id = self._normalize_identifier(
                row.get("party_id") if row is not None else None
            )
            if resolved_party_id is not None:
                return resolved_party_id

        normalized_code = self._normalize_identifier(organization_code)
        normalized_name = self._normalize_identifier(organization_name)
        if normalized_code is None or normalized_name is None:
            from ..models.organization import Organization

            org_stmt = (
                select(
                    Organization.code.label("organization_code"),
                    Organization.name.label("organization_name"),
                )
                .where(Organization.id == normalized_organization_id)
                .limit(1)
            )
            org_row = (await db.execute(org_stmt)).mappings().one_or_none()
            if org_row is not None:
                if normalized_code is None:
                    normalized_code = self._normalize_identifier(
                        org_row.get("organization_code")
                    )
                if normalized_name is None:
                    normalized_name = self._normalize_identifier(
                        org_row.get("organization_name")
                    )

        code_or_name_conditions = []
        if normalized_code is not None:
            code_or_name_conditions.append(Party.code == normalized_code)
        if normalized_name is not None:
            code_or_name_conditions.append(Party.name == normalized_name)

        for condition in code_or_name_conditions:
            stmt = (
                select(Party.id.label("party_id"))
                .where(
                    Party.party_type == PartyType.ORGANIZATION.value,
                    condition,
                )
                .order_by(Party.id)
                .limit(1)
            )
            row = (await db.execute(stmt)).mappings().one_or_none()
            resolved_party_id = self._normalize_identifier(
                row.get("party_id") if row is not None else None
            )
            if resolved_party_id is not None:
                return resolved_party_id

        return None

    async def resolve_legal_entity_party_id(
        self,
        db: AsyncSession,
        *,
        ownership_id: str,
        ownership_code: str | None = None,
        ownership_name: str | None = None,
    ) -> str | None:
        normalized_ownership_id = self._normalize_identifier(ownership_id)
        if normalized_ownership_id is None:
            return None

        lookup_conditions = [
            Party.id == normalized_ownership_id,
            Party.external_ref == normalized_ownership_id,
        ]

        normalized_code = self._normalize_identifier(ownership_code)
        if normalized_code is not None:
            lookup_conditions.append(Party.code == normalized_code)

        normalized_name = self._normalize_identifier(ownership_name)
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
            resolved_party_id = self._normalize_identifier(
                row.get("party_id") if row is not None else None
            )
            if resolved_party_id is not None:
                return resolved_party_id

        return None

    async def get_parties(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        party_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Party]:
        stmt = select(Party)
        if party_type is not None:
            stmt = stmt.where(Party.party_type == party_type)
        if status is not None:
            stmt = stmt.where(Party.status == status)
        if search is not None and search.strip() != "":
            keyword = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Party.name.ilike(keyword),
                    Party.code.ilike(keyword),
                )
            )
        stmt = stmt.offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def update_party(
        self,
        db: AsyncSession,
        *,
        db_obj: Party,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> Party:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_party(
        self,
        db: AsyncSession,
        *,
        db_obj: Party,
        commit: bool = True,
    ) -> None:
        await db.delete(db_obj)
        if commit:
            await db.commit()
        else:
            await db.flush()

    async def add_hierarchy(
        self,
        db: AsyncSession,
        *,
        parent_party_id: str,
        child_party_id: str,
        commit: bool = True,
    ) -> PartyHierarchy:
        relation = PartyHierarchy(
            parent_party_id=parent_party_id,
            child_party_id=child_party_id,
        )
        db.add(relation)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(relation)
        return relation

    async def remove_hierarchy(
        self,
        db: AsyncSession,
        *,
        parent_party_id: str,
        child_party_id: str,
        commit: bool = True,
    ) -> int:
        stmt = delete(PartyHierarchy).where(
            PartyHierarchy.parent_party_id == parent_party_id,
            PartyHierarchy.child_party_id == child_party_id,
        )
        result = await db.execute(stmt)
        if commit:
            await db.commit()
        else:
            await db.flush()
        return int(result.rowcount or 0)

    async def get_descendants(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        include_self: bool = False,
    ) -> list[str]:
        result = await db.execute(
            text(
                """
                WITH RECURSIVE descendants AS (
                    SELECT ph.child_party_id AS party_id
                    FROM party_hierarchy ph
                    WHERE ph.parent_party_id = :party_id

                    UNION ALL

                    SELECT ph2.child_party_id AS party_id
                    FROM party_hierarchy ph2
                    JOIN descendants d ON ph2.parent_party_id = d.party_id
                )
                SELECT party_id FROM descendants
                """
            ),
            {"party_id": party_id},
        )
        descendants = [str(row[0]) for row in result.fetchall()]
        if include_self:
            return [party_id, *descendants]
        return descendants

    async def create_contact(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> PartyContact:
        contact = PartyContact(**obj_in)
        db.add(contact)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(contact)
        return contact

    async def update_contact(
        self,
        db: AsyncSession,
        *,
        db_obj: PartyContact,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> PartyContact:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_contact(
        self,
        db: AsyncSession,
        *,
        db_obj: PartyContact,
        commit: bool = True,
    ) -> None:
        await db.delete(db_obj)
        if commit:
            await db.commit()
        else:
            await db.flush()

    async def create_user_party_binding(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> UserPartyBinding:
        binding = UserPartyBinding(**obj_in)
        db.add(binding)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(binding)
        return binding

    async def get_user_bindings(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        active_only: bool = True,
        relation_type: str | None = None,
        at_time: datetime | None = None,
    ) -> list[UserPartyBinding]:
        stmt = select(UserPartyBinding).where(UserPartyBinding.user_id == user_id)

        if relation_type is not None:
            stmt = stmt.where(UserPartyBinding.relation_type == relation_type)

        if active_only:
            now = at_time or _utcnow_naive()
            stmt = stmt.where(UserPartyBinding.valid_from <= now).where(
                (UserPartyBinding.valid_to.is_(None)) | (UserPartyBinding.valid_to >= now)
            )

        return list((await db.execute(stmt)).scalars().all())


party_crud = CRUDParty()


__all__ = ["CRUDParty", "party_crud"]
