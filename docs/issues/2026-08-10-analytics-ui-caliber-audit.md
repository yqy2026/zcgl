# 分析/报表口径一致性前端审计（§3.2 指标前置）

- **日期**: 2026-08-10
- **来源**: GitHub issue #69（wayfinder 决策地图）
- **关联需求**: PRD §3.2（关键报表口径一致性问题 ≤ 2/月）、§5（视图模型）、§6.6（经营款项与账期归属）、REQ-ANA-001（7.7）、REQ-CUS-002（7.4）、REQ-RNT-006（7.3）
- **性质**: 只读前端审计 + 后端证据核验，未改动任何 src/ 代码

## 调研目的

产品指标「关键报表口径一致性问题 ≤ 2/月」的第一道防线在前端展示层。本报告审计全部经营口径相关页面对 PRD 口径规则的符合度，输出「必须修 / 建议修 / 观察项」清单，供 wayfinder 地图 #69 决策。

## 审计范围（页面清单）

| 页面 | 路由 | 说明 |
|------|------|------|
| `AssetAnalyticsPage.tsx` | `/analytics` 与 `/assets/analytics`（两路由均映射本页，`AppRoutes.tsx:69-82`） | 经营分析综合页 |
| `DashboardPage.tsx` + `useDashboardData.ts` | `/dashboard` | 资产看板（仅资产/面积指标，无经营口径指标） |
| `OperationsLedgerPage.tsx`（1884 行） | `/operations/ledger` | 经营台账（四类视图 + 收付流水） |
| `ProjectDetailPage.tsx` | `/project/:id` | 项目详情（经营摘要 / 项目分析 / 租户客户区） |
| 支撑组件/服务（只读） | — | `ViewModeSegment.tsx`、`AnalyticsStatsCard.tsx`、`BasicFiltersSection.tsx`、`useAssetAnalytics.ts`、`useAnalytics.ts`、`analyticsService.ts`、`dataScopeStore.ts`、`ledgerService.ts`、`projectService.ts`、`types/analytics.ts`、`types/ledger.ts`、`types/project.ts` |

辅助后端证据（只读核验导出与 view_mode 契约）：`backend/src/api/v1/analytics/analytics.py`、`backend/src/services/analytics/analytics_service.py`、`backend/src/services/analytics/analytics_export_service.py`、`backend/src/services/contract/ledger_export_service.py`。

---

## 逐条规则结论

### 规则 1：四类视图分区（终端租户收缴 / 运营方收入 / 运营方成本 / 服务费结算）

| 页面 | 结论 | 证据 |
|------|------|------|
| 经营台账 | ✅ 基本符合：四个视图以 Segmented 明确分区 | `OperationsLedgerPage.tsx:59-64`（VIEW_OPTIONS）、`:1180-1187`（Segmented） |
| 项目详情经营摘要 | ✅ 符合：五分区按钮（含经营净流入） | `ProjectDetailPage.tsx:480-511` |
| 经营分析页 | ❌ 不符合：无任何四类视图/经营结果分区；REQ-ANA-001 要求的「终端租户收缴、运营方收入、运营方成本、经营结果」在综合页完全不渲染 | `AssetAnalyticsPage.tsx:236-256` 仅渲染 RevenueStatsGrid（总/自营租金/代理服务费/实收/收缴率/客户双指标）；后端已返回的 `operational_metric_groups`（terminal_collection / operator_income / operator_cost / operating_result）经 `analyticsService.ts:357-380` 适配后**无任何 tsx 渲染点**（全库 grep 为空），属死数据 |

子问题（命名与拆分可见性）：

- ❌ 「自营租金收入」命名与 PRD「承租转租租金收入」不一致（运营方收入必须拆分为承租转租租金收入 + 代理服务费收入）。`AnalyticsStatsCard.tsx:329` title="自营租金收入"，映射 `self_operated_rent_income`。PRD §6.6：运营方收入拆分「承租转租租金收入」与「代理服务费收入」。「自营」为账期/模式外自定义词，容易与「自有经营」混淆。
- ⚠️ 台账「终端租户收缴」视图内无法区分代理直租租金与承租转租下游租金：`LedgerEntry` 无关系模式字段（`types/ledger.ts:17-40`），列表无「模式/直租/转租」列；PRD 要求代理直租租金进入终端租户收缴（运营方需跟进终端付款），但需在界面可辨认。
- ⚠️ 台账「运营方收入」视图未显式拆分转租租金收入 vs 代理服务费收入（服务费结算独立成 Tab，结构上成立，但运营方收入列表本身无拆分提示，口径依赖用户对四视图含义的既有认知）。

修复建议：

1. 综合页渲染 `operational_metric_groups` 四分组卡片（与台账、项目摘要同口径），并补「经营结果（经营净流入/账面差额）」；
2. 「自营租金收入」→「承租转租租金收入」；
3. 台账列表增加「模式」列（直租/转租）或在终端租户收缴视图内做子分区标签。

### 规则 2：逾期只属终端租户收缴

- ❌ 前端逾期派生缺少视图守卫：`isDerivedOverdue`（`OperationsLedgerPage.tsx:209-218`）仅排除 `operator_cost` 与 `voided`，**未排除 `operator_income`**。状态列（`:885-887`）对 运营方收入 视图同样套用逾期判定——只要后端返回 `due_date`（台账条目统一带到期日字段，`types/ledger.ts:21`），运营方收入/未收清条目就会被标「逾期」，违反「运营方收入不产生逾期，逾期只属于终端租户收缴」。
- ✅ 服务费结算视图使用独立列（无逾期逻辑，`:991-998`），项目详情经营摘要不展示分组逾期值（仅项目分析趋势展示逾期，`ProjectDetailPage.tsx:982`，属终端收缴口径）。

修复建议：`isDerivedOverdue` 第一行改为 `if (view !== 'terminal_collection' || entry.payment_status === 'voided') return false;`，并补单测（operator_income 带过期 due_date 不得标逾期）。

### 规则 3：账期归属

- ✅ 经营台账双筛选：账期范围（月粒度，默认当月）+ 流水日期（`OperationsLedgerPage.tsx:1256-1277`），参数 `year_month_start/end` + `flow_occurred_on_start/end`（`:305-308`），符合「台账默认按账期月份筛选，同时支持收付发生日期筛选」。
- ✅ 经营分析归属契约：后端 `ANALYTICS_PERIOD_ATTRIBUTION_BASIS = "rent_year_month"`（`analytics_service.py:44-46`，按租金账期归属），前端展示「账期归属」标签（`AnalyticsStatsCard.tsx:433-435`，来自 `period_attribution_label`）。
- ⚠️ 经营分析筛选器标签为「时间范围」（日粒度，`BasicFiltersSection.tsx:98-106`），未声明为账期月份口径，与台账的「账期范围 + 流水日期」双控件相比容易让用户误以为是发生日期筛选。后端把 date_from/date_to 截断为 YYYY-MM 账期边界（`analytics_service.py:319-343`），但前端无任何文案提示。

修复建议：经营分析筛选器改月粒度并标注「账期范围（按租金账期归属）」；若后端支持，再补发生日期筛选。

### 规则 4：view_mode UX（PRD §5 / REQ-ANA-001）

- ✅ 选择器存在：经营分析页与看板均渲染 `ViewModeSegment`（`AssetAnalyticsPage.tsx:138`、`DashboardPage.tsx:105`）；单一视角用户不显示（自动采用唯一视角，`ViewModeSegment.tsx:11-13`），符合「范围只有一种视角则自动采用」。
- ❌ **双视角默认猜选「owner」**：`resolveDefaultViewMode`（`dataScopeStore.ts:88-102`）在同时含 owner/manager 且无持久化选择时返回 `'owner'`——这正是 PRD §5 明令禁止的「不得从绑定顺序或展示偏好猜选；需要单一视角的分析端点要求用户明确选择」。后果：
  - 前端永远携带具体 view_mode（`analyticsService.ts:171-185` appendViewMode），后端综合端点的混合范围硬拒绝（`analytics.py:45-56`，「请选择 owner 或 manager 视图」）**永远不会被触发**，「请选视图」提示在产品上不可达；
  - 用户首次进入即看到 owner 口径数据，口径选择被静默固化（localStorage `data-scope:view-mode`），混淆风险高。
- ⚠️ `ViewModeSegment.tsx:22` `value={currentViewMode ?? 'owner'}` 对 null 静默回退 owner。
- ⚠️ 项目详情「项目分析」区正确渲染抑制标记（`ProjectDetailPage.tsx:935-937` 金色 Tag「客户指标需选产权方或运营方视图」+ `:168-169` formatSuppressedMetric 输出「需选视图」），符合「项目分析端点置空客户双指标并标记，其余照常渲染」；但**页面本身没有任何视图选择器**，用户无法在本页解除抑制，必须跳转 /analytics——抑制标记变成了死胡同。

修复建议：

1. 双视角用户首次进入分析类页面时强制显式选择（模态「请选择产权方/运营方口径」或在选择前不发起请求），选择前允许「不做选择」则发 `view_mode=all` 让后端硬拒绝并展示其错误提示；移除 localStorage 静默默认 owner；
2. 项目详情页补充视图选择控件（复用 ViewModeSegment），选择后重查项目分析接口。

### 规则 5：客户双指标（REQ-CUS-002 / REQ-ANA-001）

- ✅ 经营分析综合页：客户主体数/客户合同数（`AnalyticsStatsCard.tsx:373-391`）来自综合端点，该端点后端对混合范围硬拒绝（`analytics.py:45-56`），且前端总是携带具体 view_mode——单视图契约成立。
- ⚠️ 项目详情「租户/客户」卡片（`ProjectDetailPage.tsx:857-910`）：客户主体数 = `projectTenants.length`、客户合同数 = 合同数求和，由 `getProjectTenants(projectId)`（`projectService.ts:187-210`）拉取，**不带 view_mode 参数、无任何抑制/标记渲染**。若后端在混合范围下计算该汇总，即违反「客户双指标无论在哪个端点暴露都不得在 scope_mode=all 下计算」。前端侧无法自行证明合规——需后端契约核验（建议后端按 REQ-ANA-001 契约处理：混合范围置空 + 标记，前端补「需选视图」渲染）。
- ✅ 项目分析 `mode_summaries` 客户数走 `formatSuppressedMetric`（`ProjectDetailPage.tsx:956`）——符合抑制契约。

修复建议：与后端确认 getProjectTenants/项目分析的 view 契约；前端对租户/客户卡片补抑制标记渲染与视图选择联动。

### 规则 6：导出带口径版本标记（REQ-ANA-001）

- ✅ 经营分析导出：后端导出表含「口径版本」列（`analytics_export_service.py:27` 的 `("口径版本", ("metrics_version",), "")`），前端 UI 同步展示口径版本 Tag（`AnalyticsStatsCard.tsx:430-432`），导出请求携带 view_mode（`useAssetAnalytics.ts:74-95` → `analyticsService.ts:503-548`）。符合。
- ⚠️ 经营台账导出：`OperationsLedgerPage.tsx:683-697` → `ledgerService.exportLedgerEntries`（`ledgerService.ts:67-89`）→ `/ledger/entries/export`（`ledger.py:208`），后端 `ledger_export_service.py` 无任何口径版本标记（grep 无 `口径版本/metrics_version`）。台账导出属 REQ-RNT-006 查询导出，可论证不强制，但为口径可追溯一致建议补版本标记。
- ⚠️ 前端导出文件名 `analytics_<ts>.xlsx`（`analyticsService.ts:187-191`）无版本信息（仅外观问题）。

修复建议：台账导出补「口径版本 + 账期归属」列（与综合导出对齐）。

### 规则 7：「利润」词规避（PRD §6.6 末段）

- ✅ 全前端无「利润」字样（grep 为空）。
- ✅ 项目详情正确使用「经营净流入（已登记实收实付）」+「账面差额（应收应付）」（`ProjectDetailPage.tsx:506-509`，detail 展示 accrual_net_amount）。
- ❌ 经营分析页核心指标使用「净收益」：`AnalyticsStatsCard.tsx:177`（概览网格）、`:251`（财务指标网格），来自 `financial_summary.total_net_income`，且该值由前端**客户端派生**（`dataConversion.ts:195-199`：年收益 − 年支出）。「净收益」不在 PRD 口径词典（应使用 经营净流入 / 账面经营差额），且客户端自行计算会计式差值违背「不做会计收入确认」边界；同时 PRD 口径的「经营结果」（operating_result.cash_net_amount / accrual_net_amount）已取回但从未展示（见规则 1）。

修复建议：删除/改名「净收益」卡片为「经营净流入（已登记实收实付）」并改由 `operational_metric_groups.operating_result` 渲染，删除客户端 net_income 派生（`dataConversion.ts:195-199`）。

### 规则 8：服务费结算（§6.6 汇总生成）

- ✅ 台账「服务费结算」视图按账期/协议汇总展示：账期、来源租金台账（`source_ledger_ids` 多来源）、计算基数、费率、应收/实收/状态（`OperationsLedgerPage.tsx:928-1038`，汇总表 `:1457-1492`），不逐笔展示，与「服务费应收按租金账期月份/项目/委托协议/产权方汇总生成」展示口径一致（聚合由后端承担）。
- ⚠️ 查询入口要求手工输入合同组 ID 或项目 ID（`OperationsLedgerPage.tsx:1426-1450`、`serviceFeeQuery` enabled 条件 `:351`），无全局账期范围筛选，与其余三视图的「账期+流水日期+项目+合同+资产+主体」筛选能力不对称；批量对账场景不便。

修复建议：服务费结算视图补账期月份筛选（服务费按账期归属，按账期范围查询即可），并支持按产权方筛选。

---

## 汇总

### 必须修（口径违规，直接影响「口径一致性问题 ≤ 2/月」）

| # | 问题 | 位置 | 修复方向 |
|---|------|------|----------|
| M1 | 双视角默认猜选 owner，绕过「请选视图」强制选择契约 | `dataScopeStore.ts:88-102`、`ViewModeSegment.tsx:22` | 首访强制显式选择；未选择不静默发具体 view_mode |
| M2 | 经营分析页无四类视图/经营结果分区；`operational_metric_groups` 死数据 | `AssetAnalyticsPage.tsx:236-256`、`analyticsService.ts:357-380` | 渲染四分组卡片 + 经营结果 |
| M3 | 「净收益」核心指标名 + 客户端派生会计式差值 | `AnalyticsStatsCard.tsx:177,251`、`dataConversion.ts:195-199` | 改名并改用 operating_result（经营净流入/账面差额） |
| M4 | 逾期派生缺少 operator_income 守卫 | `OperationsLedgerPage.tsx:209-218,885-887` | 逾期仅 terminal_collection 可派生，补测试 |
| M5 | 「自营租金收入」命名 ≠ PRD「承租转租租金收入」 | `AnalyticsStatsCard.tsx:329` | 改名对齐口径 |

### 建议修（口径可辨性与体验）

| # | 问题 | 位置 |
|---|------|------|
| S1 | 台账终端租户收缴/运营方收入视图无直租-转租、转租租金-服务费拆分可见性 | `OperationsLedgerPage.tsx`、`types/ledger.ts:17-40` |
| S2 | 项目详情无视图选择器，抑制标记成死胡同 | `ProjectDetailPage.tsx:912-992` |
| S3 | 经营分析「时间范围」筛选未声明账期口径 | `BasicFiltersSection.tsx:98-106` |
| S4 | 台账导出无口径版本标记 | `backend/src/services/contract/ledger_export_service.py` |
| S5 | 服务费结算视图无账期/产权方全局筛选 | `OperationsLedgerPage.tsx:1426-1492` |
| S6 | 项目详情「租户/客户」客户双指标无 view_mode 契约证据与抑制渲染 | `ProjectDetailPage.tsx:857-910`、`projectService.ts:187-210` |

### 观察项（非违规，记录在案）

| # | 观察 | 位置 |
|---|------|------|
| O1 | Dashboard 导出按钮为空实现（handleExport 注释占位） | `DashboardPage.tsx:63-66` |
| O2 | `useDashboardData.ts` 已无调用方（DashboardPage 使用 `useAnalytics`） | `useDashboardData.ts` |
| O3 | 综合导出文件名不含版本信息（仅外观） | `analyticsService.ts:187-191` |
| O4 | 经营台账页面（查询类端点）无 view 选择器，混合范围下按统一解析器过滤，逾期按条目派生——与 REQ-AUTH-002 一致，但需注意 M4 修复后与后端 due_date 契约的一致性验证 | `OperationsLedgerPage.tsx` |
| O5 | 看板仅展示资产/面积指标，标题「资产管理看板」，与经营口径无冲突 | `DashboardPage.tsx` |

## 建议测试用例（修复时补）

1. `isDerivedOverdue`：operator_income 条目带过期 due_date 且未收清 → 不显示「逾期」（当前会显示，红测）。
2. `resolveDefaultViewMode`：双视角 + 无持久化选择 → 不返回 owner/manager（应进入「请选视图」态）；单视角 → 自动采用。
3. ViewModeSegment：currentViewMode 为 null 时不回退 owner 显示。
4. RevenueStatsGrid：metrics_version 为空时「经营结果/净流入」仍由 operating_result 渲染；「净收益」文案不存在。
5. 服务费结算视图：按账期范围查询返回聚合条目（非逐笔）。

---

## 参考

- PRD §3.2、§5、§6.6、§7.4（REQ-CUS-002）、§7.7（REQ-ANA-001）、§7.3（REQ-RNT-006）
- wayfinder 决策地图：issue #69
