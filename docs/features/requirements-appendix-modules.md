# 模块与接口附录已迁移

## 1. 当前状态

本文档已降级为兼容跳转页，不再作为模块清单、接口清单或代码证据入口。

## 2. 当前入口

| 信息类型 | 当前入口 |
|---|---|
| API、鉴权、数据范围和错误边界 | `docs/specs/api-contract.md` |
| REQ 实现状态、代码证据、测试证据 | `docs/traceability/requirements-trace.md` |
| 产品范围和 Out of Scope | `docs/prd.md` |
| 领域对象和字段 | `docs/specs/domain-model.md` |

## 3. 迁移说明

- 当前 API 和权限契约已迁入 `docs/specs/api-contract.md`。
- 模块实现证据和测试证据已迁入 `docs/traceability/requirements-trace.md`。
- 旧模块清单和接口证据归档摘要见 `docs/archive/requirements-decisions/2026-04-27-requirements-appendices-process-archive.md`。

## 4. 维护规则

- 不再向本文档追加模块或代码证据正文。
- 新增 API 或模块边界变更时，同步更新 `docs/specs/api-contract.md`。
- 实现状态、代码证据或测试证据变化时，同步更新 `docs/traceability/requirements-trace.md`。
- 所有文档变更同步更新 `CHANGELOG.md`。
