# 项目表字段收口方案（M1）

**状态**: ✅ 已完成  
**创建日期**: 2026-03-05  
**完成日期**: 2026-03-05  
**关联需求**: REQ-PRJ-001、REQ-PRJ-002  
**里程碑**: M1（截止 2026-03-31）

---

## 1. 问题描述

`requirements-appendix-fields.md` §3.2 已冻结 Project 字段规格，但 `src/models/project.py` 与规格存在严重偏差：

| 规格要求 | 当前模型状态 |
|---------|-------------|
| `project_name` | 以 `name` 存储，**命名不符** |
| `project_code` | 以 `code` 存储，**命名不符** |
| `status`（英文枚举） | 以 `project_status`（中文值）存储，**命名+值不符** |
| `review_status/by/at/reason` | **全部缺失** |
| 25 个工程管理类字段 | **不在规格内，需 DROP** |
| `is_active` | 已由 `data_status` 替代，**需 DROP** |

---

## 2. 变更策略（破坏性，0→1 阶段不保留兼容层）

### 2.1 字段改名

| 旧列名 | 新列名 | 说明 |
|--------|--------|------|
| `name` | `project_name` | 与规格对齐 |
| `code` | `project_code` | 与规格对齐，UNIQUE 约束随列名更新 |
| `project_status` | `status` | 列名+值同步迁移 |

### 2.2 status 数据迁移映射

| 旧值（中文） | 新值（英文枚举） |
|------------|----------------|
| `规划中` | `planning` |
| `进行中` | `active` |
| `暂停` | `paused` |
| `已完成` | `completed` |
| `已终止` | `terminated` |
| `doing`（历史脏数据） | `active` |
| 其他/NULL | `planning` |

### 2.3 新增枚举

```python
class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"

class ProjectReviewStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
```

### 2.4 新增列

| 列名 | 类型 | 约束 | 默认值 |
|------|------|------|--------|
| `review_status` | String(20) | NOT NULL | `'draft'` |
| `review_by` | String(100) | NULL | — |
| `reviewed_at` | DateTime | NULL | — |
| `review_reason` | Text | NULL | — |

### 2.5 DROP 列（共 22 列）

工程管理类：`short_name`, `project_type`, `project_scale`, `start_date`, `end_date`, `expected_completion_date`, `actual_completion_date`, `construction_company`, `design_company`, `supervision_company`

投资金额类：`total_investment`, `planned_investment`, `actual_investment`, `project_budget`

文本描述类：`project_description`, `project_objectives`, `project_scope`

地址/联系人类：`address`, `city`, `district`, `province`, `project_manager`, `project_phone`, `project_email`

冗余状态类：`is_active`

---

## 3. 全局改名影响（sed）

| 改名 | 后端源文件 | 测试文件 | 前端 |
|------|-----------|---------|------|
| `\.name` / `["name"]` → `project_name` | 慎重（只改 Project 上下文） | — | — |
| `\.code\b` → `project_code` | 慎重（只改 Project 上下文） | — | — |
| `project_status` → `status` | schemas, crud, service | tests | frontend |
| `is_active` → (删除) | crud, service | tests | frontend |

> ⚠️ `name`/`code` 是通用词，**不能用全局 sed**，需要文件级精准替换。

---

## 4. 执行顺序

```
Model (models/project.py)
  → Alembic 迁移（down_revision: 20260305_asset_field_enrichment_m1）
  → Schema (schemas/project.py) — 精准替换
  → CRUD (crud/project.py) — 精准替换
  → Service (services/project/service.py) — 精准替换
  → 全局 sed: project_status → status（仅 project 相关文件）
  → 前端精准替换
  → pytest -m unit
  → SSOT docs 同步 + CHANGELOG
```

---

## 5. 代码证据

- `backend/src/models/project.py` — 新枚举 `ProjectStatus`/`ProjectReviewStatus`，字段全部收口
- `backend/alembic/versions/20260305_project_field_enrichment_m1.py` — RENAME + DROP + ADD 迁移
- `backend/src/schemas/project.py` — 重写 `ProjectBase/Create/Update/Response/SearchRequest`
- `backend/src/crud/project.py` — 字段引用全部更新
- `backend/src/crud/field_whitelist.py` — `ProjectWhitelist` 更新
- `backend/src/services/project/service.py` — `create_project`/`toggle_status`/`generate_project_code` 更新
- `frontend/src/types/project.ts` — 接口全部重写
- `frontend/src/services/projectService.ts` — 字段引用更新
- 测试：4418 passed, 3 skipped（2026-03-05）
