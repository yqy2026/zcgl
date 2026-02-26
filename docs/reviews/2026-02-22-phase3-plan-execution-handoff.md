# Phase 3 计划修订与门禁落地交付归档（2026-02-22）

## 1) 本轮交付目标

- 将 `docs/plans/2026-02-20-phase3-implementation-plan.md` 从“可读”推进到“可执行可验收”。
- 把高风险文本 grep 门禁改为脚本门禁，降低误判。
- 将脚本门禁接入前端聚合检查链路，并确保可通过。

## 2) 已落地变更（代码/文档）

### 2.1 计划与审阅文档

- 审阅报告：`docs/reviews/2026-02-22-phase3-implementation-plan-strict-review-v4.md`
- 计划文档修订：`docs/plans/2026-02-20-phase3-implementation-plan.md`（含 v1.47/v1.48 收敛）
  - 修复 P3d/D9 中 Bash `(( ))` 误用
  - 强化 P3d Day-0 前置
  - 将 D9 拆分为开发 Exit 与发布验签双层
  - 将部分高风险门禁改为脚本入口

### 2.2 前端门禁脚本化

- 新增 `frontend/scripts/check-authz-vocabulary.mjs`
  - AST 检查守卫链中禁用动作词：`view/edit/import/settings/logs/dictionary/lock/assign_permissions`
  - AST 检查禁用资源名：`rental`
- 新增 `frontend/scripts/check-capability-guard-wiring.mjs`
  - 校验 `App.tsx`/`AppRoutes.tsx` 主链接线证据（`VITE_ENABLE_CAPABILITY_GUARD`、`capabilityGuardEnabled`、`renderProtectedElement`、`adminOnly/permissions/permissionMode`）

### 2.3 前端接线与词汇标准化

- `frontend/package.json`
  - 新增 `check:authz-vocabulary`
  - 新增 `check:capability-guard-wiring`
  - 并入 `check` 聚合链
- `frontend/src/constants/routes.ts`
  - 权限动作词标准化（ABAC 口径）
  - `resource: rental` 映射为 `rent_contract`
- `frontend/src/hooks/usePermission.tsx`
  - `PERMISSIONS` 常量动作词标准化
  - `resource` 口径对齐（`rental -> rent_contract`）
- `frontend/src/routes/AppRoutes.tsx`
  - 增加路由权限元数据类型：`permissions` / `permissionMode` / `adminOnly`
- `frontend/src/App.tsx`
  - 增加 capability guard 环境开关接线骨架

## 3) 验证结果

### 3.1 新增脚本门禁

- `cd frontend && node scripts/check-authz-vocabulary.mjs` ✅
- `cd frontend && node scripts/check-capability-guard-wiring.mjs` ✅

### 3.2 前端聚合门禁

- `cd frontend && pnpm check` 首次执行仅 `format:check` 失败（3 文件格式）
- 定向格式化后再次执行 `cd frontend && pnpm check` ✅ 全通过
  - 通过项：`lint` / `guard:ui` / `type-check` / `type-check:e2e` / `check:route-authz` / `check:authz-vocabulary` / `check:capability-guard-wiring` / `format:check`

## 4) 当前状态与建议

- 当前状态：Phase 3 本轮“计划修订 + 门禁落地 + 可执行验证”已闭环。
- 建议下一步（可选）：
  1. 按“文档修订、门禁脚本、前端接线”拆分提交（便于评审）
  2. 进入 Phase 3 业务迁移主线实现（在现有门禁下推进）
