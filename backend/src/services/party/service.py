"""Party domain service orchestration."""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.party import CRUDParty, party_crud
from ...crud.query_builder import PartyFilter
from ...models.auth import User
from ...models.party import Party, PartyContact, PartyHierarchy, PartyReviewStatus
from ...models.party_review_log import PartyReviewLog
from ...models.user_party_binding import UserPartyBinding
from ...schemas.party import (
    PartyContactCreate,
    PartyCreate,
    PartyUpdate,
    UserPartyBindingCreate,
    UserPartyBindingUpdate,
)
from ...services.party_scope import resolve_user_party_filter
from ...utils.time import utcnow_naive

logger = logging.getLogger(__name__)


class PartyService:
    """Service layer for Party/Hierarchy/Contact operations."""

    def __init__(self, data_access: CRUDParty | None = None) -> None:
        self.party_crud = data_access or party_crud

    async def create_party(self, db: AsyncSession, *, obj_in: PartyCreate) -> Party:
        payload = self._normalize_party_payload(obj_in.model_dump())
        payload.setdefault("review_status", PartyReviewStatus.DRAFT.value)
        payload.setdefault("review_by", None)
        payload.setdefault("reviewed_at", None)
        payload.setdefault("review_reason", None)

        party_type = payload.get("party_type", "")
        code = payload.get("code", "")
        existing = await self.party_crud.get_party_by_type_and_code(
            db, party_type=party_type, code=code
        )
        if existing is not None:
            raise DuplicateResourceError(
                resource_type="主体",
                field="party_type+code",
                value=f"{party_type}/{code}",
            )

        return await self.party_crud.create_party(db, obj_in=payload)

    async def get_party(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> Party | None:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            return None

        resolved_party_filter = await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )
        if resolved_party_filter is None:
            return party

        scoped_party_ids = self._resolve_scoped_party_ids(resolved_party_filter)
        if scoped_party_ids is None:
            return party
        if party.id not in scoped_party_ids:
            return None
        return party

    async def get_parties(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        party_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[Party]:
        resolved_party_filter = await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )
        scoped_party_ids = self._resolve_scoped_party_ids(resolved_party_filter)
        return await self.party_crud.get_parties(
            db,
            skip=skip,
            limit=limit,
            party_type=party_type,
            status=status,
            search=search,
            scoped_party_ids=scoped_party_ids,
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

        if party.review_status in (
            PartyReviewStatus.PENDING,
            PartyReviewStatus.APPROVED,
        ):
            raise OperationNotAllowedError(
                "待审或已审核状态的主体不允许编辑，请先驳回或反审核",
                reason="party_update_forbidden_by_review_status",
            )

        payload = self._normalize_party_payload(obj_in.model_dump(exclude_unset=True))
        return await self.party_crud.update_party(db, db_obj=party, obj_in=payload)

    async def delete_party(self, db: AsyncSession, *, party_id: str) -> bool:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            return False

        if party.review_status in (
            PartyReviewStatus.PENDING,
            PartyReviewStatus.APPROVED,
        ):
            raise OperationNotAllowedError(
                "待审或已审核状态的主体不允许删除",
                reason="party_delete_forbidden_by_review_status",
            )

        await self._assert_no_references(db, party_id=party_id)

        await self.party_crud.delete_party(db, db_obj=party)
        return True

    async def submit_party_review(self, db: AsyncSession, *, party_id: str) -> Party:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)
        if party.review_status != PartyReviewStatus.DRAFT:
            raise OperationNotAllowedError(
                "仅草稿状态的主体允许提审",
                reason="party_review_submit_invalid_status",
            )

        from_status = (
            party.review_status.value
            if isinstance(party.review_status, PartyReviewStatus)
            else str(party.review_status)
        )
        result = await self.party_crud.update_party(
            db,
            db_obj=party,
            obj_in={
                "review_status": PartyReviewStatus.PENDING.value,
                "review_by": None,
                "reviewed_at": None,
                "review_reason": None,
            },
        )
        await self._write_review_log(
            db,
            party_id=party_id,
            action="submit",
            from_status=from_status,
            to_status=PartyReviewStatus.PENDING.value,
        )
        return result

    async def approve_party_review(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        reviewer: str | None = None,
    ) -> Party:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)
        if party.review_status != PartyReviewStatus.PENDING:
            raise OperationNotAllowedError(
                "仅待审状态的主体允许审核通过",
                reason="party_review_approve_invalid_status",
            )

        from_status = (
            party.review_status.value
            if isinstance(party.review_status, PartyReviewStatus)
            else str(party.review_status)
        )
        result = await self.party_crud.update_party(
            db,
            db_obj=party,
            obj_in={
                "review_status": PartyReviewStatus.APPROVED.value,
                "review_by": reviewer,
                "reviewed_at": utcnow_naive(),
                "review_reason": None,
            },
        )
        await self._write_review_log(
            db,
            party_id=party_id,
            action="approve",
            from_status=from_status,
            to_status=PartyReviewStatus.APPROVED.value,
            operator=reviewer,
        )
        return result

    async def reject_party_review(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        reviewer: str | None = None,
        reason: str,
    ) -> Party:
        normalized_reason = str(reason).strip()
        if normalized_reason == "":
            raise OperationNotAllowedError(
                "驳回主体审核时必须填写原因",
                reason="party_review_reject_missing_reason",
            )

        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)
        if party.review_status != PartyReviewStatus.PENDING:
            raise OperationNotAllowedError(
                "仅待审状态的主体允许驳回",
                reason="party_review_reject_invalid_status",
            )

        from_status = (
            party.review_status.value
            if isinstance(party.review_status, PartyReviewStatus)
            else str(party.review_status)
        )
        result = await self.party_crud.update_party(
            db,
            db_obj=party,
            obj_in={
                "review_status": PartyReviewStatus.DRAFT.value,
                "review_by": reviewer,
                "reviewed_at": utcnow_naive(),
                "review_reason": normalized_reason,
            },
        )
        await self._write_review_log(
            db,
            party_id=party_id,
            action="reject",
            from_status=from_status,
            to_status=PartyReviewStatus.DRAFT.value,
            operator=reviewer,
            reason=normalized_reason,
        )
        return result

    async def _assert_no_references(self, db: AsyncSession, *, party_id: str) -> None:
        """Check if this party is referenced by assets or contract groups."""
        from ...models.asset import Asset
        from ...models.contract_group import Contract, ContractGroup
        from ...models.project import Project

        # Check assets referencing this party as owner or manager
        asset_count_stmt = (
            select(func.count())
            .select_from(Asset)
            .where(
                (Asset.owner_party_id == party_id)
                | (Asset.manager_party_id == party_id)
            )
        )
        asset_count = (await db.execute(asset_count_stmt)).scalar() or 0
        if asset_count > 0:
            raise OperationNotAllowedError(
                f"该主体被 {asset_count} 个资产引用，无法删除",
                reason="party_delete_has_asset_references",
            )

        # Check contract groups referencing this party
        cg_count_stmt = (
            select(func.count())
            .select_from(ContractGroup)
            .where(
                (ContractGroup.operator_party_id == party_id)
                | (ContractGroup.owner_party_id == party_id)
            )
        )
        cg_count = (await db.execute(cg_count_stmt)).scalar() or 0
        if cg_count > 0:
            raise OperationNotAllowedError(
                f"该主体被 {cg_count} 个合同组引用，无法删除",
                reason="party_delete_has_contract_group_references",
            )

        # Check contracts referencing this party as lessor or lessee
        contract_count_stmt = (
            select(func.count())
            .select_from(Contract)
            .where(
                (Contract.lessor_party_id == party_id)
                | (Contract.lessee_party_id == party_id)
            )
        )
        contract_count = (await db.execute(contract_count_stmt)).scalar() or 0
        if contract_count > 0:
            raise OperationNotAllowedError(
                f"该主体被 {contract_count} 个租赁合同引用，无法删除",
                reason="party_delete_has_lease_contract_references",
            )

        # Check projects referencing this party as manager
        project_count_stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.manager_party_id == party_id)
        )
        project_count = (await db.execute(project_count_stmt)).scalar() or 0
        if project_count > 0:
            raise OperationNotAllowedError(
                f"该主体被 {project_count} 个项目引用，无法删除",
                reason="party_delete_has_project_references",
            )

    async def _write_review_log(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        action: str,
        from_status: str,
        to_status: str,
        operator: str | None = None,
        reason: str | None = None,
    ) -> None:
        log = PartyReviewLog(
            party_id=party_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            reason=reason,
        )
        db.add(log)
        await db.flush()

    async def assert_parties_approved(
        self,
        db: AsyncSession,
        *,
        party_ids: list[str],
        operation: str,
    ) -> None:
        normalized_party_ids: list[str] = []
        seen_party_ids: set[str] = set()
        for raw_party_id in party_ids:
            normalized_party_id = str(raw_party_id).strip()
            if normalized_party_id == "" or normalized_party_id in seen_party_ids:
                continue
            seen_party_ids.add(normalized_party_id)
            normalized_party_ids.append(normalized_party_id)

        if len(normalized_party_ids) == 0:
            return

        blocked_parties: list[str] = []
        for party_id in normalized_party_ids:
            party = await self.party_crud.get_party(db, party_id=party_id)
            if party is None:
                blocked_parties.append(f"{party_id}(missing)")
                continue
            if party.review_status != PartyReviewStatus.APPROVED:
                party_name = str(getattr(party, "name", party_id)).strip() or party_id
                blocked_parties.append(f"{party_name}({party_id})")

        if len(blocked_parties) > 0:
            raise OperationNotAllowedError(
                f"{operation}前，关联主体必须全部已审核，未通过主体："
                + ", ".join(blocked_parties),
                reason="party_review_not_approved",
                details={"party_ids": normalized_party_ids},
            )

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

    async def get_contacts(
        self, db: AsyncSession, *, party_id: str
    ) -> list[PartyContact]:
        stmt = select(PartyContact).where(PartyContact.party_id == party_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_user_party_binding(
        self,
        db: AsyncSession,
        *,
        obj_in: UserPartyBindingCreate,
    ) -> UserPartyBinding:
        await self._assert_user_exists(db, user_id=obj_in.user_id)
        await self._assert_party_exists(db, party_id=obj_in.party_id)

        payload = obj_in.model_dump(exclude_none=True)
        if "valid_from" not in payload:
            payload["valid_from"] = utcnow_naive()
        self._validate_binding_valid_range(payload)
        relation_type = str(payload["relation_type"])
        is_primary = bool(payload.get("is_primary", False))
        if is_primary:
            await self.party_crud.clear_primary_bindings_for_relation(
                db,
                user_id=obj_in.user_id,
                relation_type=relation_type,
                commit=False,
            )

        binding = await self.party_crud.create_user_party_binding(
            db,
            obj_in=payload,
            commit=True,
        )
        await self._publish_user_scope_invalidation(str(binding.user_id))
        return binding

    async def get_user_party_bindings(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        active_only: bool = True,
    ) -> list[UserPartyBinding]:
        await self._assert_user_exists(db, user_id=user_id)
        return await self.party_crud.get_user_bindings(
            db,
            user_id=user_id,
            active_only=active_only,
        )

    async def update_user_party_binding(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        binding_id: str,
        obj_in: UserPartyBindingUpdate,
    ) -> UserPartyBinding:
        await self._assert_user_exists(db, user_id=user_id)
        binding = await self.party_crud.get_user_binding(
            db,
            user_id=user_id,
            binding_id=binding_id,
        )
        if binding is None:
            raise ResourceNotFoundError("用户主体绑定", binding_id)

        payload = obj_in.model_dump(exclude_unset=True)
        if "party_id" in payload:
            party_id = payload.get("party_id")
            if party_id is None or str(party_id).strip() == "":
                raise OperationNotAllowedError(
                    "party_id 不能为空",
                    reason="user_party_binding_missing_party_id",
                )
            await self._assert_party_exists(db, party_id=str(party_id))

        if "relation_type" in payload and payload["relation_type"] is None:
            raise OperationNotAllowedError(
                "relation_type 不能为空",
                reason="user_party_binding_missing_relation_type",
            )
        if "valid_from" in payload and payload["valid_from"] is None:
            raise OperationNotAllowedError(
                "valid_from 不能为空",
                reason="user_party_binding_missing_valid_from",
            )

        merged_payload = {
            "valid_from": payload.get("valid_from", binding.valid_from),
            "valid_to": payload.get("valid_to", binding.valid_to),
        }
        self._validate_binding_valid_range(merged_payload)

        next_relation_type = str(payload.get("relation_type", binding.relation_type))
        next_is_primary = bool(payload.get("is_primary", binding.is_primary))
        if next_is_primary:
            await self.party_crud.clear_primary_bindings_for_relation(
                db,
                user_id=user_id,
                relation_type=next_relation_type,
                exclude_binding_id=binding_id,
                commit=False,
            )

        updated = await self.party_crud.update_user_party_binding(
            db,
            db_obj=binding,
            obj_in=payload,
            commit=True,
        )
        await self._publish_user_scope_invalidation(user_id)
        return updated

    async def close_user_party_binding(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        binding_id: str,
    ) -> bool:
        await self._assert_user_exists(db, user_id=user_id)
        binding = await self.party_crud.get_user_binding(
            db,
            user_id=user_id,
            binding_id=binding_id,
        )
        if binding is None:
            return False

        now = utcnow_naive()
        if binding.valid_to is not None and binding.valid_to <= now:
            return False

        close_time = now
        if binding.valid_from > now:
            close_time = binding.valid_from

        await self.party_crud.update_user_party_binding(
            db,
            db_obj=binding,
            obj_in={
                "valid_to": close_time,
                "is_primary": False,
            },
            commit=True,
        )
        await self._publish_user_scope_invalidation(user_id)
        return True

    @staticmethod
    async def _publish_user_scope_invalidation(user_id: str) -> None:
        normalized_user_id = str(user_id).strip()
        if normalized_user_id == "":
            return

        try:
            from ..authz import AUTHZ_USER_SCOPE_UPDATED, authz_event_bus

            authz_event_bus.publish_invalidation(
                event_type=AUTHZ_USER_SCOPE_UPDATED,
                payload={"user_id": normalized_user_id},
            )
        except Exception:
            logger.warning(
                "Failed to publish authz user-scope invalidation event for user %s",
                normalized_user_id,
                exc_info=True,
            )

    @staticmethod
    def _resolve_scoped_party_ids(
        party_filter: PartyFilter | None,
    ) -> list[str] | None:
        if party_filter is None:
            return None

        normalized_ids: list[str] = []
        seen_ids: set[str] = set()
        for raw_value in [
            *(party_filter.party_ids or []),
            *(party_filter.owner_party_ids or []),
            *(party_filter.manager_party_ids or []),
        ]:
            normalized = str(raw_value).strip()
            if normalized == "" or normalized in seen_ids:
                continue
            seen_ids.add(normalized)
            normalized_ids.append(normalized)
        return normalized_ids

    @staticmethod
    def _validate_binding_valid_range(payload: dict[str, Any]) -> None:
        valid_from = payload.get("valid_from")
        valid_to = payload.get("valid_to")
        if valid_to is not None and valid_from is not None and valid_to < valid_from:
            raise OperationNotAllowedError(
                "失效时间不能早于生效时间",
                reason="user_party_binding_invalid_valid_range",
            )

    async def _assert_user_exists(self, db: AsyncSession, *, user_id: str) -> None:
        stmt = select(User.id).where(User.id == user_id).limit(1)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if exists is None:
            raise ResourceNotFoundError("用户", user_id)

    async def _assert_party_exists(self, db: AsyncSession, *, party_id: str) -> None:
        party = await self.party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)

    @staticmethod
    def _normalize_party_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "metadata" in payload:
            payload["metadata_json"] = payload.pop("metadata")
        return payload


party_service = PartyService()

__all__ = ["PartyService", "party_service"]
