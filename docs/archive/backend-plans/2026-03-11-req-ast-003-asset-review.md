# REQ-AST-003：资产主数据审核与反审核

**状态**: ✅ 已完成  
**需求编号**: REQ-AST-003  
**里程碑**: M1  
**创建日期**: 2026-03-11  
**前置依赖**: REQ-AST-001 ✅

---

## 1. 需求摘要

资产等关键主数据需支持审核状态流转，保留操作者与时间。反审核后可恢复可编辑状态。审核态关键字段变更受控。

### 验收条件（引自 requirements-specification.md）

1. 审核前后状态可追踪，保留操作者与时间
2. 反审核后可恢复可编辑状态
3. 审核态关键字段变更受控

---

## 2. 设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 反审核语义 | APPROVED → REVERSED（回退机制） | 发现已审核资产信息有误时可回退修改 |
| 审核态编辑策略 | APPROVED/PENDING 禁止编辑一切业务字段，需先反审核 | 选项 A，最简单可靠 |
| 合同提审 vs 资产审核 | 软警告（warning），不阻断 | MVP 存量资产全为 DRAFT，硬阻断会卡死合同流程 |
| 反审核后行为 | REVERSED 状态可编辑 + 可重提审 | 完整闭环 |
| 审核历史 | 新建 `AssetReviewLog` 审计日志表 | 资产可能多轮审核，覆写字段会丢失历史 |
| 枚举命名 | `REJECTED` → `REVERSED` | 对齐合同侧 `ContractReviewStatus.REVERSED`，反审核 ≠ 驳回 |
| 资产引用方式 | 合同保持实时引用资产，不做签约快照 | 资产是单一主档 SSOT，反审核纠错后合同应看到修正数据；快照留 vNext |

---

## 3. 状态机

```
DRAFT ──提审──▶ PENDING ──通过──▶ APPROVED
  ▲                |                   |
  +────驳回────────+                   +──反审核──▶ REVERSED
                                                      |
                   PENDING ◀────重提审────────────────+
```

### 合法转换（5 条）

| 动作 | 前置状态 | 目标状态 | 谁可操作 | 必填字段 |
|------|----------|----------|----------|----------|
| submit（提审） | DRAFT | PENDING | 运营管理员 | — |
| approve（通过） | PENDING | APPROVED | 业务审核人 | review_by, reviewed_at |
| reject（驳回） | PENDING | DRAFT | 业务审核人 | review_by, reviewed_at, reason |
| reverse（反审核） | APPROVED | REVERSED | 业务审核人 | review_by, reviewed_at, reason |
| resubmit（重提审） | REVERSED | PENDING | 运营管理员 | — |

### 编辑守卫

| 状态 | 可编辑业务字段 | 可提审 |
|------|--------------|--------|
| DRAFT | ✅ | ✅ |
| PENDING | ❌ | ❌ |
| APPROVED | ❌ | ❌ |
| REVERSED | ✅ | ✅ |

---

## 4. 变更清单

### 4.1 ORM 枚举改名

**文件**: `backend/src/models/asset.py`

```python
# Before
class AssetReviewStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"    # 反审核

# After
class AssetReviewStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REVERSED = "reversed"    # 反审核
```

> 数据库列 `review_status` 为 `String(20)` 非 PG enum 类型，改名无需 DDL 迁移。
> 但需 Alembic 数据迁移：`UPDATE assets SET review_status = 'reversed' WHERE review_status = 'rejected'`。

### 4.2 新建 AssetReviewLog 模型

**文件**: `backend/src/models/asset_review_log.py`（新建）

```python
class AssetReviewLog(Base):
    __tablename__ = "asset_review_logs"

    id          # string PK, uuid
    asset_id    # string FK → assets.id, NOT NULL, INDEX
    action      # string(20), NOT NULL — submit/approve/reject/reverse/resubmit
    from_status # string(20), NOT NULL
    to_status   # string(20), NOT NULL
    operator    # string(100) — 操作人
    reason      # text — 原因（reject/reverse 必填）
    context     # text — 附加上下文 JSON（reverse 时记录 {"active_contract_count": N}）
    created_at  # datetime, NOT NULL
```

### 4.3 Alembic 迁移

**文件**: `backend/alembic/versions/20260311_req_ast_003_asset_review.py`（新建）

操作：
1. `CREATE TABLE asset_review_logs`（§4.2 结构）
2. `UPDATE assets SET review_status = 'reversed' WHERE review_status = 'rejected'`

### 4.4 Schema 变更

**文件**: `backend/src/schemas/asset.py`

1. `AssetResponse.review_status` description 更新为 `draft/pending/approved/reversed`
2. 新增 `AssetReviewRejectRequest`（驳回/反审核共用请求体）：
   ```python
   class AssetReviewRejectRequest(BaseModel):
       reason: str = Field(..., min_length=1, max_length=500, description="原因（必填）")
   ```
3. 新增 `AssetReviewWarning`（合同提审时 warning 返回体）——在合同侧 schema 中追加。

### 4.5 Service 层

**文件**: `backend/src/services/asset/asset_service.py`

新增 5 个方法 + 2 个守卫 + 1 个辅助查询：

```python
async def submit_asset_review(self, asset_id: str, operator: str) -> Asset
async def approve_asset_review(self, asset_id: str, reviewer: str) -> Asset
async def reject_asset_review(self, asset_id: str, reviewer: str, reason: str) -> Asset
async def reverse_asset_review(self, asset_id: str, reviewer: str, reason: str) -> Asset
async def resubmit_asset_review(self, asset_id: str, operator: str) -> Asset
```

每个方法内部：
1. 获取资产并校验存在性（使用 `self.get_asset()`）
2. 校验当前 `review_status` 是否为合法前置状态（否则抛 `OperationNotAllowedError`）
3. 直接 `setattr` 更新 `review_status` + `review_by` + `reviewed_at` + `review_reason`（**不走** `update_with_history_async`，避免与 AssetReviewLog 重复记录；参照 `delete_asset` 的直接操作模式）
4. 写入 `AssetReviewLog` 记录（reverse 操作额外查询关联生效合同数写入 `context`）
5. flush（不直接 commit，由 `_transaction()` 上下文管理）
6. 所有方法使用 `self.db`，不额外接收 db 参数（与 `update_asset`/`delete_asset` 一致）

**编辑守卫**：在现有 `update_asset()` 方法头部（步骤 1 存在性检查后）增加：

```python
if asset.review_status in (
    AssetReviewStatus.APPROVED.value,
    AssetReviewStatus.PENDING.value,
):
    raise OperationNotAllowedError(
        f"资产处于 {asset.review_status} 状态，不允许编辑业务字段，请先反审核",
        reason="asset_edit_blocked_by_review_status",
    )
```

**删除守卫**：在现有 `delete_asset()` 方法中（`_ensure_asset_not_linked` 之前）增加同样的状态检查，APPROVED/PENDING 状态禁止删除。

### 4.6 API 端点

**文件**: `backend/src/api/v1/assets/assets.py`

新增 5 个端点（参照 Party 审核 API 模式）：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/{asset_id}/submit-review` | 提审 |
| POST | `/{asset_id}/approve-review` | 通过 |
| POST | `/{asset_id}/reject-review` | 驳回（需 body: reason） |
| POST | `/{asset_id}/reverse-review` | 反审核（需 body: reason） |
| POST | `/{asset_id}/resubmit-review` | 重提审 |
| GET  | `/{asset_id}/review-logs` | 查看审核历史日志 |

权限：
- 写操作端点统一使用 `require_authz(action="update", resource_type="asset", resource_id="{asset_id}")`
- `GET /{asset_id}/review-logs` 使用 `require_authz(action="read", resource_type="asset", resource_id="{asset_id}")`

### 4.7 合同提审软警告

**文件**: `backend/src/services/contract/contract_group_service.py`

在 `submit_review()` 方法中，Party 门禁之后、状态转换之前，增加：

```python
# 软警告：关联资产审核状态检查（不阻断）
# 直接通过 contract_assets 中间表 JOIN assets 查询，不依赖 AssetService
stmt = (
    select(Asset.id, Asset.asset_name, Asset.review_status)
    .join(contract_assets, contract_assets.c.asset_id == Asset.id)
    .where(
        contract_assets.c.contract_id == contract_id,
        Asset.review_status != AssetReviewStatus.APPROVED.value,
    )
)
non_approved_assets = (await db.execute(stmt)).all()
asset_warnings = [
    f"关联资产 {row.asset_name} 尚未审核通过（当前状态：{row.review_status}），请注意核实"
    for row in non_approved_assets
]
```

**返回路径设计**：
- `submit_review` 方法签名改为返回 `tuple[Contract, list[str]]`（合同 + warnings）
- API 层从 tuple 取 warnings，encode 为 JSON 写入 response header `X-Asset-Review-Warnings`
- 前端读取该 header 弹 toast 提示
- 需要 `from src.models.asset import Asset, AssetReviewStatus` 和 `from src.models.associations import contract_assets` 两个新增 import

---

## 5. 不涉及的变更

- 不修改 `AssetCreate` schema（创建时默认 `review_status = draft`，现有行为正确）
- 不新增前端页面（前端对接在方案落地后单独规划）
- 不修改 `AssetCalculator`（计算字段不受审核状态影响）
- 不修改附录字段清单（枚举值 `草稿/待审/已审/反审核` 与 ORM `draft/pending/approved/reversed` 的映射关系不变）

---

## 6. 测试计划

### 6.1 Service 层单元测试

**文件**: `backend/tests/unit/services/asset/test_asset_review.py`（新建）

| 编号 | 测试 | 类型 |
|------|------|------|
| T-01 | submit：DRAFT → PENDING 成功 | 正向 |
| T-02 | submit：非 DRAFT 状态拒绝 | 反向 |
| T-03 | approve：PENDING → APPROVED 成功，写入 review_by/reviewed_at | 正向 |
| T-04 | approve：非 PENDING 状态拒绝 | 反向 |
| T-05 | reject：PENDING → DRAFT 成功，reason 必填校验 | 正向 |
| T-06 | reject：reason 为空拒绝 | 反向 |
| T-07 | reject：非 PENDING 状态拒绝 | 反向 |
| T-08 | reverse：APPROVED → REVERSED 成功，reason 必填 | 正向 |
| T-09 | reverse：reason 为空拒绝 | 反向 |
| T-10 | reverse：非 APPROVED 状态拒绝 | 反向 |
| T-11 | resubmit：REVERSED → PENDING 成功 | 正向 |
| T-12 | resubmit：非 REVERSED 状态拒绝 | 反向 |
| T-13 | 编辑守卫：APPROVED 状态 update_asset 被拒绝 | 反向 |
| T-14 | 编辑守卫：PENDING 状态 update_asset 被拒绝 | 反向 |
| T-15 | 编辑守卫：DRAFT 状态 update_asset 允许 | 正向 |
| T-16 | 编辑守卫：REVERSED 状态 update_asset 允许 | 正向 |
| T-17 | 删除守卫：APPROVED 状态 delete_asset 被拒绝 | 反向 |
| T-18 | 删除守卫：PENDING 状态 delete_asset 被拒绝 | 反向 |
| T-19 | 审核日志：每次状态转换都写入 AssetReviewLog | 正向 |
| T-20 | 审核日志：reverse 操作记录 active_contract_count 到 context | 正向 |
| T-21 | 资产不存在时所有审核操作返回 404 | 反向 |

### 6.2 API 层单元测试

**文件**: `backend/tests/unit/api/v1/test_asset_review_api.py`（新建）

| 编号 | 测试 | 类型 |
|------|------|------|
| TA-01 | 5 个审核端点委托 service 层（分层守卫） | 分层 |
| TA-02 | reject-review / reverse-review 需 request body | 契约 |
| TA-03 | review-logs 返回日志列表 | 正向 |
| TA-04 | 合同提审时关联资产未审核返回 warning header（不阻断） | 正向 |
| TA-05 | 合同提审时关联资产全部审核通过无 warning header | 正向 |

### 6.3 模型静态内省测试

**文件**: `backend/tests/unit/models/test_asset_review_status.py`（新建）

| 编号 | 测试 |
|------|------|
| TM-01 | `AssetReviewStatus` 成员集合为 `{DRAFT, PENDING, APPROVED, REVERSED}` |
| TM-02 | 对应 value 为 `{draft, pending, approved, reversed}` |

---

## 7. 复核记录

### 2026-03-11 首次复核（6 个问题）

| 编号 | 级别 | 问题 | 修正 |
|------|------|------|------|
| P1 | 设计缺陷 | `delete_asset` 缺审核态守卫 | 增加 APPROVED/PENDING 状态禁止删除 |
| P2 | 设计缺陷 | 合同侧软警告路径不可行（`AssetService` 是实例类，`contract_group_service` 无依赖） | 改为 CRUD 层直接 JOIN 查询，`submit_review` 改返回 `tuple[Contract, list[str]]` |
| P3 | 精确性 | Service 方法签名缺 db 参数描述 | 明确使用 `self.db`，与 `update_asset`/`delete_asset` 一致 |
| P4 | 精确性 | 审核字段更新走 `update_with_history_async` 会造成日志重复 | 改为直接 `setattr` + `db.flush()`，审计由 `AssetReviewLog` 独立承担 |
| P5 | 遗漏 | `AssetReviewLog` 缺少反审核上下文信息 | 增加 `context` JSON 字段，reverse 时记录关联生效合同数 |
| P6 | 权限 | `review-logs` 端点应为 read 权限 | 改为 `action="read"` |

---

## 7. 文件清单

| 文件 | 操作 |
|------|------|
| `backend/src/models/asset.py` | 改（枚举 REJECTED → REVERSED） |
| `backend/src/models/asset_review_log.py` | 新建 |
| `backend/src/models/__init__.py` | 改（导出 AssetReviewLog） |
| `backend/alembic/versions/20260311_req_ast_003_asset_review.py` | 新建 |
| `backend/src/schemas/asset.py` | 改（新增 AssetReviewRejectRequest + description 更新） |
| `backend/src/services/asset/asset_service.py` | 改（5 个审核方法 + 编辑守卫 + 删除守卫） |
| `backend/src/api/v1/assets/assets.py` | 改（6 个新端点） |
| `backend/src/api/v1/contracts/contract_groups.py` | 改（submit_contract_review 处理 warnings tuple + header） |
| `backend/src/services/contract/contract_group_service.py` | 改（软警告 + `submit_review` 返回 `tuple[Contract, list[str]]`） |
| `backend/tests/unit/services/asset/test_asset_review.py` | 新建 |
| `backend/tests/unit/api/v1/test_asset_review_api.py` | 新建 |
| `backend/tests/unit/models/test_asset_review_status.py` | 新建 |
| `docs/requirements-specification.md` | 改（REQ-AST-003 状态 📋 → 🚧 + 代码证据） |
| `docs/plans/README.md` | 改（新增活跃方案条目） |
| `CHANGELOG.md` | 改 |

共 15 个文件（6 新建 + 9 修改），在 20 文件阈值内，无需进一步拆分。

> ⚠️ **资产与合同数据引用策略**：合同通过 `contract_assets` 中间表 FK 引用资产，始终实时查询最新资产数据，不做签约快照。资产反审核→修改→重审核后，合同侧自动看到修正数据。快照需求留 vNext。

> ⚠️ **资产反审核不联动合同状态**：反审核仅改变资产的 `review_status`，不触碰关联合同的任何状态。通过审计日志 `context` 记录反审核时的关联合同数，便于追溯。
