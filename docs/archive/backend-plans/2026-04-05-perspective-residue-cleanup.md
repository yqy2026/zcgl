# Perspective Residue Cleanup Plan

> **Status**: ✅ Completed
> **Created**: 2026-04-05
> **Parent REQ**: REQ-AUTH-002 (Perspective → Data Scope refactor)

---

## 1. Background

REQ-AUTH-002 已完成"视角切换 → 数据范围自动注入"的收口。前端路由已扁平化为 `/assets`、`/project`、`/search`、`/customers/:id` 等，不再以 `/owner/`、`/manager/` 区分入口。后端 `X-Perspective` header 改为可选，缺失时自动走 `all`（owner+manager 并集）。

但代码中仍存在大量以 `perspective` 命名的参数、字段、路由路径和文案，部分已与新设计矛盾。本计划按"保留 / 重命名 / 删除 / 更新"四类逐一清理。

---

## 2. Classification Matrix

### 2.1 合理保留 — 不改（技术内部语义，不暴露给用户）

| 文件 | 符号 | 原因 |
|------|------|------|
| `backend/src/schemas/authz.py` | `PerspectiveName = Literal["owner", "manager"]` | 内部类型，表示用户绑定类型 |
| `backend/src/schemas/authz.py` | `EffectivePerspective = Literal["owner", "manager", "all"]` | 内部类型，表示运行时有效范围 |
| `backend/src/services/authz/resource_perspective_registry.py` | 整个文件 | 资源级数据范围注册表，是 capabilities 生成的后端真值 |
| `backend/src/services/authz/service.py` | `_resolve_perspectives()` | 从 SubjectContext 推导用户可用的 owner/manager 绑定 |
| `backend/src/services/authz/service.py` | `_build_perspective_token()` | 缓存键构造片段，不暴露给外部 |
| `backend/src/services/authz/cache.py` | `build_decision_key(..., perspective=...)` | 缓存隔离需要，内部变量 |
| `backend/src/services/authz/context_builder.py` | `resolve_allowed_perspectives()` | 内部工具，从 SubjectContext 推导可用绑定 |
| `backend/src/services/authz/context_builder.py` | `resolve_effective_party_ids()` | 内部工具，按绑定类型返回 party_ids |
| `backend/src/services/party_scope.py` | `build_party_filter_from_perspective_context()` | 从 PerspectiveContext 构建 PartyFilter 的桥梁函数 |
| `backend/src/middleware/auth.py` | `PerspectiveContext` | 请求级上下文对象，承载 perspective + effective_party_ids |
| `backend/src/middleware/auth.py` | `require_perspective_context()` | FastAPI 依赖注入，自动构建 PerspectiveContext |
| `frontend/src/types/capability.ts` | `perspectives: Perspective[]` in `CapabilityItem` | 后端 capabilities 响应字段，前端必须消费 |
| `frontend/src/utils/authz/capabilityEvaluator.ts` | `perspective` 参数 | 用于判断用户对该资源是否有该数据范围权限 |
| `frontend/src/hooks/useCapabilities.ts` | `getAvailablePerspectives()` | 暴露 capabilities 中的 perspectives 供页面使用 |
| `frontend/src/components/System/CapabilityGuard.tsx` | `perspective` prop | 传入 capabilityEvaluator 做权限判定 |
| `frontend/src/services/capabilityService.ts` | `perspectives` 读取 | 规范化 capabilities 响应 |

**判定依据**：这些 `perspective` 在代码中实际表示"数据范围绑定类型（owner/manager）"，是技术实现细节，不直接暴露给用户。重命名它们会引入大量改动且无用户可见收益。

### 2.2 需要修复 — 与新设计矛盾

#### Batch A: 搜索结果路由路径仍拼 `/owner/`、`/manager/`

| 文件 | 行 | 当前行为 | 目标行为 |
|------|-----|----------|----------|
| `backend/src/services/search/service.py` | 163 | `route_path=f"/{perspective}/assets/{asset.id}"` | `route_path=f"/assets/{asset.id}"` |
| `backend/src/services/search/service.py` | 195-199 | manager → `/manager/projects/{id}`，owner → `/project/{id}` | 统一 `/project/{id}` |
| `backend/src/services/search/service.py` | 236 | `route_path=f"/{perspective}/contract-groups/{id}"` | `route_path=f"/contract-groups/{id}"` |
| `backend/src/services/search/service.py` | 277 | `route_path=f"/{perspective}/contract-groups/{id}"` | `route_path=f"/contract-groups/{id}"` |
| `backend/src/services/search/service.py` | 341 | `route_path=f"/{perspective}/customers/{party.id}"` | `route_path=f"/customers/{party.id}"` |
| `backend/src/services/search/service.py` | 389 | `route_path=f"/owner/property-certificates/{id}"` | `route_path=f"/property-certificates/{id}"` |

**影响**：用户从全局搜索点击结果后，会跳到 `/owner/assets/...` 等旧视角路由，被 `CanonicalEntryRedirect` 再次重定向，产生不必要的跳转链。

#### Batch B: `perspective_type` 字段名未同步为 `binding_type`

需求附录已将 `perspective_type` 更名为 `binding_type`，描述从"当前视角"改为"数据范围绑定类型"。

| 文件 | 行 | 当前 | 目标 |
|------|-----|------|------|
| `backend/src/schemas/party.py` | 200 | `perspective_type: str = Field(..., description="当前视角 owner/manager")` | `binding_type: str = Field(..., description="数据范围绑定类型 owner/manager")` |
| `backend/src/services/party/service.py` | 681 | `"perspective_type": perspective,` | `"binding_type": perspective,` |
| `frontend/src/types/party.ts` | 52 | `perspective_type: 'owner' \| 'manager';` | `binding_type: 'owner' \| 'manager';` |

**影响**：API 响应字段名与需求文档不一致，前端类型定义也不同步。

#### Batch C: 客户档案文案残留"当前视角"

| 文件 | 行 | 当前 | 目标 |
|------|-----|------|------|
| `frontend/src/pages/Customer/CustomerDetailPage.tsx` | 81 | `"客户档案基于当前视角聚合 Party 主档、联系人与合同历史。"` | `"客户档案基于当前数据范围聚合 Party 主档、联系人与合同历史。"` |

#### Batch D: `routes/perspective.ts` 功能已被 `dataScopeStore` 替代

| 文件 | 状态 |
|------|------|
| `frontend/src/routes/perspective.ts` | 工具函数仍被多个测试 mock，但生产代码已无直接引用（`grep` 结果为 0）。可安全删除。 |
| `frontend/src/routes/__tests__/perspective.test.ts` | 随 `perspective.ts` 一起删除。 |

**注意**：多个测试文件通过 `vi.mock('@/routes/perspective', ...)` 提供 mock。删除 `perspective.ts` 后，这些 mock 会变成空 mock（不报错但无意义），需要逐一清理。

#### Batch E: `contract_group_service.py` 的 `perspective` 参数语义

| 文件 | 方法 | 当前签名 | 分析 |
|------|------|----------|------|
| `backend/src/services/contract/contract_group_service.py` | `_assert_group_in_scope` | `perspective: Literal["owner", "manager"] \| None` | 参数名 `perspective` 实际表示"数据范围类型"，用于决定用 `owner_party_id` 还是 `operator_party_id` 做范围校验。语义正确但命名易混淆。 |
| `backend/src/services/contract/contract_group_service.py` | `get_group_detail` | `perspective: Literal["owner", "manager"] \| None = None` | 同上 |
| `backend/src/services/contract/contract_group_service.py` | `list_groups` | `perspective: Literal["owner", "manager"] \| None = None` | 同上 |

**判定**：这些 `perspective` 参数是内部服务层参数，不暴露给 API 层。当前调用方都从 `PerspectiveContext.perspective` 传入。建议**本轮不改**，留到 vNext 统一做服务层参数重命名为 `scope_type` 或 `binding_type`。

---

## 3. Execution Plan

### Phase 1: 搜索结果路由路径修复（Batch A）

**文件**：`backend/src/services/search/service.py`

**改动**：将所有 `route_path` 从 `/{perspective}/...` 改为扁平路由。

**测试**：
- `backend/tests/unit/services/search/test_search_service.py` — 更新 route_path 断言
- `backend/tests/unit/api/v1/test_search_api.py` — 已有测试，验证搜索结果 route_path 格式

**验证命令**：
```bash
cd backend && uv run pytest --no-cov tests/unit/services/search/test_search_service.py tests/unit/api/v1/test_search_api.py -q
```

### Phase 2: perspective_type → binding_type 重命名（Batch B）

**文件**：
1. `backend/src/schemas/party.py` — 字段名 + description
2. `backend/src/services/party/service.py` — 字典 key
3. `frontend/src/types/party.ts` — 接口字段名

**测试**：
- `backend/tests/unit/services/test_party_service.py` — 更新 `perspective_type` 断言
- `frontend/src/pages/Customer/__tests__/CustomerDetailPage.test.tsx` — 更新 mock 数据

**验证命令**：
```bash
cd backend && uv run pytest --no-cov tests/unit/services/test_party_service.py -q
cd frontend && corepack pnpm exec vitest run src/pages/Customer/__tests__/CustomerDetailPage.test.tsx -q
```

### Phase 3: 文案更新（Batch C）

**文件**：`frontend/src/pages/Customer/CustomerDetailPage.tsx`

**验证**：页面渲染测试无断言此文案，手动确认即可。

### Phase 4: 删除 `routes/perspective.ts` 及清理 mock（Batch D）

**步骤**：
1. 删除 `frontend/src/routes/perspective.ts`
2. 删除 `frontend/src/routes/__tests__/perspective.test.ts`
3. 清理以下测试中的 `vi.mock('@/routes/perspective', ...)` 空 mock：
   - `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
   - `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`
   - `frontend/src/pages/Assets/__tests__/AssetCreatePage.test.tsx`
   - `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx`
   - `frontend/src/hooks/__tests__/useProject.test.ts`
   - `frontend/src/hooks/__tests__/useAssets.test.ts`
   - `frontend/src/hooks/__tests__/useAnalytics.test.ts`

**验证命令**：
```bash
cd frontend && corepack pnpm exec vitest run --reporter=verbose
```

### Phase 5: 门禁验证

```bash
# 后端
cd backend && uv run --extra dev python -m ruff check .
cd backend && uv run pytest -m "not slow" -q

# 前端
cd frontend && corepack pnpm lint
cd frontend && corepack pnpm type-check
cd frontend && corepack pnpm test

# 文档
make docs-lint
```

---

## 4. Out of Scope（本轮不动）

| 项目 | 原因 |
|------|------|
| `contract_group_service.py` 的 `perspective` 参数 | 内部服务层参数，不影响用户可见行为 |
| `resource_perspective_registry.py` 的命名 | 是资源级数据范围注册表的标准名称 |
| `cache.py` 的 `perspective` 缓存键 | 内部缓存隔离机制 |
| `authz/service.py` 的 `_build_perspective_token` | 内部缓存键构造 |
| `context_builder.py` 的 `resolve_allowed_perspectives` | 内部工具函数 |
| 文档/CHANGELOG 中的历史"视角"措辞 | 历史记录，不修改 |

---

## 5. Risk Assessment

| 风险 | 影响 | 缓解 |
|------|------|------|
| Batch A 改动后搜索跳转异常 | 中 | 每个 route_path 改动后跑搜索相关单测 |
| Batch B `perspective_type` 重命名为 `binding_type` | 中 | 前后端同步改，跑 party service + customer detail 测试 |
| Batch D 删除 `perspective.ts` 后 mock 残留导致测试静默跳过 | 低 | 删除后跑全量前端测试，确认无 regression |

---

## 6. Success Criteria

1. 搜索结果 `route_path` 全部使用扁平路由（`/assets/...`、`/project/...`、`/contract-groups/...`、`/customers/...`、`/property-certificates/...`）
2. `CustomerProfileResponse` 中 `perspective_type` 字段更名为 `binding_type`
3. `routes/perspective.ts` 已删除，所有测试 mock 已清理
4. 客户档案页面文案已更新
5. `make check` 等价门禁全量通过
6. 无新的测试失败或 lint 错误引入
