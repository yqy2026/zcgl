# Phase 3d 权限冻结清单（Day-0 模板）

> 用途：作为 Phase 3d 进入门禁的最小冻结记录。执行当日必须回填责任人、日期与 release-id。

## 元信息
- 日期：`2026-02-27`
- 责任人：`phase3-preflight`
- release-id：`phase3-preflight-20260227`
- 范围：`Phase 3d authz + capability guard`

## 冻结决策
1. D7 /403 落点决策：`B（InlineForbidden/route.fallback）`
2. D8 feature flag 熔断策略：`VITE_ENABLE_CAPABILITY_GUARD=false 时仅保留认证守卫，禁用 capability 计算`
3. perspectives 决策（A/B）：`B（frontend resource-specific override，project: ['manager']）`
4. 同资源多条合并规则：`按 resource 并集归并（actions/owner_party_ids/manager_party_ids 去重并集，perspectives 走 override > union）`
5. 权限单源迁移清单：`守卫主链固定 AuthContext.capabilities；禁止 AuthService.hasPermission/getLocalPermissions/hasAnyPermission 与 permissions/summary 直连`
6. constants/routes 派生导出审计表：`已登记为“仅字面量卫生审计，不作为运行时权限真源”`

## constants/routes 审计表
| 文件 | 结论 | 责任人 | 截止日期 | 验证命令 |
|---|---|---|---|---|
| `frontend/src/routes/AppRoutes.tsx` | 已移除 `ROUTE_CONFIG` 派生链；运行时权限真源固定为 AppRoutes 显式元数据 | codex | 2026-02-28 | `! (grep -rEn "ROUTE_CONFIG" frontend/src/ --include="*.ts" --include="*.tsx" --exclude-dir="__tests__" --exclude-dir="test" --exclude-dir="test-utils" | grep -vE "^frontend/src/constants/routes\\.ts:")` |
| `frontend/src/constants/routes.ts` | 保留为路由常量定义；禁止回流权限判定逻辑 | phase3-preflight | 2026-02-27 | `rg -n "permissions|adminOnly|ROUTE_CONFIG" frontend/src/constants/routes.ts` |

## 验证命令快照
- `cd frontend && pnpm check`
- `cd frontend && pnpm check:authz-vocabulary`
- `cd frontend && pnpm check:capability-guard-wiring`
- `cd frontend && pnpm check:route-authz`

## 备注
- 若存在偏差，需在此记录临时豁免原因、影响范围和关闭时间。
