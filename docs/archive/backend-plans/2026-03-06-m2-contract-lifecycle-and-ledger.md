# M2 技术方案：合同组生命周期、审核闭环与台账自动化

> **状态**：🔄 待执行  
> **目标里程碑**：M2（2026-04-01 ~ 2026-05-10）  
> **涉及需求**：REQ-RNT-002 / REQ-RNT-003 / REQ-RNT-004 / REQ-RNT-005 / REQ-RNT-006 / REQ-PRJ-002（合同组双入口）  
> **前置依赖**：REQ-RNT-001 ✅（五层合同模型 `contracts` / `contract_groups` / `lease_contract_details` / `agency_agreement_details` / `contract_relations` 已落地）

---

## 1. 现状诊断

### 1.1 M1 遗产（已完成）

| 层级 | 文件 | 覆盖内容 |
|------|------|----------|
| ORM | `models/contract_group.py` | ContractGroup、Contract、LeaseContractDetail、AgencyAgreementDetail、ContractRelation；ContractLifecycleStatus / ContractReviewStatus 枚举已定义 |
| Schema | `schemas/contract_group.py` | 创建/更新/响应 Schema |
| CRUD | `crud/contract_group.py` | 基础 CRUD（179 行） |
| Service | `services/rent_contract/contract_group_service.py` | create / update / list / soft_delete / add_contract_to_group；revenue_mode ↔ group_relation_type 一致性校验 |
| API | `api/v1/rent_contracts/contract_groups.py` | CRUD 端点（382 行） |
| 测试 | `tests/unit/services/rent_contract/test_contract_group_service.py` | 合同组 Service 单测 |

### 1.2 M2 缺口（需新建 / 扩展）

1. **生命周期状态机 API** —— `lifecycle.py` / `contract_groups.py` 缺提交审核、审核通过/驳回、到期标记、终止接口（新模型版本）。
2. **ContractAuditLog 表** —— 无审计日志表，所有状态流转无留痕。
3. **ContractLedgerEntry 表** —— 旧 `rent_ledger` 挂在 `rent_contracts`；新架构下台账需挂 `contracts.contract_id`（附录 §11.2）。
4. **反审核纠错闭环** —— 无 void（作废）接口，无台账存在时的防护守门 。
5. **前端合同组管理页面** —— 无 ContractGroupListPage / ContractGroupDetailPage / ContractGroupFormPage。
6. **合同组双入口** —— 资产详情页、项目详情页缺合同组跳转链接。

---

## 2. 架构决策

### AD-1：审核在合同级进行（确认附录 §11.1）

ContractGroup 为纯容器 + 派生状态，不额外新增 group_review_status 字段。合同组批量提审 = Service 层将组内所有草稿合同原子性提交为待审，不做联审（不区分关键变更/文本变更，不建联审批次表）。

### AD-2：反审核 = 作废 + 重建（不回退状态）

- 无台账：直接 void（标记 `data_status = 已作废`）
- 有台账：拒绝直接 void，必须先冲销台账条目再 void + 重建。
- 体现为两个互斥 API：`void`（无台账快路径）、`void-with-ledger-cancel`（有台账路径，M2 仅实现校验拦截，冲销台账留 M3）。

### AD-3：台账生成触发时机（附录 §11.2 冻结）

- 合同 `status` 从 `PENDING_REVIEW` → `ACTIVE` 时，在同一事务内生成月度台账条目。
- **生成依据：`ContractRentTerm`（分阶段租金条款子表，FK → `contracts.contract_id`）**——附录 §3.5 脚注已冻结"RentTerm 为独立子表 FK → Contract 基表"，附录 §11.2 已冻结"按 RentTerm 生成月度台账"；`monthly_rent_base` 仅作合同汇总展示字段，不再作为台账生成口径。
- M2 在 T1 阶段新建 `contract_rent_terms` 表（ORM `ContractRentTerm`，FK → `contracts.contract_id`），与旧 `rent_terms`（挂旧 `rent_contracts`）相互独立，不迁移旧数据。
- 代理协议（`AgencyAgreementDetail`）不生成 RentLedger，ServiceFeeLedger 留 M3 实现。

### AD-4：旧合同域全量下线（AGENTS.md "0→1 不做兼容" + 附录 §10 口径）

M2 迁移阶段物理删除旧合同域所有表和代码，不做兼容保留，不迁移数据（测试数据可直接删除）：

**数据库 DROP（Alembic 迁移）**：`rent_contracts`、`rent_terms`、`rent_ledger`、`rent_deposit_ledger`、`service_fee_ledger`

**代码删除**：
- `backend/src/models/rent_contract.py`（含 RentContract / RentTerm / RentLedger / RentDepositLedger / ServiceFeeLedger ORM 类）
- `backend/src/crud/rent_contract.py`（若独立存在）
- `backend/src/services/rent_contract/service.py`（旧合同 Service，与新 contract_group_service 区分）
- `backend/src/api/v1/rent_contracts/lifecycle.py`（旧生命周期 API：renew_contract / terminate_contract，均操作旧模型）
- 对应测试文件

**新台账表**：`contract_ledger_entries`（ORM 类 `ContractLedgerEntry`），挂 FK `contracts.contract_id`，完全取代旧 `rent_ledger`。

---

## 3. 任务拆分（≤10 文件/任务）

M2 分 4 个子任务顺序交付，相邻任务之间存在 schema/model 依赖，不可并行。

---

### M2-T1：ContractAuditLog 模型 + 合同生命周期状态机

**目标**：在新 `contracts` 模型上实现完整状态 DRAFT→PENDING_REVIEW→ACTIVE→EXPIRED/TERMINATED，并全程留审计。

#### 3.1.1 新增 ContractAuditLog 模型

```python
# 追加到 models/contract_group.py
class ContractAuditLog(Base):
    __tablename__ = "contract_audit_logs"

    log_id: str (PK, uuid)
    contract_id: str (FK → contracts)
    action: str           # submit_review / approve / reject / expire / terminate / void
    old_status: str | None
    new_status: str | None
    review_status_old: str | None
    review_status_new: str | None
    reason: str | None    # 必填于 reject / void / terminate
    operator_id: str | None
    operator_name: str | None
    related_entry_id: str | None  # 关联单号（附录 REQ-RNT-005 "全流程强制留痕"要求，冲销台账时填写）
    created_at: datetime
```

#### 3.1.2 状态转换规则（Service 层强制）

| 动作 | 前置状态 | 后置状态 | review_status 变化 | 附加条件 |
|------|----------|----------|-------------------|----------|
| `submit_review` | DRAFT | PENDING_REVIEW | DRAFT→PENDING | `sign_date` 不能为空 |
| `approve` | PENDING_REVIEW | ACTIVE | PENDING→APPROVED | 触发台账生成（M2-T2 后） |
| `reject` | PENDING_REVIEW | DRAFT | PENDING→DRAFT | `reason` 必填 |
| `expire` | ACTIVE | EXPIRED | 不变 | 手动或定时触发 |
| `terminate` | ACTIVE / EXPIRED | TERMINATED | 不变 | `reason` 必填 |
| `void` | 任意非 ACTIVE | data_status=已作废 | — | 无台账时允许；有台账拒绝。**注：ACTIVE 合同必须先 terminate 再 void，即使无台账也不允许直接 void ACTIVE 合同（业务承诺不可跳过终止流程）。** |

#### 3.1.3 合同组批量提审 API

```
POST /api/v1/contract-groups/{group_id}/submit-review
```
Service 逻辑：遍历组内 DRAFT 合同，逐一执行 `submit_review`。任一失败则回滚全组（原子操作）。

#### 3.1.4 文件清单（≤10 文件新增 + 删除旧文件）

| # | 文件 | 操作 |
|---|------|------|
| 1 | `backend/src/models/contract_group.py` | 追加 ContractAuditLog 类 + ContractRentTerm 类 |
| 2 | `backend/alembic/versions/YYYYMMDD_m2_drop_old_rent_tables.py` | 新建迁移（DROP 旧表，逆 FK 顺序） |
| 3 | `backend/alembic/versions/YYYYMMDD_m2_contract_audit_log.py` | 新建迁移（`contract_audit_logs` 表） |
| 4 | `backend/alembic/versions/YYYYMMDD_m2_contract_rent_terms.py` | 新建迁移（`contract_rent_terms` 表，FK → `contracts.contract_id`） |
| 5 | `backend/src/schemas/contract_group.py` | 追加 ContractLifecycleAction / AuditLogResponse / ContractRentTermCreate / ContractRentTermResponse Schema |
| 6 | `backend/src/crud/contract_group.py` | 追加 `create_audit_log` / `get_audit_logs` / `create_rent_term` / `get_rent_terms_by_contract` |
| 7 | `backend/src/services/rent_contract/contract_group_service.py` | 追加 `submit_review` / `approve` / `reject` / `expire` / `terminate_contract_v2` / `void_contract` |
| 8 | `backend/src/api/v1/rent_contracts/contract_groups.py` | 追加 lifecycle 路由（submit-review / approve / reject / expire / terminate / void）+ RentTerm CRUD 路由 |
| 9 | `backend/tests/unit/services/rent_contract/test_lifecycle_v2.py` | 新建单测（每种状态转换 + 守门条件） |
| 10 | `backend/tests/unit/api/v1/test_contract_lifecycle_api.py` | 新建 API 分层测试 |
| 11 | `backend/tests/unit/services/rent_contract/test_rent_term_crud.py` | 新建 ContractRentTerm 增删改查测试 |
| D1 | `backend/src/models/rent_contract.py` | **删除**（RentContract / RentTerm / RentLedger 等旧 ORM） |
| D2 | `backend/src/api/v1/rent_contracts/lifecycle.py` | **删除**（旧 renew_contract / terminate_contract，操作旧模型） |
| D3 | `backend/src/services/rent_contract/service.py` | **删除**（旧合同 Service，确认无新代码依赖后删除） |
| D4 | 旧合同域对应测试文件 | **删除**（随旧代码一并清除） |

#### 3.1.5 验收条件

- 非法状态转换 → `OperationNotAllowedError`（HTTP 422）。
- `reject` / `terminate` / `void` 缺 `reason` → `BusinessValidationError`（HTTP 400）。
- `submit_review` 时 `sign_date` 为空 → HTTP 400。
- 每次成功转换写入 `contract_audit_logs` 一条记录。
- `void` 有台账时 → HTTP 422，消息明确说明需要先冲销台账。
- `POST /contract-groups/{id}/submit-review` 组内多合同原子提交。

#### 3.1.6 新增 ContractRentTerm 模型（附录 §3.5 冻结要求）

```python
# 追加到 models/contract_group.py
class ContractRentTerm(Base):
    __tablename__ = "contract_rent_terms"

    rent_term_id: str          # PK, uuid
    contract_id: str           # FK → contracts.contract_id（新模型，非旧 rent_contracts）
    sort_order: int            # 条款排序，从 1 开始
    start_date: date           # 本阶段开始日
    end_date: date             # 本阶段结束日
    monthly_rent: Decimal      # 本阶段月租金
    management_fee: Decimal    # 管理费，>=0，默认 0
    other_fees: Decimal        # 其他费用，>=0，默认 0
    total_monthly_amount: Decimal | None  # 派生：monthly_rent + management_fee + other_fees
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

唯一约束：`(contract_id, sort_order)`。台账生成时按 `sort_order` 升序遍历，每阶段覆盖 `[start_date, end_date]` 内的自然月。

---

### M2-T2：ContractLedgerEntry 表 + 台账自动化

**目标**：合同激活时自动生成月度台账；提供查询 API。

#### 3.2.1 新增 ContractLedgerEntry 模型

```python
# 追加到 models/contract_group.py
class ContractLedgerEntry(Base):
    __tablename__ = "contract_ledger_entries"

    entry_id: str (PK, uuid)
    contract_id: str (FK → contracts)
    year_month: str          # "YYYY-MM" 格式，唯一键：(contract_id, year_month)
    due_date: date           # 应付/应收日（按 payment_cycle 计算）
    amount_due: Decimal      # 应付金额（含税或不含税，按 is_tax_included 口径）
    currency_code: str       # 固定 CNY（MVP）
    is_tax_included: bool
    tax_rate: Decimal | None
    payment_status: str      # unpaid / paid / overdue / partial
    paid_amount: Decimal     # 实收金额，默认 0
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

唯一约束：`(contract_id, year_month)` 防重复生成。

#### 3.2.2 生成逻辑（Service 层）

```python
# services/rent_contract/ledger_service_v2.py
async def generate_ledger_on_activation(db, contract_id: str) -> list[ContractLedgerEntry]:
    """
    合同激活时调用（在 approve() 内事务内调用）。
    1. 读取 Contract + LeaseContractDetail（获取 payment_cycle 用于 due_date 计算）
    2. 读取 ContractRentTerm 列表（按 sort_order 升序）
    3. 无 ContractRentTerm 记录则跳过生成（记录警告日志，不报错）
    4. 遍历各 RentTerm 阶段，按自然月展开覆盖范围，生成月度条目
    5. 金额来源：ContractRentTerm.total_monthly_amount（附录 §11.2 冻结）
    6. due_date = 每月应付日（按 LeaseContractDetail.payment_cycle 规则计算：月付=次月N日、季付=季初等）
    7. 幂等：year_month 已存在则跳过
    """
```

#### 3.2.3 文件清单（≤8 文件）

| # | 文件 | 操作 |
|---|------|------|
| 1 | `backend/src/models/contract_group.py` | 追加 ContractLedgerEntry 类 |
| 2 | `backend/alembic/versions/YYYYMMDD_m2_contract_ledger_entries.py` | 新建迁移（`contract_ledger_entries` 表） |
| 3 | `backend/src/schemas/contract_group.py` | 追加 ContractLedgerEntryResponse / LedgerQueryParams |
| 4 | `backend/src/crud/contract_group.py` | 追加 `create_ledger_entry` / `get_ledger_by_contract` / `get_existing_year_months` / `batch_update_payment_status` |
| 5 | `backend/src/services/rent_contract/ledger_service_v2.py` | 新建：`generate_ledger_on_activation` / `query_ledger` / `batch_update_status` |
| 6 | `backend/src/api/v1/rent_contracts/ledger_v2.py` | 新建：`GET /contracts/{id}/ledger` / `PATCH /contracts/{id}/ledger/batch-update-status`；通过 `route_registry.register_router(router, prefix="/api/v1", tags=["ledger"])` 注册，路径前缀 `/api/v1/contracts/{contract_id}/` |
| 7 | `backend/tests/unit/services/rent_contract/test_ledger_service_v2.py` | 新建单测（生成逻辑、幂等性、金额计算） |
| 8 | `backend/tests/unit/api/v1/test_ledger_v2_api.py` | 新建 API 分层测试 |

> 注：同时在 M2-T1 的 `approve()` 内调用 `generate_ledger_on_activation()`，需更新 `contract_group_service.py`（或 M2-T1 末尾预留调用点）。

#### 3.2.4 验收条件

- 合同激活（approve）→ 自动生成 `[effective_from, effective_to]` 全生命周期月度台账条目。
- 幂等：重复调用 approve 不重复生成。
- `GET /contracts/{id}/ledger` 支持 `year_month_start` / `year_month_end` 分页筛选。
- `PATCH /contracts/{id}/ledger/batch-update-status` 正确更新 `payment_status` + `paid_amount`。
- 代理协议合同（`AgencyAgreementDetail`，无 `monthly_rent_base`）激活时台账生成跳过，不报错。

---

### M2-T3：前端合同组管理页面

**目标**：ContractGroupListPage + ContractGroupDetailPage + ContractGroupFormPage + 配套 service/types/routes。

#### 3.3.1 文件清单（≤9 文件）

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `frontend/src/types/contractGroup.ts` | 新建 | ContractGroup / Contract / ContractLedgerEntry TS 类型（对齐后端 Schema） |
| 2 | `frontend/src/services/contractGroupService.ts` | 新建 | API 调用层（React Query hooks 封装） |
| 3 | `frontend/src/pages/Rental/ContractGroupListPage.tsx` | 新建 | 合同组列表页（筛选/分页/状态标签+跳转详情） |
| 4 | `frontend/src/pages/Rental/ContractGroupDetailPage.tsx` | 新建 | 合同组详情页（组信息卡片 + 组内合同列表 + 派生状态 + 审核操作入口） |
| 5 | `frontend/src/pages/Rental/ContractGroupFormPage.tsx` | 新建 | 创建/编辑合同组表单页（revenue_mode 选择、主体选择、有效期、结算规则） |
| 6 | `frontend/src/routes/AppRoutes.tsx` | 修改 | 新增 `/contract-groups`、`/contract-groups/:id`、`/contract-groups/new`、`/contract-groups/:id/edit` 路由 |
| 7 | `frontend/src/constants/routes.ts` | 修改 | 追加合同组路由常量 |
| 8 | `frontend/src/pages/Rental/__tests__/ContractGroupDetailPage.test.tsx` | 新建 | 渲染测试 |
| 9 | `frontend/src/pages/Rental/__tests__/ContractGroupListPage.test.tsx` | 新建 | 列表 + 筛选测试 |

#### 3.3.2 ContractGroupDetailPage 关键交互

- 顶部：合同组编码、经营模式标签（承租/代理）、派生状态徽标、主体信息。
- 合同列表：按 `group_relation_type` 分组展示（上游/下游 或 委托/直租）。
- 合同状态徽标：草稿 / 待审 / 生效 / 已到期 / 已终止。
- 操作按钮（按权限显示）：提交审核 / 审核通过 / 驳回 / 终止 / 查看台账。
- **代理模式**合同组顶部展示警告标签"代理口径，非自营出租"（REQ-RNT-002 要求）。

---

### M2-T4：合同组双入口 + 审核流 UI

**目标**：资产详情页 / 项目详情页挂合同组入口；实现合同级审核流操作面板（REQ-PRJ-002 + REQ-RNT-004）。

#### 3.4.1 文件清单（≤7 文件）

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `frontend/src/pages/Assets/AssetDetailPage.tsx` | 修改 | 新增"关联合同组"卡片：按资产 ID 查询合同组列表，点击跳转 ContractGroupDetailPage |
| 2 | `frontend/src/pages/Project/ProjectDetailPage.tsx` | 修改 | 新增"项目合同组"卡片：通过项目资产 ID 汇总合同组，点击跳转 |
| 3 | `frontend/src/components/ContractGroup/ReviewPanel.tsx` | 新建 | 审核操作面板（提交审核 / 审核通过 / 驳回 / 作废，含 reason 输入框） |
| 4 | `frontend/src/components/ContractGroup/AuditLogTable.tsx` | 新建 | 审计日志表格（按 contract_id 查询 ContractAuditLog） |
| 5 | `frontend/src/services/contractGroupService.ts` | 修改 | 追加生命周期操作 API（submit / approve / reject / void） |
| 6 | `frontend/src/pages/Rental/__tests__/ReviewPanel.test.tsx` | 新建 | ReviewPanel 交互测试 |
| 7 | `frontend/src/pages/Assets/__tests__/AssetDetailPage.contractgroup.test.tsx` | 新建 | 资产详情页合同组卡片测试 |

#### 3.4.2 双入口路由策略

- 资产详情 `GET /api/v1/contract-groups?asset_id={id}` → 列表（后端 M2-T1 阶段在 `list_groups()` 追加 `asset_id` 筛选参数）。
- 项目详情 → 先获取项目下资产列表，再按 asset_id 批量查询合同组（或后端新增 `GET /api/v1/contract-groups?project_id={id}` 聚合接口）。

---

## 4. 依赖与执行顺序

```
M2-T1（ContractAuditLog + 状态机 API）
  ↓
M2-T2（ContractLedgerEntry + 台账自动化）  ← 依赖 T1 approve() 钩子
  ↓
M2-T3（前端合同组管理页面）               ← 依赖 T1/T2 API 就绪
  ↓
M2-T4（双入口 + 审核 UI）                 ← 依赖 T3 基础组件 + T1 生命周期 API
```

---

## 5. Alembic 迁移策略

两次迁移分步进行（每任务独立迁移，便于回滚）：

| 迁移文件 | 内容 |
|---------|------|
| `YYYYMMDD_m2_drop_old_rent_tables.py` | **DROP** `service_fee_ledger` → `rent_deposit_ledger` → `rent_ledger` → `rent_terms` → `rent_contracts`（按 FK 依赖逆序删除） |
| `YYYYMMDD_m2_contract_audit_log.py` | 新建 `contract_audit_logs` 表 |
| `YYYYMMDD_m2_contract_rent_terms.py` | 新建 `contract_rent_terms` 表（FK → `contracts.contract_id`）+ `(contract_id, sort_order)` 唯一索引 |
| `YYYYMMDD_m2_contract_ledger_entries.py` | 新建 `contract_ledger_entries` 表 + `(contract_id, year_month)` 唯一索引 |

> ⚠️ DROP 迁移执行前须确认测试库无需保留旧数据（口径：测试数据可删，附录 §10）。

---

## 6. 需求追踪矩阵更新（M2 完成后目标状态）

| 需求ID | M2 前 | M2 后目标 | 关键证据 |
|--------|-------|-----------|----------|
| REQ-RNT-002 | 📋 | ✅ | ContractGroupDetailPage 代理标签 + 模式一致性校验测试 |
| REQ-RNT-003 | 🚧 | ✅ | contract_group_service lifecycle 方法 + API endpoints + ContractAuditLog |
| REQ-RNT-004 | 📋 | ✅ | `POST /contract-groups/{id}/submit-review` 批量提审 + 合同级 approve/reject + ReviewPanel UI |
| REQ-RNT-005 | 📋 | ✅ | void_contract 守门 + ContractAuditLog 留痕 |
| REQ-RNT-006 | 🚧 | ✅ | ContractLedgerEntry 自动生成 + ledger_service_v2 + ledger_v2 API |
| REQ-PRJ-002 | ✅（有效资产） | ✅（合同组双入口） | ProjectDetailPage 合同组卡片 + AssetDetailPage 合同组链接 |

---

## 7. 边界条件与风险

| 风险 | 缓解措施 |
|------|---------|
| `contract_rent_terms` 无记录时台账生成行为 | 允许提交审核，生成台账时跳过并写入警告日志；前端提示录入人员补录 RentTerm |
| 批量提审时部分合同 `sign_date` 缺失 | 批量提审 Service 收集所有失败原因，一次性返回（不逐条短路） |
| AgencyAgreementDetail 合同激活台账策略不明 | M2 跳过代理协议台账生成（不报错），ServiceFeeLedger 留 M3 |
| 前端合同组表单中 `settlement_rule` 结构化字段复杂 | MVP 允许 JSON 文本输入，M3 升级为结构化表单 |
| DROP 旧表时外部 API 仍引用旧模型 | M2-T1 先删旧代码，make check 暴露所有断点后再执行 DROP 迁移 |

---

## 8. 测试用例建议

### 后端单测重点

| # | 用例 | 期望 |
|---|------|------|
| T-01 | DRAFT → PENDING_REVIEW，`sign_date` 为 null | HTTP 400 |
| T-02 | DRAFT → PENDING_REVIEW，`sign_date` 有值 | 成功，ContractAuditLog 写入 1 条 |
| T-03 | PENDING_REVIEW → ACTIVE（approve），合同有 N 个 RentTerm 阶段 | 台账条目数 = 各 RentTerm 阶段覆盖自然月数之和 |
| T-04 | PENDING_REVIEW → ACTIVE 重复调用 | 幂等，台账不重复生成 |
| T-05 | reject 不填 reason | HTTP 400 |
| T-06 | void，无台账 | 成功，data_status = 已作废 |
| T-07 | void，有台账 | HTTP 422，提示需先冲销 |
| T-08 | 合同组主审（submit-review），组内有非 DRAFT 合同（PENDING_REVIEW / ACTIVE / EXPIRED / TERMINATED） | 仅提交 DRAFT 合同，其余状态全部跳过 |
| T-09 | revenue_mode=lease，group_relation_type=委托 | HTTP 422，不兼容 |
| T-10 | 台账生成，`contract_rent_terms` 无记录 | 跳过生成，无报错，写入警告日志 |

### 前端测试重点

| # | 用例 | 期望 |
|---|------|------|
| F-01 | ContractGroupListPage，无数据 | 展示空状态 |
| F-02 | ContractGroupDetailPage，agency 模式 | 展示"代理口径"警告标签 |
| F-03 | ReviewPanel，点击"驳回"未填 reason | 按钮禁用或 inline 错误提示 |
| F-04 | AssetDetailPage，无关联合同组 | 展示空状态卡片 |

---

## 9. CHANGELOG 计划条目（M2 完成后追加）

```markdown
## [M2] 2026-04-xx

### Added
- REQ-RNT-003: Contract 生命周期状态机（submit/approve/reject/expire/terminate/void）+ ContractAuditLog 审计日志
- REQ-RNT-004: 合同组批量提审 POST /contract-groups/{id}/submit-review + 合同级 approve/reject
- REQ-RNT-005: void_contract 守门（有台账时拒绝直接 void）
- REQ-RNT-006: ContractRentTerm 子表 + ContractLedgerEntry 自动生成（合同激活触发）+ ledger_v2 查询/批量更新 API
- REQ-RNT-002: ContractGroupDetailPage 代理口径标签
- REQ-PRJ-002: 合同组双入口（资产详情 + 项目详情 → ContractGroupDetailPage）
- 前端：ContractGroupListPage / ContractGroupDetailPage / ContractGroupFormPage
- 前端：ReviewPanel + AuditLogTable 组件

### Removed
- 旧合同域全量下线：DROP `rent_contracts` / `rent_terms` / `rent_ledger` / `rent_deposit_ledger` / `service_fee_ledger` 表
- 删除 `models/rent_contract.py` / `services/rent_contract/service.py`（旧）/ `api/v1/rent_contracts/lifecycle.py`（旧）及关联测试
```
