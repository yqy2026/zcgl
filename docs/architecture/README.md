# Architecture Decision Records (ADR)

## Purpose

集中维护架构决策记录，确保关键产品和技术选择可追溯。

命名规范：`ADR-NNNN-<slug>.md`，按决策顺序编号。

## ADR 列表

| 编号 | 文件 | 主题 | 状态 |
|---|---|---|---|
| ADR-0001 | [ADR-0001-party-role-architecture.md](./ADR-0001-party-role-architecture.md) | Party-Role 组织架构模型（主体 + 角色双层） | 已实施 |
| ADR-0002 | [ADR-0002-asset-review-no-approval-workflow.md](./ADR-0002-asset-review-no-approval-workflow.md) | 资产删除路由审批流，仅保留 `review_status` 两步确认 | 已实施 |
| ADR-0003 | [ADR-0003-contract-relation-direction-only.md](./ADR-0003-contract-relation-direction-only.md) | 合同上下游退化为收入/成本方向标记，删除逐对配对表与主合同覆盖风险 | 已实施 |
| ADR-0004 | [ADR-0004-settlement-rule-optional-at-creation.md](./ADR-0004-settlement-rule-optional-at-creation.md) | 合同关系 `settlement_rule` 创建时选填可缓填 | 已实施 |
| ADR-0005 | [ADR-0005-drop-property-certificate-verification.md](./ADR-0005-drop-property-certificate-verification.md) | 删除产权证 `is_verified` 核验状态和未核验风险 | 已实施 |
| ADR-0006 | [ADR-0006-drop-collection-module.md](./ADR-0006-drop-collection-module.md) | 删除催缴管理模块 | 已决策待实施 |
| ADR-0007 | [ADR-0007-overdue-derived-not-marked.md](./ADR-0007-overdue-derived-not-marked.md) | “逾期”改为派生口径，删除 `overdue` 手工登记状态 | 已决策待实施 |

## 当前架构基线

- 架构概览：[system-overview.md](./system-overview.md)
- 数据库设计基线：[database-design.md](./database-design.md)
- 产品需求入口：[../prd.md](../prd.md)
- 领域模型契约：[../specs/domain-model.md](../specs/domain-model.md)
- API 契约：[../specs/api-contract.md](../specs/api-contract.md)
- 实现追踪：[../traceability/requirements-trace.md](../traceability/requirements-trace.md)
