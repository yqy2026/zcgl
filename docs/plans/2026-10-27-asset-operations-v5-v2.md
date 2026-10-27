# 资产运营 v5 V2 租金、押金与委托管理费实施计划

> **状态**：🔄 实施就绪（§3 裁决已回写 SSOT，2026-10-27 整体复核修订；D-17、D-18 两项待产品确认，不阻塞开工；待 V1 合并后开工）
> **日期**：2026-10-27
> **需求**：REQ-LED-001、REQ-DEP-001、REQ-FEE-001（联动 REQ-CTR-001/002 的台账类筛选、付款计划展示和终止 / 退出预览）
> **产品基线**：`docs/prd.md` §4.1 / §6.5、`docs/specs/domain-model.md` §4.14–4.20 / §4.31 / §5.3–5.4 / §6.7–6.8、`docs/specs/api-contract.md` §5.6–5.9 / §7、`frontend/prototype/asset-ops-v5-handoff.md`（本月卡片 1–3、终端合同详情与终止弹窗、台账、对账单）
> **前置条件**：V1（PR #95）已合并到 `develop`；目标环境数据切换方案已确认（见 `docs/archive/2026-10-26-asset-operations-v5-remaining-work-handoff.md`）

## 1. 目标与非目标

V2 在 V1 的“上游合同 → 资产单元 → 终端合同”事实链上，建立三条资金事实：

1. **租金义务与登记**：由合同租金阶段生成承租应付、转租应收、直签产权方应报到账三类义务；合同期限或生命周期变化时重排未锁定义务；外部付款 / 到账以追加记录登记，支持部分完成、跨月结转与有原因撤销。
2. **押金**：每份合同一条押金条目，跟踪约定与实际持有，区分应收未收、应付未付（上游押金）、应退未退、应收回四类；续签时押金转入后继合同，转租押金可抵扣欠租。
3. **委托管理费对账**：基于产权方实际到账逐户试算，每产权方每月一张对账单，截止日后未收余额自动顺延，按月份顺序盖章确认后锁定，更正走后继单。

V2 **不实现**：本月工作台（V5，仅保留义务 / 押金 / 对账状态的可查询投影）、考核范围与报送（V3）、档案矩阵与导入（V4，盖章件与凭证复用 V1 已有 Attachment 存储，不建档案矩阵）、银行流水认领、发票、催收、付款指令（PRD §4.2 Out of Scope），以及 §3 中待产品确认的 D-17、D-18。

## 2. 现有实现盘点与裁决

| 现有对象 | 实际状态 | V2 裁决 |
|---|---|---|
| `ContractRentSchedule`（V1） | 存阶段起止、原定 / 实际月租、递增、免租、`payment_cycle`、`due_day`；录入后没有修改入口 | 义务只取 `actual_monthly_rent`、账期与 `due_day`；其余字段只做核对展示（D-05）；修改入口缺失见 D-18 |
| `UpstreamContract.payment_cycle` / `payment_day` | 合同级字段，与阶段级字段重复；V1 PATCH 可改 | 只作录入默认值与展示，修改不重算义务（D-02）；前端在修改处提示“付款周期以租金阶段为准” |
| `UpstreamContractUpdate` / `TerminalContractUpdate`（V1 PATCH） | 可改 `end_date`、押金、委托管理费比例、绑上游等 | `end_date` 变更在同一事务触发义务重排；押金约定由押金条目派生读取，无需同步；比例变化只影响未确认对账单；绑上游使待补录户进入对账（D-12） |
| `ContractLifecycleEvent`（终止 / 退出 / 续签 / 撤销） | 追加事件，可按日重放；终止事件带 `deposit_settlement_status` 声明 | 驱动义务重排与押金阶段；义务服务只读事件，不改写事件；押金状态以派生为准，事件上的声明不参与计算 |
| `AssetContractWriteReceipt`（V1） | 只有 `create_upstream` / `create_terminal` 两类，数据库 CHECK 约束限定 | 扩展为资产运营高后果命令的幂等回执，新增手工义务与管理费对账命令类型（D-15），迁移同步放宽 CHECK |
| `ContractLedgerEntry` / `OperationalPaymentFlow` / `ServiceFeeLedger`（旧 v4，`contract_group.py`） | 含可变 `paid_amount`、旧归属口径；V1 已断开路由 | **不复用、不双读、不迁移语义**；新表另起名，旧表随旧域清理删除 |
| `Attachment` 私有存储（V1 扫描件） | 已有统一文件校验与私有存储 | 付款凭证、押金凭证与盖章件复用；不建 `ArchiveDocument` 矩阵（V4） |
| `BusinessChangeEvent` | 领域模型已定义，V1 未落地 | V2 首次落地：登记、撤销、重排、顺延、确认、更正均写变更记录（V3 报送引用） |
| 前端 `/operations/ledger`（旧） | V1-4 已删除 | 新建 `/asset-operations/ledgers` 与 `/asset-operations/management-fees/:statement_id` |

## 3. 裁决记录

起草时 SSOT 未定义或互相冲突之处，经 2026-10-27 采纳并回写 `docs/specs/domain-model.md`、`docs/specs/api-contract.md` 和 `docs/prd.md`；同日整体复核后修订了与原型、V1 实现不一致的裁决（“复核修订”列）。实施以 SSOT 为准，本表只作决策追溯。

| ID | 问题 | 裁决 | 复核修订 |
|---|---|---|---|
| D-01 | 金额舍入规则未定义 | 两位小数 `ROUND_HALF_UP`；义务生成时舍入，管理费按行舍入后求和 | — |
| D-02 | 合同级与阶段级账期字段并存 | 义务只读阶段级；合同级只作录入默认值 | 补充：V1 PATCH 仍可改合同级字段，前端须提示不影响义务 |
| D-03 | 季付 / 年付 / 自定义账期如何出义务 | 按自然月；同账期的连续阶段合并为账期段，季付 / 年付以段起始月为锚每 3 / 12 个月一期；`custom` 手工登记并可作废 | 原裁决“季付在 1/4/7/10 月出、年付只在阶段起始月出一期”与原型不符（原型 `upDue` 以起租月为锚），且年付漏了多年阶段，已改 |
| D-04 | 起止日落在月中是否折算 | 按自然日折算，同月跨阶段分段折算 | 保留。原型终止弹窗按整月计当月欠租，属原型简化，见 §8 风险 |
| D-05 | 免租如何落到各期 | 只用 `actual_monthly_rent`；0 元账期不生成义务，台账按阶段显示“免租” | 原裁决“免租月置 0”会与原型“按月平均减免”模式重复扣减，已改；删除 `free_rent` 字段 |
| D-06 | 锁定边界 | 只有存在有效登记才锁定 | 原裁决把“账期早于当前月”也算锁定，会让补登的终止无法作废往月未付义务，已改；租金阶段变更仍只重排当前月起的义务 |
| D-07 | 终止 / 退出后多出的义务 | 统一“重排”：未锁定义务按目标集合更新 / 作废 / 恢复 / 新建；锁定义务不动并提示 `RENT_LEDGER_PLAN_MISMATCH` | 原裁决按事件作废并在撤销时恢复，未覆盖期限更新与登记撤销，已改为重排；字段改为 `voided_at` / `void_correlation_id`；唯一键改为 `period_start`，避免月中换账期时同月两期冲突 |
| D-08 | 押金记录 | 新增 `DepositRecord`：`collect` / `refund` / `deduct` / `owner_reported_collect` / `owner_reported_refund` / `pay` / `recover` / `reversal` | 原 `owner_reported` 无法区分收与退，已拆分；新增上游 `pay`；新增 `deduct` 与租金 `deposit_offset` 成对写入、成对撤销 |
| D-09 | 押金方向 | 每份合同一条条目，阶段、方向和状态全部派生；上游押金跟踪应付未付与应收回 | 按产品决定改为跟踪上游押金（原裁决不跟踪）；按原型“续签后押金转入新合同，不退回”增加续签转入；合同改押金约定时自动重算 |
| D-10 | 对账单单值上游 vs 每产权方每月一张 | 产权方 + 月份唯一，协议记在行上 | — |
| D-11 | 到账登记与对账单行是否两份事实 | 一份：`owner_reported_receipt`；对账单确认前投影、确认时快照 | 补充：快照记录 `counted_record_ids`；被已确认单计入的到账不可撤销，须先更正 |
| D-12 | 顺延时点与对账单生命周期 | 截止日为对账月次月最后一天；截止日前可手工顺延（原因必填），截止后未收余额自动顺延；按月份顺序确认；只能更正最近一张已确认单 | 原裁决“不自动顺延”与 PRD“月末仍未收到的户顺延、不阻塞”和原型“10-31 仍未收的顺延下月”不符，已改；补充对账单创建时机、`collecting` / `pending_stamp` 改为派生、上游缺失户的处理 |
| D-13 | 盖章件上传与确认权限 | `asset_ops:write` | — |
| D-14 | 超额登记 | 不做扩展，409 失败关闭 | — |
| D-15 | 幂等存储（复核新增） | 租金 / 押金记录用自身唯一 `idempotency_key`；手工义务与管理费对账命令用扩展后的 `AssetContractWriteReceipt` | — |
| D-16 | 终止 / 退出预览（复核新增） | 预览返回义务新建 / 更新 / 作废 / 恢复数量、锁定不一致清单与押金状态变化；token 绑定受影响义务版本 | — |
| D-17 | 提前退租补收免租优惠（复核发现，**待产品确认**） | 原型终止弹窗有“免租优惠补收”，SSOT 没有，合同也没有补收条款字段。V2 不实现；如采纳，需先在合同上增加补收条款并定义补收义务类型 | — |
| D-18 | 租金阶段更正入口（复核发现，**待产品确认**） | V1 PATCH 不能改租金阶段，录错的阶段只能等 V4 导入更新。V2 不新增入口；重排规则已为阶段变更预留（只重排当前月起的义务） | — |

## 4. 失败测试清单（先写）

| 测试 ID | 预期失败条件 | 守护的意图 |
|---|---|---|
| V2-T01 | 季付按自然季度而非账期段起始月出应付；年付多年阶段只出一期；跨阶段账期未分段计算 | 账期规则（领域模型 §4.14） |
| V2-T02 | 月中起止未按日折算；同月跨阶段未分段；“免租期前置”的 0 元阶段生成了义务；“按月平均减免”被二次扣减 | 折算与免租（D-04 / D-05） |
| V2-T03 | 期限更新后未锁定义务未更新 / 作废 / 新建；有效登记的义务被改动或未出现 `RENT_LEDGER_PLAN_MISMATCH`；月中换账期产生重复行 | 重排与锁定（D-06 / D-07） |
| V2-T04 | 一笔义务分两次登记结清后撤销第二笔，状态不是 `partial` 或原记录被修改 / 删除 | 追加式登记与撤销（ACC-V5-006 / G2） |
| V2-T05 | 登记金额超出剩余义务被接受，或重复撤销同一记录成功 | `PAYMENT_AMOUNT_EXCEEDS_REMAINING` / `PAYMENT_RECORD_ALREADY_REVERSED` |
| V2-T06 | 同幂等键同请求生成第二条记录；同键不同金额未返回 `IDEMPOTENCY_CONFLICT` | 重试不重复写入 |
| V2-T07 | 往月未完成义务在切换查询月份后从“未完成”列表消失 | 跨月结转（PRD §6.5） |
| V2-T08 | 补登过去生效的终止后，生效日之后未登记的往月义务仍计入应收；边界账期未按日重算；撤销终止后未恢复；续签改动了前驱义务 | 重排覆盖补登与撤销 |
| V2-T09 | 直签终端押金可登记 `collect` / `deduct` 等非产权方报告类型 | 直签押金只登记产权方报告（api-contract §5.8） |
| V2-T10 | 终端到期后未转应退、上游退出后未转应收回；上游在期未付清未显示应付未付；合同调低押金后未出现应退 / 应收回；撤销记录后余额未恢复 | 押金四类方向（REQ-DEP-001） |
| V2-T11 | 续签后前驱仍显示应退 / 应收回，后继未转入前驱余额；向已续签条目登记未返回 `DEPOSIT_ENTRY_CARRIED_FORWARD` | 续签转入 |
| V2-T12 | 押金抵扣未同时写入租金 `deposit_offset`；撤销任一侧未撤销另一侧；超出义务剩余金额未返回 `DEPOSIT_OFFSET_TARGET_INVALID` | 抵扣成对一致 |
| V2-T13 | 截止日前未处理行仍可确认；截止日后未收余额未自动顺延；顺延余额计入本单基数或未带入下月单；部分到账未分别计入与顺延 | 顺延不阻塞已具备条件的对账（PRD §6.5、§6.8） |
| V2-T14 | 已确认对账单在修改比例、租户名称或补登到账后金额变化；撤销已被计入的到账未返回 `MANAGEMENT_FEE_STATEMENT_LOCKED` | 确认锁定（ACC-V5-007 / G2） |
| V2-T15 | 存在更早未确认单时可确认；可更正非最近一张已确认单；无盖章件可确认；更正覆盖原单而非生成后继 | 对账顺序与状态机（§5.4） |
| V2-T16 | 上游缺失的直签义务进入对账单；补录上游后未按规则进入当月或带入最早未确认单 | 上游缺失不影响对账口径 |
| V2-T17 | 无 Party 范围时台账 / 押金 / 对账单返回空列表；范围外合同的义务或押金可被登记 | 403 失败关闭（REQ-AUTH-002） |
| V2-T18 | 账期、截止日或逾期按 UTC 日期判断，`Asia/Shanghai` 跨日边界归属错误 | 业务时区口径 |
| V2-T19 | 台账、押金或对账单页把 403 当 empty，或把刷新错误清空成空列表 | 四态不混淆（ACC-V5-010） |
| V2-T20 | 台账矩阵合计与逐条义务不一致；对账单合计与行合计不一致 | 派生页面数字一致（G1） |

## 5. 文件级实施顺序

每个切片按 V1 惯例走“失败测试 → 模型 / 迁移 → CRUD → 服务 → API → 前端”纵向红绿循环，单独提交，切片完成后做一次双轴复核（标准轴 + 规格轴）。整个 V2 按以下三个 PR 交付，不合成一个大 PR；PR-B 的押金抵扣依赖 PR-A 的租金记录，PR-C 依赖 PR-A 的义务与到账。

### PR-A：租金义务与登记（REQ-LED-001）

**V2-0 SSOT 回写**（2026-10-27 已回写并复核修订，见 §9）

**V2-1 领域与持久化**
- `backend/src/models/asset_ledger.py`：`RentLedgerEntry`（`entry_type`、`contract_kind`、`contract_id`、`period`、`period_start`、`period_end`、`due_date`、`due_amount`、`origin`、`basis_note`、`locked_source` JSONB、`voided_at`、`void_correlation_id`、`version`）、`RentPaymentRecord`（追加式；`reverses_record_id` 部分唯一索引保证一笔只能撤销一次；`paired_deposit_record_id` 预留给 PR-B）、`BusinessChangeEvent`。
- `backend/alembic/versions/2026xxxx_asset_operations_v5_rent_ledger.py`：建表；`generated` 义务在 `(contract_kind, contract_id, entry_type, period_start)` 上唯一；金额 `Numeric(14,2)`，义务金额 CHECK 大于 0；放宽 `asset_contract_write_receipts.command_kind` CHECK，加入 `create_manual_rent_entry` / `void_manual_rent_entry`；不建旧表外键。
- `backend/src/schemas/asset_ledger.py`：写模型 `extra=forbid`，拒绝 `status` / `effective_paid_amount` / `remaining_amount` 等派生字段（`DERIVED_FIELD_NOT_WRITABLE`）。
- `backend/src/models/__init__.py` 显式导出。

**V2-2 义务生成与重排（纯函数优先）**
- `backend/src/services/asset_operations/rent_obligation_rules.py`：纯函数计算目标账期集合——账期段与锚月、跨阶段分段、按日折算、0 元账期跳过、期限截断与 `RENT_SCHEDULE_GAP`；纯函数对齐目标与现有义务，输出新建 / 更新 / 作废 / 恢复 / 不一致。V2-T01 / T02 / T03 / T08 在此层先转绿。
- `backend/src/services/asset_operations/rent_obligation_service.py`：在**同一事务**内执行重排并写 `BusinessChangeEvent`。挂接点：`contract_command_service.py` 的合同确认、`update_upstream` / `update_terminal` 的 `end_date` 变更；`contract_lifecycle_command_service.py` 的续签、终止、退出及其撤销。锁顺序沿用 V1：先资产单元、再合同、再义务行。
- 终止 / 退出预览（D-16）：在 V1 预览响应中追加义务影响与押金状态变化，预览 token 指纹加入受影响义务版本；保持 V1 已有字段不变。
- `backend/scripts/` 新增一次性幂等回填：为 V1 已存在的合同重排生成义务（PR-B、PR-C 合并后同一脚本补押金条目与对账单）；先 dry-run 输出合同数、义务数与金额合计，再执行。

**V2-3 登记、撤销与手工义务**
- `backend/src/services/asset_operations/rent_payment_command_service.py`：登记（按 Party 范围锁义务行 `FOR UPDATE`，校验剩余金额、记录类型与 `entry_type` 匹配、凭证归属）；撤销（原因必填、重复撤销 409，同一事务重排该合同义务）；幂等以记录自身唯一键实现，同键比对已存字段。
- 手工义务创建 / 作废：限 `custom` 账期段，依据说明必填，幂等走 `AssetContractWriteReceipt`。
- `backend/src/services/asset_operations/rent_ledger_query_service.py`：派生 `effective_paid_amount` / `remaining_amount` / `status`；矩阵按 `ledger_type`（`upstream_rent` / `terminal_rent`）× 1–12 月聚合，标注非付款月与免租期；列表关联统一 `selectinload` 防 N+1。
- `backend/src/api/v1/rent_ledgers.py`：自注册 §5.7 的六个端点。
- `terminal-contracts` 列表接入 `rent_unpaid` 筛选；上游合同详情返回“付款计划”阶段汇总（已付 a/b · 下期）。

**V2-4 前端台账**
- `frontend/src/services/assetLedgerService.ts`：封装 V2 API，Decimal 走 `convertBackendToFrontend` / `convertFrontendToBackend`。
- `frontend/src/pages/AssetOperations/LedgersPage.tsx`：`/asset-operations/ledgers`，页签“承租租金（应付）/ 终端租金（应收）”（管理费页签在 PR-C 接入）；行 = 合同，列 = 1–12 月 + 合计，当前月主色、未来月灰，表内横向滚动；格子点击后右侧详情栏展示来源条款、账期起止、记录链、warning 与“登记 / 撤销”。
- 登记卡与撤销弹窗：React Hook Form；金额默认剩余额、日期默认今天（上海业务日）、凭证可选；部分登记显示“部分付款 · 欠 ¥x”。
- 合同列表 / 详情：终端合同“本月收租块”（转租登记到账、直签登记产权方已报）、“租金未到账”筛选；上游合同“付款计划”块；合同级付款周期旁提示以租金阶段为准；终止 / 退出确认页展示义务影响。
- `frontend/src/constants/routes.ts`、`AppRoutes.tsx`、`menuConfig.tsx` 注册“台账”入口（`asset_ops:read`，写操作 `asset_ops:write`）。
- 四态、唯一主按钮、1280px / 200% / 320px 走查。

### PR-B：押金（REQ-DEP-001）

**V2-5 押金**
- 模型 / 迁移：`DepositLedgerEntry`（每份合同一条，只存 `collector` 与版本）、`DepositRecord`；合同确认与续签事务内创建条目。
- `backend/src/services/asset_operations/deposit_rules.py`：纯函数派生 `own_held` / 续签转入转出 / 在期阶段 / `gap` / 方向与状态；V2-T10 / T11 在此层先转绿。
- `deposit_command_service.py`：登记（记录类型与收取方匹配、收入不超过待收 / 待付、支出不超过持有余额、已续签条目拒绝）；`deduct` 与租金 `deposit_offset` 同一事务成对写入，撤销任一侧成对撤销（V2-T12）。
- `deposit_query_service.py`：待处理列表按派生状态筛选，用 SQL 聚合记录合计与续签链，避免逐条计算；`backend/src/api/v1/deposits.py` 自注册 §5.8 四个端点。
- `terminal-contracts` 列表接入 `deposit_unsettled` 筛选。
- 前端：终端 / 上游合同详情栏“押金明细”（约定、持有、转入 / 转出、待处理方向与金额、记录链）与登记 / 退还 / 支付 / 收回 / 抵扣按钮；终止弹窗“押金结算”区展示已收、抵扣欠租与应退；“押金未结清”筛选。本月页“押金待处理”通栏留给 V5。

### PR-C：委托管理费对账（REQ-FEE-001）

**V2-6 对账单**
- 模型 / 迁移：`ManagementFeeStatement`（产权方 + 月份在非 `superseded` 上唯一）、`ManagementFeeStatementLine`（确认快照）；放宽回执 CHECK，加入 `defer_management_fee_line` / `confirm_management_fee_statement` / `supersede_management_fee_statement`。
- `management_fee_rules.py`：纯函数投影——`current` / `carried` 行、计入实收（扣除已被确认单计入的记录）、截止日自动顺延、已处理判定与派生状态、行费舍入与合计。V2-T13 / T16 在此层先转绿。
- `management_fee_command_service.py`：对账单随 `owner_receipt_expected` 义务生成创建（挂到 PR-A 的重排服务）；产权方到账委托租金登记服务并使对账单版本加一；手工顺延（原因必填）；上传 / 替换盖章件；确认（期望版本 + 幂等键、盖章件必填、顺序校验、写快照、带出顺延余额并按需创建下月单）；更正（只限最近一张已确认单，创建后继、原单 `superseded`）。
- 租金登记撤销服务补充校验：被已确认单计入的到账撤销返回 `MANAGEMENT_FEE_STATEMENT_LOCKED`（V2-T14）。
- `backend/src/api/v1/management_fee_statements.py`：§5.9 七个端点。
- 前端：`/asset-operations/management-fees/:statement_id` 纸面样式对账单（最大宽 760px，明细列、合计大写、盖章栏、“上传盖章件”主按钮、打印、截止日与待补录上游提示）；台账“委托管理费”页签（已确认金额 / 待盖章 / 收租中 / 未到，合计只计已确认）；`from=monthly` 时的“← 返回本月”留待 V5 接入。

## 6. 数据与切换原则

1. V2 只新增表与追加记录，不修改 V1 已有合同事实；义务、押金条目与对账单回填走一次性幂等脚本，先 dry-run 后执行，输出合同数、义务数、押金条目数、对账单数与金额合计供核对。
2. 不读取、不转换旧 `contract_ledger_entries` / `operational_payment_flows` / `service_fee_ledgers`；目标环境若需要历史付款、押金或对账事实，走 V4 导入或人工底稿，不在 V2 做语义迁移。
3. 不建立“新表无数据时回落旧表”的兼容分支；旧表删除仍归旧域清理专项。
4. 金额全程 `Decimal`，日期全程 `Asia/Shanghai` 业务日；任何派生值（状态、余额、合计、押金方向、管理费金额）不入写模型。

## 7. 验证门槛

- 各切片按 TDD 顺序跑定向测试，再跑 `ruff check` / `ruff format` / `mypy src`、受影响的前后端单测、迁移命名检查、`backend-import`、`docs-lint`、前端 lint / 严格 UI / type-check / 构建。
- V2-T01–V2-T20 全部转绿；V2-T03 / T04 / T08 / T10 / T11 / T12 / T14 必须有真实 PostgreSQL 集成证据；真实 HTTP E2E 至少覆盖“登记两笔 → 撤销第二笔 → 状态回到 partial”“补登终止 → 往月未登记义务作废”“续签 → 押金转入后继”和“对账确认后改比例金额不变”。
- 每个 PR 合并前更新 `docs/traceability/requirements-trace.md` 对应 REQ 的代码与测试证据，并在 `docs/traceability/mvp-acceptance-checklist.md` 回填 ACC-V5-006 / 007 与 G2；没有产品验收记录不写“已验收”。
- 未执行的测试、未接入的页面或在实施中新发现的规格缺口均使 V2 保持进行中；D-17 / D-18 若在开工前被采纳，先回写 SSOT 并补失败测试。

## 8. 风险

| 风险 | 缓解 |
|---|---|
| 重排与生命周期命令或登记撤销并发，导致重复或遗漏义务 | 与合同写操作共用资产单元 / 合同 / 义务行锁顺序；`period_start` 唯一约束兜底；重排纯函数可重复执行 |
| 锁定义务与合同条款不一致长期滞留 | `RENT_LEDGER_PLAN_MISMATCH` 在台账格子、合同详情和终止 / 退出预览可见；V5 本月页再汇总 |
| 原型终止弹窗按整月计当月欠租，规格按日折算 | 以 SSOT 为准；产品走查时专门核对终止当月金额，如需改为整月计租，先改领域模型 §4.14 |
| 押金派生状态在列表筛选时计算量大 | 记录合计与续签链用 SQL 聚合一次算出；待处理列表分页在数据库完成 |
| 回填脚本在已有登记的环境重复执行 | 脚本幂等（重排纯函数 + 唯一键），dry-run 输出差异，锁定义务只报告不改 |
| 对账单投影与租金登记两处数字不一致 | D-11 单一事实源；V2-T20 交叉断言对账单合计、行合计与台账格子 |
| 三个 PR 改动同一套金额口径 | PR-A 固化舍入、账期与重排，PR-B / PR-C 只读复用，不得各自实现舍入 |

## 9. 实施记录

- 2026-10-27：起草本计划。依据 PRD §6.5、领域模型 §4.16–4.20、API 契约 §5.7–5.9 与 v5 原型交接文档；列出 14 项开工前待裁决事项，待评审。
- 2026-10-27：§3 的 14 项按建议裁决采纳，V2-0 回写 SSOT（领域模型 §2 / §4.10 / §4.14 / §4.16–4.20 / §5.3–5.4 / §6.7–6.8，API 契约 §3.1 / §5.6–5.9 / §7）。未改代码与需求追踪状态。
- 2026-10-27：按产品决定改为跟踪上游押金，并对 V2 规格做整体复核。对照原型 `asset-ops-v5.html` 与 V1 代码修订 D-02 / D-03 / D-05 / D-06 / D-07 / D-08 / D-09 / D-11 / D-12，新增 D-15–D-18：季付锚定账期段起始月、只用实际月租、锁定只看有效登记、统一重排与 `period_start` 唯一、押金每合同一条且全部派生（含应付未付、续签转入、抵扣欠租）、对账单截止日自动顺延与按月顺序确认。同步回写领域模型 §3 / §4.14 / §4.16–4.20 / §4.31 / §5.3–5.4 / §6.8、API 契约 §4 / §5.6–5.9 / §7、PRD §4.1 / §6.5 / REQ-DEP-001、需求追踪 REQ-DEP-001 说明和原型交接文档押金口径；测试清单扩为 V2-T01–T20。未改代码。
