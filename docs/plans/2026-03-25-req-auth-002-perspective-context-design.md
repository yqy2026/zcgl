# REQ-AUTH-002 视角上下文强制注入设计

## 状态

📋 待评审

## 背景

`REQ-AUTH-002` 当前仍处于 `📋` 状态，但系统已经形成了两套并未完全收口的“视角”机制：

1. 前端通过 [frontend/src/routes/perspective.ts](/home/y/projects/zcgl/frontend/src/routes/perspective.ts) 从 `/owner/*`、`/manager/*` 路由推导视角。
2. 后端通过 [backend/src/services/authz/service.py](/home/y/projects/zcgl/backend/src/services/authz/service.py) 与 [backend/src/services/authz/context_builder.py](/home/y/projects/zcgl/backend/src/services/authz/context_builder.py) 解析用户拥有哪些 `owner_party_ids` / `manager_party_ids`。

当前缺口在于：后端知道“用户拥有哪些 scope”，但不知道“这一次请求到底应该按 owner 还是 manager 口径执行”。因此业务查询、统计、搜索仍可能依赖隐式 scope 或前端约定，而不是单一协议真值。

同时，前端在 [frontend/src/utils/authz/capabilityEvaluator.ts](/home/y/projects/zcgl/frontend/src/utils/authz/capabilityEvaluator.ts) 中保留了 `project -> manager` 的 `PERSPECTIVE_OVERRIDES` 硬编码，说明“资源允许哪些视角”这条规则仍没有回到后端权威模型。

## 目标

本轮设计目标是彻底收口 `REQ-AUTH-002`，把“当前视角”升级为业务请求的强协议，而不是前端约定：

- 所有业务请求必须携带当前视角上下文。
- 后端统一校验、注入、传播 `PerspectiveContext`。
- 查询、统计、搜索、导出都按单一视角口径执行，不再 owner/manager 混查兜底。
- `/auth/me/capabilities` 由后端直接返回资源级 perspective 能力，前端不再保留资源级 override 硬编码。
- 当默认/当前视角失效时，系统进入统一的视角恢复流程，而不是各页面各自 403。

## 非目标

本轮明确不做以下事项：

- 不重做 RBAC / ABAC 基础模型本身。
- 不引入新的“selected perspective” 服务端 session 状态。
- 不重构 owner / manager 现有 URL 结构。
- 不把 neutral 页面（如 `/dashboard`、`/profile`）强行改造成必须带视角的页面。

## 备选方案

### 方案 A：Route + Request Header + Backend Context（推荐）

- 前端 canonical route 仍为用户可见真值。
- API 客户端自动注入 `X-Perspective: owner|manager`。
- 后端中间件统一解析 header，构建 `PerspectiveContext` 并注入 request。
- 业务查询只按 `PerspectiveContext.effective_party_ids` 执行。

优点：

- 协议明确，浏览器外调用也可验证。
- 后端可审计、可 fail-closed。
- 与现有 route-based 结构兼容最好。

缺点：

- 需要补一层全局请求契约和中间件 plumbing。

### 方案 B：Route-derived only

- 前端仅按当前路由区分 owner/manager。
- 后端继续只依赖现有 party scope，不知道当前请求视角。

优点：

- 改动最小。

缺点：

- 不能真正解决口径漂移。
- 浏览器外请求、导出、搜索、统计仍可能继续隐式混口径。

### 方案 C：Server Session Selected Perspective

- 当前视角写入服务端 session 或 cookie，再由后端读取。

优点：

- 请求面上不需要显式 header。

缺点：

- 多标签页、刷新、跨入口跳转更容易漂移。
- 与现有 route-based canonical 结构冲突。

## 选择方案

采用方案 A，并以“强协议 + 单一真值”方式落地：

- 非 neutral 业务请求缺少 `X-Perspective` 直接拒绝。
- `X-Perspective` 非 `owner|manager` 直接拒绝。
- `X-Perspective` 不属于当前用户 capabilities 允许集合直接拒绝。
- 后端不再根据用户同时拥有的 owner/manager scope 自行猜测口径。

## 设计细节

### 1. 请求契约

所有业务域请求统一携带：

```http
X-Perspective: owner
```

或

```http
X-Perspective: manager
```

规则：

- header 值只允许 `owner` 或 `manager`。
- 前端业务调用不得手写该 header，由 [frontend/src/api/client.ts](/home/y/projects/zcgl/frontend/src/api/client.ts) 自动注入。
- header 真值只能来自当前路由 [frontend/src/routes/perspective.ts](/home/y/projects/zcgl/frontend/src/routes/perspective.ts)。

### 2. 后端 `PerspectiveContext`

在 [backend/src/middleware/auth.py](/home/y/projects/zcgl/backend/src/middleware/auth.py) 中新增独立的 `PerspectiveContext`，在认证通过后、业务鉴权和服务调用前解析。

建议字段：

- `perspective: Literal["owner", "manager"]`
- `allowed_perspectives: list[str]`
- `owner_party_ids: list[str]`
- `manager_party_ids: list[str]`
- `effective_party_ids: list[str]`
- `source: Literal["header"]`

计算规则：

- `owner`：`effective_party_ids = owner_party_ids`
- `manager`：`effective_party_ids = manager_party_ids`

禁止规则：

- 不允许 owner/manager 混合并集兜底。
- 不允许缺失或非法 perspective 时自动回退到任一 scope。

### 3. 后端能力模型收口

现有 [backend/src/api/v1/auth/auth_modules/authentication.py](/home/y/projects/zcgl/backend/src/api/v1/auth/auth_modules/authentication.py) 中的 `/auth/me/capabilities` 需要从“用户有哪些 owner/manager 绑定”收口为“每个资源允许哪些 perspective”。

设计要求：

- `capabilities[].perspectives` 必须表示资源级可访问视角，而不是主体绑定快照的简单镜像。
- `project` 仅允许 `manager` 这类规则必须由后端生成。
- 前端 [frontend/src/utils/authz/capabilityEvaluator.ts](/home/y/projects/zcgl/frontend/src/utils/authz/capabilityEvaluator.ts) 中的 `PERSPECTIVE_OVERRIDES` 应在实现后删除。

### 4. 业务查询/统计/搜索收口

所有业务查询统一消费 `PerspectiveContext.effective_party_ids`，而不是继续通过混合 party filter 猜测：

- 资产：列表、详情、分析、导出
- 项目：列表、详情、汇总
- 合同组：列表、详情、导入、台账
- 分析：统计、趋势、分布、导出
- 搜索：全局搜索及相关 suggestion

收口要求：

- 服务层 / CRUD 层统一显式接收 `perspective + effective_party_ids`。
- 不再允许默认 owner/manager scope 并查。
- neutral 业务接口必须显式声明豁免，否则按业务接口处理。

### 5. 视角失效 UX

当前/默认视角失效不能只表现为 403，需要统一恢复流程：

#### neutral routes

- 如 `/dashboard`、`/profile`、`/auth/*`
- 不要求 perspective header
- 可提示用户当前可用视角

#### perspective routes

- `/owner/*`、`/manager/*`
- 进入页面前先校验 route perspective 是否仍在 capabilities 可用集合中
- 若已失效，不发业务请求，立即进入统一 `PerspectiveResolution` 页面

#### legacy shared routes

- 继续由 [frontend/src/routes/LegacyRouteRedirect.tsx](/home/y/projects/zcgl/frontend/src/routes/LegacyRouteRedirect.tsx) 接管
- 但内部选路逻辑应与 `PerspectiveResolution` 共享，不再多处各自 owner-first / manager-first

`PerspectiveResolution` 页面职责：

- 若还有另一可用视角，提供唯一安全跳转目标
- 若无任何可用视角，显示 fail-closed 拒绝态并提示联系管理员

### 6. 豁免规则

必须豁免 perspective header 的接口：

- `/auth/*`
- `/auth/me/capabilities`
- 纯系统健康检查 / 诊断接口

默认不豁免的接口：

- 资产
- 项目
- 合同组
- 台账
- 分析
- 搜索
- 导出
- PDF 导入会话业务接口

若某接口 today 无法明确归类，默认按业务接口处理，缺 header 直接拒绝。

### 7. 路由分类真值表

为避免“强协议”被大量临时豁免打穿，本轮先明确现有路由分层：

#### A. perspective canonical routes

这些路由的 perspective 真值来自 URL，必须携带 `X-Perspective`：

- `/owner/assets/*`
- `/owner/contract-groups/*`
- `/owner/property-certificates/*`
- `/manager/assets/*`
- `/manager/contract-groups/*`
- `/manager/projects/*`

#### B. neutral routes（永久 neutral）

这些路由不表达 owner/manager 视角，不应强制 perspective header：

- `/dashboard`
- `/profile`
- `/auth/*`
- `/system/*`（管理员系统管理）

#### C. neutral business routes（待迁移或待裁决）

这些路由 today 仍是共享业务入口，但从长期看不应永久维持为“带业务却无视角”：

- `/assets/*`
- `/contract-groups/*`
- `/project/*`
- `/property-certificates/*`
- `/ownership/*`

处理原则：

- Phase 1 不直接删除这些路由，但它们不得继续直接发起业务请求。
- 对列表入口优先复用 `LegacyRouteRedirect` / `PerspectiveResolution` 做重定向。
- 对详情 / 编辑 / 导入类入口必须定义 deterministic fallback，不允许“先请求再 403”。

其中 `/ownership/*` 需要单独标注为“待裁决业务域”：

- 若后续确认权属方是 owner-only 业务对象，则迁入 owner canonical route。
- 若后续确认其为跨视角共享主数据，则保留 neutral，但必须在设计/需求里明确写成“永久 neutral 业务域”，并从 `REQ-AUTH-002` 的强协议范围中正式豁免。

在该裁决未完成前，实施计划不得把 `/ownership/*` 误算为 canonical perspective route。

### 8. resource -> perspectives 的后端真值来源

`/auth/me/capabilities` 不应再把 `subject_context.owner_party_ids/manager_party_ids` 直接镜像成所有资源的 `perspectives`。本轮要求新增一层后端资源视角注册表，作为资源级 perspective 的单一真值。

推荐落点：

- 新增独立模块，例如 `backend/src/services/authz/resource_perspective_registry.py`
- 由后端静态注册每个 `resource_type` 的允许视角集合
- `authz_service.get_capabilities()` 在聚合 `actions_by_resource` 后，再以该注册表裁剪 `capabilities[].perspectives`

理由：

- 现有 ABAC 规则模型 [backend/src/models/abac.py](/home/y/projects/zcgl/backend/src/models/abac.py) 只有 `resource_type + action`，没有 perspective 维度；若直接依赖 policy/rule 表，必须先扩 schema，范围过大。
- 先用注册表把资源级 perspective 真值收口到后端，能立刻消除前端 `PERSPECTIVE_OVERRIDES`。
- 后续若要把 perspective 下沉到 ABAC rule 元数据，再从注册表平滑迁移即可。

注册表示例：

- `asset` -> `["owner", "manager"]`
- `contract_group` -> `["owner", "manager"]`
- `project` -> `["manager"]`
- `property_certificate` -> `["owner"]`
- `analytics` -> `["owner", "manager"]`
- `party` / `role` / `user` / `system_*` -> `[]`（neutral/admin，不参与业务视角）

空数组语义需要定死：

- `[]` 表示该资源不受 owner/manager perspective 控制，属于 neutral/admin resource
- 前端不得将 `[]` 理解成“两个视角都允许”

### 9. invalid perspective route 的确定性 fallback 映射

`PerspectiveResolution` 和 `LegacyRouteRedirect` 不能只做到“有另一个视角就跳过去”，必须定义 deterministic route mapping。否则详情/编辑/导入路径仍会各处各猜。

建议映射规则：

#### 列表页

- `/assets`、`/assets/list` -> `owner assets` 优先，其次 `manager assets`
- `/contract-groups` -> `owner contract-groups` 优先，其次 `manager contract-groups`
- `/project` -> `manager projects`
- `/property-certificates` -> `owner property-certificates`

#### 详情页

- `/owner/assets/:id` 失效 -> `/manager/assets/:id`
- `/manager/assets/:id` 失效 -> `/owner/assets/:id`
- `/owner/contract-groups/:id` 失效 -> `/manager/contract-groups/:id`
- `/manager/contract-groups/:id` 失效 -> `/owner/contract-groups/:id`
- `/manager/projects/:id` 失效 -> `/manager/projects`
- `/owner/property-certificates/:id` 失效 -> `/owner/property-certificates`

原则：

- 只有在另一视角存在同资源 canonical detail route 时，才允许 detail-to-detail 跳转。
- 否则统一退回该资源的 canonical list route。

#### 编辑 / 创建 / 导入页

- 失效后不做“跨视角继续编辑”跳转
- 一律退回该资源可用的 canonical list route 或 import/list landing

原因：

- create/edit/import 页面通常携带未提交状态与表单上下文，跨视角直接迁移风险过高。
- fail-closed 比“帮用户猜测继续在哪个视角编辑”更安全。

#### 无任何可用视角

- 统一退回 `/dashboard`，并展示明确的 `PerspectiveResolution` 拒绝态，不允许 silent redirect。

## 实施阶段建议

### Phase 1：协议层

- 前端 API client 自动注入 `X-Perspective`
- 后端新增 `PerspectiveContext`
- neutral / business 接口豁免表收口
- route 分类表与 deterministic fallback mapping 落地
- `/auth/me/capabilities` 返回资源级 perspective

### Phase 2：业务口径收口

- 资产、项目、合同组、分析、搜索链路按 `effective_party_ids` 收口
- 删除前端 `PERSPECTIVE_OVERRIDES`

### Phase 3：前端恢复 UX

- 新增 `PerspectiveResolution`
- Route guard / Legacy redirect 统一复用 resolution 逻辑

## 测试策略

### 后端

- middleware 单测：
  - 缺 header 拒绝
  - 非法 header 拒绝
  - 无该视角权限拒绝
  - neutral 接口豁免
- capabilities 契约测试：
  - `project` 等资源返回的 perspective 由后端定义
- API 口径测试：
  - 同一用户 owner/manager 下资产、项目、分析结果不同

### 前端

- `apiClient` header 注入测试
- route guard / `PerspectiveResolution` 测试
- owner / manager 页面切换后的请求参数与缓存隔离测试

### E2E

- 同一用户具备双视角时，切换 canonical route 验证结果口径不同
- 当前视角失效后进入 resolution，而不是 403 白屏

## 影响文件（设计阶段预估）

后端重点：

- `backend/src/middleware/auth.py`
- `backend/src/services/authz/service.py`
- `backend/src/services/authz/context_builder.py`
- `backend/src/services/party_scope.py`
- `backend/src/crud/query_builder.py`
- `backend/src/api/v1/auth/auth_modules/authentication.py`
- `backend/src/api/v1/assets/*`
- `backend/src/api/v1/analytics/*`
- `backend/src/api/v1/contracts/*`
- `backend/src/api/v1/projects/*`

前端重点：

- `frontend/src/api/client.ts`
- `frontend/src/routes/perspective.ts`
- `frontend/src/routes/LegacyRouteRedirect.tsx`
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/utils/authz/capabilityEvaluator.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/hooks/useCapabilities.ts`

文档重点：

- `docs/requirements-specification.md`
- `docs/plans/README.md`
- `CHANGELOG.md`

## 完成定义

当以下条件同时满足时，可视为 `REQ-AUTH-002` 完成：

- 所有业务请求都可追溯到明确 `perspective`
- 后端不存在 owner/manager 混查默认路径
- 前端不存在资源级 perspective override 硬编码
- 当前视角失效时存在统一恢复流程
- SSOT 与测试证据同步完成
