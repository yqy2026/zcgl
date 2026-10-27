# 资产运营 v5 V2 租金、押金与委托管理费实施计划

> **状态**：🔄 实施就绪（§3 已按建议裁决并回写 SSOT；待 V1 合并后开工）
> **日期**：2026-10-27
> **需求**：REQ-LED-001、REQ-DEP-001、REQ-FEE-001（联动 REQ-CTR-001/002 的台账类筛选与付款计划展示）
> **产品基线**：`docs/prd.md` §6.5、`docs/specs/domain-model.md` §4.16–4.20 / §5.3–5.4 / §6.7–6.8、`docs/specs/api-contract.md` §5.7–5.9、`frontend/prototype/asset-ops-v5-handoff.md`（本月卡片 1–3、终端合同详情、台账、对账单）
> **前置条件**：V1（PR #95）已合并到 `develop`；目标环境数据切换方案已确认（见 `docs/archive/2026-10-26-asset-operations-v5-remaining-work-handoff.md`）

## 1. 目标与非目标

V2 在 V1 的“上游合同 → 资产单元 → 终端合同”事实链上，建立三条资金事实：

1. **租金义务与登记**：由合同租金阶段生成承租应付、转租应收、直签产权方应报到账三类义务；外部付款/到账以追加记录登记，支持部分完成、跨月结转与有原因撤销。
2. **押金待处理**：按合同生成押金约定，区分应收未收、应退未退、应收回三个方向，收退以追加记录登记。
3. **委托管理费对账**：基于产权方实际到账逐户试算，每产权方每月一张对账单，顺延未收户，盖章确认后锁定，更正走后继单。

V2 **不实现**：本月工作台（V5，仅保留义务/对账状态的可查询投影）、考核范围与报送（V3）、档案矩阵与导入（V4，盖章件与凭证复用 V1 已有 Attachment 存储，不建档案矩阵）、银行流水认领、发票、催收、付款指令（PRD §4.2 Out of Scope）。

## 2. 现有实现盘点与裁决

| 现有对象 | 实际状态 | V2 裁决 |
|---|---|---|
| `ContractRentSchedule`（V1） | 已存阶段起止、原定/实际月租、递增、免租、`payment_cycle`、`due_day` | 作为义务生成的唯一条款来源；不新增第二份租金条款表 |
| `UpstreamContract.payment_cycle` / `payment_day` | 合同级字段，与阶段级 `payment_cycle` / `due_day` 重复 | 以阶段级为准；合同级只作录入默认值与展示（待 §3 D-02 确认） |
| `UpstreamContract.management_fee_rate` | 委托管理协议比例 0–1 | 对账单与行级比例快照的来源 |
| `TerminalContract.rent_collector` / `deposit_*`、`UpstreamContract.deposit_amount` | 已签约定 | 押金约定来源；V2 不改 V1 写模型 |
| `ContractLifecycleEvent`（终止/退出/续签/撤销） | 追加事件，可按日重放 | 驱动未来义务作废与押金方向切换；义务服务只读事件，不改写事件 |
| `ContractLedgerEntry` / `OperationalPaymentFlow` / `ServiceFeeLedger`（旧 v4，`contract_group.py`） | 含可变 `paid_amount`、旧归属口径；V1 已断开路由 | **不复用、不双读、不迁移语义**；新表另起名，旧表随旧域清理删除 |
| `Attachment` 私有存储（V1 扫描件） | 已有统一文件校验与私有存储 | 付款凭证与盖章件复用；不建 `ArchiveDocument` 矩阵（V4） |
| `BusinessChangeEvent` | 领域模型已定义，尚未落地 | V2 首次落地：登记、撤销、顺延、确认、更正均写变更记录（V3 报送引用） |
| 前端 `/operations/ledger`（旧） | V1-4 已删除 | 新建 `/asset-operations/ledgers` 与 `/asset-operations/management-fees/:statement_id` |

## 3. 开工前裁决事项

以下是起草时 SSOT 未定义或互相冲突之处。2026-10-27 按下表裁决采纳，已回写 `docs/specs/domain-model.md` 与 `docs/specs/api-contract.md`（见“回写位置”）；实施以 SSOT 为准，本表只作决策追溯。

| ID | 问题 | 裁决 |
|---|---|---|
| D-01 | 金额舍入规则未定义（§4.19“按金额规则舍入”） | 统一 `Decimal.quantize(0.01, ROUND_HALF_UP)`；义务金额在生成时舍入，管理费按行舍入后求和（§6.8 已定先行后和） |
| D-02 | 合同级 `payment_cycle`/`payment_day` 与阶段级 `payment_cycle`/`due_day` 并存 | 义务只读阶段级；合同级字段仅作录入默认值，更新合同级字段不重算义务 |
| D-03 | `yearly` / `custom` 账期如何出义务未定义 | `yearly`：阶段起始月同月出一期（12 个月租金）；`custom`：V2 不自动生成，详情页提示“自定义账期需手工登记义务”，并新增手工义务端点（受 `asset_ops:write`，必须填依据说明） |
| D-04 | 起止日落在月中时是否按天折算 | 首末不足月按自然日折算：`月租 × 当月覆盖天数 / 当月天数`；季付/年付期内不足月同样折算后合并入该期 |
| D-05 | 免租 `free_rent_months` / `discount_amount` 如何落到各期 | 免租月数从阶段起始月顺延，对应月份义务金额为 0 且保留 `free_rent=true` 标记；`discount_amount` 只作核对展示，不二次扣减 |
| D-06 | “未锁定的未来义务”的锁定边界 | 义务在以下任一条件成立时锁定：存在任何登记记录（含已撤销）、账期早于当前业务月、已纳入非 `collecting` 对账单。租金阶段或期限变更只重建未锁定义务，已锁定义务保留原 `locked_source` |
| D-07 | 终止/退出/续签后多出的未来义务如何处理；状态机无“作废” | 义务新增追加式 `voided` 标记（`voided_by_event_id`），不删除行；生命周期事件撤销时恢复。`status` 增加派生值 `void`，不计入任何合计（需回写 §5.3） |
| D-08 | 押金收退记录无对象定义（§4.18 只有余额） | 新增 `DepositRecord`（结构与 `RentPaymentRecord` 同构：`collect` / `refund` / `recover` / `owner_reported` / `reversal`），`effective_amount` 由其派生；补错误码 `DEPOSIT_AMOUNT_EXCEEDS_REMAINING`、`DEPOSIT_RECORD_ALREADY_REVERSED` |
| D-09 | 押金约定何时生成、方向何时切换 | 终端合同确认时生成 `receivable`（向租户收，直签由产权方收、只登记报告）；终止生效后转 `refundable`（应退租户）。上游承租合同的押金由我方付给产权方，生效期内不进入“待处理”三类；退出或到期后生成 `recoverable`（应向产权方收回）。V2 不跟踪“本公司应付上游押金”的付款过程 |
| D-10 | 管理费对账单 `upstream_contract_id` 单值 vs “每产权方每月一张” | 一个产权方同时有多份委托管理协议时：对账单按产权方+月份唯一，`upstream_contract_id` 改为行级字段（`ManagementFeeStatementLine.upstream_contract_id`），单头保留 `upstream_contract_ids` 快照；行级比例各自快照 |
| D-11 | 产权方到账登记与对账单行是否两份事实 | 只有一份：到账登记为 `RentPaymentRecord(record_type=owner_reported_receipt)` 挂在 `owner_receipt_expected` 义务上；对账单在 `collecting` 时实时投影这些记录，`confirmed` 时把行写成快照。`owner-receipts` 端点内部委托租金登记服务 |
| D-12 | 顺延的判定时点与目标期间 | 对账月（N−1 月）的义务到当月最后一天仍未有足额到账的，由用户在对账单上“标记顺延”（原因必填），顺延到 N 月对账单；不自动顺延。部分到账时已到部分计入本期、余额顺延 |
| D-13 | 盖章件上传与确认的权限 | 均为 `asset_ops:write`（PRD 视为资金登记）；不引入 `asset_ops:archive` 依赖 |
| D-14 | 超额登记的“独立规则扩展” | V2 不做；保持 409 `PAYMENT_AMOUNT_EXCEEDS_REMAINING` 失败关闭 |

## 4. 失败测试清单（先写）

| 测试 ID | 预期失败条件 | 守护的意图 |
|---|---|---|
| V2-T01 | 季付阶段在非季初月份产生义务，或月付金额未按递增阶段叠加 | 义务只按条款与账期生成（PRD §6.5） |
| V2-T02 | 月中起租未折算，或免租月仍产生应付 | 首末月与免租口径确定（D-04/D-05） |
| V2-T03 | 修改租金阶段后，已有登记或已过账期的义务金额被改写 | 历史义务锁定，只重建未锁定义务（D-06） |
| V2-T04 | 一笔义务分两次登记结清后撤销第二笔，状态不是 `partial` 或原记录被修改/删除 | 追加式登记与撤销（ACC-V5-006 / G2） |
| V2-T05 | 登记金额超出剩余义务被接受，或重复撤销同一记录成功 | 409 `PAYMENT_AMOUNT_EXCEEDS_REMAINING` / `PAYMENT_RECORD_ALREADY_REVERSED` |
| V2-T06 | 同幂等键同请求生成第二条记录；同键不同金额未返回 `IDEMPOTENCY_CONFLICT` | 重试不重复写入 |
| V2-T07 | 往月未完成义务在切换查询月份后从“未完成”列表消失 | 跨月结转（PRD §6.5） |
| V2-T08 | 终端终止后，生效日之后的义务仍计入应收合计；撤销终止后未恢复 | 生命周期驱动作废且可逆（D-07） |
| V2-T09 | 直签终端合同出现“抵扣押金”或本公司收取押金操作 | 直签押金只登记产权方报告（api-contract §5.8） |
| V2-T10 | 押金三类方向混算，或撤销押金记录后余额未恢复 | REQ-DEP-001 方向与追加记录 |
| V2-T11 | 月末未收户未标记顺延就阻塞当月对账单进入 `pending_stamp`，或顺延户计入本期基数 | 顺延不阻塞已具备条件的对账（PRD §6.5、§6.8） |
| V2-T12 | 已确认对账单在修改合同比例、租户名称或补登到账后金额变化 | 确认锁定（ACC-V5-007 / G2） |
| V2-T13 | 无盖章件即可确认；更正时覆盖原单而非生成后继、原单未转 `superseded` | 对账状态机 §5.4 |
| V2-T14 | 无 Party 范围时台账/押金/对账单返回空列表；范围外合同的义务可被登记 | 403 失败关闭，写操作服务端解析范围（REQ-AUTH-002） |
| V2-T15 | 账期/逾期按 UTC 日期判断，`Asia/Shanghai` 跨日边界月份归属错误 | 业务时区口径 |
| V2-T16 | 台账页把 403 当 empty，或把刷新错误清空成空矩阵 | 四态不混淆（ACC-V5-010） |
| V2-T17 | 台账矩阵合计与逐条义务明细合计不一致 | 派生页面数字一致（G1） |

## 5. 文件级实施顺序

每个切片按 V1 惯例走“失败测试 → 模型/迁移 → CRUD → 服务 → API → 前端”纵向红绿循环，单独提交，切片完成后做一次双轴复核（标准轴 + 规格轴）。整个 V2 按以下三个 PR 交付，不合成一个大 PR。

### PR-A：租金义务与登记（REQ-LED-001）

**V2-0 SSOT 回写**（2026-10-27 已回写，见 §9）
- 按 §3 裁决更新 `docs/specs/domain-model.md`（§4.16–4.18 字段、`void` 状态、`DepositRecord`、对账单行级上游、舍入规则）与 `docs/specs/api-contract.md`（手工义务端点、押金错误码、`rent_unpaid` / `deposit_unsettled` 筛选）。只改规格，不改代码。

**V2-1 领域与持久化**
- `backend/src/models/asset_ledger.py`：`RentLedgerEntry`（`entry_type`、`contract_kind`、`contract_id`、`period`、`due_date`、`due_amount`、`free_rent`、`locked_source` JSONB、`voided_by_event_id`、`version`）、`RentPaymentRecord`（追加式，`reverses_record_id` 部分唯一索引保证一笔只能撤销一次）、`BusinessChangeEvent`。
- `backend/alembic/versions/2026xxxx_asset_operations_v5_rent_ledger.py`：建表；`(contract_kind, contract_id, entry_type, period)` 在未作废行上唯一；金额 `Numeric(14,2)` 且 CHECK 非负；不建旧表外键。
- `backend/src/schemas/asset_ledger.py`：写模型 `extra=forbid`，拒绝 `status` / `effective_paid_amount` / `remaining_amount` 等派生字段（`DERIVED_FIELD_NOT_WRITABLE`）。
- `backend/src/models/__init__.py` 显式导出。

**V2-2 义务生成（纯函数优先）**
- `backend/src/services/asset_operations/rent_obligation_rules.py`：纯函数 `generate_obligations(contract, schedules, lifecycle_events, as_of)`，覆盖月/季/年账期、递增、折算、免租、作废；V2-T01/T02/T08 在此层先转绿。
- `backend/src/services/asset_operations/rent_obligation_service.py`：在合同确认、续签、更新期限/租金阶段、终止/退出及其撤销的**同一事务**内调用“重建未锁定义务”（D-06），挂接到 `contract_command_service.py` 与 `contract_lifecycle_command_service.py` 现有提交点。
- `backend/scripts/` 新增一次性幂等回填：为 V1 已存在的合同生成义务；先 dry-run 输出行数与金额合计，再执行。

**V2-3 登记与撤销**
- `backend/src/services/asset_operations/rent_payment_command_service.py`：登记（按 Party 范围锁义务行 `FOR UPDATE`，校验剩余金额、记录类型与 `entry_type` 匹配、凭证归属）、撤销（原因必填、重复撤销 409）、持久幂等回执（复用 `AssetContractWriteReceipt` 模式，`command_kind` 扩展）。
- `backend/src/services/asset_operations/rent_ledger_query_service.py`：派生 `effective_paid_amount` / `remaining_amount` / `status`，矩阵按合同行 × 1–12 月聚合；列表关联统一 `selectinload` 防 N+1。
- `backend/src/api/v1/rent_ledgers.py`：自注册 `GET /rent-ledgers`、`GET /rent-ledger-entries/{id}`、`POST .../records`、`POST /rent-payment-records/{id}/reversal`（D-03 若采纳，另加手工义务端点）。
- `terminal-contracts` 列表接入 `rent_unpaid` 筛选；上游合同详情返回“付款计划”阶段汇总（已付 a/b · 下期）。

**V2-4 前端台账**
- `frontend/src/services/assetLedgerService.ts`：封装 V2 API，Decimal 走 `convertBackendToFrontend` / `convertFrontendToBackend`。
- `frontend/src/pages/AssetOperations/LedgersPage.tsx`：`/asset-operations/ledgers`，页签“承租租金（应付）/ 终端租金（应收）”（管理费页签在 PR-C 接入）；行 = 合同，列 = 1–12 月 + 合计，当前月主色、未来月灰，表内横向滚动；格子点击后右侧详情栏展示来源条款、记录链与“登记 / 撤销”。
- 登记卡与撤销弹窗：React Hook Form；金额默认剩余额、日期默认今天（上海业务日）、凭证可选；部分登记显示“部分付款 · 欠 ¥x”。
- 合同列表/详情：终端合同“本月收租块”（转租登记到账、直签登记产权方已报）、“租金未到账”筛选；上游合同“付款计划”块。
- `frontend/src/constants/routes.ts`、`AppRoutes.tsx`、`menuConfig.tsx` 注册“台账”入口（`asset_ops:read`，写操作 `asset_ops:write`）。
- 四态、唯一主按钮、1280px / 200% / 320px 走查。

### PR-B：押金待处理（REQ-DEP-001）

**V2-5 押金**
- 模型/迁移：`DepositLedgerEntry`、`DepositRecord`（D-08）。
- `backend/src/services/asset_operations/deposit_rules.py`：由合同约定与生命周期事件派生方向（D-09），直签只允许 `owner_reported`。
- `deposit_command_service.py` / `deposit_query_service.py` / `backend/src/api/v1/deposits.py`：§5.8 四个端点，幂等与撤销同 V2-3。
- 前端：终端/上游合同详情栏“押金明细”与登记/退还按钮，“押金未结清”筛选；押金三类汇总列表暂由合同列表筛选承载，本月页“押金待处理”通栏留给 V5。

### PR-C：委托管理费对账（REQ-FEE-001）

**V2-6 对账单**
- 模型/迁移：`ManagementFeeStatement`（产权方 + 月份在非 `superseded` 上唯一）、`ManagementFeeStatementLine`（D-10 行级上游）。
- `management_fee_rules.py`：纯函数试算——行费 = 实收 × 行级比例，按 D-01 舍入后求和；顺延行不计基数。
- `management_fee_command_service.py`：生成/刷新 `collecting` 单（投影 D-11 到账记录）、标记顺延（原因必填，写入下月单的来源行）、上传盖章件（复用 Attachment 校验）、确认（期望版本 + 幂等键；锁定行/比例/金额为快照）、更正（创建后继、原单 `superseded`、原行不改）。
- `backend/src/api/v1/management_fee_statements.py`：§5.9 七个端点。
- 前端：`/asset-operations/management-fees/:statement_id` 纸面样式对账单（最大宽 760px，明细列、合计大写、盖章栏、“上传盖章件”主按钮、打印）；台账“委托管理费”页签（已确认金额 / 待盖章 / 收租中 / 未到，合计只计已确认）；`from=monthly` 时的“← 返回本月”留待 V5 接入。

## 6. 数据与切换原则

1. V2 只新增表与追加记录，不修改 V1 已有合同事实；义务/押金/对账单回填走一次性幂等脚本，先 dry-run 后执行，输出合同数、义务数与金额合计供核对。
2. 不读取、不转换旧 `contract_ledger_entries` / `operational_payment_flows` / `service_fee_ledgers`；目标环境若需要历史付款事实，走 V4 导入或人工底稿，不在 V2 做语义迁移。
3. 不建立“新表无数据时回落旧表”的兼容分支；旧表删除仍归旧域清理专项。
4. 金额全程 `Decimal`，日期全程 `Asia/Shanghai` 业务日；任何派生值（状态、余额、合计、管理费金额）不入写模型。

## 7. 验证门槛

- 各切片按 TDD 顺序跑定向测试，再跑 `ruff check` / `ruff format` / `mypy src`、受影响的前后端单测、迁移命名检查、`backend-import`、`docs-lint`、前端 lint / 严格 UI / type-check / 构建。
- V2-T01–V2-T17 全部转绿；V2-T03/T04/T08/T12 必须有真实 PostgreSQL 集成证据；至少一条真实 HTTP E2E 覆盖“登记两笔 → 撤销第二笔 → 状态回到 partial”与“对账确认后改比例金额不变”。
- 每个 PR 合并前更新 `docs/traceability/requirements-trace.md` 对应 REQ 的代码与测试证据，并在 `docs/traceability/mvp-acceptance-checklist.md` 回填 ACC-V5-006 / 007 与 G2；没有产品验收记录不写“已验收”。
- 未执行的测试、未裁决的 §3 事项或未接入的页面均使 V2 保持进行中。

## 8. 风险

| 风险 | 缓解 |
|---|---|
| 义务重建与生命周期事件并发，导致重复或遗漏义务 | 与合同写操作共用资产单元/合同行锁顺序；未作废行唯一约束兜底 |
| 回填脚本在已有登记的环境重复执行 | 脚本幂等（按唯一键 upsert 未锁定义务），dry-run 输出差异，已锁定义务只报告不改 |
| 对账单投影与租金登记两处展示数字不一致 | D-11 单一事实源；V2-T17 与对账单合计/台账格子交叉断言 |
| 三个 PR 改动同一套金额口径 | PR-A 先固化舍入与义务模型，PR-B/PR-C 只读复用，不得各自实现舍入 |

## 9. 实施记录

- 2026-10-27：起草本计划。依据 PRD §6.5、领域模型 §4.16–4.20、API 契约 §5.7–5.9 与 v5 原型交接文档；列出 14 项开工前待裁决事项，待评审。
- 2026-10-27：§3 的 14 项按建议裁决采纳，V2-0 回写 SSOT。领域模型：§2 金额规则补 `ROUND_HALF_UP` 两位小数与“先行后和”；§4.10 合同级账期字段降为录入默认值；§4.14 补账期、到期日、不足月折算、免租与锁定五条义务生成规则；§4.16 补 `contract_kind` / `free_rent` / `origin` / `basis_note` / `voided_by_event_id`、合同到义务类型映射、作废与恢复规则及 `void` 状态；§4.17 补记录类型匹配与 `owner_reported_receipt` 作为管理费唯一事实来源；§4.18 补押金生成与方向规则，新增 §4.18.1 `DepositRecord`；§4.19 对账单改为产权方+月份唯一并以 `upstream_contract_ids` 快照多协议；§4.20 行级补 `upstream_contract_id` / `rent_ledger_entry_id` / 顺延原因与来源，明确 `collecting` 投影与人工顺延；§5.3/§5.4/§6.7/§6.8 同步。API 契约：`asset_ops:write` 覆盖管理费对账；终端合同列表定义 `rent_unpaid` / `deposit_unsettled`；新增 `custom` 账期手工义务端点；到账登记与租金登记共用事实；新增 11 个错误码。未改代码与需求追踪状态。
