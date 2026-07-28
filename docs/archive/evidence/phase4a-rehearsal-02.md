# Phase 4a Rehearsal #2（2026-03-01）

## 状态
- result: `PASS_LOCAL`
- scope: `本地可执行门禁复演（不含真实维护窗口动作）`

## 预置内容
- 演练#1 阻塞项已在本地修复：
  - Alembic Step4 删表顺序依赖冲突
  - 产权证 API 单测授权 mock 与当前 authz 依赖对齐
  - RentContract owner/ownership 更新链路别名覆盖问题
  - QueryBuilder / Asset / RentContract 相关 Step4 语义断言漂移

## 本地复演结果（2026-03-01）
1. 后端全量非慢测门禁
- 命令：`cd backend && ./.venv/bin/pytest --no-cov -m "not slow" -q -x`
- 结果：`PASS (4820 passed, 6 skipped)`

2. 前端门禁链路
- 命令：`pnpm -C frontend check`
- 结果：`PASS`
- 命令：`pnpm -C frontend build` + `grep warning gate`
- 结果：`PASS`（`/tmp/phase4-local-build.log` 无 `warning/warn` token）
- 命令：`pnpm -C frontend test`
- 结果：`PASS`
- 命令：`BASE_URL=http://127.0.0.1:5173 pnpm -C frontend e2e --grep "@authz-minimal" --project=chromium`
- 结果：`PASS (2 passed)`

3. No-Go SQL 门禁快照（本地测试库）
- 执行口径：`PHASE4_TENANT_NOT_NULL_DECISION=B ./.venv/bin/python -m src.scripts.migration.party_migration.phase4_no_go_snapshot --database-url "$DB_URL" --format markdown --enforce`
- 留痕文件：`docs/release/evidence/phase4-no-go-sql-snapshot-20260302.md`
- 结果：
  - `subject_table=null`（`abac_policy_subjects` 不存在）
  - `subject_count=0`
  - `assets_owner_null=0`
  - `assets_manager_null=0`
  - `rc_owner_null=0`
  - `rc_manager_null=0`
  - `ledger_owner_null=0`
  - `projects_manager_null=0`
  - `tenant_null_count=0`
  - `tenant_total_count=0`
  - `user_dual_party_viewer_mapping_count=1`
  - `tenant_decision_declared=PASS(B)`，`tenant_null_zero_when_decision_a=SKIP`

## 补充执行（2026-03-02）
1. 本地 DB 迁移已升级到 Phase4 head。
2. final backup 已落盘并通过 `pg_restore --list` 校验。
3. post-drop reconciliation 已通过。
4. Canary 流量指标门禁在本地环境记为 `WAIVED_LOCAL`（无线上流量）。
