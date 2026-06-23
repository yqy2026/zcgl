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
| ADR-0006 | [ADR-0006-drop-collection-module.md](./ADR-0006-drop-collection-module.md) | 删除催缴管理模块 | 已实施 |
| ADR-0007 | [ADR-0007-overdue-derived-not-marked.md](./ADR-0007-overdue-derived-not-marked.md) | “逾期”改为派生口径，删除 `overdue` 手工登记状态 | 已实施 |
| ADR-0008 | [ADR-0008-stale-paid-ledger-derived-risk.md](./ADR-0008-stale-paid-ledger-derived-risk.md) | 合同更正后陈旧已收台账改为派生风险 ledger_stale_after_correction，删除孤儿响应值式标记 | ✅ 已实施 |
| ADR-0009 | [ADR-0009-perm-admin-grant-boundary.md](./ADR-0009-perm-admin-grant-boundary.md) | 权限管理员授予边界：业务角色不得由 perm_admin 授予（含授予自己），封堵单人自我提权 | ✅ 已实施 |
| ADR-0010 | [ADR-0010-manager-derived-owner-intrinsic.md](./ADR-0010-manager-derived-owner-intrinsic.md) | 运营方单一权威轴：`Asset.manager_party_id` 随项目派生，`owner_party_id` 挂资产独立必填 | ✅ 已实施 |
| ADR-0011 | [ADR-0011-ledger-frozen-attribution.md](./ADR-0011-ledger-frozen-attribution.md) | 台账是账本：条目生成时固化归属（项目/产权方/运营方/资产），历史口径不 join 当前 | 🟡 已决策待实施 |
| ADR-0012 | [ADR-0012-contract-relation-single-project.md](./ADR-0012-contract-relation-single-project.md) | 合同关系锁单项目，代理合同跨项目靠共享盖章扫描件、不靠跨项目合同关系 | ✅ 已实施 |
| ADR-0013 | [ADR-0013-drop-contract-approval-workflow.md](./ADR-0013-drop-contract-approval-workflow.md) | 删除合同审批流（提审/审核/联审/反审核/制审分离降级 vNext），保留最小合同生命周期 | 🟡 已决策待实施 |
| ADR-0014 | [ADR-0014-drop-project-review-lifecycle.md](./ADR-0014-drop-project-review-lifecycle.md) | 删除 Project review 生命周期（零消费孤儿列），Party/Asset review 各自保留 | 🟡 已决策待实施 |
| ADR-0015 | [ADR-0015-notification-tier-keyed-idempotency.md](./ADR-0015-notification-tier-keyed-idempotency.md) | 通知幂等按优先级档位（不按未读、不按天），修逾期日刷屏与到期升级塌缩 | 🟡 已决策待实施 |
| ADR-0016 | [ADR-0016-wecom-per-user-push.md](./ADR-0016-wecom-per-user-push.md) | 企业微信推送按人定向（应用消息），删群机器人广播，§8 自洽，非企业微信待办 | 🟡 已决策待实施 |
| ADR-0017 | [ADR-0017-asset-code-owner-segment-generation.md](./ADR-0017-asset-code-owner-segment-generation.md) | `asset_code` 按产权方编码段自动生成，身份锚、生成后冻结、owner 更正不重编号（段来源经 ADR-0018 改用 owner `party_code` 派生） | 🟡 已决策待实施 |
| ADR-0018 | [ADR-0018-project-code-operator-segment-and-unified-code-segment.md](./ADR-0018-project-code-operator-segment-and-unified-code-segment.md) | `project_code` 按运营方编码段生成；三类业务编码段统一由 `party_code` 派生（撤 ADR-0017 专用 `asset_code_prefix` 字段） | 🟡 已决策待实施 |
| ADR-0019 | [ADR-0019-payment-status-derived-from-paid-amount.md](./ADR-0019-payment-status-derived-from-paid-amount.md) | 台账 `unpaid/partial/paid` 改为从 `paid_amount` 派生，实收登记只填金额；`voided` 唯一非派生、跳过判据改 `paid_amount > 0` | 🟡 已决策待实施 |
| ADR-0020 | [ADR-0020-party-identity-history-stability.md](./ADR-0020-party-identity-history-stability.md) | 主体历史身份稳定性：MVP 不合并主体（去重=建档查重）+ 合同对手方名称定稿固化快照，当前身份 live / 历史引用冻结 | 🟡 已决策待实施 |

## 当前架构基线

- 架构概览：[system-overview.md](./system-overview.md)
- 数据库设计基线：[database-design.md](./database-design.md)
- 产品需求入口：[../prd.md](../prd.md)
- 领域模型契约：[../specs/domain-model.md](../specs/domain-model.md)
- API 契约：[../specs/api-contract.md](../specs/api-contract.md)
- 实现追踪：[../traceability/requirements-trace.md](../traceability/requirements-trace.md)
