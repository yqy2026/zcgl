# 前端视觉一致性执行提示语与剩余问题（2026-02-14）

## 1) 可直接复用的提示语（Prompt）

### Prompt A（连续轮次，不停顿）
```text
请使用 ui-ux-pro-max 连续执行前端视觉一致性修复，不要停。
每轮必须完成：1) 选择1-3个高影响样式文件；2) 将硬编码 px 迁移为设计令牌；
3) 更新 CHANGELOG.md；4) 运行 pnpm lint、pnpm type-check、pnpm vitest；
5) 输出“本轮修改文件 + 验证结果 + 下一轮目标”。
```

### Prompt B（按优先级推进）
```text
请按 P0→P1→P2 优先级修复样式不一致问题：
P0: 导航/按钮/表单触控高度与焦点态；
P1: 卡片与列表间距、状态标签字号/行高；
P2: 次级文本和微间距（2/4/6/8px）。
使用 ui-ux-pro-max，每轮修复后必须更新 CHANGELOG.md 并跑前端全量回归。
```

### Prompt C（验收导向）
```text
请使用 ui-ux-pro-max 对前端做“视觉一致性验收修复”，目标是：
跨页面按钮高度统一、状态标签统一、卡片内外边距统一、移动端触控目标统一。
每轮给出“已收敛项/未收敛项/风险项”，并保持主动连续推进。
```

---

## 2) 当前剩余问题概览（基于代码扫描，更新于 2026-02-15）

- 扫描范围 A：`frontend/src/**/*.module.css`
- 硬编码 `px` 命中总数：`0`
- 涉及文件数：`0`

- 扫描范围 B：`frontend/src/**`（排除 `*.module.css`）
- 非 token 源文件中的硬编码 `px` 命中总数：`0`
- 已知保留 `px` 的文件：`无`
- token 源文件中的硬编码 `px` 命中总数：`0`

### 当前高优先级剩余文件（策略决策项）

1. `frontend/src/styles/variables.css`（已切换 `rem`，需固化令牌单位规范）
2. `frontend/src/theme/sharedTokens.ts`（已切换 `rem`，需保持与样式 token 同步）
3. `frontend/scripts/scan-style-px.config.json`（持续维护 token 源白名单）

---

## 3) 剩余问题类型（建议优先处理）

- **令牌单位治理需要固化**：当前 token 源已统一 `rem`，下一步需文档化并避免回退。
- **主题 token 仍有多入口维护成本**：`variables.css` 与 `theme/*` 仍分层存在，需持续校准。
- **回归重点转为门禁稳定性**：保持扫描与审计链路一致，防止新增硬编码回流。

---

## 4) 建议的下一批执行顺序

1. 固化 “token 源统一使用 `rem`” 规范并补充到开发文档
2. 将扫描脚本升级为可选“全量零 `px`”模式，用于阶段性验收
3. 持续在 `audit:*` 链路保留像素门禁，避免回归
4. 继续跟踪主题 token 复用，减少跨文件重复定义

补充：扫描规则已配置化，token 源列表由 `frontend/scripts/scan-style-px.config.json` 维护。

---

## 5) 当前回归基线（最近一次）

- `pnpm lint`：通过（`oxlint` 0 warning / 0 error）
- `pnpm type-check`：通过（`tsgo --noEmit`）
- `pnpm vitest`：定向通过（`OccupancyRateChart` + `LoadingSpinner`，`12/12`）
- `pnpm scan:px:all-strict`：通过（`module-style / non-token-source / token-source px = 0`）
- `pnpm verify:token-sync`：通过（`variables.css` 与 `theme/sharedTokens.ts` 尺度令牌一致）
- `pnpm guard:ui`：通过（聚合执行 `scan:lint-disable + scan:px:all-strict + verify:token-sync`）
- `pnpm guard:ui:report`：通过（仅导出 `style-px-report.json` + `token-sync-report.json`）
- `pnpm guard:ui:ci`：通过（阻塞校验并导出报告，供 CI 使用）
- `make scan-frontend-report`：通过（仓库根目录执行严格门禁并导出前端报告）
- 审计链路已接入：`audit:ui / audit:full / audit:full:coverage` 包含 `guard:ui`
- CI 链路已接入：`.github/workflows/ci.yml` 的 `frontend-lint` 作业执行 `guard:ui:ci`
- CI 报告产物：`frontend-lint-reports` 附带 `style-px-report.json` 与 `token-sync-report.json`
- 本地 `pnpm check` 已接入：默认执行 `guard:ui`
- `frontend/src/**/*.module.css`：`px` 命中 `0`
- 非 token 源文件（排除 `variables.css`、`theme/sharedTokens.ts`）：`px` 命中 `0`
- token 源文件（`variables.css`、`theme/sharedTokens.ts`）：`px` 命中 `0`
