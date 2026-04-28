# PRD 文档体系重构方案

## Status

✅ Completed

## Progress

- 2026-04-27：Phase 1 已启动，创建 `docs/prd.md`、`docs/specs/`、`docs/traceability/`、`docs/archive/requirements-decisions/` 骨架，并完成 PRD 产品目标态首轮抽取。
- 2026-04-27：Phase 3 已启动，`docs/specs/domain-model.md` 已扩展为字段、状态机和统计口径契约，`docs/specs/api-contract.md` 已扩展为端点、鉴权、数据范围和错误边界契约。
- 2026-04-27：Phase 4 已启动，`docs/traceability/requirements-trace.md` 已扩展为完整 REQ 追踪矩阵，集中承载产品状态、实现状态、代码证据和测试证据，并完成路径存在性校验。
- 2026-04-27：Phase 5 已启动，`docs/requirements-specification.md` 已降级为兼容跳转页，过程信息归档摘要已新增到 `docs/archive/requirements-decisions/2026-04-27-requirements-specification-process-archive.md`。
- 2026-04-27：Phase 6 已启动，`scripts/check_requirements_authority.py` 已新增 PRD/spec 实现证据守卫、traceability 路径存在性守卫和旧需求入口跳转页守卫，`make docs-lint` 已覆盖这些规则。
- 2026-04-27：Phase 7 已启动，`docs/features/requirements-appendix-fields.md` 与 `docs/features/requirements-appendix-modules.md` 已降级为兼容跳转页，字段漂移检查改为读取 `docs/specs/domain-model.md`，旧附录过程信息归档摘要已新增到 `docs/archive/requirements-decisions/2026-04-27-requirements-appendices-process-archive.md`。
- 2026-04-27：方案已完成并归档。当前需求入口、领域契约、API 契约、实现追踪和旧文档跳转页均已收口，`make docs-lint` 已覆盖新增守卫。

## Goal

把当前混合型 `docs/requirements-specification.md` 重构为清晰的产品与工程文档体系，解决“最终结果文档”和“过程信息、代码证据、历史迁移记录”交织的问题。

本方案只规划文档重构，不改变业务需求本身，不改代码。

## Problem

当前需求文档体系存在职责混杂：

- 主文档同时承担 PRD、SRS、实现台账、代码证据索引、验收矩阵和历史决策记录。
- 字段附录同时承担字段冻结、As-Built 对照、旧字段迁移策略和历史版本说明。
- 模块附录同时承担模块清单、接口清单、代码现状索引和 Out of Scope 代码骨架标记。
- 读者无法快速回答三个基本问题：产品到底要什么、字段/API 契约是什么、哪些代码已经实现。

## Principles

1. 最终态和过程态分离：PRD 只写产品目标态，历史过程归档。
2. 产品事实和工程证据分离：PRD 不出现代码路径、测试文件、实现状态细节。
3. 一个事实只放一个地方：字段口径、API 契约、代码证据各有唯一文档来源。
4. 先搬迁再清理：第一阶段只迁移和标注，不重新发明需求。
5. 可回溯：所有从旧文档迁出的内容保留来源或归档位置。

## Target Structure

| 目标文档 | 职责 | 不应包含 |
|---|---|---|
| `docs/prd.md` | 产品目标态：背景、范围、角色、核心流程、功能需求、验收标准 | 代码路径、测试文件、迁移过程、As-Built、实现状态 |
| `docs/specs/domain-model.md` | 业务对象、字段口径、状态机、枚举、统计公式 | 历史字段清理过程、代码证据 |
| `docs/specs/api-contract.md` | API 契约、权限边界、请求/响应关键规则 | 产品背景、实现文件路径 |
| `docs/traceability/requirements-trace.md` | REQ 到代码证据、测试证据、实现状态的映射 | 产品叙事、字段定义全文 |
| `docs/archive/requirements-decisions/` | 访谈冻结、历史决策、As-Built 对照、评审记录 | 当前目标态正文 |

## Migration Map

| 当前内容 | 目标位置 | 处理方式 |
|---|---|---|
| 背景、痛点、目标、MVP 范围 | `docs/prd.md` | 保留并压缩为产品语言 |
| 角色、数据范围、客户定义 | `docs/prd.md` + `docs/specs/domain-model.md` | PRD 留业务规则，领域模型留术语和状态 |
| 功能需求 `REQ-*` | `docs/prd.md` | 保留需求和验收，不保留代码证据 |
| 字段表、状态机、统计公式 | `docs/specs/domain-model.md` | 从字段附录和主文档抽取统一版本 |
| API 路径、鉴权契约、请求约束 | `docs/specs/api-contract.md` | 从主文档和模块附录抽取 |
| `代码证据`、测试证据、实现状态 | `docs/traceability/requirements-trace.md` | 从主文档追踪矩阵和代码证据块迁出 |
| As-Built 对照、旧字段 DROP 策略 | `docs/archive/requirements-decisions/` | 归档，保留历史价值，不进入目标态文档 |
| 访谈冻结结论、评审补充说明 | `docs/archive/requirements-decisions/` | PRD 只吸收最终结论，不保留过程叙事 |
| `requirements-appendix-fields.md` | 过渡后废弃或改为跳转页 | 迁移完成后只保留指向 `domain-model.md` 的说明 |
| `requirements-appendix-modules.md` | 过渡后废弃或并入 traceability | 迁移完成后只保留指向 traceability 的说明 |

## Proposed PRD Shape

`docs/prd.md` 建议控制在 400-600 行内：

1. 文档定位
2. 业务背景与问题
3. 产品目标与成功指标
4. MVP 范围与非范围
5. 角色、权限和数据范围规则
6. 核心业务流程
7. 功能需求
8. 非功能需求
9. 验收标准
10. vNext 候选能力

PRD 中禁止出现：`代码证据`、`As-Built`、`测试证据`、`当前实现`、`已废弃`、具体代码文件路径。

## Execution Plan

### Phase 1: Build New Skeletons

创建新文档骨架：

- `docs/prd.md`
- `docs/specs/domain-model.md`
- `docs/specs/api-contract.md`
- `docs/traceability/requirements-trace.md`
- `docs/archive/requirements-decisions/README.md`

同步更新：

- `docs/index.md`
- `CHANGELOG.md`

### Phase 2: Extract Product Target State

从 `docs/requirements-specification.md` 迁出产品目标态内容到 `docs/prd.md`。

保留内容：

- 背景、痛点、目标、范围
- 业务规则和核心流程
- 功能需求与验收条件
- 非功能需求
- vNext 候选能力

剔除内容：

- 代码证据
- 技术方案引用
- 实现依赖
- 历史版本说明
- 迁移过程说明

### Phase 3: Extract Domain And API Contracts

从主文档和字段附录抽取当前目标态：

- 字段、枚举、状态机、统计公式迁入 `domain-model.md`
- API 路径、鉴权规则、请求/响应约束迁入 `api-contract.md`

历史字段对照不进入目标态契约。

### Phase 4: Extract Traceability

将所有代码证据、测试证据、实现状态迁入 `requirements-trace.md`。

建议字段：

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|

产品状态与实现状态分开，避免继续把 ✅ 同时解释为产品验收和代码落地。

### Phase 5: Archive Process Material

将以下内容归档到 `docs/archive/requirements-decisions/`：

- 访谈冻结结论
- 2026-04-06 评审补充过程
- As-Built 字段对照
- 旧字段下线策略
- 历史迁移说明

归档后，PRD 只保留最终结论。

### Phase 6: Add Guardrails

增强文档检查脚本，避免再次混杂：

- `docs/prd.md` 不允许出现 `代码证据`、`As-Built`、`backend/src/`、`frontend/src/`。
- `docs/specs/domain-model.md` 不允许出现测试文件路径。
- `docs/traceability/requirements-trace.md` 中代码证据路径必须存在。
- `docs/plans/` 不允许完成态方案残留。

## Done When

1. `docs/prd.md` 可以独立回答“产品要做什么”。
2. `docs/specs/domain-model.md` 可以独立回答“字段、状态、口径是什么”。
3. `docs/specs/api-contract.md` 可以独立回答“接口和权限契约是什么”。
4. `docs/traceability/requirements-trace.md` 可以独立回答“做到哪了，证据在哪”。
5. 旧附录不再承载活跃事实，只作为跳转页或归档入口。
6. `make docs-lint` 通过。
7. `CHANGELOG.md` 记录重构。

## Open Decisions

1. `docs/requirements-specification.md` 最终处理方式：已决定保留为兼容跳转页。
2. `docs/features/requirements-appendix-fields.md` 和 `docs/features/requirements-appendix-modules.md` 最终处理方式：已决定保留为兼容跳转页。
3. PRD 的需求编号是否沿用当前 `REQ-*`：已决定沿用以降低迁移风险。

## Recommendation

建议采用“保留跳转页一段时间”的方式迁移：

- `requirements-specification.md` 改为指向 `prd.md`、`domain-model.md`、`api-contract.md`、`requirements-trace.md` 的入口。
- 两个 appendix 改为指向新契约文档的入口。
- 过程内容归档，不直接删除。

这样可以降低外部链接断裂风险，同时把阅读入口变清晰。
