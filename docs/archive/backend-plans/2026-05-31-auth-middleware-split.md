# Auth Middleware 拆分方案

## Status

✅ 已完成（2026-06-01）

## 背景

`backend/src/middleware/auth.py` 当前约 1470 行，承载 Cookie/JWT 身份解析、当前用户依赖、RBAC/ABAC 鉴权依赖、数据范围上下文、资源上下文加载、审计日志和遗留 checker。它是高风险授权中枢，不应混入代码库瘦身第一轮。

本方案只规划拆分边界。实施前必须先补护栏测试，避免拆文件时改变认证、鉴权或数据范围语义。

## 目标

1. 把身份解析、权限判定、数据范围、资源上下文加载和中间件编排分离。
2. 保持外部依赖入口清晰：路由继续通过稳定 helper 取得当前用户、鉴权依赖和数据范围依赖。
3. 拆分过程中不做兼容分支，不保留双实现。

## 非目标

- 不重新设计 RBAC/ABAC 策略模型。
- 不改变 Cookie 会话、JWT 校验、CSRF 或刷新机制。
- 不改变现有资源类型、action 命名和 data scope 语义。
- 不在本方案中处理 Out of Scope 模块启用。

## 目标结构

```text
backend/src/middleware/
  auth.py                # 对外兼容层在切换期最短存在；最终只保留公共入口或删除
  identity.py            # Cookie/JWT 解析、current user、active user
  authorization.py       # require_authz、AuthzContext、ABAC 调用
  data_scope.py          # DataScopeContext、require_data_scope_context、view_mode 解析
  resource_context.py    # 资产/项目/合同/组织/任务等可信资源上下文加载
  audit.py               # audit_action 与审计依赖
  middleware_stack.py    # 中间件注册与编排
```

## 实施顺序

### Phase 0：护栏测试

- 2026-05-31 已补第一批拆分护栏：公共入口导出、cookie-only 当前用户、缺失 token、黑名单 token、禁用用户、锁定用户；并复跑现有 authz/data-scope 相关测试。
- 当前用户：未登录、token 黑名单、禁用用户、cookie 登录。
- 鉴权：读拒绝映射 404、写拒绝映射 403、可信资源上下文优先于请求体。
- 数据范围：`view_mode=owner|manager` 仅分析域生效，常规 CRUD 保持自动范围。
- 资源上下文：asset、project、contract、organization、task、property certificate、ownership 的现有上下文加载行为先固定。
- 路由烟测：系统管理、项目、资产、合同关系、财务台账关键接口复用同一批授权夹具。

### Phase 1：Identity 拆分

- 2026-05-31 已新增 `backend/src/middleware/identity.py` 承载 Cookie/JWT 校验、当前用户、active user 和 optional auth；`backend/src/middleware/auth.py` 保持原公共依赖入口为薄包装，避免路由依赖签名漂移。
- 移出 `_validate_jwt_token()`、`get_current_user()`、`get_current_user_from_cookie()`、`get_current_active_user()`、`get_optional_current_user()`。
- 保持依赖函数签名不变。
- 验证 auth 和 optional auth 单测。

### Phase 2：Authorization 拆分

- 2026-05-31 已新增 `backend/src/middleware/authorization.py` 承载 `AuthzContext`、`AuthzPermissionChecker` 和 ABAC 资源上下文加载；`auth.py` 保留 `require_authz()` 公共工厂并注入当前 `authz_service` / logger，维持既有测试 patch 点和路由依赖入口。
- 移出 `AuthzContext`、`AuthzPermissionChecker`、`require_authz()`。
- 保持 ABAC 服务调用、拒绝映射和 trusted context 逻辑不变。
- 验证 `test_authz_dependency.py` 和路由分层测试。

### Phase 3：Data Scope 拆分

- 2026-06-01 已新增 `backend/src/middleware/data_scope.py` 承载 `DataScopeContext`、`DataScopeContextChecker` 和 data-scope 解析逻辑；`auth.py` 保留 `require_data_scope_context()` 公共工厂并注入当前 `authz_service` / `RBACService`，维持既有路由依赖入口、FastAPI dependency override 和测试 patch 点。
- 移出 `DataScopeContext`、`DataScopeContextChecker`、`require_data_scope_context()`。
- 保持 `view_mode` 只作用于分析域的规则。
- 验证 perspective/data-scope 相关单测和项目/资产可见性集成测试。

### Phase 4：Resource Context 拆分

- 2026-06-01 已新增 `backend/src/middleware/resource_context.py` 承载 asset、project、contract、ownership、party、role、user、task、organization、property certificate 的可信资源上下文加载；`authorization.AuthzPermissionChecker` 保留 `_load_*_scope_context()`、`_resolve_organization_party_id()`、`_resolve_ownership_party_id()` 等薄委托，维持既有测试直接调用和 patch 点。
- 把 `_load_asset_scope_context()`、`_load_project_scope_context()` 等资源上下文加载逻辑移入 `resource_context.py`。
- 明确每个 loader 的输入、输出和失败语义。
- 验证资源上下文单测。

### Phase 5：清理遗留 checker

- 2026-06-01 已从 `backend/src/middleware/auth.py` 删除无运行时调用方的 `PermissionChecker`、`OrganizationPermissionChecker`、`ResourcePermissionChecker`、`RBACPermissionChecker`、`RoleBasedAccessChecker`、`can_edit_contract()`、`get_user_rbac_permissions()` 及对应工厂；补充护栏测试确保这些旧入口不再从 auth facade 导出。
- 2026-06-01 已新增 `backend/src/middleware/audit.py` 和 `backend/src/middleware/security_config.py`，将审计依赖与安全配置展示逻辑移出 `auth.py`；`auth.py` 保留短公共入口包装，继续支持现有路由导入和 FastAPI dependency override。
- 逐个确认 `PermissionChecker`、`OrganizationPermissionChecker`、`ResourcePermissionChecker`、`RBACPermissionChecker`、`RoleBasedAccessChecker` 的实际调用方。
- 无调用方的删除；仍有调用方的迁移到 canonical `require_authz()` 或明确保留。

## 收尾说明

- 本次拆分不改变 Cookie 会话、JWT 校验、ABAC/RBAC 策略模型、资源类型、action 命名或 data-scope 语义，因此无需同步 `docs/specs/api-contract.md` 或 `docs/traceability/requirements-trace.md` 的契约内容。
- `backend/src/middleware/auth.py` 仍作为公共 facade 保留，用于稳定现有路由导入、测试 patch 点和 FastAPI dependency override；核心实现已分别落在 `identity.py`、`authorization.py`、`data_scope.py`、`resource_context.py`、`audit.py`、`security_config.py`。

## Done When

1. `backend/src/middleware/auth.py` 不再承载核心实现，或只保留短小公共入口。
2. 关键认证、鉴权、数据范围和资源上下文测试通过。
3. `docs/specs/api-contract.md` 和 `docs/traceability/requirements-trace.md` 如有契约变化已同步；无契约变化则不改 SSOT。
4. `CHANGELOG.md` 已更新。
5. `make check` 或受影响范围内的 lint/type/test/docs-lint 已通过。
