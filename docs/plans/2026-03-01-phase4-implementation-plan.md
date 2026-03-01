# Phase 4 实施计划：发布窗口执行 + 对账验收 + 发布后收敛

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> I'm using the writing-plans skill to create the implementation plan.

**Goal:** 在一次发布窗口内完成 Party-Role 迁移最终切换（约束收紧 + 旧列/旧表物理删除），并通过对账、权限、性能与回滚演练门禁，进入稳定运行态。  
**Architecture:** 采用 `P4a（Runbook 硬化与演练） -> P4b（维护窗口执行） -> P4c（发布后收敛）` 三段式执行。以“先证据、后放量”为原则，所有放流动作都由硬门禁结果驱动。  
**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 18 + Redis 8 + React 19 + Vite 6 + pnpm

---

**文档类型**: 实施计划  
**创建日期**: 2026-03-01  
**最后更新**: 2026-03-01（v1.0）  
**上游依赖**: [Phase 2 实施计划](./2026-02-19-phase2-implementation-plan.md) / [Phase 3 实施计划](./2026-02-20-phase3-implementation-plan.md)  
**阶段定位**: Party-Role 架构最终切换阶段。执行数据库约束收紧、旧字段物理删除、发布窗口验证与回滚预案闭环。

---

## 0. 阶段总览（P4a / P4b / P4c）

| 子阶段 | 目标 | 时长（估算） | 产物 | 通过标准 |
|---|---|---:|---|---|
| **P4a** | Runbook 硬化 + 生产快照演练 ×2 | 3 天 | 演练记录、No-Go 清单、发布窗口脚本清单 | 两次演练全门禁通过，关键耗时稳定 |
| **P4b** | 维护窗口执行 + 对账/冒烟/性能验收 | 1 个维护窗口（2~6 小时，按数据量） | 窗口执行记录、放流决策记录、回滚证据 | 所有阻断门禁通过后才恢复流量 |
| **P4c** | 发布后收敛与观察 | 3 天 | 稳定性日报、问题台账、Phase 4 Exit 结论 | 无 P0/P1 回归、关键指标稳定、Phase 4 Exit Pass |

---

## 1. Entry 硬门禁（进入 P4 前必须全部满足）

| 门禁项 | 证据 | 状态要求 |
|---|---|---|
| Phase 2 完成（代码就绪） | `docs/plans/2026-02-19-phase2-implementation-plan.md`（v1.14） | 必须完成 |
| Phase 3 完成（P3e Exit） | `docs/plans/execution/phase3e-exit-readiness-20260301.md` | 必须通过 |
| P3→P4 交接 6 项闭环 | `docs/plans/2026-02-20-phase3-implementation-plan.md` §9 | 必须完成 |
| D9 发布验签证据完整 | `docs/release/evidence/capability-guard-env.md` | 必须通过 |
| 维护窗口回滚前置就绪 | 备份策略 + 恢复演练记录 + 恢复后对账记录 | 必须通过 |
| 外部调用方契约签收 | 发布签收单（API 调用方列表 + 负责人） | 必须完成 |
| 阻断缺陷清零 | P0/P1 缺陷台账 | 必须清零 |

> [!IMPORTANT]
> 任何单项未满足，P4 不得开工；禁止“先发布后补证据”。

---

## 2. 产物与文件清单（P4 全程）

### 2.1 计划/执行记录

- 新建：`docs/plans/execution/phase4-execution-context.md`
- 新建：`docs/plans/execution/phase4a-rehearsal-01.md`
- 新建：`docs/plans/execution/phase4a-rehearsal-02.md`
- 新建：`docs/plans/execution/phase4b-release-window-<YYYYMMDD>.md`
- 新建：`docs/plans/execution/phase4c-stabilization-<YYYYMMDD>.md`
- 新建：`docs/plans/execution/phase4-exit-readiness-<YYYYMMDD>.md`

### 2.2 发布证据

- 新建：`docs/release/evidence/phase4-no-go-checklist.md`
- 新建：`docs/release/evidence/phase4-rollback-evidence.md`
- 新建：`docs/release/evidence/phase4-external-signoff.md`

### 2.3 后端执行位点

- 新增 Alembic（约束收紧）：`backend/alembic/versions/20260301_phase4_set_party_columns_not_null.py`
- 新增 Alembic（旧字段删除）：`backend/alembic/versions/20260301_phase4_drop_legacy_party_columns.py`
- 复用脚本：`backend/src/scripts/migration/party_migration/*.py`

---

## 3. P4a：Runbook 硬化 + 生产快照演练 ×2

### Task P4a-1：执行上下文冻结

**目标**: 固化执行快照，避免“跨快照结论漂移”  
**文件**: `docs/plans/execution/phase4-execution-context.md`

**执行命令**

```bash
mkdir -p docs/plans/execution docs/release/evidence
{
  echo "# Phase 4 Execution Context"
  echo "- generated_at_utc: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "- git_branch: $(git rev-parse --abbrev-ref HEAD)"
  echo "- git_commit: $(git rev-parse --short HEAD)"
  echo "- backend_python: $(cd backend && ./.venv/bin/python -V 2>&1)"
  echo "- alembic_current: $(cd backend && ./.venv/bin/alembic current 2>/dev/null | tr '\n' ' ')"
} > docs/plans/execution/phase4-execution-context.md
```

**通过标准**
- 执行快照文件已生成且包含 `git_commit` / `alembic_current`

---

### Task P4a-2：No-Go 清单与阈值固化

**目标**: 把“口头风险”转成阻断规则  
**文件**: `docs/release/evidence/phase4-no-go-checklist.md`

**最低必填项**

1. `abac_policy_subjects` 必须为空或不存在  
2. `owner_party_id / manager_party_id / tenant_party_id` 关键空值计数为 0（按计划阈值）  
3. 角色策略包映射一致性（`user -> dual_party_viewer` 等）  
4. 外部调用方签收完成  
5. 回滚备份与恢复演练完成  
6. 关键耗时不超过演练基线 `+30%`

---

### Task P4a-3：补齐 Phase 4 Alembic 迁移（Step 3 / Step 4）

**目标**: 将 Phase 2 设计里的 Step 3/4 代码化、可回放  
**文件**

- Create: `backend/alembic/versions/20260301_phase4_set_party_columns_not_null.py`
- Create: `backend/alembic/versions/20260301_phase4_drop_legacy_party_columns.py`
- Modify: `backend/tests/unit/migration/`（新增/扩展迁移回归）

**迁移约束**

1. `set_not_null` 必须先于 `drop_legacy` 执行（`depends_on` 明确）  
2. `drop_legacy` 仅删除计划内字段/旧关联表，禁止额外破坏性操作  
3. 迁移脚本需具备“表/列存在性防护”，避免重复执行失败

**验证命令**

```bash
cd backend
./.venv/bin/alembic upgrade head
./.venv/bin/pytest --no-cov tests/unit/migration -q
./.venv/bin/ruff check alembic/versions tests/unit/migration
```

---

### Task P4a-4：演练 #1（生产快照）

**目标**: 跑通完整窗口流程并采集耗时基线  
**文件**: `docs/plans/execution/phase4a-rehearsal-01.md`

**演练流程**

1. 预检（No-Go）  
2. 迁移执行（`set_not_null -> drop_legacy`）  
3. 对账（`reconciliation` 11 项）  
4. 冒烟（后端权限 + 前端主链）  
5. 记录每一阶段耗时、失败点、回滚点

**关键命令**

```bash
cd backend && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --mode rehearsal-1
cd frontend && pnpm check && pnpm build && pnpm test
```

---

### Task P4a-5：演练 #2（修正后复演）

**目标**: 验证修复项有效，确认可进入正式窗口  
**文件**: `docs/plans/execution/phase4a-rehearsal-02.md`

**通过标准**

- 相比演练 #1，失败项已清零或明确豁免签字  
- 总耗时 <= 目标窗口 `80%`  
- 无新增高风险回归

---

### Task P4a-6：发布包冻结

**目标**: 固定窗口执行版本，防止临门变更  
**输出**

- 后端发布 SHA / 前端发布 SHA  
- DB migration revision 清单  
- 窗口操作人 + 回滚负责人 + 值班人名单

---

## 4. P4b：发布窗口执行（维护模式）

### 4.1 执行顺序（严格串行）

1. **T-60 分钟**：发布前预检、备份就绪确认  
2. **T-0**：网关切维护模式，阻断业务流量  
3. **T+0~T+30**：执行 `set_not_null` 迁移  
4. **T+30~T+90**：执行 `drop_legacy` 迁移  
5. **T+90~T+120**：执行对账、权限校验、关键冒烟  
6. **T+120~T+150**：放流决策（通过则恢复，失败则回滚）  
7. **T+150 以后**：发布后首轮观察

> [!WARNING]
> 任何阻断门禁失败，立即停止后续步骤并进入回滚路径。

---

### 4.2 发布窗口硬门禁（阻断项）

| 类别 | 检查项 | 通过标准 |
|---|---|---|
| DDL | 迁移执行成功 | Alembic `upgrade head` 成功且无错误 |
| 数据 | 核心对账 11 项 | `reconciliation` 全 PASS |
| 权限 | ABAC 主路径 | `admin/manager/user` 关键用例行为正确 |
| 前端 | 主链构建与测试 | `pnpm check && pnpm build && pnpm test` 通过 |
| 性能 | 关键 API 延迟 | 相比演练基线劣化 <= 30% |
| 风险 | 错误率 | `5xx` 无持续异常峰值（连续 10 分钟） |

---

### 4.3 窗口执行命令清单（标准口径）

```bash
# 0) 备份（窗口前）
pg_dump --format=custom --file=pre_phase4_$(date +%Y%m%d_%H%M).dump <DB_CONN>

# 1) 进入维护模式（由网关/平台执行）

# 2) 迁移执行
cd backend && ./.venv/bin/alembic upgrade head

# 3) 对账
cd backend && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --mode release

# 4) 后端快速回归（建议最小集）
cd backend && ./.venv/bin/pytest --no-cov tests/unit/migration tests/unit/middleware -q

# 5) 前端门禁
cd frontend && pnpm check && pnpm build && pnpm test
```

---

### 4.4 放流决策规则

**全部满足才允许恢复流量**:

1. 阻断门禁全部通过  
2. 回滚材料完整且可执行  
3. 业务负责人 + 技术负责人共同签字

**任一不满足**:

- 不放流，进入回滚  
- 在 `docs/plans/execution/phase4b-release-window-<YYYYMMDD>.md` 记录失败点与动作

---

## 5. P4c：发布后收敛（3 天观察窗）

### 5.1 观察指标（按天）

1. 鉴权拒绝率（403）与历史基线对比  
2. 核心接口错误率（5xx）  
3. 前端关键页面成功率（资产/合同/项目）  
4. 用户反馈中的权限与数据可见性问题

### 5.2 每日动作

1. 执行一次 `reconciliation` 快速核查  
2. 汇总 P0/P1 缺陷并判定是否触发应急  
3. 更新 `phase4c-stabilization-<YYYYMMDD>.md`

### 5.3 P4 Exit 判定

- 连续 3 天无 P0/P1 回归  
- 指标恢复稳定  
- 风险项均有闭环责任人和截止日期  
- `phase4-exit-readiness-<YYYYMMDD>.md` 结论为 `Pass`

---

## 6. 验证矩阵（命令 + 通过标准）

| 维度 | 命令 | 通过标准 |
|---|---|---|
| 后端 lint | `cd backend && ./.venv/bin/ruff check .` | 无 error |
| 后端测试 | `cd backend && ./.venv/bin/pytest -m "not slow" -q` | 无新增 failure |
| 迁移对账 | `cd backend && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --mode <phase>` | 全 PASS |
| 前端门禁 | `cd frontend && pnpm check` | PASS |
| 前端构建 | `cd frontend && pnpm build` | PASS |
| 前端测试 | `cd frontend && pnpm test` | PASS |
| 最小权限 E2E | `cd frontend && pnpm e2e -- --grep "@authz-minimal"` | PASS |

---

## 7. 回滚预案（窗口级）

### 7.1 触发条件

1. 任一阻断门禁失败且不可在窗口内修复  
2. 关键数据对账 FAIL  
3. 核心功能冒烟失败并影响主业务路径

### 7.2 回滚步骤

1. 维持维护模式（不放流）  
2. 应用回滚到窗口前 SHA  
3. 使用窗口前备份执行 DB 恢复  
4. 恢复后执行最小对账（核心表行数 + `reconciliation --mode rollback-verify`）  
5. 冒烟通过后恢复流量

### 7.3 RTO / RPO 目标

- **RTO**: <= 维护窗口时长的 50%  
- **RPO**: 以窗口前全量备份为准（逻辑丢失目标为 0）

---

## 8. 角色与职责（RACI）

| 事项 | 负责（R） | 审批（A） | 协作（C） | 知会（I） |
|---|---|---|---|---|
| P4a 演练 | 后端负责人 | 技术负责人 | 前端、QA、DBA | 业务负责人 |
| 窗口迁移执行 | DBA + 后端负责人 | 发布负责人 | 前端、QA | 全体干系人 |
| 放流决策 | 发布负责人 | 技术负责人 + 业务负责人 | DBA、QA | 全体干系人 |
| 回滚决策 | 发布负责人 | 技术负责人 | DBA、后端 | 全体干系人 |
| P4c 收敛报告 | QA/值班负责人 | 技术负责人 | 前后端负责人 | 业务负责人 |

---

## 9. 里程碑与节奏（建议）

- **2026-03-02 ~ 2026-03-04**：P4a（Runbook + 演练 2 次）  
- **2026-03-05**：P4b（维护窗口）  
- **2026-03-06 ~ 2026-03-08**：P4c（观察与收敛）  
- **2026-03-08**：Phase 4 Exit 评审

> 若 P4a 任一演练失败，发布窗口顺延，不得压缩验证环节。

---

## 10. 风险清单与缓解

| 风险 | 级别 | 缓解措施 |
|---|---|---|
| 迁移耗时超窗 | 高 | 以两次演练耗时为基线，设置 `+30%` 阈值与 No-Go |
| 删列后回滚复杂 | 高 | 强制全量备份 + 恢复演练 + 回滚脚本演练 |
| 权限语义漂移 | 高 | 发布前后执行最小权限 E2E + 角色 spot-check |
| 外部调用方未适配 | 中 | 签收未完成即阻断发布 |
| 前端构建 warning 演化为故障 | 中 | `pnpm check/build/test` 连续通过才放流 |

---

## 11. Phase 4 Exit Criteria（最终验收）

1. P4a / P4b / P4c 全部完成且证据齐全  
2. Step 3/4（收紧约束 + 旧列删除）在生产窗口执行成功  
3. 对账、权限、性能、冒烟全部通过  
4. 回滚预案执行性经演练验证  
5. 形成 Phase 4 Exit 结论文档并经双负责人签字

---

## 12. 文档历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-03-01 | 1.0 | 新建 P4 完整实施计划（P4a/P4b/P4c、门禁、回滚、RACI、里程碑、Exit 标准）。 |

