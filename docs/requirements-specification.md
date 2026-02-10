# 土地物业资产管理系统需求规格说明书（SRS）

## ✅ Status
**当前状态**: Active Baseline (2026-02-09)  
**基线策略**: 代码现状优先（Code-as-Truth）  
**文档类型**: 可验收级需求规格

---

## 1. 文档定位

本规格用于替代历史散落 PRD 的“单一权威需求基线（SSOT）”，用于：
- 研发实现范围界定
- 测试验收依据
- 新需求评审与变更影响分析

> 说明：本规格只收录“已被代码与测试证实”的能力。  
> 未实现但可能需要的内容统一放入 [第 10 章 vNext 候选](#10-vnext-候选需求未实现)。

---

## 2. 证据与判定规则

### 2.1 证据优先级
1. 单元/集成测试（`backend/tests/`, `frontend/src/**/__tests__`）
2. 路由 + 服务 + 数据模型实现（`backend/src/`）
3. 前端路由与菜单（`frontend/src/routes/`, `frontend/src/config/`）
4. 既有文档（仅作辅助，不作为最终判定）

### 2.2 收录规则
- 每条需求必须能映射到至少一个代码证据路径。
- 高风险需求（认证、权限、删除约束、数据一致性）优先要求有测试证据。
- 与代码冲突的历史文档结论不纳入本基线。

---

## 3. 系统范围

### 3.1 In Scope（已实现）
- 资产全生命周期管理（列表/详情/创建/更新/删除/恢复/彻底删除）
- 资产批量操作、导入、附件管理
- 租赁合同管理（合同、生命周期、台账、统计）
- 认证与 RBAC 权限管理
- 组织、字典、通知、任务、联系人、催缴等系统模块
- PDF 智能导入与批量导入（批量导入为可选注册）
- 综合分析与统计 API

### 3.2 Out of Scope（当前未纳入）
- 审批流/工作流引擎
- 财务总账/税票系统
- 高级 BI 建模平台
- 跨租户隔离策略的完整产品化治理

---

## 4. 角色与权限模型（当前基线）

### REQ-AUTH-ROLE-001 角色与权限由 RBAC 服务统一管理
- 需求描述：角色、权限、授权粒度变更由 RBAC 服务层统一处理，路由层仅编排。
- 验收标准：
  - 角色增删改查可通过 `/api/v1/roles/*` 完成。
  - 权限授予/撤销可通过 roles 路由统一入口完成。
  - 非管理员访问他人权限摘要时应被拒绝。
- 代码证据：
  - `backend/src/api/v1/auth/roles.py`
  - `backend/src/services/permission/rbac_service.py`
  - `backend/tests/unit/api/v1/test_roles_permission_grants.py`

---

## 5. 功能需求（可验收）

### 5.1 资产管理

#### REQ-AST-001 资产列表支持分页、搜索、筛选、排序与关联投影控制
- 需求描述：资产列表接口应支持分页参数、筛选参数、排序参数及 `include_relations` 投影开关。
- 验收标准：
  - `page/page_size` 生效，`page_size` 受上限约束。
  - 支持 `ownership_status/property_nature/usage_status/...` 等筛选。
  - `include_relations=false` 时不强制返回合同投影字段。
  - `include_relations=true` 时可返回关联投影（如 `ownership_entity`、活动合同信息）。
- 代码证据：
  - `backend/src/api/v1/assets/assets.py`
  - `backend/src/services/asset/asset_service.py`
  - `backend/tests/unit/api/v1/test_assets_projection_guard.py`

#### REQ-AST-002 创建资产必须通过枚举校验、重名校验、面积一致性校验
- 需求描述：创建资产时，必须先做业务合法性校验，再入库。
- 验收标准：
  - 枚举非法时返回 422。
  - `property_name` 重复时拒绝创建。
  - `rented_area > rentable_area` 时拒绝创建。
- 代码证据：
  - `backend/src/services/asset/asset_service.py`
  - `backend/src/services/asset/asset_calculator.py`
  - `backend/tests/unit/services/asset/test_asset_service.py`

#### REQ-AST-003 资产删除采用软删除并受关联约束保护
- 需求描述：资产删除优先软删除；当资产已关联合同/产权证/台账时必须阻止删除。
- 验收标准：
  - 删除后 `data_status` 变更为“已删除”。
  - 已关联 `rent_contract_assets` / `property_cert_assets` / `RentLedger` 时删除失败。
  - 支持“恢复”与“彻底删除”（彻底删除仅允许已删除状态资产）。
- 代码证据：
  - `backend/src/services/asset/asset_service.py`
  - `backend/src/api/v1/assets/assets.py`
  - `backend/tests/unit/services/asset/test_asset_service.py`

#### REQ-AST-004 资产关键展示字段为计算/投影字段，不直接落库写入
- 需求描述：`unrented_area`、`occupancy_rate`、`ownership_entity` 作为计算/投影语义处理。
- 验收标准：
  - 更新/创建请求中携带这些字段时，数据访问层应剔除或忽略写库。
  - `ownership_entity` 从关联 `ownership` 动态投影。
  - `version` 字段用于乐观锁控制并可触发冲突处理。
- 代码证据：
  - `backend/src/models/asset.py`
  - `backend/src/crud/asset.py`
  - `backend/src/services/asset/asset_service.py`
  - `backend/tests/unit/models/test_asset.py`

#### REQ-AST-005 资产批量、导入、附件能力必须通过子路由提供
- 需求描述：资产模块必须保留批量、导入、附件接口并纳入统一路由。
- 验收标准：
  - `/assets/batch-*`、`/assets/import`、附件上传/下载/删除端点可用。
  - 资产主路由通过子路由组合方式挂载上述能力。
- 代码证据：
  - `backend/src/api/v1/assets/assets.py`
  - `backend/src/api/v1/assets/asset_batch.py`
  - `backend/src/api/v1/assets/asset_import.py`
  - `backend/src/api/v1/assets/asset_attachments.py`

---

### 5.2 租赁合同管理

#### REQ-RNT-001 合同创建需验证资产与权属方存在性
- 需求描述：创建合同前必须验证关联资产与权属方存在，缺失则拒绝。
- 验收标准：
  - `asset_ids` 中任一资产不存在应返回资源不存在错误。
  - `ownership_id` 不存在应返回资源不存在错误。
- 代码证据：
  - `backend/src/api/v1/rent_contracts/contracts.py`
  - `backend/src/services/rent_contract/service.py`

#### REQ-RNT-002 合同生命周期管理需包含冲突检测与状态流转
- 需求描述：合同创建/更新/续签/终止应通过生命周期服务，执行时段冲突检测。
- 验收标准：
  - 冲突资产给出冲突明细并拒绝提交。
  - 生命周期端点可触发合同状态流转。
- 代码证据：
  - `backend/src/services/rent_contract/lifecycle_service.py`
  - `backend/src/api/v1/rent_contracts/lifecycle.py`

#### REQ-RNT-003 租金台账支持生成、查询、批量更新与导出
- 需求描述：系统应提供合同相关台账自动生成与批量维护能力。
- 验收标准：
  - 支持按合同/资产/权属方/时间范围查询台账。
  - 支持批量更新支付状态及相关字段。
  - 支持台账导出能力。
- 代码证据：
  - `backend/src/api/v1/rent_contracts/ledger.py`
  - `backend/src/services/rent_contract/ledger_service.py`

#### REQ-RNT-004 租赁统计需提供概览、按维度查询与导出
- 需求描述：租赁统计接口应覆盖概览、按权属方/资产/月度等维度查询与导出。
- 验收标准：
  - 统计模块端点可按定义路径访问并返回结构化结果。
- 代码证据：
  - `backend/src/api/v1/rent_contracts/statistics.py`
  - `frontend/src/pages/Rental/RentStatisticsPage.tsx`

---

### 5.3 认证与会话

#### REQ-AUTH-001 认证模式为 HttpOnly Cookie
- 需求描述：登录与刷新流程必须通过 Cookie 写入令牌，不在响应体输出敏感令牌供前端存储。
- 验收标准：
  - 登录成功设置 `auth_token` 与 `refresh_token` Cookie。
  - 刷新接口从 Cookie 读取刷新令牌并轮转 Cookie。
  - 前端请求默认 `withCredentials=true`。
- 代码证据：
  - `backend/src/api/v1/auth/auth_modules/authentication.py`
  - `backend/src/security/cookie_manager.py`
  - `backend/src/middleware/auth.py`
  - `frontend/src/api/client.ts`
  - `frontend/src/services/authService.ts`
  - `backend/tests/unit/middleware/test_optional_auth.py`

#### REQ-AUTH-002 认证路由遵循“路由编排、服务执行业务”分层
- 需求描述：认证路由不得直接操作 CRUD 与事务提交，应委托服务层。
- 验收标准：
  - 认证模块分层测试通过。
  - 路由层无直接 `db.commit` 语句。
- 代码证据：
  - `backend/src/api/v1/auth/auth_modules/authentication.py`
  - `backend/tests/unit/api/v1/test_authentication_layering.py`

---

### 5.4 系统管理与文档处理

#### REQ-SYS-001 系统基础端点提供健康检查、系统信息、API根说明
- 需求描述：系统模块应提供基础可观测与服务信息接口。
- 验收标准：
  - 健康检查端点返回数据库健康与指标摘要。
  - 系统信息端点返回版本与能力说明。
  - API 根说明端点返回核心入口路径。
- 代码证据：
  - `backend/src/api/v1/system/system.py`
  - `backend/src/main.py`

#### REQ-DOC-001 文档处理应支持 PDF 导入主流程与批量处理能力
- 需求描述：系统需提供 PDF 上传、会话、进度与批处理相关接口。
- 验收标准：
  - 主流程路由在 `/api/v1/pdf-import/*` 可访问。
  - 批量路由模块可导入时应自动挂载。
- 代码证据：
  - `backend/src/api/v1/documents/pdf_import.py`
  - `backend/src/api/v1/documents/pdf_upload.py`
  - `backend/src/api/v1/documents/pdf_batch_routes.py`
  - `backend/src/api/v1/__init__.py`

---

### 5.5 分析与报表

#### REQ-ANA-001 分析模块提供综合分析、趋势、分布、缓存管理与导出
- 需求描述：分析模块应输出可用于看板的聚合数据，并支持缓存管理与导出。
- 验收标准：
  - `/analytics/comprehensive`、`/analytics/trend`、`/analytics/distribution` 可访问。
  - 提供缓存统计与清理端点。
- 代码证据：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/src/services/analytics/analytics_service.py`

---

## 6. 跨模块约束

### REQ-XCUT-001 API 统一版本化
- 所有业务 API 统一挂载到 `/api/v1/*`。
- 证据：
  - `backend/src/core/router_registry.py`
  - `backend/src/main.py`
  - `backend/src/api/v1/__init__.py`

### REQ-XCUT-002 路由层不得绕过服务层直接承载业务规则
- 证据：
  - `backend/tests/unit/api/v1/test_project_layering.py`
  - `backend/tests/unit/api/v1/test_authentication_layering.py`
  - `backend/tests/unit/api/v1/test_assets_ownership_entities_layering.py`

### REQ-XCUT-003 敏感字段采用字段级加密，并允许开发环境降级
- 需求描述：PII 字段通过 `SensitiveDataHandler` + `FieldEncryptor` 处理；无有效密钥时降级明文并记录告警。
- 证据：
  - `backend/src/crud/asset.py`
  - `backend/src/crud/contact.py`
  - `backend/src/crud/property_certificate.py`
  - `backend/src/core/encryption.py`

### REQ-XCUT-004 前端导航与路由应与后端模块能力对齐
- 证据：
  - `frontend/src/constants/routes.ts`
  - `frontend/src/routes/AppRoutes.tsx`
  - `frontend/src/config/menuConfig.tsx`

---

## 7. 非功能需求基线

### 7.1 安全性
- Cookie 鉴权默认启用 `HttpOnly`，并带 `SameSite` 策略。
- CORS 必须允许 `Authorization`、`X-CSRF-Token` 等关键请求头。
- 生产环境禁止弱密钥与部分降级配置。
- 证据：
  - `backend/src/security/cookie_manager.py`
  - `backend/src/main.py`
  - `backend/src/security/secret_validator.py`

### 7.2 可维护性
- 路由聚合与模块拆分（auth/rent_contracts/documents）作为结构基线。
- 分层约束以测试持续守护。
- 证据：
  - `backend/src/api/v1/auth/auth.py`
  - `backend/src/api/v1/rent_contracts/__init__.py`
  - `backend/tests/unit/api/v1/*layering*.py`

### 7.3 可观测性
- 提供健康检查与系统信息端点。
- 支持操作审计与认证审计记录。
- 证据：
  - `backend/src/api/v1/system/system.py`
  - `backend/src/services/core/audit_service.py`

---

## 8. 需求追踪矩阵（核心）

| 需求ID | 关键端点/能力 | 数据模型/服务 | 关键测试证据 |
|---|---|---|---|
| REQ-AST-001 | `/api/v1/assets` | `AssetService.get_assets` | `backend/tests/unit/api/v1/test_assets_projection_guard.py` |
| REQ-AST-002 | `POST /api/v1/assets` | `AssetService.create_asset` | `backend/tests/unit/services/asset/test_asset_service.py` |
| REQ-AST-003 | `DELETE/restore/hard-delete` | `AssetService._ensure_asset_not_linked` | `backend/tests/unit/services/asset/test_asset_service.py` |
| REQ-RNT-001 | `POST /api/v1/rental-contracts/contracts` | `rent_contract_service` | `backend/src/api/v1/rent_contracts/contracts.py` |
| REQ-RNT-003 | `/api/v1/rental-contracts/ledger/*` | `RentContractLedgerService` | `backend/src/services/rent_contract/ledger_service.py` |
| REQ-AUTH-001 | `/api/v1/auth/login/refresh` | `CookieManager` | `backend/tests/unit/middleware/test_optional_auth.py` |
| REQ-AUTH-ROLE-001 | `/api/v1/roles/*` | `RBACService` | `backend/tests/unit/api/v1/test_roles_permission_grants.py` |
| REQ-SYS-001 | `/api/v1/monitoring/health` | `get_database_status` | `backend/src/api/v1/system/system.py` |
| REQ-DOC-001 | `/api/v1/pdf-import/*` | `pdf_import` 组合路由 | `backend/src/api/v1/documents/pdf_import.py` |

---

## 9. 验收场景（建议最小集）

### 9.1 资产
- 场景 A1：创建资产重名拦截。
- 场景 A2：面积不一致拦截（`rented_area > rentable_area`）。
- 场景 A3：资产已关联合同时删除拦截。
- 场景 A4：`include_relations` 开关影响投影字段返回。

### 9.2 认证与权限
- 场景 P1：登录后 Cookie 写入成功。
- 场景 P2：刷新令牌走 Cookie 读取流程。
- 场景 P3：普通用户访问他人权限摘要被拒绝。

### 9.3 租赁
- 场景 R1：创建合同时关联资产不存在应失败。
- 场景 R2：合同生命周期冲突检测触发拒绝。
- 场景 R3：台账批量更新成功并更新欠费状态字段。

### 9.4 推荐执行（后端）
```bash
cd backend
pytest -m unit tests/unit/services/asset/test_asset_service.py -q
pytest -m unit tests/unit/api/v1/test_assets_projection_guard.py -q
pytest -m unit tests/unit/api/v1/test_authentication_layering.py -q
pytest -m unit tests/unit/api/v1/test_roles_permission_grants.py -q
```

评审执行建议：使用 `docs/requirements-review-checklist.md` 进行逐项签字确认与留痕。

---

## 10. vNext 候选需求（未实现）

以下为“已观察到工程迹象但未纳入当前正式基线”的候选项：

1. **错误恢复模块正式化**  
   - 迹象：`error_recovery` 路由在聚合处被临时禁用。
   - 证据：`backend/src/api/v1/__init__.py`

2. **系统设置模块能力稳定化与对外契约固化**  
   - 迹象：`system_settings_router` 为条件导入/条件注册。
   - 证据：`backend/src/api/v1/__init__.py`

3. **PDF 批量导入能力从“可选加载”提升为“必选能力”**  
   - 迹象：批量路由当前通过可导入性判断注册。
   - 证据：`backend/src/api/v1/__init__.py`

---

## 11. 变更规则

- 新增/修改业务能力时，必须同步更新本 SRS 与附录。
- 需求变更必须携带至少一个代码证据路径与一个验收场景。
- 如与历史 PRD 冲突，以本 SRS 与当前代码行为为准。
