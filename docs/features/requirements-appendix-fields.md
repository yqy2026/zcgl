# 字段附录已迁移

## 1. 当前状态

本文档已降级为兼容跳转页，不再作为字段冻结清单或字段变更入口。

## 2. 当前入口

| 信息类型 | 当前入口 |
|---|---|
| 领域对象、字段、状态机、枚举、统计口径 | `docs/specs/domain-model.md` |
| 产品需求与验收标准 | `docs/prd.md` |
| API 与权限契约 | `docs/specs/api-contract.md` |
| 实现状态、代码证据、测试证据 | `docs/traceability/requirements-trace.md` |

## 3. 迁移说明

- 当前字段契约已迁入 `docs/specs/domain-model.md`。
- 字段漂移检查已改为读取 `docs/specs/domain-model.md`。
- 历史字段冻结、As-Built 对照和旧字段下线策略归档摘要见 `docs/archive/requirements-decisions/2026-04-27-requirements-appendices-process-archive.md`。

## 4. 维护规则

- 不再向本文档追加字段正文。
- 新增或修改 ORM 字段时，同步更新 `docs/specs/domain-model.md`。
- 涉及 API 契约时，同步更新 `docs/specs/api-contract.md`。
- 涉及实现证据时，同步更新 `docs/traceability/requirements-trace.md`。
- 所有文档变更同步更新 `CHANGELOG.md`。
