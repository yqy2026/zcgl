"""Exercise real ORM flush, uniqueness and receipt versions in a local database.

SQLite does not verify PostgreSQL row locks or external business-object FKs.
Scope/fact loading and owner locking are stubbed; writes use real repositories.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.models.asset_contract import AssetContractWriteReceipt
from src.models.business_change_event import BusinessChangeEvent
from src.models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)
from src.schemas.management_fee_commands import (
    ManagementFeeConfirmationRequest,
    ManagementFeeSuccessorRequest,
)
from src.services.asset_operations import management_fee_confirmation_service as module
from src.services.asset_operations.management_fee_rules import (
    AgreementFact,
    ObligationFact,
    ReceiptFact,
    project_statement,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class AsyncSessionFacade:
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, row):
        self.session.add(row)

    def add_all(self, rows):
        self.session.add_all(rows)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (
        ManagementFeeStatement,
        ManagementFeeStatementLine,
        AssetContractWriteReceipt,
        BusinessChangeEvent,
    ):
        model.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                ManagementFeeStatement(
                    id="st",
                    owner_party_id="owner",
                    period="2026-10",
                    statement_number="MF-10",
                    stamped_document_id="doc",
                    version=1,
                ),
                ManagementFeeStatement(
                    id="next",
                    owner_party_id="owner",
                    period="2026-11",
                    statement_number="MF-11",
                    version=1,
                ),
            ]
        )
        session.commit()
        projection = project_statement(
            statement_period="2026-10",
            agreements=(AgreementFact("up", Decimal("0.1")),),
            obligations=(
                ObligationFact(
                    "rent",
                    "tm",
                    "up",
                    "2026-10",
                    Decimal("100"),
                    False,
                    "租户",
                    ("unit",),
                ),
            ),
            receipts=(
                ReceiptFact("receipt", "rent", Decimal("40"), date(2026, 10, 15)),
            ),
            already_counted_record_ids=frozenset(),
            confirmed_periods=frozenset(),
            prior_statement_id=None,
            prior_statement_confirmed=False,
            prior_deferred_rows=(),
            deferral_marks={"rent": "下月补齐"},
            today=date(2026, 10, 20),
        )

        async def detail(db, *, statement_id, scope):
            statement = session.get(
                ManagementFeeStatement, statement_id, populate_existing=True
            )
            return Row(
                statement=statement,
                projection=projection if statement.status is None else None,
            )

        monkeypatch.setattr(module.management_fee_query_service, "detail", detail)
        monkeypatch.setattr(
            module.management_fee_statement_repository, "lock_owner", AsyncMock()
        )
        scope = EffectivePartyScope(
            user_id="actor",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner"],
        )
        yield session, AsyncSessionFacade(session), scope
    engine.dispose()


async def test_actual_flush_preserves_confirmation_correction_chain_and_receipt_version(
    database,
):
    session, db, scope = database
    service = module.management_fee_confirmation_service
    confirmed = await service.confirm(
        db,
        statement_id="st",
        request=ManagementFeeConfirmationRequest(expected_version=1),
        actor_id="actor",
        scope=scope,
        idempotency_key="confirm-key",
    )
    assert confirmed.version == 2
    line = session.scalars(select(ManagementFeeStatementLine)).one()
    assert line.owner_received_amount == Decimal("40")
    assert line.deferred_amount == Decimal("60")
    stored = session.get(ManagementFeeStatement, "st")
    assert stored.base_amount == line.owner_received_amount
    assert stored.fee_amount == line.fee_amount
    assert session.get(ManagementFeeStatement, "next").version == 2
    corrected = await service.supersede(
        db,
        statement_id="st",
        request=ManagementFeeSuccessorRequest(expected_version=2, reason="到账有误"),
        actor_id="actor",
        scope=scope,
        idempotency_key="correct-key",
    )
    original = session.get(ManagementFeeStatement, "st")
    successor = session.get(ManagementFeeStatement, corrected.successor_statement_id)
    assert original.status == "superseded"
    assert original.version == corrected.version
    assert original.successor_statement_id == successor.id
    assert successor.predecessor_statement_id == original.id
    assert successor.stamped_document_id is None
    assert successor.base_amount is None
    assert line.owner_received_amount == Decimal("40")
    replay = await service.supersede(
        db,
        statement_id="st",
        request=ManagementFeeSuccessorRequest(expected_version=2, reason="到账有误"),
        actor_id="actor",
        scope=scope,
        idempotency_key="correct-key",
    )
    assert replay.idempotent is True
    assert replay.version == corrected.version
    assert (
        session.scalar(select(func.count()).select_from(AssetContractWriteReceipt)) == 2
    )


async def test_audit_failure_rolls_back_actual_snapshot_rows_and_header(
    database, monkeypatch
):
    session, db, scope = database
    monkeypatch.setattr(
        module.business_change_repository,
        "add",
        AsyncMock(side_effect=RuntimeError("audit unavailable")),
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await module.management_fee_confirmation_service.confirm(
            db,
            statement_id="st",
            request=ManagementFeeConfirmationRequest(expected_version=1),
            actor_id="actor",
            scope=scope,
            idempotency_key="key",
        )
    assert session.get(ManagementFeeStatement, "st").status is None
    assert session.get(ManagementFeeStatement, "st").version == 1
    assert (
        session.scalar(select(func.count()).select_from(ManagementFeeStatementLine))
        == 0
    )
    assert (
        session.scalar(select(func.count()).select_from(AssetContractWriteReceipt)) == 0
    )
