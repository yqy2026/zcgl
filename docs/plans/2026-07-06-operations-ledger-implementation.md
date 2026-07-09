# 经营台账与收付流水实施计划

## Status

🔄 实施中

## 1. 目标

把 2026-07-06 已确认的经营台账口径从 PRD/SSOT 落到代码：

- 项目仍是默认主入口，但经营台账、合同中心、资产资源、主体客户和经营分析保留全局直接入口。
- 用户侧展示“合同与协议”和“经营台账”，不把内部 `ContractGroup` 或“合同关系”作为普通页面对象。
- 经营台账拆为四类业务视图：终端租户收缴、运营方收入、运营方成本、服务费结算。
- 终端租户租金收缴是唯一逾期来源；运营方成本未付、服务费未收不产生逾期。
- 实收/实付由轻量收付流水和到账期分摊汇总生成，经营分析默认按租金账期归属，流水发生日期仅用于查询、导出和审计。
- 代理服务费按租金账期月份、项目、委托协议和产权方汇总生成，不逐笔生成。

## 2. 权威来源

- `docs/prd.md`
- `docs/specs/domain-model.md`
- `docs/specs/api-contract.md`
- `docs/traceability/requirements-trace.md`
- `docs/issues/2026-07-06-operations-ledger-prd-revision.md`

涉及 REQ：

- `REQ-PRJ-003`：项目详情承载经营台账。
- `REQ-RNT-001` / `REQ-RNT-002`：合同与协议、承租转租和代理运营。
- `REQ-RNT-005`：合同/协议更正与作废留痕。
- `REQ-RNT-006`：经营台账与收付流水。
- `REQ-ANA-001`：经营分析与导出。
- `REQ-NTF-001`：业务提醒与站内通知。

## 3. 非目标

- 不接入财务总账、银行流水、支付通道、税票、开票或现金流分析。
- 不建设催缴工单、指派、审批或催缴成功率统计。
- 不做会计收入确认或利润口径，界面使用“经营净流入”“账面经营差额”等运营口径。
- 不为了兼容旧“财务台账”页面文案保留双命名；0 到 1 阶段直接收口。
- 不新增跨项目合同/协议聚合对象；跨项目委托协议继续靠共享盖章扫描件和各项目各自合同/协议记录表达。

## 4. 总体设计

### 4.1 后端数据模型

沿用现有合同域落点，优先在 `backend/src/models/contract_group.py` 内扩展台账相关模型，保持 `ContractLedgerEntry`、`ServiceFeeLedger`、合同补录和台账生成在同一领域边界内。

新增或调整：

- `ContractLedgerEntry.ledger_views`：JSONB 字符串数组。承租转租下游租金同时进入 `terminal_collection` 和 `operator_income`；代理直租租金只进入 `terminal_collection`；上游承租租金只进入 `operator_cost`。
- `ContractLedgerEntry.follow_up_status` / `next_follow_up_date` / `follow_up_note`：仅终端租户收缴视图可维护。
- `OperationalPaymentFlow`：轻量收付流水，类型为 `terminal_rent_receipt`、`service_fee_receipt`、`upstream_cost_payment`。
- `PaymentAllocation`：一笔流水到账期条目的人工分摊，目标可为 `ContractLedgerEntry` 或 `ServiceFeeLedger`。
- `ServiceFeeLedger`：从单来源租金台账调整为按租金账期月份聚合，补 `agency_agreement_contract_id`、`source_ledger_ids`、`calculation_base_amount`，唯一性收口到项目/委托协议/产权方/账期维度。`agency_contract_id` 继续表示代理直租合同；`agency_agreement_contract_id` 表示委托协议合同。

### 4.2 服务边界

- `ledger_service_v2` 继续负责合同租金台账生成、重算、查询和派生支付状态。
- 新增 `payment_flow_service` 负责流水登记、作废、分摊校验和汇总。
- `service_fee_ledger_service` 从逐笔同步改为月度汇总生成。已生成服务费应收后，来源租金条目被合同更正重算跳过时，不自动重算或覆盖服务费台账，改为派生服务费来源不一致风险并交由人工处理；尚未生成服务费的账期按修正后实收进入后续月度生成。
- `ledger_compensation_service` 补偿缺失租金台账、流水派生金额、服务费月度台账，保持幂等。
- `analytics_service` 只读经营台账和流水汇总，不直接重新解释合同条款。
- `notification.scheduler` 只扫描终端租户租金到期/逾期和合同/协议到期。

### 4.3 前端信息架构

- 左侧导航将“财务台账”收口为“经营台账”。
- 项目详情展示四组摘要，并支持跳转到带筛选条件的全局经营台账。
- 合同中心保留直接入口，页面文案为合同/协议业务语言。
- 经营台账页面提供四个视图 tab 或 segmented control：终端租户收缴、运营方收入、运营方成本、服务费结算。

## 5. 实施阶段

### Phase 1：后端模型与迁移底座

目标：先建立真实数据结构，不改前端主流程。

文件范围：

- `backend/src/models/contract_group.py`
- `backend/src/models/__init__.py`
- `backend/src/schemas/contract_group.py`
- `backend/alembic/versions/*operations_ledger*.py`
- `backend/tests/unit/models/test_contract_group_model.py`
- `backend/tests/unit/migration/*operations_ledger*.py`
- `scripts/check_field_drift.py`
- `docs/specs/domain-model.md`
- `docs/traceability/requirements-trace.md`
- `CHANGELOG.md`

任务：

- [x] 增加 `ledger_views`、跟进状态字段和 DB 约束。
- [x] 新增 `operational_payment_flows` 和 `payment_allocations` 表。
- [x] 调整 `service_fee_ledgers` 为月度聚合结构。
- [x] 迁移存量 `paid_amount`：生成最小回填流水和分摊，或在发现无法唯一回填时 fail-loud。
- [x] 将 `OperationalPaymentFlow`、`PaymentAllocation` 和调整后的 `ServiceFeeLedger` 加入或同步更新 `scripts/check_field_drift.py` 映射，避免新增或改造 ORM 后字段漂移检查继续 SKIP 或误报。
- [x] 写模型和 migration 测试，覆盖约束、默认值、回填和失败暴露。

验收：

- `ContractLedgerEntry` 能表达一条账同时属于多个经营视图。
- 流水金额必须大于 0。
- 同一流水的分摊合计必须由服务层校验等于流水金额。
- 服务费台账不再依赖单个 `source_ledger_id` 唯一。
- Phase 1 回填迁移后不得存在 `paid_amount > 0` 但无有效 `PaymentAllocation` 的非作废台账；发现即失败暴露，Phase 2 才允许切换保护逻辑。

### Phase 2：台账生成、流水登记和分摊服务

目标：让实收/实付事实由流水和分摊产生，替代直接改累计金额。

前置条件：Phase 1 存量回填迁移必须 100% 成功；若仍存在非作废台账 `paid_amount > 0` 但无有效分摊记录，禁止启用 Phase 2 的重算保护逻辑切换。

文件范围：

- `backend/src/services/contract/ledger_service_v2.py`
- `backend/src/services/contract/payment_flow_service.py`
- `backend/src/services/contract/service_fee_ledger_service.py`
- `backend/src/services/contract/ledger_compensation_service.py`
- `backend/src/crud/contract_group.py`
- `backend/tests/unit/services/contract/test_ledger_service_v2.py`
- `backend/tests/unit/services/contract/test_payment_flow_service.py`
- `backend/tests/unit/services/contract/test_service_fee_ledger_service.py`
- `backend/tests/unit/services/contract/test_ledger_compensation_service.py`

任务：

- [x] 台账生成时按合同角色写入 `ledger_views`。
- [x] 查询与状态派生改读 `PaymentAllocation` 汇总金额，并用迁移后的分摊记录验证存量回填结果等价。
- [x] 流水登记支持租金收款、服务费收款、上游成本付款三类。
- [x] 分摊服务校验目标条目类型、账期、项目/主体范围和金额合计。
- [x] 服务费生成按租金账期月份汇总代理直租实收，固化服务费比例、计算基数和来源账期。
- [x] 合同更正重算跳过已有流水分摊的条目，并保留 `ledger_stale_after_correction` 风险口径。
- [x] 来源租金条目被重算跳过时，已生成服务费台账不得自动重算或覆盖；派生服务费来源不一致风险，未生成服务费的账期才按修正后实收参与后续月度生成。

验收：

- 一笔租金收款可以分摊到多个账期，账期实收按分摊汇总。
- 代理直租租金收款进入终端租户收缴，但不进入运营方收入。
- 服务费应收只在代理直租租金实际收到后形成。
- 上游成本付款只影响运营方成本，不产生逾期。
- 同一 `ContractLedgerEntry` 同时属于 `terminal_collection` 和 `operator_income` 时，两个视图分别正确汇总，跨视图汇总按指标定义去重，不重复计入。
- 合同更正跳过来源租金条目时，既有服务费台账保持原值并产生服务费来源不一致风险；不静默重算。

### Phase 3：经营台账 API

目标：提供项目上下文和全局上下文统一 API。

文件范围：

- `backend/src/api/v1/contracts/ledger.py`
- `backend/src/schemas/contract_group.py`
- `backend/tests/unit/api/v1/test_ledger_api.py`
- `docs/specs/api-contract.md`
- `docs/traceability/requirements-trace.md`

任务：

- [x] `GET /api/v1/ledger/entries` 支持合同租金台账 `ledger_view`、项目、主体、资产、合同/协议、账期、发生日期和派生支付状态筛选。
- [x] `GET /api/v1/projects/{project_id}/ledger-summary` 返回四类经营摘要。
- [x] `POST /api/v1/ledger/payment-flows` 创建流水。
- [x] `POST /api/v1/ledger/payment-flows/{flow_id}/allocations` 保存分摊。
- [x] `POST /api/v1/ledger/service-fees/generate` 生成月度服务费。
- [x] `GET /api/v1/ledger/entries/export` 导出经营台账视图、账期归属和流水发生日期字段。

说明：`GET /api/v1/ledger/entries` 的 `ledger_view` 当前覆盖 `ContractLedgerEntry` 三类合同租金台账视图（`terminal_collection` / `operator_income` / `operator_cost`）。服务费结算由 `ServiceFeeLedger`、服务费生成和服务费收款分摊路径承载；若后续前端需要单一列表同时混排租金台账与服务费台账，应新增统一响应载荷，不复用 `ContractLedgerEntryResponse` 暗中兼容。

验收：

- 未传足够筛选条件时仍按现有保护规则避免全量重查询。
- 权限过滤复用既有主体范围，不泄露范围外合同号、租户名或流水备注。
- API 入参不允许手工写 `payment_status` 作为事实来源。

### Phase 4：前端经营台账与项目详情联动

目标：用户能按运营视角完成查询、登记、分摊和跳转。

文件范围：

- `frontend/src/config/menuConfig.tsx`
- `frontend/src/constants/routes.ts`
- `frontend/src/types/ledger.ts`
- `frontend/src/services/ledgerService.ts`
- `frontend/src/pages/OperationsLedger/OperationsLedgerPage.tsx`
- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/pages/ContractGroup/*`
- 对应前端单测

任务：

- [x] 将全局入口从“财务台账”改为“经营台账”，路由、页面目录、组件名、面包屑和导出文件名同步收口，目标路由为 `/operations/ledger`。
- [x] 经营台账页面按四类视图展示不同列和操作。
- [x] 终端租户收缴视图支持登记收款、分摊账期、维护跟进状态。
- [x] 运营方成本视图支持登记付款和查看未付，不展示逾期标签。
- [ ] 服务费结算视图支持生成服务费、登记服务费收款和查看来源账期。
- [x] 项目详情四组摘要可跳转到经营台账过滤视图。
- [x] 合同/协议号、资产、客户在项目详情、合同详情和经营台账之间互相跳转。

说明：服务费结算视图已支持生成服务费和按服务费台账 ID 登记服务费收款；来源账期列表仍需统一服务费台账查询载荷后补齐。

验收：

- 普通用户界面不再出现“财务台账”作为目标入口名。
- 普通用户界面不把“合同关系”作为页面对象名。
- 前端实现层不再保留 `Finance/FinancialLedgerPage` 作为经营台账页面名。
- 金额列和状态列不因不同视图导致布局跳动。
- 终端租户逾期、运营方成本未付和服务费未收的视觉状态可明确区分。

### Phase 5：经营分析、通知和导出收口

目标：把经营数据消费端全部切到新口径。

文件范围：

- `backend/src/services/analytics/analytics_service.py`
- `backend/src/services/analytics/analytics_export_service.py`
- `backend/src/api/v1/analytics/*`
- `backend/src/services/notification/scheduler.py`
- `frontend/src/components/Analytics/*`
- `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`
- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/pages/System/NotificationCenter.tsx`
- 对应前后端测试

任务：

- [ ] 综合分析返回终端租户收缴、运营方收入、运营方成本、经营结果四组指标。
- [ ] 项目分析按租金账期归属，流水发生日期只用于查询/导出字段。
- [ ] 导出文件标记统计口径版本和账期归属口径。
- [ ] 通知扫描只对终端租户租金生成到期/逾期提醒。
- [ ] 合同/协议到期提醒文案收口，不暴露内部聚合对象。

验收：

- 代理直租租金不进入运营方收入。
- 服务费未收不产生逾期通知。
- 运营方成本未付不产生逾期通知。
- 客户双指标继续遵守单视图口径守卫。

### Phase 6：收口、清理和门禁

目标：删除旧入口残留并完成全量校验。

任务：

- [ ] 清理旧“财务台账”文案、测试快照和导出文件名。
- [ ] 清理旧直接改 `paid_amount` 的前端入口。
- [ ] 更新 `docs/prd.md`、`docs/specs/*`、`docs/traceability/*` 的实现证据。
- [ ] 更新 `docs/issues/2026-07-06-operations-ledger-prd-revision.md` 状态。
- [ ] 完成 `CHANGELOG.md`。
- [ ] 跑受影响测试；能跑 `make check` 时跑全量门禁。

## 6. 建议首个代码切片

首个切片只做后端底座，不碰前端页面：

- 新增 migration 和 ORM 字段/表。
- 新增 Pydantic schema。
- 写模型、migration 和 service 单测。
- 让 `ContractLedgerEntry` 生成时具备 `ledger_views`。
- 加 `PaymentFlowService` 的最小创建和分摊校验。

原因：后续经营台账页面、分析和通知都依赖这层事实模型。先做页面会继续被旧 `paid_amount` 口径牵着走。

## 7. 风险与处理

| 风险 | 处理 |
|---|---|
| 旧累计 `paid_amount` 无法精确还原流水发生日期 | 0 到 1 阶段不做静默兼容；迁移生成 `occurred_on = due_date` 的系统回填流水并标记备注，无法匹配时失败暴露 |
| 服务费从逐笔改为月度汇总会破坏旧唯一约束 | migration 显式替换唯一约束，回填时按账期聚合旧数据 |
| `ledger_views` 多视图导致重复统计 | 查询和分析层必须按视图归属显式过滤，跨视图汇总必须去重或按指标定义取数 |
| 已有合同更正逻辑仍按 `paid_amount > 0` 判断 | Phase 1 先把所有非作废已收付条目回填为有效分摊并做失败暴露；Phase 2 再改为按分摊汇总金额或存在有效分摊判断 |
| 已生成服务费来源租金被更正跳过 | 既有服务费台账不自动重算或覆盖，派生服务费来源不一致风险并交由人工处理；未生成服务费的账期按修正后实收进入后续月度生成 |
| 前端路由仍叫 `/finance/ledger` | Phase 4 同步收口路由、页面目录、组件名、面包屑和导出文件名，目标路由为 `/operations/ledger` |

## 8. 待实施前确认

以下问题不阻断首个后端底座切片，但会影响后续流水状态与审计设计：

- 收付流水作废、更正、反向冲正的最小状态机。
- 凭证附件是否需要下载审计。
- 历史 `paid_amount` 回填流水的备注和来源字段是否需要专门枚举。

## 9. 验证命令

优先：

```bash
make check
```

定向：

```bash
cd backend && uv run --frozen --extra dev pytest --no-cov tests/unit/models/test_contract_group_model.py -q
cd backend && uv run --frozen --extra dev pytest --no-cov tests/unit/services/contract/test_payment_flow_service.py -q
cd backend && uv run --frozen --extra dev pytest --no-cov tests/unit/api/v1/test_ledger_api.py -q
cd frontend && pnpm test -- --run OperationsLedgerPage
```
