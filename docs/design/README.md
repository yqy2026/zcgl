# 设计资产

本目录存放产品设计相关资产，包括 UI 图、静态画板和设计评审材料。

## 目录

- [UI 图](ui-mockups/README.md)
- [早期 UI 设计原型](ui-mockups/ui-design-prototype.html)
- [UI/UX 全面分析与对齐方案（2026-06-20）](2026-06-20-uiux-analysis-and-alignment.md) — 现状诊断 + 解决方案；收口下条
- [角色化工作台设计方案](role-based-dashboard-redesign.md) — ⚠️ 部分过时，以上条为准
- [核心任务流（User Journeys）](flows/README.md) — 补录链路 / 实收登记 / 风险处置

## 治理规则

- 可继续迭代的 UI 设计稿放在 `ui-mockups/`。
- 一次性巡检截图或测试截图仍放在 `output/` 或测试报告目录，不放入本目录。
- 设计资产修改后同步更新 `CHANGELOG.md`。
- **设计稿须标注「对齐的 MVP 范围基线」**：功能超出当前 PRD §4 In Scope 的，显式标 `vNext`、不混入当前设计（防设计漂移超范围，见 [2026-06-20 对齐方案](2026-06-20-uiux-analysis-and-alignment.md) G1/G5）。
- **口径单源**：设计稿引用业务口径只引 PRD / domain-model 锚点，不在设计稿里自行定义（防口径双源）。
