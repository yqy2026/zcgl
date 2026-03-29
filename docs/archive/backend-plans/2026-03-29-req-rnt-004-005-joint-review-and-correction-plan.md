# REQ-RNT-004/005 Joint Review And Correction Implementation Plan

> **状态**：✅ 已完成 / 已归档（2026-03-29）

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close `REQ-RNT-004` and `REQ-RNT-005` by adding contract-level critical-change detection, group-level joint review enforcement, and a correction-only reversal flow that voids impacted ledger rows and rebuilds the successor contract instead of rolling status backward in place.

**Architecture:** Keep contract review at the `Contract` level and reuse the existing `ContractGroupService` state machine, but add one explicit correction path: approved contracts spawn a successor draft in the same group, draft-vs-predecessor diffs decide whether single submit is allowed, and correction approval reverses the predecessor via audit logs plus ledger voiding before activating the successor. Extend `ContractAuditLog` with structured context so review scope, affected contracts, diff categories, and correction linkage are auditable without inventing a second workflow system.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL/Alembic, pytest, existing contract ledger services, `make check`, docs-lint

---

## Chunk 1: Scope Freeze And File Map

### Scope Decisions

1. `REQ-RNT-004` is implemented as a **policy engine on top of existing submit endpoints**, not a new BPM engine.
2. Strong joint review means: when a draft contract differs from its approved predecessor on critical categories, `POST /contracts/{id}/submit-review` must fail closed and direct callers to `POST /contract-groups/{group_id}/submit-review`.
3. Non-critical text-only changes may still use single-contract submit.
4. Critical categories in this slice are limited to data the current system can actually mutate and verify:
   - parties (`lessor_party_id`, `lessee_party_id`)
   - assets (`contract_assets`)
   - rent-term structure and financials (`start/end`, `monthly_rent`, `management_fee`, `other_fees`)
   - billing cycle / contract detail payment fields
   - contract/group economic rule payloads already exposed in current CRUD
5. `REQ-RNT-005` is implemented as **correction-only reversal**:
   - approved contract cannot be edited in place
   - approved contract must start a correction draft
   - correction approval reverses predecessor semantics by terminating the predecessor, setting `review_status=REVERSED`, voiding eligible future ledger rows, and activating the successor draft
6. Paid / partial ledger rows in the impacted correction window are a hard blocker for automatic correction approval in this slice. The system must fail closed and require manual resolution instead of silently rewriting financial history.
7. No new frontend module is introduced in this slice. Backend API and the existing contract-group UI/service surface may be minimally extended only if needed for smoke verification.

### File Map

**Create**
- `backend/alembic/versions/20260329_req_rnt_004_005_joint_review_and_correction.py`
- `backend/tests/unit/services/contract/test_contract_joint_review.py`
- `backend/tests/unit/services/contract/test_contract_correction_flow.py`

**Modify**
- `backend/src/models/contract_group.py`
- `backend/src/schemas/contract_group.py`
- `backend/src/crud/contract.py`
- `backend/src/crud/contract_group.py`
- `backend/src/services/contract/contract_group_service.py`
- `backend/src/services/contract/ledger_service_v2.py`
- `backend/src/api/v1/contracts/contract_groups.py`
- `backend/tests/unit/services/contract/test_lifecycle_v2.py`
- `backend/tests/unit/services/contract/test_contract_group_service.py`
- `backend/tests/unit/services/contract/test_ledger_recalculate.py`
- `backend/tests/unit/api/v1/test_contract_lifecycle_api.py`
- `docs/requirements-specification.md`
- `docs/features/requirements-appendix-fields.md`
- `docs/plans/README.md`
- `CHANGELOG.md`

### Non-Goals

- Full approval-center workflow or task inbox
- Manual settlement write-off tooling for already paid correction windows
- New standalone contract-detail frontend module

---

## Chunk 2: Audit Contract And Diff Policy

### Task 1: Add Structured Audit Context And Joint-Review Diff Detection

**Files:**
- Modify: `backend/src/models/contract_group.py`
- Modify: `backend/src/schemas/contract_group.py`
- Modify: `backend/src/crud/contract.py`
- Modify: `backend/src/crud/contract_group.py`
- Modify: `backend/src/services/contract/contract_group_service.py`
- Test: `backend/tests/unit/services/contract/test_contract_joint_review.py`
- Test: `backend/tests/unit/services/contract/test_lifecycle_v2.py`

- [ ] **Step 1: Write the failing diff-policy tests**

```python
async def test_submit_review_should_fail_closed_for_critical_change_and_require_group_review():
    with pytest.raises(OperationNotAllowedError, match="合同组联审"):
        await service.submit_review(db, contract_id="draft-correction")


async def test_submit_review_allows_text_only_change_without_group_review():
    contract, warnings = await service.submit_review(db, contract_id="draft-text-only")
    assert contract.status == ContractLifecycleStatus.PENDING_REVIEW
```

- [ ] **Step 2: Run tests to verify red**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_joint_review.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_lifecycle_v2.py -k "submit_review" -q`

Expected: FAIL because no diff-policy or audit context exists yet.

- [ ] **Step 3: Extend audit-log storage**

Add nullable `context JSONB` to `ContractAuditLog` plus Pydantic response field:

```python
context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
```

Store structured metadata such as:
- `review_scope`
- `affected_contract_ids`
- `change_categories`
- `correction_source_contract_id`
- `voided_entry_ids`

- [ ] **Step 4: Add predecessor and diff helpers**

Implement minimal helpers in `ContractGroupService`:
- load predecessor contract via `ContractRelationType.RENEWAL`
- compare draft vs predecessor on mutable business fields
- classify change categories into `critical` vs `non_critical`

- [ ] **Step 5: Enforce mixed review strategy**

Behavior:
- no predecessor: keep current single submit path
- predecessor + only non-critical changes: allow single submit
- predecessor + critical changes: raise `OperationNotAllowedError` instructing caller to use group joint review
- group submit path should aggregate `affected_contract_ids`, `review_scope="joint"`, and `change_categories` into audit context

- [ ] **Step 6: Green targeted tests**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_joint_review.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_lifecycle_v2.py -k "submit_review or group_review" -q`

Expected: PASS

---

## Chunk 3: Correction-Only Reversal Flow

### Task 2: Start Correction Draft Instead Of Editing Approved Contract In Place

**Files:**
- Modify: `backend/src/schemas/contract_group.py`
- Modify: `backend/src/crud/contract.py`
- Modify: `backend/src/crud/contract_group.py`
- Modify: `backend/src/services/contract/contract_group_service.py`
- Modify: `backend/src/api/v1/contracts/contract_groups.py`
- Test: `backend/tests/unit/services/contract/test_contract_correction_flow.py`
- Test: `backend/tests/unit/api/v1/test_contract_lifecycle_api.py`

- [ ] **Step 1: Write the failing correction-start tests**

```python
async def test_start_correction_should_clone_contract_detail_rent_terms_and_assets():
    draft = await service.start_correction(db, contract_id="approved-contract", reason="租金条款调整")
    assert draft.status == ContractLifecycleStatus.DRAFT
    assert draft.review_status == ContractReviewStatus.DRAFT
```

- [ ] **Step 2: Run tests to verify red**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_correction_flow.py -k "start_correction" -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_contract_lifecycle_api.py -k "correction" -q`

Expected: FAIL because correction API does not exist.

- [ ] **Step 3: Add correction request schema and route**

Add:
- `CorrectionStartRequest(reason: str)`
- `POST /api/v1/contracts/{contract_id}/start-correction`

- [ ] **Step 4: Implement correction draft cloning**

Rules:
- source contract must be `APPROVED`
- clone base contract, matching detail row, rent terms, and asset links
- assign new contract number with deterministic correction suffix
- create `ContractRelation(relation_type=RENEWAL)` from source to draft
- append audit log context linking source and draft

- [ ] **Step 5: Guard direct mutation**

Block rent-term create/update/delete and any new contract-update path unless target contract is `DRAFT`. Approved / active contracts must go through correction draft, not in-place edits.

- [ ] **Step 6: Green targeted tests**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_correction_flow.py -k "start_correction or draft_only" -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_contract_lifecycle_api.py -k "start_correction" -q`

Expected: PASS

### Task 3: Reverse Predecessor By Voiding Eligible Ledger Rows And Activating Successor

**Files:**
- Modify: `backend/src/services/contract/ledger_service_v2.py`
- Modify: `backend/src/services/contract/contract_group_service.py`
- Modify: `backend/src/crud/contract_group.py`
- Test: `backend/tests/unit/services/contract/test_contract_correction_flow.py`
- Test: `backend/tests/unit/services/contract/test_ledger_recalculate.py`
- Test: `backend/tests/unit/services/contract/test_lifecycle_v2.py`

- [ ] **Step 1: Write the failing approval handoff tests**

```python
async def test_approve_correction_should_reverse_predecessor_void_future_unpaid_entries_and_activate_successor():
    result = await service.approve(db, contract_id="draft-correction")
    assert result.status == ContractLifecycleStatus.ACTIVE
    assert predecessor.review_status == ContractReviewStatus.REVERSED


async def test_approve_correction_should_block_when_impacted_paid_entries_exist():
    with pytest.raises(OperationNotAllowedError, match="已支付"):
        await service.approve(db, contract_id="draft-correction")
```

- [ ] **Step 2: Run tests to verify red**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_correction_flow.py -k "approve_correction" -q`

Expected: FAIL because approval handoff does not exist.

- [ ] **Step 3: Extract ledger-void helper**

Add service/crud support to:
- find impacted predecessor entries from correction start month
- block on `paid` / `partial`
- mark remaining entries `voided`

- [ ] **Step 4: Wire approval handoff**

When approving a correction draft:
- reverse predecessor semantics:
  - `status -> TERMINATED`
  - `review_status -> REVERSED`
  - `review_reason -> correction reason`
- void eligible predecessor ledger rows in impacted window
- append predecessor audit log with `action="reverse_review"` and context payload
- continue normal successor approval and ledger generation

- [ ] **Step 5: Green targeted tests**

Run:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_correction_flow.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_lifecycle_v2.py -k "approve" -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_recalculate.py -q`

Expected: PASS

---

## Chunk 4: API Surface, SSOT, And Verification

### Task 4: Close API Coverage, Docs, And Verification

**Files:**
- Modify: `backend/src/api/v1/contracts/contract_groups.py`
- Modify: `backend/tests/unit/api/v1/test_contract_lifecycle_api.py`
- Modify: `docs/requirements-specification.md`
- Modify: `docs/features/requirements-appendix-fields.md`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add / update API-layer tests first**

Cover:
- new route path registration
- correction-start endpoint delegates to service
- single submit returns 409/4xx on critical diff requiring group review
- group submit returns structured warnings / review-scope metadata where applicable

- [ ] **Step 2: Wire API contracts**

Add:
- `POST /contracts/{contract_id}/start-correction`
- `GET /contracts/{contract_id}/audit-logs`
- any minimal response fields needed for audit context and correction linkage

- [ ] **Step 3: Update SSOT docs**

Sync:
- `REQ-RNT-004` → ✅ with code evidence
- `REQ-RNT-005` → ✅ with code evidence
- append field rules for audit-log context and correction path
- update active-plan index now, and archive this plan after implementation completes

- [ ] **Step 4: Run verification**

Minimum:
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_joint_review.py tests/unit/services/contract/test_contract_correction_flow.py tests/unit/services/contract/test_lifecycle_v2.py tests/unit/api/v1/test_contract_lifecycle_api.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_ledger_recalculate.py -q`
- `make check`

Expected: PASS

- [ ] **Step 5: Finish branch artifacts**

After verification:
- update `CHANGELOG.md`
- move this plan to `docs/archive/backend-plans/`
- update `docs/plans/README.md`
- commit with conventional message
