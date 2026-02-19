"""Party domain service orchestration."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from ...crud.party import CRUDParty, party_crud
from ...models.party import Party, PartyContact, PartyHierarchy
from ...models.user_party_binding import UserPartyBinding
from ...schemas.party import (
    PartyContactCreate,
    PartyCreate,
    PartyUpdate,
    UserPartyBindingCreate,
)


class PartyService:
    """Service layer for Party/Hierarchy/Contact operations."""

    def __init__(self, data_access: CRUDParty | None = None) -> None:
        self.party_crud = data_access or party_crud

    async def create_party(self, db: AsyncSession, *, obj_in: PartyCreate) -> Party:
        payload = self._normalize_party_payload(obj_in.model_dump())
        return await self.party_crud.create_party(db, obj_in=payload)

    async def get_party(self, db: AsyncSession, *, party_id: str) -> Party | None:
        return await self.party_crud.get_party(db, party_id=party_id)

    async def get_parties(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        party_type: str | None = None,
        status: str | None = None,
    ) -> list[Party]:
        return await self.party_crud.get_parties(
            db,
            skip=skip,
            limit=limit,
            party_type=party_type,
            status=status,
        )

    async def update_party(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        obj_in: PartyUpdate,
    ) -> Party:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)

        payload = self._normalize_party_payload(obj_in.model_dump(exclude_unset=True))
        return await self.party_crud.update_party(db, db_obj=party, obj_in=payload)

    async def delete_party(self, db: AsyncSession, *, party_id: str) -> bool:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            return False

        await self.party_crud.delete_party(db, db_obj=party)
        return True

    async def add_hierarchy(
        self,
        db: AsyncSession,
        *,
        parent_party_id: str,
        child_party_id: str,
    ) -> PartyHierarchy:
        if parent_party_id == child_party_id:
            raise OperationNotAllowedError(
                "父主体和子主体不能相同",
                reason="party_hierarchy_self_reference",
            )

        parent = await self.party_crud.get_party(db, party_id=parent_party_id)
        if parent is None:
            raise ResourceNotFoundError("主体", parent_party_id)

        child = await self.party_crud.get_party(db, party_id=child_party_id)
        if child is None:
            raise ResourceNotFoundError("主体", child_party_id)

        child_descendants = await self.party_crud.get_descendants(
            db,
            party_id=child_party_id,
            include_self=True,
        )
        if parent_party_id in child_descendants:
            raise OperationNotAllowedError(
                "新增层级会形成环，已拒绝",
                reason="party_hierarchy_cycle",
            )

        return await self.party_crud.add_hierarchy(
            db,
            parent_party_id=parent_party_id,
            child_party_id=child_party_id,
        )

    async def remove_hierarchy(
        self,
        db: AsyncSession,
        *,
        parent_party_id: str,
        child_party_id: str,
    ) -> bool:
        deleted = await self.party_crud.remove_hierarchy(
            db,
            parent_party_id=parent_party_id,
            child_party_id=child_party_id,
        )
        return deleted > 0

    async def get_descendants(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        include_self: bool = False,
    ) -> list[str]:
        return await self.party_crud.get_descendants(
            db,
            party_id=party_id,
            include_self=include_self,
        )

    async def create_contact(
        self,
        db: AsyncSession,
        *,
        obj_in: PartyContactCreate,
    ) -> PartyContact:
        party_id = obj_in.party_id
        if party_id is None or party_id.strip() == "":
            raise OperationNotAllowedError(
                "party_id 不能为空",
                reason="party_contact_missing_party_id",
            )

        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)

        payload = obj_in.model_dump(exclude_none=True)
        return await self.party_crud.create_contact(db, obj_in=payload)

    async def get_contacts(self, db: AsyncSession, *, party_id: str) -> list[PartyContact]:
        stmt = select(PartyContact).where(PartyContact.party_id == party_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_user_party_binding(
        self,
        db: AsyncSession,
        *,
        obj_in: UserPartyBindingCreate,
    ) -> UserPartyBinding:
        payload = obj_in.model_dump(exclude_none=True)
        return await self.party_crud.create_user_party_binding(db, obj_in=payload)

    @staticmethod
    def _normalize_party_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "metadata" in payload:
            payload["metadata_json"] = payload.pop("metadata")
        return payload


party_service = PartyService()

__all__ = ["PartyService", "party_service"]
