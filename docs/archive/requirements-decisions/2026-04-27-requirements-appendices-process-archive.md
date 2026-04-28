# 旧需求附录过程信息归档

## 1. 文档定位

本文档归档 `docs/features/requirements-appendix-fields.md` 与 `docs/features/requirements-appendix-modules.md` 降级为兼容跳转页前承载的历史信息。

当前字段、API、模块和实现证据不以旧附录为准：

- 字段、状态、统计口径：`docs/specs/domain-model.md`
- API、鉴权、数据范围和错误边界：`docs/specs/api-contract.md`
- REQ 实现状态、代码证据和测试证据：`docs/traceability/requirements-trace.md`

如需查看旧附录完整正文，使用 Git 历史追溯本文件创建前的对应路径。

## 2. 归档来源

| 旧文档 | 原职责 | 当前归属 |
|---|---|---|
| `docs/features/requirements-appendix-fields.md` | 字段冻结清单、字段状态、历史 As-Built 对照、旧字段下线策略 | `docs/specs/domain-model.md` + Git 历史 |
| `docs/features/requirements-appendix-modules.md` | 模块清单、接口清单、代码路径、测试建议 | `docs/specs/api-contract.md` + `docs/traceability/requirements-trace.md` |

## 3. 已吸收内容

| 历史内容 | 当前归属 |
|---|---|
| Asset、Project、ContractGroup、Contract 等字段清单 | `docs/specs/domain-model.md` |
| 审核状态、合同生命周期、台账状态 | `docs/specs/domain-model.md` |
| 统计指标公式和口径 | `docs/specs/domain-model.md` |
| API 模块、端点和权限边界 | `docs/specs/api-contract.md` |
| 代码证据和测试证据 | `docs/traceability/requirements-trace.md` |
| 产权证、权属方 Out of Scope 说明 | `docs/prd.md`, `docs/specs/domain-model.md`, `docs/specs/api-contract.md` |

## 4. 后续维护规则

- 不再向旧附录追加活跃需求事实。
- ORM 字段变化同步 `docs/specs/domain-model.md`。
- API 或模块边界变化同步 `docs/specs/api-contract.md`。
- 代码证据或测试证据变化同步 `docs/traceability/requirements-trace.md`。
- 需要保留历史过程时追加到 `docs/archive/requirements-decisions/`。
