# Phase 4 实施计划：发布窗口执行 + 对账验收 + 发布后收敛

**文档类型**: 实施计划  
**创建日期**: 2026-03-01  
**最后更新**: 2026-03-01（v2.0 — No-Go 自动断言/Step4 实例引用补盲/E2E 口径收紧）  
**上游依赖**: [Phase 2 实施计划](./2026-02-19-phase2-implementation-plan.md) / [Phase 3 实施计划](./2026-02-20-phase3-implementation-plan.md) / [Party-Role 架构设计](./2026-02-16-party-role-architecture-design.md)  
**阶段定位**: Party-Role 架构最终切换阶段。执行数据库约束收紧、旧字段物理删除、发布窗口验证与回滚预案闭环。  
**执行约定**: 除特别声明外，本文所有命令默认在仓库根目录执行（`/home/y/projects/zcgl`）。

---

## 0. 阶段总览（P4a / P4b / P4c）

| 子阶段 | 目标 | 时长（估算） | 产物 | 通过标准 |
|---|---|---:|---|---|
| **P4a** | Runbook 硬化 + 生产快照演练 ×2 | 3 天 | 演练记录、No-Go 清单、发布窗口脚本清单 | 两次演练全门禁通过，关键耗时稳定 |
| **P4b** | 维护窗口执行 + 对账/冒烟/放流前验收 + Canary 指标判定 | 1 个维护窗口（2~6 小时，按数据量） | 窗口执行记录、放流决策记录、回滚证据 | 放流前阻断门禁通过；Canary 指标通过后才全量恢复 |
| **P4c** | 发布后收敛与观察 | 3 天 | 稳定性日报、问题台账、Phase 4 Exit 结论 | 无 P0/P1 回归、关键指标稳定、Phase 4 Exit Pass |

---

## 1. Entry 硬门禁（进入 P4 前必须全部满足）

| 门禁项 | 证据 | 状态要求 |
|---|---|---|
| Phase 2 完成（代码就绪） | `docs/plans/2026-02-19-phase2-implementation-plan.md`（v1.14） | 必须完成 |
| Phase 3 完成（P3e Exit） | `docs/plans/execution/phase3e-exit-readiness-20260301.md` | 必须通过 |
| P3→P4 交接 6 项闭环 | `docs/plans/2026-02-20-phase3-implementation-plan.md` §9 | 必须完成 |
| D9 发布验签证据完整 | `docs/release/evidence/capability-guard-env.md` | 必须通过 |
| `X-Authz-Stale` 契约补齐并联调留痕 | `docs/release/evidence/phase4-authz-stale-contract.md` | 必须通过 |
| Step 4 运行时依赖基线评审完成 | `docs/release/evidence/phase4-step4-runtime-compat.md`（初版） | 必须通过 |
| 前端构建“无 warning”交接闭环 | 构建日志 + 结论记录（见 §4.2 / §6） | 必须通过 |
| 维护窗口回滚前置就绪 | 备份策略 + 恢复演练记录 + 恢复后对账记录 | 必须通过 |
| 外部调用方契约签收 | `docs/release/evidence/phase4-external-signoff.md` | 必须完成 |
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
- 前置并持续更新：`docs/release/evidence/phase4-authz-stale-contract.md`（Entry 前必须存在，P4 仅补充）
- 新建并持续更新：`docs/release/evidence/phase4-step4-runtime-compat.md`
- 新建：`docs/release/evidence/phase4-rollback-evidence.md`
- 前置并持续更新：`docs/release/evidence/phase4-external-signoff.md`（Entry 前必须存在，P4 仅补充）
- 新建：`docs/release/evidence/phase4-performance-gate.md`
- 新建：`docs/release/evidence/phase4-error-rate-gate.md`
- 新建：`docs/release/evidence/phase4-final-backup-reference.md`

### 2.3 后端执行位点

- 新增 Alembic（约束收紧）：`backend/alembic/versions/20260301_phase4_set_party_columns_not_null.py`
- 新增 Alembic（旧字段删除）：`backend/alembic/versions/20260301_phase4_drop_legacy_party_columns.py`
- 修改对账脚本：`backend/src/scripts/migration/party_migration/reconciliation.py`（兼容 Step 4 删旧列后执行）
- 修改运行时代码：`backend/src/{models,crud,services,middleware,api}/**/*`（清理 Step 4 删除对象引用）
- 修改回归测试：`backend/tests/unit/{migration,middleware,crud,api/v1,schemas}/**/*`（覆盖删列/删表后主链）
- 复用脚本：`backend/src/scripts/migration/party_migration/*.py`

### 2.4 环境变量单源（执行前统一）

```bash
# 建议固定仓库根目录，避免多段命令执行时路径漂移
export PHASE4_REPO_ROOT="${PHASE4_REPO_ROOT:-/home/y/projects/zcgl}"

# 必填：数据库连接（仅接受 postgres 原生 DSN，供 psql/pg_dump/pg_restore 直接使用）
export PHASE4_DB_DSN="${PHASE4_DB_DSN:?Set PHASE4_DB_DSN, e.g. postgresql://user:pass@host:5432/zcgl}"

# 选填：恢复目标库（默认同库恢复，演练建议独立库）
export PHASE4_RESTORE_DSN="${PHASE4_RESTORE_DSN:-$PHASE4_DB_DSN}"

# 选填：目标 API 地址（默认本地，生产必须覆盖）
export PHASE4_API_BASE_URL="${PHASE4_API_BASE_URL:-http://127.0.0.1:8002}"

# 选填：Canary 前端地址（最小权限 E2E 目标地址，发布窗口必须覆盖为真实 Canary URL）
export PHASE4_CANARY_WEB_BASE_URL="${PHASE4_CANARY_WEB_BASE_URL:-http://127.0.0.1:5173}"

# 选填：final backup 引用文件（回滚命令从该文件读取）
export PHASE4_FINAL_BACKUP_REF="${PHASE4_FINAL_BACKUP_REF:-docs/release/evidence/phase4-final-backup-reference.md}"

# 选填：final backup 文件目录（建议持久化挂载盘，避免跨会话/跨目录丢失）
export PHASE4_BACKUP_DIR="${PHASE4_BACKUP_DIR:-$PHASE4_REPO_ROOT/backups/phase4}"

# 必填：tenant_party_id 收紧决策（A=本窗口收紧；B=本窗口保持可空）
export PHASE4_TENANT_NOT_NULL_DECISION="${PHASE4_TENANT_NOT_NULL_DECISION:?Set PHASE4_TENANT_NOT_NULL_DECISION to A or B}"

# 必填：写冻结探针（必须指向一个“写接口”，用于验证维护模式下拒绝写入）
# 建议使用“幂等/无副作用”写探针端点
export PHASE4_WRITE_PROBE_URL="${PHASE4_WRITE_PROBE_URL:?Set PHASE4_WRITE_PROBE_URL to a write endpoint}"

# 必填：写冻结探针 token（必须可触发正常写路径；用于区分“冻结拒绝”与“鉴权失败”）
export PHASE4_WRITE_PROBE_TOKEN="${PHASE4_WRITE_PROBE_TOKEN:?Set PHASE4_WRITE_PROBE_TOKEN to a write-capable bearer token}"

# 必填：X-Authz-Stale 拒绝样例 token（必须为非管理员账号）
export P4_NON_ADMIN_TOKEN="${P4_NON_ADMIN_TOKEN:?Set P4_NON_ADMIN_TOKEN to a non-admin bearer token}"

# Alembic/reconciliation 单源数据库连接（由 libpq DSN 派生）
case "$PHASE4_DB_DSN" in
  postgresql://*) export DATABASE_URL="postgresql+psycopg://${PHASE4_DB_DSN#postgresql://}" ;;
  *)
    echo "Unsupported PHASE4_DB_DSN scheme: $PHASE4_DB_DSN (must be postgresql:// for psql/pg_dump/pg_restore)" >&2
    exit 1
    ;;
esac

# 回滚后对账连接（由 libpq DSN 派生）
case "$PHASE4_RESTORE_DSN" in
  postgresql://*) export PHASE4_RESTORE_DATABASE_URL="postgresql+psycopg://${PHASE4_RESTORE_DSN#postgresql://}" ;;
  *)
    echo "Unsupported PHASE4_RESTORE_DSN scheme: $PHASE4_RESTORE_DSN (must be postgresql:// for psql/pg_restore)" >&2
    exit 1
    ;;
esac

# tenant 决策白名单校验（禁止未声明/拼写错误导致误收紧）
case "$PHASE4_TENANT_NOT_NULL_DECISION" in
  A|B) ;;
  *)
    echo "Unsupported PHASE4_TENANT_NOT_NULL_DECISION: $PHASE4_TENANT_NOT_NULL_DECISION (must be A or B)" >&2
    exit 1
    ;;
esac

# 统一 psql 调用（避免字符串变量中的引号/分词问题）
phase4_psql() {
  psql "$PHASE4_DB_DSN" "$@"
}

# Step4 删除对象运行时引用清零：单源 regex（与 §3 / §4 / §6 共用，禁止各段漂移）
export PHASE4_STEP4_LEGACY_SYMBOL_PATTERN="${PHASE4_STEP4_LEGACY_SYMBOL_PATTERN:-Asset\\.organization_id|assets\\.organization_id|asset\\.organization_id|Asset\\.ownership_id|assets\\.ownership_id|asset\\.ownership_id|Asset\\.management_entity|assets\\.management_entity|asset\\.management_entity|Asset\\.project_id|assets\\.project_id|asset\\.project_id|Project\\.organization_id|projects\\.organization_id|project\\.organization_id|Project\\.management_entity|projects\\.management_entity|project\\.management_entity|Project\\.ownership_entity|projects\\.ownership_entity|project\\.ownership_entity|RentContract\\.ownership_id|rent_contracts\\.ownership_id|rent_contract\\.ownership_id|RentLedger\\.ownership_id|rent_ledger\\.ownership_id|ledger\\.ownership_id|PropertyCertificate\\.organization_id|property_certificates\\.organization_id|property_certificate\\.organization_id|Role\\.organization_id|roles\\.organization_id|role\\.organization_id|entity\\.organization_id|contract\\.ownership_id}"
export PHASE4_STEP4_LEGACY_TABLE_PATTERN="${PHASE4_STEP4_LEGACY_TABLE_PATTERN:-project_ownership_relations|property_owners|property_certificate_owners|abac_policy_subjects}"

# rg 命令必须严格区分“无命中(1)”与“命令异常(2+)”，防止 !rg 误判通过
phase4_assert_no_match() {
  local pattern="$1"
  shift

  rg -n "$pattern" "$@"
  local rg_exit=$?
  if [ "$rg_exit" -eq 0 ]; then
    echo "Unexpected match for pattern: $pattern" >&2
    return 1
  fi

  if [ "$rg_exit" -ne 1 ]; then
    echo "rg execution failed with exit=${rg_exit} for pattern: $pattern" >&2
    return "$rg_exit"
  fi

  return 0
}

# grep 门禁同样区分“无命中(1)”与“命令异常(2+)”
phase4_assert_no_warning_in_file() {
  local file="$1"
  local warning_pattern="${2:-(^|[^a-z])(warning|warn)([^a-z]|$)}"

  if [ ! -r "$file" ]; then
    echo "Log file not readable: $file" >&2
    return 2
  fi

  grep -Eiq "$warning_pattern" "$file"
  local grep_exit=$?
  if [ "$grep_exit" -eq 0 ]; then
    echo "Warning token detected in $file" >&2
    return 1
  fi

  if [ "$grep_exit" -ne 1 ]; then
    echo "grep execution failed with exit=${grep_exit} for file: $file" >&2
    return "$grep_exit"
  fi

  return 0
}

# SQL 数值门禁：必须等于 expected
phase4_assert_sql_equals() {
  local label="$1"
  local sql="$2"
  local expected="$3"
  local actual
  actual="$(phase4_psql -Atqc "$sql")"
  echo "${label}=${actual} (expected=${expected})"
  [ "$actual" = "$expected" ] || {
    echo "Gate failed: ${label} expected=${expected} actual=${actual}" >&2
    return 1
  }
}

# SQL 数值门禁：必须 >= expected
phase4_assert_sql_ge() {
  local label="$1"
  local sql="$2"
  local expected="$3"
  local actual
  actual="$(phase4_psql -Atqc "$sql")"
  case "$actual" in
    ''|*[!0-9]*)
      echo "Gate failed: ${label} non-numeric actual=${actual}" >&2
      return 2
      ;;
  esac
  echo "${label}=${actual} (expected>=${expected})"
  [ "$actual" -ge "$expected" ] || {
    echo "Gate failed: ${label} expected>=${expected} actual=${actual}" >&2
    return 1
  }
}
```

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
  echo "- backend_python: $(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -V 2>&1)"
  echo "- alembic_current: $(cd "$PHASE4_REPO_ROOT/backend" && DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic current 2>/dev/null | tr '\n' ' ')"
} > docs/plans/execution/phase4-execution-context.md
```

**通过标准**
- 执行快照文件已生成且包含 `git_commit` / `alembic_current`

---

### Task P4a-2：No-Go 清单与阈值固化

**目标**: 把“口头风险”转成阻断规则  
**文件**: `docs/release/evidence/phase4-no-go-checklist.md`  
**附加输出**: 更新 `docs/release/evidence/phase4-step4-runtime-compat.md`（保留扫描命令、结果、签字）

**推荐自动化快照（避免手工抄写漂移）**

```bash
(cd "$PHASE4_REPO_ROOT/backend" && \
  PHASE4_TENANT_NOT_NULL_DECISION="$PHASE4_TENANT_NOT_NULL_DECISION" \
  ./.venv/bin/python -m src.scripts.migration.party_migration.phase4_no_go_snapshot \
    --database-url "$DATABASE_URL" \
    --format markdown \
    --enforce) \
  > "$PHASE4_REPO_ROOT/docs/release/evidence/phase4-no-go-sql-snapshot-$(date +%Y%m%d).md"
```

- 该脚本统一产出：SQL 指标快照、门禁判定（PASS/FAIL/SKIP）、`tenant_decision` 留痕。
- 若任一阻断门禁失败，`--enforce` 将返回非零并阻断后续发布动作。

**硬门禁与命令（必须全部有结果）**

1. `abac_policy_subjects` 不得残留（不存在或空表）

```bash
phase4_psql -v ON_ERROR_STOP=1 -c "SELECT to_regclass('public.abac_policy_subjects') AS subject_table;"
phase4_assert_sql_equals "subject_count" \
  "SELECT CASE WHEN to_regclass('public.abac_policy_subjects') IS NULL THEN 0 ELSE (SELECT COUNT(*) FROM abac_policy_subjects) END" \
  "0"
```

2. 主链必填列空值必须为 0（Step 3 前置）

```bash
phase4_assert_sql_equals "assets_owner_null" "SELECT COUNT(*) FROM assets WHERE owner_party_id IS NULL OR owner_party_id=''" "0"
phase4_assert_sql_equals "assets_manager_null" "SELECT COUNT(*) FROM assets WHERE manager_party_id IS NULL OR manager_party_id=''" "0"
phase4_assert_sql_equals "rc_owner_null" "SELECT COUNT(*) FROM rent_contracts WHERE owner_party_id IS NULL OR owner_party_id=''" "0"
phase4_assert_sql_equals "rc_manager_null" "SELECT COUNT(*) FROM rent_contracts WHERE manager_party_id IS NULL OR manager_party_id=''" "0"
phase4_assert_sql_equals "ledger_owner_null" "SELECT COUNT(*) FROM rent_ledger WHERE owner_party_id IS NULL OR owner_party_id=''" "0"
phase4_assert_sql_equals "projects_manager_null" "SELECT COUNT(*) FROM projects WHERE manager_party_id IS NULL OR manager_party_id=''" "0"
```

3. `tenant_party_id` 冻结决策（A/B 二选一，禁止缺省）

- A：本窗口收紧为非空（需 `null_count=0`）
- B：本窗口保持可空（必须写明原因 + 回收时点）

```bash
TENANT_NULL_COUNT="$(phase4_psql -Atqc "SELECT COUNT(*) FROM rent_contracts WHERE tenant_party_id IS NULL OR tenant_party_id=''")"
TENANT_TOTAL_COUNT="$(phase4_psql -Atqc "SELECT COUNT(*) FROM rent_contracts")"
echo "tenant_decision=${PHASE4_TENANT_NOT_NULL_DECISION} tenant_null_count=${TENANT_NULL_COUNT} tenant_total_count=${TENANT_TOTAL_COUNT}"
if [ "$PHASE4_TENANT_NOT_NULL_DECISION" = "A" ]; then
  test "$TENANT_NULL_COUNT" = "0"
fi
```

4. 角色策略包映射一致性（含 `user -> dual_party_viewer`）

```bash
phase4_psql -v ON_ERROR_STOP=1 -c "SELECT r.name, p.name AS policy_name FROM roles r JOIN abac_role_policies rp ON rp.role_id=r.id JOIN abac_policies p ON p.id=rp.policy_id ORDER BY r.name"
phase4_assert_sql_ge "user_dual_party_viewer_mapping_count" \
  "SELECT COUNT(*) FROM roles r JOIN abac_role_policies rp ON rp.role_id=r.id JOIN abac_policies p ON p.id=rp.policy_id WHERE r.name='user' AND p.name='dual_party_viewer'" \
  "1"
```

5. `X-Authz-Stale` 契约联调留痕（代码 + 请求样例）

```bash
rg -n "X-Authz-Stale" backend/src
# 非管理员拒绝样例（示例端点可替换为实际 adminOnly 端点）
HTTP_CODE=$(curl -sS -D /tmp/phase4-authz-deny.headers -o /tmp/phase4-authz-deny.body -w "%{http_code}" \
  -H "Authorization: Bearer ${P4_NON_ADMIN_TOKEN:?set P4_NON_ADMIN_TOKEN}" \
  "${PHASE4_API_BASE_URL:?set PHASE4_API_BASE_URL}/api/v1/system/backup/stats")
echo "http_code=${HTTP_CODE}"
test "${HTTP_CODE}" = "401" || test "${HTTP_CODE}" = "403"
grep -in "x-authz-stale" /tmp/phase4-authz-deny.headers
```

6. 外部调用方签收完成（未签收即 No-Go）

- 证据文件必须包含：调用方清单、负责人、签收日期、风险备注

```bash
test -s docs/release/evidence/phase4-authz-stale-contract.md
test -s docs/release/evidence/phase4-external-signoff.md
```

7. Step 4 删除对象运行时引用清零（未清零即 No-Go）

```bash
phase4_assert_no_match "${PHASE4_STEP4_LEGACY_SYMBOL_PATTERN:?set PHASE4_STEP4_LEGACY_SYMBOL_PATTERN}" \
  backend/src/api backend/src/services backend/src/crud backend/src/middleware backend/src/models backend/src/schemas
phase4_assert_no_match "${PHASE4_STEP4_LEGACY_TABLE_PATTERN:?set PHASE4_STEP4_LEGACY_TABLE_PATTERN}" \
  backend/src/api backend/src/services backend/src/crud backend/src/middleware backend/src/models backend/src/schemas
```

8. `@authz-minimal` 用例强度（禁止 skeleton 占位）

```bash
test -s frontend/tests/e2e/auth/authz-minimal.spec.ts
! rg -n "skeleton: capability guard wiring baseline" frontend/tests/e2e/auth/authz-minimal.spec.ts
AUTHZ_MINIMAL_CASE_COUNT="$(rg -n "test\\(" frontend/tests/e2e/auth/authz-minimal.spec.ts | wc -l | tr -d ' ')"
echo "authz_minimal_case_count=${AUTHZ_MINIMAL_CASE_COUNT}"
test "${AUTHZ_MINIMAL_CASE_COUNT}" -ge 2
```

---

### Task P4a-3：补齐 Phase 4 Alembic 迁移（Step 3 / Step 4）

**目标**: 将 Phase 2 的 Step 3/4 代码化、可回放  
**文件**

- Create: `backend/alembic/versions/20260301_phase4_set_party_columns_not_null.py`
- Create: `backend/alembic/versions/20260301_phase4_drop_legacy_party_columns.py`
- Modify: `backend/src/scripts/migration/party_migration/reconciliation.py`（兼容 Step 4 后 schema）
- Modify: `backend/tests/unit/migration/`（新增/扩展迁移回归）

**迁移约束**

1. `set_not_null` 必须先于 `drop_legacy` 执行（`depends_on` 明确）
2. `drop_legacy` 仅删除计划内字段/旧关联表，禁止额外破坏性操作
3. 迁移脚本需具备“表/列存在性防护”，避免重复执行失败
4. `tenant_party_id` 只在 P4a-2 选择 A 且 `tenant_null_count=0` 时才可收紧
5. `set_not_null` 必须读取 `PHASE4_TENANT_NOT_NULL_DECISION` 并显式执行分支（A=收紧，B=跳过）
6. `reconciliation` 必须兼容 Step 4 删旧列后 schema（禁止硬依赖 `ownership_id`/`organization_id`）
7. 单测需覆盖“删旧列后 reconciliation 仍可运行”场景
8. Step 4 执行前必须通过“删除对象运行时引用清零”门禁（见 P4a-2 第 7 项）
9. 删除 `project_ownership_relations`/`property_owners`/`property_certificate_owners` 前，必须完成替代链路回归并留痕

**Step 3（收紧约束）目标清单**

| 表 | 字段 | 规则 |
|---|---|---|
| `assets` | `owner_party_id` | `SET NOT NULL` |
| `assets` | `manager_party_id` | `SET NOT NULL` |
| `rent_contracts` | `owner_party_id` | `SET NOT NULL` |
| `rent_contracts` | `manager_party_id` | `SET NOT NULL` |
| `rent_contracts` | `tenant_party_id` | 条件收紧（仅决策 A） |
| `rent_ledger` | `owner_party_id` | `SET NOT NULL` |
| `projects` | `manager_party_id` | `SET NOT NULL` |

**Step 4（旧字段/旧表删除）目标清单**

| 类型 | 对象 |
|---|---|
| 旧字段 | `assets.organization_id` |
| 旧字段 | `assets.ownership_id` |
| 旧字段 | `assets.management_entity` |
| 旧字段 | `assets.project_id` |
| 旧字段 | `rent_contracts.ownership_id` |
| 旧字段 | `rent_ledger.ownership_id` |
| 旧字段 | `projects.organization_id` |
| 旧字段 | `projects.management_entity` |
| 旧字段 | `projects.ownership_entity` |
| 旧字段 | `property_certificates.organization_id` |
| 旧字段 | `roles.organization_id` |
| 旧表 | `project_ownership_relations` |
| 旧表 | `property_owners` |
| 旧表 | `property_certificate_owners` |
| 旧表 | `abac_policy_subjects`（存在则删除） |

> [!WARNING]
> Step 4 中“旧表删除”仅在运行时引用清零门禁通过后执行；否则必须 No-Go，不得带病切换。

**验证命令（分段执行）**

```bash
(cd "$PHASE4_REPO_ROOT/backend" && PHASE4_TENANT_NOT_NULL_DECISION="$PHASE4_TENANT_NOT_NULL_DECISION" DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_set_party_columns_not_null)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode phase4a-pre-drop)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest --no-cov tests/unit/migration -q)
phase4_assert_no_match "${PHASE4_STEP4_LEGACY_SYMBOL_PATTERN:?set PHASE4_STEP4_LEGACY_SYMBOL_PATTERN}" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"
phase4_assert_no_match "${PHASE4_STEP4_LEGACY_TABLE_PATTERN:?set PHASE4_STEP4_LEGACY_TABLE_PATTERN}" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"
(cd "$PHASE4_REPO_ROOT/backend" && DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_drop_legacy_party_columns)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode phase4a-post-drop)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest --no-cov tests/unit/migration tests/unit/middleware/test_authz_dependency.py tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/ruff check alembic/versions tests/unit/migration)
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
set -euo pipefail
(cd "$PHASE4_REPO_ROOT/backend" && PHASE4_TENANT_NOT_NULL_DECISION="$PHASE4_TENANT_NOT_NULL_DECISION" DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_set_party_columns_not_null)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode rehearsal-1-pre-drop)
phase4_assert_no_match "$PHASE4_STEP4_LEGACY_SYMBOL_PATTERN" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"
phase4_assert_no_match "$PHASE4_STEP4_LEGACY_TABLE_PATTERN" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"
(cd "$PHASE4_REPO_ROOT/backend" && DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_drop_legacy_party_columns)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode rehearsal-1-post-drop)
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest --no-cov tests/unit/migration tests/unit/middleware/test_authz_dependency.py tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q)
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm check)
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm build 2>&1 | tee /tmp/phase4-rehearsal1-build.log)
phase4_assert_no_warning_in_file /tmp/phase4-rehearsal1-build.log
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm test)
test -s "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts"
! rg -n "skeleton: capability guard wiring baseline" "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts"
(cd "$PHASE4_REPO_ROOT/frontend" && BASE_URL="$PHASE4_CANARY_WEB_BASE_URL" pnpm e2e -- --grep "@authz-minimal" --project=chromium)
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
2. **T-15 分钟**：网关切维护模式 + 业务写冻结（阻断外部写流量）
3. **T-10 分钟**：双重冻结核验（DB 活跃写事务清零 + 写接口拒绝探针）
4. **T-0**：执行冻结后的 `final backup`（RPO=0 前提）
5. **T+0~T+30**：执行 `set_not_null` 迁移
6. **T+30~T+60**：执行 Step 3 后对账（11 项）
7. **T+60~T+90**：执行 `drop_legacy` 迁移
8. **T+90~T+120**：执行 Step 4 后对账、权限校验、关键冒烟
9. **T+120~T+130**：放流前决策（满足放流前门禁后，先恢复 Canary/灰度流量）
10. **T+130~T+140**：Canary 观察 10 分钟（采集性能与 5xx）
11. **T+140~T+150**：全量放流决策（Canary PASS 则全量，FAIL 则回滚/回切）
12. **T+150 以后**：发布后首轮观察

> [!WARNING]
> 任何阻断门禁失败，立即停止后续步骤并进入回滚路径。

### 4.1.1 写冻结核验（T-10 必执行）

```bash
phase4_psql -v ON_ERROR_STOP=1 -c "
DO \$\$
DECLARE
  active_write_txn integer;
BEGIN
  SELECT COUNT(*)
    INTO active_write_txn
  FROM pg_stat_activity
  WHERE datname = current_database()
    AND backend_type = 'client backend'
    AND pid <> pg_backend_pid()
    AND state <> 'idle'
    AND xact_start IS NOT NULL
    AND query IS NOT NULL
    AND query !~* 'pg_stat_activity'
    AND query ~* '(insert|update|delete|merge|copy|truncate|alter|create|drop)';

  RAISE NOTICE 'active_write_txn=%', active_write_txn;
  IF active_write_txn > 0 THEN
    RAISE EXCEPTION 'write freeze check failed: active_write_txn=%', active_write_txn;
  END IF;
END
\$\$;
"
```

### 4.1.2 写接口拒绝探针（T-10 必执行）

```bash
WRITE_HTTP_CODE=$(curl -sS -o /tmp/phase4-write-freeze-probe.body -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${PHASE4_WRITE_PROBE_TOKEN:?set PHASE4_WRITE_PROBE_TOKEN}" \
  "${PHASE4_WRITE_PROBE_URL:?set PHASE4_WRITE_PROBE_URL}")
echo "write_probe_http_code=${WRITE_HTTP_CODE}"
case "${WRITE_HTTP_CODE}" in
  423|429|503) ;;
  401|403)
    echo "Write probe rejected by auth; inconclusive for write-freeze verification" >&2
    exit 1
    ;;
  *)
    echo "Unexpected write probe status: ${WRITE_HTTP_CODE} (expected 423/429/503)" >&2
    exit 1
    ;;
esac
```

---

### 4.2 发布窗口硬门禁（放流前阻断项）

| 类别 | 检查项 | 通过标准 |
|---|---|---|
| DDL | 迁移执行成功 | Alembic 分段执行成功且无错误 |
| 数据 | 核心对账（前后分段） | `set_not_null` 后 `reconciliation` PASS，`drop_legacy` 后 `reconciliation` 兼容 PASS |
| 权限 | ABAC 主路径 | `admin/manager/user` 关键用例行为正确 |
| 协议 | `X-Authz-Stale` 契约 | 证据文档完整 + 样例可复现 |
| 写冻结 | 网关拒绝探针 + DB 活跃写核验 | 写接口返回维护拒绝态（423/429/503）；`401/403` 视为探针无效且阻断；且 `active_write_txn=0` |
| Step4 引用 | 删除对象运行时引用清零 | `rg` 清零门禁通过（覆盖类属性 + 实例属性形态，见 §4.3 Step 5.1） |
| 前端构建 | 构建零告警 | `pnpm build` 输出无 `warning/warn` |
| 前端质量 | 门禁与测试 | `pnpm check && pnpm test` 通过 |
| 最小权限 E2E | 最小权限拒绝链路 | 禁止 skeleton 占位；`@authz-minimal` 至少 2 条用例（allow + deny）；以 `BASE_URL=$PHASE4_CANARY_WEB_BASE_URL` 执行通过 |
| 删表链路 | 项目-权属关系 / 产权证权利人 | 目标回归测试通过（见 §6） |

### 4.2.1 性能与 5xx 的证据格式（必须留痕）

- 新建：`docs/release/evidence/phase4-performance-gate.md`
- 新建：`docs/release/evidence/phase4-error-rate-gate.md`
- 两份证据均必须包含：
  - 数据来源（监控系统/网关日志/APM）
  - 查询表达式或统计脚本
  - 采样时间窗（开始/结束，精确到分钟）
  - 原始输出（截图或文本）
  - 标准结论行：`result: PASS|FAIL`
  - 结论与签字人

### 4.2.2 放流后 Canary 门禁（10 分钟观察窗）

- 仅在 §4.2 放流前阻断门禁全部通过且已恢复 Canary 流量后执行
- 阈值要求：
  - `p95_release <= p95_rehearsal * 1.30`（见 `phase4-performance-gate.md`）
  - 连续 10 分钟每分钟 `5xx_rate <= 1%`（见 `phase4-error-rate-gate.md`）
- 任一失败：禁止扩大流量，立即执行回滚/回切并留痕

### 4.2.3 最小权限 E2E 内容基线（阻断项）

- 用例文件必须存在，且禁止保留 skeleton 占位描述
- 至少 2 条断言用例：1) 授权角色 allow；2) 非授权角色 deny（403 或等价拒绝）
- 发布窗口执行必须显式指定 `BASE_URL=$PHASE4_CANARY_WEB_BASE_URL`，禁止默认本地 URL 通过

---

### 4.3 窗口执行命令清单（标准口径）

```bash
set -euo pipefail

: "${PHASE4_REPO_ROOT:?set PHASE4_REPO_ROOT}"
: "${PHASE4_DB_DSN:?set PHASE4_DB_DSN}"
: "${PHASE4_RESTORE_DSN:?set PHASE4_RESTORE_DSN}"
: "${PHASE4_API_BASE_URL:?set PHASE4_API_BASE_URL}"
: "${PHASE4_CANARY_WEB_BASE_URL:?set PHASE4_CANARY_WEB_BASE_URL}"
: "${PHASE4_FINAL_BACKUP_REF:?set PHASE4_FINAL_BACKUP_REF}"
: "${PHASE4_BACKUP_DIR:?set PHASE4_BACKUP_DIR}"
: "${PHASE4_TENANT_NOT_NULL_DECISION:?set PHASE4_TENANT_NOT_NULL_DECISION (A or B)}"
: "${PHASE4_WRITE_PROBE_URL:?set PHASE4_WRITE_PROBE_URL}"
: "${PHASE4_WRITE_PROBE_TOKEN:?set PHASE4_WRITE_PROBE_TOKEN}"
: "${DATABASE_URL:?set DATABASE_URL (derive from PHASE4_DB_DSN in §2.4)}"
: "${P4_NON_ADMIN_TOKEN:?set P4_NON_ADMIN_TOKEN}"
: "${PHASE4_STEP4_LEGACY_SYMBOL_PATTERN:=Asset\\.organization_id|assets\\.organization_id|asset\\.organization_id|Asset\\.ownership_id|assets\\.ownership_id|asset\\.ownership_id|Asset\\.management_entity|assets\\.management_entity|asset\\.management_entity|Asset\\.project_id|assets\\.project_id|asset\\.project_id|Project\\.organization_id|projects\\.organization_id|project\\.organization_id|Project\\.management_entity|projects\\.management_entity|project\\.management_entity|Project\\.ownership_entity|projects\\.ownership_entity|project\\.ownership_entity|RentContract\\.ownership_id|rent_contracts\\.ownership_id|rent_contract\\.ownership_id|RentLedger\\.ownership_id|rent_ledger\\.ownership_id|ledger\\.ownership_id|PropertyCertificate\\.organization_id|property_certificates\\.organization_id|property_certificate\\.organization_id|Role\\.organization_id|roles\\.organization_id|role\\.organization_id|entity\\.organization_id|contract\\.ownership_id}"
: "${PHASE4_STEP4_LEGACY_TABLE_PATTERN:=project_ownership_relations|property_owners|property_certificate_owners|abac_policy_subjects}"
type phase4_psql >/dev/null 2>&1 || phase4_psql() { psql "$PHASE4_DB_DSN" "$@"; }
type phase4_assert_no_match >/dev/null 2>&1 || phase4_assert_no_match() {
  local pattern="$1"; shift
  rg -n "$pattern" "$@"
  local rg_exit=$?
  if [ "$rg_exit" -eq 0 ]; then
    echo "Unexpected match for pattern: $pattern" >&2
    return 1
  fi
  [ "$rg_exit" -eq 1 ] || { echo "rg execution failed with exit=${rg_exit} for pattern: $pattern" >&2; return "$rg_exit"; }
}
type phase4_assert_no_warning_in_file >/dev/null 2>&1 || phase4_assert_no_warning_in_file() {
  local file="$1"
  local warning_pattern="${2:-(^|[^a-z])(warning|warn)([^a-z]|$)}"
  [ -r "$file" ] || { echo "Log file not readable: $file" >&2; return 2; }
  grep -Eiq "$warning_pattern" "$file"
  local grep_exit=$?
  if [ "$grep_exit" -eq 0 ]; then
    echo "Warning token detected in $file" >&2
    return 1
  fi
  [ "$grep_exit" -eq 1 ] || { echo "grep execution failed with exit=${grep_exit} for file: $file" >&2; return "$grep_exit"; }
}
type phase4_assert_sql_equals >/dev/null 2>&1 || phase4_assert_sql_equals() {
  local label="$1"
  local sql="$2"
  local expected="$3"
  local actual
  actual="$(phase4_psql -Atqc "$sql")"
  echo "${label}=${actual} (expected=${expected})"
  [ "$actual" = "$expected" ] || { echo "Gate failed: ${label} expected=${expected} actual=${actual}" >&2; return 1; }
}
type phase4_assert_sql_ge >/dev/null 2>&1 || phase4_assert_sql_ge() {
  local label="$1"
  local sql="$2"
  local expected="$3"
  local actual
  actual="$(phase4_psql -Atqc "$sql")"
  case "$actual" in ''|*[!0-9]*) echo "Gate failed: ${label} non-numeric actual=${actual}" >&2; return 2 ;; esac
  echo "${label}=${actual} (expected>=${expected})"
  [ "$actual" -ge "$expected" ] || { echo "Gate failed: ${label} expected>=${expected} actual=${actual}" >&2; return 1; }
}
case "$PHASE4_TENANT_NOT_NULL_DECISION" in A|B) ;; *) echo "PHASE4_TENANT_NOT_NULL_DECISION must be A or B" >&2; exit 1 ;; esac
if [ "$PHASE4_CANARY_WEB_BASE_URL" = "http://127.0.0.1:5173" ]; then
  echo "PHASE4_CANARY_WEB_BASE_URL is default local URL; override to real canary URL in release window" >&2
  exit 1
fi

# 0) 窗口前预检（连通性与版本）
phase4_psql -v ON_ERROR_STOP=1 -c "SELECT now() AS db_now;"
(cd "$PHASE4_REPO_ROOT/backend" && DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic current)

# 1) 进入维护模式 + 写冻结（由网关/平台执行并留痕）

# 2) 冻结核验（活跃写事务必须为 0）
phase4_psql -v ON_ERROR_STOP=1 -c "
DO \$\$
DECLARE
  active_write_txn integer;
BEGIN
  SELECT COUNT(*)
    INTO active_write_txn
  FROM pg_stat_activity
  WHERE datname = current_database()
    AND backend_type = 'client backend'
    AND pid <> pg_backend_pid()
    AND state <> 'idle'
    AND xact_start IS NOT NULL
    AND query IS NOT NULL
    AND query !~* 'pg_stat_activity'
    AND query ~* '(insert|update|delete|merge|copy|truncate|alter|create|drop)';

  RAISE NOTICE 'active_write_txn=%', active_write_txn;
  IF active_write_txn > 0 THEN
    RAISE EXCEPTION 'write freeze check failed: active_write_txn=%', active_write_txn;
  END IF;
END
\$\$;
"

# 2.1) 写接口拒绝探针（网关/应用层必须拒绝写入）
WRITE_HTTP_CODE=$(curl -sS -o /tmp/phase4-write-freeze-probe.body -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${PHASE4_WRITE_PROBE_TOKEN}" \
  "$PHASE4_WRITE_PROBE_URL")
echo "write_probe_http_code=${WRITE_HTTP_CODE}"
case "${WRITE_HTTP_CODE}" in
  423|429|503) ;;
  401|403)
    echo "Write probe rejected by auth; inconclusive for write-freeze verification" >&2
    exit 1
    ;;
  *)
    echo "Unexpected write probe status: ${WRITE_HTTP_CODE} (expected 423/429/503)" >&2
    exit 1
    ;;
esac

# 2.2) tenant 决策硬门禁（A/B 与 null_count 绑定）
TENANT_NULL_COUNT=$(phase4_psql -Atqc "SELECT COUNT(*) FROM rent_contracts WHERE tenant_party_id IS NULL OR tenant_party_id=''")
echo "tenant_decision=${PHASE4_TENANT_NOT_NULL_DECISION} tenant_null_count=${TENANT_NULL_COUNT}"
if [ "$PHASE4_TENANT_NOT_NULL_DECISION" = "A" ]; then
  test "$TENANT_NULL_COUNT" = "0"
fi

# 3) 冻结后最终备份（RPO=0 依赖此步骤）
mkdir -p "$PHASE4_BACKUP_DIR"
FINAL_BACKUP_FILE="$PHASE4_BACKUP_DIR/pre_phase4_final_$(date +%Y%m%d_%H%M).dump"
pg_dump "$PHASE4_DB_DSN" --format=custom --file "$FINAL_BACKUP_FILE"
pg_restore --list "$FINAL_BACKUP_FILE" > /tmp/phase4-backup-manifest.txt
mkdir -p "$(dirname "$PHASE4_FINAL_BACKUP_REF")"
{
  echo "# Phase4 Final Backup Reference"
  echo "generated_at_utc: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "final_backup_file: $FINAL_BACKUP_FILE"
  echo "database_name: $(phase4_psql -Atqc 'SELECT current_database();')"
} > "$PHASE4_FINAL_BACKUP_REF"

# 4) 迁移分段执行
(cd "$PHASE4_REPO_ROOT/backend" && PHASE4_TENANT_NOT_NULL_DECISION="$PHASE4_TENANT_NOT_NULL_DECISION" DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_set_party_columns_not_null)

# 5) Step 3 后对账（11 项）
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode release-pre-drop)

# 5.1) Step 4 删除对象运行时引用清零（未通过直接 No-Go）
phase4_assert_no_match "$PHASE4_STEP4_LEGACY_SYMBOL_PATTERN" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"
phase4_assert_no_match "$PHASE4_STEP4_LEGACY_TABLE_PATTERN" \
  "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"

# 6) 执行 Step 4（删旧列/旧表）
(cd "$PHASE4_REPO_ROOT/backend" && DATABASE_URL="$DATABASE_URL" ./.venv/bin/alembic upgrade 20260301_phase4_drop_legacy_party_columns)

# 7) Step 4 后对账（必须兼容删旧列后 schema）
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode release-post-drop)

# 8) 后端快速回归（迁移+权限+删表链路最小集）
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest --no-cov tests/unit/migration tests/unit/middleware/test_authz_dependency.py tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q)

# 9) X-Authz-Stale 契约校验（拒绝样例必须携带响应头）
HTTP_CODE=$(curl -sS -D /tmp/phase4-authz-deny.headers -o /tmp/phase4-authz-deny.body -w "%{http_code}" \
  -H "Authorization: Bearer $P4_NON_ADMIN_TOKEN" \
  "${PHASE4_API_BASE_URL}/api/v1/system/backup/stats")
echo "http_code=${HTTP_CODE}"
test "${HTTP_CODE}" = "401" || test "${HTTP_CODE}" = "403"
grep -in "x-authz-stale" /tmp/phase4-authz-deny.headers

# 10) 前端门禁 + 无 warning 构建 + 最小权限 E2E
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm check)
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm build 2>&1 | tee /tmp/phase4-release-build.log)
phase4_assert_no_warning_in_file /tmp/phase4-release-build.log
(cd "$PHASE4_REPO_ROOT/frontend" && pnpm test)
test -s "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts"
! rg -n "skeleton: capability guard wiring baseline" "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts"
AUTHZ_MINIMAL_CASE_COUNT=$(rg -n "test\\(" "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts" | wc -l | tr -d ' ')
echo "authz_minimal_case_count=${AUTHZ_MINIMAL_CASE_COUNT}"
test "${AUTHZ_MINIMAL_CASE_COUNT}" -ge 2
(cd "$PHASE4_REPO_ROOT/frontend" && BASE_URL="$PHASE4_CANARY_WEB_BASE_URL" pnpm e2e -- --grep "@authz-minimal" --project=chromium)

# 11) 条件放流（Canary）后指标门禁留痕（10 分钟采样）
# 由发布平台先恢复 Canary 流量，再生成两份证据并判定 PASS/FAIL
test -s docs/release/evidence/phase4-performance-gate.md
test -s docs/release/evidence/phase4-error-rate-gate.md
grep -Eq '^result:[[:space:]]*PASS$' docs/release/evidence/phase4-performance-gate.md
grep -Eq '^result:[[:space:]]*PASS$' docs/release/evidence/phase4-error-rate-gate.md
```

---

### 4.4 放流决策规则（分段）

**4.4.1 放流前决策（进入 Canary）必须全部满足**:

1. §4.2 放流前阻断门禁全部通过
2. 回滚材料完整且可执行
3. 业务负责人 + 技术负责人共同签字

**4.4.2 Canary 转全量决策必须全部满足**:

1. `phase4-performance-gate.md` 结论为 PASS
2. `phase4-error-rate-gate.md` 结论为 PASS
3. 采样窗口 >= 10 分钟，原始证据可复现

**任一不满足**:

- 禁止扩大流量（不得全量放流）
- 立即进入回滚/回切路径
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
| 后端 lint | `(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/ruff check .)` | 无 error |
| 后端测试 | `(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest -m "not slow" -q)` | 无新增 failure |
| Step 3 后对账 | `(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode release-pre-drop)` | PASS |
| Step 4 后对账 | `(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$DATABASE_URL" --mode release-post-drop)` | PASS |
| Step4 引用清零 | `phase4_assert_no_match "$PHASE4_STEP4_LEGACY_SYMBOL_PATTERN" "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas" && phase4_assert_no_match "$PHASE4_STEP4_LEGACY_TABLE_PATTERN" "$PHASE4_REPO_ROOT/backend/src/api" "$PHASE4_REPO_ROOT/backend/src/services" "$PHASE4_REPO_ROOT/backend/src/crud" "$PHASE4_REPO_ROOT/backend/src/middleware" "$PHASE4_REPO_ROOT/backend/src/models" "$PHASE4_REPO_ROOT/backend/src/schemas"` | PASS（无命中，覆盖类属性+实例属性，且无命令异常） |
| 删表链路回归 | `(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/pytest --no-cov tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q)` | PASS |
| `X-Authz-Stale` | `rg -n "X-Authz-Stale" backend/src` + 拒绝样例请求 | 契约可复现 |
| 前端门禁 | `(cd "$PHASE4_REPO_ROOT/frontend" && pnpm check)` | PASS |
| 前端构建 | `(cd "$PHASE4_REPO_ROOT/frontend" && pnpm build 2>&1 | tee /tmp/build.log) && phase4_assert_no_warning_in_file /tmp/build.log` | PASS（无 warning，且无命令异常） |
| 前端测试 | `(cd "$PHASE4_REPO_ROOT/frontend" && pnpm test)` | PASS |
| 最小权限 E2E | `test -s "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts" && ! rg -n "skeleton: capability guard wiring baseline" "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts" && test "$(rg -n "test\\(" "$PHASE4_REPO_ROOT/frontend/tests/e2e/auth/authz-minimal.spec.ts" | wc -l | tr -d " ")" -ge 2 && (cd "$PHASE4_REPO_ROOT/frontend" && BASE_URL="$PHASE4_CANARY_WEB_BASE_URL" pnpm e2e -- --grep "@authz-minimal" --project=chromium)` | PASS（非 skeleton，>=2 用例，Canary URL 执行通过） |
| 写冻结核验 | `phase4_psql -v ON_ERROR_STOP=1 -c "<4.1.1 DO block>"` | active_write_txn=0 |
| 写冻结探针 | `curl -X POST -H "Authorization: Bearer $PHASE4_WRITE_PROBE_TOKEN" "$PHASE4_WRITE_PROBE_URL"` | HTTP 为 423/429/503（`401/403` 视为探针无效） |
| tenant 决策绑定 | `test "$PHASE4_TENANT_NOT_NULL_DECISION" = "A" || test "$PHASE4_TENANT_NOT_NULL_DECISION" = "B"` | A/B 明确；A 时 `tenant_null_count=0` |
| 性能门禁留痕（Canary 后） | `test -s docs/release/evidence/phase4-performance-gate.md && grep -Eq '^result:[[:space:]]*PASS$' docs/release/evidence/phase4-performance-gate.md` | PASS（`p95_release <= p95_rehearsal * 1.30`） |
| 5xx 门禁留痕（Canary 后） | `test -s docs/release/evidence/phase4-error-rate-gate.md && grep -Eq '^result:[[:space:]]*PASS$' docs/release/evidence/phase4-error-rate-gate.md` | PASS（连续 10 分钟每分钟 `5xx_rate <= 1%`） |
| final backup 引用留痕 | `test -s "$PHASE4_FINAL_BACKUP_REF"` | PASS |

---

## 7. 回滚预案（窗口级）

### 7.1 触发条件

1. 任一阻断门禁失败且不可在窗口内修复
2. 关键数据对账 FAIL
3. 核心功能冒烟失败并影响主业务路径

### 7.2 回滚步骤

1. 维持维护模式（不放流）
2. 应用回滚到窗口前发布包（`pre_phase4_release`）
3. 使用冻结后 `final backup` 执行 DB 恢复
4. 恢复后执行最小对账（核心表行数 + `reconciliation --mode rollback-verify`）
5. 冒烟通过后恢复流量

**参考命令**

```bash
# 1) 应用回滚（示例：通过发布平台回滚到 pre_phase4_release）
# deploy rollback --release pre_phase4_release

# 2) 数据恢复
: "${PHASE4_RESTORE_DATABASE_URL:?set PHASE4_RESTORE_DATABASE_URL (derive from PHASE4_RESTORE_DSN in §2.4)}"
FINAL_BACKUP_FILE="$(awk -F': ' '/^final_backup_file:/{print $2}' "$PHASE4_FINAL_BACKUP_REF")"
test -n "$FINAL_BACKUP_FILE"
test -r "$FINAL_BACKUP_FILE"
pg_restore --clean --if-exists --no-owner --no-privileges --dbname "$PHASE4_RESTORE_DSN" "$FINAL_BACKUP_FILE"

# 3) 最小对账
(cd "$PHASE4_REPO_ROOT/backend" && ./.venv/bin/python -m src.scripts.migration.party_migration.reconciliation --database-url "$PHASE4_RESTORE_DATABASE_URL" --mode rollback-verify)
```

### 7.3 RTO / RPO 目标

- **RTO**: <= 维护窗口时长的 50%
- **RPO**: 目标 0（前提：完成写冻结后 `final backup`；若写冻结失败则直接 No-Go，不得迁移）

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
| 权限语义漂移 | 高 | 发布前后执行最小权限 E2E + 角色 spot-check + `X-Authz-Stale` 核验 |
| 外部调用方未适配 | 中 | 签收未完成即阻断发布 |
| 前端构建 warning 演化为故障 | 中 | 构建“无 warning”硬门禁 |

---

## 11. Phase 4 Exit Criteria（最终验收）

1. P4a / P4b / P4c 全部完成且证据齐全
2. Step 3/4（收紧约束 + 旧列删除）在生产窗口执行成功
3. 对账、权限、性能、冒烟全部通过
4. 回滚预案执行性经演练验证
5. `X-Authz-Stale` 契约与 D9 验签证据齐备
6. 形成 Phase 4 Exit 结论文档并经双负责人签字

---

## 12. 文档历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-03-01 | 2.0 | 审阅修订：1) 将 P4a-2 的 No-Go 查询改为自动断言（`phase4_assert_sql_equals` / `phase4_assert_sql_ge`），避免“仅查询无阻断”导致误放流；2) 扩展 Step4 引用清零 regex，补齐实例属性形态（如 `role.organization_id` / `entity.organization_id`）的漏检风险；3) 修复演练 #1 与流程不一致问题，补齐 `set_not_null -> drop_legacy` 全链路命令；4) 新增 `@authz-minimal` 强度门禁（禁止 skeleton、至少 2 用例）；5) 发布窗口 E2E 强制 `BASE_URL=$PHASE4_CANARY_WEB_BASE_URL` 且禁止默认本地 URL。 |
| 2026-03-01 | 1.9 | 审阅修订：1) 修复 `phase4_assert_no_match` / `phase4_assert_no_warning_in_file` 的退出码判定实现，避免 `if <cmd>; then ...; fi` 导致命令异常被误判通过；2) 将写冻结探针口径收紧为“必须命中维护拒绝态（423/429/503）”，并将 `PHASE4_WRITE_PROBE_TOKEN` 升级为必填，`401/403` 明确判定为探针无效且阻断；3) 补齐 Step4 运行时引用清零模式，`PHASE4_STEP4_LEGACY_TABLE_PATTERN` 新增 `abac_policy_subjects`；4) Canary 指标门禁从“文件存在”升级为“存在且 `result: PASS`”强校验，并统一到窗口命令与验证矩阵。 |
| 2026-03-01 | 1.8 | 审阅修订：1) 修复门禁命令“假通过”风险：用 `phase4_assert_no_match` / `phase4_assert_no_warning_in_file` 取代 `! rg` / `! grep`，严格区分“无命中”与“命令异常”；2) 将 Step4 运行时引用清零 regex 升级为单源常量并补齐覆盖（新增 `Asset.management_entity`、`RentLedger.ownership_id`、`Project.management_entity`、`Project.ownership_entity`、`PropertyCertificate.organization_id`，并补齐类属性/表字段双形态匹配）；3) 将放流决策拆分为“放流前阻断门禁”与“Canary 10 分钟指标门禁”，消除性能/5xx 与放流时序冲突。 |
| 2026-03-01 | 1.7 | 审阅修订：1) 新增 Step4 删除对象“运行时引用清零”硬门禁，并在 P4a-2 / P4a-3 / P4b / 验证矩阵统一落地（失败即 No-Go）；2) 修复 Entry 与产物清单口径冲突：`phase4-authz-stale-contract.md`、`phase4-external-signoff.md` 改为“前置并持续更新”；3) 在环境变量单源补齐 `P4_NON_ADMIN_TOKEN` 必填定义，消除标准命令执行时缺参中断；4) 将项目-权属关系与产权证权利人链路回归测试纳入窗口阻断门禁。 |
| 2026-03-01 | 1.6 | 审阅修订：1) 强制 `reconciliation` 兼容 Step4 删旧列后 schema，并将窗口对账拆为 `release-pre-drop` + `release-post-drop` 两次执行，消除“先删列后对账失败”风险；2) 补齐写冻结双重核验（`pg_stat_activity` + 写接口拒绝探针）；3) 将 `PHASE4_TENANT_NOT_NULL_DECISION` 升级为必填并在窗口命令中与 `tenant_null_count` 强绑定，防止误收紧；4) 将 `@authz-minimal` E2E 纳入演练与窗口标准命令，消除门禁与执行清单不一致。 |
| 2026-03-01 | 1.5 | DSN 执行口径收敛修订：1) `PHASE4_DB_DSN` / `PHASE4_RESTORE_DSN` 明确仅接受 `postgresql://`，用于 `psql/pg_dump/pg_restore` 直连；2) 删除对 `postgresql+psycopg://` 的输入兼容分支，避免工具链错误解析导致误连本地默认库；3) `DATABASE_URL` / `PHASE4_RESTORE_DATABASE_URL` 统一由 libpq DSN 派生，继续供 Alembic/`reconciliation` 使用。 |
| 2026-03-01 | 1.4 | 发布窗口执行安全修订：1) 新增 `DATABASE_URL` / `PHASE4_RESTORE_DATABASE_URL` 派生规则，要求 Alembic/`reconciliation` 与 `PHASE4_DB_DSN`/`PHASE4_RESTORE_DSN` 单源一致，消除跨库执行风险；2) 将 `final backup` 文件落盘改为 `PHASE4_BACKUP_DIR` 绝对路径，并在回滚前新增 `test -r` 可读性校验，降低跨会话/跨目录恢复失败概率；3) 删除 `database_dsn_masked` 输出，改为 `database_name` 留痕，避免凭证泄露到证据文档。 |
| 2026-03-01 | 1.3 | 全面复核二次硬化：1) `X-Authz-Stale` 校验改为 `PHASE4_API_BASE_URL` 参数化，移除环境硬编码；2) 增加写冻结核验 SQL（`active_write_txn=0`）并纳入窗口命令与验证矩阵；3) 增加 `phase4-final-backup-reference.md` 并在窗口中落盘 `FINAL_BACKUP_FILE`，回滚命令改为从引用文件读取；4) 发布证据清单补齐性能/5xx/final backup 三类文件，修复产物清单与门禁不一致。 |
| 2026-03-01 | 1.2 | 执行口径彻底硬化：1) 修复跨目录命令可执行性（统一 `PHASE4_REPO_ROOT` + 子 shell）；2) 以 `phase4_psql()` 取代字符串命令变量，消除引号分词歧义；3) No-Go 查询改为 `ON_ERROR_STOP` 且去除 `|| true` 误判路径；4) 发布窗口改为“写冻结后 final backup”以满足 RPO=0 前提；5) 将性能/5xx 门禁量化并强制证据文件；6) 回滚路径改为发布包回滚 + final backup 恢复。 |
| 2026-03-01 | 1.1 | 彻底复核修订：补齐 `X-Authz-Stale` 门禁与证据位点；补齐 Step3/Step4 字段级清单；将备份/恢复命令改为可执行口径；将“前端构建无 warning”升级为硬门禁；新增 `tenant_party_id` A/B 冻结决策。 |
| 2026-03-01 | 1.0 | 新建 P4 完整实施计划（P4a/P4b/P4c、门禁、回滚、RACI、里程碑、Exit 标准）。 |
