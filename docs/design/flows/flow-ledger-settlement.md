# Flow · 实收登记与派生（台账录实收 → 收缴率/逾期）

- **角色**：运营操作员（运营方 × 操作）
- **触发**：收到一笔款，要在台账上登记实收
- **价值**：实收是收缴率与实收统计的事实来源；逾期/收缴率全靠它派生

## 前置条件

- 合同已定稿生效、台账已生成（见 [合同补录链路](flow-contract-intake.md)）。

## 主流程

| # | 用户动作 | 页面 | API | 校验门 / 口径 | 出错分支 |
|---|---|---|---|---|---|
| 1 | 打开财务台账（或项目台账），按项目/产权方/账期筛选 | FinancialLedgerPage | `GET /contracts/ledger`（按固化归属 `attributed_*` 聚合，ADR-0011） | 台账是**账本（历史记录）**，按固化归属读、不回算当前归属 | — |
| 2 | 在条目上录入 `paid_amount`（**只填金额**） | FinancialLedgerPage | 实收登记端点 | **不手选状态**——`unpaid/partial/paid` 由 `paid_amount` 对 `amount_due` 派生（ADR-0019，待实施） | — |
| 3 | 系统派生收缴/逾期口径 | （展示） | — | 收缴率 = 当月实收/应收；**逾期** = `due_date` 已过且 `paid_amount < amount_due` 且非 `voided`（ADR-0007）；统计/风险/筛选/通知**统一按此派生** | — |
| 4 | 少收/减免场景 | FinancialLedgerPage / 合同更正 | 合同/台账更正 | 走 `amount_due` 更正，**不翻状态、不红字冲销**（属财务总账 Out of Scope） | — |

## 关键 UX 约束（容易做错的地方）

- **只录金额，不翻牌**：UI **不提供**手选 `unpaid/partial/paid` 下拉，也**没有「逾期」登记态**——状态与逾期都是 `paid_amount`/`due_date` 实时派生的。给个手选状态轴 = 制造可漂移的第二真相（ADR-0019 正是来收掉它）。
- **不记分期流水**：MVP 台账条目只记一个实收总额，不记逐次收款日期明细，不对接真实资金通道（与「支付结算」区分，PRD §4.2）。
- **合同更正后已收条目不自动改写**：`paid`/`partial` 条目自动跳过；若与新条款不一致，派生 `ledger_stale_after_correction` 风险提醒人工对账（接 [风险处置](flow-risk-remediation.md)），**不自动改、不可手工关**（ADR-0008）。

## 引用锚点

PRD §4.2（支付结算区分）、REQ-RNT-005/006；domain-model §4.14 ContractLedgerEntry、§6 统计口径；ADR-0007（逾期派生）、ADR-0008（陈旧已收派生风险）、ADR-0011（固化归属）、ADR-0019（payment_status 派生，待实施）。
