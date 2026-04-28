# 旧需求规格过程信息归档

## 1. 文档定位

本文档归档 `docs/requirements-specification.md` 降级为兼容跳转页前承载的历史过程信息。

当前产品目标态、领域契约、API 契约和实现追踪不以本文档为准：

- 产品目标态：`docs/prd.md`
- 领域模型契约：`docs/specs/domain-model.md`
- API 契约：`docs/specs/api-contract.md`
- 实现追踪矩阵：`docs/traceability/requirements-trace.md`

如需查看旧综合文档的完整历史正文，使用 Git 历史追溯本文件创建前的 `docs/requirements-specification.md`。

## 2. 归档来源

- 来源文档：`docs/requirements-specification.md`
- 来源状态：Active Baseline，混合承载产品目标态、代码证据、测试证据、评审过程、历史迁移说明。
- 降级原因：新文档体系已拆分职责，旧综合文档不再作为当前 SSOT。

## 3. 已吸收进当前目标态的结论

| 历史结论 | 当前归属 |
|---|---|
| 资产、项目、合同组、客户、搜索、权限、分析、PDF、审批、系统管理为 MVP 主范围 | `docs/prd.md` |
| 产权证管理与权属方管理不纳入 MVP 验收 | `docs/prd.md`, `docs/specs/domain-model.md`, `docs/specs/api-contract.md` |
| 合同组是租赁主业务对象 | `docs/prd.md`, `docs/specs/domain-model.md` |
| 承租模式与代理模式并存，但单合同组不混用 | `docs/prd.md`, `docs/specs/domain-model.md` |
| 一个资产不允许关联多个有效合同组 | `docs/prd.md`, `docs/specs/domain-model.md` |
| 不存在续签；到期后继续合作按新签处理 | `docs/prd.md`, `docs/specs/domain-model.md`, `docs/specs/api-contract.md` |
| 多资产合同金额按合同级口径，不做资产级金额拆分 | `docs/prd.md`, `docs/specs/domain-model.md` |
| 客户按合同对方主体口径定义，列表唯一键为 `party_id` | `docs/prd.md`, `docs/specs/domain-model.md` |
| 用户数据范围由主体绑定自动决定，常规查询不要求手动切换 | `docs/prd.md`, `docs/specs/domain-model.md`, `docs/specs/api-contract.md` |
| 分析和大屏通过 `view_mode=owner|manager` 表达统计口径 | `docs/prd.md`, `docs/specs/domain-model.md`, `docs/specs/api-contract.md` |
| `X-Perspective` HTTP header 已废弃 | `docs/specs/api-contract.md` |
| ABAC 为 MVP 必须能力，权限管理员不可查看业务数据 | `docs/prd.md`, `docs/specs/api-contract.md` |
| Deny-Overrides 和职责分离为 vNext 候选 | `docs/prd.md` |
| 风险标签 MVP 仅人工标注，规则自动标注推迟到 vNext | `docs/prd.md` |
| 合同反审核和纠错以作废、冲销和重建闭环处理 | `docs/prd.md`, `docs/specs/domain-model.md` |
| 台账覆盖率、租金收缴率、收入拆分和客户双指标采用冻结口径 | `docs/prd.md`, `docs/specs/domain-model.md` |

## 4. 已迁出的实现证据

旧综合文档中的 `代码证据`、测试证据和 REQ 状态表已迁入 `docs/traceability/requirements-trace.md`。

迁移后的追踪矩阵将产品状态和实现状态拆分，避免继续用单个状态标记同时表达产品验收与代码落地。

## 5. 已归档的过程信息类型

旧综合文档中的以下过程信息不再进入 PRD 或规格契约：

- 业务访谈冻结说明。
- 2026-04-06 评审补充过程。
- 已采纳和已撤回的方案描述。
- As-Built 字段对照和历史命名说明。
- 旧字段下线策略和历史迁移说明。
- 已落地代码证据快照。

这些信息保留在 Git 历史和本归档摘要中，当前目标态只看 `prd.md`、`specs/` 和 `traceability/`。

## 6. 后续维护规则

- 新产品需求修改 `docs/prd.md`。
- 字段、状态、统计口径修改 `docs/specs/domain-model.md`。
- API、鉴权、错误和数据范围契约修改 `docs/specs/api-contract.md`。
- 代码证据和测试证据修改 `docs/traceability/requirements-trace.md`。
- 历史决策只追加归档，不回写旧综合文档。
