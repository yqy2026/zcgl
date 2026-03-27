# REQ-ANA-001 Export Closure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** ✅ Completed on 2026-03-25

**Goal:** Close `REQ-ANA-001` by making `/api/v1/analytics/export` the single export authority, returning real CSV/XLSX output with ANA-001 metrics, and routing both frontend analytics entry points through that same backend download path.

**Architecture:** Add one backend analytics-export mapper that converts comprehensive analytics data into a shared tabular export payload, then have both CSV and XLSX generation consume that payload instead of ad-hoc route logic. On the frontend, consolidate download behavior in `analyticsService` so `useAssetAnalytics` and `AnalyticsDashboard` stop using different export paths and instead share the same backend-driven flow.

**Tech Stack:** FastAPI, Python 3.12, pandas/openpyxl Excel export service, Vitest, React Query, React 19, TypeScript 5

---

## Chunk 1: File Structure

### Backend ownership

- Create: `backend/src/services/analytics/analytics_export_service.py`
  Responsibility: Build a stable analytics export payload from comprehensive analytics data and render CSV text rows that include ANA-001 fields and `metrics_version`.
- Create: `backend/tests/unit/services/analytics/test_analytics_export_service.py`
  Responsibility: Lock section order, ANA-001 row labels, blank-version behavior, and CSV text generation.
- Modify: `backend/src/api/v1/analytics/analytics.py`
  Responsibility: Delegate `/api/v1/analytics/export` to the export service and stop returning JSON text as CSV.
- Modify: `backend/src/services/excel/excel_export_service.py`
  Responsibility: Accept structured analytics export rows so XLSX output shares the same mapping as CSV.
- Modify: `backend/tests/unit/api/v1/test_analytics.py`
  Responsibility: Lock route-level export contract, especially CSV payload shape and PDF unsupported response.

### Frontend ownership

- Modify: `frontend/src/services/analyticsService.ts`
  Responsibility: Be the single frontend gateway for analytics export, including consistent filter-to-query translation and shared download helper.
- Modify: `frontend/src/services/__tests__/analyticsService.test.ts`
  Responsibility: Lock `exportAnalyticsReport()` request params and any new download helper behavior.
- Modify: `frontend/src/hooks/useAssetAnalytics.ts`
  Responsibility: Stop local Excel generation and use backend export/download flow.
- Modify: `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
  Responsibility: Lock that asset analytics export no longer calls `exportAnalyticsData` and now delegates to `analyticsService`.
- Modify: `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
  Responsibility: Reuse the same download path and status messaging as asset analytics.
- Modify: `frontend/src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx`
  Responsibility: Lock dashboard export delegation to the shared analytics service method.

### Documentation ownership

- Modify: `docs/requirements-specification.md`
  Responsibility: Move `REQ-ANA-001` evidence from generic “已实现部分” wording to explicit export-closure evidence once implementation is complete.
- Modify: `CHANGELOG.md`
  Responsibility: Record the implementation and verification commands.
- Modify: `docs/plans/README.md`
  Responsibility: Mark this active plan as completed and archive it after implementation finishes.

## Chunk 2: Backend Export Contract

### Task 1: Add backend export mapper service

**Files:**
- Create: `backend/src/services/analytics/analytics_export_service.py`
- Test: `backend/tests/unit/services/analytics/test_analytics_export_service.py`

- [ ] **Step 1: Write the failing mapper test**

```python
def test_build_summary_rows_should_include_req_ana_001_metrics_in_fixed_order():
    service = AnalyticsExportService()

    rows = service.build_summary_rows(
        {
            "total_assets": 1,
            "area_summary": {"total_area": 100.0, "total_rentable_area": 80.0},
            "occupancy_rate": {"overall_rate": 50.0},
            "financial_summary": {"total_annual_income": 1000.0},
            "total_income": 1200.0,
            "self_operated_rent_income": 1000.0,
            "agency_service_income": 200.0,
            "customer_entity_count": 2,
            "customer_contract_count": 3,
            "metrics_version": "req-ana-001-v1",
        }
    )

    assert [row["metric"] for row in rows].count("总收入（经营口径）") == 1
    assert rows[-1]["metric"] == "口径版本"
    assert rows[-1]["value"] == "req-ana-001-v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py -q`

Expected: FAIL because `AnalyticsExportService` and its row builder do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement `AnalyticsExportService` with focused methods:

- `build_summary_rows(analytics_data)`
- `build_distribution_rows(analytics_data)`
- `build_excel_rows(analytics_data)` or equivalent shared row payload
- `render_csv(rows)`

Rules:

- Emit real table rows, not JSON dumps
- Keep ANA-001 labels fixed
- Use `""` when `metrics_version` is missing

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/analytics/analytics_export_service.py \
  backend/tests/unit/services/analytics/test_analytics_export_service.py
git commit -m "feat(analytics): add export payload mapper"
```

### Task 2: Route `/analytics/export` through the shared backend mapper

**Files:**
- Modify: `backend/src/api/v1/analytics/analytics.py`
- Modify: `backend/src/services/excel/excel_export_service.py`
- Modify: `backend/tests/unit/api/v1/test_analytics.py`
- Test: `backend/tests/unit/services/analytics/test_analytics_export_service.py`

- [ ] **Step 1: Write the failing route test**

```python
def test_export_csv_should_return_tabular_content_not_json(client, admin_user_headers):
    response = client.post(
        "/api/v1/analytics/export?export_format=csv",
        headers=admin_user_headers,
    )

    assert response.status_code == 200
    assert "总收入（经营口径）" in response.text
    assert "\"total_income\"" not in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_analytics.py -k "export_csv_should_return_tabular_content_not_json" -q`

Expected: FAIL because current CSV export is `json.dump(result, output, ...)`.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- `analytics.py` imports and uses `AnalyticsExportService`
- `csv` branch uses `render_csv(shared_rows)`
- `excel` branch passes structured rows into `ExcelExportService.export_analytics_to_excel(...)`
- `ExcelExportService.export_analytics_to_excel()` accepts `list[dict[str, Any]]` rows or a structured payload, and writes a real analytics sheet instead of dumping nested JSON by key
- `pdf` branch continues returning a business error payload with “尚未实现”

- [ ] **Step 4: Run route and service tests**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py tests/unit/api/v1/test_analytics.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/v1/analytics/analytics.py \
  backend/src/services/excel/excel_export_service.py \
  backend/tests/unit/api/v1/test_analytics.py \
  backend/tests/unit/services/analytics/test_analytics_export_service.py
git commit -m "feat(analytics): unify csv and xlsx export contract"
```

## Chunk 3: Frontend Export Path Consolidation

### Task 3: Make `analyticsService` the only frontend export gateway

**Files:**
- Modify: `frontend/src/services/analyticsService.ts`
- Modify: `frontend/src/services/__tests__/analyticsService.test.ts`

- [ ] **Step 1: Write the failing service test**

```typescript
it('passes date filters to backend export using date_from/date_to', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({
    success: true,
    data: new Blob(['csv']),
  });

  await service.exportAnalyticsReport('csv', {
    start_date: '2026-03-01',
    end_date: '2026-03-31',
    include_deleted: true,
  });

  expect(apiClient.post).toHaveBeenCalledWith(
    '/analytics/export',
    undefined,
    expect.objectContaining({
      params: {
        export_format: 'csv',
        date_from: '2026-03-01',
        date_to: '2026-03-31',
        include_deleted: true,
      },
    })
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts --reporter=verbose`

Expected: FAIL because the test file does not yet mock `apiClient.post` or any shared download helper behavior.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Extend `analyticsService` tests to mock `apiClient.post`
- Keep `exportAnalyticsReport()` as the API call boundary
- If a shared download helper is added in `analyticsService.ts`, keep it pure and easy to test

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts --reporter=verbose`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/analyticsService.ts \
  frontend/src/services/__tests__/analyticsService.test.ts
git commit -m "test(analytics): lock backend export request contract"
```

### Task 4: Repoint asset analytics and dashboard to the shared backend export flow

**Files:**
- Modify: `frontend/src/hooks/useAssetAnalytics.ts`
- Modify: `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- Modify: `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
- Modify: `frontend/src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx`

- [ ] **Step 1: Write the failing hook and component tests**

```typescript
it('useAssetAnalytics delegates export to analyticsService instead of local exportAnalyticsData', async () => {
  await result.current.handleExport();
  expect(analyticsService.exportAnalyticsReport).toHaveBeenCalledWith('excel', expect.any(Object));
  expect(exportAnalyticsData).not.toHaveBeenCalled();
});

it('AnalyticsDashboard export menu delegates to analyticsService.exportAnalyticsReport', async () => {
  fireEvent.click(screen.getByText('导出'));
  fireEvent.click(screen.getByText('导出 CSV'));
  expect(analyticsService.exportAnalyticsReport).toHaveBeenCalledWith('csv', expect.any(Object));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useAssetAnalytics.test.ts src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx --reporter=verbose`

Expected: FAIL because `useAssetAnalytics` still imports `exportAnalyticsData` and dashboard/asset page do not share a common path.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- `useAssetAnalytics` removes `analyticsExportService` import
- `useAssetAnalytics.handleExport()` calls backend export and performs the same download UX as dashboard
- `AnalyticsDashboard` reuses the same download helper or same service-level logic instead of duplicating blob-to-download code
- Keep success/error message behavior aligned between both entry points

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useAssetAnalytics.test.ts src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx --reporter=verbose`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useAssetAnalytics.ts \
  frontend/src/hooks/__tests__/useAssetAnalytics.test.ts \
  frontend/src/components/Analytics/AnalyticsDashboard.tsx \
  frontend/src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx
git commit -m "feat(analytics): unify frontend export flow"
```

## Chunk 4: Documentation and Final Verification

### Task 5: Update SSOT and verify end-to-end

**Files:**
- Modify: `docs/requirements-specification.md`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`
- Move after completion: `docs/plans/2026-03-24-req-ana-001-export-closure-plan.md` -> `docs/archive/backend-plans/2026-03-24-req-ana-001-export-closure-plan.md`

- [ ] **Step 1: Write the failing docs expectation**

Use the existing docs gate as the failing test: the implementation is not complete until the docs reflect the new evidence and the active plan is archived.

- [ ] **Step 2: Run docs gate before doc updates**

Run: `make docs-lint`

Expected: PASS before doc updates, but `REQ-ANA-001` state/evidence will still be incomplete relative to the new implementation.

- [ ] **Step 3: Write minimal documentation updates**

Required updates:

- Change `REQ-ANA-001` status/evidence in `docs/requirements-specification.md`
- Add implementation verification entry to `CHANGELOG.md`
- After code is complete, archive this plan and remove it from active entries in `docs/plans/README.md`

- [ ] **Step 4: Run final verification**

Run:

```bash
cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py tests/unit/api/v1/test_analytics.py -q
cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts src/hooks/__tests__/useAssetAnalytics.test.ts src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx --reporter=verbose
make docs-lint
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add docs/requirements-specification.md \
  docs/plans/README.md \
  CHANGELOG.md \
  docs/archive/backend-plans/2026-03-24-req-ana-001-export-closure-plan.md
git commit -m "docs(analytics): close req-ana-001 export plan"
```

## Risks and Checks

- The current Excel exporter serializes nested analytics payloads as JSON strings; if the shared row payload is not introduced first, CSV and XLSX will drift again.
- `useAssetAnalytics` currently has no export delegation test, so it is easy to accidentally keep the local export path alive unless the test explicitly asserts `exportAnalyticsData` is not called.
- `AnalyticsDashboard` test fixtures currently focus on rendering; export interaction assertions must be added carefully so they do not over-mock the dropdown behavior.
- If the final `REQ-ANA-001` implementation still leaves PDF unsupported, the requirements doc must stay precise: export is closed for CSV/XLSX and version marking, not for PDF.
