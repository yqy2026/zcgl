"""管理费对账单纯函数投影的单元测试（V2-T17 / T20 意图）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.services.asset_operations.management_fee_rules import (
    AgreementFact,
    ManagementFeeStatementProjection,
    ObligationFact,
    PriorDeferredRow,
    ReceiptFact,
    deadline_for,
    project_statement,
)

pytestmark = pytest.mark.unit


def agreement(contract_id: str = "up-1", rate: str = "0.10") -> AgreementFact:
    return AgreementFact(upstream_contract_id=contract_id, fee_rate=Decimal(rate))


def obligation(
    entry_id: str = "ob-1",
    terminal_id: str = "tm-1",
    upstream_id: str | None = "up-1",
    period: str = "2026-10",
    due: str = "10000.00",
    voided: bool = False,
    tenant: str = "租户甲",
    units: tuple[str, ...] = ("unit-a",),
) -> ObligationFact:
    return ObligationFact(
        rent_ledger_entry_id=entry_id,
        terminal_contract_id=terminal_id,
        upstream_contract_id=upstream_id,
        period=period,
        due_amount=Decimal(due),
        voided=voided,
        tenant_name=tenant,
        asset_unit_ids=units,
    )


def receipt(
    record_id: str = "rc-1",
    entry_id: str = "ob-1",
    amount: str = "4000.00",
    occurred: date = date(2026, 10, 20),
    reversed_: bool = False,
) -> ReceiptFact:
    return ReceiptFact(
        record_id=record_id,
        rent_ledger_entry_id=entry_id,
        amount=Decimal(amount),
        occurred_on=occurred,
        reversed_=reversed_,
    )


def project(**changes: object) -> ManagementFeeStatementProjection:
    base: dict[str, object] = {
        "statement_period": "2026-10",
        "agreements": (agreement(),),
        "obligations": (obligation(),),
        "receipts": (receipt(),),
        "already_counted_record_ids": frozenset(),
        "confirmed_periods": frozenset(),
        "prior_statement_id": None,
        "prior_statement_confirmed": False,
        "prior_deferred_rows": (),
        "deferral_marks": {},
        "today": date(2026, 10, 15),
    }
    base.update(changes)
    return project_statement(**base)  # type: ignore[arg-type]


def test_deadline_is_last_day_of_next_month() -> None:
    assert deadline_for("2026-10") == date(2026, 11, 30)
    assert deadline_for("2026-12") == date(2027, 1, 31)


def test_current_line_counts_only_uncounted_valid_receipts() -> None:
    result = project(
        receipts=(
            receipt("rc-1", amount="4000.00"),
            receipt("rc-2", amount="3000.00", reversed_=True),
            receipt("rc-3", amount="500.00"),
        ),
        already_counted_record_ids=frozenset({"rc-3"}),
    )
    (line,) = result.lines
    assert line.line_kind == "current"
    assert line.scheduled_rent == Decimal("9500.00")
    assert line.owner_received_amount == Decimal("4000.00")
    assert line.counted_record_ids == ("rc-1",)
    assert line.received_on == date(2026, 10, 20)
    assert line.fee_rate == Decimal("0.10")
    assert line.fee_amount == Decimal("400.00")
    assert result.base_amount == Decimal("4000.00")
    assert result.fee_amount == Decimal("400.00")


def test_voided_and_unbound_obligations_are_excluded_with_warning() -> None:
    result = project(
        obligations=(
            obligation("ob-void", voided=True),
            obligation("ob-missing-upstream", upstream_id=None),
            obligation("ob-ok"),
        ),
        receipts=(),
    )
    assert [line.rent_ledger_entry_id for line in result.lines] == ["ob-ok"]
    assert result.upstream_missing_entry_ids == ("ob-missing-upstream",)
    assert result.upstream_missing_warning == "UPSTREAM_CONTRACT_MISSING"


def test_status_collecting_until_every_line_processed() -> None:
    collecting = project(receipts=(receipt("rc-1", amount="4000.00"),))
    assert collecting.status == "collecting"

    paid_off = project(receipts=(receipt("rc-1", amount="10000.00"),))
    assert paid_off.status == "pending_stamp"
    (line,) = paid_off.lines
    assert line.processed is True
    assert line.deferred_amount == Decimal("0")


def test_marked_deferral_processes_line_and_defers_balance() -> None:
    result = project(
        receipts=(receipt("rc-1", amount="4000.00"),),
        deferral_marks={"ob-1": "租户申请下月补齐"},
    )
    (line,) = result.lines
    assert line.processed is True
    assert line.deferred_amount == Decimal("6000.00")
    assert line.deferral_reason == "租户申请下月补齐"
    assert result.status == "pending_stamp"


def test_past_deadline_auto_defers_remaining_balance() -> None:
    result = project(
        receipts=(receipt("rc-1", amount="4000.00"),),
        today=date(2026, 12, 1),
    )
    (line,) = result.lines
    assert line.processed is True
    assert line.deferred_amount == Decimal("6000.00")
    assert line.deferral_reason == "截止日未到账，自动顺延"
    assert result.status == "pending_stamp"


def test_prior_deferred_rows_carry_in_only_when_prior_confirmed() -> None:
    carried = project(
        prior_statement_id="st-9",
        prior_statement_confirmed=True,
        prior_deferred_rows=(
            PriorDeferredRow(
                rent_ledger_entry_id="ob-1",
                prior_statement_id="st-9",
                deferred_amount=Decimal("6000.00"),
            ),
        ),
        obligations=(obligation(),),
        receipts=(receipt("rc-prior", amount="4000.00"),),
        already_counted_record_ids=frozenset({"rc-prior"}),
    )
    (line,) = carried.lines
    assert line.line_kind == "carried"
    assert line.carried_from_statement_id == "st-9"
    assert line.scheduled_rent == Decimal("6000.00")

    waiting = project(
        prior_statement_id="st-9",
        prior_statement_confirmed=False,
        prior_deferred_rows=(
            PriorDeferredRow(
                rent_ledger_entry_id="ob-1",
                prior_statement_id="st-9",
                deferred_amount=Decimal("6000.00"),
            ),
        ),
        obligations=(),
        receipts=(),
    )
    assert waiting.lines == ()
    assert waiting.carried_waiting_hint is True


def test_late_obligation_from_confirmed_period_is_carried() -> None:
    result = project(
        obligations=(obligation("ob-late", period="2026-09"),),
        confirmed_periods=frozenset({"2026-09"}),
        receipts=(),
    )
    (line,) = result.lines
    assert line.line_kind == "carried"
    assert line.carried_from_statement_id is None
    assert line.rent_period == "2026-09"


def test_late_obligation_deduplicates_prior_carried_row() -> None:
    result = project(
        obligations=(obligation("ob-late", period="2026-09"),),
        confirmed_periods=frozenset({"2026-09"}),
        prior_statement_id="st-9",
        prior_statement_confirmed=True,
        prior_deferred_rows=(
            PriorDeferredRow(
                rent_ledger_entry_id="ob-late",
                prior_statement_id="st-9",
                deferred_amount=Decimal("10000.00"),
            ),
        ),
        receipts=(),
    )
    (line,) = result.lines
    assert line.carried_from_statement_id == "st-9"
    assert line.scheduled_rent == Decimal("10000.00")


def test_line_fee_rounded_half_up_per_line_then_summed() -> None:
    result = project(
        agreements=(agreement("up-1", "0.333333"),),
        obligations=(obligation("ob-1"), obligation("ob-2", "ob-2")),
        receipts=(
            receipt("rc-1", "ob-1", "3333.00"),
            receipt("rc-2", "ob-2", "3333.00"),
        ),
    )
    fees = {line.rent_ledger_entry_id: line.fee_amount for line in result.lines}
    assert fees["ob-1"] == Decimal("1111.00")
    assert fees["ob-2"] == Decimal("1111.00")
    assert result.fee_amount == Decimal("2222.00")
    assert result.base_amount == Decimal("6666.00")


def test_statement_number_and_period_passthrough() -> None:
    result = project()
    assert result.statement_period == "2026-10"


def test_deadline_day_still_requires_processing() -> None:
    assert project(today=date(2026, 11, 30)).status == "collecting"
    assert deadline_for("2028-01") == date(2028, 2, 29)


def test_previously_listed_obligation_does_not_reappear_as_late() -> None:
    result = project(
        obligations=(obligation(period="2026-09"),),
        confirmed_periods=frozenset({"2026-09"}),
        already_listed_entry_ids=frozenset({"ob-1"}),
    )
    assert result.lines == ()
    assert result.base_amount == Decimal("0")


def test_carried_balance_uses_current_obligation_and_excludes_counted_receipts() -> (
    None
):
    result = project(
        obligations=(obligation(period="2026-09", due="12000.00"),),
        prior_statement_id="st-9",
        prior_statement_confirmed=True,
        prior_deferred_rows=(PriorDeferredRow("ob-1", "st-9", Decimal("6000.00")),),
        already_listed_entry_ids=frozenset({"ob-1"}),
        already_counted_record_ids=frozenset({"old"}),
        receipts=(receipt("old", amount="4000.00"), receipt("new", amount="2000.00")),
    )
    (line,) = result.lines
    assert line.scheduled_rent == Decimal("8000.00")
    assert line.owner_received_amount == Decimal("2000.00")
    assert line.deferred_amount == Decimal("6000.00")
    assert line.fee_amount == Decimal("200.00")
    assert line.counted_record_ids == ("new",)


def test_future_and_unconfirmed_past_periods_are_not_carried() -> None:
    assert project(obligations=(obligation(period="2026-11"),)).lines == ()
    assert project(obligations=(obligation(period="2026-09"),)).lines == ()


@pytest.mark.parametrize("reason", ["", "  "])
def test_empty_deferral_reason_is_rejected(reason: str) -> None:
    with pytest.raises(ValueError, match="reason"):
        project(deferral_marks={"ob-1": reason})


def test_exact_half_cent_rounds_up_per_line_before_sum() -> None:
    result = project(
        agreements=(agreement(rate="0.1"),),
        obligations=(obligation("a"), obligation("b")),
        receipts=(receipt("ra", "a", "0.05"), receipt("rb", "b", "0.05")),
    )
    assert result.fee_amount == Decimal("0.02")


def test_multiple_agreements_use_their_own_rates_and_latest_valid_receipt_date() -> (
    None
):
    result = project(
        agreements=(agreement("up-1", "0.10"), agreement("up-2", "0")),
        obligations=(obligation("a"), obligation("b", upstream_id="up-2")),
        receipts=(
            receipt("ra", "a", "100", date(2026, 10, 10)),
            receipt("rb", "a", "200", date(2026, 11, 1)),
            receipt("reversed", "a", "300", date(2026, 11, 5), reversed_=True),
            receipt("rc", "b", "500"),
        ),
    )
    assert result.upstream_contract_ids == ("up-1", "up-2")
    assert result.base_amount == Decimal("800")
    assert result.fee_amount == Decimal("30.00")
    assert result.lines[0].received_on == date(2026, 11, 1)


def test_voided_carried_row_is_excluded() -> None:
    result = project(
        obligations=(obligation(period="2026-09", voided=True),),
        prior_statement_id="st-9",
        prior_statement_confirmed=True,
        prior_deferred_rows=(PriorDeferredRow("ob-1", "st-9", Decimal("6000")),),
    )
    assert result.lines == ()


def test_full_receipt_clears_deferral_balance_and_reason() -> None:
    result = project(
        receipts=(receipt(amount="10000"),),
        deferral_marks={"ob-1": "下月补齐"},
    )
    (line,) = result.lines
    assert line.processed is True
    assert line.deferred_amount == Decimal("0")
    assert line.deferral_reason is None
