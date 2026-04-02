# REQ-SCH-001/002/003 全局搜索实施计划

> 状态：✅ 已完成
> 关联需求：REQ-SCH-001 / REQ-SCH-002 / REQ-SCH-003
> 目标：交付带视角权限过滤的统一全局搜索入口，覆盖资产、项目、合同组、合同、客户、产权证，并支持全部视图与按对象分组视图。

## 1. 当前现状

### 已有基础
- 资产域已具备搜索基础：
  - `backend/src/crud/asset.py` 支持资产多字段搜索
  - `backend/src/core/search_index.py` + `backend/src/models/asset_search_index.py` 支持加密字段 blind index
- 项目、权属方、组织分别有各自搜索接口，但都不是统一全局搜索入口。
- 客户域刚完成 `CustomerProfile` 聚合口径，可作为全局搜索中的客户对象来源。
- 前端暂无统一全局搜索入口、搜索结果页和对象级跳转规则。

### 缺口
- 没有统一搜索 API。
- 没有跨对象统一结果模型、排序策略和高亮摘要。
- 没有按当前 `X-Perspective` / 资源权限过滤的统一搜索层。
- 没有前端全局入口、结果页和“全部/分组”双视图切换。

## 2. 范围

### 本次纳入
- REQ-SCH-001：统一入口与对象范围
- REQ-SCH-002：结果组织与排序
- REQ-SCH-003：权限过滤

### 本次不纳入
- Redis / Elasticsearch / PostgreSQL FTS 大规模索引重构
- 任务、通知搜索
- 搜索推荐词、拼写纠错、语义检索

## 3. 核心决策

1. **统一聚合，不新建独立搜索基础设施**
- MVP 使用“各域现有查询能力 + 统一聚合服务”实现搜索。
- 资产继续复用现有 blind index。
- 其他对象先走结构化字段搜索。

2. **客户对象按 `CustomerProfile` 口径搜索**
- 不直接暴露系统管理里的全量 `Party`。
- 搜索命中的客户结果必须符合当前视角下“客户为合同对方主体”的定义。

3. **权限过滤 fail-closed**
- 所有搜索结果必须先经过当前视角和资源权限约束。
- 未授权对象完全不返回，不显示“存在但无权访问”占位。

4. **先交付结果页，再考虑全局 Header 入口植入**
- 降低第一批改动耦合度。
- 先落路由、服务、结果页和详情跳转；再补 Header/导航入口。

## 4. 结果模型

新增统一搜索结果模型 `GlobalSearchResult`，建议字段：
- `object_type`: `asset | project | contract_group | contract | customer | property_certificate`
- `object_id`
- `title`
- `subtitle`
- `summary`
- `keywords`: 命中的关键字段标签
- `route_path`
- `group_label`
- `score`
- `business_rank`

新增统一响应：
- `items`: 全部视图结果
- `groups`: 分组视图结果
- `query`
- `total`

## 5. 排序规则

### 默认排序
1. `business_rank` 高优先
2. `score` 高优先
3. 标题精确命中优先于模糊命中
4. 最近更新时间倒序作为最终兜底

### 业务置顶规则（MVP）
- 资产：`asset_code` / `asset_name` 精确命中优先
- 项目：`project_code` / `project_name` 精确命中优先
- 合同组/合同：编号精确命中优先
- 客户：`customer_name` / `unified_identifier` 精确命中优先
- 产权证：`certificate_number` 精确命中优先

## 6. 实施拆分

### 任务 A：后端统一搜索 API
目标：在不引入额外搜索基础设施的前提下，提供统一全局搜索接口与结果模型。

涉及文件（预计 < 20）：
- 新增：`backend/src/schemas/search.py`
- 新增：`backend/src/services/search/service.py`
- 新增：`backend/src/services/search/__init__.py`
- 新增：`backend/src/api/v1/search.py`
- 修改：`backend/src/api/v1/__init__.py`
- 修改：`backend/src/services/authz/resource_perspective_registry.py`
- 可能修改：`backend/src/services/party/service.py`
- 可能修改：`backend/src/services/property_certificate/service.py`
- 可能修改：`backend/src/services/project/service.py`
- 可能修改：`backend/src/crud/asset.py`

TDD 顺序：
1. 先写服务层失败测试：统一聚合、分组、排序、权限 fail-closed。
2. 再写 API 失败测试：缺少 `X-Perspective`、未授权对象过滤、响应结构。
3. 实现最小搜索服务和 API。

### 任务 B：前端搜索结果页
目标：交付可用的搜索结果页和对象跳转。

涉及文件（预计 < 20）：
- 新增：`frontend/src/pages/Search/GlobalSearchPage.tsx`
- 新增：`frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx`
- 新增：`frontend/src/services/searchService.ts`
- 新增：`frontend/src/services/__tests__/searchService.test.ts`
- 新增：`frontend/src/types/search.ts`
- 修改：`frontend/src/routes/AppRoutes.tsx`
- 修改：`frontend/src/constants/routes.ts`
- 修改：`frontend/src/config/breadcrumb.ts`
- 可能新增：`frontend/src/pages/Search/GlobalSearchPage.module.css`

TDD 顺序：
1. 先写 service 和 page 失败测试。
2. 实现“全部视图 / 分组视图”切换。
3. 实现结果项跳转。

### 任务 C：前端入口接入与 SSOT 收口
目标：补搜索入口、文档和最终验证。

涉及文件（预计 < 20）：
- 可能修改：`frontend/src/components/Layout/AppHeader.tsx`
- 可能修改：`frontend/src/components/Layout/__tests__/AppHeader.test.tsx`
- 修改：`docs/requirements-specification.md`
- 修改：`CHANGELOG.md`
- 修改：`docs/plans/README.md`

TDD / 验证顺序：
1. 先补入口测试，再接入搜索按钮/输入框。
2. 跑定向测试。
3. 跑 `make docs-lint` 和 `make check`。

## 7. 验证清单

### 后端
- `cd backend && uv run pytest --no-cov tests/unit/services/search/test_search_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_search_api.py -q`

### 前端
- `cd frontend && pnpm exec vitest run src/services/__tests__/searchService.test.ts src/pages/Search/__tests__/GlobalSearchPage.test.tsx --reporter=verbose`
- 如接入 Header：加跑 `src/components/Layout/__tests__/AppHeader.test.tsx`

### 全量门禁
- `make docs-lint`
- `make check`

## 8. 风险

- 项目和产权证的现有搜索能力较分散，统一聚合层可能需要补少量服务封装。
- 客户搜索如果直接扫 `Party` 会与 `CustomerProfile` 口径冲突，必须坚持聚合视图。
- 搜索排序若过度复杂，容易在 MVP 阶段引入不可控回归；本次只做可解释的规则排序。
