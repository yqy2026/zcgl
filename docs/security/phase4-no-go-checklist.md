# Phase4 No-Go Checklist

## 时间
- generated_at: `2026-03-02`

## 结果快照（本地可执行范围）
1. Step4 删除对象运行时引用清零
- symbol_pattern_scan: `PASS`（rg exit=1，无命中）
- table_pattern_scan: `PASS`（rg exit=1，无命中）

2. 后端最小回归
- command: `pytest --no-cov tests/unit/migration tests/unit/middleware/test_authz_dependency.py tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q`
- result: `PASS (78 passed)`

2.1 Step4 运行时兼容补丁回归（party FK + project scope）
- command: `cd backend && ./.venv/bin/pytest --no-cov -q tests/unit/api/v1/test_project.py tests/integration/api/test_phase2_statement_count.py tests/integration/api/test_project_visibility_real.py`
- result: `PASS (29 passed)`
- covered:
  - 集成 seed 从 legacy `organization_id` 迁移到 `Party(external_ref=organization_id)` + `owner_party_id/manager_party_id`
  - `CRUDProject` 在 Step4 删列后按 `manager_party_id` 执行主体过滤

3. 前端门禁（本地）
- `pnpm check`: `PASS`
- `pnpm build`: `PASS`
- build warning gate: `grep ... /tmp/phase4-release-build.log` -> `exit=1`（无 warning/warn token）
- `pnpm test`: `PASS`

4. 最小权限 E2E 基线
- `frontend/tests/e2e/auth/authz-minimal.spec.ts`: `PASS`（非 skeleton，`test(` 计数 `2`）
- `BASE_URL=http://127.0.0.1:5173 pnpm e2e --grep "@authz-minimal" --project=chromium`: `2 passed`

5. `X-Authz-Stale` 契约（代码/单测）
- 代码探针：`rg -n "X-Authz-Stale" backend/src` -> `src/core/exception_handler.py`
- 单测：`cd backend && uv run python -m pytest --no-cov tests/unit/core/test_exception_handling.py::TestAuthzStaleHeaderContract tests/unit/middleware/test_authz_dependency.py::test_require_authz_denied_write_with_stale_selected_view_marks_authz_stale tests/unit/middleware/test_authz_dependency.py::test_require_authz_denied_read_with_stale_selected_view_keeps_not_found_and_marks_stale -q` -> `7 passed`
- 前端联动：`cd frontend && pnpm exec vitest run src/api/__tests__/client.test.ts src/hooks/__tests__/useAuth.test.ts` -> `44 passed`
- 状态：`PASS_LOCAL`
- 2026-03-16 契约收紧：仅“已保存视角失效导致的拒绝”返回 `X-Authz-Stale`，覆盖普通 `403` 与掩码 `404`；普通 `401/403/404` 不再默认带该头。

6. 后端全量非慢测
- command: `cd backend && ./.venv/bin/pytest --no-cov -m "not slow" -q -x`
- result: `PASS (4820 passed, 6 skipped)`

7. 前端门禁复跑
- `pnpm -C frontend check`: `PASS`
- `pnpm -C frontend build`: `PASS`
- build warning gate: `grep ... /tmp/phase4-local-build.log` -> `NO_WARN_TOKEN`
- `pnpm -C frontend test`: `PASS`
- `BASE_URL=http://127.0.0.1:5173 pnpm -C frontend e2e --grep "@authz-minimal" --project=chromium`: `PASS (2 passed)`

7.1 本地写事务冻结前置检查
- command: `SELECT count(*) FROM pg_stat_activity ... active write txn`
- result: `PASS (0)`

8. No-Go SQL 门禁快照（本地测试库）
- db_url_source: `cd backend && ./.venv/bin/python -c 'from src.core.config import settings; print(settings.DATABASE_URL)'`
- execution: `cd backend && PHASE4_TENANT_NOT_NULL_DECISION=B ./.venv/bin/python -m src.scripts.migration.party_migration.phase4_no_go_snapshot --database-url "$DB_URL" --format markdown --enforce`
- evidence_file: `docs/release/evidence/phase4-no-go-sql-snapshot-20260302.md`
- `subject_table`: `null`
- `subject_count`: `0`
- `assets_owner_null`: `0`
- `assets_manager_null`: `0`
- `rc_owner_null`: `0`
- `rc_manager_null`: `0`
- `ledger_owner_null`: `0`
- `projects_manager_null`: `0`
- `tenant_null_count`: `0`
- `tenant_total_count`: `0`
- `user_dual_party_viewer_mapping_count`: `1`
- `tenant_decision_declared`: `PASS (B)`
- `tenant_null_zero_when_decision_a`: `SKIP`（决策 B）

## 生产窗口补充门禁（可选）
- 生产 Canary 指标门禁（p95/5xx，线上流量口径）
- 真实维护模式写探针拒绝态（423/429/503）留痕
