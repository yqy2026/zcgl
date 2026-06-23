# 2026-06-19 PRD Grill 代码收口跟踪

`/grill-with-docs prd.md`（2026-06-19）产出的代码层待实施项。文档基线（PRD / domain-model / CONTEXT / ADR-0019~0020 + ADR-0012/0013 修订 / CHANGELOG）已在该会话对齐，本记录跟踪**代码改造**进度（逐项进度以 git commit 追溯）。

详细文件:行证据、改造点与验收见实施详单：[`docs/archive/backend-plans/2026-06-19-prd-grill-code-followup.md`](../archive/backend-plans/2026-06-19-prd-grill-code-followup.md)。

本轮主题是「**收掉第二条可漂移轴 + 兑现历史承诺字段**」：七问贯穿一条主线——单一真相轴 + 派生优于手工标记位 + 历史事实冻结。有代码尾巴的是 Q2/Q4/Q5/Q6/Q7；Q1（仅措辞「委托协议」）与 Q3（确认既有派生模型，§4.15 本就全派生）**无代码改造**。竖切为可独立认领的 tracer bullet，全部 AFK。

## 台账（ADR-0019：payment_status 派生）

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| K1 | `payment_status` 派生化：实收登记入参去 `payment_status`（只留 `paid_amount` + 显式作废），`unpaid/partial/paid` 改派生只读（`paid_amount` 对 `amount_due`），重算跳过判据 `ledger_service_v2.py:603` 改 `paid_amount > 0`，`ServiceFeeLedger` 同步派生 | AFK | — | ADR-0019 | ✅ 已实施 |
| K2 | 存量迁移 + 前端去手选：迁移对 `payment_status` 与 `paid_amount` 不一致行按 `paid_amount` 重派生（`voided` 不动，仿 `20260616_drop_manual_overdue_status.py`）；前端财务台账实收登记去手选状态、只录金额、标签读派生 | AFK | K1 | ADR-0019 | ✅ 已实施 |

## 合同审计（ADR-0013 补漏：Q4+Q5）

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| K3 | `ContractAuditLog` 枚举收缩：`contract_group.py:545-550` action 删 `submit_review/approve/reject/reverse_review` 与 `expire`（已到期纯派生非操作），终集 `{terminate,void,start_correction,finalize_correction}`；删 `:555-556` `review_status_old/new` 列；补 `finalize_correction` 写入（定稿触发台账重算、§8 须审计）；确认无到期 job 物化 `status` | AFK | — | ADR-0013（审计日志半边，与其主体删除合并实施） | ✅ 已实施 |

## 主体（ADR-0020：Q6）

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| K4 | Contract 对手方名称快照：增 `lessor_name_snapshot`/`lessee_name_snapshot` 列 + 迁移；定稿（补录即生效 / `finalize_correction`）写入当时主档名、改名不回写；存量按当前主档名一次性回填；`LeaseContractDetail.tenant_name` 改从 lessee 快照同步 | AFK | — | ADR-0020 | ✅ 已实施 |
| K5 | Party 不合并 + 枚举修：`PartyReviewStatus.REVERSED` → `REJECTED`（+ 迁移存量 `reversed`→`rejected`）；驳回后保留 `rejected` 态，可编辑后重新提审，不引入反审闭环；确认建档查重提示在位、不引入主体合并能力（去重 = 建档查重） | AFK | — | ADR-0020 + §4.18 bug 修复 | ✅ 已实施 |

## 客户档案（Q7：代码已符合，仅回归断言）

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| K6 | **代码本就正确，本轮补回归断言**：`party/service.py` 已支持 `binding_type=all` 并集且按 `contract_id` 去重，schema 已含 `all`；新增断言锁定 `all` 模式 `historical_contract_count` 按合同 ID 去重（一份合同两绑定可见只算一次）、不被分析端单视图守卫拦截 | AFK | — | Q7 收口（无 ADR） | ✅ 已实施 |

## 验收

- **K1**：已实施。实收登记只接受 `paid_amount`，手填 `payment_status` 由 schema `extra="forbid"` 拒绝；`payment_status` 由 `paid_amount` 派生、不可登记出「paid 但 paid_amount=0」；重算跳过按 `paid_amount>0`；`ServiceFeeLedger.payment_status` 随来源台账金额派生；按 `payment_status` 的查询筛选仍按派生值生效。
- **K2**：已实施。新增迁移 `20260620_derive_ledger_payment_status.py` 归一历史非 `voided` 行；前端实收登记无手选状态控件，只提交金额和备注。
- **K3**：审计 action 枚举无 `submit_review/approve/reject/reverse_review/expire`；纠错定稿写 `finalize_correction`；无 `review_status_old/new` 残留；无定时任务把 `生效` 物化成 `已到期`。
- **K4**：Party 改名后历史合同详情显示**签署时快照名**不变；上游/下游/委托/直租全类型均有快照；`tenant_name` 与 `lessee_name_snapshot` 一致。
- **K5**：Party 驳回态值为 `rejected`、无 `reversed`；全库无主体合并端点；建档重复主体有查重提示、不自动合并。
- **K6**：多绑定用户 `all` 模式 `historical_contract_count` 按合同 ID 去重正确；该档案计数不被「分析必选视图」守卫拦截；分析端客户双指标仍受单视图约束（互不串口径）。

> 关联：K1~K6 均已落地；实施详单已归档至 `docs/archive/backend-plans/2026-06-19-prd-grill-code-followup.md`。
