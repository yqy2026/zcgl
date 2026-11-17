# 资产运营 v5 原型对齐收口（prototype-alignment）

> 状态：🔄 进行中（2026-11-17 开出）
> 依据：`frontend/prototype/asset-ops-v5.html`（布局/文案/交互终稿）+ `asset-ops-v5-handoff.md`（业务规则）。
> 前提裁决：生产已确立「列表 + 常驻详情栏 + URL 状态 + 预览-确认命令」的实现模式（V1–V4 验收）；原型三栏/弹窗形态按**功能等价**映射（每个控件、每条信息、每个状态必须在生产出现），不做像素级复刻。handoff 明示「在现有前端工程里按既有模式重新实现」。

## 一、差距总表（2026-11-17 逐页对比结论）

| # | 区域 | 原型要求 | 生产现状 | 处置 |
|---|------|----------|----------|------|
| G1 | 本月（首页） | 4 张任务卡 + 随时处理区 + 完成进度 + 逾期排序/折叠/登记卡 | **整页缺失**；根路径 `/` 重定向到已删除的 `/dashboard`（404） | WP1 新建 |
| G2 | 菜单/外壳 | 本月（未完成件数徽标）/报送/物业/合同（分组标题）/上游合同/终端合同/台账/档案（红字 缺 N 份）/数据导入；录入是合同页内按钮非菜单 | 菜单 8 项乱序、无本月、无徽标、录入挂菜单 | WP1/9 |
| G3 | 物业 | 分段筛选（全部/纳入报送/空置可租/不可租·非经营/缺产权证 带数量）、项目分组表格、列（业态/产权方/面积/性质/考核/出租状态含租户·至/产权证）、租赁时间轴、空置原因+预计起租、拆分/合并弹窗、导出台账、批量导入入口 | 简表 5 列 + 重命名 + 产权证关联；后端列表缺 owner/project 名称、考核状态、租户、产权证状态、状态筛选与计数 | WP2 |
| G4 | 终端合同 | 筛选 6 项带数量（生效中/180 天内到期/租金未到账/押金未结清/缺扫描件/已结束）、搜索含已结束、列（租户·合同号/单元 合并 N/模式/上游 未录入黄字/租期至 越界红/月租金+到账状态/押金+状态/扫描件） | 2 个 checkbox 筛选、5 列；后端 filter 仅 2 值、列表缺租户名/单元标签/月租/押金/扫描状态 | WP3 |
| G5 | 上游合同 | 到期框（≤90 红/≤180 黄）、版本链 chips（旧/当前/续签中）+登记续签/到期不续签、扫描件标签、付款计划按递增阶段（期间/月租/期数/进度/合计）、资产单元×终端合同矩阵 | ChainRow 链接 + rent_summary 摘要 + 计数；无阶段进度表、无单元矩阵、无到期色框 | WP4 |
| G6 | 报送 | 报送记录横排卡片、快照只读态、**报送说明固定句式**（项目数/万平米/宗数/出租率，浅蓝高亮）、明细列（产权方/业态/项目/地址/土地/可租/已租面积/可出租物业数/已出租物业数/出租率）+ 只看未出租 | 三 Tab + TotalsGrid + 明细（列集不同）；无固定句式、无历史卡片条（快照 Tab 内为逐期选择） | WP5 |
| G7 | 数据导入 | 四步条（新增）/三步（更新）、模板说明卡、**右栏导入批次列表（混排）**、更新模式第一步「导出当前台账」 | 两步卡（暂存+上传）+ 批次状态；无批次历史列表、无四步条、导出端点未接线（`POST /imports/templates/update` 已存在） | WP6 |
| G8 | 终止/退租 | 类型三选一卡（到期/提前/协商）、退租日期、**房屋交接**、押金结算、影响说明 | 独立操作页（生产模式）；类型是**自由文本 Input**（半成品 bug）、交接状态未暴露 UI | WP7 |
| G9 | 档案 | 顶部 4 完成率卡（已有/应有 · % + 4px 进度条）+ 右侧拖放区 | 完成情况表 + 文件选择按钮（等价信息、布局不同） | WP8 |
| G10 | 录入已签合同 | 弹窗；租户/产权方**选择**；单元多选 chips | 独立页（生产模式保留）；租户/出租方/产权方/运营方是**手输 Party ID** | WP9 |

已完成对齐（无需处理）：台账三轴矩阵+格子溯源+登记/撤销/导出（V2）、对账单纸面+盖章+顺延+更正链（V2）、押金四类+终止结算（V2）、报送草稿/门槛/快照差异/撤回/导出 CSV（V3）、考核范围草稿-预览-生效（V3）、三表导入+差异勾选+整批撤销（V4）、档案矩阵+批量配对（V4）、变更时间线面板、四态、批量配对拖拽。

## 二、工作包

### WP1 本月页 + 外壳（核心）
- 后端新增 `GET /api/v1/monthly-workbench?month=YYYY-MM`（无状态派生聚合，resource=asset_ops, action=read）：
  - `progress{total,done}`：仅计 4 类截止日任务（待付承租租金笔数 + 未到账终端租金笔数 + 待办管理费对账物业数 + 报送 1 件）
  - `rent_payments[]`：承租合同 × 账期（当月+往月逾期未付），含 due/paid/remaining、due_date（月付 25/季付 15）、days_overdue、状态
  - `rent_collections[]`：转租终端合同 × 账期（当月未到账+往月欠租），同上
  - `management_fees[]`：上月各委托物业 {owner, statement_id, status(collecting|pending_stamp|confirmed|upcoming/missing), base, fee, collected/total 户数}
  - `occupancy_report{period, submitted, rate, m, n, delta_vs_prev, gate_reasons}`
  - `anytime{expired_upstream[], expiring_upstream[], archive_gaps[], deposits_pending[], pending_scope_units[]}`
  - 复用既有 service：rent_ledger_query_service、deposit_query_service、management_fee_*、occupancy_report_draft、archive_matrix、contract_projections、assessment_scopes
- 前端 `MonthlyPage`（`/asset-operations/monthly`）：页头（日期行+大标题+进度条）、2×2 任务卡（排序/折叠/点击行打开既有登记面板或跳转）、随时处理区（红框到期、半年内到期、档案缺漏、押金四类、年中新增确认）
- 外壳：菜单重排+改名+徽标（本月 未完成 N；档案 缺 N 份）；`/` 重定向 → monthly；`constants/routes.ts` REDIRECTS/NOT_FOUND_REDIRECT 同步；录入菜单项移除（路由保留，合同两页加「＋ 录入已签合同」主按钮）

### WP2 物业页对齐
- 后端：`GET /asset-units` 增 `filter`（all|in_assessment|vacant|non_rentable|missing_certificate）+ 响应行补 `owner_party_name/project_name/assessment_included(v当年)/current_tenant_name/current_contract_end_date/certificate_count`；响应加 `counts{...}`（各筛选数量）；新增 `GET /asset-units/export`（xlsx，列同表格）
- 前端：分段筛选（Segmented 带数量）、项目下拉、搜索占位符对齐（地址、单元、租户、产权证号）、按项目分组行（组头折叠）、列补齐、详情栏加：空置原因块（chips+预计起租月 → PUT vacancy-note）、租赁时间轴（上终端/下上游/斜纹空置/红线今天，点段跳合同）、合同链列表、「拆分 / 合并单元」弹窗（接 split/merge preview+commit）、「编辑基本信息」扩为多字段（PATCH 支持范围）、「导出台账」「批量导入单元」

### WP3 终端合同页对齐
- 后端：`filter` 增 `active|expiring_180|missing_scan|ended`（保留旧 2 值）；列表行补 `tenant_party_name/upstream_contract_number/unit_labels[](合并 N)/current_monthly_rent/current_month_collection{status,amount}/deposit_status/has_scan`；响应加 `counts{...}`；`q` 扩租户名
- 前端：Segmented 6 项带数量、列补齐（租户·合同号/单元/模式/上游 未录入黄字/租期至 越界红/月租金+到账状态/押金/扫描件）、搜索含已结束

### WP4 上游合同页对齐
- 后端：上游详情补 `payment_plan[]`（按租金阶段：期间/月租/期数/已付期数/下期/合计，lease 型）与 `units_matrix[]`（单元×面积×租户×终端合同号×租期至×月租×扫描状态）
- 前端：详情栏到期色框（≤90 红/≤180 黄/其他灰）、版本链 chips 化＋「＋ 登记续签合同」「到期不续签」直达（保留生命周期操作页承接）、扫描件状态标签（缺=红虚线）、付款计划阶段表（ContractRentPanel 内）、单元×终端矩阵表、列表行「＋ 录入已签合同」按钮

### WP5 报送页对齐
- 后端：新增 `GET /occupancy-reports?operator_party_id=&year=`（历史列表：period/rate/committed_at/scope_version/状态）；draft 响应补 `statement_paragraph{...}`（固定句式 4 条的数字，含经营性/非经营性项目数、万平米、宗数、出租率）
- 前端：报送记录横排卡片（含当月草稿卡）、报送说明固定句式块（数字浅蓝高亮）、明细表列对齐＋「全部/只看未出租」Segmented＋合计行

### WP6 导入页对齐
- 后端：新增 `GET /import-batches?offset&limit`（批次历史，两模式混排）；模板说明元数据（`GET /imports/templates/create` 响应或常量对齐前端）
- 前端：四步条（新增模式）/三步（更新模式）、「1 · 下载模板」卡（三表列说明）、更新模式「1 · 导出现有台账」接 `POST /imports/templates/update`、右栏批次列表

### WP7 终止表单修正
- 前端：终止类型改三选一卡（expiry/early/mutual 对齐后端枚举）、房屋交接 select（pending/completed/not_applicable）、押金结算区块文案对齐原型；补测试

### WP8 档案页布局对齐
- 前端：完成率区改顶部卡片行（每类 已有/应有 · % + 4px 进度条）+ 右侧拖放区（AntD Upload.Dragger，多选，接批量配对）

### WP9 录入页选择器
- 前端：租户/出租方/产权方/运营方改主体选择器（复用 OwnerPartySelect 模式或 party 搜索 Select）；单元多选改 chips 多选（后端候选）；合同页 ＋ 按钮预选类型

### WP10 收口
- 全量 `make check` + 定向 e2e；`docs/specs/domain-model.md`（新端点/新字段）、`docs/specs/api-contract.md`（新端点）、`docs/traceability/requirements-trace.md`（实现证据）、CHANGELOG

## 三、裁决记录

1. **本月页任务模型**：handoff「当月任务清单由后端按月生成，未完成事项结转到下一期」→ 实现为**无状态派生**（每次按当前事实重算）。逾期/往月欠租项天然带出拖延天数，等价于「上月未完成事项带入」；不建持久任务表、不做每月 1 日定时机（避免 0→1 阶段引入调度复杂度，数据口径始终=当前事实）。
2. **录入弹窗 vs 页面**：保留生产独立页（有会话有效期/幂等键/两步向导），原型弹窗形态不复刻；菜单项移除以对齐「录入从合同页发起」。
3. **示意按钮**（导出台账/导出 Excel/打印/下载外发/编辑基本信息）：原型标 data-stub「开发按常规实现」→ 本轮实现物业导出与既有导出；「下载/外发」按文档外发需求挂后续（不在本轮）。
4. **布局等价映射**：上游三栏 → 列表+详情栏（中栏信息进详情栏）；对账单/终止等弹窗 → 生产已有页面模式。
