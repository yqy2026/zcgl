# Phase 3d Exit 验收记录（2026-02-28）

## 元信息
- 日期：`2026-02-28`
- 阶段：`P3d（useCapabilities + 策略包管理 UI）`
- 责任人：`codex`
- release-id：`phase3d-exit-20260228`

## 结论
- `P3d Exit`：`Pass`
- 说明：P3d 代码链路与脚本门禁通过，`usePermission` 主运行链残留已清零，`@authz-minimal` E2E 标签用例可执行并通过。

## Exit 门禁证据

| 门禁项 | 证据 | 结果 |
|---|---|---|
| D10 互斥门禁 | `pnpm -C frontend check:route-authz` | Pass |
| 动作/资源词汇门禁 | `pnpm -C frontend check:authz-vocabulary` | Pass |
| CapabilityGuard 主链接线门禁 | `pnpm -C frontend check:capability-guard-wiring` | Pass |
| 前端全链路静态门禁 | `pnpm -C frontend check` | Pass |
| `usePermission` 主生效链脱钩 | `! grep -rEl "usePermission" frontend/src/ --include="*.ts" --include="*.tsx" --exclude="usePermission.tsx" --exclude="PermissionGuard.tsx" --exclude-dir="Router" --exclude-dir="__tests__" --exclude-dir="test" --exclude-dir="test-utils"` | Pass |
| 最小权限 E2E（`@authz-minimal`） | `pnpm -C frontend e2e --grep "@authz-minimal" --project=chromium`（本地拉起 `pnpm dev --host 127.0.0.1 --port 5173` 后执行） | Pass（1 passed） |
| 策略包页面同角色重复加载回归 | `pnpm -C frontend vitest run src/pages/System/__tests__/DataPolicyManagementPage.test.tsx` | Pass |
| `PermissionGuard` Hook 顺序回归 | `pnpm -C frontend vitest run src/components/System/__tests__/PermissionGuard.test.tsx` | Pass |
| 资产列表去 `usePermission` 回归 | `pnpm -C frontend vitest run src/components/Asset/__tests__/AssetList.test.tsx` | Pass |
| 策略包服务契约回归 | `pnpm -C frontend vitest run src/services/__tests__/dataPolicyService.test.ts` | Pass |

## 本批次新增/变更（补充）
- `frontend/src/components/Asset/AssetList.tsx`：改为 `useAuth().isAdmin`，移除 `usePermission` 运行时依赖。
- `frontend/src/components/Asset/__tests__/AssetList.test.tsx`：更新为 `AuthContext` mock。
- `frontend/src/services/__tests__/dataPolicyService.test.ts`：新增服务层回归测试。

## 备注
- 本次 `@authz-minimal` 首次执行失败原因为本地 `127.0.0.1:5173` 未启动（`ERR_CONNECTION_REFUSED`）；拉起前端 dev server 后同命令通过。
- D9 发布验签（`docs/release/evidence/capability-guard-env.md` 的发布态证据完整性）属于 Release Gate，未作为本次开发态 Exit 阻断项。
