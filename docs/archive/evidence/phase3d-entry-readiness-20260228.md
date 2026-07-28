# Phase 3d Entry 就绪证据（2026-02-28）

## 元信息
- 日期：`2026-02-28`
- 责任人：`codex`
- release-id：`phase3d-entry-20260228`
- 范围：`P3d Entry hard gates re-check`

## 结论
- `P3d Entry`：`Pass`
- 说明：完成 `ROUTE_CONFIG` 回流阻断修复后，P3d 关键 Entry 门禁已满足，可进入实施。

## 关键证据
1. 前置阶段门禁
- `P2d` 已完成：`docs/plans/2026-02-19-phase2-implementation-plan.md`（P2d=done）
- `P3c Exit` 已通过：`docs/plans/execution/phase3c-exit-readiness-20260228.md`

2. Day-0 / 冻结文档
- `docs/plans/execution/phase3-execution-context.md` 存在
- `docs/plans/execution/phase3d-authz-freeze.md` 存在并包含 D7/D8/perspectives/并集归并/权限单源
- `docs/release/evidence/capability-guard-env.md` 存在并包含必填节
- `frontend/tests/e2e/auth/authz-minimal.spec.ts` 存在且含 `@authz-minimal`

3. seed 与数据库就绪
- `cd backend && ./.venv/bin/alembic current` -> `20260224_backfill_ownership_occupancy_policy_rules (head)`
- `cd backend && ./.venv/bin/alembic history --indicate-current` 命中：
  - `20260219_phase2_seed_data_policy_packages`
  - `20260221_backfill_expanded_policy_package_rules`
- `SELECT COUNT(*) FROM abac_policy_rules WHERE id LIKE 'seed_rule_%'` -> `485 (>0)`

4. request_id 观测前置
- `backend/src/main.py` 包含 `expose_headers=['X-Request-ID','Request-ID']`
- `curl` 跨域响应头命中：`Access-Control-Expose-Headers: X-Request-ID, Request-ID`

5. ROUTE_CONFIG 回流门禁（本次修复）
- 修复前：`frontend/src/routes/AppRoutes.tsx` 存在 `ROUTE_CONFIG` 导入与派生
- 修复后门禁命令通过：
  - `! (grep -rEn "ROUTE_CONFIG" frontend/src/ --include="*.ts" --include="*.tsx" --exclude-dir="__tests__" --exclude-dir="test" --exclude-dir="test-utils" | grep -vE "^frontend/src/constants/routes\.ts:")`

6. 前端门禁脚本
- `pnpm -C frontend check:route-authz` -> PASS
- `pnpm -C frontend check:authz-vocabulary` -> PASS
- `pnpm -C frontend check:capability-guard-wiring` -> PASS
- `pnpm -C frontend type-check` -> PASS
- `pnpm -C frontend vitest run src/routes/__tests__/AppRoutes.authz-metadata.test.ts` -> PASS (3/3)

## 本次变更文件
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts`
- `docs/plans/execution/phase3d-authz-freeze.md`
