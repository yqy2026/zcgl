# Phase 3b 预检就绪证据（2026-02-27）

## 元信息
- 日期：`2026-02-27`
- 责任人：`phase3-preflight`
- release-id：`phase3-preflight-20260227`
- 范围：`P3b Entry hard gates + ABAC seed matrix reconciliation`

## 结论
1. `frontend` 类型门禁阻断已解除：`tsgo` 已可执行，`pnpm check` 全通过。
2. `party.read` 非管理员绑定阻断已解除：`abac_role_policies` 已回填，`non_admin_party_read_binding_count=6`。
3. `ABAC seed` 与“主路由权限词表”已对齐可开工；扩展词条缺口已登记到 P3d 阶段处置。
4. P3b Entry API 实证已补齐（2026-02-28）：非管理员会话下 `GET /api/v1/auth/me/capabilities` 返回含 `party.read`，`GET /api/v1/parties?search=` 可按关键词过滤返回。

## 执行记录
### 1) 前端类型门禁恢复
- 命令：`cd frontend && pnpm install`
- 结果：`node_modules/.bin/tsgo` 存在
- 验证：`cd frontend && pnpm check` 通过（含 `type-check` / `type-check:e2e` / authz 门禁）

### 2) ABAC 角色策略绑定回填
- 命令（dry-run）：  
  `cd backend && ./.venv/bin/python -m src.scripts.migration.party_migration.backfill_role_policies --database-url "$DATABASE_URL" --dry-run`
- 输出：`[DRY-RUN] backfill_role_policies scanned=7 updated=7 skipped=0`
- 命令（exec）：  
  `cd backend && ./.venv/bin/python -m src.scripts.migration.party_migration.backfill_role_policies --database-url "$DATABASE_URL"`
- 输出：`[EXEC] backfill_role_policies scanned=7 updated=7 skipped=0`

### 3) SQL 门禁快照（回填后）
- `abac_role_policies_count=7`
- `non_admin_party_read_binding_count=6`
- `users_with_non_admin_party_read=4`
- `parties_total=0`
- `parties_active=0`

## ABAC 覆盖矩阵实证（2026-02-27）
### 满足项（非管理员可达）
- `party.read=6`
- `project.read=1`
- `rent_contract.read=6`
- `property_certificate.read=6`
- `asset.create=3`
- `asset.delete=3`

### 缺失项（规则未种入）
- `project.list: rules_total=0, role_bindings=0`
- `ledger.read: rules_total=0, role_bindings=0`
- `asset.export: rules_total=0, role_bindings=0`

## 兼容映射冻结（P3b -> P3d）
1. `project` 列表/可达性按 `project.read` 判定（当前主路由即该口径）。
2. `/rental/ledger` 按 `rent_contract.read` 判定（当前主路由即该口径）。
3. `asset.export` 不作为 P3b 阻断项，保留到 P3d 按按钮级能力补齐；若后端暂不提供 `asset.export`，沿用 admin-only 临时豁免并带 `TODO(P4)`。

## 代码位点
- 路由权限：`frontend/src/constants/routes.ts`
- 项目路由：`project.* -> project.read`
- 台账路由：`/rental/ledger -> rent_contract.read`

## API 联调补证（2026-02-28）
### 4) 非管理员 capabilities spot-check（P3b Entry 必做）
- 会话：非管理员账号 `manager` 角色（`is_admin=false`）
- 请求：`GET /api/v1/auth/me/capabilities`
- 结果：`HTTP 200`
- 关键断言：
  - 返回包含 `resource=party` 且 `actions` 含 `read`
  - `perspectives=["manager"]`
  - `data_scope.manager_party_ids` 非空

### 5) `/api/v1/parties?search=` 过滤实证（P3b 硬门禁）
- 请求 A：`GET /api/v1/parties?search=P3B&limit=20` → `HTTP 200`，命中 3 条（`code` 包含 `P3B`）
- 请求 B：`GET /api/v1/parties?search=甲&limit=20` → `HTTP 200`，命中 1 条（仅 `P3B演示主体-甲`）
- 判定：`search` 参数已在真实鉴权会话下生效，不依赖“全量拉取 + 前端过滤”。

### 6) 根因备注（避免门禁误判）
- `user` 角色当前绑定策略包为 `no_data_access`（`deny`），其 capabilities 预期为空，不应作为 P3b 的“非管理员 `party.read` 能力”验收账号。
- P3b Entry 的“非管理员 API spot-check”应使用具备 allow 策略包的非管理员角色（如 `manager`/`viewer`）执行。
