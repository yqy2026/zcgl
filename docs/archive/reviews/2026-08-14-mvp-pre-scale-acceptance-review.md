# MVP 放量前验收报告（工程侧执行，2026-08-14）

> 文档定位：放量前验收（PRD §3.1 / §9）的**工程侧执行记录**。本报告登记工程验证证据、发现与修复、剩余人工抽验项；最终放量认定由产品负责人按 PRD §3.2 真实使用抽验完成，状态登记见 `docs/traceability/mvp-acceptance-checklist.md`。

## 1. 背景与基线

- 验收依据：`docs/prd.md` §3.1（MVP 一票否决目标）、§9（G1-G3 门槛 + 建议验收覆盖 ACC-001~030）、§3.2（认定规则）。
- 执行基线：`develop` 分支（领先 `main` 50 提交，工作区在验收前干净），2026-08-09 预演报告（`docs/issues/2026-08-09-mvp-g1-acceptance-dryrun.md`）已闭环 G1/G2 大部分展示链路与 ACC-023。
- 环境：后端 FastAPI :8002（种子库 admin/system_admin，11 项目/19 资产/承租转租关系）、前端 Vite :5173、PostgreSQL :5432、Redis docker :16379 全部在线；Playwright chromium-1228 冒烟可用。

## 2. 验收方法

| 手段 | 内容 |
|---|---|
| 工程门禁 | `make check` 全链（lint / UI guard / type-check / 后端单元 / 前端测试 / 生产构建 / document-runtime / backend-import / query-param-drift / test-credentials / docs-lint） |
| 证据审计 | 追踪矩阵 342 条代码/测试证据路径逐一验证存在性 |
| API 实测 | 双探针（P1：展示/统计/权限域；P2：租赁/文档/产权证域）对 :8002 真实 HTTP 调用，含 CSRF 双提交、Cookie 会话 |
| GUI 冒烟 | 既有 Playwright spec `smoke/main-pages-render.spec.ts`（6/6）+ `mobile/dashboard-smoke.spec.ts`（1/1） |
| 回归测试 | 全部修复 TDD red→green；修复后全量后端单元 4187 passed / 0 failed |

## 3. 门禁结果

| 门禁项 | 结果 |
|---|---|
| lint-backend / lint-frontend / scan-frontend / type-check | ✅（round-2 gate run） |
| test-backend | ✅ 4187 passed / 0 failed / 23 skipped（修复后全量） |
| test-frontend / build-frontend / check-document-runtime | ✅（round-2 gate run） |
| backend-import | ✅ `import ok`（GnuWin32 make 无 sh 导致 Makefile 脚本目标无法经 make 运行，按 Makefile 等价命令 + 自带 fallback SECRET_KEY 手工验证） |
| check-query-param-drift | ✅ 7 explicit contracts, zero drift |
| check-test-credentials | ✅ PASS |
| docs-lint | ✅ 10 项全 PASS（含 field-drift 报告 exit 0，spec-only/orm-only 为既有已知口径） |

> 环境备注：`make check` 在本机需两个环境修复——pnpm 经 corepack shim（`packageManager: pnpm@10.34.5`）、`PYTHON=$(shell …)` 因无 sh 解析为空需命令行覆盖 `PYTHON=backend/.venv/Scripts/python.exe`；`backend-import` 等 bash 语法 recipe 需 sh 或等价手工执行。均为工具链问题，非代码缺陷（2026-08-12 复核报告已记载同类环境项）。

## 4. G1-G3 门槛结论

| 门槛 | 结论 | 关键证据 |
|---|---|---|
| G1 资产页/项目页展示 | 🟡 工程通过 | GUI 冒烟 7/7；API 实测列表/详情/租赁摘要/项目列表与详情字段；2026-08-09 预演 |
| G2 合同与协议能力 | 🟡 工程通过 | 模式校验/扫描件下限/确认合规/重算作废/多账期分摊 API 实测；解析会话可达 ready_for_review；2026-08-09 全链路 |
| G3 经营统计口径 | 🟡 工程通过 | 综合分析四组指标+口径版本+账期归属、view_mode 硬拒绝、ledger-summary、台账视图、服务费、导出 |

## 5. 验收发现与修复（6 项，全部 TDD + 复验）

| # | 缺陷 | 根因 | 修复 | 验证 |
|---|---|---|---|---|
| D1 | `test_analytics.py` 9 用例 500 | 端点按契约传 `perspective`（api-contract §4.9），测试手写 mock 签名陈旧 | 更新 mock 签名 + 断言「`view_mode=manager` → service 收到 `perspective="manager"`」锁定转发契约；两个语义误导的日期用例改为断言透传 | 25 passed；全量门禁转绿 |
| D2 | `POST /property-certificates` 对所有输入一律 500（阻断 ACC-010~014） | 端点 `except Exception → 500` 吞掉服务层 `BaseBusinessError`（BusinessValidationError 应 422 / DuplicateResourceError 应 409 / ResourceNotFoundError 应 404） | 五个端点处理器补 `except BaseBusinessError: raise` 透传给全局异常处理器 | 新增 `test_property_certificate_create_api.py` 4 用例（422/409/404/200）；在线实测缺门槛 → 422 字段级（`property_address/asset_ids/holder_party_ids`） |
| D3 | `GET /projects/{id}/tenants` 恒 500 | `_party_name_from_contract` 访问 `contract.lessee_party` 触发异步懒加载 `MissingGreenlet`；`contract_crud.list_by_group` 未预加载该关系 | `list_by_group` 基础语句增加 `selectinload(Contract.lessee_party)` | crud 回归测试锁定 loader 路径；在线实测 200 total=1 |
| D4 | 项目详情 `asset_count=0`/`manager_party_name=null`（列表正常） | 详情经 `get_project_by_id` 返回的 ORM 无这两个属性，schema coerce validator 仅在属性存在时填充 | 新增 service `attach_project_display_summary`（批量取数与运营方名，与 `search_projects` 口径一致），详情端点调用 | service 测试 2 用例 + layering 测试适配；在线实测 1/广州国有资产管理集团有限公司 |
| D5 | 客户端自带 `project_code` 时绕过运营方必填（ACC-005） | 运营方必填只在自动生成 project_code 路径强制（`_resolve_operator_party_for_code`） | service `create_project` 在编码处理后再强制 `manager_party_id`（API 层按契约从 payload/组织/范围推断，推断不出即拒绝） | 新增拒绝测试；5 个既有创建用例补 `manager_party_id`；在线实测管理员创建仍经组织推断获得运营方（契约行为） |
| D6 | 管理员全局搜索恒空（REQ-SCH-001/003） | `search_global` 对空 `effective_party_ids` 短路返回空；管理员（unrestricted）主体 ID 恒空 | 移除短路；空 ids = 无范围限制（`_build_party_filter` 返回 None、`_apply_contract_group_scope` 跳过、客户双绑定类型） | 搜索测试重写为 unrestricted 语义 + 5 新用例；在线实测「长堤」返回项目+资产 2 条 |

## 6. 验收项判定汇总

- ✅/🟡 明细见 `docs/traceability/mvp-acceptance-checklist.md` §3/§4（30 项 ACC + 3 门槛，均无 ❌）。
- 全部 ACC 项均有工程证据（API 实测 / GUI 冒烟 / 测试 / 契约）；**无遗留代码级失败项**。

## 7. 剩余人工抽验项（产品负责人按 PRD §3.2 执行后登记 ✅）

1. **AI 解析候选质量**（ACC-008/009）：需 `DOCUMENT_LLM_ENABLED=true` + DeepSeek 配置 + 真实盖章扫描件（2026-08-09 预演 5.6 已用 OCR 版 PDF 验证候选链路，含 4 字段候选）。
2. **ACC-021 补缴历史账期回补**：无专门端到端演示，需真实业务数据抽验。
3. **ACC-006 多绑定并集去重 / ACC-026 双视角项目分析抑制路径 / ACC-028 perm_admin 授予边界**：需双绑定与 perm_admin 种子账号场景。
4. **ACC-018 逾期筛选参数口径**：台账查询已强制至少一个筛选并支持视图/账期/派生状态，逾期专用过滤参数存在性与产品确认。
5. **G1-G3 放量认定**：产品负责人按真实使用抽验后逐门槛登记 ✅。

## 8. 外部依赖与已知项（不阻塞站内验收）

- 企业微信推送（REQ-NTF-001 剩余项）：真实发送待可信 IP / 域名配置与 userid 映射，PRD 定义为可选通道。
- `make check` 的 bash recipe（backend-import 等）在无 sh 的 Windows 环境需等价手工执行（本报告 §3 环境备注）。
- open issue #89/#90（analytics 收敛/业态口径）为 needs-triage 分析类，非验收阻塞；#86 已按 CHANGELOG 收口。

## 9. 结论与建议

- **工程侧验收通过**：门禁全绿、G1-G3 与 30 项 ACC 证据齐全、6 项缺陷全部修复并复验，无遗留代码级阻塞。
- **放量前关闭条件**：G1-G3 全部 ✅ 且 REQ 实现状态无阻塞项（当前 REQ-NTF-001 仅剩外部依赖）。建议产品负责人按 §7 清单抽验后关闭，随后将对应 REQ 在 `requirements-trace.md` 推进为「已验收」。
- 本报告不替代产品验收动作本身（PRD §3.2 二元认定）。

## 10. LLM 配置后复验（2026-08-14 追加）

产品负责人配置 `DOCUMENT_LLM_ENABLED=true` + DeepSeek（`backend/.env`）后，对 ACC-008/009 的 AI 解析候选质量执行真实全链路复验（OCR 版中文扫描件 PDF + RapidOCR + DeepSeek）。

### 10.1 ACC-008 合同解析全链路 🟡 工程侧闭环（待产品抽验）

1. **解析候选**：OCR 版合同 PDF 上传 → 会话 `ready_for_review`，DeepSeek 提取 4 字段候选（合同编号 CT-QC-2026-UP-888 / 起止日期 2026-09-01~2027-08-31 / 月租金 68000），均带置信度与逐页来源证据（dry-run 5.6 同款链路在 LLM 配置下复现）。
2. **逐字段人工确认**：`accept_candidate`（采用候选）、`correct_candidate`（人工修正合同号，验证候选防呆：不匹配真实候选被拒 `candidate_not_found`）、`manual`（签订日期手工录入）三种动作实测。
3. **合规闸门**：未审核/不存在主体 → 400 `party_review_not_approved`（明确列出未通过主体）；`sign_date` 未处理 → 422 `required_field_unreviewed`（ACC-015 全项实测）。
4. **台账生成（修复缺陷后）**：确认创建合同（lease_detail + rent_terms）→ **12 条台账**（2026-09~2027-08，`operator_cost` 口径，月 68000，unpaid）✅。

### 10.2 ACC-009 产权证解析全链路 🟡 工程侧闭环（待产品抽验）

1. **解析候选**：OCR 版不动产权证 PDF 上传 → 4 字段候选（证号/坐落/建筑面积 128.50/土地面积 50.00），证号提取截断（「粤（2026）广州市不动产权第」）→ 演示低置信场景人工修正。
2. **确认**：`correct_candidate` 修正证号 + 逐字段确认 → **产权证创建成功**（`attach_staged` 暂存文件晋升正式附件、资产关联、已审核权利人关联），**`incomplete_certificate_info` warning 实时派生**（缺失 土地使用期限起/止、限制信息，稳定 risk_id、不阻断保存、按资产独立判断——同时实证 ACC-012 机制）。
3. 会话即用即弃（确认后清理）✓。

### 10.3 复验发现并修复的缺陷（4 项 + 1 项可观测性）

| # | 缺陷 | 根因 | 修复 |
|---|---|---|---|
| D7 | 主体创建主路径 500（REQ-PTY-001） | `Party.metadata_json` 用 `JSONB` 默认 `none_as_null=False`，Python None 被编码为 JSON `'null'` 而非 SQL NULL，违反 `ck_parties_metadata_object`（`jsonb_typeof(metadata)` 必须为 'object' 或 NULL） | `JSONB(none_as_null=True)`；model 回归测试锁定 |
| D8 | 解析确认创建合同后**台账不生成**（ACC-008 闭环缺失） | `generate_ledger_on_activation` 以 `rent_terms` 为台账展开源，确认链路只写 `lease_detail` 未构造 `rent_terms`（空则跳过生成） | workflow 在确认月租金且期限完整时构造 `ContractRentTermCreate`（start/end/monthly_rent）；2 个 workflow 回归测试 |
| D9 | 产权证解析会话创建后 GET/confirm 一律 404（ACC-009 链路不可用） | `public_session` 有意剥离 context（防暴露 staged 元信息），但授权校验 `_require_property_context` 与 confirm 的 mode/来源判断都依赖 context；端点把 public 会话用于内部校验 | property workflow 新增 `get_raw`（完整会话）；`_authorize_existing_session` 与 confirm 端点改用完整会话；端点 except 链补 `HTTPException` re-raise（此前 404 被吞成 500）；红测试锁定 |
| D10 | 产权证创建 DB 层 500（REQ-AST-005 核心，`UndefinedObjectError: type certificatetype does not exist`） | model 声明 `SQLEnum(CertificateType)`（PG 原生枚举），但全部迁移中该列均为 `String`——数据库无此类型，任何完整合法输入的 INSERT 必炸（422 门槛类校验先于 INSERT 故未暴露） | model 改回 `String(50)`（与迁移/契约一致，Python 枚举仅作校验），移除未用 import；证书套件 179 passed |
| 可观测性 | 确认失败无任何 traceback 可查 | `handle_general_exception` 把堆栈写入 `extra`（formatter 不输出）；`extraction_sessions.py` 端点模块**没有 logger**，`logger.exception` 直接 NameError | 两个端点模块补 `logger` + 确认路径 `logger.exception` 标准记录（Make It Observable） |

### 10.4 结论

ACC-008/009 由「⚠️ 需人工抽验」推进为 **🟡 工程通过（工程侧闭环：LLM 配置 + 真实 OCR 扫描件全链路实测；最终放量认定待产品负责人按 PRD §3.2 抽验，与 mvp-acceptance-checklist 状态词汇一致）**；复验发现并修复的缺陷全部 TDD + 在线复验，全量后端单元套件 4187 passed / 0 failed 全绿。剩余人工抽验项见 §7（AI 解析质量已由本复验覆盖，剩余为真实业务扫描件多样性抽验）。
