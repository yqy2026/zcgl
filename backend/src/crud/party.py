"""CRUD helpers for party-domain entities."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.business_constants import DataStatusValues
from ..models.asset import Asset
from ..models.contract_group import (
    Contract,
    ContractGroup,
    ContractLifecycleStatus,
    GroupRelationType,
)
from ..models.party import Party, PartyContact, PartyType
from ..models.project import Project, ProjectStatus
from ..models.user_party_binding import UserPartyBinding
from .asset_support import SensitiveDataHandler


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDParty:
    """Party and related hierarchy/contact/user-binding CRUD methods."""

    def __init__(self) -> None:
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={"contact_phone"},
        )

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

    async def get_party(
        self, db: AsyncSession, party_id: str, *, include_deleted: bool = False
    ) -> Party | None:
        stmt = select(Party).where(Party.id == party_id)
        if not include_deleted:
            stmt = stmt.where(Party.deleted_at.is_(None))
        return (await db.execute(stmt)).scalars().first()

    async def get_party_for_update(
        self, db: AsyncSession, *, party_id: str
    ) -> Party | None:
        """Read one Party with a row lock for lifecycle changes."""
        stmt = (
            select(Party)
            .where(
                Party.id == party_id,
                Party.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_lifecycle_reference_snapshot(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Return stable IDs and binding versions used by a lifecycle preview."""
        asset_ids = [
            str(value)
            for value in (
                await db.execute(
                    select(Asset.id)
                    .where(
                        or_(
                            Asset.owner_party_id == party_id,
                            Asset.manager_party_id == party_id,
                        )
                    )
                    .order_by(Asset.id)
                )
            )
            .scalars()
            .all()
        ]
        project_ids = [
            str(value)
            for value in (
                await db.execute(
                    select(Project.id)
                    .where(Project.manager_party_id == party_id)
                    .order_by(Project.id)
                )
            )
            .scalars()
            .all()
        ]
        contract_group_ids = [
            str(value)
            for value in (
                await db.execute(
                    select(ContractGroup.contract_group_id)
                    .where(
                        or_(
                            ContractGroup.owner_party_id == party_id,
                            ContractGroup.operator_party_id == party_id,
                        )
                    )
                    .order_by(ContractGroup.contract_group_id)
                )
            )
            .scalars()
            .all()
        ]
        contract_ids = [
            str(value)
            for value in (
                await db.execute(
                    select(Contract.contract_id)
                    .where(
                        or_(
                            Contract.lessor_party_id == party_id,
                            Contract.lessee_party_id == party_id,
                        )
                    )
                    .order_by(Contract.contract_id)
                )
            )
            .scalars()
            .all()
        ]
        binding_rows = list(
            (
                await db.execute(
                    select(UserPartyBinding)
                    .where(
                        UserPartyBinding.party_id == party_id,
                        or_(
                            UserPartyBinding.valid_to.is_(None),
                            UserPartyBinding.valid_to >= now,
                        ),
                    )
                    .order_by(UserPartyBinding.id)
                )
            )
            .scalars()
            .all()
        )
        return {
            "asset_ids": tuple(asset_ids),
            "project_ids": tuple(project_ids),
            "contract_group_ids": tuple(contract_group_ids),
            "contract_ids": tuple(contract_ids),
            "bindings": tuple(
                {
                    "id": str(binding.id),
                    "user_id": str(binding.user_id),
                    "relation_type": binding.relation_type,
                    "valid_from": binding.valid_from,
                    "valid_to": binding.valid_to,
                    "updated_at": binding.updated_at,
                }
                for binding in binding_rows
            ),
        }

    async def get_party_by_type_and_code(
        self,
        db: AsyncSession,
        *,
        party_type: str,
        code: str,
    ) -> Party | None:
        stmt = select(Party).where(
            Party.party_type == party_type,
            Party.code == code,
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_party_by_type_and_name(
        self,
        db: AsyncSession,
        *,
        party_type: str,
        name: str,
    ) -> Party | None:
        stmt = select(Party).where(
            Party.party_type == party_type,
            Party.name == name,
            Party.deleted_at.is_(None),
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_represented_party_id_for_organization(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
    ) -> str | None:
        normalized_organization_id = self._normalize_identifier(organization_id)
        if normalized_organization_id is None:
            return None

        from ..models.organization import Organization

        stmt = (
            select(Organization.represented_party_id.label("party_id"))
            .where(Organization.id == normalized_organization_id)
            .limit(1)
        )
        row = (await db.execute(stmt)).mappings().one_or_none()
        return self._normalize_identifier(
            row.get("party_id") if row is not None else None
        )

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

    @staticmethod
    def _current_business_role_sources(*, as_of: date) -> Any:
        def active_dates(model: Any) -> tuple[Any, Any]:
            return (
                model.effective_from <= as_of,
                or_(model.effective_to.is_(None), model.effective_to >= as_of),
            )

        owner_roles = select(
            Asset.owner_party_id.label("party_id"),
            literal("owner").label("business_role"),
        ).where(
            Asset.owner_party_id.is_not(None),
            Asset.data_status.in_(DataStatusValues.get_active_asset_statuses()),
        )
        operator_roles = select(
            Project.manager_party_id.label("party_id"),
            literal("operator").label("business_role"),
        ).where(
            Project.manager_party_id.is_not(None),
            Project.data_status == DataStatusValues.ASSET_NORMAL,
            Project.status == ProjectStatus.ACTIVE.value,
        )
        terminal_tenant_roles = (
            select(
                Contract.lessee_party_id.label("party_id"),
                literal("terminal_tenant").label("business_role"),
            )
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                Contract.lessee_party_id.is_not(None),
                Contract.group_relation_type.in_(
                    [GroupRelationType.DOWNSTREAM, GroupRelationType.DIRECT_LEASE]
                ),
                Contract.status == ContractLifecycleStatus.ACTIVE,
                Contract.data_status == DataStatusValues.ASSET_NORMAL,
                ContractGroup.data_status == DataStatusValues.ASSET_NORMAL,
                *active_dates(Contract),
                *active_dates(ContractGroup),
            )
        )
        return union_all(owner_roles, operator_roles, terminal_tenant_roles).subquery()

    async def get_parties(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        party_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        business_role: str | None = None,
        scoped_party_ids: list[str] | None = None,
    ) -> list[Party]:
        role_sources = self._current_business_role_sources(as_of=date.today())
        stmt = select(Party).where(Party.deleted_at.is_(None))
        if scoped_party_ids is not None:
            normalized_scope_ids = [
                normalized
                for raw_party_id in scoped_party_ids
                if (normalized := self._normalize_identifier(raw_party_id)) is not None
            ]
            if len(normalized_scope_ids) == 0:
                return []
            stmt = stmt.where(Party.id.in_(normalized_scope_ids))
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
        if business_role is not None:
            stmt = stmt.where(
                Party.id.in_(
                    select(role_sources.c.party_id).where(
                        role_sources.c.business_role == business_role
                    )
                )
            )
        parties = list(
            (await db.execute(stmt.order_by(Party.id).offset(skip).limit(limit)))
            .scalars()
            .all()
        )
        if len(parties) == 0:
            return []

        party_ids = [party.id for party in parties]
        role_rows = (
            await db.execute(
                select(role_sources.c.party_id, role_sources.c.business_role)
                .where(role_sources.c.party_id.in_(party_ids))
                .distinct()
            )
        ).all()
        roles_by_party_id: dict[str, set[str]] = {}
        for party_id, role in role_rows:
            roles_by_party_id.setdefault(str(party_id), set()).add(str(role))

        role_order = {"owner": 0, "operator": 1, "terminal_tenant": 2}
        for party in parties:
            setattr(
                party,
                "business_roles",
                sorted(
                    roles_by_party_id.get(str(party.id), set()),
                    key=lambda role: role_order[role],
                ),
            )
        return parties

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
        db_obj.deleted_at = _utcnow_naive()
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)

    async def create_contact(
        self,
        db: AsyncSession,
        *,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> PartyContact:
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in.copy())
        contact = PartyContact(**encrypted_data)
        db.add(contact)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(contact)
        self._decrypt_contact_object(contact)
        return contact

    async def update_contact(
        self,
        db: AsyncSession,
        *,
        db_obj: PartyContact,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> PartyContact:
        encrypted_data = self._encrypt_contact_update_data(obj_in)
        for key, value in encrypted_data.items():
            setattr(db_obj, key, value)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        self._decrypt_contact_object(db_obj)
        return db_obj

    async def get_contacts(
        self, db: AsyncSession, *, party_id: str
    ) -> list[PartyContact]:
        stmt = select(PartyContact).where(PartyContact.party_id == party_id)
        result = await db.execute(stmt)
        contacts = list(result.scalars().all())
        for contact in contacts:
            self._decrypt_contact_object(contact)
        return contacts

    def _encrypt_contact_update_data(
        self, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        encrypted_data: dict[str, Any] = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    def _decrypt_contact_object(self, contact: PartyContact) -> None:
        value = getattr(contact, "contact_phone", None)
        if value is None:
            return
        decrypted_value = self.sensitive_data_handler.decrypt_field(
            "contact_phone", value
        )
        setattr(contact, "contact_phone", decrypted_value)

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

    async def get_user_binding(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        binding_id: str,
    ) -> UserPartyBinding | None:
        stmt = select(UserPartyBinding).where(
            UserPartyBinding.user_id == user_id,
            UserPartyBinding.id == binding_id,
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_user_binding_for_update(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        binding_id: str,
    ) -> UserPartyBinding | None:
        """Read one binding with a row lock for sensitive scope changes."""
        stmt = (
            select(UserPartyBinding)
            .where(
                UserPartyBinding.user_id == user_id,
                UserPartyBinding.id == binding_id,
            )
            .with_for_update()
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_user_bindings_for_update(
        self,
        db: AsyncSession,
        *,
        binding_ids: tuple[str, ...],
    ) -> list[UserPartyBinding]:
        """Read multiple bindings with deterministic row locks for a batch."""
        if not binding_ids:
            return []
        stmt = (
            select(UserPartyBinding)
            .where(UserPartyBinding.id.in_(binding_ids))
            .order_by(UserPartyBinding.id)
            .with_for_update()
        )
        return list((await db.execute(stmt)).scalars().all())

    async def update_user_party_binding(
        self,
        db: AsyncSession,
        *,
        db_obj: UserPartyBinding,
        obj_in: dict[str, Any],
        commit: bool = True,
    ) -> UserPartyBinding:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

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
                (UserPartyBinding.valid_to.is_(None))
                | (UserPartyBinding.valid_to >= now)
            )

        return list((await db.execute(stmt)).scalars().all())


party_crud = CRUDParty()


__all__ = ["CRUDParty", "party_crud"]
