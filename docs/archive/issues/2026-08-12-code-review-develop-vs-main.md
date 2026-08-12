# 代码审查报告：develop vs main（双轴，复核修订版）

- **原始基线（fixed point）**：`main` = `a37fb65e816ca8adbfa6ae2ba833ab6a57f2f952`
- **原始对比范围**：`git diff main...HEAD`（三点 diff，相对 merge-base）
- **原始规模**：36 个提交，187 个文件，+8,623 / -2,286
- **方法**：
  - **Standards 轴**：对照 `AGENTS.md` / `CLAUDE.md` 的成文规则，并区分分层违规、正确性缺陷和预防性门禁缺口。
  - **Spec 轴**：以 `docs/prd.md`、`docs/specs/api-contract.md`、`docs/specs/domain-model.md`、`docs/traceability/requirements-trace.md` 为契约。
- **复核说明**：2026-08-12 对原报告逐项追踪实际调用链、测试与验收记录后修订。下文先保留评审时事实；整改状态和最终验证证据在实现完成后补充，避免把“已识别”写成“已解决”。

---

## Standards

### 成文标准违规

1. **`AssetMultiSelect` 使用本地 state/effect 管理服务器数据。**
   - 证据：`frontend/src/components/Common/AssetMultiSelect.tsx` 通过 `useState`、`useEffect` 和手工 request ID 调用 `assetService.searchAssets`。
   - 违反：`AGENTS.md` 明确要求服务器数据使用 React Query，禁止 `useState + useEffect` 取数。
   - 影响：项目/关键词切换时需要自行处理 debounce、竞态、loading/error 和旧响应污染，当前实现未完整满足这些边界。

2. **项目视角业务决策落在 API 层。**
   - 证据：`backend/src/api/v1/assets/project.py::_build_project_party_filter` 在端点层解释 `view_mode` 并构造 owner/manager `PartyFilter`。
   - 违反：项目后端分层要求业务逻辑位于 `services/`，`DataScopeContext -> PartyFilter` 转换应有唯一服务边界。
   - 这不是 Fowler 的 Feature Envy 判断，而是仓库成文分层规则的直接违规。

### 正确性与预防性缺口

3. **显式 `view_mode` 可回退并扩大范围。**
   - `_build_project_party_filter` 在请求 owner/manager 视角但对应 Party ID 为空时，不返回空范围或拒绝请求，而是回退到原始 scope。
   - `DataScopeContext` 又用“Party ID 为空”同时表达管理员无限制和受限用户无可用主体，`party_scope` 将两者都转换为 `None`（unrestricted）。
   - 结果：不可用视角没有稳定 403，受限空范围可能变成另一视角或无限制范围；应显式区分 unrestricted，并 fail closed。

4. **资产详情产权证采用固定 1000 条客户端过滤。**
   - 证据：`frontend/src/pages/Assets/AssetDetailPage.tsx` 请求 `listCertificates({ skip: 0, limit: 1000 })` 后按 `asset_ids` 过滤。
   - 这是分页阈值正确性缺陷，不是 Shotgun Surgery：第 1001 条以后的关联证书会被静默漏掉，且全量拉取扩大传输和前端处理成本。

5. **query-param drift gate 未覆盖新增的一对一查询契约。**
   - `scripts/check_query_param_drift.py` 原映射只覆盖项目列表，未覆盖 project tenants、project analytics 和 property-certificate list。
   - 解析器原本也无法证明 `API_ENDPOINTS.PROJECT.TENANTS(projectId)` 一类动态端点常量与 FastAPI `/{project_id}/tenants` 为同一路径。
   - 影响：`view_mode`、`asset_id` 等查询参数未来漂移时，`make check` 无法阻断。

6. **一次性 seed 与特定环境主体耦合。**
   - 证据：`backend/scripts/maintenance/seed_projects_from_assets.py` 原先硬编码 Party UUID，并在脚本中直接查询 Asset/ProjectAsset ORM。
   - 这是环境耦合和 CRUD 分层问题，不是 Primitive Obsession。脚本应要求显式 CLI Party ID，并通过 CRUD 编排数据访问。

### 已核验合规

- 后端路由注册：产权证模块经 `route_registry.register_router()` 自注册，聚合模块仅 import 触发注册，无双公共入口。
- Pydantic v2：合同 schema 的 `field_validator(mode="before")` 只做枚举规范化，不触发关系懒加载。
- 项目列表批量补充资产数和管理方名称经 CRUD 完成，未引入 N+1。
- 前端未新增禁止的深层相对导入；抽查的严格布尔表达式符合项目规则。

---

## Spec

### 缺失 / 部分实现

1. **产权证 holder/asset owner 不一致 warning 链路缺失。**
   - SSOT：REQ-AST-005 要求产权证权利人与关联资产当前主产权主体不一致时，为对应资产生成 warning 级数据质量风险。
   - 评审时实现只有证书基础卡片，没有服务端当前 holder 投影、逐证书/资产 mismatch 计算和稳定 warning identity；资产详情、产权证详情、项目风险均无该风险数据。
   - `证照信息不完整` 是另一独立缺口，本次整改不应虚报为已完成。

### 错误实现

2. **合同导入 Party 选择器错误限定 `legal_entity`。**
   - `PDFImportPage::approvedPartyFetcher` 原先硬编码 `party_type: 'legal_entity'`，四个合同主体选择器共用该 fetcher。
   - REQ-PTY-001 与合同相对方规则允许已审核的法人和自然人 Party；因此这是确定缺陷，不再标为“疑似、待产品确认”。

3. **资产选择器发送的 `project_id` 被后端静默忽略。**
   - 前端 `assetService.searchAssets` 发送 `project_id`，但评审时 `GET /api/v1/assets` 未声明该 Query 参数，FastAPI 因而忽略它。
   - 结果：看似项目内的资产选择器实际可返回其他项目资产。正确契约应由 API -> service -> CRUD 显式传递，并在分页和 count 前按当前有效 `ProjectAsset.valid_to IS NULL` 过滤。

4. **project tenants/analytics 的 `view_mode` 未由统一 scope dependency 消费。**
   - 端点声明了 `view_mode`，但 scope middleware 原先只对 analytics/statistics 路径读取该参数，项目端点仍得到混合 context，再由 API helper 二次解释。
   - 双绑定 tenants 未选择视角时没有统一稳定 400；不可用视角没有稳定 403；analytics 是否抑制客户指标依赖原始 query，而不是最终解析后的 scope。

### 复核排除的原报告误报

- **`payment_cycle` 未透传：部分误报。** 合同确认通过通用 `actions[]` 传输字段，后端 candidate-review 白名单接受 `payment_cycle`，workflow 将其映射到 `ContractCreate`——「未透传」这一原始诊断确属误报。但复核只追到传输层，未验证 service 落库：`contract_group_service.add_contract_to_group` 曾把 `payment_cycle` 写进 `Contract` 主表构造 dict（该列属于 `LeaseContractDetail`），真实 ORM 构造 `Contract(**data)` 直接 `TypeError` 崩溃（PDF 确认创建与直接创建均为生产崩溃路径；单元测试因 mock `contract_crud.create` 而未暴露）。该崩溃缺陷已修复（见整改状态「最终双轴复核后的追加修复」）。
- **seed 属 scope creep：误报。** `docs/issues/2026-08-09-mvp-g1-acceptance-dryrun.md` §3.2 明确记录 G1 验收环境缺少项目实体的阻断、补数方案和幂等验证。seed 有真实任务来源；只需做低优先级运维加固。

### 已核验一致

- 分析口径（#73）：移除净收益、重命名承租转租租金收入、`operating_result` 双口径及 `metrics_version=req-rnt-006-v1` 与 SSOT 一致。
- Party `review_status` 服务端过滤（#82）与 API 契约一致。
- 顶层产权证模块读取经过用户 Party scope 解析，评审时不存在无条件全量旁路。

---

## 汇总

- **Standards 轴**：6 项发现，包括 2 项成文标准违规、2 项行为正确性缺陷、1 项门禁覆盖缺口、1 项运维边界问题。
- **Spec 轴**：4 项有效发现，包括 1 项缺失链路和 3 项错误实现。
- **排除误报**：`payment_cycle` 未透传、seed scope creep 共 2 项。
- **最高优先级**：project `view_mode` 的 fail-open 数据范围风险、资产选择器 `project_id` 被静默忽略、产权证 mismatch warning 缺失。

## 整改状态

> 本分支 `fix/code-review-remediation-20260812`（固定点 `b9a09230`）于 2026-08-12 完成整改。10 项评审发现大部分已修复；最终双轴复核后又发现并修复一处合同创建崩溃（`payment_cycle` 写入错误 ORM 实体）。以下先列整改事实，再列验证证据，最后列未通过门禁与合并准备度。

### 逐项整改结果

**Standards 轴（6 项）**

| # | 发现 | 修复与代码证据 |
|---|------|----------------|
| 1 | `AssetMultiSelect` 用 state/effect 管理服务器数据 | 迁移 React Query：`frontend/src/components/Common/AssetMultiSelect.tsx` 用 `useQuery`，query key 含 scope/项目/trim 关键词，300ms debounce、无项目不发请求、错误可观察、项目切换取消旧 debounce 并清空可见搜索词（受控 `searchValue`）；测试 `AssetMultiSelect.test.tsx` 覆盖初始/无项目/连续输入/项目切换/迟到响应/错误 10 例 |
| 2 | 项目视角业务决策落在 API 层 | 删除 `api/v1/assets/project.py::_build_project_party_filter`；`services/party_scope.py::build_party_filter_from_scope_context` 成为 `DataScopeContext -> PartyFilter` 唯一转换点；`test_project_layering.py` 增加路由模块不得调用 `project_crud.` / 不得重定义 helper 的守卫 |
| 3 | 显式 `view_mode` 可回退并扩大范围 | `DataScopeContext` 增加显式 `is_unrestricted`（管理员 true，受限空范围 false）；`party_scope` 对受限空范围返回空 `PartyFilter`（fail closed），对未知 mode 报错，绝不回退；双视角 tenants 未选择时统一 400（`middleware/data_scope.py`），不可用视角 403，项目不在范围 404；`test_perspective_context.py` 新增 128 行覆盖 |
| 4 | 资产详情 1000 条客户端过滤 | `GET /api/v1/property-certificates` 新增可选非空 `asset_id`（`api/v1/assets/property_certificate.py` Query 校验），CRUD 在分页/count 前用 `property_cert_assets` 关联 `EXISTS` 与 Party scope 取交集；资产详情改为服务端过滤（`AssetDetailPage.tsx`），`test_property_certificate_list.py` + `test_crud/test_property_certificate.py` 断言 `EXISTS` 在分页前 |
| 5 | query-param drift gate 未覆盖新契约 | gate 增加 project tenants、project analytics、property certificate list 三个一对一契约；支持动态端点常量 `API_ENDPOINTS.PROJECT.TENANTS(projectId)` 解析，并新增 `_parse_backend_registered_route_path` 以 AST 证明 `/projects` 聚合 prefix（拒绝 router 别名重绑定、要求唯一静态 prefix）；`test_check_query_param_drift.py` 76+ 用例 |
| 6 | seed 与特定环境主体耦合 | `seed_projects_from_assets.py` 的硬编码 UUID 改为必填 CLI `--manager-party-id`（UUID 校验）；脚本数据访问收敛到 service/CRUD；`ProjectService.create_project(commit=False)` + 末尾一次 `db.commit()`，失败回滚不提交部分项目；`test_seed_projects_from_assets.py` 覆盖延迟提交与链接失败不回滚 |

**Spec 轴（4 项）**

| # | 发现 | 修复与代码证据 |
|---|------|----------------|
| 1 | 产权证 holder/owner mismatch 链路缺失 | 新增 `services/property_certificate/risks.py`：只实现 `holder_owner_mismatch`；当前 holder 为有效期内 `OWNER|CO_OWNER`（`ISSUER|CUSTODIAN` 不参与），半开区间 `valid_from <= as_of < valid_to`；逐证书/资产独立比较 `Asset.owner_party_id`，空源只记诊断不伪造；稳定 ID `property-certificate:{certificate_id}:asset:{asset_id}:holder_owner_mismatch`；CRUD `selectinload` 批量加载；项目风险按当前 `ProjectAsset` 批量取证书复用同一计算器；`ProjectRiskItem` 增加 `asset_id/property_certificate_id/warning_code`，总风险数含 warning、经营模式计数仍只统计有 `contract_relation_id` 的项；资产详情只展示当前资产 warning，证书详情展示全部关联资产 warning |
| 2 | Party 选择器限定 `legal_entity` | `PDFImportPage.tsx` 删除 `party_type: 'legal_entity'`，保留 `review_status=approved` + `status=active`；回归 fixture 改为自然人主体直接编码"客户端不得重新引入法人过滤"；项目切换清空已选 `assetIds` 防跨项目提交 |
| 3 | 资产选择器 `project_id` 被静默忽略 | `GET /api/v1/assets` 显式声明 `project_id`（非空校验），API → service → CRUD 显式传递，CRUD 用当前 `ProjectAsset.valid_to IS NULL` 的关联 `EXISTS` 在分页/count 前过滤；前端远程搜索发送真实 `page_size:20`；`test_asset.py`/`test_query_builder.py`/`test_asset_service.py` 覆盖未知/不可见关联返回空集 |
| 4 | project tenants/analytics `view_mode` 未由统一 dependency 消费 | `require_data_scope_context` 支持 `accepts_view_mode/query_modes/require_single_perspective` 声明；项目端点不再二次解释 query；`证照信息不完整` 保持独立未完成项，未虚报 |

**排除误报**：`payment_cycle` 为**部分误报**（传输层未透传是误报，但 service 落库层存在真实崩溃缺陷，已修复，见下）；seed scope creep（G1 验收 dry-run 有真实任务来源）按上文记录排除。

### 测试证据

- **TDD red→green**：范围失败模式（400/403/404）、迟到响应隔离、SQL `EXISTS` 分页前位置、半开 holder 有效期边界（`valid_to == as_of` 不算当前）、项目仅投影 warning、稳定 ID、结构化风险字段、空范围查询跳过、同文件 params 类型绑定、聚合 prefix 证明、死依赖工厂删除后的行为等价，均先红后绿。
- **定向**：后端 235 项（project layering / certificate list / alembic logging / query-drift / crud / seed / risks / response mapper / service）+ 收敛后 119 项；前端复核套件 52 项（7 文件）+ 证书服务 58 项；query-drift 77 项。
- **全量**：后端 unit **4145 passed / 23 skipped / 358 deselected**（覆盖率 77.23%）；前端 **186 文件 / 2186 passed**；前端生产构建 **5502 modules** 成功。
- **门禁**：MyPy `Success: no issues found in 388 source files`；Bandit `No issues identified`（86,323 行）；changed-file Ruff lint + format 全部通过；`make check-query-param-drift` **OK (7 explicit contracts, zero drift)**；docs-lint 10 项 PASS；document runtime ok；后端导入烟测 `import ok`（`REDIS_ENABLED=false` 测试配置）；`git diff --check` 通过。

### Alembic 日志根因修复

全量后端套件一度出现依赖测试顺序的告警抑制：in-process Alembic 运行期间 `logging.config.fileConfig()` 默认 `disable_existing_loggers=True` 关闭了测试收集期创建的既有 logger。修复：`backend/alembic/env.py` 显式 `disable_existing_loggers=False`，并新增 AST 守卫测试 `test_alembic_logging_config.py` 防止回退。

### 最终双轴复核（2026-08-12，latest worktree）

- **Standards 轴**：无成文标准违规；5 个判断性发现全部收敛——客户指标抑制规则收敛为 service 单点推导（`services/project/service.py` 依据 `filter_mode == "any"`，API 不再重复计算 `scope_mode == "all" and not is_unrestricted`，`test_project_layering.py` 断言不再传 `suppress_customer_metrics`）、删除 `middleware/data_scope.py` 零引用死工厂 `require_data_scope_context`、端点 `view_mode` 死赋值改为 OpenAPI 契约注释、`crud/property_certificate.py` 提取 `_apply_party_scope/_apply_asset_scope` 消除重复 EXISTS、`get_multi` 补 `order_by(PropertyCertificate.id)` 确定性分页（新增 SQL 断言测试）。
- **Spec 轴**：计划 7 节全部符合，无 scope creep；1 个 LOW 收敛——drift gate 的 `_has_mapped_params_type_binding` 不再对 service/type 同文件无条件放行，`PropertyCertificateListParams` 移入 `frontend/src/types/propertyCertificate.ts` 并由 service `import type` 绑定，仓库契约映射同步指向类型文件（此前 2 次 Spec reviewer 因 provider 过载失败，未计为通过；最终窄化复核完成）。
- 复核期间 3 次 sub-agent 因 provider 过载失败，未作为通过结论计入；上述结论来自成功完成的复核。

### 最终双轴复核后的追加修复（payment_cycle 落库崩溃）

- 复核结论发布后，人工复核指出 `payment_cycle` 的「未透传」误报判定只追到了 `actions[]` 传输层：`contract_group_service.py` 原第 1259 行把 `payment_cycle` 写进 `Contract` 主表构造 dict，而该列属于 `LeaseContractDetail`；`crud/contract.py::Contract(**data)` 真实构造必然 `TypeError`。PDF 确认创建（`contract_extraction_workflow.py` 提取 `payment_cycle` → `ContractCreate`）与直接创建（`ContractCreate` 带顶层 `payment_cycle`）都走此路径，均为生产崩溃；单元测试因成功路径 mock `contract_crud.create` 而全部通过，未暴露真实构造。
- **修复（TDD）**：red 测试锁定「`data` 不含 `payment_cycle`、`lease_detail_data["payment_cycle"]` 等于传入值」；CRUD 层新增真实构造防御测试（`Contract(**data)` 含 `payment_cycle` 必抛 `TypeError`）与合法字段真实构造回归测试。实现：service 从主表 dict 移除该键，并在 `lease_detail_data` 存在时把顶层 `payment_cycle` 合并进租约明细（无明细时无处承载，忽略不崩溃）。验证：合同 service/CRUD/文档 workflow 213 项通过；全量后端 unit 重跑通过；ruff/mypy 通过。
- **遗留语义**：无 `lease_detail` 的合同（非 LEASE 或 LEASE 无月租金）不承载付款周期；账务层（`ledger_service_v2`）本就只从 `lease_detail.payment_cycle` 读取，行为一致。

### 已知未通过门禁（未涉及本次改动，但属于当前分支合并阻塞）

以下问题早于固定点 `b9a09230`，且本次整改未改动相关文件；但它们多数位于原始 `main...develop` 差异内，**不能作为 `develop` 合并 `main` 的放行依据**。**2026-08-12 更新：13 项代码类阻塞已由 `fix/gate-blockers-20260812`（#87）逐项修复**：

- `make check` 的两个 Ruff `I001`：`backend/src/api/v1/__init__.py`、`backend/tests/unit/services/document/test_contract_extraction_workflow.py` — ✅ `ruff --fix` 收敛 import 排序，`ruff check` 通过。
- UI guard 4 处模块化 px：`DashboardPage.module.css` ×3、`ProjectDetailPage.module.css` ×1 — ✅ 替换为等价 token/rem（`12px`→`var(--spacing-md)`、`24px`→`var(--spacing-xl)`、`1200px`→`75rem`），`scan-style-px --fail-on-module` EXIT 0。
- E2E TypeScript 6 处：`tests/e2e/user/import-guardrails.spec.ts`、`tests/e2e/user/property-certificate-import-success.spec.ts` — ✅ 根因修复：`Request` 未导入解析到全局 fetch `Request`（`method`/`url` 是属性非方法，且连带 `page.on/off` 重载解析到 `'worker'` 事件），改显式 `import type { Request } from '@playwright/test'`；`confirmPayload` 初始化 `= null` 且仅在 `page.route` 闭包内赋值导致流收窄为 `null`，`?.actions` 报 `never`，用显式 `as` 初始值拓宽；`tsc -p tsconfig.e2e.json` 通过。均为类型层修复，运行行为不变。
- 前端 lint 1 警告：`ProjectList.tsx:49` 未使用 `isRelationActive` — ✅ 删除死代码。
- 环境（非代码，遗留）：本地 Redis 不可用（门禁以 `REDIS_ENABLED=false` 验证）、Docker Desktop API 不可用、后端与测试种子环境缺失 → 浏览器黑盒与受影响 E2E 运行验证未完成。

### 结论

评审发现的 10 项有效问题中，**大部分已完成整改并有测试证据**；`payment_cycle` 的「未透传」诊断属误报，但复核后追加发现其落库崩溃缺陷并已修复（修复后全量后端重跑通过）。REQ-AST-005 仍为 `部分实现`：「证照信息不完整」warning 未实现，已由开放 issue **#85**（`ready-for-agent`）承接，明确判定规则、展示范围与验收测试待收口。

**2026-08-12 二次更新（#87 收口）**：上节 13 项代码类门禁阻塞已全部修复，`make check` 链上 lint ×2 / UI guard / type-check（含 E2E TS）/ 后端测试 / 前端测试 / 生产构建 / document-runtime 全部通过，`backend-import`（`REDIS_ENABLED=false` 文档化本地验证模式）、`check-query-param-drift`（7 contracts zero drift）、`docs-lint`（10 PASS）通过。剩余阻塞仅为环境类：本地 Redis 未运行、Docker Desktop API 不可用、后端与测试种子环境缺失 → 浏览器黑盒与 E2E 运行验证未完成，需环境就绪后补跑。代码与门禁层面本报告不再构成 `develop` 合并 `main` 的障碍；环境类验证完成前仍建议保留该结论的谨慎性。
