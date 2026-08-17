# 模块点检问题报告（2026-08-17）

## 1. 背景与目的

按「启动项目并点检各功能模块」的目标，对土地物业资产运营管理系统执行一次全模块点检：启动前后端 → API 层冒烟探测 → 前端页面层浏览器实测，输出问题清单与修复建议。参考既有验收抽验报告 `docs/issues/2026-08-09-mvp-g1-acceptance-dryrun.md` 的风格，本次为常规点检（非正式验收），发现的问题按严重级别登记，供后续排期修复。

## 2. 启动环境与验证方式

| 项 | 结果 |
|---|---|
| PostgreSQL | ✅ 本机 5432 运行中（`postgresql+psycopg://postgres@localhost:5432/zcgl_db`） |
| Redis | ✅ `127.0.0.1:16379` 可达（PING → PONG；经 Docker backend/wslrelay 转发；Docker CLI daemon 本身不可达但端口转发存活；`.env` 中 `REDIS_ENABLED=true` 按文档要求连接失败不降级，实测连接成功） |
| 后端 | ✅ `cd backend && uv run --frozen --extra dev python run_dev.py` → uvicorn 8002，`Application startup complete`，枚举数据初始化 9 类型/38 值，DB 健康检查通过，缓存预热成功 |
| 前端 | ✅ `cd frontend && corepack pnpm dev`（本机 `pnpm` 不在 PATH，经 corepack 激活 pnpm@10.34.5）→ Vite 6.4.3 :5173 |
| 登录 | ✅ admin / admin123（`Development Administrator`，无界数据范围 unrestricted，前端恒解析 view_mode=owner） |
| API 探测 | 70 条 GET 冒烟 + 33 条复核/定向探测（脚本留存 `tmp/api_probe*.ps1`、`tmp/api_probe*_results.json`） |
| 页面层 | Playwright（系统 Chrome 通道）20 个路由实测 + `/analytics` 深探（截图 `tmp/screenshots/`、汇总 `tmp/ui_point_check.json`、`tmp/analytics_deep.json`） |

> 启动备注：worker 子进程日志出现一次 `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f510'`（🔐 emoji）——见缺陷 2.5。

## 3. 模块点检结果

### 3.1 资产管理（assets / asset-custom-fields / projects）

- 资产列表、`/assets/all`、分类/确权状态/物业性质/使用状态下拉、资产详情、租赁汇总、审核日志、历史记录、附件列表、自定义字段值：**全部 200**。
- 工作台统计与资产列表渲染正常（资产总数 19、管理总面积 17,250.17㎡、可租面积 27,856.58㎡、整体出租率 91.4%，与 `statistics/overall` 91.47% 一致）。
- ⚠️ 资产自定义字段类型接口路由错位（缺陷 2.1）。
- ⚠️ `GET /assets/ownership-entities` 返回空（观察项 3.5.1）。

### 3.2 项目运营（projects）

- 列表、详情、统计概览、analytics、关联资产、收付款摘要、风险提示、租户客户摘要、下拉选项：**全部 200**，页面渲染正常。

### 3.3 租赁合同与经营台账（contract-groups / contracts / ledger / extraction）

- 合同关系列表、详情、关系内合同列表、台账条目（带项目/账期筛选）、经营口径汇总（`/projects/{id}/ledger-summary` 200，应收/实付派生正确）：**全部 200**。
- 合同解析能力端点（contract/property_certificate 目标、PDF/图片输入、页数上限）：200。
- `GET /extraction-sessions` 405 为设计（无列表端点，创建走 POST、读取走 `/{session_id}`）；`ledger/payment-flows|service-fees` 无参 422 为参数契约要求（须提供 target_type/target_id 或筛选维度）——均非缺陷（见 §5 澄清）。

### 3.4 数据分析报表（statistics / analytics / occupancy）

- 22 项统计端点（dashboard/summary/basic/comprehensive/financial-summary/occupancy-rate 系/area 系/distribution 系/trend/cache）+ 6 项 analytics/occupancy 端点：**正确参数下全部 200**，数值口径自洽（出租率 91.47%、经营口径总收入 ¥600,000/实收 ¥100,000/收缴率 16.67%、应付出租成本 ¥6,216,000 等）。
- ⚠️ 经营分析页前端图表层抛出未捕获异常（缺陷 2.4）。
- 说明：`analytics/comprehensive` 不传 `view_mode` 时对无界管理员返回 400 属口径设计（要求 owner/manager 视角），前端始终携带 view_mode（浏览器路径正常）。

### 3.5 组织架构 / 主体 / 角色 / 用户（organizations / parties / roles / users）

- 组织列表/树/搜索/统计、主体列表/客户摘要、角色列表/统计/权限清单、用户列表/详情：**全部 200**；页面渲染正常（总组织 1、主体 2、总角色 6、总用户 5）。
- 用户管理/组织架构页各有 1 条 antd `useForm` 未连接 Form 的 console 告警（缺陷 2.6）。

### 3.6 产权证管理（property-certificates）

- 证书列表/详情：**全部 200**，数据结构完整（证书编号「粤（2026）广州市不动产…」、类型、坐落、面积、附件）。页面渲染正常。

### 3.7 系统与其它（search / system / tasks / notifications / logs / enum-fields / excel）

- 全局搜索（q=广州 → 7 条）、历史、操作日志（今日 20/共 5,318 条）、通知未读数、任务执行态、字典类型/统计、excel 配置：**全部 200**；页面渲染正常（系统设置/数据策略包/日志/字典/搜索 20 页全部 loadOk）。
- ⚠️ 任务管理三个 GET 端点不可达（缺陷 2.2）。
- ⚠️ 枚举类别路径污染（缺陷 2.3）。
- `/ownership` 路由已下线（页面返回应用内 404 页），符合预期。

## 4. 页面层实测结果

Playwright 20 个路由（工作台/资产列表与详情/项目列表与详情/合同中心列表与明细/经营台账/经营分析/主体/用户/角色/组织/字典/日志/设置/数据策略/产权证/全局搜索/ownership）：**全部 loadOk、0 个 HTTP 请求失败（httpFailures=0）**；主要页面控制台无错误。
唯一异常集中在：
- `/analytics`：8 条 console error / 4 条 pageerror（`ExpressionError`，缺陷 2.4），图表仍渲染（canvas×4、svg×45、无骨架屏、无错误提示文案）；
- `/assets/{id}`：1 条 antd `Descriptions` span 合计告警；
- `/system/users`、`/system/organizations`：各 1 条 antd `useForm` 未连接告警；
- 登录页：1 条资源 `ERR_CONNECTION_TIMED_OUT`（非 API 资源，httpFailures 为空）。

## 5. 问题清单

### 2.1 【高】资产自定义字段类型接口：后端路由被遮蔽 + URL 污染 + 前端调用路径三方错位（asset-custom-fields）

- **现象**：
  - `GET /api/v1/asset-custom-fields/types` → **404**（后端已声明，`custom_fields.py:271`，但打开 OpenAPI 可见、运行时不可达）；
  - `GET /api/v1/asset-custom-fields/types/list[Any]` → 200（可用但 URL 含 Python 类型注解残留 `[Any]`，`custom_fields.py:272`，`include_in_schema=False`）；
  - 前端 `frontend/src/services/asset/assetFieldService.ts:257`（`getFieldOptions`）调用 **`GET /asset-custom-fields/types/list`** → **404**。
- **根因**：路由声明顺序缺陷——`@router.get("/{field_id}")`（`custom_fields.py:92`）声明在 `@router.get("/types")`（:271）之前，`/types` 被 `/{field_id}` 遮蔽（field_id="types" 查询不到 → 404）；同时存在一条历史遗留的 `[Any]` 垃圾 URL 路径，前端调用的是第三条不存在的路径，三方互不匹配。
- **影响**：资产自定义字段「字段类型选项」功能一旦有页面接入必然报错（当前无页面调用，单测均 mock HTTP，CI 未暴露）；OpenAPI 契约错误引导客户端。
- **建议**：将类型路由整理为单一规范路径（如 `GET /types` 移到 `/{field_id}` 之前或改为 `/types/list`），删除 `[Any]` 路径，同步前端 `assetFieldService` URL；补一个路由层测试钉住「`/types*` 不被 `/{field_id}` 吸收」。

### 2.2 【中】任务管理三个已声明 GET 端点被 `/{task_id}` 遮蔽（system/tasks）

- **现象**：`GET /api/v1/tasks/statistics`、`GET /api/v1/tasks/running`、`GET /api/v1/tasks/recent` 运行时均 **404**；OpenAPI 中三者均列出。
- **根因**：`tasks.py` 中 `@router.get("/{task_id}")`（:166）声明早于 `/statistics`（:331）、`/running`（:357）、`/recent`（:386），三者被当作 task_id 查询返回 404。
- **影响**：当前前端未调用（grep 无 `tasks/recent|running|statistics` 引用），属 API 契约/未来功能风险；任何 OpenAPI 客户端按文档调用即失败。
- **建议**：静态路径统一前置（或引入路径转换器约束 / UUID 校验让 `/statistics` 不匹配 `{task_id}`）；补路由可达性测试。

### 2.3 【中】枚举类别接口路径污染：/types/categories/list[Any]（system/enum_field）

- **现象**：`GET /api/v1/enum-fields/types/categories/list` → **404**；`GET /api/v1/enum-fields/types/categories/list%5BAny%5D` → 200（`enum_field.py:229` 路由字面量即 `list[Any]`），且该垃圾路径直接暴露在 OpenAPI 中。
- **根因**：同 2.1 的 `[Any]` 残留模式（`git log -S 'list[Any]'` 显示至少 `d412b91f`/`d71a74c4` 起即存在，属长期遗留）。
- **影响**：前端字典管理未调用该端点（`dictionary/manager.ts` 只走 `/enum-fields/types`），影响面为 API 契约正确性与文档污染。
- **建议**：路径改回 `/types/categories/list`，删除 `[Any]` 残留；与 2.1 一并排查全仓 `list[Any]`、`/types/list[Any]`、`monitoring.py` 内 mock 键 `"/assets/list[Any]"` 等同类残留。

### 2.4 【中】经营分析页图表库未捕获异常（@ant-design/plots）

- **现象**：`/analytics` 页面 4 次 pageerror + 6 次未捕获 Promise rejection：`ExpressionError: Unexpected character: }`，堆栈指向 `node_modules/.vite/deps/@ant-design/plots.js`（vite 预打包产物，行 64837 起）。数据与图表主体仍渲染（4 canvas、45 svg、概览/分布/经营口径/分区全部出数，无空态），但错误链上「图表初始化表达式求值」失败，导致错误监控持续上报噪音，且无法排除个别图表元素局部失败。
- **根因待定位**：`ExpressionError` 常见于 G2 表达式（如百分比 label formatter 被当作表达式字符串解析、数据序列含非法字符）或该库与当前数据的兼容问题；需逐个图表组件二分定位（`analytics` 页 Pie/Column/Line 等配置），并确认是否与「百分比小数位 label」或「零值系列」相关。
- **建议**：取现网数据在图表组件层最小复现；优先排查 `percentage`/`label.formatter` 传入的表达式字符串与空数据系列。
- **备注**：历史 CHANGELOG（`fix(mobile-menu)`）记录过该页图表在 1280×720 实测正常，需确认是否为本次数据（新增合同/台账种子）触发，还是浏览器/版本差异。

### 2.5 【低】后端启动日志 GBK 编码告警（Windows worker 子进程）

- **现象**：启动期 `src.main` 打 `🔐 Validating application secrets...` 日志时，`logging` emit 抛 `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f510'` —— `run_dev.py` 对 `sys.stdout/stderr` 的 UTF-8 包装只作用于 reloader 主进程，uvicorn multiprocessing worker 子进程（`multiprocessing.spawn`）未继承，控制台编码回退 GBK。
- **影响**：含 emoji 的日志行写入失败（该行丢失，仅记录 Logging error 自身）；不影响应用运行，但削弱排障可观测性（与 8/9 dryrun 报告的排障诉求相悖）。
- **建议**：为 worker 子进程统一设置 UTF-8（如 `PYTHONIOENCODING=utf-8` 或 logging handler 显式编码），或在启动入口对 spawn 子进程同样应用编码包装。

### 2.6 【低】antd 控制台告警与登录页资源超时

- 资产详情页：`[antd: Descriptions] Sum of column span in a line not match column of Descriptions.`（详情 `Descriptions` 的 span 合计与 column 配置不符，布局可能错位）；
- 用户管理/组织架构页：`Instance created by useForm is not connected to any Form element.`（查询表单的 useForm 实例未绑定 Form，属悬挂实例告警）；
- 登录页：1 次 `Failed to load resource: net::ERR_CONNECTION_TIMED_OUT`（非 API 资源，`httpFailures=0`，可能为外部字体/统计源超时）。

### 2.7 【观察项】数据口径疑点（非功能缺陷，待产品确认）

1. **`GET /assets/ownership-entities` 返回 `[]`**：服务读 `ownership` 表（按 data_status 正常查询，当前表空），而 19 条资产的 `ownership_entity` 文本列均带「广州国有资产管理集团有限公司」；前端 `constants/api.ts` 已定义 `OWNERSHIP_ENTITIES` 常量但无页面引用。若资产列表的「权属方」筛选接通该端点将恒为空。建议确认筛选数据源（文本列 vs ownership 实体表）。
2. **`statistics/financial-summary` 年收入/月租金全 0.00**：与经营分析页「经营口径总收入 ¥600,000 / 月实收 ¥100,000」不一致——该端点财务口径（资产财务字段）在种子数据中未填充；需确认最终口径。
3. **物业性质枚举词表不一**：`assets/property-natures` 返回 `["经营类"]`；`analytics/distribution?distribution_type=property_nature` 输出键 `经营性/非经营性`；`statistics/basic` 的 `property_nature.commercial/non_commercial` 均为 0。三处「物业性质」用语/取值口径不统一，建议统一。
4. **健康端点要求认证**：`/api/v1/system/health` 与 `/api/v1/admin/health` 未登录访问返回 **401**（登录态 200）。若用作外部健康探针/负载均衡器检查需带认证凭据或追加公开探活端点（如 `/healthz`），属部署可观测性设计观察项。

## 6. 非缺陷澄清（探测误判排除，避免后续重复排查）

| 现象 | 结论 |
|---|---|
| `GET /projects/search`、`GET /organizations/advanced-search` 404 | 真实契约为 POST（搜索/高级搜索是 POST 语义）；GET 落入 `/{project_id}`/`/{org_id}` 得 404 而非 405。功能正常；可选项：对静态路径方法与参数不匹配时更快给出 405/422 提示（可观测性改进，非缺陷） |
| POST 类接口裸探 403 | CSRF 双重提交防护的**预期行为**（`security_middleware.py` CSRFMiddleware；登录下发 `csrf_token` cookie，变更方法须带 `X-CSRF-Token`）；前端 `api/client.ts:397` 自动附带，浏览器流程正常 |
| `ledger/entries` 无参 422 | 参数契约要求至少一个筛选维度（project_id/asset_id/party_id/contract_id/账期/流水日期，`LedgerAggregateQueryParams`），设计中明确「至少需要一个筛选条件」 |
| `ledger/payment-flows`、`service-fees` 无参 422 | 要求 `target_type`+`target_id` 等必填参数，属契约要求 |
| `GET /extraction-sessions` 405 | 该资源无列表 GET（创建 POST、读取 `/{session_id}`），设计如此 |
| `analytics/comprehensive` 无 view_mode → 400 | 口径设计：客户双指标分析要求 owner/manager 单视角（`_get_analytics_perspective`）；前端 dataScopeStore 对 admin 恒解析 view_mode（owner），浏览器路径正常 |

## 7. 结论与建议

- **整体结论**：系统可正常启动运行，**8 大模块（资产/项目/合同台账/分析报表/组织主体/角色用户/产权证/系统功能）API 与页面主路径全部可用**，0 个 HTTP 请求失败；无数据丢失、无 500 级错误。本次点检为「可用但存在若干契约与前端告警问题」状态。
- **建议修复顺序**：
  1. 高优：2.1 资产自定义字段类型接口（三方错位，一修即闭环，含路由顺序 + URL 规范 + 前端路径 + 路由可达性测试）；
  2. 中优：2.2 tasks 路由顺序、2.3 enum `[Any]` 路径残留（同类根因，可合并一次「静态路径前置 + 残留清理」整改）；
  3. 中优：2.4 图表 ExpressionError（需在 analytics 图表组件层复现定位后修复）；
  4. 低优：2.5 日志编码、2.6 antd 告警；
  5. 口径确认：2.7 三项数据口径疑点由产品负责人认定。
- **环境备注**：本机 pnpm 需 `corepack pnpm` 激活；Docker CLI daemon 不可达但 Redis 端口转发（16379）正常；Playwright 用系统 Chrome 通道（`chromium_headless_shell-1208` 未安装）。

## 8. 证据留存

- 探测脚本与结果：`tmp/api_probe.ps1`、`tmp/api_probe_v2.ps1`、`tmp/api_probe_results.json`、`tmp/api_probe_v2_results.json`（API 层 103 条记录）
- 页面实测：`tmp/ui_point_check.js`、`tmp/ui_point_check.json`（20 页）、`tmp/ui_probe2.js`、`tmp/analytics_deep.json`（/analytics 深探）、`tmp/screenshots/*.png`（20 页截图）
- 端点源码证据：`backend/src/api/v1/assets/custom_fields.py:92/271/272`、`backend/src/api/v1/system/tasks.py:166/331/357/386`、`backend/src/api/v1/system/enum_field.py:229`、`backend/src/api/v1/analytics/analytics.py:56-60/94`、`backend/src/api/v1/assets/assets.py:405-418`、`backend/src/services/asset/asset_service.py:1068-1079`、`frontend/src/services/asset/assetFieldService.ts:254-279`、`frontend/src/services/analyticsService.ts:222-234`、`frontend/src/stores/dataScopeStore.ts:66-104`

## 9. 修复记录（2026-08-17，同日收口）

复核确认本报告全部缺陷指控属实，并发现两处报告未列的同族问题（见 9.8）。除 2.7 观察项（待产品确认，未动代码）与登录页外部资源超时（非本仓资源）外，全部修复：

### 9.1 缺陷 2.1 已修复（asset-custom-fields/types 三方错位）

- `custom_fields.py`：`GET /types` 路由整体前移至 `GET /{field_id}` 之前；删除 `@router.get("/types/list[Any]", include_in_schema=False)` 垃圾装饰器，规范路径唯一化为 `GET /types`。
- 前端 `assetFieldService.ts` `getFieldOptions` 改调 `/asset-custom-fields/types`（测试断言同步更新）。
- 新增路由层回归测试 `backend/tests/unit/api/v1/test_static_route_shadowing.py`（钉住 `/types` 先于 `/{field_id}` + 无 `[Any]` 路径）。

### 9.2 缺陷 2.2 已修复（tasks 静态端点遮蔽，含报告遗漏项）

- `tasks.py`：`/statistics`、`/running`、`/recent` 三端点前移至 `/{task_id}` 之前。
- **复核补充**：`GET /tasks/cleanup`（`tasks.py:627`，同样声明在 `/{task_id}` 之后）属同类遮蔽，报告 §2.2 未列出，一并前移修复。
- 可达性由 9.5 的全局守卫测试覆盖。

### 9.3 缺陷 2.3 已修复（enum 路径污染 + 同族残留清理）

- `enum_field.py:229`：路径 `/types/categories/list[Any]` → `/types/categories/list`（该函数无遮蔽问题，仅字面量污染）。
- `monitoring.py:178`：mock 键 `"/assets/list[Any]"` → `"/assets/list"`。
- 全仓 `list[Any]` 扫尾：路由路径残留仅上述两处，已清零（`tests/unit/api/v1/test_static_route_shadowing.py` 含全 api_router 级守卫，任何已挂载路由再出现 `[Any]` 即红）。

### 9.4 缺陷 2.4 已修复（/analytics 图表 ExpressionError，根因定位）

- **根因**（报告写作「待定位」，现已闭合）：`@ant-design/plots` v2 底层 G2 5 的 `parseOptionsExpr`（`@antv/g2/lib/utils/expr.js`）会对 spec 白名单键（`labels`/`style`/`encode`/`children`）内**以 `{` 开头且以 `}` 结尾的字符串**剥去首尾花括号后交给 `@antv/expr` 编译。饼图 label 配置 `content: '{name} {percentage}'`（G2 4.x 模板语法在 v2 下为死配置）剥壳成 `name} {percentage`，解析器遇 `}` 抛 `ExpressionError: Unexpected character: }` —— 与本报告 §2.4 报错逐字吻合，且 vite 预打包产物 `@ant-design_plots.js` 行 64837 的 sourcemap 反解指向 `@antv/expr@1.0.2`，与报告堆栈行号一致。
- **触发点两处**：`frontend/src/components/Analytics/chartComponents/AnalyticsPieChart.tsx`（/analytics 页 `AssetDistributionGrid` 的分布饼图）与 `frontend/src/components/Analytics/AnalyticsChart.tsx`（`AnalyticsPieChart` 导出，`innerRadius=0` 分支）。仓库内其余 `content: '{percentage}%'`/`'{value}%'` 因不以 `}` 结尾不满足编译条件（无告警，未改动）。
- **修复**：两处均改为 v2 语法 `label: { position: 'spider'（外环）/ 'inside'（内环）, text: (d) => …回调计算 名称+占比 }`，模板字符串全部消除，label 由 v1 死配置变为实际生效。

### 9.5 路由回归测试与运行时验证

- 新增 `backend/tests/unit/api/v1/test_static_route_shadowing.py` 5 用例：custom_fields `/types` 前置、tasks 四静态路径前置、enum categories 规范路径、各 router 无 `[Any]`、**api_router 全局无 `[Any]` 守卫**（延续 08-09 点检 `test_backup_layering.py` 的回归范式）。
- 运行时探针（TestClient 未登录，鉴权先于业务、后于路由匹配，401 即证明路由可达）：`/asset-custom-fields/types`、`/tasks/statistics|running|recent|cleanup`、`/enum-fields/types/categories/list` 全部由修复前 **404 → 401**；两个 `[Any]` 垃圾路径由 200 → **404**（已删除）；`/{field_id}` 动态路由行为不变。

### 9.6 缺陷 2.5 已修复（worker 子进程 GBK 编码）——含复核补修

- 第一轮修复：`run_dev.py` win32 分支新增 `os.environ.setdefault("PYTHONIOENCODING", "utf-8")`（`multiprocessing.spawn` worker 继承进程环境，解释器启动即 UTF-8；`setdefault` 不覆盖用户显式配置）。
- **复核偏差（2026-08-17 补修）**：复核实测该修复**未消除启动 Logging error**——`UnicodeEncodeError: 'gbk'` 依旧出现。探针定位：抛错流是 `security/logging_security.py` 的 **`logging.FileHandler(log_file)`，默认以 locale 编码（本机 cp936/strict）打开文件**，而 `PYTHONIOENCODING` 只影响 std 流、对 FileHandler 无效（spawn 探针证实：uvicorn reload worker 即使继承到 `PYTHONIOENCODING=utf-8`，`__stderr__` 仍为 gbk；FileHandler 探针显示 `enc='cp936' errors='strict'`）。
- **补修**：`logging.FileHandler(log_file, encoding="utf-8")`。TDD：新增 `backend/tests/unit/security/test_logging_security.py` 2 用例（mock 捕获 `basicConfig` 入参断言 FileHandler 必须 utf-8；用捕获的 FileHandler 端到端落盘 emoji 行；pytest logging 插件占用 root handlers 使真实 basicConfig 幂等跳过，故采用契约捕获）。red（修复前 2 failed）→ green（2 passed）。
- **真实启动复验**：后端重启后启动日志**无 Logging error**，`🔐 Validating application secrets...` 正常输出且**落盘 `logs/app.log`**（修复前文件仅有 `main.py:140` 的无 emoji 行，`:146` 的 emoji 行被 cp936 丢弃；修复后两行均落盘）。

### 9.7 缺陷 2.6 已修复（antd 控制台告警）

- **Descriptions span**（`AssetDetailInfo.tsx`）：antd 仅在某行 span 合计**超出**列数时告警（`useRow.js` 的 `exceed` 分支；尾行不足会被自动拉伸补齐，不告警）。`所在地址 span={2}` 在 sm（2 列）下超出、`接收协议文件 span={2}` 在 xs（1 列）下超出，两处 `span={2}` 删除后所有断点均无超出。
- **useForm 悬挂告警**：触发条件是 form 方法在 Form 未挂载时被调用（`@rc-component/form` 每个方法入口的 `warningUnhooked`）。修复：`UserOrganizationTransferModal`、`OrganizationFormModal` 补 `forceRender`（沿用同页 `UserFormModal`/`UserPartyBindingModal` 既有先例，Form 常驻挂载）；`OrganizationMoveModal`、`OrganizationPartyScopeBatchModal` 删除关闭态 effect 里的 `form.resetFields()`（两弹窗均 `destroyOnHidden`，关闭即卸载表单、重开按 initialValues 重建，重置冗余），组件级 state 重置保留。
- 登录页外部资源超时非本仓资源，未处理。

### 9.8 复核补充发现（登记备查，未在本轮修复）

1. **`monitoring.py` 整个模块未挂载**：全仓无任何 `include_router`/`register_router` 引用（`api/v1/__init__.py` 与 `system.py` 均无），522 行 mock 数据/性能端点全部为死代码。本轮仅按 §2.3 建议清理了其中 `[Any]` mock 键；模块去留建议单独立项。
2. **前端 `assetDictionaryService` 指向未挂载旧域**：7 个方法全部调 `/system-dictionaries*`（对应 `system_dictionaries.py`，该模块被 `api/v1/__init__.py:74-77` `REMOVED CONFLICTING ROUTER` 注释下线；实际挂载的是 `dictionaries.py`，前缀 `/system/dictionaries` 且路由面不同）。当前无页面消费（`assetService` 的 7 个包装方法无调用方），属潜在死代码/契约错位，与 2.1 同族但影响面为零，建议随 monitoring.py 一并立项清理。
3. **`system_monitoring/` 包同样未挂载（复核补充，2026-08-17）**：`backend/src/api/v1/system/system_monitoring/`（`endpoints.py` + `database_endpoints.py`，路由前缀 `/monitoring`）全仓无任何 import/include——与 `monitoring.py` 同类死代码，且两个模块路径前缀相同（均 `/monitoring`），清理时需一并决策去留，避免将来重复挂载冲突。

### 9.9 验证记录

- 后端：ruff / mypy / bandit 对改动文件全部干净；定向套件 `test_static_route_shadowing` + `test_backup_layering` + `test_enum_field_layering` 15 passed、`test_custom_fields` 20 passed、`test_tasks` + `test_tasks_layering` + `test_assets_authz_layering` 70 passed、**`test_logging_security` 2 passed（2.5 复核补修，red→green）**；9.5 运行时探针通过；2.5 真实启动复验无 Logging error、emoji 落盘。
- 前端：oxlint 0 warnings / 0 errors；type-check 通过；定向 vitest 128 passed（assetFieldService / AssetDetailInfo / Analytics 4 套件 / Organization 2 套件）；**复核追加：assetFieldService+AssetDetailInfo 52、Analytics+components 169 passed；浏览器层 /analytics 复验 ExpressionError 清零（修复前 8 console error + 4 pageerror → 修复后 0 图表错误，唯一残留为登录页外部资源超时）**。
- SSOT：`docs/specs/api-contract.md` 从未收录上述端点路径（修复前后均无条目），无契约文档差异；修复状态登记于本节与 CHANGELOG。
- 未做：全量 `make check`（修复已由运行时路由探针 + 单测 + 浏览器复验锁定；建议下次例行点检对 20 路由做全量回归复测）。