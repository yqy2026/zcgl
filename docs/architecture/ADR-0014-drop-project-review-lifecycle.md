# ADR-0014: 删除 Project review 生命周期——孤儿列，名实不符

**状态**: 🟡 已决策，待实施（2026-06-16）
**决策日期**: 2026-06-16
**相关需求**: REQ-PRJ-001/002/003（项目域）、REQ-PTY-001/002（主体域）、PRD §7.2/§7.8

---

## 背景

domain-model §4.2 给 `Project` 配了完整 review 生命周期：`review_status`（`draft/pending/approved/rejected`，不可逆驳回）、`review_by`、`reviewed_at`、`review_reason`；CONTEXT「轻量提交标记」词条进一步描述「Project 用终态 `rejected`（不可逆，驳回即回 draft 重填）」。

代码核对（2026-06-16）：

- `models/project.py`：`ProjectReviewStatus` 枚举 + `review_status` 列（带默认值）**仅此而已**。
- `services/project/service.py`、`api/v1/assets/project.py`：**零引用**——无提审/审核/驳回流转、无门禁、无按 `review_status` 的筛选、API 不暴露不写入。

即 `Project.review_status` 是**孤儿列**：定义了、给了默认值，但没有任何东西流转它、卡它、读它、过滤它。文档把它描述得像个真生命周期，代码里它从未活过——与已删的 `is_verified`（ADR-0005）同型（零消费 + 消费者从未实现）。

对比佐证「项目不需要它」：

- **Asset** 要 `approved`——它是台账与经营统计的事实底座（ADR-0002 资产确认）。
- **Party** 要 `approved`——`assert_parties_approved`（`services/party/service.py`）在合同补录/产权证权利人引用前要求关联主体全部已审核，是 REQ-PTY-002「引用主体必须来自已审核 Party」的载体，真承重。
- **Project** 只是资产的「业务管理归集」桶（ADR-0010 决策访谈语），无任何下游会问「这个项目审了没」。

## 决策

**删除 Project 的 review 生命周期（删而非冻——纯孤儿列、无外部副作用）：**

1. 删 `Project.review_status` / `review_by` / `reviewed_at` / `review_reason` 列与 `ProjectReviewStatus` 枚举。
2. 修正 CONTEXT「轻量提交标记」：去掉 Project 那半边「`rejected` 终态生命周期」的名实不符描述；该词条收敛为 Party 的轻量提交语义（Asset 有自己的「资产确认」词条）。
3. **Party 侧不动**——其两步审核真承重，保留；PRD REQ-PTY 补一行点明「Party 支持两步审核」让契约与 `assert_parties_approved` 对齐。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 补建 Project 提审/审核/驳回流转 | 无下游消费——没有任何统计、门禁、引用要求「项目已审」；为没人用的状态建流转是过度建模 |
| 冻结保留孤儿列 | 纯孤儿列、无外部副作用，按「删而非冻」拆净（区别于接副作用的死代码与可冻的静态骨架） |
| 连 Party review 一起删 | Party review 真承重（编辑/删除门禁 + `assert_parties_approved` 背 REQ-PTY-002 已审主体引用），删则合同/产权证主体引用失去合格性门禁 |

## 关键冻结决策

1. **Project 无 review 生命周期**——项目是归集桶，不做提交确认。
2. **Party / Asset review 各自保留**（都承重，且都不做职责互斥，见 ADR-0002）。

## 影响

待实施的工程项：

- **后端**：删 `Project.review_status`/`review_by`/`reviewed_at`/`review_reason` 列与 `ProjectReviewStatus` 枚举；新增 Alembic 迁移 drop 列；清理字段白名单与任何残留引用；补路由/字段漂移护栏测试。
- **domain-model**：§4.2 Project 删 review 四列（本次随手落）。
- **CONTEXT.md**：「轻量提交标记」词条去 Project 半边、收敛为 Party（本次随手落）。
- **PRD**：REQ-PTY-001 补「Party 支持两步审核」一行；REQ-PRJ 无需改（本就未声称项目 review）（本次随手落）。
- **traceability**：REQ-PRJ / REQ-PTY 记代码收口缺口。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`轻量提交标记`、`资产确认（两步生命周期）` 词条
- `models/project.py`、`services/party/service.py`（`assert_parties_approved`）
- 相关簇：[ADR-0005](./ADR-0005-drop-property-certificate-verification.md)（删 `is_verified` 孤儿状态——同型）、[ADR-0002](./ADR-0002-asset-review-no-approval-workflow.md)（资产确认两步、不做职责互斥）
