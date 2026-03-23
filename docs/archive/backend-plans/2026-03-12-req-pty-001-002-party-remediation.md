# REQ-PTY-001/002：主体主档管理 Gap 修复

**状态**: ✅ 已完成  
**需求编号**: REQ-PTY-001, REQ-PTY-002  
**里程碑**: M1  
**创建日期**: 2026-03-12  
**前置依赖**: Party CRUD / 审核流骨架已存在

---

## 1. 背景

对 PTY-001/002 现有代码做深度审查后，发现 11 个验收 Gap（7 P1 + 4 P2）。本方案修复全部 P1 和部分 P2，**批量导入本轮不做**。

---

## 2. 已确认设计决策

| # | 决策项 | 结论 | 理由 |
|---|--------|------|------|
| 1 | 驳回语义 | PENDING → DRAFT（直接回草稿） | 无死状态，被驳回后立即可编辑重提审 |
| 2 | 审核历史 | 新建 `PartyReviewLog` 专表 | 对齐 AST-003 的 `AssetReviewLog`，支持多轮历史追溯 |
| 3 | 软删除 | 新增 `deleted_at` 时间戳字段 | 行业惯例，NULL=未删，有值=已软删 |
| 4 | 批量导入 | 本轮不做 | 先跑通核心审核闭环，批量导入后续单独排期 |
| 5 | 前端位置 | 系统管理模块 `/system/parties` | 主体是基础主数据，属低频维护，与组织管理/字典管理同级 |
| 6 | 自然人类型 | 后端 `PartyType` 枚举新增 `INDIVIDUAL` | 自然人租户大量存在，需统一进主档管理；前端已预留该类型 |

---

## 3. Party 状态机（修复后）

```
DRAFT ──提审──▶ PENDING ──通过──▶ APPROVED
  ▲                |
  +────驳回────────+
```

### 合法转换（3 条）

| 动作 | 前置状态 | 目标状态 | 必填字段 |
|------|----------|----------|----------|
| submit（提审） | DRAFT | PENDING | — |
| approve（通过） | PENDING | APPROVED | reviewer, reviewed_at |
| reject（驳回） | PENDING | DRAFT | reviewer, reviewed_at, reason |

> 注：反审核（APPROVED → REVERSED）本轮不实现，保留枚举值 `REVERSED` 供后续扩展。

### 编辑守卫

| 状态 | 可编辑业务字段 | 可提审 | 可删除 |
|------|--------------|--------|--------|
| DRAFT | ✅ | ✅ | ✅ |
| PENDING | ❌ | ❌ | ❌ |
| APPROVED | ❌ | ❌ | ❌ |

---

## 4. 批次拆分

### B1 — 后端状态机 + 编辑守卫 + 去重校验（~8 文件）

| 改动 | 文件 | 说明 |
|------|------|------|
| 枚举对齐 | `backend/src/models/party.py` | `REJECTED` → `REVERSED`（保留供未来反审核用）；`PartyType` 新增 `INDIVIDUAL` |
| 驳回逻辑修复 | `backend/src/services/party/service.py` | `reject_party_review` 目标状态改为 `DRAFT`（不再写入 REJECTED/REVERSED） |
| 编辑守卫 | `backend/src/services/party/service.py` | `update_party()` 检查 `review_status`，PENDING/APPROVED 禁编辑 |
| 删除守卫 | `backend/src/services/party/service.py` | `delete_party()` PENDING/APPROVED 禁删除 |
| 去重友好化 | `backend/src/services/party/service.py` | `create_party()` 先查重 `(party_type, code)`，冲突抛 `DuplicateResourceError` |
| 去重 CRUD 方法 | `backend/src/crud/party.py` | 新增 `get_party_by_type_and_code()` 查询方法 |
| 现有 API 测试修正 | `backend/tests/unit/api/v1/test_party_api.py` | 驳回测试断言：`REJECTED` → `DRAFT` |
| Service 测试 | `backend/tests/unit/services/test_party_service.py` | 补充：驳回回草稿、编辑守卫、删除守卫、去重校验 |

**影响面排查**（枚举改名 `REJECTED` → `REVERSED`，需同步修改引用点）：
- `backend/src/services/party/service.py` — `reject_party_review` 不再使用 REJECTED（改为 DRAFT）
- `backend/src/services/analytics/analytics_service.py` — 仅比对 `APPROVED`，无需改
- `backend/src/services/contract/contract_group_service.py` — `assert_parties_approved` 仅比对 `APPROVED`，无需改
- `backend/tests/unit/api/v1/test_party_api.py` — 断言需从 `REJECTED` 改为 `DRAFT`

**数据迁移**：Alembic 迁移脚本，`UPDATE parties SET review_status = 'draft' WHERE review_status = 'rejected'`（存量被驳回的记录恢复为草稿）

### B2 — 软删除 + 审计日志（~6 文件）

| 改动 | 文件 | 说明 |
|------|------|------|
| Party 加 `deleted_at` | `backend/src/models/party.py` | `DateTime, nullable=True, default=None` |
| 新建 PartyReviewLog | `backend/src/models/party_review_log.py` | party_id, action, from_status, to_status, reviewer, reason, created_at |
| 软删除逻辑 | `backend/src/crud/party.py` | `delete_party` 改为设 `deleted_at`；`get_parties` 默认过滤已删除 |
| 关联引用保护 | `backend/src/services/party/service.py` | 删除前检查是否被合同/资产/项目引用，有引用则拒绝 |
| 审核日志写入 | `backend/src/services/party/service.py` | submit/approve/reject 时写 `PartyReviewLog` |
| Alembic 迁移 | `backend/alembic/versions/xxx_party_soft_delete_review_log.py` | 加列 + 建表 |
| 测试 | `backend/tests/unit/` | 软删除、引用保护、审计日志写入 |

### B3 — 前端补齐（~8 文件）

| 改动 | 文件 | 说明 |
|------|------|------|
| 类型补全 | `frontend/src/types/party.ts` | 加 `review_status / review_by / reviewed_at / review_reason` |
| Service 补审核方法 | `frontend/src/services/partyService.ts` | 加 `submitReview / approveReview / rejectReview` |
| 路由常量 | `frontend/src/constants/routes.ts` | `SYSTEM_ROUTES` 加 `PARTIES: '/system/parties'` |
| 路由注册 | `frontend/src/routes/AppRoutes.tsx` | 注册 Party 列表 / 详情路由 |
| 主体列表页 | `frontend/src/pages/System/PartyListPage.tsx` | 表格 + 搜索 + 筛选 + 审核状态展示 |
| 主体详情页 | `frontend/src/pages/System/PartyDetailPage.tsx` | 详情 + 编辑表单 + 审核操作按钮 |
| 导航菜单 | 侧边栏组件 | 系统管理下加"主体管理"入口 |
| 测试 | `frontend/src/pages/System/__tests__/` | 列表渲染、审核流转、编辑守卫 |

**完成情况**：已落地 `PartyListPage` / `PartyDetailPage`、`SYSTEM_ROUTES.PARTIES` 与详情路由、系统菜单入口、面包屑/高亮适配，以及前端回归测试 `PartyPages.test.tsx`、`partyService.test.ts`。

---

## 5. 执行顺序

```
B1（状态机 + 守卫 + 去重）
  ↓
B2（软删除 + 审计日志）
  ↓
B3（前端页面）
```

每批完成后运行 `make check` 门禁通过再进入下一批。

---

## 6. 不做 / 后续

| 事项 | 说明 |
|------|------|
| 批量导入 | 后续单独排期，不在本方案范围 |
| 反审核（APPROVED → REVERSED） | 枚举值保留，逻辑后续按需实现 |
| 启停用专用 API | 当前通过 `update_party(status='inactive')` 实现，后续可加专用端点 |
| 合同组表单快速创建 Party | 前端联动，后续单独做 |

---

## 7. 完成结论

- B1：状态机、编辑/删除守卫、去重校验已完成，并由 `backend/tests/unit/services/test_party_service.py`、`backend/tests/unit/api/v1/test_party_api.py` 覆盖。
- B2：软删除、引用保护、审核日志已完成，并由 `backend/alembic/versions/20260312_party_soft_delete_review_log.py` 与对应单测覆盖。
- B3：系统管理前端页面与审核操作已完成，并由 `frontend/src/pages/System/__tests__/PartyPages.test.tsx`、`frontend/src/services/__tests__/partyService.test.ts` 覆盖。
- REQ-PTY-002 中“批量导入”“合同组流程快速创建 Party”仍按本方案约定留待后续排期，因此需求总状态保持 🚧，但本次 Gap remediation 方案已完成并归档。
