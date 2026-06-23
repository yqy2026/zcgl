# ADR-0019: 台账 `unpaid/partial/paid` 改为从 `paid_amount` 派生，实收登记只填金额

**状态**: ✅ 已实施（2026-06-20）
**决策日期**: 2026-06-19
**相关需求**: REQ-RNT-006（台账自动化与实收登记）、REQ-RNT-005（合同更正与作废留痕）、REQ-ANA-001（实收与收缴率口径可信）、§3.2（关键报表口径一致性）

---

## 背景

台账条目（`ContractLedgerEntry`）同时持有两个字段：

- `payment_status` 枚举（`unpaid` / `paid` / `partial` / `voided`）
- `paid_amount` 实收金额（`>= 0`，默认 0）

ADR-0007 已把 `overdue` 从 `payment_status` 删除、改为按 `paid_amount < amount_due` 派生；2026-06-16 落地后，`payment_status` 仅剩用户登记的 `unpaid` / `partial` / `paid` 加系统 `voided`。CONTEXT「逾期（派生口径）」当时记的实收登记事实是「收款结果（`unpaid/partial/paid`）**和**实收金额（`paid_amount`）」——即两个轴都让用户手填。

grill（2026-06-19）核对消费方后发现这是一个**残留的双真相轴**：

- **逾期**：按 `paid_amount < amount_due` 派生，**不读 `payment_status`**（ADR-0007）。
- **收缴率 / 实收**：分子 = 非作废条目 `paid_amount` 之和，分母 = 非作废条目 `amount_due` 之和，**不读 `payment_status`**（domain-model §6）。
- **唯一消费 `payment_status` 的是 ADR-0008 重算跳过逻辑**：`paid` / `partial` 条目重算时跳过、不自动改写。

于是 `payment_status` 与 `paid_amount` 可漂移并产生自相矛盾：用户登记 `payment_status=paid` 但 `paid_amount=0`（手滑、或先点状态未填金额），重算会把它当「已收」**跳过**，逾期口径却仍把它**标逾期**（`paid_amount=0 < amount_due`），收缴率也算它没收。同一条目，状态轴说「已收」、金钱轴说「没收」。这正是 `is_verified`（ADR-0005）、`overdue` 登记态（ADR-0007）被删掉的同一种病——一个能脱离权威事实漂移、卡不住任何口径的手工标记位，直接侵蚀 §3.2 关键报表口径一致性。

## 决策

**`unpaid` / `partial` / `paid` 改为从 `paid_amount` 对 `amount_due` 纯派生，实收登记只填 `paid_amount`。**

1. **派生规则**（单一真相轴 = `paid_amount`）：
   - `paid_amount == 0` → `unpaid`
   - `0 < paid_amount < amount_due` → `partial`
   - `paid_amount >= amount_due` → `paid`
2. **`voided` 是唯一非派生状态**，仅由系统在重算 / 作废流程写入（与现状一致，不变）。
3. **实收登记入参只接受 `paid_amount`**（外加显式作废动作）；不再接受用户手登记 `unpaid/partial/paid`。状态枚举从登记入参中移除，仅作派生只读投影对外暴露。
4. **ADR-0008 跳过判据改按 `paid_amount > 0`**：合同更正重算时「已收/部分已收条目不自动改写」的判据从读 `payment_status in (paid, partial)` 改为读 `paid_amount > 0`，语义不变、但不再依赖可漂移的标记位。`ledger_stale_after_correction` 派生风险口径不变。
5. **`ServiceFeeLedger.payment_status`** 继承来源租金台账，同步改为派生投影（其 `paid_amount` 本就是派生）。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 保留 `payment_status` 为可登记枚举 + 保存时校验与 `paid_amount` 一致 | 校验只能在写入时挡一次，跨更正 / 重算 / 部分收款多次写入仍会漂移；且「两个字段必须始终相等」本身就证明其中一个是冗余轴——直接派生比加校验更彻底（同 ADR-0007 选派生不选「翻态时校验」） |
| 保留登记枚举用于表达「减免后视为结清」（`paid_amount < amount_due` 但登记 `paid`） | 减免 / 坏账核销属财务总账，§4.2 明确 Out of Scope；MVP 无红冲（ADR-0008）。真要少收结清，走 `amount_due` 更正把应收改小，不靠翻状态——否则又回到「手工标记位盖过金钱事实」 |

## 关键冻结决策

1. **`paid_amount` 是实收唯一真相轴**，`unpaid/partial/paid` 是它对 `amount_due` 的派生投影。
2. **`voided` 是台账上唯一非派生状态**，仅系统写。
3. **实收登记只填金额**，不让用户手翻收款结果状态。
4. **MVP 不表达减免 / 结清少收**——需要时走 `amount_due` 更正（属 REQ-RNT-005 更正链路），不翻状态。

## 影响

已实施的工程项：

- **后端**：实收登记 API / schema 去掉 `payment_status` 入参（仅留 `paid_amount` 与作废动作）；`payment_status` 改为按 `paid_amount`/`amount_due` 计算的只读派生投影；ADR-0008 重算跳过逻辑判据从 `payment_status` 改 `paid_amount > 0`；`ServiceFeeLedger` 同步按来源金额派生。存量数据迁移：对 `payment_status` 与 `paid_amount` 不一致的历史行，以 `paid_amount` 为准重派生（`voided` 行不动）。
- **前端**：财务台账实收登记去掉手选 `unpaid/partial/paid`，只录 `paid_amount`；表格状态标签改读派生值。
- **domain-model**：§4.14 `payment_status` 描述改「派生投影、仅 `voided` 系统写」；§6 收缴率/逾期口径无需改（本就读 `paid_amount`）。
- **api-contract**：实收登记端点去 `payment_status` 入参，标注派生只读。
- **CONTEXT.md**：「逾期（派生口径）」「台账重算（已收条目不可变）」词条同步（本次随手落）。
- **traceability**：REQ-RNT-006 记代码收口证据。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`逾期（派生口径）`、`台账重算（已收条目不可变）`、`台账（账本语义·归属固化）` 词条
- domain-model §4.14 ContractLedgerEntry、§4.15 ServiceFeeLedger、§6 口径
- 相关簇：[ADR-0007](./ADR-0007-overdue-derived-not-marked.md)（逾期派生——本 ADR 同philosophy 收掉最后一个手工标记位）、[ADR-0008](./ADR-0008-stale-paid-ledger-derived-risk.md)（陈旧已收派生风险——跳过判据改 `paid_amount > 0`）、[ADR-0011](./ADR-0011-ledger-frozen-attribution.md)（台账固化归属）
