# REQ-RNT-006 M3 Ledger Operations Implementation Plan

> **状态**：✅ 已完成 / 已归档（2026-03-24）

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining M3 scope of `REQ-RNT-006` by adding ledger export, daily compensation, and agency service-fee ledgers on top of the existing M2 ledger core, while emitting a stable backend data contract that unblocks `REQ-ANA-001`.

**Architecture:** Keep `ContractLedgerEntry` as the rent-ledger source of truth for active lease contracts, and derive `ServiceFeeLedger` from agency-mode direct-lease ledger entries plus the entrust contract ratio in the same `ContractGroup`. Reuse the existing FastAPI + SQLAlchemy service stack, add an idempotent compensation runner plus a manual admin trigger, keep scheduling outside the app process via a maintenance script, and explicitly hand off the daily cron/systemd wiring in deployment docs instead of inventing a new in-process scheduler.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL, existing `ExcelExportService`, existing task/maintenance patterns, `uv run pytest`, `make docs-lint`

---

## Chunk 1: Scope Freeze And File Map

### Scope Decisions

1. `REQ-RNT-006` in this slice means only the remaining **M3** items from [requirements-specification.md](/home/y/projects/zcgl/docs/requirements-specification.md): ledger export, daily compensation, and `ServiceFeeLedger`.
2. No legacy rental frontend resurrection. The current `/rental/ledger` retirement remains unchanged; this slice is backend-first.
3. No in-process scheduler. Daily execution is implemented as an idempotent service plus a maintenance runner and an admin-only manual trigger.
4. `REQ-ANA-001` is only touched at the **data-source** layer in this plan. Existing analytics API shape and frontend consumers stay stable; we only replace placeholder revenue math with ledger-backed inputs.
5. Analytics filtering keeps the current `date_from` / `date_to` contract in this slice. Introducing `year_month_start` / `year_month_end` as analytics API parameters would be a separate `REQ-ANA-001` API-shape change and is explicitly out of scope here.

### File Map

**Create**
- `backend/src/services/contract/ledger_export_service.py`
- `backend/src/services/contract/ledger_compensation_service.py`
- `backend/src/services/contract/service_fee_ledger_service.py`
- `backend/scripts/maintenance/run_ledger_compensation.py`
- `backend/tests/unit/services/contract/test_ledger_export_service.py`
- `backend/tests/unit/services/contract/test_ledger_compensation_service.py`
- `backend/tests/unit/services/contract/test_service_fee_ledger_service.py`
- `backend/alembic/versions/20260324_req_rnt_006_service_fee_ledger_m3.py`

**Modify**
- `backend/src/models/contract_group.py`
- `backend/src/models/__init__.py`
- `backend/src/schemas/contract_group.py`
- `backend/src/crud/contract_group.py`
- `backend/src/services/contract/ledger_service_v2.py`
- `backend/src/services/analytics/analytics_service.py`
- `backend/src/api/v1/contracts/ledger.py`
- `backend/tests/unit/api/v1/test_ledger_api.py`
- `backend/tests/unit/services/analytics/test_analytics_service.py`
- `backend/src/services/contract/ledger_compensation_service.py`
- `docs/guides/deployment-operations.md`
- `docs/requirements-specification.md`
- `docs/features/requirements-appendix-fields.md`
- `scripts/check_field_drift.py`
- `CHANGELOG.md`

### Non-Goals

- Reopening a dedicated rental ledger frontend page.
- Designing a generic scheduler framework.
- Introducing payment reconciliation workflows beyond mirroring source ledger status into `ServiceFeeLedger`.

---

## Chunk 2: Ledger Export

### Task 1: Export Aggregated Rent Ledger Rows

**Files:**
- Create: `backend/src/services/contract/ledger_export_service.py`
- Modify: `backend/src/schemas/contract_group.py`
- Modify: `backend/src/api/v1/contracts/ledger.py`
- Test: `backend/tests/unit/services/contract/test_ledger_export_service.py`
- Test: `backend/tests/unit/api/v1/test_ledger_api.py`

- [ ] **Step 1: Write the failing service test**

```python
async def test_export_rows_should_follow_query_filters_and_column_order():
    result = await ledger_export_service.export_ledger_entries(
        db,
        export_format="csv",
        asset_id="asset-1",
        year_month_start="2026-05",
        year_month_end="2026-05",
    )
    assert result.filename.startswith("ledger_entries_")
    assert "contract_id,year_month,amount_due,paid_amount" in result.content.decode("utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_export_service.py -q`
Expected: FAIL because `ledger_export_service` or export contract does not exist yet.

- [ ] **Step 3: Add export schema contract**

Add minimal request/response helpers to `backend/src/schemas/contract_group.py`:

```python
class LedgerExportQueryParams(BaseModel):
    export_format: Literal["csv", "excel"] = "excel"
    asset_id: str | None = None
    party_id: str | None = None
    contract_id: str | None = None
    year_month_start: str | None = None
    year_month_end: str | None = None
    payment_status: Literal["unpaid", "paid", "overdue", "partial", "voided"] | None = None
    include_voided: bool = False
```

- [ ] **Step 4: Implement the export service**

Add `backend/src/services/contract/ledger_export_service.py` with a small service that:
- reuses `ledger_service_v2.query_ledger_entries(...)`
- normalizes export rows
- streams CSV directly
- reuses `ExcelExportService` workbook-writing style for XLSX output instead of inventing a second spreadsheet helper

```python
class LedgerExportService:
    async def export_ledger_entries(self, db: AsyncSession, params: LedgerExportQueryParams) -> ExportPayload:
        rows = await ledger_service_v2.query_ledger_entries(...)
        ...
```

- [ ] **Step 5: Wire the API endpoint**

Add `GET /api/v1/ledger/entries/export` to `backend/src/api/v1/contracts/ledger.py`, with the same filter surface as `GET /ledger/entries` plus `export_format`.

- [ ] **Step 6: Run targeted tests to green**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_export_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_ledger_api.py -k "export" -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/contract/ledger_export_service.py \
  backend/src/schemas/contract_group.py \
  backend/src/api/v1/contracts/ledger.py \
  backend/tests/unit/services/contract/test_ledger_export_service.py \
  backend/tests/unit/api/v1/test_ledger_api.py
git commit -m "feat(ledger): add aggregated ledger export"
```

### Export Acceptance Notes

- Exported rows must respect exactly the same filters as `GET /ledger/entries`.
- CSV and Excel headers must be stable and documented.
- No async task type is added in this slice; keep export synchronous until a real throughput problem is observed.

---

## Chunk 3: Daily Compensation

### Task 2: Add Idempotent Compensation Service And Manual Trigger

**Files:**
- Create: `backend/src/services/contract/ledger_compensation_service.py`
- Create: `backend/scripts/maintenance/run_ledger_compensation.py`
- Modify: `backend/src/services/contract/ledger_service_v2.py`
- Modify: `backend/src/api/v1/contracts/ledger.py`
- Test: `backend/tests/unit/services/contract/test_ledger_compensation_service.py`
- Test: `backend/tests/unit/api/v1/test_ledger_api.py`

- [ ] **Step 1: Write the failing compensation service test**

```python
async def test_compensation_should_fill_missing_months_for_active_contract():
    result = await ledger_compensation_service.run(db)
    assert result.contracts_scanned == 1
    assert result.contracts_repaired == 1
    assert result.rent_entries_created == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_compensation_service.py -q`
Expected: FAIL because no compensation runner exists.

- [ ] **Step 3: Extract shared ledger expectation helpers**

Refactor `backend/src/services/contract/ledger_service_v2.py` only as much as needed so compensation can reuse month-expansion and recalc logic without copying it:

```python
def compute_expected_year_months(rent_terms: list[ContractRentTerm]) -> list[str]:
    ...
```

- [ ] **Step 4: Implement compensation runner**

Add `backend/src/services/contract/ledger_compensation_service.py` with:
- active contract scan (`ACTIVE`, non-deleted, lease-detail-backed)
- expected vs actual ledger month comparison
- targeted call into `ledger_service_v2.recalculate_ledger(...)` only when drift exists
- this first pass only repairs `ContractLedgerEntry`; agency service-fee resync is added in Task 3
- summary output:

```python
{
    "contracts_scanned": 0,
    "contracts_repaired": 0,
    "rent_entries_created": 0,
    "rent_entries_voided": 0,
    "failures": [],
    "timestamp": "...",
}
```

- [ ] **Step 5: Add manual admin trigger, maintenance runner, and ops handoff**

Add:
- `POST /api/v1/ledger/compensation/run` in `backend/src/api/v1/contracts/ledger.py`
- `backend/scripts/maintenance/run_ledger_compensation.py`
- `docs/guides/deployment-operations.md` entry with cron/systemd example, required env vars, working directory, and rollback note

Pattern reference: `backend/src/services/notification/scheduler.py` and `backend/src/api/v1/system/notifications.py`.

- [ ] **Step 6: Run targeted tests**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_compensation_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_ledger_api.py -k "compensation" -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/contract/ledger_compensation_service.py \
  backend/scripts/maintenance/run_ledger_compensation.py \
  backend/src/services/contract/ledger_service_v2.py \
  backend/src/api/v1/contracts/ledger.py \
  docs/guides/deployment-operations.md \
  backend/tests/unit/services/contract/test_ledger_compensation_service.py \
  backend/tests/unit/api/v1/test_ledger_api.py
git commit -m "feat(ledger): add daily compensation runner"
```

### Compensation Acceptance Notes

- Compensation must be idempotent; a second run over clean data should report zero repairs.
- The app process does not own scheduling. Ops can call the maintenance script daily via cron/systemd.
- The admin trigger is only for smoke tests and manual recovery, not the primary scheduler.
- Task 2 only repairs rent ledgers. Agency service-fee resync is layered in Task 3.

---

## Chunk 4: Agency Service-Fee Ledger

### Task 3: Add `ServiceFeeLedger` As A Derived Read-Only Ledger

**Files:**
- Modify: `backend/src/models/contract_group.py`
- Modify: `backend/src/models/__init__.py`
- Modify: `backend/src/schemas/contract_group.py`
- Modify: `backend/src/crud/contract_group.py`
- Create: `backend/src/services/contract/service_fee_ledger_service.py`
- Modify: `backend/src/services/contract/ledger_service_v2.py`
- Modify: `backend/src/services/contract/ledger_compensation_service.py`
- Create: `backend/alembic/versions/20260324_req_rnt_006_service_fee_ledger_m3.py`
- Test: `backend/tests/unit/services/contract/test_service_fee_ledger_service.py`
- Test: `backend/tests/unit/migration/test_service_fee_ledger_migration.py`

- [ ] **Step 1: Write the failing service-fee ledger tests**

```python
async def test_sync_should_create_service_fee_entries_from_direct_lease_ledgers():
    summary = await service_fee_ledger_service.sync_contract_group(db, group_id="group-1")
    assert summary.created == 3
    assert summary.updated == 0

async def test_sync_should_void_fee_entry_when_source_ledger_is_voided():
    summary = await service_fee_ledger_service.sync_contract_group(db, group_id="group-1")
    assert summary.voided == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_service_fee_ledger_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/migration/test_service_fee_ledger_migration.py -q`

Expected: FAIL because the model/table/service do not exist yet.

- [ ] **Step 3: Add the ORM model and migration**

Append a new derived ledger model to `backend/src/models/contract_group.py`:

```python
class ServiceFeeLedger(Base):
    __tablename__ = "service_fee_ledgers"

    service_fee_entry_id: Mapped[str]
    contract_group_id: Mapped[str]
    agency_contract_id: Mapped[str]
    source_ledger_id: Mapped[str]  # unique
    year_month: Mapped[str]
    amount_due: Mapped[Decimal]
    paid_amount: Mapped[Decimal]
    payment_status: Mapped[str]
    currency_code: Mapped[str]
    service_fee_ratio: Mapped[Decimal]
```

Rules:
- one row per `source_ledger_id`
- source must be a direct-lease contract in an `AGENCY` group
- ratio comes from the single entrust contract in the same group

- [ ] **Step 4: Implement sync service**

Add `backend/src/services/contract/service_fee_ledger_service.py` that:
- resolves the agency group
- finds the unique entrust contract and its `AgencyAgreementDetail.service_fee_ratio`
- reads direct-lease `ContractLedgerEntry` rows
- upserts `ServiceFeeLedger`
- mirrors source `payment_status` and ratio-scaled `paid_amount`
- returns a deterministic sync summary that the compensation runner can merge into its own result payload

- [ ] **Step 5: Hook sync into existing ledger lifecycle**

Minimal integration points:
- after `generate_ledger_on_activation(...)`
- after `recalculate_ledger(...)`
- inside `ledger_compensation_service.run(...)` as a second pass over active `AGENCY` groups, even when rent-ledger month drift is zero

Do not duplicate derivation logic in three places; call the new service from each hook.

- [ ] **Step 6: Run targeted tests**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_service_fee_ledger_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/migration/test_service_fee_ledger_migration.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_compensation_service.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/models/contract_group.py \
  backend/src/models/__init__.py \
  backend/src/schemas/contract_group.py \
  backend/src/crud/contract_group.py \
  backend/src/services/contract/service_fee_ledger_service.py \
  backend/src/services/contract/ledger_compensation_service.py \
  backend/src/services/contract/ledger_service_v2.py \
  backend/alembic/versions/20260324_req_rnt_006_service_fee_ledger_m3.py \
  backend/tests/unit/services/contract/test_service_fee_ledger_service.py \
  backend/tests/unit/migration/test_service_fee_ledger_migration.py
git commit -m "feat(ledger): add agency service fee ledger"
```

### Service-Fee Ledger Acceptance Notes

- This ledger is derived and read-only in M3.
- No separate payment workflow is introduced; status mirrors the source direct-lease ledger entry.
- If an agency group cannot resolve exactly one entrust contract ratio, sync must fail loudly and compensation must report the group in `failures`.
- Compensation must resync service-fee ledgers independently of rent-ledger month drift so ratio changes and missing derived rows are not skipped.

---

## Chunk 5: Analytics Bridge And Documentation

### Task 4: Switch Analytics Revenue Math To Ledger-Backed Sources

**Files:**
- Modify: `backend/src/services/analytics/analytics_service.py`
- Test: `backend/tests/unit/services/analytics/test_analytics_service.py`
- Modify: `docs/requirements-specification.md`
- Modify: `docs/features/requirements-appendix-fields.md`
- Modify: `scripts/check_field_drift.py`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the failing analytics regression test**

```python
async def test_comprehensive_analytics_should_use_ledger_backed_income_fields():
    result = await service.get_comprehensive_analytics(
        filters={"date_from": "2026-05-01", "date_to": "2026-05-31"}
    )
    assert result["total_income"] == 180000.0
    assert result["self_operated_rent_income"] == 120000.0
    assert result["agency_service_income"] == 60000.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_service.py -k "ledger_backed_income_fields" -q`
Expected: FAIL because the service still uses `lease_detail.rent_amount * ratio` approximations.

- [ ] **Step 3: Replace placeholder math with ledger-backed aggregation**

Update `backend/src/services/analytics/analytics_service.py` so that:
- `self_operated_rent_income` comes from downstream lease-group `ContractLedgerEntry.amount_due`
- `agency_service_income` comes from `ServiceFeeLedger.amount_due`
- `total_income` is their sum
- ledger-backed aggregation respects the existing `date_from` / `date_to` filter contract by converting the requested date window into the corresponding ledger month set, instead of introducing new analytics request parameters in this slice
- `customer_entity_count` / `customer_contract_count` logic remains unchanged unless tests prove otherwise

- [ ] **Step 4: Update docs and field drift mapping**

When implementation is green:
- add `ServiceFeeLedger` to `docs/features/requirements-appendix-fields.md`
- extend `scripts/check_field_drift.py` `ENTITY_MODEL_MAP`
- update `docs/requirements-specification.md` code evidence for `REQ-RNT-006`
- only flip `REQ-RNT-006` to `✅` if export, compensation, and service-fee coverage all landed in the same merge

- [ ] **Step 5: Run full targeted verification**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_export_service.py tests/unit/services/contract/test_ledger_compensation_service.py tests/unit/services/contract/test_service_fee_ledger_service.py tests/unit/services/contract/test_ledger_service_v2.py tests/unit/services/analytics/test_analytics_service.py tests/unit/api/v1/test_ledger_api.py tests/unit/migration/test_contract_ledger_entries_migration.py tests/unit/migration/test_service_fee_ledger_migration.py -q`
- `make docs-lint`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/analytics/analytics_service.py \
  backend/tests/unit/services/analytics/test_analytics_service.py \
  docs/requirements-specification.md \
  docs/features/requirements-appendix-fields.md \
  docs/plans/README.md \
  scripts/check_field_drift.py \
  CHANGELOG.md
git commit -m "feat(analytics): consume ledger-backed revenue metrics"
```

---

## Execution Notes

### Manual Verification Checklist

- `GET /api/v1/ledger/entries/export` returns the same row count as `GET /api/v1/ledger/entries` under the same filters.
- Running `backend/scripts/maintenance/run_ledger_compensation.py` twice on unchanged data produces zero second-run repairs.
- Agency-mode direct-lease ledgers generate corresponding `ServiceFeeLedger` rows with the expected ratio and mirrored status.
- Analytics summary now changes when source ledger values change, without changing API field names.

### Risks

- Agency groups with malformed contract topology (missing or duplicate entrust contracts) will block fee-ledger derivation.
- Sync export can become slow for very large result sets; if that happens in practice, split export into a follow-up async task instead of preemptively designing one now.
- `REQ-ANA-001` still needs product sign-off on period semantics if the current `stat_period` UX expects a different time window than ledger `year_month`.

### Downstream Handoff

After this plan lands:
- `REQ-RNT-006` should be eligible to move from `🚧` to `✅`
- `REQ-ANA-001` should be reduced to API/export smoke verification plus any remaining dashboard presentation gaps, not ledger math rework
