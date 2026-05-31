# 代码库瘦身与业务聚焦方案

## Status

📋 待评审

## 1) 问题诊断

### 1.1 量化数据

| 维度 | 数值 |
|------|------|
| 后端源码 | 410 文件 / ~101,000 行 |
| 后端测试 | 428 文件 / ~119,000 行 |
| 前端源码 | 628 文件 / ~62,000 行 |
| 测试/源码比 | 1.18 : 1（0→1 阶段偏高） |

### 1.2 臃肿诊断

对服务层 35,047 行按业务归属分类：

| 类别 | 估算行数 | 占比 | 问题 |
|------|----------|------|------|
| 核心业务（资产/合同/项目/台账） | ~12,000 | 34% | ✅ 合理 |
| 文档处理管道（PDF/AI/缓存） | ~5,000 | 14% | ⚠️ 过度工程 |
| 认证授权（中间件/RBAC/ABAC） | ~4,500 | 13% | ⚠️ 企业级但 MVP 用不上 |
| Excel 引擎（7 个服务文件） | ~1,800 | 5% | ⚠️ 过度拆分 |
| Out of Scope 模块（产权证/权属方） | ~1,500 | 4% | 🔴 纯负债 |
| 系统监控/备份/日志/恢复 | ~3,000 | 9% | ⚠️ 可替代 |
| 其他（字典/枚举/通知/搜索/自定义字段） | ~7,200 | 21% | 部分合理 |

### 1.3 业务缺口诊断

来自 `docs/traceability/requirements-trace.md` 的实现状态：

| REQ | 状态 | 核心痛点 |
|-----|------|----------|
| REQ-PRJ-003 | ✅ 已有证据 | 项目运营台账已补齐月度趋势和空置风险 |
| REQ-RNT-001 | ✅ 已有证据 | 合同关系作为用户可见业务对象已形成代码和测试证据 |
| REQ-RNT-002 | ✅ 已有证据 | 承租/代理双模式已有模式约束、资产摘要和经营分析证据 |
| REQ-SCH-001 | ✅ 已有证据 | 全局搜索入口、对象范围和合同关系文案已有证据 |

### 1.4 根因

```
              ████████████████████████████  基础设施 ~40%
              ████████████████████████████  (PDF管道、Excel引擎、ABAC、自建监控)

              ██████████                    核心业务 ~25%
              ██████████                    (资产、合同、项目、台账)

              ████████                      Out of Scope ~15%
              ████████                      (产权证、权属方、field_whitelist)

              ██████████████                Auth/中间件 ~20%
              ██████████████                (auth middleware 1722行单文件)
```

**核心矛盾**：工程资源倾斜在"将来可能需要"的基础设施上，用户每天要用的合同关系、项目台账、模式切换仍在修补迭代。

---

## 2) 目标与原则

### 2.1 目标

1. **瘦身**：移除未验收/可替代代码，降低维护负担
2. **聚焦**：SSOT 核心需求已完成证据收口，后续资源集中到评审确认后的瘦身清理
3. **不破坏**：已验收功能（已有证据的 REQ）零回退

### 2.2 原则

- ✅ 用移除代替注释，用报错代替降级（匹配 AGENTS.md "充分暴露问题"）
- ✅ 每个清理动作有对应测试更新
- ✅ 先出方案、评审通过、再执行
- ❌ 不做"万一以后用得到"的保留
- ❌ 不做大规模重构——只删不用的、不改能用的

---

## 3) 实施计划

### Phase 1：冻结与标记（预计 0.5 天）🔴 高优先

#### 1.1 标记 Out of Scope 模块

| 模块 | 行数 | 动作 |
|------|------|------|
| `services/property_certificate/` | ~700 | 从路由注册移除，代码保留不删（后续版本可能启用） |
| `services/ownership/` | ~450 | 同上 |
| `crud/property_certificate.py` | 160 | 同上 |
| `crud/ownership.py` | 265 | 同上 |
| `api/v1/assets/property_certificate.py` | 已存在 | 从路由注册移除 |
| `api/v1/assets/ownership.py` | 已存在 | 从路由注册移除 |

**验收标准**：
- `make check` 通过
- 前端产权证/权属方入口不可访问（如已接入）
- `docs/traceability/requirements-trace.md` 更新，Out of Scope 表注明"路由已冻结"

#### 1.2 标记冗余测试

- 对上述冻结模块的测试标记 `@pytest.mark.skip("Out of Scope - route frozen")`
- 统计跳过数量，不删除测试文件

---

### Phase 2：AI 适配器收敛（预计 1 天）🔴 高优先

#### 2.1 现状

```
services/core/
  qwen_vision_service.py      单独文件
  glm_ocr_service.py          单独文件
  hunyuan_vision_service.py   单独文件
  deepseek_vision_service.py  单独文件
  zhipu_vision_service.py     单独文件
  base_vision_service.py      基类
  llm_service.py              514 行

services/document/extractors/
  qwen_adapter.py
  glm_adapter.py
  hunyuan_adapter.py
  deepseek_adapter.py
  property_cert_adapter.py
  base.py
  factory.py
```

**5 个 Vision 服务 + 5 个 Adapter = 10 个文件，但当前实际使用的模型 ≤ 2 个。**

#### 2.2 收敛方案

```
services/core/
  vision_service.py           ← 统一入口，通过配置选择模型
  llm_service.py              ← 保留

services/document/extractors/
  base.py                     ← 保留
  factory.py                  ← 简化为双模型切换
  qwen_adapter.py             ← 保留（如 Qwen 为主力）
  deepseek_adapter.py         ← 保留（如 DeepSeek 为备选）
  glm_adapter.py              → 移入 archive/
  hunyuan_adapter.py          → 移入 archive/
  property_cert_adapter.py    → 移入 archive/
```

**验收标准**：
- 现有 PDF 导入流程功能不变
- `make check` 通过
- 配置文件新增 `VISION_MODEL` 环境变量，可选 `qwen` / `deepseek`
- 相关测试更新引用

---

### Phase 3：Excel 模块合并（预计 0.5 天）🟡 中优先

#### 3.1 现状

```
services/excel/
  excel_config_service.py     441 行（单独的"配置"服务？）
  excel_export_service.py     441 行
  excel_import_service.py     636 行
  excel_preview_service.py    单独文件
  excel_status_service.py     单独文件
  excel_task_service.py       单独文件
  excel_template_service.py   单独文件
```

7 个文件，但导入导出是一个连贯流程，preview/status/task/template/config 不是独立领域。

#### 3.2 合并方案

```
services/excel/
  excel_import_service.py     ← 吸收 preview + template + task 逻辑
  excel_export_service.py     ← 吸收 config + status 逻辑
```

`excel_preview_service` → 合并入 `excel_import_service`（预览是导入的前置步骤）
`excel_template_service` → 合并入 `excel_import_service`（模板是导入的配置）
`excel_task_service` → 合并入 `excel_import_service`（任务是导入的执行态）
`excel_config_service` → 合并入 `excel_export_service`（配置是导出的参数）
`excel_status_service` → 合并入 `excel_export_service`（状态是导出的查询）

**验收标准**：
- Excel 导入导出功能不变
- `make check` 通过
- 路由层 import 路径更新

---

### Phase 4：移除自建监控（预计 0.5 天）🟡 中优先

#### 4.1 现状

```
api/v1/system/system_monitoring/
  collectors.py
  database_endpoints.py
  endpoints.py
  health.py
  models.py
```

项目已依赖 `sentry-sdk[fastapi]`，健康检查可以用 FastAPI 内置的 `/health` 端点替代。

#### 4.2 方案

- 移除 `system_monitoring/` 整个子模块
- 在 `api/v1/system/system.py` 中保留一个简单的 `/api/v1/system/health` 端点（数据库连通性检查）
- 生产环境监控依赖 Sentry

**验收标准**：
- `make check` 通过
- `/api/v1/system/health` 返回数据库状态
- Sentry 错误上报不受影响

---

### Phase 5：auth middleware 拆分（预计 1 天）🟡 中优先

#### 5.1 现状

`middleware/auth.py` 1722 行 —— 项目最大单文件，混合了认证、鉴权、数据范围注入三种职责。

#### 5.2 拆分方案

```
middleware/
  auth.py                ← 认证：Cookie/JWT 解析，用户身份注入（~400 行）
  authorization.py       ← 鉴权：RBAC/ABAC 权限判定（~500 行）
  data_scope.py          ← 数据范围：主体绑定自动注入（~500 行）
  middleware_stack.py    ← 中间件注册与编排（~200 行）
```

不修改逻辑，只做文件拆分 + import 调整。

**验收标准**：
- 认证、鉴权、数据范围过滤行为不变
- `make check` 通过
- 所有中间件相关测试通过

---

### Phase 6：核心业务收敛（预计 2-3 天）🟢 核心目标

#### 6.1 REQ-PRJ-003 收尾：项目运营台账

当前状态：Phase 1a→2c 已完成大部分，2026-05-30 已补齐项目分析月度趋势和空置风险。

**动作**：
- 梳理 `contract_group_service.py` 中与项目台账相关的逻辑（`get_project_ledger_summary`、`get_project_risks`、`get_project_tenants`、`get_project_analytics`）
- 已补充项目分析月度趋势和空置风险口径
- 清理 Phase 迭代中遗留的临时代码（如"隐藏枚举"类注释标记的 workaround）

**验收标准**：
- `REQ-PRJ-003` 实现状态已从"开发中"变更为"已有证据"
- `docs/traceability/requirements-trace.md` 更新

#### 6.2 REQ-RNT-001/002 收尾：合同关系与双模式

当前状态：核心逻辑和 UI 交互已形成代码与测试证据。2026-05-30 复核确认 RNT 相关代码无"隐藏枚举"、`workaround`、`TODO`、`FIXME` 临时标记残留。

**动作**：
- 已确认承租/代理模式切换在服务、资产摘要、经营分析和前端详情入口的行为一致性
- 已验证合同关系新建、编辑、查看和关系内新增合同的前端覆盖测试
- 已验证搜索入口中的合同聚合对象使用"合同关系"文案

**验收标准**：
- `REQ-RNT-001`、`REQ-RNT-002`、`REQ-SCH-001` 实现状态已从"开发中"变更为"已有证据"
- `docs/traceability/requirements-trace.md` 已更新
- 合同关系新建/编辑/查看、关系内新增合同和全局搜索证据测试已通过

---

## 4) 影响评估

### 4.1 代码量变化预估

| 阶段 | 动作 | 行数变化 |
|------|------|----------|
| Phase 1 | 冻结 Out of Scope 路由 | ~0（代码不删） |
| Phase 2 | AI 适配器收敛 | -3 文件，~-800 行 |
| Phase 3 | Excel 合并 | -5 文件，~0（逻辑合并） |
| Phase 4 | 移除自建监控 | -6 文件，~-800 行 |
| Phase 5 | middleware 拆分 | ~0（逻辑不变） |
| Phase 6 | 核心业务收敛 | ~-500 行（清理临时代码） |
| **合计** | | **-14 文件，~-2,100 行最小估计** |

### 4.2 风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| AI 适配器收敛后模型切换异常 | 中 | 保留 Qwen + DeepSeek 双通道，收敛前后端集成测试 |
| Excel 合并引入回归 | 低 | Excel 导入导出已有测试覆盖 |
| middleware 拆分后认证链路异常 | 中 | 先跑全量中间件测试再合并 |
| 移除监控后健康检查缺失 | 低 | 新 `/health` 端点覆盖数据库连通性 |

### 4.3 不纳入本次的范围

- ❌ 不重写 `contract_group_service.py`——当前 1612 行虽大，但业务复杂度合理，等待 REQ 收敛后再评估重构
- ❌ 不调整测试策略——测试行数偏高是后续独立讨论的话题
- ❌ 不修改前端代码——除非 Phase 1 冻结路由导致前端入口报错
- ❌ 不换语言——已确认 Python/FastAPI 栈适合当前业务

---

## 5) 关联文档更新清单

| 文档 | 更新内容 |
|------|----------|
| `docs/traceability/requirements-trace.md` | Phase 1 冻结模块标注；Phase 6 状态变更 |
| `docs/specs/domain-model.md` | 如有字段因冻结不再暴露，需标注 |
| `docs/specs/api-contract.md` | Phase 1/4 移除的路由端点需移除或标注 deprecated |
| `CHANGELOG.md` | 每 Phase 完成后更新 |

---

## 6) 时间线

| Phase | 内容 | 预计工时 | 依赖 |
|-------|------|----------|------|
| 1 | 冻结 Out of Scope | 0.5 天 | 无 |
| 2 | AI 适配器收敛 | 1 天 | 无 |
| 3 | Excel 合并 | 0.5 天 | 无 |
| 4 | 移除自建监控 | 0.5 天 | 无 |
| 5 | middleware 拆分 | 1 天 | 无 |
| 6 | 核心业务收敛 | 2-3 天 | Phase 1-5 完成后 |
| **总计** | | **5.5-6.5 天** | |

Phase 1-5 可并行执行（无相互依赖），Phase 6 建议在前面清理完成后再启动。

---

## 7) 评审要点

1. ✅ Out of Scope 模块冻结是否影响任何现有用户流程？
2. ✅ AI 适配器保留 Qwen + DeepSeek 双通道是否覆盖当前业务？
3. ✅ Excel 合并是否会导致循环导入？
4. ✅ middleware 拆分后的文件边界是否清晰？
5. ✅ Phase 6 的 REQ 状态变更是否与产品经理对齐？
