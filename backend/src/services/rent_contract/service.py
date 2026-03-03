from datetime import date
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import ContractStatus
from src.core.exception_handler import ResourceNotFoundError
from src.crud.asset import asset_crud
from src.crud.ownership import ownership as ownership_crud
from src.crud.party import party_crud
from src.crud.rent_contract import (
    rent_contract as rent_contract_crud,
)
from src.crud.rent_contract import (
    rent_term as rent_term_crud,
)
from src.crud.rent_contract_attachment import (
    rent_contract_attachment_crud,
)
from src.models.ownership import Ownership
from src.models.rent_contract import (
    RentContract,
    RentContractAttachment,
    RentContractHistory,
    RentLedger,
    RentTerm,
)
from src.schemas.rent_contract import RentContractCreate, RentTermCreate

from .ledger_service import RentContractLedgerService
from .lifecycle_service import RentContractLifecycleService
from .statistics_service import RentContractStatisticsService


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def model_to_dict(model: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """
    将 SQLAlchemy 模型或 Pydantic 模型转换为字典

    Args:
        model: SQLAlchemy 或 Pydantic 模型实例
        exclude: 要排除的字段集合

    Returns:
        dict: 模型数据的字典表示
    """
    if model is None:
        return {}

    if hasattr(model, "model_dump"):
        return cast(dict[str, Any], model.model_dump(exclude=exclude))

    if hasattr(model, "__table__"):
        columns = model.__table__.columns.keys()
        return {
            col: getattr(model, col)
            for col in columns
            if exclude is None or col not in exclude
        }

    return cast(dict[str, Any], dict(model))


class RentContractService(
    RentContractLifecycleService,
    RentContractLedgerService,
    RentContractStatisticsService,
):
    """租金合同业务服务"""

    async def get_contract_terms_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentTerm]:
        return await rent_term_crud.get_by_contract_async(db, contract_id=contract_id)

    async def add_contract_term_async(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        term_in: RentTermCreate,
    ) -> RentTerm:
        contract = await rent_contract_crud.get_with_details_async(db, id=contract_id)
        if not contract:
            raise ResourceNotFoundError("合同", contract_id)

        term_data = term_in.model_dump()
        term_data["contract_id"] = contract_id
        term = await rent_term_crud.create(db=db, obj_in=term_data)
        if not term:
            raise ResourceNotFoundError("合同", contract_id)
        return term

    async def get_contract_by_id_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> RentContract | None:
        return await rent_contract_crud.get_async(db, id=contract_id)

    async def get_contract_with_details_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> RentContract | None:
        return await rent_contract_crud.get_with_details_async(db, id=contract_id)

    async def get_contract_page_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        contract_number: str | None = None,
        tenant_name: str | None = None,
        asset_id: str | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_id: str | None = None,  # DEPRECATED alias
        contract_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[RentContract], int]:
        return await rent_contract_crud.get_multi_with_filters_async(
            db=db,
            skip=skip,
            limit=limit,
            contract_number=contract_number,
            tenant_name=tenant_name,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            contract_status=contract_status,
            start_date=start_date,
            end_date=end_date,
        )

    async def delete_contract_by_id_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> None:
        # Keep FK integrity: history table references rent_contracts without ON DELETE CASCADE.
        await db.execute(
            delete(RentContractHistory).where(
                RentContractHistory.contract_id == contract_id
            )
        )
        await rent_contract_crud.remove(db, id=contract_id)

    async def get_assets_by_ids_async(
        self, db: AsyncSession, *, asset_ids: list[str]
    ) -> list[Any]:
        return await asset_crud.get_multi_by_ids_async(
            db=db,
            ids=asset_ids,
            include_relations=False,
        )

    async def get_owner_party_by_id_async(
        self, db: AsyncSession, *, owner_party_id: str
    ) -> Any:
        return await party_crud.get_party(db, owner_party_id)

    async def get_ownership_by_id_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, *, ownership_id: str  # DEPRECATED alias
    ) -> Any:
        return await ownership_crud.get(db, id=ownership_id)  # DEPRECATED alias

    async def resolve_owner_party_scope_by_ownership_id_async(
        self,
        db: AsyncSession,
        *,
        ownership_id: str,
    ) -> str | None:
        normalized_ownership_id = _normalize_optional_str(ownership_id)
        if normalized_ownership_id is None:
            return None

        ownership_obj = await ownership_crud.get(db, id=normalized_ownership_id)
        ownership_code = _normalize_optional_str(
            getattr(ownership_obj, "code", None) if ownership_obj is not None else None
        )
        ownership_name = _normalize_optional_str(
            getattr(ownership_obj, "name", None) if ownership_obj is not None else None
        )

        resolved_party_id = await party_crud.resolve_legal_entity_party_id(
            db,
            ownership_id=normalized_ownership_id,
            ownership_code=ownership_code,
            ownership_name=ownership_name,
        )
        return _normalize_optional_str(resolved_party_id)

    async def resolve_ownership_id_by_owner_party_id_async(
        self,
        db: AsyncSession,
        *,
        owner_party_id: str,
    ) -> str | None:
        normalized_owner_party_id = _normalize_optional_str(owner_party_id)
        if normalized_owner_party_id is None:
            return None

        owner_party = await party_crud.get_party(db, normalized_owner_party_id)
        if owner_party is None:
            return None

        candidate_ownership_ids: list[str] = []
        seen_candidate_ids: set[str] = set()

        async def _append_candidate_if_exists(candidate_id: str | None) -> None:
            normalized_candidate_id = _normalize_optional_str(candidate_id)
            if (
                normalized_candidate_id is None
                or normalized_candidate_id in seen_candidate_ids
            ):
                return
            ownership_obj = await ownership_crud.get(db, id=normalized_candidate_id)
            if ownership_obj is None:
                return
            candidate_ownership_ids.append(normalized_candidate_id)
            seen_candidate_ids.add(normalized_candidate_id)

        async def _query_ownership_ids_by_field(
            *,
            field: str,
            value: str | None,
        ) -> list[str]:
            normalized_value = _normalize_optional_str(value)
            if normalized_value is None:
                return []

            column = Ownership.code if field == "code" else Ownership.name
            stmt = (
                select(Ownership.id)
                .where(
                    column == normalized_value,
                    Ownership.is_active.is_(True),
                    Ownership.data_status == "正常",
                )
                .order_by(Ownership.id)
            )
            rows = (await db.execute(stmt)).scalars().all()
            return [str(ownership_id) for ownership_id in rows if ownership_id is not None]

        # Highest confidence: explicit external reference / ID aliasing.
        await _append_candidate_if_exists(getattr(owner_party, "external_ref", None))
        await _append_candidate_if_exists(normalized_owner_party_id)
        if len(candidate_ownership_ids) == 1:
            return candidate_ownership_ids[0]
        if len(candidate_ownership_ids) > 1:
            return None

        owner_party_code = _normalize_optional_str(getattr(owner_party, "code", None))
        owner_party_name = _normalize_optional_str(getattr(owner_party, "name", None))
        ownership_ids_by_code = await _query_ownership_ids_by_field(
            field="code",
            value=owner_party_code,
        )
        ownership_ids_by_name = await _query_ownership_ids_by_field(
            field="name",
            value=owner_party_name,
        )

        if len(ownership_ids_by_code) > 1:
            return None
        if len(ownership_ids_by_name) > 1:
            return None

        if len(ownership_ids_by_code) == 1 and len(ownership_ids_by_name) == 1:
            if ownership_ids_by_code[0] != ownership_ids_by_name[0]:
                return None
            return ownership_ids_by_code[0]

        if len(ownership_ids_by_code) == 1:
            return ownership_ids_by_code[0]
        if len(ownership_ids_by_name) == 1:
            return ownership_ids_by_name[0]
        return None

    async def get_asset_contracts_async(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        limit: int = 1000,
    ) -> list[RentContract]:
        contracts, _ = await self.get_contract_page_async(
            db=db,
            skip=0,
            limit=limit,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
        )
        return contracts

    async def get_contract_attachments_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentContractAttachment]:
        return await rent_contract_attachment_crud.get_by_contract_async(
            db, contract_id=contract_id
        )

    async def get_contract_attachment_async(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        contract_id: str | None = None,
    ) -> RentContractAttachment | None:
        return await rent_contract_attachment_crud.get_async(
            db,
            attachment_id=attachment_id,
            contract_id=contract_id,
        )

    async def delete_contract_attachment_async(
        self,
        db: AsyncSession,
        *,
        attachment: RentContractAttachment,
    ) -> None:
        await db.delete(attachment)
        await db.commit()

    async def renew_contract_async(
        self,
        db: AsyncSession,
        *,
        original_contract_id: str,
        new_contract_data: RentContractCreate,
        should_transfer_deposit: bool = True,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        original_contract = await self.get_contract_with_details_async(
            db, contract_id=original_contract_id
        )
        if original_contract is None:
            raise ResourceNotFoundError("合同", original_contract_id)

        create_data = new_contract_data.model_copy(deep=True)
        if should_transfer_deposit and create_data.total_deposit is None:
            create_data.total_deposit = original_contract.total_deposit

        new_contract = await self.create_contract_async(db, obj_in=create_data)

        original_contract.contract_status = ContractStatus.TERMINATED.value
        if (
            original_contract.end_date is None
            or original_contract.end_date > new_contract.start_date
        ):
            original_contract.end_date = new_contract.start_date

        db.add(original_contract)
        await db.commit()

        await self._create_history_async(
            db,
            contract_id=original_contract.id,
            change_type="续签",
            change_description=f"合同续签为新合同 {new_contract.id}",
            old_data={"contract_status": ContractStatus.ACTIVE.value},
            new_data={"contract_status": ContractStatus.TERMINATED.value},
            operator=operator,
            operator_id=operator_id,
        )
        return new_contract

    async def terminate_contract_async(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        termination_date: date,
        should_refund_deposit: bool = True,
        deduction_amount: Any = None,
        termination_reason: str | None = None,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        contract = await self.get_contract_by_id_async(db, contract_id=contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)

        old_status = contract.contract_status
        contract.contract_status = ContractStatus.TERMINATED.value
        contract.end_date = termination_date

        notes: list[str] = []
        if termination_reason:
            notes.append(f"终止原因: {termination_reason}")
        notes.append(f"退押金: {'是' if should_refund_deposit else '否'}")
        if deduction_amount is not None:
            notes.append(f"扣减金额: {deduction_amount}")
        termination_note = "；".join(notes)
        if termination_note:
            existing_notes = contract.contract_notes or ""
            contract.contract_notes = (
                f"{existing_notes}\n{termination_note}".strip()
                if existing_notes
                else termination_note
            )

        db.add(contract)
        await db.commit()
        await db.refresh(contract)

        await self._create_history_async(
            db,
            contract_id=contract.id,
            change_type="终止",
            change_description=termination_note or "合同终止",
            old_data={"contract_status": old_status},
            new_data={"contract_status": ContractStatus.TERMINATED.value},
            operator=operator,
            operator_id=operator_id,
        )
        return contract

    async def upload_contract_attachment_async(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        file: UploadFile,
        file_type: str,
        description: str | None = None,
        uploader_id: str | None = None,
        uploader_name: str | None = None,
    ) -> dict[str, Any]:
        contract = await self.get_contract_by_id_async(db, contract_id=contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)

        original_name = (file.filename or "attachment").strip() or "attachment"
        safe_name = Path(original_name).name

        storage_dir = Path("temp_uploads") / "rent_contract_attachments" / contract_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}_{safe_name}"
        storage_path = storage_dir / stored_name

        content = await file.read()
        storage_path.write_bytes(content)

        attachment = RentContractAttachment()
        attachment.contract_id = contract_id
        attachment.file_name = safe_name
        attachment.file_path = str(storage_path)
        attachment.file_size = len(content)
        attachment.mime_type = file.content_type
        attachment.file_type = file_type
        attachment.description = description
        attachment.uploader = uploader_name
        attachment.uploader_id = uploader_id
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)

        return {
            "id": attachment.id,
            "contract_id": attachment.contract_id,
            "file_name": attachment.file_name,
            "file_path": attachment.file_path,
            "file_size": attachment.file_size,
            "mime_type": attachment.mime_type,
            "file_type": attachment.file_type,
            "description": attachment.description,
            "uploader": attachment.uploader,
            "uploader_id": attachment.uploader_id,
            "created_at": attachment.created_at.isoformat()
            if attachment.created_at is not None
            else None,
        }


rent_contract_service = RentContractService()

rent_contract = RentContract
rent_ledger = RentLedger
rent_term = RentTerm

__all__ = [
    "RentContractService",
    "rent_contract_service",
    "model_to_dict",
    "rent_contract",
    "rent_ledger",
    "rent_term",
]
