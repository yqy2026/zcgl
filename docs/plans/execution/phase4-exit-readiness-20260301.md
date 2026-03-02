# Phase 4 Exit Readiness（2026-03-01）

## 当前结论
- phase4_exit: `PASS_LOCAL`
- reason: `本地环境已完成 Phase4 迁移、门禁、回归与证据收口（2026-03-02）`

## 已完成
1. Phase4 Step3/Step4 Alembic 迁移脚本落地。
2. reconciliation 兼容 Step4 删旧列后 schema。
3. Step4 运行时引用清零门禁（symbol/table 双扫描）通过。
4. 最小回归通过：`78 passed`。
5. 前端本地门禁通过：`pnpm check`、`pnpm build`（warning token gate 通过）、`pnpm test`。
6. `@authz-minimal` 基线达标并通过 Chromium E2E：`2 passed`（allow + deny）。
7. `X-Authz-Stale` 契约已在后端统一异常链落地，并通过单测验证（`11 passed`）。
8. Step4 运行时兼容补丁已追加：集成 seed 完成 party 化（`owner_party_id/manager_party_id`），`CRUDProject` 修复为按 `manager_party_id` 过滤而非创建人回退。
9. 新增/修复回归通过：
   - `tests/integration/api/test_phase2_statement_count.py` + `tests/integration/api/test_project_visibility_real.py`：`5 passed`
   - `tests/unit/api/v1/test_project.py` + 上述集成：`29 passed`
10. 后端非慢测全量回归通过：`pytest --no-cov -m "not slow" -q -x` -> `4820 passed, 6 skipped`。
11. 前端门禁复跑通过：
   - `pnpm -C frontend check` -> PASS
   - `pnpm -C frontend build` + warning token gate -> PASS
   - `pnpm -C frontend test` -> PASS
   - `BASE_URL=http://127.0.0.1:5173 pnpm -C frontend e2e --grep "@authz-minimal" --project=chromium` -> `2 passed`
12. No-Go SQL 门禁本地快照通过：
   - `subject_count=0`
   - 主链空值计数（assets/rent_contracts/rent_ledger/projects）均为 `0`
   - `user_dual_party_viewer_mapping_count=1`
   - 执行方式已收敛为脚本：`phase4_no_go_snapshot --enforce`（证据：`docs/release/evidence/phase4-no-go-sql-snapshot-20260302.md`）
13. 本地 DB 已迁移到 Phase4 head：`20260301_phase4_drop_legacy_party_columns (head)`。
14. final backup 与清单校验通过（证据：`docs/release/evidence/phase4-final-backup-reference.md`）。
15. `X-Authz-Stale` 本地 HTTP 样例通过：`401` + `X-Authz-Stale=true`（证据：`docs/release/evidence/phase4-authz-stale-contract.md`）。
16. P4b/P4c 本地收口：`PASS_LOCAL`（见 `phase4b-release-window-20260301.md` / `phase4c-stabilization-20260301.md`）。

## 结论备注
1. 本次为“本地环境完成态”；如需生产放流，建议补做真实 Canary 指标观测与维护模式写探针留痕。
