from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ...constants.rent_contract_constants import PaymentStatus
from ...core.exception_handler import BusinessValidationError, ResourceNotFoundError
from ...crud.rent_contract import rent_contract, rent_ledger, rent_term
from ...models.rent_contract import (
    RentContract,
    RentDepositLedger,
    RentLedger,
    ServiceFeeLedger,
)
from ...schemas.rent_contract import (
    GenerateLedgerRequest,
    RentLedgerBatchUpdate,
    RentLedgerUpdate,
)
from .helpers import RentContractHelperMixin


class RentContractLedgerService(RentContractHelperMixin):
    """合同台账相关服务"""

    async def generate_monthly_ledger_async(
        self, db: AsyncSession, *, request: GenerateLedgerRequest
    ) -> list[RentLedger]:
        contract = await rent_contract.get_async(db, id=request.contract_id)
        if not contract:
            raise ResourceNotFoundError("合同", request.contract_id)

        rent_terms = await rent_term.get_by_contract_async(
            db, contract_id=request.contract_id
        )
        if not rent_terms:
            raise BusinessValidationError(
                f"合同没有租金条款: {request.contract_id}",
                field_errors={"rent_terms": ["合同没有租金条款"]},
            )

        if not request.start_year_month:
            start_year_month = contract.start_date.strftime("%Y-%m")
        else:
            start_year_month = request.start_year_month

        if not request.end_year_month:
            end_year_month = contract.end_date.strftime("%Y-%m")
        else:
            end_year_month = request.end_year_month

        months = self._generate_month_range(start_year_month, end_year_month)
        existing_months = await rent_ledger.get_existing_year_months_async(
            db, contract_id=request.contract_id, year_months=months
        )

        created_ledgers: list[RentLedger] = []
        for year_month in months:
            if year_month in existing_months:
                continue

            month_date = datetime.strptime(year_month + "-01", "%Y-%m-%d").date()
            term = self._get_rent_term_for_date(rent_terms, month_date)

            if term:
                due_amount = term.total_monthly_amount or term.monthly_rent
                due_date = self._calculate_due_date(month_date, contract)

                db_ledger = RentLedger()
                db_ledger.contract_id = request.contract_id
                db_ledger.asset_id = None
                db_ledger.owner_party_id = contract.owner_party_id
                db_ledger.year_month = year_month
                db_ledger.due_date = due_date
                db_ledger.due_amount = due_amount
                db_ledger.paid_amount = Decimal("0")
                db_ledger.overdue_amount = Decimal("0")
                db_ledger.payment_status = PaymentStatus.UNPAID
                db.add(db_ledger)
                created_ledgers.append(db_ledger)

        await db.commit()
        return created_ledgers

    async def batch_update_payment_async(
        self, db: AsyncSession, *, request: RentLedgerBatchUpdate
    ) -> list[RentLedger]:
        ledgers = await rent_ledger.get_multi_by_ids_async(
            db,
            ledger_ids=request.ledger_ids,
        )

        for ledger in ledgers:
            if request.payment_status is not None:
                ledger.payment_status = request.payment_status
            if request.payment_date is not None:
                setattr(ledger, "payment_date", request.payment_date)
            if request.payment_method is not None:
                ledger.payment_method = request.payment_method
            if request.payment_reference is not None:
                ledger.payment_reference = request.payment_reference
            if request.notes is not None:
                ledger.notes = request.notes

            if ledger.payment_status in [PaymentStatus.PAID, PaymentStatus.PARTIAL]:
                if ledger.paid_amount < ledger.due_amount:
                    ledger.overdue_amount = ledger.due_amount - ledger.paid_amount
                else:
                    ledger.overdue_amount = Decimal("0")

                await self._calculate_service_fee_for_ledger_async(db, ledger)

        await db.commit()
        return ledgers

    async def update_ledger_async(
        self, db: AsyncSession, *, ledger_id: str, update_data: RentLedgerUpdate
    ) -> RentLedger:
        ledger = await rent_ledger.get(db, id=ledger_id)
        if not ledger:
            raise ResourceNotFoundError("台账记录", ledger_id)

        payload = update_data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(ledger, field, value)

        if ledger.payment_status in [PaymentStatus.PAID, PaymentStatus.PARTIAL]:
            if ledger.paid_amount < ledger.due_amount:
                ledger.overdue_amount = ledger.due_amount - ledger.paid_amount
            else:
                ledger.overdue_amount = Decimal("0")

            await self._calculate_service_fee_for_ledger_async(db, ledger)

        db.add(ledger)
        await db.commit()
        await db.refresh(ledger)
        return ledger

    async def get_rent_ledger_page_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 10,
        contract_id: str | None = None,
        asset_id: str | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_id: str | None = None,  # DEPRECATED alias
        year_month: str | None = None,
        payment_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[RentLedger], int]:
        return await rent_ledger.get_multi_with_filters_async(
            db=db,
            skip=skip,
            limit=limit,
            contract_id=contract_id,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            year_month=year_month,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_rent_ledger_by_id_async(
        self, db: AsyncSession, *, ledger_id: str
    ) -> RentLedger | None:
        return await rent_ledger.get(db, id=ledger_id)

    async def get_contract_ledger_async(
        self, db: AsyncSession, *, contract_id: str, limit: int = 1000
    ) -> list[RentLedger]:
        ledgers, _ = await self.get_rent_ledger_page_async(
            db,
            skip=0,
            limit=limit,
            contract_id=contract_id,
        )
        return ledgers

    async def get_contract_by_id_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> RentContract | None:
        return await rent_contract.get_async(db, id=contract_id)

    async def get_deposit_ledger_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentDepositLedger]:
        return await rent_ledger.get_deposit_ledger_by_contract_async(
            db,
            contract_id=contract_id,
        )

    async def get_service_fee_ledger_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[ServiceFeeLedger]:
        return await rent_ledger.get_service_fee_ledger_by_contract_async(
            db,
            contract_id=contract_id,
        )
