# 需求规格附录：模块与接口清单（代码证据版）

## ✅ Status
**当前状态**: Active (2026-02-09)  
**对应主文档**: `docs/requirements-specification.md`

---

## 1. 后端模块与路由聚合清单

> 说明：以下为 `/api/v1` 下当前可观察能力，来源于统一路由聚合器。

| 模块 | 主要前缀/能力 | 路由聚合文件 | 关键实现文件 |
|---|---|---|---|
| 认证 | `/auth/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/auth/auth_modules/authentication.py` |
| 角色权限 | `/roles/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/auth/roles.py` |
| 资产 | `/assets/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/assets/assets.py` |
| 资产批量 | `/assets/batch-*` 等 | `backend/src/api/v1/assets/assets.py` | `backend/src/api/v1/assets/asset_batch.py` |
| 资产导入 | `/assets/import` | `backend/src/api/v1/assets/assets.py` | `backend/src/api/v1/assets/asset_import.py` |
| 资产附件 | `/assets/{id}/attachments/*` | `backend/src/api/v1/assets/assets.py` | `backend/src/api/v1/assets/asset_attachments.py` |
| 项目 | `/projects/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/assets/project.py` |
| 权属方 | `/ownerships/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/assets/ownership.py` |
| 产权证 | `/property-certificates/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/assets/property_certificate.py` |
| 租赁合同 | `/rental-contracts/contracts/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/rent_contracts/contracts.py` |
| 合同生命周期 | `/rental-contracts/contracts/*/(renew|terminate)` | `backend/src/api/v1/rent_contracts/__init__.py` | `backend/src/api/v1/rent_contracts/lifecycle.py` |
| 租金台账 | `/rental-contracts/ledger/*` | `backend/src/api/v1/rent_contracts/__init__.py` | `backend/src/api/v1/rent_contracts/ledger.py` |
| 租赁统计 | `/rental-contracts/statistics/*` | `backend/src/api/v1/rent_contracts/__init__.py` | `backend/src/api/v1/rent_contracts/statistics.py` |
| 综合分析 | `/analytics/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/analytics/analytics.py` |
| 统计报表 | `/statistics/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/analytics/statistics.py` |
| PDF 导入 | `/pdf-import/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/documents/pdf_import.py` |
| PDF 批量 | 批量上传/状态/取消/清理 | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/documents/pdf_batch_routes.py` |
| 系统基础 | `/monitoring/health`, `/system/info`, `/system/root` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/system/system.py` |
| 组织管理 | `/organizations/*` | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/auth/organization.py` |
| 字典/枚举 | `/system/dictionaries/*`, 枚举相关 | `backend/src/api/v1/__init__.py` | `backend/src/api/v1/system/dictionaries.py` |
| 通知/任务/联系人/催缴 | `/notifications/*`, `/tasks/*`, `/contacts/*`, `/collections/*` | `backend/src/api/v1/__init__.py` | 对应 `backend/src/api/v1/system/*.py` |

---

## 2. 前端模块与页面路由清单

| 前端模块 | 路径基线 | 页面入口证据 |
|---|---|---|
| 数据看板 | `/dashboard` | `frontend/src/routes/AppRoutes.tsx` |
| 资产管理 | `/assets/list`, `/assets/new`, `/assets/import`, `/assets/analytics` | `frontend/src/routes/AppRoutes.tsx` |
| 租赁管理 | `/rental/contracts`, `/rental/contracts/pdf-import`, `/rental/ledger`, `/rental/statistics` | `frontend/src/routes/AppRoutes.tsx` |
| 产权证 | `/property-certificates`, `/property-certificates/import` | `frontend/src/routes/AppRoutes.tsx` |
| 权属方 | `/ownership` | `frontend/src/routes/AppRoutes.tsx` |
| 项目管理 | `/project` | `frontend/src/routes/AppRoutes.tsx` |
| 系统管理 | `/system/users`, `/system/roles`, `/system/organizations`, `/system/dictionaries` | `frontend/src/routes/AppRoutes.tsx` |
| 菜单配置 | 一级菜单与业务分组 | `frontend/src/config/menuConfig.tsx` |
| 路由常量 | 路由单一常量源 | `frontend/src/constants/routes.ts` |

---

## 3. 核心数据对象附录

| 实体 | 主要职责 | 关键字段/行为证据 |
|---|---|---|
| `Asset` | 资产核心主实体 | `backend/src/models/asset.py` |
| `Ownership` | 权属方主数据 | `backend/src/models/ownership.py` |
| `Project` | 项目主数据 | `backend/src/models/project.py` |
| `RentContract` | 合同主数据 | `backend/src/models/rent_contract.py` |
| `RentLedger` | 租金台账 | `backend/src/models/rent_contract.py` |
| `PropertyCertificate` | 产权证主数据 | `backend/src/models/property_certificate.py` |
| `PropertyOwner` | 权利人（含 PII） | `backend/src/models/property_certificate.py` |
| `User/Role/Permission` | 认证与 RBAC | `backend/src/models/auth.py`, `backend/src/models/rbac.py` |

---

## 4. 安全与数据保护附录

### 4.1 鉴权与会话
- 后端登录/刷新写 Cookie：`backend/src/api/v1/auth/auth_modules/authentication.py`
- Cookie 配置：`backend/src/security/cookie_manager.py`
- 前端携带 Cookie 请求：`frontend/src/api/client.ts`

### 4.2 敏感字段加密
- 通用字段加密器：`backend/src/core/encryption.py`
- 资产敏感字段处理：`backend/src/crud/asset.py`
- 联系人敏感字段处理：`backend/src/crud/contact.py`
- 权利人敏感字段处理：`backend/src/crud/property_certificate.py`

---

## 5. 分层约束附录

> 要求：路由层仅负责编排，不直接承担业务规则与数据访问细节。

关键守护测试：
- `backend/tests/unit/api/v1/test_project_layering.py`
- `backend/tests/unit/api/v1/test_authentication_layering.py`
- `backend/tests/unit/api/v1/test_assets_ownership_entities_layering.py`

---

## 6. 可执行验收用例索引（建议）

| 能力域 | 推荐测试文件 |
|---|---|
| 资产服务规则 | `backend/tests/unit/services/asset/test_asset_service.py` |
| 资产列表投影 | `backend/tests/unit/api/v1/test_assets_projection_guard.py` |
| 认证分层与流程 | `backend/tests/unit/api/v1/test_authentication_layering.py` |
| 角色权限授权 | `backend/tests/unit/api/v1/test_roles_permission_grants.py` |
| PDF 导入路由 | `backend/tests/unit/api/v1/documents/test_pdf_import_routes.py` |
| 租赁合同 API | `backend/tests/unit/api/v1/test_rent_contract_api.py` |

---

## 7. 附录维护规则

- 新增 API 模块时，必须更新本附录第 1、2 章对应清单。
- 若主 SRS 中新增 `REQ-*`，必须同步补充本附录的证据路径。
- 若模块被废弃，需在本附录显式标注“废弃日期 + 替代能力”。

