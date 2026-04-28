# 数据库设计基线

## Status

**当前状态**: Active (2026-04-28)

本文是数据库设计的当前入口，不重复维护完整字段清单。字段、状态机和统计口径以 [`docs/specs/domain-model.md`](../specs/domain-model.md) 为准；API 与权限边界以 [`docs/specs/api-contract.md`](../specs/api-contract.md) 为准；实现状态和代码证据以 [`docs/traceability/requirements-trace.md`](../traceability/requirements-trace.md) 为准。

历史长版数据库设计已归档到 [`docs/archive/guides/database-design-2026-01.md`](../archive/guides/database-design-2026-01.md)，仅用于追溯早期设计，不作为当前开发依据。

## 当前数据模型主线

| 域 | 当前主对象 | 说明 |
|---|---|---|
| 主体 | `Party`、`UserPartyBinding` | 统一承载产权方、运营方、客户等主体身份和用户数据范围绑定 |
| 资产 | `Asset`、`AssetHistory`、`AssetDocument` | 资产主数据、历史、附件和审核信息 |
| 项目 | `Project`、`ProjectAsset` | 项目作为资产运营管理归集单元 |
| 合同 | `ContractGroup`、`Contract`、`ContractRelation` | 合同组承载一笔经营关系，合同基表承载上下游、委托、直租合同 |
| 台账 | `ContractLedgerEntry`、`ServiceFeeLedger` | 租金台账和代理服务费台账 |
| 审批 | `ApprovalInstance`、`ApprovalTaskSnapshot`、`ApprovalActionLog` | MVP 阶段承接资产审批和必要业务审批动作 |
| 权限 | `User`、`Role`、`Permission`、`ABACPolicy` | RBAC + ABAC 授权和数据策略 |

## 设计约束

- 新增或修改 ORM 字段后，先同步 [`docs/specs/domain-model.md`](../specs/domain-model.md)。
- 新增或修改 API 后，同步 [`docs/specs/api-contract.md`](../specs/api-contract.md) 和 [`docs/traceability/requirements-trace.md`](../traceability/requirements-trace.md)。
- 关键业务记录默认逻辑删除，不提供用户侧物理删除入口。
- 资产、项目、主体、合同进入关键业务流转前必须满足审核状态约束。
- 多资产合同金额按合同级口径记录，不做资产级金额拆分。
