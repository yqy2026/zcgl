# ADR-0004: 合同关系 settlement_rule 创建时选填可缓填

**状态**: 已实施（2026-06-12）
**决策日期**: 2026-06-10
**实施日期**: 2026-06-12
**相关需求**: REQ-RNT-001

---

## 背景

合同关系（`ContractGroup`）的 `settlement_rule` 原先在代码和数据库中是硬必填，但文档语义已经把它描述为“软必填、可缓填”。这造成了两个问题：

- 创建合同关系时必须一次性填满结算 JSON，用户无法先建关系、后补合同和结算信息。
- 台账实际并不读取 `settlement_rule`，而是按组内合同条款明细生成，因此硬必填带来摩擦但没有计算收益。

同时，`ContractGroupCreate.predecessor_group_id` 是续签残留字段；MVP 已明确不提供续签能力，`ContractRelationType.RENEWAL` 也随 ADR-0003 删除。

## 决策

1. `settlement_rule` 创建时改为选填、可缓填。
2. 数据库 `contract_groups.settlement_rule` 放宽为 nullable。
3. 后端创建和更新路径不得假设 `settlement_rule` 非空。
4. 台账生成仍只依据合同条款明细，不读取 `settlement_rule`。
5. 移除 `predecessor_group_id` 续签残留字段，不恢复续签或逐对配对关系。

## 被否决的方案

| 方案 | 否决原因 |
|---|---|
| 保持创建时硬必填并改文档 | 与 MVP 降摩擦方向相反，且台账不消费该字段 |
| 直接删除 `settlement_rule` | 字段仍可留存运营约定，删除会丢失潜在业务信息 |
| 立即与 `revenue_share_rule` 合并 | 语义边界需要单独评估，不属于本次减法范围 |

## 影响

- Schema: `ContractGroupCreate.settlement_rule` 改为可空。
- 数据库: 新增迁移放宽 `contract_groups.settlement_rule`。
- 服务层: 创建/更新合同关系时允许缺省或清空结算规则。
- 前端: 合同关系表单和详情页支持未配置结算规则。
- 文档: PRD、领域模型、追踪矩阵和 CHANGELOG 同步目标态。

## 参考

- [ADR-0003](./ADR-0003-contract-relation-direction-only.md)
- [需求追踪矩阵](../traceability/requirements-trace.md)
