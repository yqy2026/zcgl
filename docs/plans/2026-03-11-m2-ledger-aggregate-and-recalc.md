# M2 技术方案：台账跨合同聚合查询 + 变更重算

> **状态**：🔄 待执行  
> **涉及需求**：REQ-RNT-006（M2 范围）  
> **前置依赖**：台账初次生成 ✅ + 单合同查询 ✅ + 批量状态更新 ✅（均已实现）

---

## 1. 现状

| 能力 | 状态 | 位置 |
|------|------|------|
| 合同激活时生成台账 | ✅ | `ledger_service_v2.generate_ledger_on_activation()` |
| 按合同 ID + 账期查询 | ✅ | `contract_group_crud.get_ledger_by_contract()` |
| 批量更新支付状态 | ✅ | `contract_group_crud.batch_update_ledger_status()` |
| **跨合同聚合查询**（按资产/主体/时间区间） | ❌ | — |
| **变更重算**（RentTerm 变更后作废+重建） | ❌ | — |

### 关键数据模型关系

```
ContractGroup 1──N Contract 1──N ContractLedgerEntry
                       │              │
                       │              └─ year_month, amount_due, payment_status
                       │
                       ├── lessor_party_id (FK → parties)
                       ├── lessee_party_id (FK → parties)
                       └── M:N ── contract_assets ── Asset
```

- `ContractLedgerEntry` 无直接 `asset_id` / `party_id`，聚合查询需 JOIN `contracts` + `contract_assets`。
- 一份合同可关联多个资产（`contract_assets` 多对多），聚合按资产查询时需 JOIN。

---

## 2. 功能设计

### 2.1 跨合同聚合查询

**API**：

```
GET /api/v1/ledger/entries
```

独立路由（不嵌套在 `/contracts/{id}/` 下），支持以下筛选参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `asset_id` | string | 否 | 按资产 ID 筛选（JOIN contract_assets） |
| `party_id` | string | 否 | 按主体 ID 筛选（匹配 lessor_party_id 或 lessee_party_id） |
| `contract_id` | string | 否 | 按合同 ID 筛选（已有能力，兼容迁移） |
| `year_month_start` | string | 否 | 开始账期，格式 YYYY-MM |
| `year_month_end` | string | 否 | 结束账期，格式 YYYY-MM |
| `payment_status` | string | 否 | 按支付状态筛选（unpaid/paid/overdue/partial） |
| `offset` | int | 否 | 分页偏移，默认 0 |
| `limit` | int | 否 | 每页条数，默认 20，最大 200 |

**响应**：复用 `ContractLedgerListResponse`（items + total + offset + limit），每条 item 中已包含 `contract_id`，调用方可据此关联合同信息。

**SQL 核心逻辑**：

```sql
SELECT cle.*
FROM contract_ledger_entries cle
JOIN contracts c ON cle.contract_id = c.contract_id
-- 可选 JOIN
LEFT JOIN contract_assets ca ON c.contract_id = ca.contract_id
WHERE 1=1
  AND (:asset_id IS NULL OR ca.asset_id = :asset_id)
  AND (:party_id IS NULL OR c.lessor_party_id = :party_id OR c.lessee_party_id = :party_id)
  AND (:contract_id IS NULL OR cle.contract_id = :contract_id)
  AND (:year_month_start IS NULL OR cle.year_month >= :year_month_start)
  AND (:year_month_end IS NULL OR cle.year_month <= :year_month_end)
  AND (:payment_status IS NULL OR cle.payment_status = :payment_status)
  AND c.data_status = '正常'
ORDER BY cle.year_month ASC, cle.contract_id ASC
```

### 2.2 变更重算

**触发场景**：合同 RentTerm（分阶段租金条款）新增/修改/删除后，若合同处于 `ACTIVE` 状态，需要重算受影响月份的台账。

**API**：

```
POST /api/v1/contracts/{contract_id}/ledger/recalculate
```

**业务规则**：

1. 仅 `ACTIVE` 合同允许重算，其他状态返回 422。
2. 重新读取当前全部 `ContractRentTerm`，展开为新的 `year_month` 覆盖集合。
3. 对比现有台账条目：
   - **新增月份**：创建新台账条目（`payment_status=unpaid`）。
   - **删除月份**（旧条款覆盖但新条款不再覆盖）：标记 `payment_status=voided`（不物理删除）。
   - **金额变动月份**（月份仍覆盖但 `amount_due` 变化）：
     - 若 `payment_status` 为 `unpaid`：直接更新 `amount_due`。
     - 若已部分付/已付（`paid`/`partial`）：不自动覆盖，跳过并记入返回值 `skipped_entries`，由人工决策处理。
4. 返回变更摘要：`{ created: N, updated: N, voided: N, skipped: [...] }`。

**设计决策**：
- 不引入新的"作废+重建"表，直接在 `ContractLedgerEntry` 上操作——`voided` 作为 `payment_status` 新值标记废弃条目。
- 已收款条目不自动覆盖，避免财务数据被意外篡改。

---

## 3. 文件清单（≤10 文件）

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `backend/src/crud/contract_group.py` | 修改 | 新增 `query_ledger_entries()` 方法（跨合同聚合查询，JOIN contract_assets/contracts） |
| 2 | `backend/src/services/contract/ledger_service_v2.py` | 修改 | 新增 `query_ledger_entries()` + `recalculate_ledger()` 方法 |
| 3 | `backend/src/api/v1/contracts/ledger.py` | 新建 | 独立台账路由：`GET /api/v1/ledger/entries` + `POST /contracts/{id}/ledger/recalculate`，通过 `route_registry` 注册 |
| 4 | `backend/src/schemas/contract_group.py` | 修改 | 新增 `LedgerAggregateQueryParams`、`LedgerRecalculateResponse` schema |
| 5 | `backend/tests/unit/services/contract/test_ledger_aggregate_query.py` | 新建 | 聚合查询单测（按资产/主体/时间区间/组合筛选） |
| 6 | `backend/tests/unit/services/contract/test_ledger_recalculate.py` | 新建 | 变更重算单测（新增/作废/金额变动/已付跳过） |
| 7 | `backend/tests/unit/api/v1/test_ledger_api.py` | 新建 | API 分层测试（聚合查询 + 重算端点） |

共计 **3 修改 + 4 新建 = 7 文件**。

---

## 4. 实施步骤

```
Step 1: CRUD 层 — query_ledger_entries()
  ↓
Step 2: Schema 层 — LedgerAggregateQueryParams + LedgerRecalculateResponse
  ↓
Step 3: Service 层 — query_ledger_entries() + recalculate_ledger()
  ↓
Step 4: API 层 — 新建 ledger.py 路由 + 注册
  ↓
Step 5: 测试 — 单测 + API 测试
  ↓
Step 6: 文档更新 — REQ-RNT-006 代码证据 + CHANGELOG
```

---

## 5. 测试用例

### 聚合查询

| # | 用例 | 期望 |
|---|------|------|
| Q-01 | 按 `asset_id` 查询，资产关联 2 份合同 | 返回两份合同的全部台账条目 |
| Q-02 | 按 `party_id` 查询（作为 lessor） | 返回该主体作为出租方的合同台账 |
| Q-03 | 按 `party_id` 查询（作为 lessee） | 返回该主体作为承租方的合同台账 |
| Q-04 | 按 `year_month_start` + `year_month_end` 时间窗口 | 仅返回窗口内的台账条目 |
| Q-05 | 组合筛选：`asset_id` + `year_month_start` | 交集结果 |
| Q-06 | 筛选条件无匹配 | 返回空列表，total=0 |
| Q-07 | `data_status=已删除` 的合同台账 | 不返回（被过滤） |
| Q-08 | `payment_status=overdue` 筛选 | 仅返回逾期条目 |

### 变更重算

| # | 用例 | 期望 |
|---|------|------|
| R-01 | RentTerm 新增覆盖 3 个月 | 创建 3 条新台账（unpaid） |
| R-02 | RentTerm 删除使 2 个月不再覆盖 | 2 条台账标记 voided |
| R-03 | RentTerm 金额变更，台账 unpaid | 直接更新 amount_due |
| R-04 | RentTerm 金额变更，台账 paid | 跳过，记入 skipped_entries |
| R-05 | RentTerm 金额变更，台账 partial | 跳过，记入 skipped_entries |
| R-06 | 合同非 ACTIVE 状态 | 返回 422 |
| R-07 | 重算幂等：连续调用两次，第二次无变化 | created=0, updated=0, voided=0 |

---

## 6. 边界条件

| 风险 | 缓解 |
|------|------|
| 一份合同关联多个资产，按 asset_id 查询会返回重复台账条目 | 查询 SQL 使用 `DISTINCT cle.entry_id` 或 `EXISTS` 子查询去重 |
| 重算时合同无 RentTerm | 全部现有台账标记 voided；不报错 |
| 重算时 `total_monthly_amount` 为 NULL（RentTerm 派生字段未写入） | 回退取 `monthly_rent`，与现有生成逻辑一致 |
| 聚合查询数据量大（无筛选条件） | 至少一个筛选条件必填 OR 限制 limit 最大 200 |
| voided 条目在后续查询中的展示 | 聚合查询默认排除 voided；加 `include_voided=true` 参数可选包含 |

---

## 7. 不包含（M3 范围）

- Excel/CSV 导出
- 每日补偿扫描任务
- 代理协议服务费台账（`ServiceFeeLedger`）
