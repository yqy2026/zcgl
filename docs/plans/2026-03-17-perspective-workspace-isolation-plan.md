# 视角简化实施前工作区隔离计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不丢失当前混合 WIP 的前提下，为“视角机制简化”创建一个干净、可回退、可分批实施的新工作区，并明确何时可以真正开始实现。

**Architecture:** 当前工作区先从 `develop` 脱离到本地 WIP 分支，完整保全所有未提交改动；随后从干净 `develop` 派生 `.worktrees/` planning worktree，并只把视角审计/方案文档带入。由于当前本地 `develop` 尚不包含 selected-view 的实现基线，这个新 worktree 先承担文档/隔离职责；只有当 selected-view 基线先落到某个可引用分支后，才应从那个基线创建真正的实现 worktree。

**Tech Stack:** Git, `git worktree`, 项目内 `.worktrees/`, `docs/plans/`

---

## 1. 背景

当前仓库工作区同时混有至少 3 条改动流：

1. 视角/selected-view 机制及其前后端测试、文档
2. AI code-debt remediation / 大文件拆分 / service 重构
3. 更广的 auth / party-scope / M1 closure / SSOT 收口

这些改动共享了大量文件，直接在当前脏工作区上继续实施“视角机制简化”，会同时引入：

- 普通 merge conflict
- 更危险的语义 conflict（沿用旧 selected-view 实现，同时又想删掉它）
- 难以回退的历史污染（AI 优化、party-scope 收口、视角简化混在同一条实现线上）

因此，实施前必须先做“冻结现场 + 创建隔离 worktree”。

---

## 2. 处理目标

本计划只解决实施前的工作区管理，不涉及业务代码实现。

处理完成后，应满足：

1. 当前混合工作区的所有改动都仍然可找回。
2. `develop` 能作为干净基线，用于创建新的 planning worktree。
3. 新 worktree 初始只承接视角简化相关文档，不承接当前 header-based selected-view 实现代码。
4. 仅当 selected-view 基线已先落到某个可引用分支时，才从那个分支创建真正的实现 worktree。

### 2.1 当前仓库前提（复核结论）

经复核，当前本地 `develop` **不包含** 以下 selected-view 基线文件：

- `backend/src/services/view_scope.py`
- `frontend/src/contexts/ViewContext.tsx`
- `frontend/src/components/System/GlobalViewSwitcher.tsx`
- `frontend/src/components/System/CurrentViewBanner.tsx`
- `frontend/src/utils/viewSelectionStorage.ts`
- `frontend/src/types/viewSelection.ts`

这意味着：

- 从 `develop` 派生的 `.worktrees/perspective-simplification-planning` 只能作为 **planning/docs worktree**
- 不能在这个 worktree 里直接开始“删除旧 selected-view 机制”的实现，因为 `develop` 上还没有这套实现可删
- 如果要立即开始真正的简化实现，必须先让 selected-view 基线落到一个可引用分支/commit 上，再从那个基线创建第二个 implementation worktree

---

## 3. 命名约定（建议值）

| 对象 | 建议名称 | 说明 |
|------|----------|------|
| 当前混合 WIP 分支 | `wip/2026-03-17-mixed-auth-ai-perspective` | 只用于保全现场 |
| planning 分支 | `docs/perspective-simplification-planning` | 只承载隔离/规划文档 |
| planning worktree 路径 | `.worktrees/perspective-simplification-planning` | 项目内隔离工作区 |
| 视角简化实现分支 | `feature/perspective-simplification` | 真正开始实施时使用 |
| implementation worktree 路径 | `.worktrees/perspective-simplification` | 真正开始实施时使用 |
| 文档检查点 commit | `docs(plan): checkpoint perspective planning docs` | 仅承载 3 个视角简化文档，不承载实现代码 |

---

## 4. 初始带入新 worktree 的文件范围

### 4.1 允许带入

推荐初始只带以下 3 个视角简化专属文档：

- `docs/issues/2026-03-17-view-perspective-mechanism-audit.md`
- `docs/plans/2026-03-17-perspective-simplification-plan.md`
- `docs/plans/2026-03-17-perspective-workspace-isolation-plan.md`

说明：为了避免把当前工作区里其他未落地的索引/日志改动一起带入，新 worktree 的初始运输集合默认**不包含** `docs/plans/README.md` 和 `CHANGELOG.md`。

### 4.2 暂不带入

以下文件即使与视角机制有关，也先不要带入新的简化 worktree：

#### 后端混合链路

- `backend/src/api/v1/assets/assets.py`
- `backend/src/api/v1/assets/project.py`
- `backend/src/api/v1/assets/property_certificate.py`
- `backend/src/api/v1/contracts/contract_groups.py`
- `backend/src/api/v1/contracts/ledger.py`
- `backend/src/api/v1/system/collection.py`
- `backend/src/api/v1/system/history.py`
- `backend/src/api/v1/party.py`
- `backend/src/core/exception_handler.py`
- `backend/src/middleware/auth_authz.py`
- `backend/src/services/view_scope.py`

#### 前端混合链路

- `frontend/src/pages/Assets/AssetListPage.tsx`
- `frontend/src/components/Project/ProjectList.tsx`
- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/components/Common/PartySelector.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/contexts/AuthContext.tsx`

#### AI 优化 / 大文件拆分链路

- `frontend/src/components/Project/ProjectTable.tsx`
- `frontend/src/components/Project/ProjectActions.tsx`
- `frontend/src/pages/Contract/ReviewSections.tsx`
- `frontend/src/pages/Contract/ReviewSummary.tsx`
- `frontend/src/pages/Contract/useReviewData.tsx`
- `frontend/src/services/dictionary/*`
- `frontend/src/services/{excelExportService.ts,excelImportService.ts,monitoringMetrics.ts,monitoringTypes.ts,organizationQuery.ts,pdfImportParser.ts,pdfImportTypes.ts}`
- `backend/src/crud/asset_query.py`
- `backend/src/services/asset/{asset_query_service.py,asset_validation.py}`
- `backend/src/services/document/pdf_import_pipeline.py`
- `backend/src/services/permission/{rbac_cache.py,rbac_grant.py,rbac_policy.py,rbac_role.py}`

#### 更广的 auth / party-scope / M1 / SSOT 链路

- `backend/alembic/versions/20260315_party_review_status_backfill.py`
- `backend/src/scripts/migration/party_migration/*`
- `docs/requirements-specification.md`
- `docs/features/requirements-appendix-fields.md`
- `docs/security/phase4-authz-stale-contract.md`
- `docs/security/phase4-no-go-checklist.md`
- `CHANGELOG.md`
- `docs/plans/README.md`

---

## 5. 操作清单

### Task 1：把当前脏工作区从 `develop` 脱离出来

**Files:** 当前所有未提交/未跟踪文件（不做内容修改，只改变分支归属）

- [ ] **Step 1: 记录当前状态**

Run:

```bash
git status --short --branch
```

Expected:

- 输出显示当前在 `develop`
- 仍然能看到大量 `M` / `??` 文件

- [ ] **Step 2: 创建本地 WIP 分支并切换过去**

Run:

```bash
git switch -c "wip/2026-03-17-mixed-auth-ai-perspective"
```

Expected:

- 当前工作区文件内容完全不变
- 只是分支名从 `develop` 变为 `wip/2026-03-17-mixed-auth-ai-perspective`

- [ ] **Step 3: 再次确认文件没有丢失**

Run:

```bash
git status --short --branch
```

Expected:

- 第一行变为 `## wip/2026-03-17-mixed-auth-ai-perspective`
- 文件列表与切分支前一致或仅有分支名变化

### Task 2：创建文档检查点（Task 4 的 commit-based 恢复前提）

**Files:**

- `docs/issues/2026-03-17-view-perspective-mechanism-audit.md`
- `docs/plans/2026-03-17-perspective-simplification-plan.md`
- `docs/plans/2026-03-17-perspective-workspace-isolation-plan.md`

说明：这一步的目标不是提交全部混合 WIP，而是只把 3 个“视角简化专属文档”做成一个可搬运的检查点。由于 Task 4 使用 commit hash 恢复文档，所以本任务对该路径是**必需**的。

- [ ] **Step 1: 只暂存视角简化文档**

Run:

```bash
git add "docs/issues/2026-03-17-view-perspective-mechanism-audit.md" "docs/plans/2026-03-17-perspective-simplification-plan.md" "docs/plans/2026-03-17-perspective-workspace-isolation-plan.md"
```

- [ ] **Step 2: 核对暂存区只包含文档**

Run:

```bash
git diff --cached --name-only
```

Expected:

- 只出现上述 3 个 docs 文件
- 不出现后端/前端实现代码文件

- [ ] **Step 3: 提交文档检查点**

Run:

```bash
git commit -m "docs(plan): checkpoint perspective planning docs"
```

Expected:

- 只生成一个 docs-only commit

注意：

- 如果 hook 失败，修文档后重试
- 不要使用 `--no-verify`

- [ ] **Step 4: 记录检查点 commit hash**

Run:

```bash
git rev-parse --short HEAD
```

Expected:

- 得到一个短 hash，后续用于把文档带入新 worktree

### Task 3：从本地 `develop` 引用创建新的 planning worktree

**Files:** `.worktrees/perspective-simplification-planning`（新工作目录）

- [ ] **Step 1: 确认 `.worktrees/` 已被忽略**

Run:

```bash
git check-ignore .worktrees
```

Expected:

- 输出 `.worktrees`
- 如果没有输出，先停止并修正 `.gitignore`

- [ ] **Step 2: 确保 `.worktrees/` 目录存在**

Run:

```bash
mkdir -p ".worktrees"
```

Expected:

- `.worktrees/` 目录存在
- 本步骤不会影响 git 跟踪状态（该目录已被忽略）

- [ ] **Step 3: 预检查目标路径和分支名未被占用**

Run:

```bash
git branch --list "docs/perspective-simplification-planning" && ls ".worktrees"
```

Expected:

- 第一段输出为空（表示本地分支尚不存在）
- 第二段输出中不包含 `perspective-simplification-planning`
- 如果任一项已存在，改用唯一后缀名（如 `docs/perspective-simplification-planning-v2`）

- [ ] **Step 4: 在当前 WIP 工作区中，基于本地 `develop` 引用派生新的 planning worktree 与分支**

Run:

```bash
git worktree add ".worktrees/perspective-simplification-planning" -b "docs/perspective-simplification-planning" develop
```

Expected:

- 新目录 `.worktrees/perspective-simplification-planning` 被创建
- 新分支 `docs/perspective-simplification-planning` 建立成功
- 本步骤不要求先把当前工作区切回 `develop`

- [ ] **Step 5: 确认新 worktree 是干净基线**

Run:

```bash
git -C ".worktrees/perspective-simplification-planning" status --short --branch
```

Expected:

- 第一行显示 `docs/perspective-simplification-planning`
- 没有未提交改动

- [ ] **Step 6: 确认两个工作区并存**

Run:

```bash
git worktree list
```

Expected:

- 主工作区仍在 `wip/2026-03-17-mixed-auth-ai-perspective`
- 新 worktree 在 `.worktrees/perspective-simplification-planning`
- 该新 worktree 当前只承担 planning/docs 隔离职责

### Task 4：只把视角简化文档带入新 worktree

**Files:**

- `docs/issues/2026-03-17-view-perspective-mechanism-audit.md`
- `docs/plans/2026-03-17-perspective-simplification-plan.md`
- `docs/plans/2026-03-17-perspective-workspace-isolation-plan.md`

- [ ] **Step 1: 在新 worktree 中从文档检查点恢复文件**

Run:

```bash
git -C ".worktrees/perspective-simplification-planning" restore --source "<docs-commit-hash>" -- "docs/issues/2026-03-17-view-perspective-mechanism-audit.md" "docs/plans/2026-03-17-perspective-simplification-plan.md" "docs/plans/2026-03-17-perspective-workspace-isolation-plan.md"
```

Expected:

- 只恢复 3 个 docs 文件（通常在 `git status --short` 中表现为 `M` 或 `A`）
- 不会带入任何 selected-view 实现代码

- [ ] **Step 2: 核对新 worktree 中的改动范围**

Run:

```bash
git -C ".worktrees/perspective-simplification-planning" status --short
```

Expected:

- 只出现 3 个 docs 文件

- [ ] **Step 3: 可选提交文档到 planning 分支**

Run:

```bash
git -C ".worktrees/perspective-simplification-planning" add "docs/issues/2026-03-17-view-perspective-mechanism-audit.md" "docs/plans/2026-03-17-perspective-simplification-plan.md" "docs/plans/2026-03-17-perspective-workspace-isolation-plan.md" && git -C ".worktrees/perspective-simplification-planning" commit -m "docs(plan): import perspective simplification docs"
```

Expected:

- 新 worktree 拥有自己的 docs 起点提交

说明：

- 本文档检查点 commit 只作为“运输载体”，默认不恢复 `docs/plans/README.md` 与 `CHANGELOG.md`
- `docs/plans/README.md` 和 `CHANGELOG.md` 建议等真正开始实现或正式整理 docs 变更时再处理

### Task 5：确认新 worktree 已满足“可继续规划”的前提

**Files:** 新 worktree 当前状态

- [ ] **Step 1: 确认新 worktree 不含混合实现代码**

Run:

```bash
git -C ".worktrees/perspective-simplification-planning" status --short
```

Expected:

- 除 docs 外没有其他改动，或已经 clean

- [ ] **Step 2: 确认当前 WIP 工作区仍完整保留所有旧改动**

Run:

```bash
git status --short --branch
```

Expected:

- 仍在 `wip/2026-03-17-mixed-auth-ai-perspective`
- 所有未拆主题的改动仍在

- [ ] **Step 3: 确认当前不在该 planning worktree 中直接启动实现**

在**当前仓库状态**下，此时应先停止在 planning/docs 层面，不要直接开始实现。原因是本地 `develop` 尚不包含 selected-view 的实现基线。

- [ ] **Step 4: 判断后续走哪条路径**

推荐二选一：

1. **先让 selected-view 基线落到一个可引用分支**
   - 例如：从当前 WIP 工作区后续再整理出一个仅包含 selected-view 基线代码的 checkpoint 分支
   - 再从那个分支创建真正的 implementation worktree
2. **先继续整理文档，不立即开始实现**
   - 保持 `.worktrees/perspective-simplification-planning` 只承载方案
   - 等 selected-view 基线先落地后，再创建 implementation worktree

- [ ] **Step 5: 只有在 implementation worktree 建立后，才按以下顺序开工**

1. `Batch A`
2. `Batch B`
3. `Batch F`

不要先做：

- 删除 `ViewContext`
- 删除 `authz-stale`
- 删除旧路由
- 批量迁移所有 endpoint

---

## 6. 不要做的操作

- 不要在当前混合工作区直接开始视角简化实现
- 不要先用一个大 `stash` 作为唯一保护手段
- 不要使用 `git reset --hard`
- 不要使用 `git checkout -- <file>` 清理当前工作区
- 不要把 AI 优化文件和视角简化文件一起 cherry-pick 到新 worktree
- 不要把 `backend/alembic/versions/20260315_party_review_status_backfill.py`、`docs/requirements-specification.md`、`docs/features/requirements-appendix-fields.md` 这类更广泛的 auth / M1 / SSOT 改动提前带入新 worktree

---

## 7. 完成标准

满足以下条件后，才算“实施前工作区处理完成”：

1. 当前主工作区已切到 `wip/2026-03-17-mixed-auth-ai-perspective`
2. `.worktrees/perspective-simplification-planning` 已创建
3. 新 worktree 基于干净 `develop`
4. 新 worktree 中只带入了视角简化相关文档
5. 当前混合 WIP 仍完整保留在原工作区
6. 已明确：该 worktree 当前是 planning/docs worktree，而非 implementation worktree
7. 已明确：真正实现要等 selected-view 基线先落到可引用分支后，再按 `Batch A -> Batch B -> Batch F` 开始

---

## 8. 后续拆分建议（非本计划范围）

等视角简化 worktree 稳定后，再回头处理当前混合 WIP，可再拆成：

- `wip/ai-code-debt-remediation`
- `wip/auth-party-scope-m1-closure`

这一步不应与“视角简化实施”并行展开。
