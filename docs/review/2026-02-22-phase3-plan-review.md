# Phase 3 实施计划深度审阅报告（v1.36 复核版）

**审阅对象**: `docs/plans/2026-02-20-phase3-implementation-plan.md` (v1.36)  
**审阅日期**: 2026-02-22  
**审阅方法**: 逐节阅读 + 代码库实证交叉验证（grep / 文件读取 / 后端模型核实）

---

## 审阅概要

本次对原审阅报告做了版本对齐复核。结论：

1. 原报告中有多条结论已因计划文档升级到 `v1.36` 而失效。
2. 仍有若干阻断项成立，主要集中在后端交付状态与前端计划门禁不一致。
3. 风险最高的链路是 `project.party_relations[]` 契约、`tenant_party_id` 收紧、以及 P3d feature-flag 验签证据链。

---

## 一、已失效/需修正结论（相对原报告）

### #R1 — 审阅对象版本已过期

- 原文使用 `v1.35`。
- 当前计划文档已到 `v1.36`（见文档历史 `2026-02-22 | 1.36`）。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:1610`

---

### #R2 — “`services/asset/types.ts` 遗漏”结论已失效

- 原结论称 §4.2 变更清单遗漏 `services/asset/types.ts`。
- `v1.36` 已在服务层变更表显式纳入：`asset/types.ts` 的旧字段迁移。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:477`

---

### #R3 — “§3.1 未提 `assetFormSchema.ts`”结论不成立

- 原结论称统计分布遗漏 `assetFormSchema.ts`。
- `v1.36` 的 §3.1 `management_entity` 分布已明确包含 `assetFormSchema`。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:150`

---

### #R4 — “`.github/workflows/` 不存在”是事实错误

- 原结论中将其列为不存在。
- 仓库中该目录存在，且有 `ci.yml` 等文件。

**修正口径**: 风险不在“目录不存在”，而在“验签变量/证据未落地”。

**证据**: `.github/workflows/ci.yml`

---

### #R5 — `Omit` 风险表述不准确

- 原结论称删除 `Asset.ownership_entity` 后，`Omit<Asset, 'ownership_entity'>` 会触发 TS 编译错误。
- `Omit<T, K extends keyof any>` 对不存在键通常不会报错，该条属于误判。

**证据**:
- `frontend/node_modules/typescript/lib/lib.es5.d.ts:1630`
- `frontend/src/types/asset.ts:210`

---

### #R6 — “§10 文档历史 250+ 行”结论已失效

- 当前计划文档 §10 已收敛，仅保留近版本摘要。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:1605`

---

## 二、仍成立的高优先级问题（建议继续阻断）

### #P1 — `AuthStorage` 的 capabilities 字段为计划态，尚未落地

计划要求 `AuthStorage` 增加 `capabilities`/`capabilities_cached_at`/`capabilities_version`，但实现文件当前仅有 `user` + `permissions`。

**风险**: 执行者误判为“已实现”，导致 P3d 权限单源链路落空。

**证据**:
- 计划定义: `docs/plans/2026-02-20-phase3-implementation-plan.md:562`
- 实现现状: `frontend/src/utils/AuthStorage.ts:3`

---

### #P2 — `project.party_relations[]` 仍未形成后端可用契约

计划要求前端仅消费/提交 `party_relations[]`，但后端 Schema 仍是 `ownership_relations`，且 `project_to_response()` 仍硬编码空数组。

**风险**: P3b/P3c 联调链路与计划契约不一致，形成“前端按新契约改、后端不给数据”的阻断。

**证据**:
- 前端计划约束: `docs/plans/2026-02-20-phase3-implementation-plan.md:486`, `docs/plans/2026-02-20-phase3-implementation-plan.md:663`
- 后端 Schema 现状: `backend/src/schemas/project.py:77`
- 后端转换实现: `backend/src/services/project/service.py:58`

---

### #P3 — `tenant_party_id` 收紧与后端可空定义仍冲突

计划在 P3e 收紧为必填非空字符串，但后端模型仍允许 `NULL`。

**风险**: 存量空值合同编辑/回显失败，历史数据无法平滑过渡。

**证据**:
- 计划收紧: `docs/plans/2026-02-20-phase3-implementation-plan.md:355`
- 后端可空: `backend/src/models/rent_contract.py:98`
- 仅有“处置门禁”但无量化标准: `docs/plans/2026-02-20-phase3-implementation-plan.md:1225`

---

### #P4 — P3d feature flag 验签证据链仍未就绪

计划要求生产环境显式声明并留存证据；当前 `.env.production` 与证据文档均不存在，workflow 中也未命中相关变量。

**风险**: P3d Exit 的 D9 验签门禁无法通过或只能临时补材料。

**证据**:
- 验签门禁定义: `docs/plans/2026-02-20-phase3-implementation-plan.md:1211`
- 文件缺失: `frontend/.env.production`, `docs/release/evidence/capability-guard-env.md`
- workflow 现状: `.github/workflows/ci.yml`

---

### #P5 — `phase3d-authz-freeze.md` 仍是“必须存在但无模板”

P3d Entry 已要求该文件存在并命中关键字，但仓库中当前无 `docs/plans/execution/` 目录，且无模板。

**风险**: 执行日临时造文可过 grep，但内容质量不可控。

**证据**:
- Entry 门禁: `docs/plans/2026-02-20-phase3-implementation-plan.md:1182`, `docs/plans/2026-02-20-phase3-implementation-plan.md:1188`
- 当前缺失路径: `docs/plans/execution/`

---

### #P6 — 门禁 A 与 `usePermission.tsx` 兼容壳定位仍存在张力

计划一方面把 `usePermission` 定位为兼容壳，另一方面门禁 A 把 `usePermission.tsx` 纳入“非标准动作词”扫描。

**风险**: 若保留旧常量值作为兼容层，门禁 A 会持续失败；若全改标准动作，又与“兼容壳”语义冲突。

**证据**:
- 兼容壳定义: `docs/plans/2026-02-20-phase3-implementation-plan.md:396`
- 门禁 A 扫描包含文件: `docs/plans/2026-02-20-phase3-implementation-plan.md:845`
- 现有常量含旧动作词: `frontend/src/hooks/usePermission.tsx:200`

---

## 三、中优先级优化项（建议纳入 v1.37+）

### #M1 — `capabilities_version` 用途需明示

计划写了“不用 `CapabilitiesResponse.version` 做变更判据”，但仍定义缓存 `capabilities_version`，应说明用途（协议兼容标记/调试观测等）。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:555`, `docs/plans/2026-02-20-phase3-implementation-plan.md:562`

### #M2 — `ownership_category` 处置决策应补充

`assetFormSchema` 仍有 `ownership_category`，计划未明确“保留/改名/删除”。

**证据**:
- 字段现状: `frontend/src/assetFormSchema.ts:25`
- 计划中无明确处置: `docs/plans/2026-02-20-phase3-implementation-plan.md`

### #M3 — BroadcastChannel 降级协议需写实

计划提到 `BroadcastChannel` 降级到 `storage`，但缺 feature detect 与事件协议最小规范。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:1069`

### #M4 — Excel 中文旧列名门禁仍仅扫前端

当前 grep 只覆盖 `frontend/src`，后端模板生成链路可能漏检。

**证据**: `docs/plans/2026-02-20-phase3-implementation-plan.md:1416`

---

## 四、建议执行顺序（面向落地）

1. 先补 P3d/P3e 的“硬阻断前置资产”：`phase3d-authz-freeze.md` 模板、`capability-guard-env.md` 模板、`.env.production` 或 CI 注入证据。
2. 再处理契约阻断：把 `project.party_relations[]` 提升为 P3b Entry 实际可验证门禁（后端响应样本 + 集成测试）。
3. 最后处理语义收紧风险：为 `tenant_party_id` 制定空值阈值与回填策略（含回滚口径）。

---

## 附录：复核命令（节选）

```bash
# 计划文档关键口径
rg -n "party_relations|capabilities_version|VITE_ENABLE_CAPABILITY_GUARD|phase3d-authz-freeze" docs/plans/2026-02-20-phase3-implementation-plan.md

# 后端项目契约现状
rg -n "ownership_relations|party_relations|project_to_response" backend/src/schemas/project.py backend/src/services/project/service.py

# AuthStorage 现状
rg -n "interface AuthData|permissions|capabilities" frontend/src/utils/AuthStorage.ts

# feature flag 证据链现状
ls -la frontend/.env.production docs/release/evidence/capability-guard-env.md .github/workflows 2>/dev/null || true
```
