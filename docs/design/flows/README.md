# 核心任务流（User Journeys）

本目录把系统**最核心的端到端任务链路**画成流程文档，补 [`../2026-06-20-uiux-analysis-and-alignment.md`](../2026-06-20-uiux-analysis-and-alignment.md) 诊断的 G4（只有屏级 mockup、无任务流）。

> 这三条流同时是 PRD 质量分析 P6/B 缺的「用户层」最小可用版——不必另写大 PRD，把它们作为 PRD 的用户视角补充即可。每条流贴着 PRD / domain-model / api-contract / ADR 的现有口径，**不重新定义业务规则**。

| 流 | 角色 | 覆盖 |
|---|---|---|
| [合同补录链路](flow-contract-intake.md) | 运营操作员 | 扫描件 → 解析确认 → 写入合同 → 生成台账（PRD §3.2 核心使用信号主链路） |
| [实收登记与派生](flow-ledger-settlement.md) | 运营操作员 | 台账录实收 → 收缴率/逾期实时派生 |
| [风险处置](flow-risk-remediation.md) | 运营/管理 | 风险下钻 → 改源数据 → 派生自然消除（**无「标记已处理」**） |

## 流程文档约定

- 每条流含：角色/触发、前置、主流程步骤表（用户动作 / 页面 / API / 校验门·口径 / 出错分支）、关键 UX 约束、状态、引用锚点。
- **口径单源**：引用 PRD/domain-model 锚点，不在此重定义。
- **范围**：只画当前 MVP 真做的链路；超范围步骤显式标 vNext。
