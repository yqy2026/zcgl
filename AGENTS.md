# AGENTS.md

本文件为 AI Coding Agents 提供项目上下文与执行约束（Single Source of Truth）。
每次修改后请先复核没问题后更新 `CHANGELOG.md`。
项目目前在从0到1阶段的开发中，不要做兼容保留操作，充分的暴露问题，要打牢系统基础。
1、写代码之前，先说清楚你打算怎么做，等我确认了再动手。
2、如果我给的需求不够明确，先问清楚再写代码，别自己猜。
3、每次写完代码之后，把你能想到的边界情况列出来，再建议几个测试用例覆盖它们。
4、如果一个任务需要改20个以上的文件，先停下来输出计划文档，按计划文档把它拆成更小的任务再逐一完成。
5、采用TDD方式，遇到 bug 的时候，先写一个能复现这个 bug 的测试，然后修到测试通过为止。
6、每次我纠正你的时候，想想自己哪里做错了，拿出一个方案确保以后不再犯同样的错。
**Last Updated**: 2026-03-28（补充 Done when、Codex 配置与任务模板入口）

---

## 协作入口

### 标准任务输入

优先直接按 [`docs/guides/codex-task-template.md`](docs/guides/codex-task-template.md) 提需求，至少包含以下四段：
- `Goal`：要实现/修复什么
- `Context`：涉及模块、文件、报错、REQ 编号、上下游约束
- `Constraints`：必须遵守的规则，例如先出方案、TDD、不要做兼容保留
- `Done when`：完成标准，避免“做了一半就停”

### 统一完成标准（Done when）

除非任务明确说明只做调研，否则完成时默认同时满足：
1. 代码、文档或配置改动已完成，并与需求一致。
2. 涉及行为变更或 bug 修复时，已先补失败测试或复现用例，再完成修复；纯文档/配置任务至少完成相应校验。
3. 已运行受影响范围内的校验命令；能跑 `make check` 时优先跑，至少保证相关 lint、type-check、test、docs-lint 或定向验证完成。
4. 涉及需求、字段、接口、计划状态时，已同步 SSOT 文档与代码证据。
5. `CHANGELOG.md` 已更新。
6. 回复中已补充边界情况与建议测试用例。

### Codex 项目默认配置

- 仓库级默认配置放在 `.codex/config.toml`
- 长期稳定的项目规则放在本文件
- 操作型说明放在 `docs/guides/`

---

## 项目概述

**土地物业资产运营管理系统**（Real Estate Asset Management & Operations System）

核心功能：资产管理 | 租赁合同管理（PDF 智能提取）| 数据分析报表 | 组织架构管理 | 产权证管理

技术栈：前端 `React 19 + TypeScript 5 + Vite 6 + Ant Design 6 + pnpm`；后端 `FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic`；数据库 `PostgreSQL 18`；缓存 `Redis 8`；文档 AI `Qwen-VL / GLM-4V / Hunyuan Vision / DeepSeek-VL`。

---

## 快速命令

```bash
make dev            # 前后端同时启动（后端 :8002，前端 :5173）
make lint           # 前后端 lint
make type-check     # TypeScript 类型检查
make test           # 前后端测试
make migrate        # alembic upgrade head
make secrets        # 生成 SECRET_KEY / DATA_ENCRYPTION_KEY
make check          # lint + type-check + test + build + docs-lint 全量门禁
make docs-lint      # 仅跑 SSOT 完整性检查
```

> ⚠️ 后端命令统一用 `uv run <cmd>`，禁止直接使用系统 `python/pip` 或 Anaconda。虚拟环境：`backend/.venv`（`uv sync --frozen` 安装依赖）。

---

## 项目结构

```
backend/src/
  api/v1/       # analytics / assets / auth / documents / rent_contracts / system
  services/     # 业务逻辑层
  crud/         # 数据访问层
  models/       # SQLAlchemy ORM
  schemas/      # Pydantic
  core/ security/ middleware/ config/ constants/ enums/ utils/

frontend/src/
  api/ components/ pages/ services/ hooks/ store/ contexts/ types/ routes/ styles/ utils/

docs/ scripts/ Makefile
```

---

## 架构原则

### 后端分层

```
请求 → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑              ↑
         业务逻辑       数据访问
```

**DO / DO NOT：**
- ✅ 业务逻辑 **必须** 放在 `services/`
- ❌ **不要** 在 API 端点中放业务逻辑
- ✅ 数据访问通过 `crud/` 层
- ❌ **不要** 绕过 CRUD 直接操作数据库
- ✅ 新 API 使用 `route_registry.register_router()` 注册
- ✅ API 路径统一 `/api/v1/*`

### 前端状态管理

- 全局 UI / 偏好：Zustand（`useAppStore` / `useAssetStore`）
- 认证状态：React Context（`AuthContext`）
- 服务器数据：React Query
- 表单：React Hook Form
- 局部 UI：`useState`

---

## 后端开发要点

- Pydantic v2：使用 `model_validate()` / `model_dump()`；配置 `model_config = ConfigDict(from_attributes=True)`
- SQLAlchemy 2.0：ORM + QueryBuilder；集合关系用 `selectinload` 避免 N+1；❌ 不要在 schema validator 中触发懒加载
- PII 数据加密：`SensitiveDataHandler` 对身份证号/手机号做 AES-256-CBC 确定性加密；❌ 不要绕过 CRUD 直接写库；`DATA_ENCRYPTION_KEY` 缺失会降级为明文存储
- 计算字段：`unrented_area`、`occupancy_rate` 等由 `AssetCalculator` 计算；❌ 不要从 API 直接写入计算字段；`version` 字段由 ORM 自动维护（乐观锁）

### 新增功能流程
```
Schema (schemas/) → Model (models/) → CRUD (crud/) → Service (services/) → API (api/v1/)
→ 注册: route_registry.register_router(router, prefix="/api/v1", tags=[...], version="v1")
```

---

## 前端开发要点

### 严格布尔表达式

| 场景 | ❌ 错误 | ✅ 正确 |
|------|--------|--------|
| 默认值 | `\|\|` | `??` |
| 空值检查 | `if (value)` | `if (value != null)` |
| 字符串检查 | `if (str)` | `if (str?.trim() !== '')` |
| 数组长度 | `arr.length` | `arr?.length ?? 0` |

### 导入路径
- ✅ 使用 `@/` 别名：`import { X } from '@/components'`
- ❌ 不要用深层相对路径 `../../../`

### API 数据
- ✅ 使用 React Query 管理服务器数据
- ❌ 不要用 `useState + useEffect` 做数据获取

---

## 测试

**后端标记**：`unit` / `integration` / `e2e` / `api` / `database` / `security` / `performance` / `slow`

```bash
cd backend && uv run pytest -m unit
cd backend && uv run pytest -m "not slow"
cd backend && uv run pytest --no-cov <path>        # 低内存
cd backend && uv run pytest -x --maxfail=1 <path>  # 失败即停
cd frontend && pnpm test
```

覆盖率目标：后端 ≥70%（目标 85%）/ 前端 ≥50%（目标 75%）

---

## 参考文档

- 环境变量与启动：[`docs/guides/environment-setup.md`](docs/guides/environment-setup.md)
- 数据库初始化与迁移：[`docs/guides/database.md`](docs/guides/database.md)
- 开发工作流：[`docs/guides/development-workflow.md`](docs/guides/development-workflow.md)
- 测试规范：[`docs/guides/testing-standards.md`](docs/guides/testing-standards.md)
- 文档总入口：[`docs/index.md`](docs/index.md)

---

## Git 工作流

- **分支**：`main`（生产）← `develop`（开发）← `feature/*` / `hotfix/*`
- **提交格式**：`type(scope): description`（如 `feat(auth): 添加 OAuth2 登录`）

### 冲突处理规则

- ❌ **禁止** 大量冲突时直接 `-X theirs/ours` 后推送，必须逐文件人工复核
- ✅ `modify/delete` 冲突先查 `git log -- <file>` 确认是否架构收口
- ✅ 冲突解决后检查：无冲突标记 + 关键导入烟测 + `ruff check` + 受影响测试
- ✅ 涉及 `models/` / `crud/` 的冲突需重点复核，防止重复定义
- ⚠️ rebase `--continue` 会静默丢弃文件，push 前必须核查：文件数吻合 + 关键符号存在；丢失时用 `git cherry-pick <hash>` 恢复

> 📖 详细流程见 [docs/incidents/2026-02-git-conflict-postmortem.md](docs/incidents/2026-02-git-conflict-postmortem.md)

---

## ⚠️ 安全警告

- `SECRET_KEY` 必须为强随机密钥，不得使用默认值；生产环境修改所有默认密码
- **永远不要**提交 `.env` 文件
- 拉取代码后运行 `make migrate`；API 403 检查 RBAC（`init_rbac_data.py`）

---

## 需求 → 代码 SSOT 工作流（AI 必读）

### 唯一真相链路

```
需求变更
  ↓
docs/prd.md                              ← 产品需求入口
docs/specs/domain-model.md               ← 字段、状态、统计口径契约
docs/specs/api-contract.md               ← API、鉴权、数据范围契约
docs/traceability/requirements-trace.md  ← 实现状态、代码证据、测试证据
          ↓
  docs/plans/<date>-<slug>.md             ← 活跃技术方案（🔄/⏸）
  完结后立即移入 docs/archive/backend-plans/
          ↓
  代码实现（分层强制）
  Schema → Model → CRUD → Service → API
          ↓
  make check                              ← 全量门禁（含 docs-lint）
          ↓
  CHANGELOG.md 更新（每次改动强制）
```

### make check 门禁

lint + type-check + test + build + backend-import + **docs-lint**（`check_requirements_authority.py` + `check_field_drift.py`）

docs-lint 覆盖：①旧文档引用守卫 ②代码证据死链检测 ③`plans/` 完成态残留检测 ④PRD/spec 实现证据守卫 ⑤traceability 路径存在性守卫 ⑥旧需求入口跳转页守卫。

`make check-field-drift` 输出字段规格 vs ORM diff：spec-only = 待实现或改名未同步；orm-only = 未文档化或已废弃。

### 新增功能必须遵守的关联动作

| 动作 | 必须同步 |
|------|----------|
| 新增/修改 ORM 字段 | 同步更新 `docs/specs/domain-model.md` 对应实体 |
| 新增 API 端点 | 同步更新 `docs/specs/api-contract.md`；实现证据写入 `docs/traceability/requirements-trace.md` |
| 技术方案完结 | 将 `docs/plans/` 文件移入 `docs/archive/backend-plans/`，更新 `plans/README.md` |
| 需求状态变更 | 产品事实修改 `docs/prd.md`；实现状态修改 `docs/traceability/requirements-trace.md` |
| 任何上述改动 | 更新 `CHANGELOG.md` |

---

## 文档治理规范（AI 必读）

文档根目录：`docs/`，索引：[`docs/index.md`](docs/index.md)。新建文档放 `docs/` 对应子目录，不在 `backend/docs/` 新建。

| 目录 | 放什么 |
|------|--------|
| `docs/guides/` | 操作性开发指南（禁止放 AI 报告）|
| `docs/integrations/` | API 规范、组件手册 |
| `docs/architecture/` | 架构概览、ADR |
| `docs/security/` | 加密、认证、权限设计 |
| `docs/features/` | 旧需求附录兼容跳转页 |
| `docs/plans/` | 仅活跃方案（🔄/⏸），完结后移入 `docs/archive/backend-plans/` |
| `docs/incidents/` | 事故复盘 |
| `docs/issues/` | 技术债务排查报告 |
| `docs/archive/` | 所有不再维护的历史内容 |

**强制规则**：
1. AI 任务报告（summary/report/fix-summary）→ `docs/archive/`，**禁止放 `docs/guides/`**
2. 方案标记 ✅ → 立即移入 `docs/archive/backend-plans/`；`plans/` 只保留 🔄 和 ⏸
3. 文件命名：全小写 + 连字符；方案 `YYYY-MM-DD-<slug>.md`；复盘 `YYYY-MM-<slug>.md`；ADR `ADR-NNNN-<slug>.md`
4. 单文档 >800 行须拆分；新建子目录必须同时创建 `README.md`
5. 内容修改后同步更新 `CHANGELOG.md`
