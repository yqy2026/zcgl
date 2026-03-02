# Phase 4a Rehearsal #1（2026-03-01）

## 结论
- result: `PASS`（针对本地可执行范围）
- scope: `P4a-3 迁移代码/兼容性/最小回归`

## 执行记录
1. Phase4 迁移与对账代码落地
- 新增 `20260301_phase4_set_party_columns_not_null.py`
- 新增 `20260301_phase4_drop_legacy_party_columns.py`
- `reconciliation.py` 已兼容 Step4 删列后 schema

2. 测试环境修复
- `tests/conftest.py` 与 `tests/unit/conftest.py` 默认注入 `PHASE4_TENANT_NOT_NULL_DECISION=B`（允许显式覆盖）
- 修复 Step4 删表顺序：先删 `property_certificate_owners` 再删 `property_owners`

3. 最小回归命令
- 命令：
  `cd backend && ./.venv/bin/pytest --no-cov tests/unit/migration tests/unit/middleware/test_authz_dependency.py tests/unit/crud/test_property_certificate.py tests/unit/api/v1/test_property_certificate.py tests/unit/schemas/test_project_schema.py -q`
- 结果：`78 passed`

4. Step4 引用清零门禁
- symbol pattern 扫描：`exit=1`（无命中）
- table pattern 扫描：`exit=1`（无命中）

5. 前端门禁（本地）
- `pnpm check`：`PASS`
- `pnpm build`：`PASS`
- `grep -Eiq '(^|[^a-z])(warning|warn)([^a-z]|$)' /tmp/phase4-release-build.log`：`exit=1`（无 warning token）
- `pnpm test`：`PASS`
- `BASE_URL=http://127.0.0.1:5173 pnpm e2e --grep "@authz-minimal" --project=chromium`：`2 passed`

## 后续补充（2026-03-02）
- 本地真实 DB 已完成迁移到 `20260301_phase4_drop_legacy_party_columns (head)`。
- post-drop 对账已执行并通过：`reconciliation --mode phase4-local-post-drop`。
- 写事务冻结前置检查（active write txn）结果：`0`。
