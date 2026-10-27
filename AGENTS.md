# AGENTS.md

本文件为 AI Coding Agents 提供项目上下文与执行约束（Single Source of Truth）。

- **加载方式**：Codex / opencode 原生读取本文件；`CLAUDE.md`、`GEMINI.md` 首行导入本文件，只放模型专属补充。
- **子目录规则**：`backend/AGENTS.md`、`frontend/AGENTS.md`。所用工具不自动加载子目录文件时，进入该目录工作前先读。
- **维护约定**：长期稳定的规则写本文件，操作型说明放 `docs/guides/`；同一条规则只写一处，其他地方引用。给 agent 提需求的模板见 [`docs/guides/codex-task-template.md`](docs/guides/codex-task-template.md)。

---

## 项目概述

**土地物业资产运营管理系统**（Real Estate Asset Management & Operations System）。项目处于 0→1 阶段：不做兼容保留，充分暴露问题，打牢系统基础。

核心功能：资产管理 | 租赁合同管理（PDF 智能提取）| 数据分析报表 | 组织架构管理 | 产权证管理

技术栈：前端 `React 19 + TypeScript 5 + Vite 6 + Ant Design 6 + pnpm`；后端 `FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic`；数据库 `PostgreSQL 18`；缓存 `Redis 8`

---

## 红线

以下每条只在此处定义，其他章节引用编号：

1. **项目环境**：优先运行 `Makefile` 目标；脱离 `make` 手工执行后端工具时一律 `cd backend && uv run --frozen --extra dev <cmd>`（依赖用 `uv sync --frozen` 装进 `backend/.venv`）。禁止用系统 `python/pip` 或 Anaconda 安装依赖、绕过项目环境。
2. **密钥**：未经用户明确要求，不读取、复制或提交 `.env` 等本地密钥文件（可按需修改 `.env.example`）；`SECRET_KEY` 必须为强随机值，生产环境修改所有默认密码。
3. **本地数据**：未经用户明确要求，不清理或重写 `uploads/`、`logs/`、`output/`、`reports/`、`test-results/`、`node_modules/`、`backend/.venv/` 等本地数据、产物或依赖目录。
4. **分层**：业务逻辑必须放 `services/`，API 端点不放业务逻辑；数据访问必须走 `crud/`，不绕过 CRUD 直接操作数据库。
5. **SSOT 同步**：改动涉及需求、字段、接口、鉴权、数据范围、计划状态或实现证据时，同步对应 SSOT 文档（见「需求 → 代码 SSOT」）；不涉及时不改。
6. **不做兼容保留**：派生投影不得反向成为事实源；禁止以“兼容期”让新旧写入口长期双写；内部模型词不得进入前端导航、按钮、URL 参数或空态。
7. **CHANGELOG**：产生文件改动时，先复核无误，再按「CHANGELOG 规范」追加条目；只读调研不需要。

---

## 快速命令

```bash
make setup       # 安装前后端依赖（uv sync + pnpm install）
make dev         # 前后端同时启动（后端 :8002，前端 :5173）
make check       # 全量门禁（组成见下）
make test        # 后端单元测试 + 前端测试
make lint        # 前后端 lint
make type-check  # 前端类型检查（app + e2e）
make migrate     # alembic upgrade head；拉取代码后先跑
make docs-lint   # SSOT 完整性检查
make secrets     # 生成 SECRET_KEY / DATA_ENCRYPTION_KEY
```

- 其余目标见 `make help`；子目录手工命令见 `backend/AGENTS.md`、`frontend/AGENTS.md`；Windows 进程监控启动：`pwsh -File scripts/dev_watch.ps1`。
- `make check` = 后端 ruff + 迁移命名检查、前端 oxlint、UI guard、type-check、后端单测、前端测试、前端构建、`check-document-runtime`（校验本地 OCR 依赖与模型哈希，环境不全会失败）、backend-import、query-param-drift、test-credentials、docs-lint。以 `Makefile` 的 `check:` 为准。
- API 返回 403 时先查 RBAC 种子数据（`backend/scripts/setup/init_rbac_data.py`）。

---

## 完成标准（Done when）

除非任务明确说明只做调研，完成时默认同时满足：
1. 代码、文档或配置改动已完成，并与需求一致。
2. 涉及行为变更或 bug 修复时，已先补失败测试或复现用例，再完成修复；纯文档/配置任务至少完成相应校验。
3. 已运行受影响范围内的校验：能跑 `make check` 时优先跑，至少保证相关 lint、type-check、test、docs-lint 或定向验证完成。
4. 红线 5（SSOT）与红线 7（CHANGELOG）已落实。
5. 回复中已补充边界情况与建议测试用例。

---

## 12-rule

适用于每个任务（除非被明确覆盖）。非平凡工作谨慎优先于速度；琐事自行判断。上下文受限时，优先满足 7（写前先读）、3（外科手术）、8（测试编码意图）、10（贴合惯例）、11（失败要响）。

1. 先想后写（Think Before Coding）：明确写出假设；不确定就问而非猜；存在歧义列出多种理解；有更简单做法就提出异议；乱了就停下来说清哪里不清楚。
2. 简单优先（Simplicity First）：最小实现解决问题；不写推测性代码；不做超出需求的特性；不为一次性代码建抽象。
3. 外科手术式改动（Surgical Changes）：只动必须动的；不顺手改进相邻代码、注释、格式；不重构没坏的东西；贴合现有风格。
4. 目标驱动（Goal-Driven）：先定成功标准，循环直到验证通过，而不是跟着步骤走。
5. 判断交给模型，路由交给代码：模型只做分类、起草、总结、抽取；不做路由、重试、确定性变换；代码能回答就代码回答。
6. 冲突亮出来，不要折中（Surface Conflicts）：两种模式矛盾时选一种（更新或更经测试的），说明理由，另一处标记待清理。
7. 写前先读（Read Before Writing）：先读导出、直接调用方、共享工具；不理解现有结构就问。
8. 测试编码意图而非行为：业务逻辑变了，测试必须能失败。
9. 每个重要步骤后留检查点（Checkpoint）：能复述已做、已验证、待办。
10. 贴合代码库惯例（Conventions）：惯例优先于个人品味；真有危害就提出来，不要默默另起炉灶。
11. 失败要响（Fail loud）：跳过任何东西就别写“完成”，跳过任何测试就别写“通过”；默认暴露不确定性。不写吞错兜底，让问题爆出来。
12. 治根不治表、可观测：定位真实根因彻底修复，不用补丁掩盖；关键路径留足排查日志，无法修复就如实说明需加日志，不假装修好。

### Sub-agent 使用授权

长期授权：非平凡代码修改、架构收口、测试失败诊断、完成前复核时，按需派发 sub-agent / code-reviewer，无需每次单独询问；使用时必须说明派发目的、边界、复核结论以及是否采纳其建议。子任务边界必须清晰，避免覆盖用户或其他 agent 的未关联改动；代码修改类子任务应明确文件或模块责任范围。

---

## 架构原则

### 后端分层

```
请求 → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑              ↑
         业务逻辑       数据访问
```

- 分层约束见红线 4；API 路径统一 `/api/v1/*`。
- 新 API 在模块内用 `route_registry.register_router(router, prefix="/api/v1", tags=[...], version="v1")` 自注册（示例：`backend/src/api/v1/authz.py`、`party.py`）；已自注册的路由不得再被 `api_router.include_router()` 二次聚合，避免双公共入口；`api/v1/__init__.py` 只负责导入自注册模块以触发注册。
- 新增功能流程：Schema (`schemas/`) → Model (`models/`) → CRUD (`crud/`) → Service (`services/`) → API (`api/v1/`) → `route_registry.register_router(...)` 注册。

> 旧合同域 `rent_contract/` / `rent_contracts/` 已于 M2（REQ-RNT-001 / REQ-RNT-006）按 AD-4 全量下线，新实现落在 `api/v1/contracts/` + `services/contract/` + `models/contract_group.py`，不迁移旧数据。详见 `docs/archive/issues/2026-06-20-rent-contract-dead-dir-cleanup.md`。

### 后端开发要点

- Pydantic v2：使用 `model_validate()` / `model_dump()`；配置 `model_config = ConfigDict(from_attributes=True)`
- SQLAlchemy 2.0：ORM + QueryBuilder；集合关系用 `selectinload` 避免 N+1；不在 schema validator 中触发懒加载
- PII 数据加密：`SensitiveDataHandler` 对身份证号/手机号做 AES-256-CBC 确定性加密；`DATA_ENCRYPTION_KEY` 缺失会降级为明文存储（细节见 `backend/AGENTS.md`）
- 计算字段：`unrented_area`、`occupancy_rate` 等由 `AssetCalculator` 计算，API 不得直接写入；`version` 字段由 ORM 自动维护（乐观锁）

### 前端开发要点

- 状态分工：全局 UI / 偏好用 Zustand（`useAppStore` / `useAssetStore`）；认证用 React Context（`AuthContext`）；服务器数据用 React Query（❌ `useState + useEffect` 做数据获取）；表单用 React Hook Form；局部 UI 用 `useState`。
- 导入路径：✅ `@/` 别名；❌ 深层相对路径 `../../../`。
- 严格布尔表达式（oxlint 不检查这些写法，靠 review 把关）：

| 场景 | ❌ 错误 | ✅ 正确 |
|------|--------|--------|
| 默认值 | `a \|\| b` | `a ?? b` |
| 空值检查 | `if (value)` | `if (value != null)` |
| 非空字符串 | `if (str)`、`str?.trim() !== ''` | `str != null && str.trim() !== ''` |
| 非空数组 | `if (arr.length)` | `(arr?.length ?? 0) > 0` |

> `str?.trim() !== ''` 在 `str` 为 `null/undefined` 时结果为 `true`，等于没判空。

---

## 测试

测试命令、标记、命名与规范见 [`docs/guides/testing-standards.md`](docs/guides/testing-standards.md)。覆盖率目标：后端 ≥70%（目标 85%）/ 前端 ≥50%（目标 75%）。

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
docs/plans/<date>-<slug>.md              ← 活跃技术方案（🔄/⏸）
    完结后立即移入 docs/archive/backend-plans/
  ↓
代码实现（分层强制：Schema → Model → CRUD → Service → API）
  ↓
make check                               ← 全量门禁（含 docs-lint）
  ↓
CHANGELOG.md 追加条目（红线 7）
```

### 门禁说明

docs-lint 覆盖：旧文档引用守卫、代码证据死链检测、`plans/` 完成态残留检测、PRD/spec 实现证据守卫、traceability 路径存在性守卫、旧需求入口跳转页守卫。

`make check-field-drift` 输出字段规格 vs ORM diff：spec-only = 待实现或改名未同步；orm-only = 未文档化或已废弃。

### 新增功能必须遵守的关联动作

| 动作 | 必须同步 |
|------|----------|
| 新增/修改 ORM 字段 | 同步更新 `docs/specs/domain-model.md` 对应实体 |
| 新增 API 端点 | 同步更新 `docs/specs/api-contract.md`；实现证据写入 `docs/traceability/requirements-trace.md` |
| 技术方案完结 | 将 `docs/plans/` 文件移入 `docs/archive/backend-plans/`，更新 `plans/README.md` |
| 需求状态变更 | 产品事实修改 `docs/prd.md`；实现状态修改 `docs/traceability/requirements-trace.md` |

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
4. 单文档 >2000 行须拆分；新建子目录必须同时创建 `README.md`

### CHANGELOG 规范

- 新条目追加在 `CHANGELOG.md`「未发布」段的最上方；更新前读文件开头约 50 行即可，不要整读。
- 每条一行、不超过 200 字：`- type(scope): 做了什么、为什么（REQ-xxx / #issue）`。
- 验证命令输出、截图、逐文件明细写进提交说明或 PR 描述，不写进 CHANGELOG。
- 文件超过 2000 行时，把旧条目按时间段移入 `docs/archive/changelog/` 并更新该目录 `README.md`。

---

## Git 工作流

- **分支**：`main`（生产）← `develop`（开发）← `feature/*` / `hotfix/*`
- **提交格式**：`type(scope): description`（如 `feat(auth): 添加 OAuth2 登录`）
- 大规模重构或实验性改动前，必须先切新分支

### 冲突处理规则

- ❌ **禁止**大量冲突时直接 `-X theirs/ours` 后推送，必须逐文件人工复核
- ✅ `modify/delete` 冲突先查 `git log -- <file>` 确认是否架构收口
- ✅ 解决后检查：无冲突标记 + 关键导入烟测 + `ruff check` + 受影响测试
- ✅ 涉及 `models/` / `crud/` 的冲突需重点复核，防止重复定义
- ⚠️ rebase `--continue` 会静默丢弃文件，push 前必须核查：文件数吻合 + 关键符号存在；丢失时用 `git cherry-pick <hash>` 恢复

---

## Agent skills

- Issues / specs 存于 GitHub Issues：优先用 `gh` CLI（本地已认证 github.com 账户 yqy2026）；无 `gh` 的环境用 GitHub MCP 工具。约定见 `docs/agents/issue-tracker.md`
- Triage 标签：`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`：`docs/agents/triage-labels.md`
- 领域词义与布局：根目录 `CONTEXT.md` + `docs/agents/domain.md`。本段由 `setup-matt-pocock-skills` 生成，`docs/agents/*.md` 可随时手动编辑。

---

## 参考文档

- 环境变量与启动：[`docs/guides/environment-setup.md`](docs/guides/environment-setup.md)；数据库初始化与迁移：[`docs/guides/database.md`](docs/guides/database.md)
- 开发工作流：[`docs/guides/development-workflow.md`](docs/guides/development-workflow.md)；测试规范：[`docs/guides/testing-standards.md`](docs/guides/testing-standards.md)
- 文档总入口：[`docs/index.md`](docs/index.md)
