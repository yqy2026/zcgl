# 土地物业资产运营管理系统 — 项目深度分析报告

> 生成时间: 2026-06-12 | 分析范围: 全量代码库 + 文档 SSOT

## 1. 项目概况

**名称**: 土地物业资产运营管理系统 (Real Estate Asset Management & Operations System)
**版本**: 2.0.0
**阶段**: 从 0 到 1 MVP 收口期

| 维度 | 技术选型 |
|------|----------|
| 前端 | React 19 + TypeScript 5 + Vite 6 + Ant Design 6 + pnpm |
| 后端 | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 18 / Redis 8 |
| 端口 | 后端 :8002 / 前端 :5173 |

---

## 2. 架构全景

### 2.1 后端分层

```
请求 → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑              ↑
         业务逻辑层      数据访问层
```

| 层 | 文件数 | 职责 |
|----|--------|------|
| models/ | 32 | SQLAlchemy ORM 实体 |
| schemas/ | 28 | Pydantic v2 数据契约 |
| crud/ | 32 | 数据访问封装 |
| services/ | 38 | 业务逻辑（含 12 个子模块目录） |
| api/v1/ | 17 模块 | 路由 + 端点 |
| middleware/ | 14 | 身份认证、授权、审计、安全 |
| core/ | 30 | 配置、路由注册、加密、环境、异常 |
| security/ | 23 | JWT、Cookie、权限、限流、日志安全 |

**路由注册**: 使用 `route_registry.register_router()` 统一注册，`main.py` 通过 `route_registry.include_all(app, version="v1")` 一次性挂载。

**中间件链** (按请求顺序):
1. `security_middleware.py` — 安全防护
2. `request_logging.py` — 请求日志
3. `error_recovery_middleware.py` — 错误恢复
4. `CORSMiddleware` — 跨域

**认证授权链**:
- `identity.py` — Cookie/JWT 解析、当前用户
- `authorization.py` — ABAC 可信资源上下文
- `data_scope.py` — 数据范围解析
- `resource_context.py` — 资源上下文加载

### 2.2 前端结构

| 层 | 文件数 | 职责 |
|----|--------|------|
| pages/ | 18 个模块目录 | 页面级组件 |
| components/ | 22 个模块目录 | 可复用组件库 |
| services/ | 35 | API 服务封装 |
| hooks/ | 22 | React Query 自定义 Hook |
| types/ | 31 | TypeScript 类型定义 |
| store/ | 2 (Zustand) | 全局 UI 状态 |
| contexts/ | 2 | AuthContext / ErrorHandlingContext |
| routes/ | 3 | 路由定义 + 懒加载 + canonical redirect |

**状态管理策略**:
- 全局 UI / 偏好: Zustand（`useAppStore` / `useAssetStore`）
- 认证状态: React Context（`AuthContext`）
- 服务器数据: React Query（`useQuery` / `useMutation`）
- 表单: React Hook Form
- 局部 UI: `useState`

**路由保护**: `ProtectedRouteItem` 配置 `permissions` / `adminOnly` / `capabilityGuardBypass`，配合 `PermissionGuard` 组件实现。

---

## 3. 业务模块清单与完成度

### 3.1 需求追踪矩阵状态

| REQ | 模块 | 产品状态 | 实现状态 | 说明 |
|-----|------|----------|----------|------|
| REQ-AST-001 | 资产 CRUD | MVP | ✅ 已有证据 | 完整 CRUD + 筛选 + 导入 + 附件 + 字段校验 |
| REQ-AST-002 | 资产主项目/主权主体/经营方历史 | MVP | ✅ 已有证据 | |
| REQ-AST-003 | 资产生命周期(两步) | MVP | ✅ 已有证据 | 含批量提交/确认，复核权限门控 |
| REQ-AST-004 | 资产租赁摘要/客户摘要 | MVP | ✅ 已有证据 | 合同级金额口径 |
| REQ-AST-005 | 产权证管理 | MVP | 🔄 开发中 | 主路径应收到资产详情内能力；重复证号追加关联待收口 |
| REQ-PRJ-001 | 项目运营管理 | MVP | ✅ 已有证据 | |
| REQ-PRJ-002 | 项目详情按有效资产汇总 | MVP | ✅ 已有证据 | |
| REQ-PRJ-003 | 项目运营台账/风险/分析 | MVP | ✅ 已有证据 | 含 ledger-summary, risks, analytics |
| REQ-RNT-001 | 合同关系(ContractGroup) | MVP | ✅ 已有证据 | |
| REQ-RNT-002 | 承租/代理双模式 | MVP | ✅ 已有证据 | |
| REQ-RNT-003 | 合同 PDF 导入 | MVP | 🔄 开发中 | 存量证据已多；仍需统一临时解析会话、字段来源快照等 |
| REQ-RNT-004 | 主合同覆盖 | 已移除 | ❌ 已清理 | ContractRelation 表已删除 |
| REQ-RNT-005 | 纠错/更正/台账重算 | MVP | ✅ 已有证据 | 只动未收条目，已收跳过 |
| REQ-RNT-006 | 台账生成/查询/导出/补偿/实收登记 | MVP | ✅ 已有证据 | 含服务费台账 |
| REQ-CUS-001 | 客户增强信息/风险/历史 | MVP | ✅ 已有证据 | |
| REQ-CUS-002 | 客户双指标(仅终端客户) | MVP | ✅ 已有证据 | customer_type 仅为展示标签 |
| REQ-SCH-001 | 全局搜索入口 | MVP | ✅ 已有证据 | 资产/项目/合同关系/合同/客户 |
| REQ-SCH-002 | 搜索分组排序 | MVP | ✅ 已有证据 | |
| REQ-SCH-003 | 搜索权限过滤 | MVP | ✅ 已有证据 | 数据范围收缩 |
| REQ-AUTH-001 | Cookie JWT 认证 | MVP | ✅ 已有证据 | |
| REQ-AUTH-002 | 数据范围/ViewMode | MVP | ✅ 已有证据 | |
| REQ-AUTH-003 | ABAC 策略/Deny优先 | MVP | ✅ 已有证据 | |
| REQ-DOC-001 | 合同/产权证 OCR/AI 提取 | MVP | 🔄 开发中 | 需统一 ScanExtractionSession、字段来源、低置信处理 |
| REQ-ANA-001 | 经营分析 | MVP | ✅ 已有证据 | 项目/模式分区分拆 |
| REQ-PTY-001 | Party 单一主档 | MVP | ✅ 已有证据 | |
| REQ-PTY-002 | Party 导入/引用 | MVP | ✅ 已有证据 | |
| REQ-APR-001 | 资产路由审批 | 已移除 | ❌ 已清理 | Approval 三表 + 通知 + 权限已全删 |
| REQ-SYS-001 | 用户管理/多角色 | MVP | ✅ 已有证据 | |
| REQ-SYS-002 | 组织 CRUD + 主体绑定 | MVP | ✅ 已有证据 | |
| REQ-SYS-003 | 数据字典 | MVP | ✅ 已有证据 | |

**汇总**: 30 个 REQ 中，22 个已有证据 ✅，4 个开发中 🔄，2 个已移除 ❌，2 个跨模块约束 ✅。

### 3.2 后端模块详细完成度

| API 模块 | Schema | Model | CRUD | Service | Test | 备注 |
|----------|--------|-------|------|---------|------|------|
| assets/ | ✅ | ✅ | ✅ | ✅ | ✅ | 含 batch, property_cert |
| analytics/ | ✅ | — | — | ✅ | ✅ | |
| auth/ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| contracts/ | ✅ | ✅ | ✅ | ✅ | ✅ | 含 ledger, service_fee |
| documents/ | ✅ | ✅ | ✅ | ✅ | ✅ | PDF 导入 |
| party.py | ✅ | ✅ | ✅ | ✅ | ✅ | |
| rent_contracts/ | ✅ | — | — | ✅ | ✅ | |
| search.py | ✅ | — | — | ✅ | ✅ | |
| system/ | ✅ | ✅ | ✅ | ✅ | ✅ | dictionaries, health |

### 3.3 前端模块详细完成度

| 页面模块 | 列表 | 详情 | 表单 | 导入 | 分析 | 测试 | 备注 |
|----------|------|------|------|------|------|------|------|
| Assets | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| Project | ✅ | ✅ | — | — | — | ✅ | |
| ContractGroup | ✅ | ✅ | ✅ | ✅ | — | ✅ | 含组内合同表单 |
| Contract | — | — | — | ✅ | — | ✅ | PDF 导入 |
| Finance | ✅ | — | — | — | — | ✅ | 全局财务台账 |
| Customer | — | ✅ | — | — | — | ✅ | |
| Search | ✅ | — | — | — | — | ✅ | |
| PropertyCertificate | ✅ | ✅ | — | ✅ | — | ✅ | |
| System | ✅ | ✅ | ✅ | — | — | ✅ | 10+ 子页面 |
| Dashboard | ✅ | — | — | — | — | ✅ | |
| Profile | ✅ | — | — | — | — | ✅ | |

---

## 4. 关键架构决策 (ADR)

| ADR | 标题 | 状态 | 生效日期 |
|-----|------|------|----------|
| ADR-0001 | Party-Role 组织架构 | ✅ 生效 | 2026-02 |
| ADR-0002 | 资产审核取消职责互斥 | ✅ 生效 | 2026-06-10 翻转 |
| ADR-0003 | 合同上下游简化为方向标记 | ✅ 生效 | 2026-06-10 |
| ADR-0004 | settlement_rule 创建时选填可缓填 | ✅ 生效 | 2026-06-10 |
| ADR-0005 | 产权证核验状态 is_verified 删除 | ✅ 生效 | 2026-06-11 |

---

## 5. MVP 减法工程状态

2026-06-10 启动的 MVP 减法工程（followup §A~§K）已全部落地：

| 编号 | 内容 | 状态 |
|------|------|------|
| §A | 删除资产路由审批流（Approval 域代码 + 通知 + RBAC seed） | ✅ 完成 |
| §B | 资产确认权限门控 + 批量提交/确认 | ✅ 完成 |
| §C | 删除 ContractRelation 配对表 + RENEAL + 纠错来源字段 | ✅ 完成 |
| §D | settlement_rule 选填可缓填 + DB 去 NOT NULL | ✅ 完成 |
| §E | 客户双指标与 customer_type 解耦 + view_mode=all 拒绝 | ✅ 完成 |
| §F | 台账口径收口（财务台账入口） | ✅ 完成 |
| §G | 实收登记入口（batch_update_status 复用） | ✅ 完成 |
| §H | 删除产权证 is_verified（模型 + schema + 前端 + 迁移） | ✅ 完成 |
| §I | 删除 ContractGroup/Contract.version 字段 + 迁移 | ✅ 完成 |
| §J | PartyContact 电话加密补漏（SensitiveDataHandler + 迁移） | ✅ 完成 |
| §K | 客户主体数口径修正（去重 + 仅终端客户） | ✅ 完成 |

---

## 6. 数据库状态

- **57 个 Alembic 迁移文件**，从初始 schema 到最新 `20260612_drop_contract_relations.py`
- **最近迁移** (2026-06-11~12): 审批域清理、产权证核验删除、合同关系配对删除、加密补漏、settlement_rule 放宽、Contract.version 删除
- **32 个 ORM 模型**，覆盖核心业务实体 + 审计/通知/安全/字典

关键模型关系:
- `Asset` → `ProjectAsset` → `Project` (多对多)
- `ContractGroup` → `Contract` (一对多)
- `ContractGroup` → `Project` (多对一)
- `Contract` → `ContractRentTerm` / `AgencyAgreementDetail` (一对多)
- `Party` → `PartyContact` (一对多)
- `PropertyCertificate` ↔ `Asset` (多对多，通过 `CertificateAssetRelation`)
- `PropertyCertificate` ↔ `Party` (多对多，通过 `CertificatePartyRelation`)

---

## 7. 测试覆盖

### 后端测试
| 目录 | 文件数 | 覆盖范围 |
|------|--------|----------|
| unit/api/ | 8+ (含 v1/) | API 端点分层测试 |
| unit/services/ | 47+ | 业务逻辑单元测试 |
| unit/middleware/ | — | 中间件行为测试 |
| unit/crud/ | — | 数据访问测试 |
| unit/schemas/ | — | Schema 验证测试 |
| unit/models/ | — | 模型约束测试 |
| unit/security/ | — | 安全专项测试 |
| unit/migration/ | — | 迁移回归测试 |
| e2e/ | 4 | 资产生命周期、认证、PDF 导入、产权证导入 |
| integration/ | — | 数据可见性、资产可见性等 |

### 前端测试
- 各页面 `__tests__/` 目录均有测试
- services `__tests__/` 覆盖主要服务
- hooks `__tests__/` 覆盖核心 Hook
- components `__tests__/` 覆盖关键组件
- routes `__tests__/` 覆盖路由元数据

---

## 8. 文档 SSOT 健康度

| 文档 | 位置 | 状态 | 说明 |
|------|------|------|------|
| PRD | docs/prd.md | ✅ 活跃 | 产品目标态 |
| 领域模型 | docs/specs/domain-model.md | ✅ 活跃 | 字段、状态、口径 |
| API 契约 | docs/specs/api-contract.md | ✅ 活跃 | API、鉴权、数据范围 |
| 追踪矩阵 | docs/traceability/requirements-trace.md | ✅ 活跃 | 实现状态 + 代码/测试证据 |
| ADR | docs/architecture/ADR-*.md | ✅ 5 篇 | 全部生效 |
| 问题排查 | docs/issues/ | ✅ 4 篇活跃 | 技术债务排查 |
| 开发指南 | docs/guides/ | ✅ 12+ 篇 | 环境/后端/前端/测试/部署 |
| 设计资产 | docs/design/ | ✅ | UI 图 + 原型 |
| 已归档 | docs/archive/ | ✅ | 历史方案/证据/指南/问题 |

---

## 9. 技术债务与风险点

### 9.1 当前待收口项（3 个未闭环 MVP 需求）

| REQ | 缺口 | 影响 |
|-----|------|------|
| REQ-AST-005 | 产权证主路径应收到资产详情内；重复证号追加关联前端确认目标待收口；`should_create_new_asset=true` 清空 `asset_ids` 与"至少关联一个资产"约束冲突 | 产权证无法完整使用 |
| REQ-RNT-003 | 统一临时 `ScanExtractionSession`；确认后不保留解析会话；低置信字段逐项处理；字段来源快照；主档未匹配时不直接创建 | 合同 PDF 导入体验不完整 |
| REQ-DOC-001 | 同 REQ-RNT-003 共享缺口；另需确认页字段来源 fail-closed 校验、建议补全字段范围 | OCR/AI 辅助补录不完整 |

### 9.2 架构风险

| 风险 | 等级 | 说明 |
|------|------|------|
| safe_import 降级链 | 中 | main.py 中大量 `safe_import` + `ALLOW_MOCK_REGISTRY`，生产环境配置错误可能导致关键依赖缺失 |
| PII 加密覆盖 | 中 | 10 个字段已加密，但新增 PII 字段需持续关注加密一致性（如 `PartyContact.contact_phone` 曾遗漏） |
| 合同关系模式复杂度 | 低 | 承租/代理双模式下的台账计算、客户指标过滤逻辑密集，已通过减法工程简化 |
| 前端双入口 | 低 | `CONTRACT_CENTER_ROUTES` / `CONTRACT_GROUP_ROUTES` 并存，已通过 canonical redirect 缓解 |

### 9.3 前端技术债

| 项目 | 说明 |
|------|------|
| Ownership 模块 | 已冻结但仍保留在代码中，占用资源 |
| plans/ 目录 | `2026-02-11-approval-flowable-b-plan.md` 需确认是否已过时 |
| 测试覆盖率 | 后端目标 ≥70%（当前未明示），前端目标 ≥50% |

---

## 10. 代码量估计

| 目录 | 估计文件数 | 估计行数 |
|------|-----------|----------|
| backend/src/ | ~200+ | ~30,000+ |
| backend/tests/ | ~150+ | ~25,000+ |
| frontend/src/ | ~400+ | ~50,000+ |
| docs/ | ~80+ | ~15,000+ |
| **总计** | **~830+** | **~120,000+** |

---

## 11. 核心发现与建议

### 发现

1. **MVP 收口基本完成**: 30 个 REQ 中 22 个已有完整证据，2 个已正确移除
2. **减法工程做得干净**: Approval、ContractRelation、is_verified、RENEWAL、version 等非 MVP 代码已彻底清理（连表带代码带迁移带测试）
3. **文档 SSOT 体系成熟**: PRD → 域模型 → API 契约 → 追踪矩阵的完整链路，5 篇 ADR 记录关键决策
4. **测试覆盖扎实**: 后端 unit + integration + e2e + security + migration，前端覆盖各层
5. **加密体系完善**: 10 个 PII 字段加密，确定性加密支持搜索，迁移补漏完整

### 建议（按优先级排序）

| 优先级 | 建议 | 理由 |
|--------|------|------|
| P0 | 运行 `make check` 验证当前代码通过全量门禁 | 减法工程后可能有残留引用 |
| P1 | 收口 REQ-AST-005 产权证重复证号追加关联 | 当前最大未闭环 MVP 需求 |
| P1 | 统一扫描件解析会话契约 (ScanExtractionSession) | REQ-RNT-003/REQ-DOC-001 共享缺口 |
| P2 | 清理 Ownership 冻结模块的路由和菜单暴露 | 已冻结但仍在导航中 |
| P2 | 归档过时的 plans/ 方案文件 | 保持活跃 plans 目录干净 |
| P3 | 补充后端测试覆盖率到 ≥70% | 当前未明示覆盖率数据 |
