# Phase 3d 权限冻结清单（Day-0 模板）

> 用途：作为 Phase 3d 进入门禁的最小冻结记录。执行当日必须回填责任人、日期与 release-id。

## 元信息
- 日期：`YYYY-MM-DD`
- 责任人：`<owner>`
- release-id：`<release-id>`
- 范围：`Phase 3d authz + capability guard`

## 冻结决策
1. D7 /403 落点决策：`<decision>`
2. D8 feature flag 熔断策略：`<decision>`
3. perspectives 决策（A/B）：`<decision>`
4. 同资源多条合并规则：`<decision>`
5. 权限单源迁移清单：`<link or note>`
6. constants/routes 派生导出审计表：`<link or note>`

## 验证命令快照
- `cd frontend && pnpm check`
- `cd frontend && pnpm check:authz-vocabulary`
- `cd frontend && pnpm check:capability-guard-wiring`
- `cd frontend && pnpm check:route-authz-exclusive`

## 备注
- 若存在偏差，需在此记录临时豁免原因、影响范围和关闭时间。