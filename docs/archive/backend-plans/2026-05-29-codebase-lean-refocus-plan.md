# 代码库瘦身与业务聚焦方案

## Status

✅ 已完成（2026-05-31 第一轮落地并归档）

第一轮已完成：冻结 Out of Scope 可见面、系统监控最小化、文档 AI Provider 统一入口、Excel 审计归档，以及 auth middleware 拆分方案独立立项。

## 1) 问题诊断

### 1.1 当前基线

项目主轴资产运营已完成代码、测试和 SSOT 收口，`docs/traceability/requirements-trace.md` 中 `REQ-PRJ-003`、`REQ-RNT-001`、`REQ-RNT-002`、`REQ-SCH-001` 均为“已有证据”。下一阶段的主要矛盾不再是继续补项目主轴，而是降低 Out of Scope、历史基础设施和过早抽象带来的维护成本。

| 维度 | 现状 | 判断 |
|------|------|------|
| 项目主轴 | 已归档完成 | 不再作为本方案实施范围 |
| 产权证 / 权属方 | PRD/spec/traceability 标为 MVP 外，但后端路由和前端入口仍暴露 | 第一优先级冻结 |
| 文档 AI Provider | 配置、路由、测试仍覆盖 GLM/Qwen/DeepSeek/Hunyuan | 先统一入口，不直接删除 provider |
| Excel 模块 | 文件较多，但 import/export 已是大文件 | 先审计调用关系，不以文件数为合并目标 |
| system monitoring | 自建监控子模块和系统域能力偏重 | 先最小化监控 API，保留 health |
| auth middleware | 单文件过大，混合认证、鉴权、数据范围 | 单独架构治理，不放入瘦身第一轮 |

### 1.2 已确认的 SSOT 冲突

| 冲突 | 证据 | 处理原则 |
|------|------|----------|
| 产权证 / 权属方为 Out of Scope，但仍作为可见功能暴露 | `docs/prd.md`、`docs/specs/domain-model.md`、`docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md` 标注 MVP 外；代码仍注册 `/ownerships`、`/property-certificates`，前端菜单仍有“权属方管理 / 产权证管理” | 以 PRD/spec 为准，冻结可见面 |
| `REQ-SCH-001` 仍写搜索覆盖产权证 | 追踪矩阵中全局搜索说明包含产权证 | 搜索对象范围回收，产权证不再作为 MVP 搜索对象 |
| AI provider 删除假设不足 | 当前配置默认值、PDF 路由测试和 LLM 测试仍覆盖多个 provider | 先统一 provider 入口和失败语义，删除动作另行确认 |

### 1.3 根因

代码库中存在三类负担：

1. **需求边界负担**：MVP 外功能仍有路由、菜单、页面和测试入口，给用户和维护者制造“已纳入产品”的错觉。
2. **基础设施负担**：自建监控、过多 AI provider、系统任务等能力超过 0→1 阶段的实际需要。
3. **架构负担**：auth middleware、Excel 等模块存在可读性和局部性问题，但不是所有问题都应该用“合并文件”解决。

本方案的修正原则：**先冻结暴露面，再清理基础设施，最后再做架构拆分；不把文件数减少误当成复杂度降低。**

---

## 2) 目标与原则

### 2.1 目标

1. **冻结不属于 MVP 的可见功能**：Out of Scope 功能不再出现在普通用户路径、注册路由和搜索结果中。
2. **减少可替代基础设施**：系统监控收敛到最小健康检查，避免维护一套半成品监控面。
3. **收口 AI 调用入口**：统一 provider 选择和错误语义，先降低调用分散度，再决定是否删除 provider。
4. **保护已验收主线**：项目、资产、合同关系、台账、搜索等已有证据需求不得回退。

### 2.2 原则

- 用冻结和失败显性化替代“半可用”入口。
- 每个清理动作必须同步 SSOT 和测试。
- 不为减少文件数牺牲局部性。
- 不把 middleware 拆分伪装成瘦身；认证、鉴权、数据范围属于高风险架构治理。
- 不继续为 MVP 外功能补兼容和用户路径。

---

## 3) 修正后的实施计划

### Phase 1：冻结 Out of Scope 可见面（预计 0.5-1 天）🔴 第一优先级

#### 1.1 范围

| 区域 | 动作 |
|------|------|
| 后端路由 | 停止注册 `/ownerships`、`/property-certificates` |
| 前端菜单 | 移除“权属方管理 / 产权证管理”可见入口 |
| 前端路由 | 普通用户不可进入权属方和产权证管理页；如保留内部组件，路由不得作为产品入口暴露 |
| 面包屑 / 路由常量 | 清理可见入口映射，避免导航仍指向冻结功能 |
| 全局搜索 | 后端 `services/search/service.py` 搜索索引对象范围移除 `PropertyCertificate`；前端独立过滤作为防御层可保留。`REQ-SCH-001` MVP 对象范围回收为资产、项目、合同关系、合同、客户等已验收对象 |
| SSOT | 更新 API 契约、追踪矩阵和计划说明，明确产权证 / 权属方路由已冻结 |

#### 1.2 不做

- 不删除资产中的 `owner_party_id`、`owner_party_name`、`ownership_status` 等资产确权属性。
- 不删除 Party 主体能力。权属方管理模块冻结不等于主体主档冻结。
- 不删除产权证 / 权属方 ORM 和迁移文件，避免破坏既有数据库结构。
- 不删除产权证 / 权属方的现有测试文件，改为 `@pytest.mark.skip("Out of Scope - route frozen")` 并统计跳过数量。后续启用时直接取消 skip 即可恢复。

#### 1.3 验收标准

- 后端注册路由中不再包含 `/ownerships`、`/property-certificates`。
- 前端菜单不再出现“权属方管理 / 产权证管理”。
- 全局搜索不再返回产权证对象。
- `docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md`、`CHANGELOG.md` 已同步。
- `make docs-lint` 通过。
- 相关后端 route/import 测试、前端菜单/路由/搜索测试通过。

---

### Phase 2：系统监控最小化（预计 0.5 天）🟡 第二优先级

#### 2.1 范围

| 区域 | 动作 |
|------|------|
| `api/v1/system/system_monitoring/` | 冻结或移除复杂监控端点 |
| health | 保留最小 `/api/v1/system/health`，只表达应用和数据库连通性 |
| API 契约 | 标注 MVP 系统健康能力仅保留 health |
| 测试 | 以 health 行为和路由注册为测试面 |

#### 2.2 不做

- 不在本阶段处理 `backup.py`、`tasks.py`、`error_recovery.py`。
- 不引入新的监控平台封装。
- 不改变 Sentry 错误上报配置。

#### 2.3 验收标准

- 最小 health 端点可用。
- 复杂 system monitoring API 不再作为产品能力暴露。
- `make docs-lint`、`make backend-import` 和相关 system 测试通过。

---

### Phase 3：AI Provider 统一入口（预计 1 天）🟡 第三优先级

#### 3.1 范围

| 区域 | 动作 |
|------|------|
| Provider 配置 | 统一文档 AI provider 选择入口，通过环境变量 `VISION_MODEL` 控制，明确支持值（`qwen`、`deepseek`、`glm`、`hunyuan`）和默认值 |
| Provider 工厂 | 在 `services/core/` 新增 `get_vision_provider()` 工厂函数，根据 `VISION_MODEL` 返回对应 adapter。调用方（PDF 导入、OCR 回退等）统一走工厂，不再散落 `import qwen_vision_service` 后自行选择 |
| 错误语义 | provider 未配置、provider 不支持、API key 缺失时 fail loud，不静默降级 |
| 测试 | 保留当前已覆盖 provider 的行为测试，先验证统一入口不破坏 PDF 导入。测试改为通过工厂函数获取 provider，不再直接 import 具体 adapter |

#### 3.2 暂不删除 provider

当前代码和测试仍覆盖 GLM、Qwen、DeepSeek、Hunyuan。未确认生产实际 provider 前，不直接删除 GLM/Hunyuan 文件。删除动作需要满足：

- 实际部署配置已确认只使用保留 provider。
- PDF 导入和 OCR 回退链路已有定向回归。
- 变更前后 provider 错误语义一致或更清晰。

#### 3.3 验收标准

- PDF 导入流程行为不变。
- provider 选择路径集中。
- 配置错误不静默降级。
- PDF import 和 LLM/provider 相关测试通过。

---

### Phase 4：Excel 模块审计门（暂不直接合并）🟢 待 Phase 1-3 后评审

#### 4.1 修正原因

原方案把 Excel 7 个服务文件直接合并为 import/export 两个文件，但当前 `excel_import_service.py`、`excel_export_service.py` 已经较大。继续把 preview、template、task、config、status 塞入大文件，可能降低局部性。

#### 4.2 先做审计

| 审计项 | 判断标准 |
|--------|----------|
| 调用关系 | 是否只有单一调用方 |
| 接口深度 | 是否只是透传参数到另一个服务 |
| 测试面 | 合并后测试是否更清晰，还是更难定位失败 |
| 业务语言 | preview/template/task/status 是否是用户可理解流程节点 |

#### 4.3 决策规则

- 纯透传模块可以合并。
- 承载独立流程语义的模块保留。
- 合并后的文件若超过当前可读性阈值，优先改接口，不强行合并文件。

---

### Phase 5：auth middleware 拆分（单独立项，不纳入第一轮瘦身）

`middleware/auth.py` 单文件过大是事实，但它同时承载认证、鉴权、数据范围注入，属于高风险架构治理。该工作应独立成方案，先补行为护栏测试，再做文件拆分。

建议后续独立方案边界：

```
middleware/
  auth.py                # 身份解析：Cookie/JWT 解析，用户身份注入
  authorization.py       # 权限判定：RBAC/ABAC
  data_scope.py          # 数据范围：主体绑定自动注入
  middleware_stack.py    # 中间件注册与编排
```

进入条件：

- 认证、鉴权、数据范围注入的关键行为测试齐备。
- 当前系统管理、项目、资产、合同关系、财务台账接口的授权烟测可复用。
- Phase 1-3 已完成并稳定。

---

## 4) 第一轮交付范围

第一轮只交付以下内容：

| 阶段 | 内容 | 是否进入第一轮 |
|------|------|----------------|
| Phase 1 | 冻结 Out of Scope 可见面 | 是 |
| Phase 2 | 系统监控最小化 | 是 |
| Phase 3 | AI Provider 统一入口 | 是 |
| Phase 4 | Excel 模块审计门 | 只输出审计，不直接合并 |
| Phase 5 | auth middleware 拆分 | 否，另立方案 |

第一轮完成后，再根据测试结果和代码影响决定是否推进 Excel 或 middleware。

---

## 5) 影响评估

### 5.1 预期收益

| 方向 | 收益 |
|------|------|
| Out of Scope 冻结 | 消除 MVP 外功能被误认为已交付的产品风险 |
| 监控最小化 | 减少自建基础设施维护面 |
| AI Provider 统一入口 | 降低 PDF/AI 调用路径分散度 |
| Excel 审计门 | 避免为了少文件而制造更大的文件 |
| middleware 独立立项 | 避免高风险授权改造混入瘦身提交 |

### 5.2 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 冻结 Out of Scope 误伤资产确权属性 | 中 | 明确不删除 `ownership_status`、`owner_party_id`、Party 主体能力 |
| 搜索对象范围调整导致测试漂移 | 中 | 同步 `REQ-SCH-001` 说明和搜索测试 |
| 系统监控最小化误删运维依赖 | 中 | 第一阶段只处理 monitoring 暴露面，不碰 backup/tasks/error_recovery |
| AI provider 收口影响 PDF 导入 | 中 | 先统一入口，不立即删除 provider；保留现有 provider 测试 |
| Excel 合并收益不足 | 高 | Phase 4 改为审计门 |
| middleware 拆分引入鉴权回归 | 高 | 移出第一轮，单独做护栏测试和方案 |

---

## 6) 第一轮完成标准（Done when）

1. Phase 1-3 全部完成，每项验收标准通过。
2. `make check` 全量门禁通过（含冻结路由后跳过的测试）。
3. SSOT 四文档（`docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md`、`docs/specs/domain-model.md`、`CHANGELOG.md`）已同步。
4. Phase 4 Excel 审计报告已输出到 `docs/archive/`。
5. Phase 5 auth middleware 独立方案已发起（至少创建方案文件 `docs/plans/YYYY-MM-DD-auth-middleware-split.md` 并标注 📋 待评审）。

---

## 7) 关联文档更新清单

| 文档 | 更新内容 |
|------|----------|
| `docs/archive/backend-plans/2026-05-29-codebase-lean-refocus-plan.md` | 归档本修正版方案 |
| `docs/plans/README.md` | 同步活跃方案摘要 |
| `docs/specs/api-contract.md` | Phase 1/2 的 API 暴露范围变化 |
| `docs/traceability/requirements-trace.md` | Phase 1 搜索对象范围和 Out of Scope 冻结说明 |
| `CHANGELOG.md` | 每次文档或实现变更后更新 |

---

## 8) 时间线

| 阶段 | 内容 | 预计工时 | 依赖 |
|------|------|----------|------|
| Phase 1 | 冻结 Out of Scope 可见面 | 0.5-1 天 | 无 |
| Phase 2 | 系统监控最小化 | 0.5 天 | 无（与 Phase 1 可并行） |
| Phase 3 | AI Provider 统一入口 | 1 天 | 无硬依赖（与 Phase 1/2 可并行） |
| Phase 4 | Excel 模块审计门 | 0.5 天 | Phase 1-3 后 |
| Phase 5 | auth middleware 拆分独立立项 | 待评估 | 不纳入第一轮 |

Phase 1-3 无文件冲突，可并行执行。第一轮预计 2-3 天（并行时 1-2 天），不追求一次性大删代码；优先让产品暴露面和 SSOT 对齐。

---

## 9) 评审要点

1. Out of Scope 冻结是否以 PRD/spec 为准，而不是继续维护半成品入口？
2. `REQ-SCH-001` 是否应移除产权证搜索对象，避免和 Out of Scope 冲突？
3. 系统监控最小化是否只处理 monitoring 暴露面，不误伤任务、备份、错误恢复？
4. AI provider 是否先统一入口，再根据真实部署决定删除 provider？
5. Excel 是否接受“先审计再合并”的门槛？
6. middleware 拆分是否同意单独立项，而不是混入瘦身第一轮？
