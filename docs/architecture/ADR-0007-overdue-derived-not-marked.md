# ADR-0007: 「逾期」改为派生口径，删除 `overdue` 手工登记状态

**状态**: ✅ 已实施（2026-06-16）
**决策日期**: 2026-06-12
**实施日期**: 2026-06-16
**相关需求**: REQ-RNT-005（重算范围口径）、REQ-RNT-006（台账实收登记）、REQ-ANA-001（收缴率与逾期统计）

---

## 背景

台账条目 `payment_status` 枚举含手工可设的 `overdue` 值（`ledger_service_v2.py` `_MANUAL_LEDGER_PAYMENT_STATUSES`），靠用户经批量更新接口手工翻态；**没有任何定时任务或代码自动把过期未收条目翻成 `overdue`**（全库零命中）。

交叉核对（2026-06-12）发现「逾期」实际存在**三套互相打架的口径**：

1. **手工标记口径**：项目风险摘要 `payment_overdue` 与项目分析逾期金额（`project/service.py`）**只认 `payment_status == "overdue"`**——没人手工翻态就永远无逾期风险。
2. **派生口径**：逾期通知调度（`contract_group.py: get_overdue_with_contract_async`）按 `status in (unpaid, partial) AND due_date < today` 派生——**手工标了 `overdue` 的条目反而收不到逾期通知**（状态不在过滤列表里）。
3. **无日期口径**：按产权方逾期统计（`contract_group.py: sum_overdue_amount_by_ownership_async`）按 `status in (unpaid, partial, overdue)` 汇总，**完全没有 `due_date` 过滤**——未到期的未收条目也被算成「逾期」。

具体场景：6 月 1 日到期的租金条目无人动它（状态 `unpaid`），6 月 12 日看——产权方统计算逾期、通知调度算逾期、项目风险**不算**。同一条数据，报表打架，直接命中 PRD §3.2「关键报表口径一致性问题 ≤ 2 个/月」要防的事。

根因与已删的 `is_verified`（ADR-0005）同构：一个靠手工维护、又没人保证维护对的状态位，消费方各自为政。

## 决策

**逾期是算出来的，不是登记出来的。**

1. **删除 `overdue` 登记状态**：从 `_MANUAL_LEDGER_PAYMENT_STATUSES`、schema `Literal`、前端状态选项中移除；台账登记态只剩 `unpaid / partial / paid`（加系统写的 `voided`）。
2. **统一派生口径**：「逾期」= `due_date` 已过 且 `paid_amount < amount_due` 且状态非 `voided`。全系统逾期统计、逾期筛选、`payment_overdue` 项目风险、逾期通知一律按此派生。
3. **存量数据迁移**：现存 `overdue` 行迁回 `unpaid`（`paid_amount > 0` 的归 `partial`），写迁移。
4. **修复无日期口径**：`sum_overdue_amount_by_ownership_async` 补 `due_date < today` 过滤（否则它是「未收总额」不是「逾期金额」）。
5. **重算范围口径同步**：REQ-RNT-005「重算只调整未收条目」中未收 = `unpaid`（逾期只是 `unpaid`/`partial` 的派生标签，不再单列）。
6. **用户登记的事实只有两个**：收款结果（`unpaid/partial/paid`）与实收金额（`paid_amount`）；是否逾期不由用户表达。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 维持现状（手工 `overdue`） | 三套口径并存，报表打架；依赖录入纪律的状态位与 ADR-0005 删 `is_verified` 的理由同构——靠手工勾维护、没人保证勾对、消费方不一致 |
| 保留 `overdue` 态 + 加定时翻态任务 | 多一个定时任务、一份状态冗余和一类「任务没跑/跑挂导致状态滞后」的故障面；派生口径零成本天然实时一致 |
| 引入宽限期参数 | 不是保留手工标记的理由；宽限期若将来需要是给派生规则加参数（`due_date + N 天`），MVP 用 `due_date` 硬线 |

## 关键冻结决策

1. **台账登记态只剩 `unpaid / partial / paid`（+ 系统写 `voided`）**，无 `overdue`。
2. **逾期口径全局唯一**：`due_date` 已过且未收清且非 `voided`；任何「逾期」统计不得缺 `due_date` 过滤。
3. **不建自动翻态任务**：逾期不需要状态位，自然不需要翻态。

## 影响

已实施的工程项：

- **后端**：`ledger_service_v2.py` 已删 `_MANUAL_LEDGER_PAYMENT_STATUSES` 中 `overdue`；`schemas/contract_group.py` 与 `api/v1/contracts/ledger.py` 已拒绝 `overdue` 查询/批量登记；`project/service.py` 风险、汇总与分析统一用 `due_date < today and paid_amount < amount_due and status != voided` 派生；服务费台账通过来源台账 `source_ledger.due_date` 派生逾期；`crud/contract_group.py` `sum_overdue_amount_by_ownership_async` 已补 `due_date` 与未收清过滤；`20260616_drop_manual_overdue_status.py` 将存量 `overdue` 行迁回 `unpaid` / `partial`。
- **前端**：`types/ledger.ts`、`FinancialLedgerPage.tsx` 及测试已去掉 `overdue` 状态选项，逾期改为派生标签展示。
- **PRD**：REQ-RNT-005、REQ-RNT-006 已改（本次决策随手落）。
- **domain-model.md**：§4.14 `payment_status` 枚举与重算约束已改（本次决策随手落）。
- **CONTEXT.md**：已增「逾期（派生口径）」词条、修订「台账重算」词条（本次决策随手落）。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`逾期（派生口径）`、`台账重算（已收条目不可变）` 词条
- 相关簇：[ADR-0005](./ADR-0005-drop-property-certificate-verification.md)（删手工维护的孤立状态位）、[ADR-0006](./ADR-0006-drop-collection-module.md)（逾期处理闭环=台账逾期查询+实收登记）
