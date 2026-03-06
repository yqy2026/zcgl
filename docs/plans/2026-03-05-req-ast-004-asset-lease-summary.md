# REQ-AST-004 资产詳情租赁情况展示

**状态**: 🔄 进行中（REQ-RNT-001 已于 2026-03-06 落地，前置依赖满足）
**创建**: 2026-03-05  
**关联需求**: REQ-AST-004  
**G1 阻塞项**: 是（G1 放量唯一剩余门槛）
**前置依赖**: REQ-RNT-001（`Contract` 基表 + `ContractGroup` + `group_relation_type` 枚举必须先建好）

---

## 1. 背景与目标

资产详情页需在一屏内展示三类信息：资产基本信息、租赁情况（按合同类型分类汇总）、客户摘要。  
本方案实现租赁情况汇总与客户摘要部分，资产基本信息已由 REQ-AST-001 覆盖。

### 1.1 口径裁决（四类业务概念 → `group_relation_type`，废弃 `contract_type` 枚举）

原需求草稿中的判定规则（`customer_type ∈ {INTERNAL, AFFILIATED}` / `INTERNAL_LEASE/SELF_USE`）依赖不存在的模型字段。旧 `ContractType` 枚举（`LEASE_UPSTREAM/LEASE_DOWNSTREAM/ENTRUSTED`）已在附录 §10.1（2026-03-03）确认废弃，被 `contract_direction + group_relation_type` 替代。

业务上确定的两种运营模式 + 四类合同角色，通过五层模型中的 `Contract.group_relation_type` 落地：

| group_relation_type | 业务含义 | 展示标签 | 模式（ContractGroup.revenue_mode） | 入约/出约 |
|---|---|---|---|---|
| `上游` | 运营方向产权方承租 | 上游承租 | lease | 内部入约 |
| `下游` | 运营方向终端租户出租 | 下游转租 | lease | 对外出约 |
| `委托` | 运营方受托管理资产 | 委托协议 | agency | 内部入约 |
| `直租` | 产权方直接与终端租户签约，运营方代管 | 直租合同 | agency | 对外出约 |

**客户摘要口径**：仅取对外出约合同（`下游` + `直租`）的 `lessee_party` 名称；内部入约合同（`上游`、`委托`）不出现在客户摘要中。

**MVP 约束**：一个资产只属于一种运营模式（承租或代理），禁止混用，不做系统强制校验，依赖录入规范。

**本方案实现的前提**：REQ-RNT-001 已落地（`Contract` 基表 + `ContractGroup` + `group_relation_type` 可查询）。在此之前，本方案处于 ⏸ 状态。

---

## 2. 活跃合同判定规则

### 2.1 "活跃"定义（MVP 冻结）

采用 **B1 方案**（`ContractLifecycleStatus` 筛选）：

```python
ACTIVE_STATUSES = {ContractLifecycleStatus.ACTIVE}
```

- 包含：`ACTIVE`（生效）
- 排除：`DRAFT`（草稿）、`PENDING_REVIEW`（待审）、`EXPIRED`（已到期）、`TERMINATED`（已终止）
- 同时要求：`data_status == '正常'`

> ⚠️ 枚举类名为 `ContractLifecycleStatus`（非 `ContractStatus`）；成员只有 5 个：`DRAFT/PENDING_REVIEW/ACTIVE/EXPIRED/TERMINATED`，无 `EXPIRING` 或 `RENEWED`。`DataStatusValues` 无 `CONTRACT_NORMAL` 常量，直接用字符串 `"正常"`。

> 不做日期区间重叠检测（B2），MVP 以状态机为准，避免引入日期边界计算复杂度。

### 2.2 周期参数

接口提供 `period_start` / `period_end`（`date` 类型，可选），默认值为**当月第一天到最后一天**：

```python
today = date.today()
default_start = today.replace(day=1)
default_end = (default_start + relativedelta(months=1)) - timedelta(days=1)
```

MVP 阶段 period 参数目前仅影响展示标签（"当月"），**不过滤合同本身**——活跃判定仍以 `ContractStatus` 为准。  
（原因：合同台账还未全量落地，无法可靠地按 period 做金额切片；等 REQ-RNT-006 完成后升级。）

---

## 3. 接口设计

### 3.1 端点

```
GET /api/v1/assets/{asset_id}/lease-summary
```

Query 参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `period_start` | `date` (YYYY-MM-DD) | 否 | 当月第一天 | 展示周期开始 |
| `period_end` | `date` (YYYY-MM-DD) | 否 | 当月最后一天 | 展示周期结束 |

鉴权：`require_authz(action="read", resource_type="asset", resource_id="{asset_id}", deny_as_not_found=True)`

### 3.2 响应 Schema

```python
class ContractTypeSummary(BaseModel):
    group_relation_type: str    # "上游" / "下游" / "委托" / "直租"
    label: str                  # "上游承租" / "下游转租" / "委托协议" / "直租合同"
    contract_count: int
    total_area: float           # 合同约定面积之和（m²），None 时记 0
    monthly_amount: float       # 月度金额合计（monthly_rent_base 之和），None 时记 0

class ContractPartyItem(BaseModel):
    party_id: str | None
    party_name: str             # lessee_party 的名称（下游/直租合同）
    group_relation_type: str    # "下游" 或 "直租"
    contract_count: int

class AssetLeaseSummaryResponse(BaseModel):
    asset_id: str
    period_start: date
    period_end: date
    # 汇总
    total_contracts: int
    total_rented_area: float    # 已出租/管理面积（m²）
    rentable_area: float        # 可出租面积（来自 Asset.rentable_area）
    occupancy_rate: float       # total_rented_area / rentable_area * 100，ROUND_HALF_UP；rentable_area=0 时返回 0
    # 按合同角色分类（固定顺序：上游 → 下游 → 委托 → 直租，无合同的类型也返回 count=0）
    by_type: list[ContractTypeSummary]
    # 客户摘要（仅对外出约：下游 + 直租；同 party_name + group_relation_type 合并计数）
    customer_summary: list[ContractPartyItem]
```

响应包装：`APIResponse[AssetLeaseSummaryResponse]`

### 3.3 面积字段语义

> ⚠️ 依赖 REQ-RNT-001：面积字段归属于 `LeaseContractDetail`（附录 §3.5），当前旧 `RentContract` 无此字段。

- `上游`/`下游`/`直租` 合同：取 `LeaseContractDetail.monthly_rent_base` 做金额统计；面积字段待 REQ-RNT-001 补充后升级。
- `委托` 合同：取 `AgencyAgreementDetail.service_fee_ratio` × 基数；面积字段待升级。
- MVP 策略：`total_area` 统一返回 0，`monthly_amount` 取现有字段。
- `total_rented_area` = 所有活跃合同的面积之和（当前为 0 占位）。

---

## 4. 服务层逻辑

> ⚠️ 以下伪代码基于 REQ-RNT-001 落地后的五层模型，查询对象为 `Contract`（基表）+ `ContractGroup`，不再使用废弃的 `RentContract.contract_type`。

```python
async def get_asset_lease_summary(
    db, *, asset_id: str, period_start: date, period_end: date, current_user_id=None
) -> AssetLeaseSummaryResponse:
    # 1. 获取资产（404 if None 或 data_status=已删除）
    # ⚠️ 正确方法名为 get_async(db, id=asset_id)，不是 get_by_id_async
    asset = await asset_crud.get_async(db, id=asset_id, include_deleted=True)
    if not asset or asset.data_status == DataStatusValues.ASSET_DELETED:
        raise HTTPException(404)

    # 2. 查询该资产的活跃合同（Contract 基表，通过 contract_assets M2M）
    # ⚠️ CRUD 需加载 lease_detail、agency_detail、lessee_party（供客户摘要取名）
    contracts = await contract_crud.get_active_by_asset_id(
        db, asset_id=asset_id, active_statuses=ACTIVE_STATUSES
    )

    # 3. 按 group_relation_type 分组聚合
    type_buckets: dict[str, list[Contract]] = defaultdict(list)
    for c in contracts:
        type_buckets[c.group_relation_type].append(c)

    by_type = []
    for grt, label in [
        ("上游", "上游承租"),
        ("下游", "下游转租"),
        ("委托", "委托协议"),
        ("直租", "直租合同"),
    ]:
        bucket = type_buckets.get(grt, [])
        by_type.append(ContractTypeSummary(
            group_relation_type=grt,
            label=label,
            contract_count=len(bucket),
            total_area=0.0,  # MVP 占位，待 LeaseContractDetail 面积字段落地后升级
            # ⚠️ 不用 _as_decimal()（未定义），直接用 Decimal 运算
            # 委托合同无 lease_detail，monthly_amount 为 0（MVP 可接受，待 REQ-RNT-006 升级）
            monthly_amount=float(sum(
                (c.lease_detail.monthly_rent_base or Decimal("0"))
                for c in bucket if c.lease_detail
            )),
        ))

    # 4. 汇总
    total_contracts = len(contracts)
    total_rented_area = 0.0  # MVP 占位
    rentable_area = float(asset.rentable_area or Decimal("0"))  # ⚠️ 不用 _as_decimal()
    occupancy_rate = 0.0  # MVP 占位（total_rented_area 落地后升级）

    # 5. 客户摘要（仅对外出约：下游 + 直租）
    OUTBOUND_TYPES = {GroupRelationType.DOWNSTREAM, GroupRelationType.DIRECT_LEASE}
    party_counter: dict[tuple[str, str], tuple[str | None, int]] = {}
    for c in contracts:
        if c.group_relation_type not in OUTBOUND_TYPES:
            continue
        # ⚠️ tenant_name 为冗余字段可能为空，优先取 lessee_party.name，均空则"未知租户"
        lessee_name = (
            (c.lease_detail.tenant_name if c.lease_detail else None)
            or (c.lessee_party.name if c.lessee_party else None)
            or "未知租户"
        )
        key = (lessee_name, c.group_relation_type.value)
        pid = str(c.lessee_party_id) if c.lessee_party_id else None
        prev_pid, prev_count = party_counter.get(key, (pid, 0))
        party_counter[key] = (prev_pid or pid, prev_count + 1)
    customer_summary = [
        ContractPartyItem(
            party_id=pid, party_name=name, group_relation_type=grt, contract_count=cnt
        )
        for (name, grt), (pid, cnt) in party_counter.items()
    ]

    return AssetLeaseSummaryResponse(
        asset_id=asset_id,
        period_start=period_start,
        period_end=period_end,
        total_contracts=total_contracts,
        total_rented_area=total_rented_area,
        rentable_area=rentable_area,
        occupancy_rate=occupancy_rate,
        by_type=by_type,
        customer_summary=customer_summary,
    )
```

---

## 5. CRUD 层新增

`contract_crud.get_active_by_asset_id(db, *, asset_id, active_statuses)`:

```python
# JOIN contract_assets（关联表列名：contract_id, asset_id）
# WHERE contract_assets.asset_id = :asset_id
#   AND contract.status IN :active_statuses          -- ContractLifecycleStatus 枚举成员
#   AND contract.data_status = '正常'
# selectinload(Contract.lease_detail)    -- LeaseContractDetail
# selectinload(Contract.agency_detail)   -- AgencyAgreementDetail
# selectinload(Contract.lessee_party)    -- ⚠️ 必须加载，供客户摘要取名
# （无需 contract_group，revenue_mode 不参与本接口计算）
```

> ⚠️ `get_active_by_asset_id` 是新增方法，加入 `CRUDContract` 类（`backend/src/crud/contract.py`）。

---

## 6. 前端设计

### 6.1 新增类型（`frontend/src/types/asset.ts`）

```typescript
export interface ContractTypeSummary {
  group_relation_type: '上游' | '下游' | '委托' | '直租';
  label: string;
  contract_count: number;
  total_area: number;
  monthly_amount: number;
}

export interface ContractPartyItem {
  party_id: string | null;
  party_name: string;
  group_relation_type: string;
  contract_count: number;
}

export interface AssetLeaseSummaryResponse {
  asset_id: string;
  period_start: string;
  period_end: string;
  total_contracts: number;
  total_rented_area: number;
  rentable_area: number;
  occupancy_rate: number;
  by_type: ContractTypeSummary[];
  customer_summary: ContractPartyItem[];
}
```

### 6.2 API 常量（`frontend/src/constants/api.ts`）

```typescript
ASSET: {
  ...
  LEASE_SUMMARY: (id: string) => `/assets/${id}/lease-summary`,
}
```

### 6.3 服务方法（`frontend/src/services/assetService.ts`）

```typescript
getAssetLeaseSummary(assetId: string, params?: { period_start?: string; period_end?: string })
  → Promise<AssetLeaseSummaryResponse>
```

### 6.4 AssetDetailPage 改动

在资产详情页新增"租赁情况"卡片：

- 顶部：本月出租率（大字 + 出租面积/可出租面积）
- 中部：三行按类型汇总表（合同数 | 面积 | 月度金额）
- 底部：客户摘要列表（按合同类型分组 Party 名称）
- 右上角：月份切换控件（`DatePicker.MonthPicker`，默认当月）

月份切换 → 更新 `period_start`/`period_end` query → React Query refetch。

---

## 7. 测试用例

| 用例 | 覆盖点 |
|---|---|
| `test_active_contracts_by_group_relation_type` | 四类（上游/下游/委托/直租）各有合同时正确分组 |
| `test_excludes_non_active_status` | 非活跃状态合同（草稿/待审/已终止）不计入 |
| `test_no_active_contracts` | 全无活跃合同时各类型 count=0，occupancy_rate=0 |
| `test_rentable_area_zero` | `rentable_area=0` 时 occupancy_rate=0（不除零） |
| `test_customer_summary_only_outbound` | 上游 + 委托不出现在客户摘要；下游 + 直租出现 |
| `test_customer_summary_dedup` | 同 party_name + group_relation_type 合并计数 |
| `test_asset_not_found` | 不存在 asset_id → 404 |
| `test_deleted_asset` | `data_status=已删除` → 404 |
| `test_authz_required` | 无 session → 401 |
| `test_period_params_default` | 不传 period → 默认当月 |

---

## 8. 实现顺序

> ⚠️ **前提**：REQ-RNT-001 完成后，按以下顺序实现。

```
[REQ-RNT-001 完成后]
schemas/ (ContractTypeSummary + AssetLeaseSummaryResponse，基于 group_relation_type)
  → crud/ (contract_crud.get_active_by_asset_id)
  → services/asset/asset_service.py (get_asset_lease_summary)
  → api/v1/assets/assets.py (GET /{asset_id}/lease-summary)
  → tests/unit/services/asset/test_asset_lease_summary.py
  → tests/unit/api/v1/test_asset_lease_summary.py
  → frontend/src/types/asset.ts
  → frontend/src/constants/api.ts
  → frontend/src/services/assetService.ts
  → frontend/src/pages/Asset/AssetDetailPage.tsx
```

---

## 9. 边界情况与风险

1. **`RentContract` 无 `rentable_area` 字段**：当前模型只有 `monthly_rent_base`，面积字段不在合同表上（V2 M2M 关联设计中面积归属于 `rent_contract_assets` 或 `ContractGroup`）。MVP 策略：`total_area` 统一返回 0，等 REQ-RNT-001 合同组建模后升级。需在文档中标注。
2. **`委托` 合同无承租方（已处理）**：客户摘要只含对外出约（`下游`、`直租`），`委托` 合同属内部入约，不计入，风险消除。`直租`（`group_relation_type=直租`）合同的承租方来自 `lessee_party`，应有值；若为空则客户摘要该条目展示为"未知租户"。
3. **多资产合同**：一份合同可关联多个资产（M2M）。当从某个资产的视角查询时，该合同会被计入该资产的统计，面积无法拆分。MVP 不处理拆分（记录合同总面积），需 UI 加注释说明。
