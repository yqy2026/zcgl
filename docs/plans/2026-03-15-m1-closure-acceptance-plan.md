# M1 Closure And Acceptance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push the current "M1 close-out + acceptance readiness" work to a defensible finish by closing real Party-domain gaps, validating ANA-001 front-end consumption, and reconciling stale SSOT / active-plan state with shipped reality.

**Architecture:** Treat this as four parallel-but-ordered tracks: `REQ-PTY-001/002` implementation gaps, `REQ-ANA-001` front-end acceptance evidence, `REQ-AUTH-002` active-plan close-out, and SSOT milestone/status reconciliation. Backend and frontend changes stay small and test-first; docs only move after fresh verification confirms the new state.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, React 19, TypeScript 5, TanStack Query, Ant Design, pytest, Vitest, Playwright, Markdown docs

---

**文档类型**: 实施计划  
**创建日期**: 2026-03-15  
**状态**: 🔄 进行中  
**需求编号**: REQ-PTY-001, REQ-PTY-002, REQ-ANA-001, REQ-AUTH-002  
**里程碑**: M1 收口 / 验收推进

---

## 1. 背景与校正后的前提

本计划建立在 2026-03-15 的仓库复核结果之上，先修正 4 个错误前提：

1. `REQ-AST-003` 已不是 M1 待开发项，而是已实现能力；本计划不再把它作为实现目标，只处理 SSOT/沟通层的错误表述。
2. `REQ-PTY-001` 当前仍未达到“可验收”：缺少“统一标识去重”与“重名校验”的明确定义和实现证据；现状只有 `(party_type, code)` 去重。
3. `REQ-PTY-002` 当前仍缺两条明确能力：批量导入主体主档、合同组流程内快速创建 Party 草稿。
4. `REQ-ANA-001` 与 `REQ-AUTH-002` 更接近“验收证据 / 计划状态未收口”，而不是“主链路尚未实现”；因此该两项优先以验证、补证据、更新文档为主，只有在验证暴露问题时才进入代码修复。

---

## 2. 范围定义

### 2.1 本计划包含

1. 为 `REQ-PTY-001` 补齐唯一标识、重名校验、变更审计可查询能力。
2. 为 `REQ-PTY-002` 补齐批量导入、合同组流程快速创建 Party 草稿路径。
3. 对 `REQ-ANA-001` 增加浏览器/UAT 级证据，并将前端消费证据回写 SSOT。
4. 收尾 `REQ-AUTH-002` 活跃方案，移除“资产/合同/项目跨主体集成测试待补充”的过时说法，明确真实剩余项。
5. 更新 `docs/requirements-specification.md`、`docs/features/requirements-appendix-fields.md`、`docs/plans/README.md`、`CHANGELOG.md`，保证唯一真相链路闭环。

### 2.2 本计划不包含

1. 重新实现 `REQ-AST-003`。
2. 为 Party 引入“反审核”完整状态机；本轮只做当前验收缺口。
3. 为 Party 批量导入引入复杂异步任务平台；优先最小闭环。
4. 对 `REQ-AUTH-002` 做无边界扩散式全量排查；只处理当前活跃计划的收尾与拆分。

---

## 3. 关键决策

### 3.1 Party 统一标识

建议新增显式字段 `unified_identifier`，不要复用 `external_ref`。

- `external_ref` 保留“外部系统映射”语义。
- `unified_identifier` 承担“统一社会信用代码 / 法人登记号 / 自然人证件号等规范化主标识”语义。
- 校验规则：非空时在未软删记录中全局唯一，空值允许存在。
- 迁移策略：本轮**不**从 `external_ref` 自动回填，避免把“外部系统映射”误当业务主标识。
- DDL 策略：新增 nullable 字段 + partial unique index（`unified_identifier IS NOT NULL AND deleted_at IS NULL`）。
- 数据策略：在真正启用唯一约束前，先产出存量冲突审计结果，确认无冲突或有明确人工处置方案后再落唯一索引。

### 3.2 Party 重名校验

建议采用“规范化后的精确重名校验”，先不上模糊匹配。

- 规范化：`trim + collapse spaces + lower-case for latin chars`。
- 作用域：同 `party_type` 下的未软删记录。
- 冲突策略：创建/编辑直接失败，返回明确冲突主体。

### 3.3 Party 变更审计

建议新增专用 `PartyChangeLog`，不要把 CRUD 审计塞进 `PartyReviewLog`。

- `PartyReviewLog` 继续只记录审核流。
- `PartyChangeLog` 只记录 `create/update/delete/import` 这类主档变更动作，不重复记录 `review_*`。
- 至少保留：操作人、动作、字段快照（before/after）、时间。
- 对外提供读取接口，前端详情页可见。
- 若仍需接入通用审计体系，通用审计日志仅作为辅助留痕，`PartyReviewLog + PartyChangeLog` 才是 Party 域查询真相源。

### 3.4 合同组快速创建 Party

建议复用现有 Party 创建接口，而不是额外新建“合同组专用 Party API”。

- 前端在 `ContractGroupFormPage` 中通过共享 `PartySelector` 打开“快速创建主体”模态。
- 快速创建默认生成 `draft` Party，并回填到当前字段。
- 可选支持“创建并提审”；合同组提审门禁继续复用现有 `assert_parties_approved()`。
- 权限前提：只有同时具备 `contract_group.create/update` 与 `party.create` 的用户才显示“快速创建主体”；没有 `party.create` 时退化为只搜索不创建。
- 验证要求：必须补一条非管理员真实权限链路用例，证明“有权用户可创建、无权用户不可创建”。

### 3.5 ANA / AUTH 的 M1 口径

本计划先把“实现完成”与“里程碑归属”拆开处理。

- `REQ-ANA-001`：先验证前端消费和导出是否完整，如果通过，再决定是改为 `✅` 还是保持 `🚧` 但写清剩余项。
- `REQ-AUTH-002`：先关闭“跨主体测试待补充”的过时描述，再决定当前活跃计划是归档还是拆分后续系统资源白名单计划。

---

## 4. 执行顺序

1. 先做 SSOT 范围冻结，避免一边开发一边改目标。
2. 再做 `REQ-PTY-001`，因为它定义后续导入和快速创建的数据边界。
3. 然后做 `REQ-PTY-002` 的批量导入。
4. 再做合同组快速创建 Party 草稿路径。
5. 最后完成 `ANA-001` 验证与 `AUTH-002` 收尾，并统一回写文档。

---

## 5. 任务拆分

### Task 0: 冻结范围并校正 SSOT 前提

**Files:**
- Modify: `docs/requirements-specification.md`
- Modify: `docs/features/requirements-appendix-fields.md`
- Modify: `docs/archive/backend-plans/2026-03-02-party-scope-isolation-fix-plan.md`
- Modify: `CHANGELOG.md`

**Outcome:** 先把“AST-003 已完成”“PTY 真缺口”“ANA/AUTH 当前真实状态”写清楚，防止后续实现围绕错误前提展开。

- [ ] **Step 1: 明确里程碑与状态冲突清单**

记录并确认以下冲突：

1. `REQ-AST-003` 已实现，但仍被口头当作 M1 待办。
2. `REQ-ANA-001` 在里程碑定义里属于 `M3`，但当前要进入 M1 验收闭环。
3. `REQ-AUTH-002` 活跃计划中的“待补跨主体测试”与当前真实测试证据不一致。
4. `unified_identifier` 的业务语义、允许为空规则、唯一约束范围、存量回填策略必须先冻结。
5. `PartyChangeLog` 与 `PartyReviewLog` 的边界必须先冻结，避免后续重复留痕。

- [ ] **Step 2: 先更新文档前提，不改功能状态**

先把错误前提改正，但不在本步骤把 `PTY/ANA/AUTH` 最终状态改成 `✅`。

Run: `make docs-lint`  
Expected: PASS

- [ ] **Step 3: 记录本计划是后续唯一执行入口**

在相关文档中引用本计划，避免后续继续围绕旧假设沟通。

---

### Task 1: 补齐 REQ-PTY-001 的唯一标识、重名校验与变更审计

**Files:**
- Create: `backend/src/models/party_change_log.py`
- Create: `backend/alembic/versions/<timestamp>_party_identifier_and_change_log.py`
- Modify: `backend/src/models/party.py`
- Modify: `backend/src/schemas/party.py`
- Modify: `backend/src/crud/party.py`
- Modify: `backend/src/services/party/service.py`
- Modify: `backend/src/api/v1/party.py`
- Modify: `frontend/src/types/party.ts`
- Modify: `frontend/src/services/partyService.ts`
- Modify: `frontend/src/pages/System/PartyListPage.tsx`
- Modify: `frontend/src/pages/System/PartyDetailPage.tsx`
- Modify: `docs/features/requirements-appendix-fields.md`
- Test: `backend/tests/unit/services/test_party_service.py`
- Test: `backend/tests/unit/api/v1/test_party_api.py`
- Test: `backend/tests/integration/api/test_party_api_real.py`
- Test: `backend/tests/unit/migration/test_party_identifier_and_change_log_migration.py`
- Test: `frontend/src/services/__tests__/partyService.test.ts`
- Test: `frontend/src/pages/System/__tests__/PartyPages.test.tsx`

**Outcome:** `REQ-PTY-001` 的“统一标识去重 / 重名校验 / 变更可追溯”变成可验证的系统能力。

- [ ] **Step 1: 先冻结字段与迁移契约**

在动代码前明确：

1. `unified_identifier` 为 nullable。
2. 本轮不从 `external_ref` 自动回填。
3. 仅对非空值建立 partial unique index。
4. `PartyChangeLog` 不重复记录 `review_*`。

- [ ] **Step 2: 先写失败测试，锁定 4 个缺口**

新增测试覆盖：

1. 非空 `unified_identifier` 创建重复时报错。
2. 规范化后的同类型重名创建/编辑时报错。
3. `create/update/delete/import` 会写入 `PartyChangeLog`，且详情接口可读取。
4. 迁移只新增 nullable 字段与 partial unique index，不做 `external_ref -> unified_identifier` 自动回填。

- [ ] **Step 3: 跑测试确认当前确实失败**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_service.py tests/unit/api/v1/test_party_api.py tests/unit/migration/test_party_identifier_and_change_log_migration.py -q -x`  
Expected: FAIL in new PTY-001 cases

- [ ] **Step 4: 实现最小后端能力**

实现内容：

1. `Party` 新增 `unified_identifier`。
2. `CRUDParty` 增加基于 `unified_identifier` 与规范化名称的查询。
3. `PartyService.create_party/update_party` 加入重复校验。
4. 新增 `PartyChangeLog` 写入与读取接口。
5. Alembic 迁移明确为“增列 + partial unique index + 不自动回填”。

- [ ] **Step 5: 补齐前端读取与展示**

实现内容：

1. `Party` 类型与服务补齐 `unified_identifier`、变更日志读取。
2. `PartyListPage` 的“新建主体”入口支持录入 `unified_identifier`。
3. `PartyDetailPage` 展示统一标识与变更轨迹。

- [ ] **Step 6: 重新运行测试并验证通过**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_service.py tests/unit/api/v1/test_party_api.py tests/integration/api/test_party_api_real.py tests/unit/migration/test_party_identifier_and_change_log_migration.py -q`  
Expected: PASS

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/partyService.test.ts src/pages/System/__tests__/PartyPages.test.tsx`  
Expected: PASS

---

### Task 2: 补齐 REQ-PTY-002 的批量导入主档能力

**Files:**
- Create: `backend/src/schemas/party_import.py`
- Create: `backend/src/services/party/import_service.py`
- Modify: `backend/src/services/party/__init__.py`
- Modify: `backend/src/api/v1/party.py`
- Modify: `backend/src/core/import_utils.py`
- Modify: `frontend/src/services/partyService.ts`
- Modify: `frontend/src/pages/System/PartyListPage.tsx`
- Modify: `docs/requirements-specification.md`
- Test: `backend/tests/unit/services/test_party_import_service.py`
- Test: `backend/tests/unit/api/v1/test_party_api.py`
- Test: `frontend/src/services/__tests__/partyService.test.ts`
- Test: `frontend/src/pages/System/__tests__/PartyPages.test.tsx`

**Outcome:** 系统管理页可上传初始化主体模板，服务端返回结构化导入结果；导入记录默认进入 `draft`，不绕过审核。

- [ ] **Step 1: 定义最小导入闭环**

导入只做 3 件事：

1. 下载模板。
2. 上传并解析。
3. 返回 `created / skipped / errors` 结果。

本轮不做：

1. 异步任务队列。
2. 复杂预览工作流。
3. 导入自动审核通过。

- [ ] **Step 2: 写失败测试**

新增测试覆盖：

1. 合法模板行能创建 Party。
2. 重复统一标识 / 重名 / 重复编码进入错误列表。
3. 导入创建的 Party 默认 `draft`。

- [ ] **Step 3: 跑失败测试**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_import_service.py tests/unit/api/v1/test_party_api.py -q -x`  
Expected: FAIL in new import cases

- [ ] **Step 4: 实现后端导入能力**

实现内容：

1. 新增模板 schema 和 import service。
2. 在 `party.py` 增加模板下载与导入接口。
3. 复用 PTY-001 的去重校验，不允许导入绕过。

- [ ] **Step 5: 实现前端入口**

在 `PartyListPage` 增加“下载模板 / 导入主体”按钮与结果反馈。

- [ ] **Step 6: 重新运行验证**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_import_service.py tests/unit/api/v1/test_party_api.py -q`  
Expected: PASS

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/partyService.test.ts src/pages/System/__tests__/PartyPages.test.tsx`  
Expected: PASS

---

### Task 3: 在合同组流程内提供 Party 草稿快速创建路径

**Files:**
- Modify: `frontend/src/components/Common/PartySelector.tsx`
- Modify: `frontend/src/components/Common/index.ts`
- Modify: `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx`
- Modify: `frontend/src/services/partyService.ts`
- Modify: `frontend/src/types/party.ts`
- Test: `frontend/src/components/Common/__tests__/PartySelector.test.tsx`
- Test: `frontend/src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx`
- Test: `backend/tests/unit/services/contract/test_contract_group_service.py`
- Test: `backend/tests/integration/api/test_party_api_real.py`

**Outcome:** 合同组新建/编辑页可以在 `operator_party_id`、`owner_party_id` 位置直接创建并选中新的 Party 草稿；合同提审门禁继续要求关联 Party 全部已审核。

- [ ] **Step 1: 先写权限与前端失败测试**

新增测试覆盖：

1. `PartySelector` 在开启 `allowCreateDraft` 时显示“快速创建主体”入口。
2. 创建成功后自动选中新 Party。
3. 合同组表单提交时会携带新建 Party ID。
4. 无 `party.create` 能力时不显示快速创建入口。
5. 有 `party.create` 但非管理员的合同组用户可真实创建草稿 Party；无权用户创建被拒绝。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && pnpm exec vitest run src/components/Common/__tests__/PartySelector.test.tsx src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx`  
Expected: FAIL in new quick-create cases

- [ ] **Step 3: 在共享选择器实现快速创建**

实现内容：

1. 给 `PartySelector` 增加可选的快速创建入口。
2. 通过 `partyService.createParty()` 创建默认 `draft` Party。
3. 可选调用 `submitReview()` 实现“创建并提审”。
4. 通过 capability 判断是否显示快速创建入口，而不是默认对所有合同组用户开放。

- [ ] **Step 4: 在合同组表单接入**

接入点：

1. `operator_party_id` 使用组织主体草稿模板。
2. `owner_party_id` 使用法人主体草稿模板。

- [ ] **Step 5: 复核合同提审门禁**

保持或补强现有 `assert_parties_approved()` 测试，确保：

1. 草稿 Party 可挂在草稿合同组上。
2. 合同组提审时仍被阻断，直到相关 Party 全部 `approved`。

- [ ] **Step 6: 重新运行验证**

Run: `cd frontend && pnpm exec vitest run src/components/Common/__tests__/PartySelector.test.tsx src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx src/services/__tests__/partyService.test.ts`  
Expected: PASS

Run: `cd backend && uv run pytest --no-cov tests/unit/services/contract/test_contract_group_service.py -q`  
Expected: PASS

Run: `cd backend && uv run pytest --no-cov tests/integration/api/test_party_api_real.py -q -k quick_create`  
Expected: PASS

---

### Task 4: 为 REQ-ANA-001 补齐浏览器级验收证据并回写 SSOT

**Files:**
- Modify: `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`
- Modify: `frontend/src/hooks/useAssetAnalytics.ts`
- Modify: `frontend/src/components/Analytics/AnalyticsStatsCard.tsx`
- Modify: `frontend/src/services/analyticsService.ts`
- Modify: `frontend/src/services/analyticsExportService.ts`
- Modify: `docs/requirements-specification.md`
- Create: `frontend/tests/e2e/analytics/asset-analytics-ana001.spec.ts`
- Test: `frontend/src/services/__tests__/analyticsService.test.ts`
- Test: `frontend/src/services/__tests__/analyticsExportService.ana001.test.ts`
- Test: `frontend/src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx`
- Test: `backend/tests/integration/test_analytics_api.py`

**Outcome:** 对 `total_income / self_operated_rent_income / agency_service_income / customer_entity_count / customer_contract_count / metrics_version` 的“前端完整消费”拥有浏览器级可重复证据，而不仅是静态代码复核。

- [ ] **Step 1: 采用“双证据”方案写验证**

分成两层：

1. 固定数据浏览器断言：保证 UI 渲染与导出结构稳定。
2. 真实接口浏览器烟测：保证页面确实消费 `/analytics/comprehensive` 的真实返回字段，而不是只消费 mocked payload。

断言点：

1. 页面显示 5 个经营口径统计卡片。
2. `metrics_version` 标签可见。
3. 导出数据包含同一组字段。
4. 浏览器真实请求拿到的 `/analytics/comprehensive` payload 中，6 个 ANA 字段均存在且被页面消费。

- [ ] **Step 2: 跑测试确认当前基线**

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts src/services/__tests__/analyticsExportService.ana001.test.ts src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx`  
Expected: PASS

Run: `cd backend && uv run pytest --no-cov tests/integration/test_analytics_api.py -q`  
Expected: PASS

- [ ] **Step 3: 补浏览器级断言**

若浏览器测试暴露 UI/导出问题，再最小修改对应页面/服务层代码。
真实接口烟测不得被纯 mock 替代；若环境数据不稳定，需先补最小种子或前置准备步骤。

- [ ] **Step 4: 把前端证据回写到 SSOT**

在 `REQ-ANA-001` 的代码证据中追加：

1. 前端页面。
2. 前端服务。
3. 前端测试。

---

### Task 5: 收尾 REQ-AUTH-002 活跃计划并同步追踪矩阵

**Files:**
- Modify: `docs/archive/backend-plans/2026-03-02-party-scope-isolation-fix-plan.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/requirements-specification.md`
- Modify: `CHANGELOG.md`
- Test: `backend/tests/integration/api/test_assets_visibility_real.py`
- Test: `backend/tests/integration/api/test_project_visibility_real.py`
- Test: `backend/tests/integration/api/test_contract_visibility_real.py`
- Test: `backend/tests/integration/api/test_collection_visibility_real.py`
- Test: `backend/tests/integration/api/test_property_certificate_visibility_real.py`

**Outcome:** 从旧方案中删除“资产/合同/项目跨主体集成测试待补充”的过期叙述；若 Party-scope 主目标已完成，则将旧方案归档，并把 `REQ-AUTH-002` 仅剩的全局视角机制尾项保留在本计划继续跟踪。

- [ ] **Step 1: 重新核对 Party-scope 证据**

以 fresh test output 为准，不依赖旧结论。

Run: `cd backend && uv run pytest --no-cov tests/integration/api/test_assets_visibility_real.py tests/integration/api/test_project_visibility_real.py tests/integration/api/test_contract_visibility_real.py tests/integration/api/test_collection_visibility_real.py tests/integration/api/test_property_certificate_visibility_real.py -q`  
Expected: PASS

- [ ] **Step 2: 修改活跃计划的状态描述**

将“资产/合同/项目跨主体测试待补充”改成：

1. 已完成的真实证据。
2. 真正剩余的系统级资源白名单 / 归类问题。

- [ ] **Step 3: 决定计划去向**

二选一：

1. 若剩余项仍属于同一实施波次：保留 `🔄`，把剩余项收敛成少量清单。
2. 若 Party-scope 主目标已完成：将旧计划归档，并为全局资源残项新建更小的 follow-up plan。

当前进展：

1. 旧的 Party-scope 隔离方案已归档至 `docs/archive/backend-plans/2026-03-02-party-scope-isolation-fix-plan.md`。
2. 前端已新增全局主体/视角选择最小闭环：`ViewContext + GlobalViewSwitcher + X-View-* 请求头 + authz-stale 后强制重选`。
3. `REQ-AUTH-002` 当前剩余点已收敛为“业务页面如何系统性消费当前视角标签/口径”，不再是主体泄露修复本身。

---

### Task 6: 最终文档收口与门禁验证

**Files:**
- Modify: `docs/requirements-specification.md`
- Modify: `docs/features/requirements-appendix-fields.md`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`

**Outcome:** 所有本轮状态变化、字段变化、证据路径都回写到 SSOT，且文档门禁通过。

- [ ] **Step 1: 更新需求追踪矩阵与里程碑说明**

按真实实现与验收结果决定：

1. `REQ-PTY-001` 是否可转 `✅`。
2. `REQ-PTY-002` 是否可转 `✅`。
3. `REQ-ANA-001` 是否可转 `✅` 或保留 `🚧` 并写清残项。
4. `REQ-AUTH-002` 是否仍保留 `🚧` 但只剩系统资源分类尾项。

- [ ] **Step 2: 运行文档门禁**

Run: `make docs-lint`  
Expected: PASS

- [ ] **Step 3: 运行受影响最小验证集**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_service.py tests/unit/api/v1/test_party_api.py tests/unit/services/contract/test_contract_group_service.py tests/integration/test_analytics_api.py tests/integration/api/test_assets_visibility_real.py tests/integration/api/test_project_visibility_real.py tests/integration/api/test_contract_visibility_real.py -q`  
Expected: PASS

Run: `cd frontend && pnpm exec vitest run src/services/__tests__/partyService.test.ts src/pages/System/__tests__/PartyPages.test.tsx src/components/Common/__tests__/PartySelector.test.tsx src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx src/services/__tests__/analyticsService.test.ts src/services/__tests__/analyticsExportService.ana001.test.ts src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx`  
Expected: PASS

---

## 6. 风险与控制

1. `unified_identifier` 语义若未被业务方确认，容易反复返工。控制方式：先在 Task 1 落文字段定义，再写迁移与校验。
2. 批量导入与快速创建若同时实现复杂审核分支，容易把 M1 拖成平台化需求。控制方式：坚持“导入默认 draft、快速创建复用现有 Party API”。
3. `REQ-ANA-001` 若只靠单测而无浏览器证据，文档状态仍容易被再次质疑。控制方式：补固定数据的浏览器级测试。
4. `REQ-AUTH-002` 若继续把“全局资源分类尾项”和“Party-scope 泄露修复”混在一个计划里，活跃方案会长期悬空。控制方式：本轮明确拆界。

---

## 7. 完成判定

满足以下条件，才可称本计划完成：

1. `REQ-PTY-001` 的统一标识、重名校验、变更审计均有代码与测试证据。
2. `REQ-PTY-002` 的批量导入与合同组快速创建 Party 草稿路径均可操作。
3. `REQ-ANA-001` 有前端浏览器级消费证据，SSOT 写入前端代码证据。
4. `REQ-AUTH-002` 活跃计划中的过时“待补跨主体测试”描述被移除，并明确真实剩余项。
5. `make docs-lint` 与受影响最小测试集通过。
