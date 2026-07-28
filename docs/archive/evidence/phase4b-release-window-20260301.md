# Phase 4b Release Window Record（2026-03-01）

## 状态
- result: `PASS_LOCAL`
- reason: `本地环境已完成等价发布窗口链路核查（2026-03-02）`

## 已具备前置
- Step4 运行时引用清零门禁（代码扫描）: `PASS`
- 后端最小回归（迁移/中间件/产权证链路）: `PASS (78 passed)`
- 后端全量非慢测回归: `PASS (4820 passed, 6 skipped)`
- No-Go SQL 门禁本地快照: `PASS`（`phase4_no_go_snapshot --enforce`，见 `docs/release/evidence/phase4-no-go-sql-snapshot-20260302.md`）
- 前端门禁（本地）：`pnpm check` / `pnpm build` / `pnpm test` 均 `PASS`
- `@authz-minimal`（Chromium，本地 BASE_URL）：`2 passed`

## 本地窗口执行记录（2026-03-02）
1. 迁移到 Phase4 head
- `PHASE4_TENANT_NOT_NULL_DECISION=B alembic upgrade head` -> PASS
- `alembic current` -> `20260301_phase4_drop_legacy_party_columns (head)`

2. 写冻结前置核验（本地）
- `active_write_txn` SQL -> `0`（PASS）

3. final backup + 可恢复性清单
- `pg_dump -Fc` 生成：`/home/y/projects/zcgl/backups/phase4/pre_phase4_final_local_20260302_122629.dump`
- `pg_restore --list` -> PASS（`1035` lines）

4. 对账（post-drop）
- `python -m src.scripts.migration.party_migration.reconciliation --mode phase4-local-post-drop` -> PASS

5. 前端/后端门禁
- backend `pytest --no-cov -m "not slow" -q -x` -> PASS
- frontend `check/build/test` -> PASS
- `@authz-minimal` E2E -> PASS（重跑稳定）

## 本地豁免项
1. 维护模式写接口拒绝态（423/429/503）探针：本地未开启维护模式，记为 `WAIVED_LOCAL`。
2. Canary 连续 10 分钟 p95/5xx 指标：本地无线上流量，记为 `WAIVED_LOCAL`。
