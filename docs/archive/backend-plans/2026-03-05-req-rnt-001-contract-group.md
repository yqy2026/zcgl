# REQ-RNT-001 合同组作为主业务对象 — 技术方案

**状态**: 🔄 进行中  
**创建时间**: 2026-03-05  
**需求来源**: `docs/requirements-specification.md` §6.3 REQ-RNT-001  
**字段附录**: `docs/features/requirements-appendix-fields.md` §3.3 – §3.7  

---

## 1. 背景与现状分析

### 1.1 当前模型问题

现行 `RentContract`（`rent_contracts` 表）是一个**扁平化单表模型**，问题：

| 问题 | 具体表现 |
|------|----------|
| 无合同组概念 | 上下游合同靠 `upstream_contract_id` 自关联，无容器聚合 |
| 类型混杂 | 通过 `ContractType` 枚举（`LEASE_UPSTREAM/LEASE_DOWNSTREAM/ENTRUSTED`）区分，语义不清 |
| 代理模式不完整 | 代理模式的"委托"与"直租"无法干净表达，`group_relation_type` 缺失 |
| 字段混用 | `tenant_name`/`owner_name` 等冗余字段混在主表，没有下沉到合同明细 |
| 合同关系语义缺失 | 没有 `ContractRelation` 表，无法干净表达续签/上下游/代理-直租关系 |
| 结算规则无结构 | 没有 `settlement_rule` JSON 结构 |

### 1.2 目标状态

以"合同组（ContractGroup）"为主业务对象，建立五层模型：

```
ContractGroup（交易包）
  └── Contract 基表（N 条）
        ├── LeaseContractDetail（租赁明细，1:1）
        └── AgencyAgreementDetail（代理明细，1:1）
ContractRelation（合同间关系）
```

---

## 2. 数据模型设计

### 2.1 新增表总览

| 表名 | ORM 类 | 说明 |
|------|--------|------|
| `contract_groups` | `ContractGroup` | 合同组主表（交易包容器） |
| `contract_group_assets` | 关联表 | 合同组-资产 M2M |
| `contracts` | `Contract` | 合同基表（替代旧 `rent_contracts` 中的合同概念） |
| `contract_assets` | 关联表 | 合同-资产 M2M |
| `lease_contract_details` | `LeaseContractDetail` | 租赁合同明细（1:1 → contracts） |
| `agency_agreement_details` | `AgencyAgreementDetail` | 代理协议明细（1:1 → contracts） |
| `contract_relations` | `ContractRelation` | 合同间关系 |

### 2.2 `contract_groups` 表

```sql
CREATE TABLE contract_groups (
    contract_group_id  VARCHAR PRIMARY KEY,
    group_code         VARCHAR(50) UNIQUE NOT NULL,  -- GRP-[A-Z0-9]{4,12}-[0-9]{6}
    revenue_mode       VARCHAR(20) NOT NULL,         -- lease / agency
    operator_party_id  VARCHAR NOT NULL REFERENCES parties(id),
    owner_party_id     VARCHAR NOT NULL REFERENCES parties(id),
    effective_from     DATE NOT NULL,
    effective_to       DATE,                         -- 手动设定 or 按组内合同派生
    settlement_rule    JSONB NOT NULL,               -- 必填见下
    revenue_attribution_rule  JSONB,
    revenue_share_rule         JSONB,
    risk_tags          TEXT[],
    predecessor_group_id  VARCHAR REFERENCES contract_groups(contract_group_id),
    data_status        VARCHAR(20) NOT NULL DEFAULT '正常',
    version            INTEGER NOT NULL DEFAULT 1,
    created_at         TIMESTAMP NOT NULL,
    updated_at         TIMESTAMP NOT NULL,
    created_by         VARCHAR(100),
    updated_by         VARCHAR(100)
);
```

`settlement_rule` 最小必填键（JSON Schema）：
```json
{
  "version": "string (必填)",
  "cycle": "月付|季付|半年付|年付 (必填)",
  "settlement_mode": "string (必填)",
  "amount_rule": "object (必填)",
  "payment_rule": "object (必填)"
}
```

派生字段（不写库，由 Service 层计算）：
- `derived_status`：`筹备中 / 生效中 / 已结束`  
- `upstream_contract_ids` / `downstream_contract_ids`：由 `ContractRelation` 聚合  

**派生状态规则**（`docs/features/requirements-appendix-fields.md §8.1`）：

| 条件 | 派生状态 |
|------|----------|
| 组内无任何合同处于 `生效` 或 `待审` | `筹备中` |
| 组内至少一条合同处于 `生效` | `生效中` |
| 组内所有合同均为 `已到期` 或 `已终止` | `已结束` |

### 2.3 `contracts` 表（合同基表）

```sql
CREATE TABLE contracts (
    contract_id        VARCHAR PRIMARY KEY,
    contract_group_id  VARCHAR NOT NULL REFERENCES contract_groups(contract_group_id),
    contract_direction VARCHAR(10) NOT NULL,   -- 出租 / 承租
    group_relation_type VARCHAR(10) NOT NULL,  -- 上游 / 下游 / 委托 / 直租
    lessor_party_id    VARCHAR NOT NULL REFERENCES parties(id),
    lessee_party_id    VARCHAR NOT NULL REFERENCES parties(id),
    sign_date          DATE,                   -- 草稿可空
    effective_from     DATE NOT NULL,
    effective_to       DATE,
    currency_code      VARCHAR(10) NOT NULL DEFAULT 'CNY',
    tax_rate           NUMERIC(5,4),
    is_tax_included    BOOLEAN NOT NULL DEFAULT TRUE,
    status             VARCHAR(20) NOT NULL DEFAULT '草稿',
    review_status      VARCHAR(20) NOT NULL DEFAULT '草稿',
    review_by          VARCHAR(100),
    reviewed_at        TIMESTAMP,
    review_reason      TEXT,
    data_status        VARCHAR(20) NOT NULL DEFAULT '正常',
    contract_notes     TEXT,
    version            INTEGER NOT NULL DEFAULT 1,
    created_at         TIMESTAMP NOT NULL,
    updated_at         TIMESTAMP NOT NULL,
    created_by         VARCHAR(100),
    updated_by         VARCHAR(100),
    source_session_id  VARCHAR(100)             -- PDF 导入追踪
);
```

枚举约束：
- `contract_direction`：`出租` / `承租`
- `group_relation_type`：`上游` / `下游` / `委托` / `直租`
- `status`：`草稿` / `待审` / `生效` / `已到期` / `已终止`
- `review_status`：`草稿` / `待审` / `已审` / `反审核`

业务约束（在 Service 层校验）：
- `承租模式`（ContractGroup.revenue_mode=lease）下 `group_relation_type` 只允许 `上游` / `下游`
- `代理模式`（ContractGroup.revenue_mode=agency）下 `group_relation_type` 只允许 `委托` / `直租`
- 进入 `待审/生效` 前 `sign_date` 必填

### 2.4 `lease_contract_details` 表

```sql
CREATE TABLE lease_contract_details (
    lease_detail_id   VARCHAR PRIMARY KEY,
    contract_id       VARCHAR UNIQUE NOT NULL REFERENCES contracts(contract_id),
    total_deposit     NUMERIC(18,2) DEFAULT 0,
    rent_amount       NUMERIC(18,2) NOT NULL,  -- 合同总租金汇总
    -- rent_amount_excl_tax 为派生字段，不写入
    monthly_rent_base NUMERIC(15,2),
    payment_cycle     VARCHAR(20) DEFAULT '月付',   -- 月付/季付/半年付/年付
    payment_terms     TEXT,
    tenant_name       VARCHAR(200),   -- 冗余展示
    tenant_contact    VARCHAR(100),
    tenant_phone      VARCHAR(20),
    tenant_address    VARCHAR(500),
    tenant_usage      VARCHAR(500),
    owner_name        VARCHAR(200),   -- 冗余展示
    owner_contact     VARCHAR(100),
    owner_phone       VARCHAR(20)
);
```

派生字段：
- `rent_amount_excl_tax`：Service 层按 `is_tax_included / tax_rate` 计算，不写库

### 2.5 `agency_agreement_details` 表

```sql
CREATE TABLE agency_agreement_details (
    agency_detail_id      VARCHAR PRIMARY KEY,
    contract_id           VARCHAR UNIQUE NOT NULL REFERENCES contracts(contract_id),
    service_fee_ratio     NUMERIC(5,4) NOT NULL,   -- 0.05 = 5%
    fee_calculation_base  VARCHAR(30) NOT NULL DEFAULT 'actual_received',
    agency_scope          TEXT
);
```

枚举：`fee_calculation_base`：`actual_received` / `due_amount`

### 2.6 `contract_relations` 表

```sql
CREATE TABLE contract_relations (
    relation_id         VARCHAR PRIMARY KEY,
    parent_contract_id  VARCHAR NOT NULL REFERENCES contracts(contract_id),
    child_contract_id   VARCHAR NOT NULL REFERENCES contracts(contract_id),
    relation_type       VARCHAR(30) NOT NULL,  -- upstream_downstream / agency_direct / renewal
    created_at          TIMESTAMP NOT NULL,
    UNIQUE (parent_contract_id, child_contract_id)
);
```

约束：一个 child 在同一 `relation_type` 下只能有一个 parent（Service 层校验）。

---

## 3. 旧模型迁移策略

### 3.1 现有数据迁移路径

旧 `rent_contracts` → 新三张表映射规则：

| 旧字段 | 新位置 | 转换规则 |
|--------|--------|----------|
| `id` | `contracts.contract_id` | 直接映射 |
| `contract_type=LEASE_UPSTREAM` | `contracts.group_relation_type=上游` | 类型映射 |
| `contract_type=LEASE_DOWNSTREAM` | `contracts.group_relation_type=下游` | 类型映射 |
| `contract_type=ENTRUSTED` | `contracts.group_relation_type=委托` | 类型映射 |
| `owner_party_id` | `contracts.lessor_party_id`（上游合同）<br>`contract_groups.owner_party_id` | 双写 |
| `manager_party_id` | `contract_groups.operator_party_id` | 迁移 |
| `tenant_party_id` | `contracts.lessee_party_id` | 迁移 |
| `start_date` / `end_date` | `contracts.effective_from` / `effective_to` | 迁移 |
| `contract_status` | `contracts.status` | 值映射（active→生效，expired→已到期，terminated→已终止）|
| 租金/押金字段 | `lease_contract_details` | 整体迁移 |
| `service_fee_rate` | `agency_agreement_details.service_fee_ratio` | 迁移 |
| `upstream_contract_id` | `contract_relations` (relation_type=upstream_downstream) | 转关系表 |

**合同组生成规则**：
- 同一 `upstream_contract_id` 关联的合同集群 → 生成一个 `ContractGroup`
- 孤立合同（无 `upstream_contract_id`）→ 每条独立生成一个 `ContractGroup`
- `ContractGroup.revenue_mode` 根据 `upstream_contract_id`（上游=lease）/ `ENTRUSTED`（=agency）推断

### 3.2 受影响的子表 FK 迁移

| 表 | 旧 FK | 新 FK | 策略 |
|----|-------|-------|------|
| `rent_terms` | `rent_contracts.id` | `contracts.contract_id` | 修改 FK，保留数据 |
| `rent_ledger` | `rent_contracts.id` | `contracts.contract_id` | 修改 FK，保留数据 |
| `rent_deposit_ledger` | `rent_contracts.id` | `contracts.contract_id` | 修改 FK，保留数据 |
| `rent_contract_attachments` | `rent_contracts.id` | `contracts.contract_id` | 修改 FK，保留数据 |
| `service_fee_ledger` | `rent_contracts.id` | `contracts.contract_id` | 修改 FK，保留数据 |
| `rent_contract_assets` | `rent_contracts.id` | 迁移至 `contract_group_assets` + `contract_assets` | 按新规映射 |

> **注意**：`ServiceFeeLedger` 当前 FK 指向 `rent_contracts.id`。迁移完成后，`ServiceFeeLedger` 应指向 `contracts.contract_id`（其所对应的委托合同）。

### 3.3 数据迁移执行顺序

```
1. 建新表（contract_groups, contracts, lease_contract_details, 
          agency_agreement_details, contract_relations,
          contract_group_assets, contract_assets）
2. 迁移数据（Python 脚本 or Alembic data migration）：
   a. 生成 ContractGroup（按 upstream_contract_id 分组）
   b. 创建 contracts 记录（映射 rent_contracts）
   c. 创建 lease_contract_details / agency_agreement_details
   d. 创建 contract_relations（从 upstream_contract_id 转化）
   e. 迁移关联表（contract_group_assets, contract_assets）
3. 更新子表 FK（rent_terms, rent_ledger 等）
4. 下线旧表（DROP TABLE rent_contracts, rent_contract_assets）
   — 建议在数据验证通过后分阶段进行
```

---

## 4. ORM 设计（SQLAlchemy 2.0）

```python
# backend/src/models/contract_group.py  （新文件）

class RevenueMode(str, enum.Enum):
    LEASE = "lease"
    AGENCY = "agency"

class ContractDirection(str, enum.Enum):
    LESSOR = "出租"
    LESSEE = "承租"

class GroupRelationType(str, enum.Enum):
    UPSTREAM = "上游"
    DOWNSTREAM = "下游"
    ENTRUSTED = "委托"
    DIRECT_LEASE = "直租"

class ContractLifecycleStatus(str, enum.Enum):
    DRAFT = "草稿"
    PENDING_REVIEW = "待审"
    ACTIVE = "生效"
    EXPIRED = "已到期"
    TERMINATED = "已终止"

class ContractReviewStatus(str, enum.Enum):
    DRAFT = "草稿"
    PENDING = "待审"
    APPROVED = "已审"
    REVERSED = "反审核"

class ContractRelationType(str, enum.Enum):
    UPSTREAM_DOWNSTREAM = "upstream_downstream"
    AGENCY_DIRECT = "agency_direct"
    RENEWAL = "renewal"
```

主要 ORM 关系：
- `ContractGroup.contracts` → `list[Contract]`（通过 `selectinload`）
- `Contract.lease_detail` → `LeaseContractDetail | None`（`uselist=False`）
- `Contract.agency_detail` → `AgencyAgreementDetail | None`（`uselist=False`）
- `Contract.contract_group` → `ContractGroup`
- `Contract.rent_terms` → `list[RentTerm]`（现有，重定向 FK）
- `Contract.rent_ledger` → `list[RentLedger]`（现有，重定向 FK）

---

## 5. CRUD 层设计

```
backend/src/crud/contract_group.py
backend/src/crud/contract.py
```

| CRUD 类 | 主要方法 |
|---------|----------|
| `CRUDContractGroup` | `create`, `get`, `get_by_code`, `update`, `list_by_party`, `soft_delete` |
| `CRUDContract` | `create`, `get`, `update`, `list_by_group`, `soft_delete` |

父表-子表一致性由 Service 层保证，CRUD 只做单表操作。

---

## 6. Service 层设计

```
backend/src/services/rent_contract/contract_group_service.py
```

| 方法 | 说明 |
|------|------|
| `create_contract_group(data, db, current_user)` | 校验 settlement_rule 必填键，生成 group_code，创建 ContractGroup + 关联资产 |
| `update_contract_group(group_id, data, db, cu)` | 更新非派生字段，版本号递增 |
| `get_group_detail(group_id, db)` | 加载 ContractGroup + 所有 contracts（selectinload），计算 derived_status，聚合 upstream/downstream contract ids |
| `list_groups(filters, db)` | 分页 + 过滤（revenue_mode, status, party, date 范围） |
| `add_contract_to_group(group_id, contract_data, db, cu)` | 创建 Contract + LeaseContractDetail/AgencyAgreementDetail，校验 group_relation_type 与 revenue_mode 一致性 |
| `calculate_derived_status(contracts)` | 纯函数，输入合同列表，输出 `筹备中/生效中/已结束` |
| `compute_upstream_downstream_ids(group_id, db)` | 查 ContractRelation 聚合 |

**group_code 生成规则**：
```
GRP-{operator_code_segment}-{YYYYMM}-{SEQ4}
operator_code_segment = Party.party_code 的前 8 位大写字母数字（不足 8 位补 X）
SEQ4 = 同 operator_party_id 当月序号，零填充到 4 位
```
例：`GRP-OPER0001-202603-0001`

---

## 7. API 端点设计

路径前缀：`/api/v1/contract-groups`（新路由，独立于现有 `/api/v1/rent-contracts`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/contract-groups` | 创建合同组 |
| `GET` | `/contract-groups` | 分页查询合同组列表 |
| `GET` | `/contract-groups/{group_id}` | 获取合同组详情（含派生字段） |
| `PUT` | `/contract-groups/{group_id}` | 更新合同组基本信息 |
| `DELETE` | `/contract-groups/{group_id}` | 逻辑删除合同组 |
| `POST` | `/contract-groups/{group_id}/contracts` | 向合同组添加合同 |
| `GET` | `/contract-groups/{group_id}/contracts` | 获取合同组内所有合同 |
| `GET` | `/contracts/{contract_id}` | 获取单合同详情（含明细） |
| `PUT` | `/contracts/{contract_id}` | 更新合同信息 |
| `DELETE` | `/contracts/{contract_id}` | 逻辑删除合同 |

> 现有 `/api/v1/rent-contracts` 端点**保持不变**，待合同组体系完全上线后单独制定渐进弃用计划。

---

## 8. Pydantic Schema 设计

```
backend/src/schemas/contract_group.py  （新文件）
```

核心 schemas：
- `ContractGroupCreate`：创建入参，含 `settlement_rule` 必填键校验（Pydantic validator）
- `ContractGroupUpdate`：更新入参
- `ContractGroupDetail`：详情出参，含 `derived_status` / `upstream_contract_ids` / `downstream_contract_ids`
- `ContractGroupListItem`：列表出参（精简字段）
- `ContractCreate`：创建合同入参，按 `group_relation_type` 条件必填 `lease_detail` or `agency_detail`
- `ContractDetail`：合同详情出参，含 lazy 加载的明细对象
- `SettlementRuleSchema`：嵌套 schema，校验 5 个必填键

---

## 9. 分阶段实施计划

### M1 — ORM + Alembic 迁移（优先级最高）

**目标**：建立新表结构，完成数据迁移，保持系统可运行。

**涉及文件**：
1. `backend/src/models/contract_group.py`（新建）
2. `backend/src/models/associations.py`（新增 `contract_group_assets`, `contract_assets`）
3. `backend/src/models/__init__.py`（导出新模型）
4. Alembic migration（新建，含 DDL + 数据迁移）

**验收条件**：
- `make migrate` 可无错执行
- `alembic downgrade -1` 可回退
- 旧 `rent_contracts` 数据全量迁移到新三张表，无数据丢失

### M2 — CRUD + Service + Schema

**目标**：建立业务逻辑骨架，通过单元测试。

**涉及文件**：
1. `backend/src/schemas/contract_group.py`（新建）
2. `backend/src/crud/contract_group.py`（新建）
3. `backend/src/crud/contract.py`（新建）
4. `backend/src/services/rent_contract/contract_group_service.py`（新建）
5. `backend/tests/unit/services/rent_contract/test_contract_group_service.py`（新建）

**验收条件**：
- `pytest -m unit -k contract_group` 全部通过
- `derived_status` 计算逻辑通过纯函数测试（筹备中/生效中/已结束三种场景）
- `settlement_rule` 缺少必填键时 Pydantic 抛 ValidationError

### M3 — API 端点

**目标**：上线合同组 CRUD API。

**涉及文件**：
1. `backend/src/api/v1/rent_contracts/contract_groups.py`（新建）
2. `backend/src/api/v1/rent_contracts/__init__.py`（注册新路由）
3. `backend/tests/unit/api/v1/test_contract_groups.py`（新建）
4. `docs/requirements-specification.md`（更新代码证据）
5. `CHANGELOG.md`（更新变更记录）

**验收条件**：
- `POST /api/v1/contract-groups` 可创建合同组，返回含 `derived_status` 的 JSON
- `GET /api/v1/contract-groups/{id}` 返回 `upstream_contract_ids` / `downstream_contract_ids`（来自 ContractRelation）
- `pytest -m api -k contract_group` 全部通过

---

## 10. 边界情况与测试要点

| 编号 | 场景 | 预期行为 |
|------|------|----------|
| B1 | 承租模式下给合同设置 `group_relation_type=委托` | Service 报错：`代理模式合同类型不能用于承租模式合同组` |
| B2 | 代理模式下给合同设置 `group_relation_type=上游` | Service 报错同上 |
| B3 | 合同组内无任何合同 | `derived_status = 筹备中` |
| B4 | 所有合同均为草稿 | `derived_status = 筹备中` |
| B5 | 有一条合同处于生效，其他均到期 | `derived_status = 生效中` |
| B6 | 所有合同均已终止或已到期 | `derived_status = 已结束` |
| B7 | `settlement_rule` 缺少 `payment_rule` 键 | 422 ValidationError，明确指出缺失字段 |
| B8 | 创建合同时 `sign_date` 为空但 `status=生效` | Service 报错：进入生效前 sign_date 必填 |
| B9 | 合同组的 child 被同一 relation_type 绑定到两个 parent | Service 报错：同类型关系只能有一个父合同 |
| B10 | 续签时 `predecessor_group_id` 指向已结束合同组 | 允许，系统不限制续签对象的状态 |
| B11 | 逻辑删除合同组时组内存在生效合同 | 拒绝：必须先终止/到期所有合同 |
| B12 | `group_code` 重复 | 409 Conflict |

---

## 11. 不在本次范围

| 功能 | 归属 |
|------|------|
| 审核流（合同组主审 + 关键合同联审）| REQ-RNT-004 |
| 反审核与纠错闭环 | REQ-RNT-005 |
| 台账自动化 | REQ-RNT-006 |
| `ContractGroup.effective_to` 自动重派生 | REQ-RNT-003 |
| 前端合同组列表/详情页 | 待 M3 后排 |

---

## 12. 待确认事项

1. **`contracts` 表命名**：是否用 `contracts` 还是保留 `rent_contracts_v3`？  
   → 建议直接用 `contracts`，配合 `CONTRACT_GROUP` 体系，明确与旧表切割。

2. **`RentTerm.contract_id` FK 迁移时机**：M1 一并迁移，还是 M2 再迁移？  
   → **建议 M1 一并迁移**，避免旧表和新表同时存在期间的双写问题。

3. **`ServiceFeeLedger` 迁移**：当前 FK 指向 `rent_contracts.id`，迁移后应指向 `contracts.contract_id`（对应委托合同）。数据量预估？

4. **旧 `/api/v1/rent-contracts` 端点**：M3 完成后是否立即下线？建议给测试账号跑完冒烟测试后再下线。

---

*方案完结后移入 `docs/archive/backend-plans/`，同步更新 `docs/plans/README.md`。*
