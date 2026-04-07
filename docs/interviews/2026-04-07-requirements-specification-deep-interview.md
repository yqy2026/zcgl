# requirements-specification deep interview（进行中）

- 日期：2026-04-07
- 目标文档：`docs/requirements-specification.md`
- 模式：deep-interview / standard
- 状态：进行中
- 记录说明：本文件用于沉淀本轮采访问答与结论；未完成前不视为冻结纪要。

## 预检结论
- `docs/requirements-specification.md` 是当前 SSOT。
- 文档当前状态为 `Active Baseline (2026-04-06 评审修订)`。
- 文档已有 2026-02-28、2026-04-06 两轮冻结结论。
- 仓库已有 `docs/interviews/` 目录，故本轮采访记录沿用该目录。

## Interview Log

### Round 1
- Target: Intent / Scope
- Ambiguity (initial): 100%
- Question: 我看到这份 SSOT 文档已经在 2026-04-06 做过评审修订，也已有两轮“访谈冻结结论”；那你这次希望我优先澄清的是哪一类变更——补充新的冻结结论、修订已有冻结条目，还是围绕某个具体 REQ/章节新增或删减需求？
- Answer: 你自己看着办。
- Notes: 用户把优先级判断委托给我，说明执行决策边界相对开放，但“要解决什么问题”仍未明确，需要我基于文档现状主动收敛主线。

## 进度评分（Round 1 后）

| 维度 | 分数 | 说明 |
|---|---:|---|
| Intent Clarity | 0.45 | 用户授权我自行判断，但尚未明确本轮想解决的业务问题。 |
| Outcome Clarity | 0.20 | 仍不清楚访谈完成后是要补冻结结论、修文档，还是产出下阶段计划输入。 |
| Scope Clarity | 0.25 | 尚未锁定章节/REQ 域。 |
| Constraint Clarity | 0.70 | 已知 deep-interview、一轮一问、记录放 `docs/interviews/`。 |
| Success Criteria | 0.20 | 还没有明确“采访完成算什么”。 |
| Context Clarity | 0.80 | 已确认 SSOT 文档结构、现有冻结结论、现有 interviews 目录。 |

- Weighted ambiguity: 55.75%
- Readiness gates:
  - Non-goals: 未明确
  - Decision Boundaries: 部分明确（优先级可由我判断；是否落文档/落规格仍未明确）
  - Pressure pass: 未完成
- Next focus: Outcome / minimal success condition

### Round 2
- Target: Outcome
- Ambiguity: 55.75%
- Question: 我先按文档现状自行收敛：当前最需要补清的是“这轮采访结束后，什么产物算完成”——是 A) 只形成一份新的访谈纪要，B) 同时沉淀一份可进入下一步规划的 deep-interview spec，还是 C) 直接把结论回写到 `docs/requirements-specification.md`；如果必须三选一，你更希望我把哪一个当作本轮完成标准？
- Answer: A
- Notes: 已明确本轮完成标准是“只形成新的访谈纪要”，不要求在本轮直接回写 SSOT 或输出规划规格。

## 进度评分（Round 2 后）

| 维度 | 分数 | 说明 |
|---|---:|---|
| Intent Clarity | 0.45 | 仍知道是“围绕 requirements 做采访”，但业务动因还没说透。 |
| Outcome Clarity | 0.80 | 已明确本轮产物仅为访谈纪要。 |
| Scope Clarity | 0.35 | 仍未锁定要采访哪一个章节/REQ 域。 |
| Constraint Clarity | 0.80 | 记录位置与不直接回写 SSOT 已明确。 |
| Success Criteria | 0.55 | 已知道交付物形态，但纪要需覆盖什么结论仍不清楚。 |
| Context Clarity | 0.80 | 现有文档结构与历史冻结背景已清楚。 |

- Weighted ambiguity: 40.25%
- Readiness gates:
  - Non-goals: 未明确
  - Decision Boundaries: 已部分明确（本轮不要求回写 SSOT）
  - Pressure pass: 未完成
- Next focus: Non-goals / scope boundary

### Round 3
- Target: Non-goals / Scope
- Ambiguity: 40.25%
- Question: 既然这轮只产出访谈纪要、不直接改 SSOT，那我需要先锁定“不采访什么”：你是否同意我把“已标记 ✅ 的成熟模块先不碰，只聚焦仍是 🚧 / 📋 或 2026-04-06 新增冻结点的章节”作为本轮非目标边界？
- Answer: 不同意，你先审阅找出疑点，然后采访我。
- Notes: 用户否定了我按状态标签先裁剪范围的假设，要求先做证据型审阅，再基于疑点采访；这完成了一次明确的 pressure pass（先前关于“可先排除 ✅ 模块”的假设被推翻）。

## 审阅发现（基于文档证据）
1. **SSOT 当前同时承载“目标状态”和“迁移中状态”**：
   - §5.3 写明 `X-Perspective` 将废弃、分析/大屏改用 `?view_mode=`；
   - 但 REQ-SCH-003 / REQ-AUTH-002 追踪矩阵又把 `X-Perspective` 描述为“当前实现仍活跃使用 / 过渡状态”。
   - 疑点：这份 SSOT 应该冻结“目标契约”，还是允许保留迁移期实现说明？
2. **认证验收场景存在编号冲突**：
   - §12.3 的 `P6` 引用了 `REQ-AUTH-003`；
   - 但正文只有 `REQ-AUTH-001` 和 `REQ-AUTH-002`，且 §13 又说明 Deny-Overrides / SoD 属于 vNext。
   - 疑点：P6 是误编号、误纳入，还是其实应补一个独立 REQ-AUTH-003？
3. **“唯一需求真相”与“计划变更”并存的边界不清**：
   - 多处“代码证据”段落里写有“计划变更”；
   - 如果采访只产出纪要、不回写 SSOT，就需要先明确这些“计划变更”在纪要中的处理原则。

## 进度评分（Round 3 后）

| 维度 | 分数 | 说明 |
|---|---:|---|
| Intent Clarity | 0.60 | 已明确用户要我先做审阅、按疑点采访，而不是按状态先裁剪范围。 |
| Outcome Clarity | 0.80 | 本轮仍只产出访谈纪要。 |
| Scope Clarity | 0.50 | 采访范围缩小到“经审阅确认的疑点”，但尚未决定先解决哪类疑点。 |
| Constraint Clarity | 0.85 | 单轮一问、记录在 `docs/interviews/`、本轮不直接改 SSOT 已明确。 |
| Success Criteria | 0.65 | 需要形成一份围绕疑点的访谈纪要，但纪要最终采用哪种原则仍未定。 |
| Context Clarity | 0.90 | 已基于文档找到可验证的具体疑点。 |

- Weighted ambiguity: 27.75%
- Readiness gates:
  - Non-goals: 仍未显式定义
  - Decision Boundaries: 部分明确（先审阅后采访；本轮不直接回写 SSOT）
  - Pressure pass: 已完成（用户否定“先排除 ✅ 模块”的假设）
- Next focus: Decision boundary on SSOT semantics

### Round 4
- Target: Decision Boundaries / Intent
- Ambiguity: 27.75%
- Question: 我审阅后认为最核心的疑点是：这份 SSOT 到底应该冻结“目标态需求”，还是允许把 `X-Perspective` 这类“当前实现仍在过渡、未来将废弃”的信息继续写在正文里；你更希望我这次访谈纪要把哪一种原则定下来？
- Answer: 待补充
- Notes: 先确认 SSOT 的语义边界，再决定后续是否继续追问 `REQ-AUTH-003/P6` 这类具体矛盾。
