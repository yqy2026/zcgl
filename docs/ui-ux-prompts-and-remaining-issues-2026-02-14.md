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

## 2) 当前剩余问题概览（基于代码扫描）

- 扫描范围：`frontend/src/**/*.module.css`
- 硬编码 `px` 命中总数：`343`
- 涉及文件数：`76`

### 高优先级剩余文件（按命中数）

1. `frontend/src/pages/Assets/AssetAnalyticsPage.module.css`（24）
2. `frontend/src/components/Layout/Layout.module.css`（16）
3. `frontend/src/components/Loading/SkeletonLoader.module.css`（15）
4. `frontend/src/components/Notification/NotificationCenter.module.css`（14）
5. `frontend/src/pages/System/RoleManagementPage.module.css`（11）
6. `frontend/src/components/Analytics/Filters/Filters.module.css`（11）
7. `frontend/src/pages/System/TemplateManagementPage.module.css`（9）
8. `frontend/src/pages/LoginPage.module.css`（9）
9. `frontend/src/pages/System/PromptListPage.module.css`（8）
10. `frontend/src/pages/System/UserManagementPage.module.css`（7）
11. `frontend/src/components/Ownership/OwnershipList.module.css`（7）
12. `frontend/src/components/Common/ResponsiveTable.module.css`（7）

---

## 3) 剩余问题类型（建议优先处理）

- **触控目标不统一**：仍有 `32/36/40/44px` 混用，移动端优先统一到按钮高度令牌。
- **状态标签与辅助文案不统一**：`12px + 18px` 组合仍在多处重复，需继续令牌化。
- **微间距硬编码残留**：`2/4/6/8px` 在导航、过滤器、列表项中分散存在。
- **卡片与布局节奏漂移**：部分页面仍保留固定高度/最小宽度表达，影响跨页面密度一致性。

---

## 4) 建议的下一批执行顺序

1. `AssetAnalyticsPage` + `Layout`（全局骨架与分析页）
2. `SkeletonLoader` + `NotificationCenter`（高可见反馈区）
3. `RoleManagementPage` + `Filters`（系统页高频交互区）
4. `PromptListPage` + `UserManagementPage` + `ResponsiveTable`（列表密集区）

---

## 5) 当前回归基线（最近一次）

- `pnpm lint`：通过
- `pnpm type-check`：通过
- `pnpm vitest`：`1934/1934` 通过（`/tmp/vitest-ui-round581.json`）

