# 需求规格说明书已拆分

## 1. 当前状态

本文档已降级为兼容跳转页，不再作为需求 SSOT。

旧综合文档曾同时承载产品目标态、字段契约、API 契约、代码证据、测试证据和历史决策。当前这些职责已拆分到以下文档。

## 2. 当前入口

| 需求信息 | 当前入口 |
|---|---|
| 产品目标态、范围、业务规则、验收标准 | `docs/prd.md` |
| 领域对象、字段、状态机、统计口径 | `docs/specs/domain-model.md` |
| API、鉴权、数据范围、错误边界 | `docs/specs/api-contract.md` |
| REQ 实现状态、代码证据、测试证据 | `docs/traceability/requirements-trace.md` |
| 历史访谈、评审、As-Built、迁移过程 | `docs/archive/requirements-decisions/` |

## 3. 迁移说明

- 产品目标态已迁入 `docs/prd.md`。
- 字段、状态和统计口径已迁入 `docs/specs/domain-model.md`。
- API 和权限契约已迁入 `docs/specs/api-contract.md`。
- 实现证据已迁入 `docs/traceability/requirements-trace.md`。
- 旧综合文档中的过程信息归档摘要见 `docs/archive/requirements-decisions/2026-04-27-requirements-specification-process-archive.md`。

## 4. 维护规则

- 不再向本文档追加需求正文。
- 新需求直接修改 `docs/prd.md`。
- 字段、状态和统计口径变更同步 `docs/specs/domain-model.md`。
- API 契约变更同步 `docs/specs/api-contract.md`。
- 实现证据变更同步 `docs/traceability/requirements-trace.md`。
- 所有文档变更同步更新 `CHANGELOG.md`。
