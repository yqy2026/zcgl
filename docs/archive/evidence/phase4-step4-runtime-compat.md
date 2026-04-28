# Phase4 Step4 Runtime Compatibility（历史证据）

> Historical evidence. 本文件是 2026-03-01 Phase4 Step4 本地运行时兼容性证据快照，不作为当前安全基线。当前安全入口见 `docs/security/README.md`，当前需求、字段与 API 基线分别见 `docs/prd.md`、`docs/specs/domain-model.md`、`docs/specs/api-contract.md`。

## 扫描口径
- symbol_pattern: `Asset.organization_id|...|contract.ownership_id`
- table_pattern: `project_ownership_relations|property_owners|property_certificate_owners|abac_policy_subjects`

## 本地扫描结果（2026-03-01）
1. symbol_pattern
- command: `rg -n <pattern> backend/src/api backend/src/services backend/src/crud backend/src/middleware backend/src/models backend/src/schemas`
- result: `PASS`（exit=1，无命中）

2. table_pattern
- command: `rg -n <pattern> backend/src/api backend/src/services backend/src/crud backend/src/middleware backend/src/models backend/src/schemas`
- result: `PASS`（exit=1，无命中）

## 运行时补充回归（2026-03-01）
1. 集成阻断修复（party FK）
- 现象：`assets.owner_party_id` / `projects.manager_party_id` 在集成测试中触发 FK 失败（seed 仍按 legacy `organization_id`）。
- 修复：
  - `backend/tests/integration/api/test_phase2_statement_count.py` 改为先创建 `Party(external_ref=organization_id)`，并显式写入 `owner_party_id/manager_party_id`。
  - `backend/tests/integration/api/test_project_visibility_real.py` 改为 `Project.manager_party_id` 明确赋值，并补齐 `UserPartyBinding(manager)`。
2. 项目作用域过滤修复（Step4 删列后）
- 现象：`Project` 已删除 `organization_id` 后，`backend/src/crud/project.py` 仍走“按创建人组织”回退分支，导致 party scope 查询空集。
- 修复：`CRUDProject` 新增 `_supports_party_scope_columns/_apply_project_party_filter`，优先用 `QueryBuilder` 在 `manager_party_id` 上执行主体过滤，仅在无任何作用域列时才回退创建人分支。
3. 相关单测/集成测试适配
- `backend/tests/unit/api/v1/test_project.py` 新增组织->party 映射 fixture（`test_org_party`），移除 legacy 字段写法。
- 验证：
  - `cd backend && ./.venv/bin/pytest --no-cov -q tests/integration/api/test_phase2_statement_count.py tests/integration/api/test_project_visibility_real.py` -> `5 passed`
  - `cd backend && ./.venv/bin/pytest --no-cov -q tests/unit/api/v1/test_project.py tests/integration/api/test_phase2_statement_count.py tests/integration/api/test_project_visibility_real.py` -> `29 passed`
  - `cd backend && ./.venv/bin/ruff check src/crud/project.py tests/integration/api/test_phase2_statement_count.py tests/integration/api/test_project_visibility_real.py tests/unit/api/v1/test_project.py` -> `PASS`

## 结论
- result: `PASS`（本地代码层兼容门禁）
- note: 运行时窗口验证（真实流量/真实数据）仍需在 P4b 执行。
