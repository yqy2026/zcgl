# ADR-0013: 删除合同审批流——保留最小合同生命周期，提审/审核/联审/反审核降级回 vNext

**状态**: 🟡 已决策，待实施（2026-06-16）
**决策日期**: 2026-06-16
**相关需求**: REQ-RNT-003（合同盖章扫描件辅助补录）、REQ-RNT-005（合同更正与作废留痕）、REQ-RNT-006（台账自动化）、PRD §4.2 Out of Scope（合同审批和状态门禁）、§10 vNext（合同审批与状态流转）

---

## 背景

PRD §4.2 明文「合同审批和状态门禁……不做合同提审、审核、生效、反审核或状态流转限制」；CONTEXT「合同补录」词条「不通过合同审批、合同状态流转……限制录入」；§10 把「合同审批与状态流转（联审、反审核、制审分离）」整体划给 vNext。

但代码核对（2026-06-16，`services/contract/contract_group_service.py`）发现一套**完整合同审批流提前建好且在跑**，并卡着编辑/删除/更正：

- `submit_review`（DRAFT → 待审）、`approve`（待审 → 生效 + 已审）、驳回（待审 → 草稿）、`reverse`（生效 → 终止 + 反审核 REVERSED）、`submit_group_review`（批量组提审）。
- **`_requires_joint_review`（联审判定）**——正是 §10 vNext 点名的「联审」。
- 更正发起门禁 `review_status == APPROVED`、编辑门禁 `status == DRAFT`、删除门禁 `status == ACTIVE`、组「生效中」由组内合同 `status` 派生。

即：§4.2 说不做、§10 划给 vNext 的合同提审/审核/联审/反审核/制审分离，代码全建了。这与 ADR-0002 删除的资产路由审批流**同一性质**——接入副作用、在跑、与 MVP 范围冲突的功能，不是静态骨架。

**Provenance——它是已移除需求 REQ-RNT-004 的残留实现**：归档计划（`docs/archive/backend-plans/2026-03-29-...joint-review...`、`2026-03-06-m2-contract-lifecycle-and-ledger.md`）记 REQ-RNT-004 =「合同组主审 + 关键合同联审」，实现即 `POST /contract-groups/{id}/submit-review` 批量提审 + 合同级 approve/reject + `_requires_joint_review` 策略引擎。REQ-RNT-004 是个**复合需求**，含两半：主合同覆盖（配对）+ 合同联审。trace（`requirements-trace.md` REQ-RNT-004）已标「已移除/已清理」，但引的迁移 `20260612_drop_contract_relations.py` 只清了**配对/覆盖**半边（ADR-0003）；**联审半边的 `_requires_joint_review`/`submit_review`/`submit_group_review` 及 `test_contract_joint_review.py` 漏拆、活到现在**。所以本删除不是新决定，而是**补完 REQ-RNT-004 移除时只做了一半的清理**——已被移出基线的需求的残留实现，按「删而非冻」拆净。

## 决策

**按 ADR-0002 同尺度处置：删除合同审批流（删而非冻），保留 REQ-RNT-005 / 台账到期真正需要的最小合同生命周期。**

**砍掉（降级回 vNext）：**

1. `ContractReviewStatus`（草稿/待审/已审/反审核）整列。
2. `ContractLifecycleStatus.PENDING_REVIEW`（待审态）。
3. `submit_review` / `approve` / 驳回 / `reverse`-as-review / `submit_group_review` / `_requires_joint_review` 这套提审—审核—联审—反审核—制审分离动作及端点。

**保留（最小生命周期，承载 REQ-RNT-005 更正、§4.14 台账到期、删除保护）：**

1. **补录即生效**：合同补录直接落「生效」事实底座，不经提审/审核步骤（对齐 CONTEXT「合同补录」零摩擦先存）。
2. **`已到期` / `已终止`**：按 `effective_to` 派生到期 + 显式终止动作；台账据此判定何时停生成未来条目（§4.14），生效中合同删除保护保留。
3. **纠错草稿**：`草稿 → 定稿` 一步留着承载 REQ-RNT-005 更正；`草稿` 仅表示「纠错草稿/录入中」，不再是「待审」。
4. **更正门禁改绑生命周期状态**：纠错草稿发起条件从 `review_status == APPROVED` 改为「只能从生效合同发起」，不再依赖被删的 review 列。

净效果：`ContractLifecycleStatus` 从 {草稿, 待审, 生效, 已到期, 已终止} 收成 {草稿(纠错/录入中), 生效, 已到期, 已终止}；`ContractReviewStatus` 整删。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 保留合同审批流、改 PRD 把它纳入 MVP | §4.2/§10 一致把审批流划在 MVP 外；与 ADR-0002（资产不做路由审批流）尺度矛盾；联审/制审分离是典型 vNext 流程引擎能力 |
| 冻结而非删除（保留死代码） | 该审批流接入了状态门禁副作用、在跑，非静态骨架；按 ADR-0002 原则，接副作用的要拆干净 |
| 连最小生命周期一起砍（合同无任何状态） | REQ-RNT-005 更正留痕需区分定稿/纠错草稿，§4.14 台账到期需生效/到期/终止；砍光则两者失去载体 |

## 关键冻结决策

1. **合同不做路由审批流**（提审/审核/联审/反审核/制审分离全降级 vNext），与 ADR-0002 一致。
2. **补录即生效**，无「待审」步骤。
3. **最小生命周期是真承重**（更正 + 台账到期 + 删除保护），保留；更正门禁改绑生命周期状态。

## 影响

待实施的工程项：

- **后端**：删 `ContractReviewStatus` 列与 `PENDING_REVIEW` 态、`submit_review`/`approve`/驳回/`reverse`/`submit_group_review`/`_requires_joint_review` 及对应端点；`start_correction` 门禁改绑生命周期状态；组「生效中」派生改读收缩后的状态集；补录落库直接置「生效」；新增 Alembic 迁移迁移存量 `review_status` 与 `PENDING_REVIEW` 行（待审→草稿或生效按业务定，已审→生效，反审核→终止）；补路由删除护栏与迁移清理测试。
- **domain-model**：§4.7 Contract 删 `review_status`/`review_by`/`reviewed_at`/`review_reason`，`status` 枚举收缩，约束改述（本次随手落）。**§4.16 ContractAuditLog（2026-06-19 grill 补漏）**：action 枚举删 `submit_review`/`approve`/`reject`/`reverse_review`，并删 `expire`（`已到期`是派生状态非操作、不入审计，同逾期口径），保留 `terminate`/`void`/`start_correction` 并补 `finalize_correction`（定稿触发台账重算的关键操作，§8 须审计），最终 action 集 = `{terminate, void, start_correction, finalize_correction}`；删 `review_status_old`/`review_status_new` 字段（`ContractReviewStatus` 已整删）。此前本影响段只列 §4.7、漏列 §4.16，致审计日志残留审批流词汇。
- **PRD**：§4.2 措辞收紧为「不做 BPM 合同审批流（提审/审核/联审/反审核/制审分离）」，明确 MVP 保留最小生命周期；§10 vNext「合同审批与状态流转」保留（本次随手落）。
- **CONTEXT.md**：「合同补录」词条补「补录即生效、最小生命周期、不做审批流」，可增「最小合同生命周期」词条（本次随手落）。
- **traceability**：REQ-RNT-003 / REQ-RNT-005 记代码收口缺口；**修正 REQ-RNT-004 行**——「已清理」需补注「联审半边（`_requires_joint_review`/`submit_review`/`submit_group_review`/`test_contract_joint_review.py`）此前漏拆，由 ADR-0013 补完」。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`合同补录`、`合同关系（建模对象）` 词条
- `services/contract/contract_group_service.py`（审批流现状）
- domain-model §4.3 ContractGroup、§4.7 Contract
- 相关簇：[ADR-0002](./ADR-0002-asset-review-no-approval-workflow.md)（删资产路由审批流——同性质同处置）、[ADR-0012](./ADR-0012-contract-relation-single-project.md)（合同关系单项目）
