# Flow · 收付流水登记与派生（流水分摊 → 收缴率/逾期）

- **角色**：运营操作员（运营方 × 操作）
- **触发**：收到或支付一笔经营款，需要登记实际发生日期并分摊到账期
- **价值**：收付流水和分摊是实收/实付与收缴统计的事实来源；逾期和收缴率由它们派生

## 前置条件

- 合同已定稿生效、台账已生成（见 [合同补录链路](flow-contract-intake.md)）。

## 主流程

| # | 用户动作 | 页面 | API | 校验门 / 口径 | 出错分支 |
|---|---|---|---|---|---|
| 1 | 打开经营台账（或从项目摘要跳转），按项目/主体/账期筛选 | `OperationsLedgerPage` | `GET /api/v1/ledger/entries` / `GET /api/v1/ledger/service-fees` | 台账是**账本（历史记录）**，按固化归属读、不回算当前归属 | — |
| 2 | 选择台账条目，登记收款或付款流水 | `OperationsLedgerPage` | `POST /api/v1/ledger/payment-flows` | 流水记录发生日期、金额、经办人、对方主体、备注和可选凭证；金额必须大于 0 | 创建失败时不保存分摊 |
| 3 | 将流水分摊到一个或多个账期 | `OperationsLedgerPage` | `POST /api/v1/ledger/payment-flows/{flow_id}/allocations` | 分摊合计必须等于流水金额，且目标类型、账期、项目/主体/币种必须一致 | 校验失败时明确拒绝 |
| 4 | 系统派生实收/实付、收缴率和逾期 | （展示） | 台账查询/分析/通知 | `paid_amount` 由有效分摊汇总；`unpaid/partial/paid` 由汇总金额对 `amount_due` 派生；逾期只属于终端租户收缴 | — |
| 5 | 少收/减免场景 | 合同/协议更正 | 合同更正 + 台账重算 | 未收付条目可重算；已有流水分摊条目跳过并派生 `ledger_stale_after_correction` 风险 | 人工对账，不静默改写 |

## 关键 UX 约束（容易做错的地方）

- **只通过流水与分摊写入实收/实付**：UI 和 API 都不提供直接改累计 `paid_amount` 的入口；`PATCH /contracts/{id}/ledger/batch-update-status` 已下线。
- **不翻牌**：UI **不提供**手选 `unpaid/partial/paid` 下拉，也**没有「逾期」登记态**；状态与逾期都是派生投影。
- **保留实际发生日期**：每笔流水保留 `occurred_on`，统计默认仍按分摊账期归属；MVP 不对接银行或支付通道。
- **合同更正后已收条目不自动改写**：`paid`/`partial` 条目自动跳过；若与新条款不一致，派生 `ledger_stale_after_correction` 风险提醒人工对账（接 [风险处置](flow-risk-remediation.md)），**不自动改、不可手工关**（ADR-0008）。

## 引用锚点

PRD §6.6、REQ-RNT-005/006；domain-model §4.14 ContractLedgerEntry / OperationalPaymentFlow / PaymentAllocation、§6 统计口径；ADR-0007（逾期派生）、ADR-0008（陈旧已收派生风险）、ADR-0011（固化归属）、ADR-0019（payment_status 派生）。
